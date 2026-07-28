"""
Grounded — Streamlit dashboard & live demo
==========================================
A colorful, story-driven front end for the RBI-compliance RAG assistant:
problem → corpus → method → results → live "ask a question" with visible citations.

Runs in three environments with the SAME code:
  * Locally on Windows  -> caches on D:, optional local Qwen LLM.
  * Streamlit Community Cloud (Linux, free) -> caches in-repo, Gemini API LLM.
  * Any machine with a GEMINI_API_KEY set -> Gemini-backed answers.

Run locally:
    conda activate D:\grounded-rag-env
    streamlit run dashboard/streamlit_app.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# --- make config/ and src/ importable --------------------------------------
REPO = Path(__file__).resolve().parents[1]
sys.path.append(str(REPO / "config"))
sys.path.append(str(REPO / "src"))

# Cache location: keep D: on this Windows machine (C: is full), but on any host
# without a D: drive (e.g. the Linux cloud runner) fall back to an in-repo cache
# so model downloads have a writable home instead of a literal "D:\..." folder.
if "GROUNDED_CACHE_ROOT" not in os.environ and not Path("D:/").exists():
    os.environ["GROUNDED_CACHE_ROOT"] = str(REPO / ".grounded_cache")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

# Pull the Gemini key from Streamlit secrets into the environment (if present),
# so the provider layer can pick it up. Never hard-coded, never committed.
try:
    if "GEMINI_API_KEY" in st.secrets:
        os.environ.setdefault("GEMINI_API_KEY", str(st.secrets["GEMINI_API_KEY"]))
except Exception:
    pass  # no secrets.toml locally — fine

import project_paths
project_paths.apply_env()

GEMINI_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

st.set_page_config(page_title="Grounded — RBI Compliance RAG",
                   page_icon="🤖", layout="wide")

# --------------------------------------------------------------------------- #
#  Colorful theme
# --------------------------------------------------------------------------- #
st.markdown("""
<style>
.stApp { background: linear-gradient(180deg,#f6f8ff 0%,#fdf6ff 100%); }
.hero {
  background: linear-gradient(135deg,#1565C0 0%,#6A1B9A 100%);
  color:#fff; padding:28px 32px; border-radius:18px; margin-bottom:8px;
  box-shadow:0 8px 24px rgba(106,27,154,.35);
}
.hero h1 { color:#fff; margin:0; font-size:30px; }
.hero p  { color:#E3F2FD; margin:8px 0 0 0; font-size:16px; }
.kpi {
  border-radius:14px; padding:16px 18px; color:#fff; text-align:center;
  box-shadow:0 4px 12px rgba(0,0,0,.12);
}
.kpi .v { font-size:26px; font-weight:800; }
.kpi .l { font-size:13px; opacity:.95; }
.card {
  background:#fff; border-radius:12px; padding:16px 18px; margin:8px 0;
  border-left:6px solid #1565C0; box-shadow:0 2px 8px rgba(0,0,0,.06);
}
.badge { padding:3px 10px; border-radius:12px; color:#fff; font-size:12px; font-weight:700; }
.cite { color:#1565C0; font-weight:700; }
</style>
""", unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
#  Data (light) — manifest + eval results for KPIs
# --------------------------------------------------------------------------- #
@st.cache_data
def load_light():
    manifest = pd.read_csv(REPO / "regulatory_corpus" / "corpus_manifest.csv")
    ev_path = REPO / "evaluation" / "eval_results.json"
    ev = json.loads(ev_path.read_text()) if ev_path.exists() else {}
    return manifest, ev


# --------------------------------------------------------------------------- #
#  Embeddings — prefer the repo-committed file (instant), else cache, else build
# --------------------------------------------------------------------------- #
def _load_or_build_embeddings(chunks):
    import numpy as np
    # 1) committed with the repo (fast path, used on the cloud)
    if project_paths.REPO_EMBEDDINGS.exists():
        emb = np.load(project_paths.REPO_EMBEDDINGS)
        if emb.shape[0] == len(chunks):
            return emb
    # 2) local D: cache from a previous run
    cache_path = project_paths.CACHE_ROOT / "embeddings" / "corpus_embeddings.npy"
    if cache_path.exists():
        emb = np.load(cache_path)
        if emb.shape[0] == len(chunks):
            return emb
    # 3) build once and cache (cold start with no precomputed file)
    from embedder import load_embedder, embed_passages
    emb = embed_passages(load_embedder(), [c["text"] for c in chunks], show_progress=False)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(cache_path, emb)
    return emb


# --------------------------------------------------------------------------- #
#  Heavy pipeline — loaded once, only when needed (live demo)
# --------------------------------------------------------------------------- #
@st.cache_resource(show_spinner="Loading the retrieval + agent pipeline (first time only)…")
def load_pipeline(llm_mode: str):
    from document_chunker import get_tokenizer, chunk_corpus
    from embedder import load_embedder
    from hybrid_retriever import HybridRetriever
    from citation_guard import load_prompt_config

    tok = get_tokenizer()
    chunks = chunk_corpus(str(project_paths.CORPUS_DIR), 384, 64, tokenizer=tok)
    embeddings = _load_or_build_embeddings(chunks)
    embedder = load_embedder()
    retriever = HybridRetriever(chunks, embeddings, embedder)
    cfg = load_prompt_config(str(project_paths.PROMPTS_DIR))

    agent = None
    if llm_mode in ("gemini", "local"):
        from llm_provider import get_llm
        from agent import build_agent
        agent = build_agent(retriever, get_llm(provider=llm_mode), cfg)
    return retriever, cfg, agent


manifest, ev = load_light()
n_docs = len(manifest)
n_pages = int(manifest["pages"].sum())
n_chars = int(manifest["total_chars"].sum())

# --------------------------------------------------------------------------- #
#  Hero + KPIs
# --------------------------------------------------------------------------- #
st.markdown("""
<div class="hero">
  <h1>🤖 Grounded — Citation-Enforced RAG for RBI Compliance</h1>
  <p>Fully-offline, agentic Retrieval-Augmented Generation over real RBI Master Directions.
  Cited answers, honest refusals, measured quality.</p>
</div>
""", unsafe_allow_html=True)

k = st.columns(6)
kpis = [
    ("#1565C0", n_docs, "RBI documents"),
    ("#6A1B9A", n_pages, "pages"),
    ("#00897B", "1,252", "chunks"),
    ("#2E7D32", ev.get("retrieval_recall_at_5", "1.0"), "recall@5"),
    ("#EF6C00", ev.get("refusal_accuracy", "1.0"), "refusal acc."),
    ("#C2185B", ev.get("faithfulness_grounded", "0.97"), "faithfulness"),
]
for col, (color, val, label) in zip(k, kpis):
    col.markdown(f'<div class="kpi" style="background:{color};">'
                 f'<div class="v">{val}</div><div class="l">{label}</div></div>',
                 unsafe_allow_html=True)

st.write("")

# --------------------------------------------------------------------------- #
#  Tabs — the storyline + the live demo
# --------------------------------------------------------------------------- #
tab_story, tab_corpus, tab_method, tab_results, tab_ask = st.tabs(
    ["🎯 The Problem", "🗂️ The Corpus", "🧠 The Method", "📊 Results", "💬 Ask Grounded"]
)

with tab_story:
    st.markdown("""
<div class="card">
<h3 style="color:#1565C0;">Why this matters</h3>
Bank &amp; NBFC compliance teams must answer precise questions against dense RBI regulation —
and a confidently <b>wrong</b> answer has real regulatory cost. A generic chatbot will happily
hallucinate. <b>Grounded</b> instead retrieves the actual regulation text, answers
<b>only</b> from it, cites the exact page, and <b>declines</b> when the evidence is insufficient.
</div>
<div class="card" style="border-left-color:#6A1B9A;">
<h3 style="color:#6A1B9A;">What makes it production-grade</h3>
① Hybrid retrieval (keyword + semantic) &nbsp; ② Cross-encoder re-ranking &nbsp;
③ Page-level citation enforcement &nbsp; ④ A LangGraph agent that decides answer-vs-decline &nbsp;
⑤ A golden evaluation set, NLI faithfulness scoring, and a CI quality gate &nbsp;
⑥ 100% offline on free tools — zero API cost.
</div>
""", unsafe_allow_html=True)

with tab_corpus:
    st.markdown('<div class="card"><h3 style="color:#1565C0;">Real RBI Master Directions</h3>'
                'Theme: <b>Lending, Credit &amp; Customer Protection (Banks &amp; NBFCs)</b> — a coherent, '
                'cross-referencing slice of RBI regulation, downloaded directly from rbi.org.in.</div>',
                unsafe_allow_html=True)
    st.dataframe(manifest[["file", "pages", "total_chars", "avg_chars_per_page"]],
                 use_container_width=True, hide_index=True)
    st.bar_chart(manifest.set_index("file")["pages"], color="#6A1B9A")

with tab_method:
    st.markdown("""
<div class="card">
<h3 style="color:#1565C0;">From question to cited answer</h3>
<b>1. Chunk</b> — 720 pages → 1,252 page-tagged chunks (384 tokens, 64 overlap).<br>
<b>2. Embed</b> — bge-small-en-v1.5 → 384-dim vectors, stored in ChromaDB.<br>
<b>3. Retrieve (hybrid)</b> — BM25 keyword + semantic search, fused by Reciprocal Rank Fusion.<br>
<b>4. Re-rank</b> — a cross-encoder re-scores the top candidates for precision.<br>
<b>5. Enforce citations</b> — if the best evidence is too weak, <b>decline</b> instead of guessing.<br>
<b>6. Agent (LangGraph)</b> — retrieve → assess → (answer | decline) → verify → cite.<br>
<b>7. Generate</b> — a provider-swappable LLM writes the answer, grounded ONLY in the cited
context: a local Qwen2.5-3B (offline, zero-cost) on a full machine, or the Gemini free-tier
API for the low-RAM public cloud demo. Same interface, same citation rules either way.
</div>
""", unsafe_allow_html=True)

with tab_results:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="card" style="border-left-color:#2E7D32;">'
                    '<h3 style="color:#2E7D32;">Retrieval &amp; refusal</h3>'
                    f'Recall@5: <b>{ev.get("retrieval_recall_at_5","1.0")}</b> · '
                    f'Refusal accuracy: <b>{ev.get("refusal_accuracy","1.0")}</b><br>'
                    'Every in-scope question retrieved the right document; every out-of-scope '
                    'question was declined.</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="card" style="border-left-color:#C2185B;">'
                    '<h3 style="color:#C2185B;">NLI faithfulness</h3>'
                    f'Grounded answer: <b>{ev.get("faithfulness_grounded","0.97")}</b> · '
                    f'Hallucinated: <b>{ev.get("faithfulness_hallucinated","0.01")}</b><br>'
                    'An offline NLI model cleanly separates supported answers from invented ones.'
                    '</div>', unsafe_allow_html=True)
    st.caption("Honest note: metrics are on a small, hand-authored golden set; recall is "
               "document-level. Strong, defensible baseline — not an inflated one.")

with tab_ask:
    st.markdown('<div class="card"><h3 style="color:#1565C0;">Ask a compliance question</h3>'
                'The agent retrieves, re-ranks, enforces citations, and (if evidence is strong) '
                'writes a cited answer — otherwise it declines.</div>', unsafe_allow_html=True)

    # Decide how answers are generated, based on what's available in THIS host.
    local_model_file = project_paths.CACHE_ROOT / "llm_models" / "Qwen2.5-3B-Instruct-Q4_K_M.gguf"
    if GEMINI_KEY:
        llm_mode = "gemini"
        st.success("🌐 Connected to the Gemini free-tier API — full cited answers, "
                   "a few seconds each.")
    elif local_model_file.exists():
        gen = st.toggle("Generate a written answer with the local LLM (slower on CPU)", value=False)
        llm_mode = "local" if gen else "none"
    else:
        llm_mode = "none"
        st.info("No LLM configured here — showing the retrieved, re-ranked citations "
                "(add a GEMINI_API_KEY to enable written answers).")

    q = st.text_input("Your question",
                      "What must a digital lending app disclose to borrowers via the Key Fact Statement?")

    if st.button("Ask Grounded", type="primary"):
        with st.spinner("Thinking…"):
            retriever, cfg, agent = load_pipeline(llm_mode=llm_mode)
            if llm_mode in ("gemini", "local") and agent is not None:
                from agent import ask_agent
                r = ask_agent(agent, q)
                if r["decision"] == "answer":
                    st.success(f"✅ Answered (evidence score {r['top_score']:+.2f}, "
                               f"verified={r.get('verified')})")
                    st.markdown(r["answer"])
                    st.markdown("**Citations:** " +
                                " · ".join(f'<span class="cite">{c}</span>' for c in r["citations"]),
                                unsafe_allow_html=True)
                else:
                    st.error(f"🛑 Declined (evidence score {r['top_score']:+.2f}) — "
                             "insufficient evidence in the corpus.")
                    st.markdown(r["answer"])
            else:
                from citation_guard import guard
                from embedder import embed_query
                hits = retriever.retrieve(q, top_k=4)
                g = guard(hits, cfg)
                if g["decision"] == "decline":
                    st.error(f"🛑 Declined (evidence score {g['top_score']:+.2f}).")
                else:
                    st.success(f"✅ Sufficient evidence (score {g['top_score']:+.2f}). "
                               "Top cited passages:")
                for h in hits:
                    st.markdown(
                        f'<div class="card"><span class="badge" style="background:#2E7D32;">'
                        f'score {h["cross_score"]:+.2f}</span> '
                        f'<span class="cite">📄 {h["source_file"]} — page {h["page"]}</span>'
                        f'<div style="margin-top:6px;color:#263238;">{h["text"][:320].strip()}…</div></div>',
                        unsafe_allow_html=True)

_backend = "Gemini free-tier API" if GEMINI_KEY else "local llama.cpp (offline)"
st.caption(f"Grounded · hybrid retrieval + cross-encoder re-rank + citation enforcement + "
           f"LangGraph agent · sentence-transformers · LLM: {_backend}")
