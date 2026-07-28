# 🚀 Deploy Grounded as a free public live demo (Streamlit Community Cloud)

This gives you a public URL where anyone can ask a compliance question and get a
page-cited answer — running for **free**, with **Google Gemini's free API tier**
doing the generation (so no multi-GB local model, which is what lets it fit a free host).

> Why not Hugging Face Spaces? As of 2026 HF requires a paid PRO plan to run any
> compute-based Space (Gradio/Docker/Streamlit); only static Spaces stay free.
> Streamlit Community Cloud still runs full Python apps for free, so that's the path.

## What powers it
- **App:** `dashboard/streamlit_app.py` (auto-detects the Gemini key and uses it)
- **Deps:** the lean root `requirements.txt` (CPU-only, no llama.cpp)
- **Data:** `regulatory_corpus/` PDFs + committed `corpus_embeddings.npy` (instant load)
- **LLM:** Gemini free tier via `GEMINI_API_KEY` (added as a Streamlit secret, never committed)

## Publish it (about 5 minutes)

1. Make sure this repo is pushed to GitHub (it is).
2. Go to **https://share.streamlit.io** and sign in with GitHub.
3. Click **Create app → Deploy a public app from GitHub**.
4. Fill in:
   - **Repository:** `SwagataBhowmik/<this-repo>`
   - **Branch:** `main`
   - **Main file path:** `dashboard/streamlit_app.py`
5. Click **Advanced settings → Secrets** and paste:
   ```toml
   GEMINI_API_KEY = "AIza...your-key..."
   ```
   (This is the same key from your local `.streamlit/secrets.toml`. It lives only
   in Streamlit's secrets store — never in Git.)
6. Click **Deploy**. First build takes a few minutes (installs deps, downloads the
   small embedding + re-ranker models). Then it's **live at a public URL** like:
   `https://<your-app>.streamlit.app`

## Notes
- Free apps **sleep when idle** and wake on the next visit (a normal ~30s cold start).
- The Gemini **free tier has daily rate limits** — plenty for a demo recruiters click
  a few times, not built for heavy traffic.
- If the build ever hits a memory limit, the quick fix is switching the default model
  to `gemini-flash-lite-latest` (lighter) — but the current setup is expected to fit.
- Put the public URL in your README, resume, and LinkedIn once it's live.
