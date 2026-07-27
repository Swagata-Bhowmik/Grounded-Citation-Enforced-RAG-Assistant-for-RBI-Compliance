"""
evaluation.py
=============
Automated quality metrics for the golden question set. Two families here, both
LLM-free (fast, deterministic), so they are ideal for a CI gate:

1. RETRIEVAL RECALL@k  — for each answerable question, does the correct source
   document appear among the top-k retrieved passages? This checks the engine is
   fetching from the right regulation. The expected document is assigned by hand
   from the question's topic (independent of the retriever), so it is a fair test.

2. REFUSAL ACCURACY    — does the citation-enforcement gate ANSWER the in-scope
   questions and DECLINE the out-of-scope ones? This checks the "don't hallucinate"
   behaviour directly, without needing the LLM.

(NLI faithfulness — which DOES need generated answers — lives in faithfulness.py.)
"""

from __future__ import annotations

import json
from pathlib import Path

from citation_guard import assess


def load_golden(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)["questions"]


def evaluate_retrieval(retriever, golden: list[dict], k: int = 5) -> dict:
    """Document-level recall@k over the answerable questions."""
    rows, hits_count = [], 0
    answerable = [q for q in golden if q["answerable"]]
    for q in answerable:
        results = retriever.retrieve(q["question"], top_k=k)
        found_docs = [h["source_file"] for h in results]
        hit = q["expected_source_file"] in found_docs
        hits_count += int(hit)
        rank = (found_docs.index(q["expected_source_file"]) + 1) if hit else None
        rows.append({"id": q["id"], "expected": q["expected_source_file"],
                     "hit": hit, "rank": rank})
    return {
        "k": k,
        "n": len(answerable),
        "recall_at_k": round(hits_count / len(answerable), 3) if answerable else 0.0,
        "details": rows,
    }


def evaluate_all(retriever, cfg: dict, golden: list[dict], k: int = 5) -> dict:
    """
    Efficient combined evaluation: retrieve ONCE per question and compute BOTH
    recall@k (answerable questions) and refusal accuracy (all questions) from the
    same results. Halves the expensive cross-encoder work versus running the two
    evaluations separately.
    """
    threshold = cfg["answerability_threshold"]
    n_ans = recall_hits = correct = 0
    ret_details, ref_details = [], []

    for q in golden:
        results = retriever.retrieve(q["question"], top_k=k)
        found_docs = [h["source_file"] for h in results]

        # refusal routing (uses the top score, independent of k)
        verdict = assess(results, threshold)
        decision = "answer" if verdict["answerable"] else "decline"
        expected_decision = "answer" if q["answerable"] else "decline"
        ok = decision == expected_decision
        correct += int(ok)
        ref_details.append({"id": q["id"], "expected": expected_decision,
                            "got": decision, "ok": ok})

        # recall@k (only meaningful for answerable questions)
        if q["answerable"]:
            n_ans += 1
            hit = q["expected_source_file"] in found_docs
            recall_hits += int(hit)
            ret_details.append({"id": q["id"], "hit": hit})

    return {
        "recall_at_k": round(recall_hits / n_ans, 3) if n_ans else 0.0,
        "recall_n": n_ans,
        "refusal_accuracy": round(correct / len(golden), 3) if golden else 0.0,
        "refusal_n": len(golden),
        "retrieval_details": ret_details,
        "refusal_details": ref_details,
    }


def evaluate_refusal(retriever, cfg: dict, golden: list[dict], k: int = 3) -> dict:
    """
    Does the enforcement gate route each question correctly?
    Answerable -> 'answer'; out-of-scope -> 'decline'.
    """
    correct, rows = 0, []
    threshold = cfg["answerability_threshold"]
    for q in golden:
        hits = retriever.retrieve(q["question"], top_k=k)
        verdict = assess(hits, threshold)
        decision = "answer" if verdict["answerable"] else "decline"
        expected = "answer" if q["answerable"] else "decline"
        ok = decision == expected
        correct += int(ok)
        rows.append({"id": q["id"], "expected": expected, "got": decision,
                     "top_score": round(verdict["top_score"], 2)
                     if verdict["top_score"] is not None else None, "ok": ok})
    return {
        "n": len(golden),
        "accuracy": round(correct / len(golden), 3) if golden else 0.0,
        "details": rows,
    }
