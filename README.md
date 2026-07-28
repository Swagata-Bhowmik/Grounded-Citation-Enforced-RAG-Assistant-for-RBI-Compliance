# 🤖 Grounded — Citation-Enforced RAG Assistant for RBI Compliance

### 🌍 [**Try the live demo →**](https://grounded-citation-enforced-rag-assistant-swagata-bhowmik.streamlit.app/)

Ask a real RBI-compliance question and watch it retrieve, cite the exact page, or honestly
decline. (Free tier: sleeps when idle — the first load may take ~30s to wake.)

A production-grade **agentic RAG** system for banking-compliance Q&A over real
**RBI Master Directions** — with hybrid retrieval, cross-encoder re-ranking, **page-level
citation enforcement**, and a **LangGraph agent that declines on insufficient evidence instead
of hallucinating**. Runs end-to-end on free, local tools at **zero API cost**.

---

## ✨ Highlights

- **Hybrid retrieval** — BM25 keyword + semantic (bge-small) search, fused via Reciprocal Rank Fusion
- **Cross-encoder re-ranking** — re-scores top candidates for precision
- **Page-level citation enforcement** — every answer cites its exact source page; declines when evidence is weak
- **Agentic control (LangGraph)** — `retrieve → assess → (answer | decline) → verify → cite`
- **Local LLM** — Qwen2.5-3B-Instruct via llama.cpp, fully offline
- **Evaluation layer** — hand-verified golden set, retrieval-recall & refusal metrics, **NLI faithfulness scoring**
- **CI quality gate** — GitHub Actions fails the build on quality regression

## 📊 Results (golden set)

| Metric | Result |
|---|---|
| Retrieval recall@5 (24 questions) | **1.00** |
| Refusal accuracy (26 questions) | **1.00** |
| NLI faithfulness — grounded vs hallucinated | **0.97 vs 0.01** |
| Corpus | 10 RBI docs · 720 pages · ~1.4M chars · 1,252 chunks |

> Honest note: metrics are on a small, hand-authored golden set and recall is document-level —
> a strong, defensible baseline, not an inflated one. The CI gate guards against regressions.

## 🏗️ Architecture

```
PDFs → profile → chunk (384/64, page-tagged) → bge-small embeddings → ChromaDB
                                                          │
   query ─► hybrid retrieve (BM25 + semantic, RRF) ─► cross-encoder re-rank
                                                          │
                        citation guard ─► answer (local LLM, cited) | decline
                        (LangGraph agent: retrieve→assess→answer/decline→verify→cite)
```

## 📁 Repository layout

```
regulatory_corpus/   real RBI PDFs + manifest
notebooks/           the full guided story notebook (Phases 1–3, executed)
src/                 pipeline modules (chunker, embedder, retriever, agent, eval, faithfulness)
prompts/             versioned prompt & policy config (prompts.yaml)
evaluation/          golden question set + eval results
scripts/             quality_gate.py (CI gate)
tests/               pytest quality-gate tests
dashboard/           Streamlit app + standalone HTML dashboard
config/              portable path/cache config
.github/workflows/   CI quality-gate workflow
```

## 🚀 Run it locally

> Dependencies: the root `requirements.txt` is the lean, cloud-deployable set;
> the full pinned local/dev environment is in `requirements-lock.txt`.

```bash
conda activate D:\grounded-rag-env

# 1) Explore the full story notebook
jupyter lab   # open notebooks/Grounded_RAG_Compliance_Assistant.ipynb

# 2) Launch the interactive dashboard
#    (uses the local Qwen LLM by default; set GEMINI_API_KEY to use Gemini instead)
streamlit run dashboard/streamlit_app.py

# 3) Open the standalone dashboard (no server needed)
#    double-click dashboard/grounded_dashboard.html

# 4) Run the quality gate
python scripts/quality_gate.py
```

## 🧰 Tech stack

Python 3.11 · PyMuPDF · sentence-transformers (bge-small) · ChromaDB · rank-bm25 ·
cross-encoder re-ranker · LangGraph · llama.cpp (Qwen2.5-3B) · NLI faithfulness ·
Streamlit · GitHub Actions · **all free / offline**.

## 🌍 Live demo (free)

**Live:** https://grounded-citation-enforced-rag-assistant-swagata-bhowmik.streamlit.app/

Runs free on **Streamlit Community Cloud** using the **Gemini free-tier API** for generation
(a swappable provider — the local Qwen LLM still runs fully offline on a full machine).
Redeploy instructions in **[`DEPLOY.md`](DEPLOY.md)**.

## 🗺️ Roadmap

- Expand the golden set (50–200 Qs), add exact-page recall
- Adversarial & cross-document questions
- ~~Optional hosted-LLM provider for a low-RAM cloud deploy~~ ✅ done (Gemini)
- Publish the Streamlit Community Cloud public link

---

*Fully offline · zero API cost · every answer traceable to a page.*
