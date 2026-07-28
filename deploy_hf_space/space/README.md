---
title: Grounded RBI Compliance RAG
emoji: 🤖
colorFrom: blue
colorTo: purple
sdk: streamlit
sdk_version: 1.60.0
app_file: app.py
pinned: false
license: mit
short_description: Citation-enforced, fully-offline agentic RAG over real RBI Master Directions.
---

# 🤖 Grounded — Citation-Enforced RAG for RBI Compliance

Ask a banking-compliance question over real **RBI Master Directions** and get a
**page-cited answer** — or an honest **refusal** when the evidence isn't there.

- **Hybrid retrieval** (BM25 + semantic) → **cross-encoder re-ranking** → **page-level citations**
- **LangGraph agent** that declines on insufficient evidence instead of hallucinating
- **Local LLM** (Qwen2.5-3B via llama.cpp) — **fully offline, zero API cost**

> Runs a real language model on a free shared CPU, so an answer takes ~30–60 seconds.
> That is the honest cost of a fully-offline, zero-API demo.

Full source, the guided notebook, and the evaluation/CI layer:
**https://github.com/Swagata-Bhowmik/Grounded-Citation-Enforced-RAG-Assistant-for-RBI-Compliance**
