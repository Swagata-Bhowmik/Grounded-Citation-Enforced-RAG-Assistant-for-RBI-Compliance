"""
quality_gate.py
===============
The automated CI quality gate. Runs the FAST, deterministic, LLM-free metrics
(retrieval recall + refusal accuracy) over the golden set and EXITS NON-ZERO if
quality drops below the agreed thresholds. A CI workflow runs this on every push;
a regression fails the build.

Why only the LLM-free metrics in CI: retrieval recall and refusal accuracy are
deterministic and fast, so they gate reliably. NLI faithfulness needs generated
answers (slow on CPU) and is evaluated locally / in the notebook rather than on
every push.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.append(str(REPO / "config"))
sys.path.append(str(REPO / "src"))

import project_paths
project_paths.apply_env()

from document_chunker import get_tokenizer, chunk_corpus
from embedder import load_embedder, embed_passages
from hybrid_retriever import HybridRetriever
from citation_guard import load_prompt_config
from evaluation import load_golden, evaluate_all

# --- Quality thresholds the build must meet -------------------------------
RECALL_AT_5_MIN = 0.85
REFUSAL_ACCURACY_MIN = 0.85


def _get_embeddings(chunks):
    """Load cached embeddings if present, else compute (and cache) them."""
    emb_dir = Path(project_paths.CACHE_ROOT) / "embeddings"
    emb_path = emb_dir / "corpus_embeddings.npy"
    if emb_path.exists():
        emb = np.load(emb_path)
        if emb.shape[0] == len(chunks):
            return emb
    embedder = load_embedder()
    emb = embed_passages(embedder, [c["text"] for c in chunks], show_progress=False)
    emb_dir.mkdir(parents=True, exist_ok=True)
    np.save(emb_path, emb)
    return emb


def main() -> int:
    tok = get_tokenizer()
    chunks = chunk_corpus(str(project_paths.CORPUS_DIR), 384, 64, tokenizer=tok)
    embeddings = _get_embeddings(chunks)
    retriever = HybridRetriever(chunks, embeddings, load_embedder())
    cfg = load_prompt_config(str(project_paths.PROMPTS_DIR))
    golden = load_golden(str(project_paths.EVALUATION_DIR / "golden_questions.json"))

    res = evaluate_all(retriever, cfg, golden, k=5)

    print("=" * 56)
    print("GROUNDED — CI QUALITY GATE")
    print("=" * 56)
    print(f"Retrieval recall@5 : {res['recall_at_k']:.3f}  (min {RECALL_AT_5_MIN})  over {res['recall_n']} Qs")
    print(f"Refusal accuracy   : {res['refusal_accuracy']:.3f}  (min {REFUSAL_ACCURACY_MIN})  over {res['refusal_n']} Qs")

    passed = (res["recall_at_k"] >= RECALL_AT_5_MIN
              and res["refusal_accuracy"] >= REFUSAL_ACCURACY_MIN)
    print("-" * 56)
    print("RESULT:", "PASS ✅" if passed else "FAIL ❌")
    print("=" * 56)
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
