# 🤖 Grounded — Citation-Enforced RAG Assistant for RBI Compliance

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Live%20Demo-Streamlit-FF4B4B?logo=streamlit&logoColor=white)
![LangGraph](https://img.shields.io/badge/Agent-LangGraph-1C3C3C)
![LLM](https://img.shields.io/badge/LLM-Gemini%20%2F%20Qwen2.5--3B-4285F4?logo=google&logoColor=white)
![CI](https://img.shields.io/badge/CI-Quality%20Gate-2E7D32?logo=githubactions&logoColor=white)
![Cost](https://img.shields.io/badge/Cost-Free%20tier-00897B)

> An **agentic Retrieval-Augmented Generation (RAG)** assistant that answers banking-compliance
> questions over **real RBI Master Directions** — with hybrid retrieval, cross-encoder
> re-ranking, **page-level citation enforcement**, and a **LangGraph agent that declines when
> the evidence is weak instead of hallucinating**.

---

## 🔗 Jump straight to the important bits

| | Resource | What it is |
|---|---|---|
| 🌍 | **[Live interactive demo](https://grounded-citation-enforced-rag-assistant-swagata-bhowmik.streamlit.app/)** | Ask a real compliance question, get a cited answer or an honest refusal (free host — first load may take ~30s to wake). |
| 📓 | **[Guided Jupyter notebook](https://nbviewer.org/github/Swagata-Bhowmik/Grounded-Citation-Enforced-RAG-Assistant-for-RBI-Compliance/blob/main/notebooks/Grounded_RAG_Compliance_Assistant.ipynb)** | The full build story, cell by cell — theory, real before/after examples, every output interpreted. ([view on GitHub](https://github.com/Swagata-Bhowmik/Grounded-Citation-Enforced-RAG-Assistant-for-RBI-Compliance/blob/main/notebooks/Grounded_RAG_Compliance_Assistant.ipynb)) |
| 📊 | **[HTML walkthrough dashboard](https://swagata-bhowmik.github.io/Grounded-Citation-Enforced-RAG-Assistant-for-RBI-Compliance/)** | A no-server, browser-only tour of the problem, method, and results. |
| 📘 | **[Complete project guide (Word)](docs/Grounded_Project_Bible.docx?raw=1)** | Every concept explained from zero, the full build story, the code, deployment, and a 130-question Q&A bank. |

---

## 📖 About

Bank and NBFC compliance teams must answer precise questions against dense, cross-referencing
RBI regulation — and a confidently **wrong** answer carries real regulatory cost. A generic
chatbot will happily hallucinate a plausible-sounding rule.

**Grounded** takes the opposite stance. It retrieves the actual regulation text, answers
**only** from what it retrieved, cites the **exact source page**, and **declines** when the
evidence is insufficient. It's built as an **agent**: it decides whether the retrieved
evidence is strong enough to answer at all, rather than following one fixed path to a forced
answer.

This is the #1 enterprise-AI pattern today (RAG) combined with agentic decision-making and
automated quality gating — applied to a genuine banking use case.

### Why this problem, this data
Regulatory text is an honest stress test for a RAG system: it has exact clause numbers,
defined terms, acronyms (e.g. **KFS** — Key Fact Statement), and supersession notices. Users
often search by an **exact regulation number**, where keyword search beats pure semantic
search — which is precisely why this project uses **hybrid retrieval** rather than embeddings
alone.

---

## ✨ Key features

- **Hybrid retrieval** — BM25 keyword search + semantic (bge-small) search, fused via
  Reciprocal Rank Fusion (RRF), so exact-token matches *and* paraphrases both surface.
- **Cross-encoder re-ranking** — a small model re-scores the top candidates by reading the
  (question, passage) pair together, for far better precision than vector similarity alone.
- **Page-level citation enforcement** — every answer cites its exact source page; if the best
  passage scores below a configured threshold, the system **refuses** instead of guessing.
- **Agentic control (LangGraph)** — `retrieve → assess → (answer | decline) → verify → cite`,
  where the answer-vs-decline branch is the agent's decision.
- **Swappable LLM provider** — a **local Qwen2.5-3B** via llama.cpp (fully offline, zero cost)
  on a full machine, or the **Gemini free-tier API** for the low-RAM public cloud demo. Same
  interface, same citation rules either way.
- **Evaluation layer** — a hand-verified golden set with retrieval-recall and refusal metrics,
  plus **NLI-based faithfulness scoring** (does the answer actually follow from the evidence?).
- **CI quality gate** — a GitHub Actions workflow re-runs the golden-set metrics on every push
  and **fails the build** if quality regresses.

---

## 📊 Results (golden set)

| Metric | Result |
|---|---|
| Retrieval recall@5 (24 in-scope questions) | **1.00** |
| Refusal accuracy (26 out-of-scope questions) | **1.00** |
| NLI faithfulness — grounded vs hallucinated answer | **0.97 vs 0.01** |
| Corpus | 10 RBI docs · 720 pages · ~1.4M chars · 1,252 chunks |

> **Honest note:** metrics are on a small, hand-authored golden set and recall is
> document-level — a strong, defensible baseline, not an inflated one. The CI gate guards
> against regressions. See [Limitations](#-limitations--honest-notes).

---

## 🏗️ How it works

```
PDFs → profile → chunk (384/64 tokens, page-tagged) → bge-small embeddings → vector index
                                                              │
   query ─► hybrid retrieve (BM25 + semantic, RRF) ─► cross-encoder re-rank
                                                              │
              citation guard ─► answer (LLM, page-cited) | decline (insufficient evidence)
              (LangGraph agent: retrieve → assess → answer/decline → verify → cite)
```

**From question to cited answer:**
1. **Chunk** — 720 pages → 1,252 page-tagged chunks (384 tokens, 64 overlap), sized in the
   embedder's own tokens so nothing is silently truncated.
2. **Embed** — `BAAI/bge-small-en-v1.5` → 384-dim vectors.
3. **Retrieve (hybrid)** — BM25 + semantic, fused by RRF.
4. **Re-rank** — `cross-encoder/ms-marco-MiniLM-L-6-v2` re-scores the top candidates.
5. **Enforce citations** — if the best evidence is too weak, decline instead of guessing.
6. **Agent (LangGraph)** — runs the decision flow and a post-answer check that citations exist.
7. **Generate** — the LLM writes the answer grounded **only** in the cited context.

---

## 🗂️ The corpus

Ten **real RBI Master Directions / Master Circulars**, downloaded directly from rbi.org.in,
themed around **lending, credit, and customer protection (banks & NBFCs)** — a coherent,
cross-referencing slice rather than a scattershot dump. The list and per-document stats live
in [`regulatory_corpus/corpus_manifest.csv`](regulatory_corpus/corpus_manifest.csv).

Topics include KYC, digital lending, NBFC scale-based regulation, credit/debit cards,
microfinance, interest rate on advances, priority-sector lending, fraud risk management,
customer service, and outsourcing.

---

## 🧰 Tech stack

Python 3.11 · PyMuPDF · sentence-transformers (bge-small + cross-encoder) · rank-bm25 ·
LangGraph · llama.cpp (Qwen2.5-3B) / Google Gemini (free tier) · NLI faithfulness scoring ·
Streamlit · GitHub Actions — **all free / offline-capable**.

---

## 📁 Repository layout

```
regulatory_corpus/   real RBI PDFs + manifest
notebooks/           the full guided story notebook (Phases 1–3, executed)
src/                 pipeline modules (chunker, embedder, retriever, citation guard, agent, eval, faithfulness, llm_provider)
prompts/             versioned prompt & policy config (prompts.yaml)
evaluation/          golden question set + eval results
scripts/             quality_gate.py + full evaluation runner
tests/               pytest quality-gate tests
dashboard/           Streamlit app + standalone HTML dashboard
docs/                HTML dashboard served via GitHub Pages
config/              portable path/cache config
corpus_embeddings.npy  precomputed embeddings (fast cloud cold-start)
requirements.txt     lean, cloud-deployable dependencies
requirements-lock.txt full pinned local/dev environment
.github/workflows/   CI quality-gate workflow
DEPLOY.md            how to deploy the free live demo
```

---

## 🚀 Run it locally

Dependencies: the root `requirements.txt` is the lean, cloud-deployable set; the full pinned
local/dev environment is in `requirements-lock.txt`.

```bash
# create an environment (example)
pip install -r requirements.txt

# 1) Explore the full story notebook
jupyter lab            # open notebooks/Grounded_RAG_Compliance_Assistant.ipynb

# 2) Launch the interactive dashboard
#    Uses the local Qwen LLM by default; set a GEMINI_API_KEY to use Gemini instead.
streamlit run dashboard/streamlit_app.py

# 3) Open the standalone dashboard (no server needed)
#    double-click dashboard/grounded_dashboard.html

# 4) Run the quality gate
python scripts/quality_gate.py
```

**Using Gemini locally (optional):** copy `.streamlit/secrets.toml.example` to
`.streamlit/secrets.toml` and add your free key from
[Google AI Studio](https://aistudio.google.com/app/apikey):

```toml
GEMINI_API_KEY = "AIza...your-key..."
```

---

## 🌍 Deploy your own live demo (free)

Full steps in **[`DEPLOY.md`](DEPLOY.md)**. In short: deploy `dashboard/streamlit_app.py` on
[Streamlit Community Cloud](https://share.streamlit.io), and paste your `GEMINI_API_KEY` into
the app's **Secrets** (never committed).

**To make the HTML dashboard link live**, enable GitHub Pages:
**repo Settings → Pages → Source: “Deploy from a branch” → Branch: `main`, folder `/docs` → Save.**
It then serves at the `github.io` URL linked at the top.

---

## 🧯 Troubleshooting

| Symptom | Likely cause & fix |
|---|---|
| Live app is blank / “Zzzz” | Free Streamlit apps **sleep when idle**. The first visit wakes it (~30s). Just wait and refresh. |
| First answer is slow | Cold start downloads the small embedding + re-ranker models once, then caches them. Later answers are a few seconds. |
| “🛑 Declined” on a question you think is covered | The evidence scored below the citation threshold. Rephrase with the regulation's own terms (e.g. use “KFS”, exact clause numbers). This is the safety feature working, not a bug. |
| Empty answer from Gemini | Very rare — usually the model spent its token budget “thinking”. The provider already uses a generous limit; retry the question. |
| `404 ... model ... no longer available` | The default model is the stable alias `gemini-flash-latest`. If a specific dated model is retired, set `GEMINI_MODEL` in secrets to another listed model. |
| Cloud build fails on memory | Switch the model to the lighter `gemini-flash-lite-latest` (set `GEMINI_MODEL` in Secrets). |
| GitHub Pages link 404s | Pages isn't enabled yet — see the deploy note above. |
| Local run can't find embeddings | The repo ships `corpus_embeddings.npy`; if chunk count changes, the app/gate rebuilds them automatically. |
| `TOMLDecodeError` in `secrets.toml` | Keys must be quoted: `GEMINI_API_KEY = "AIza..."`, saved as UTF-8 without a BOM. |

---

## 🗺️ Roadmap

- Expand the golden set (50–200 Qs) and add exact-page recall
- Adversarial & cross-document questions
- ~~Optional hosted-LLM provider for a low-RAM cloud deploy~~ ✅ done (Gemini free tier)
- ~~Public live link~~ ✅ [done](https://grounded-citation-enforced-rag-assistant-swagata-bhowmik.streamlit.app/)

---

## ⚠️ Limitations & honest notes

- This is a **portfolio demonstration** of an enterprise RAG pattern on **real** regulations —
  not a deployed product with real traffic, users, or legal sign-off.
- The golden set is **small and hand-authored**, and retrieval recall is **document-level**.
- Nothing here is legal or compliance advice; always verify against the official RBI source.
- The public demo runs on **free tiers** with daily rate limits — fine for a demo, not for load.

---

## 👤 Author

**Swagata Bhowmik** — MSc Data Science, NMIMS Mumbai.
Built as a portfolio project: a modern AI system *built for* banking compliance.

*Real public data only · every answer traceable to a page · free / offline-capable.*
