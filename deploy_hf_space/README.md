> ⚠️ **Superseded (2026).** Hugging Face now requires a paid PRO plan to run any
> compute-based Space (Gradio/Docker/Streamlit); only static Spaces stay free. The
> free public live demo has moved to **Streamlit Community Cloud + Gemini free tier** —
> see **[`DEPLOY.md`](../DEPLOY.md)** in the repo root. This folder is kept for reference.

# 🚀 Deploy Grounded as a free public Hugging Face Space

This folder holds a **ready-to-upload bundle** (`space/`) that runs the full Grounded
assistant — retrieval + re-ranking + citation enforcement + the local Qwen LLM — on
Hugging Face's **free CPU tier (16 GB RAM)**. No API key. Zero cost.

The bundle is verified working end-to-end (1,252 chunks, cited answers, honest refusal).

## What's in `space/`
- `app.py` — the Streamlit demo (downloads the LLM on first launch, then runs fully offline)
- `requirements.txt` — CPU-only deps (uses prebuilt wheels, nothing compiles)
- `README.md` — the Space card (Hugging Face metadata header)
- `src/`, `config/`, `prompts/`, `regulatory_corpus/`, `corpus_embeddings.npy` — the pipeline + data

## Publish it (about 5 minutes, one-time)
1. Make a free account at **https://huggingface.co** (email or Google).
2. Go to **https://huggingface.co/new-space**:
   - **Owner**: you · **Space name**: `grounded-rbi-compliance-rag`
   - **SDK**: **Streamlit** · **Hardware**: **CPU basic (free)** · **Visibility**: Public
   - Click **Create Space**.
3. On the new Space page → **Files** tab → **Add file → Upload files**.
   Drag in **everything inside this `space/` folder** (keep the folder structure:
   `app.py`, `requirements.txt`, `README.md`, and the `src/`, `config/`, `prompts/`,
   `regulatory_corpus/` folders, plus `corpus_embeddings.npy`). Commit.
4. The Space builds automatically (a few minutes: installs deps, first visitor triggers
   the one-time ~1.9 GB model download). Then it's **live at a public URL** like:
   `https://huggingface.co/spaces/<your-username>/grounded-rbi-compliance-rag`

## Notes
- First answer after a cold start is slow (model download + load); afterwards ~30–60s/answer on free CPU.
- Free Spaces sleep when idle and wake on the next visit — normal for the free tier.
- Put the public URL in your resume/LinkedIn and link it from the GitHub README.
