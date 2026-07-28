# 🤖 Grounded — Citation-Enforced RAG Assistant for RBI Compliance

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Live%20Demo-online-FF4B4B?logo=streamlit&logoColor=white)
![LangGraph](https://img.shields.io/badge/Agent-LangGraph-1C3C3C)
![CI](https://img.shields.io/badge/CI-Quality%20Gate-2E7D32?logo=githubactions&logoColor=white)
![Cost](https://img.shields.io/badge/Cost-Free%20tier-00897B)

An **agentic RAG assistant** that answers banking-compliance questions over real **RBI Master
Directions** — citing the exact source page, and **declining when the evidence is weak instead of
hallucinating**.

---

## 🎬 Explore the project

Three ways to see it in action — start with the live demo.

| | Deliverable | Description |
|---|---|---|
| 🌍 | **[Live Demo (online dashboard)](https://grounded-citation-enforced-rag-assistant-swagata-bhowmik.streamlit.app/)** | Ask a real compliance question and get a page-cited answer — or an honest refusal. *(Free host; first load ~30s to wake.)* |
| 📊 | **[Interactive Walkthrough (offline dashboard)](https://swagata-bhowmik.github.io/Grounded-Citation-Enforced-RAG-Assistant-for-RBI-Compliance/)** | A 15-chapter visual story of how it works — no install, runs in the browser. |
| 📓 | **[Guided Notebook](https://nbviewer.org/github/Swagata-Bhowmik/Grounded-Citation-Enforced-RAG-Assistant-for-RBI-Compliance/blob/main/notebooks/Grounded_RAG_Compliance_Assistant.ipynb)** | The full build story, cell by cell, with every result interpreted. |

---

## 🎯 What it does

Bank and NBFC compliance teams must answer precise questions against dense RBI regulation, where a
confidently **wrong** answer carries real regulatory cost. A generic chatbot hallucinates. **Grounded**
retrieves the actual regulation text, answers **only** from it, **cites the exact page**, and **refuses**
when the documents don't support an answer.

## ✨ Key features

- 🔍 **Hybrid retrieval** — keyword (BM25) + semantic search, fused with Reciprocal Rank Fusion
- 🎯 **Cross-encoder re-ranking** — a second, precise pass over the shortlist
- 📄 **Citation enforcement** — every answer cites its page; weak evidence triggers a refusal
- 🧠 **Agentic control (LangGraph)** — `retrieve → assess → answer / decline → verify → cite`
- 🔄 **Swappable LLM** — local Qwen2.5-3B (offline) or Google Gemini (free cloud), one interface
- 📈 **Measured quality** — golden question set, NLI faithfulness scoring, and a CI quality gate

## 📊 Results

| Metric | Result | Measured over |
|---|---|---|
| Retrieval recall@5 | **1.00** | 24 answerable questions |
| Refusal accuracy | **1.00** | 26 questions (24 answer + 2 decline) |
| NLI faithfulness (grounded vs hallucinated) | **0.97 vs 0.01** | supported vs invented answers |
| Corpus | **10 docs · 720 pages · 1,252 chunks** | real RBI Master Directions |

> Honest scope: metrics are on a small, hand-authored golden set and recall is document-level — a
> defensible baseline, guarded against regression by the CI gate. Not legal advice.

## 🏗️ How it works

```
PDFs → chunk (384-tok, page-tagged) → embeddings → index
                                          │
   question ─► hybrid retrieve (BM25 + semantic, RRF) ─► cross-encoder re-rank
                                          │
        citation guard ─► LLM writes page-cited answer  |  decline (weak evidence)
        └─ LangGraph agent: retrieve → assess → answer/decline → verify → cite ─┘
```

## 🧰 Tech stack

Python · PyMuPDF · sentence-transformers (bge-small + cross-encoder) · rank-bm25 · LangGraph ·
llama.cpp (Qwen2.5-3B) / Google Gemini · NLI faithfulness · Streamlit · GitHub Actions — **all free.**

## ⚠️ Limitations

Focused 10-document corpus (declines outside it by design) · small hand-authored evaluation set ·
document-level recall · a portfolio demonstration, **not legal advice or a production service**.

---

**Author:** Swagata Bhowmik · MSc Data Science
*Every answer traceable to a page · free / offline-capable.*
