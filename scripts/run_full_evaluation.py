"""Run the full evaluation: retrieval recall, refusal accuracy, NLI faithfulness."""
import sys, json, numpy as np
sys.path.append("config"); sys.path.append("src")
import project_paths
project_paths.apply_env()

from document_chunker import get_tokenizer, chunk_corpus
from embedder import load_embedder
from hybrid_retriever import HybridRetriever
from citation_guard import load_prompt_config, guard
from evaluation import load_golden, evaluate_retrieval, evaluate_refusal
from faithfulness import load_nli, faithfulness

tok = get_tokenizer()
chunks = chunk_corpus(str(project_paths.CORPUS_DIR), 384, 64, tokenizer=tok)
embeddings = np.load(str(project_paths.CACHE_ROOT / "embeddings" / "corpus_embeddings.npy"))
embedder = load_embedder()
retriever = HybridRetriever(chunks, embeddings, embedder)
cfg = load_prompt_config(str(project_paths.PROMPTS_DIR))
golden = load_golden(str(project_paths.EVALUATION_DIR / "golden_questions.json"))

print("=== RETRIEVAL RECALL@5 ===")
ret = evaluate_retrieval(retriever, golden, k=5)
print("recall@5:", ret["recall_at_k"], "over", ret["n"], "answerable questions")
misses = [d for d in ret["details"] if not d["hit"]]
print("misses:", [m["id"] for m in misses] or "none")

print("\n=== REFUSAL ACCURACY ===")
ref = evaluate_refusal(retriever, cfg, golden, k=3)
print("accuracy:", ref["accuracy"], "over", ref["n"], "questions")
wrong = [d for d in ref["details"] if not d["ok"]]
print("wrong routing:", [w["id"] for w in wrong] or "none")

print("\n=== NLI FAITHFULNESS (demo) ===")
nli = load_nli()
from llm_provider import get_llm
llm = get_llm()

q = "What must a digital lending app disclose to borrowers through the Key Fact Statement?"
hits = retriever.retrieve(q, top_k=3)
g = guard(hits, cfg)
answer = llm.chat(cfg["system_prompt"], cfg["answer_template"].format(context=g["context"], question=q))
passages = [h["text"] for h in hits]
faith = faithfulness(nli, passages, answer)
print("Q:", q)
print("answer:", answer[:200])
print("faithfulness (grounded answer):", faith["faithfulness"], "| supported_fraction:", faith["supported_fraction"])

hallucinated = "Digital lending apps must offer borrowers free airline miles and a 90-day interest-free holiday on every loan."
faith_bad = faithfulness(nli, passages, hallucinated)
print("faithfulness (hallucinated answer):", faith_bad["faithfulness"], "| supported_fraction:", faith_bad["supported_fraction"])

# Persist results for the notebook / CI gate to reuse.
out = {
    "retrieval_recall_at_5": ret["recall_at_k"],
    "retrieval_n": ret["n"],
    "retrieval_misses": [m["id"] for m in misses],
    "refusal_accuracy": ref["accuracy"],
    "refusal_details": ref["details"],
    "faithfulness_grounded": faith["faithfulness"],
    "faithfulness_hallucinated": faith_bad["faithfulness"],
}
with open(str(project_paths.EVALUATION_DIR / "eval_results.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2)
print("\nSaved eval_results.json")
