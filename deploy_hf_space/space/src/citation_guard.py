"""
citation_guard.py
=================
Citation enforcement: the rule that makes "Grounded" decline instead of guess.

After hybrid retrieval + cross-encoder re-ranking, the TOP passage carries a
relevance score. If even the best passage is not relevant enough (score below a
configured threshold), we REFUSE to answer rather than fabricate one. When we do
answer, we assemble a context block where every passage is labelled with its
source document and page, so the downstream answer can cite it.

The threshold and all prompt text live in prompts/prompts.yaml (versioned), not
hard-coded here — so policy can change without touching code.
"""

from __future__ import annotations

from pathlib import Path
import yaml


def load_prompt_config(prompts_dir: str) -> dict:
    with open(Path(prompts_dir) / "prompts.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def assess(hits: list[dict], threshold: float) -> dict:
    """
    Decide whether the retrieved evidence is strong enough to answer.
    Uses the top cross-encoder score among the hits.
    """
    if not hits:
        return {"answerable": False, "top_score": None, "reason": "no passages retrieved"}
    top_score = max(h["cross_score"] for h in hits)
    answerable = top_score >= threshold
    return {
        "answerable": answerable,
        "top_score": top_score,
        "reason": ("sufficient evidence" if answerable
                   else f"best passage scored {top_score:.3f} < threshold {threshold}"),
    }


def build_cited_context(hits: list[dict]) -> str:
    """Format retrieved passages into a labelled, citable context block."""
    blocks = []
    for h in hits:
        tag = f'[{h["source_file"]} p.{h["page"]}]'
        blocks.append(f"{tag}\n{h['text'].strip()}")
    return "\n\n".join(blocks)


def guard(hits: list[dict], config: dict) -> dict:
    """
    The enforcement gate. Returns either an 'answer-ready' context bundle or a
    refusal, based on the configured answerability threshold.
    """
    verdict = assess(hits, config["answerability_threshold"])
    if not verdict["answerable"]:
        return {
            "decision": "decline",
            "message": config["refusal_message"].strip(),
            "top_score": verdict["top_score"],
        }
    return {
        "decision": "answer",
        "context": build_cited_context(hits),
        "citations": [f'{h["source_file"]} p.{h["page"]}' for h in hits],
        "top_score": verdict["top_score"],
    }
