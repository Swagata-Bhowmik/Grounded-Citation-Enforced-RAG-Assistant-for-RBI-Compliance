"""
faithfulness.py
===============
NLI-based faithfulness scoring — the offline, zero-cost alternative to an LLM judge.

THE IDEA
--------
"Faithful" means every claim in the generated answer is actually supported by the
retrieved evidence (not invented). We use a Natural Language Inference (NLI) model,
which classifies a (premise, hypothesis) pair as ENTAILMENT / NEUTRAL /
CONTRADICTION. For each SENTENCE of the answer (the hypothesis), we ask: does any
retrieved passage (the premise) ENTAIL it?

  * per-sentence support = max entailment probability across the retrieved passages
    (a claim is faithful if ANY passage supports it — and taking the max also sidesteps
    the NLI model's ~512-token input limit, since we test one passage at a time)
  * faithfulness score = mean per-sentence support over the answer's sentences

MODEL: cross-encoder/nli-distilroberta-base — small, CPU-friendly, standard tokenizer
(no sentencepiece), downloaded once to the D: cache.
"""

from __future__ import annotations

import re
import numpy as np
from sentence_transformers import CrossEncoder

NLI_MODEL_NAME = "cross-encoder/nli-distilroberta-base"

# Split ONLY at a real sentence boundary: a lowercase letter, then '.'/'?'/'!',
# then space(s), then an uppercase letter or '('. This deliberately does NOT split
# on abbreviations ("no."), alphanumeric codes ("DOR.STR.REC"), or decimal/clause
# numbers ("13.03") — all rampant in regulatory text — which otherwise shred
# sentences into fragments and wreck NLI entailment.
_SENT_BOUNDARY = re.compile(r"(?<=[a-z])[.?!]\s+(?=[A-Z(])")


def load_nli(model_name: str = NLI_MODEL_NAME) -> CrossEncoder:
    return CrossEncoder(model_name)


def _entail_index(nli: CrossEncoder) -> int:
    """Find which output column is 'entailment' (robust to label ordering)."""
    id2label = nli.model.config.id2label
    for idx, label in id2label.items():
        if str(label).lower() == "entailment":
            return int(idx)
    return 1  # sensible default for these NLI models


def split_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()          # collapse PDF newlines/spaces
    text = re.sub(r"\[[^\]]*p\.\d+\]", "", text)       # drop citation tags
    parts = [s.strip(" .;") for s in _SENT_BOUNDARY.split(text) if s.strip(" .;")]
    # Drop trivially short fragments (e.g. a lone clause number).
    return [s for s in parts if len(s) > 20]


def _softmax(x: np.ndarray) -> np.ndarray:
    e = np.exp(x - x.max(axis=-1, keepdims=True))
    return e / e.sum(axis=-1, keepdims=True)


def faithfulness(nli: CrossEncoder, passages: list[str], answer: str) -> dict:
    """
    Score how well `answer` is supported by the retrieved `passages`.

    IMPORTANT: NLI models are trained on SHORT premises, so we break the retrieved
    passages into individual sentences and test each answer sentence against every
    context sentence, taking the best (max) entailment. Feeding whole 380-token
    passages as the premise makes the model output mushy ~0.5 scores for everything;
    sentence-level premises restore sharp, discriminating judgements.

    Returns overall score (0..1), fraction of supported sentences, and per-sentence detail.
    """
    answer_sents = split_sentences(answer)
    context_sents = []
    for p in passages:
        context_sents.extend(split_sentences(p))
    if not answer_sents or not context_sents:
        return {"faithfulness": 0.0, "supported_fraction": 0.0, "sentences": []}

    ent_idx = _entail_index(nli)
    rows, supports = [], []
    for sent in answer_sents:
        pairs = [(ctx, sent) for ctx in context_sents]        # premise=context sentence
        logits = np.asarray(nli.predict(pairs))
        if logits.ndim == 1:
            logits = logits.reshape(1, -1)
        ent_probs = _softmax(logits)[:, ent_idx]
        best = float(ent_probs.max())
        supports.append(best)
        rows.append({"sentence": sent[:90], "support": round(best, 3),
                     "supported": best >= 0.5})

    return {
        "faithfulness": round(float(np.mean(supports)), 3),
        "supported_fraction": round(float(np.mean([s >= 0.5 for s in supports])), 3),
        "sentences": rows,
    }
