"""
test_quality_gate.py
====================
Pytest wrapper around the quality metrics, so the gate integrates with standard
CI test tooling. Fails (and thus fails the build) if retrieval recall or refusal
accuracy regress below threshold.
"""

import sys
from pathlib import Path

import numpy as np
import pytest

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

RECALL_AT_5_MIN = 0.85
REFUSAL_ACCURACY_MIN = 0.85


@pytest.fixture(scope="module")
def results():
    tok = get_tokenizer()
    chunks = chunk_corpus(str(project_paths.CORPUS_DIR), 384, 64, tokenizer=tok)
    emb_path = Path(project_paths.CACHE_ROOT) / "embeddings" / "corpus_embeddings.npy"
    if emb_path.exists() and np.load(emb_path).shape[0] == len(chunks):
        embeddings = np.load(emb_path)
    else:
        embeddings = embed_passages(load_embedder(), [c["text"] for c in chunks],
                                    show_progress=False)
    retriever = HybridRetriever(chunks, embeddings, load_embedder())
    cfg = load_prompt_config(str(project_paths.PROMPTS_DIR))
    golden = load_golden(str(project_paths.EVALUATION_DIR / "golden_questions.json"))
    return evaluate_all(retriever, cfg, golden, k=5)   # one retrieval pass, both metrics


def test_retrieval_recall(results):
    assert results["recall_at_k"] >= RECALL_AT_5_MIN, \
        f"recall@5 {results['recall_at_k']} < {RECALL_AT_5_MIN}"


def test_refusal_accuracy(results):
    assert results["refusal_accuracy"] >= REFUSAL_ACCURACY_MIN, \
        f"refusal accuracy {results['refusal_accuracy']} < {REFUSAL_ACCURACY_MIN}"
