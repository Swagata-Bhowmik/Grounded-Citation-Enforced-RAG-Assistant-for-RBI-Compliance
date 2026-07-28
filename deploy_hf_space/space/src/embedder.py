"""
embedder.py
===========
Turns text into embeddings (vectors) using a small, fast, fully-offline model.

WHAT AN EMBEDDING IS
--------------------
An embedding is a list of numbers (here, 384 of them) that captures the *meaning*
of a piece of text. Texts with similar meaning get vectors that point in similar
directions, so we can find relevant passages by comparing vector directions
(cosine similarity) instead of matching exact words.

MODEL: BAAI/bge-small-en-v1.5
-----------------------------
  * embedding dimension : 384
  * max input length    : 512 tokens (why chunks were capped under 512)
  * runs on CPU         : small enough to embed the whole corpus locally, free
  * normalization       : bge models are designed to be L2-normalized, after
                          which cosine similarity == dot product.

QUERY vs PASSAGE (an important bge detail)
------------------------------------------
bge-*-en-v1.5 retrieval works best when the *query* is prefixed with a short
instruction, while the stored *passages* are embedded as-is. We implement both
paths so retrieval later is done the way the model was trained.
"""

from __future__ import annotations

import numpy as np
from sentence_transformers import SentenceTransformer

EMBED_MODEL_NAME = "BAAI/bge-small-en-v1.5"
EMBED_DIM = 384

# Recommended query-side instruction for bge-*-en-v1.5 retrieval.
QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "


def load_embedder(model_name: str = EMBED_MODEL_NAME) -> SentenceTransformer:
    """Load the embedding model (downloads once to the D: HuggingFace cache)."""
    return SentenceTransformer(model_name, device="cpu")


def embed_passages(
    model: SentenceTransformer,
    texts: list[str],
    batch_size: int = 32,
    show_progress: bool = True,
) -> np.ndarray:
    """Embed stored passages/chunks. Returns an (n, 384) float32 array."""
    return model.encode(
        texts,
        batch_size=batch_size,
        normalize_embeddings=True,      # L2-normalize -> cosine == dot product
        show_progress_bar=show_progress,
        convert_to_numpy=True,
    ).astype("float32")


def embed_query(model: SentenceTransformer, query: str) -> np.ndarray:
    """Embed a search query, with the bge query instruction prepended."""
    return model.encode(
        QUERY_INSTRUCTION + query,
        normalize_embeddings=True,
        convert_to_numpy=True,
    ).astype("float32")


def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two (already L2-normalized) vectors = dot product."""
    return float(np.dot(a, b))


if __name__ == "__main__":
    # Quick self-test on 3 tiny sentences (also pre-caches the model to D:).
    model = load_embedder()
    print("Model loaded:", EMBED_MODEL_NAME, "| dim =", EMBED_DIM)

    samples = [
        "What is the beneficial owner threshold for a trust under KYC rules?",
        "For a trust, the beneficial owner includes persons with 10 percent interest.",
        "Priority sector lending targets for regional rural banks.",
    ]
    vecs = embed_passages(model, samples, show_progress=False)
    print("Embeddings shape:", vecs.shape)

    q = embed_query(model, samples[0])
    print("\nSimilarity of the KYC question to each sample:")
    for i, s in enumerate(samples):
        print(f"  {cosine_sim(q, vecs[i]):.3f}  <- {s[:60]}")
