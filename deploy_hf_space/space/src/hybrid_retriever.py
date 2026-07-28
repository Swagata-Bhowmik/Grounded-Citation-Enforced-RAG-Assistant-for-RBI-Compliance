"""
hybrid_retriever.py
===================
Phase 2 retrieval: combine KEYWORD search (BM25) with SEMANTIC search (embeddings),
fuse them, then RE-RANK the survivors with a cross-encoder for precision.

WHY HYBRID (the core Phase-2 argument)
--------------------------------------
* Semantic search is great at meaning but weak on EXACT tokens — regulation
  numbers, acronyms (KFS), defined terms. A user typing an exact clause number
  wants a literal match.
* BM25 (keyword search) is the opposite: excellent on exact tokens, blind to
  paraphrase.
Using BOTH and fusing their rankings gets the best of each.

THE THREE STAGES
----------------
1. CANDIDATE GENERATION: take the top results from BM25 and from semantic search.
2. FUSION (Reciprocal Rank Fusion): combine the two rank lists into one. RRF needs
   only ranks, not raw scores, so it is robust to the fact that BM25 scores and
   cosine similarities live on totally different scales.
3. RE-RANKING (cross-encoder): a small model reads the (query, passage) pair
   TOGETHER and scores true relevance far more accurately than comparing two
   independently-made vectors. We only run it on the ~50 fused candidates (cheap),
   not all 1,252 chunks.
"""

from __future__ import annotations

import re
from collections import defaultdict

import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder

from embedder import embed_query

# Keep clause numbers like "3.1" or "24.2" as single tokens (they matter here).
_TOKEN_RE = re.compile(r"[a-z0-9]+(?:\.[a-z0-9]+)*")

CROSS_ENCODER_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def rrf_fuse(rankings: list[list[int]], k: int = 60) -> list[int]:
    """Reciprocal Rank Fusion: fuse several ranked idx-lists into one order."""
    scores: dict[int, float] = defaultdict(float)
    for ranking in rankings:
        for rank, idx in enumerate(ranking):
            scores[idx] += 1.0 / (k + rank + 1)
    return [idx for idx, _ in sorted(scores.items(), key=lambda x: x[1], reverse=True)]


class HybridRetriever:
    def __init__(self, chunks, embeddings, embedder, load_cross_encoder=True):
        self.chunks = chunks
        self.embeddings = embeddings                 # (n, 384) L2-normalized
        self.embedder = embedder
        self.bm25 = BM25Okapi([tokenize(c["text"]) for c in chunks])
        self.cross_encoder = (
            CrossEncoder(CROSS_ENCODER_NAME) if load_cross_encoder else None
        )

    # ---- individual retrievers -------------------------------------------
    def semantic_rank(self, query: str, top: int = 50) -> list[int]:
        qv = embed_query(self.embedder, query)
        sims = self.embeddings @ qv                  # cosine (vectors normalized)
        return list(np.argsort(-sims)[:top])

    def bm25_rank(self, query: str, top: int = 50) -> list[int]:
        scores = self.bm25.get_scores(tokenize(query))
        return list(np.argsort(-scores)[:top])

    # ---- hybrid + rerank -------------------------------------------------
    def hybrid_candidates(self, query: str, top_each: int = 50) -> list[int]:
        sem = self.semantic_rank(query, top_each)
        kw = self.bm25_rank(query, top_each)
        return rrf_fuse([sem, kw])

    def rerank(self, query: str, cand_idxs: list[int], top_k: int = 5):
        pairs = [(query, self.chunks[i]["text"]) for i in cand_idxs]
        scores = self.cross_encoder.predict(pairs)
        order = np.argsort(-scores)[:top_k]
        return [(cand_idxs[o], float(scores[o])) for o in order]

    def retrieve(self, query: str, top_k: int = 5, pool: int = 50,
                 use_rerank: bool = True) -> list[dict]:
        cands = self.hybrid_candidates(query, top_each=pool)
        if use_rerank and self.cross_encoder is not None:
            ranked = self.rerank(query, cands[:pool], top_k=top_k)
        else:
            ranked = [(i, float("nan")) for i in cands[:top_k]]
        hits = []
        for idx, score in ranked:
            c = self.chunks[idx]
            hits.append({
                "text": c["text"],
                "source_file": c["source_file"],
                "page": c["page"],
                "cross_score": round(score, 3),
            })
        return hits


if __name__ == "__main__":
    import sys
    sys.path.append("config"); sys.path.append("src")
    import project_paths
    project_paths.apply_env()
    from document_chunker import get_tokenizer, chunk_corpus
    from embedder import load_embedder

    tok = get_tokenizer()
    chunks = chunk_corpus(str(project_paths.CORPUS_DIR), 384, 64, tokenizer=tok)
    embeddings = np.load(str(project_paths.CACHE_ROOT / "embeddings" / "corpus_embeddings.npy"))
    embedder = load_embedder()

    hr = HybridRetriever(chunks, embeddings, embedder)

    for q in [
        "What must a digital lending app disclose to borrowers via KFS?",
        "beneficial owner threshold for a trust",
        "How is a recipe for chocolate cake prepared?",
    ]:
        print("\n=== Q:", q)
        print("-- semantic-only top3 --")
        for i in hr.semantic_rank(q, 3):
            print(f"   {chunks[i]['source_file']} p.{chunks[i]['page']}")
        print("-- hybrid + rerank top3 --")
        for h in hr.retrieve(q, top_k=3):
            print(f"   cross={h['cross_score']:>7.3f} | {h['source_file']} p.{h['page']}")
