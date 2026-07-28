"""
Grounded — Hugging Face Spaces app
==================================
Public, free, fully-offline live demo: ask a compliance question, get a cited
answer over real RBI Master Directions — or an honest refusal.

Runs the SAME local stack as the reference project (retrieval + hybrid + re-rank
+ citation enforcement + local Qwen LLM). No API key, zero API cost. HF's free
CPU tier (16 GB RAM) fits the whole thing; generation takes ~30–60s on CPU.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import streamlit as st

# --- writable cache on the Space (models, HF hub) --------------------------
HERE = Path(__file__).resolve().parent
os.environ.setdefault("GROUNDED_CACHE_ROOT", str(HERE / ".cache"))
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
sys.path.append(str(HERE / "config"))
sys.path.append(str(HERE / "src"))

import project_paths
project_paths.apply_env()

st.set_page_config(page_title="Grounded — RBI Compliance RAG", page_icon="🤖", layout="wide")

st.markdown("""
<style>
.stApp { background:linear-gradient(180deg,#f6f8ff 0%,#fdf6ff 100%); }
.hero { background:linear-gradient(135deg,#1565C0 0%,#6A1B9A 100%); color:#fff;
        padding:26px 30px; border-radius:18px; box-shadow:0 8px 24px rgba(106,27,154,.35); }
.hero h1 { color:#fff; margin:0; font-size:27px; } .hero p { color:#E3F2FD; margin:8px 0 0; }
.kpi { border-radius:14px; padding:14px; color:#fff; text-align:center; box-shadow:0 4px 12px rgba(0,0,0,.12); }
.kpi .v { font-size:22px; font-weight:800; } .kpi .l { font-size:12px; }
.card { background:#fff; border-radius:12px; padding:14px 16px; margin:8px 0;
        border-left:6px solid #1565C0; box-shadow:0 2px 8px rgba(0,0,0,.06); }
.cite { color:#1565C0; font-weight:700; } .badge { padding:3px 10px; border-radius:12px; color:#fff; font-size:12px; font-weight:700; }
</style>
""", unsafe_allow_html=True)

MODEL_REPO = "bartowski/Qwen2.5-3B-Instruct-GGUF"
MODEL_FILE = "Qwen2.5-3B-Instruct-Q4_K_M.gguf"


@st.cache_resource(show_spinner="Downloading the local LLM (first launch only, ~1.9 GB)…")
def get_model_path() -> str:
    from huggingface_hub import hf_hub_download
    dest = project_paths.CACHE_ROOT / "llm_models"
    dest.mkdir(parents=True, exist_ok=True)
    return hf_hub_download(repo_id=MODEL_REPO, filename=MODEL_FILE, local_dir=str(dest))


@st.cache_resource(show_spinner="Loading corpus, embeddings, retriever, agent…")
def load_pipeline():
    from document_chunker import get_tokenizer, chunk_corpus
    from embedder import load_embedder
    from hybrid_retriever import HybridRetriever
    from citation_guard import load_prompt_config
    from llm_provider import get_llm
    from agent import build_agent

    tok = get_tokenizer()
    chunks = chunk_corpus(str(HERE / "regulatory_corpus"), 384, 64, tokenizer=tok)
    embeddings = np.load(str(HERE / "corpus_embeddings.npy"))
    retriever = HybridRetriever(chunks, embeddings, load_embedder())
    cfg = load_prompt_config(str(HERE / "prompts"))
    agent = build_agent(retriever, get_llm(model_path=get_model_path()), cfg)
    return retriever, cfg, agent


st.markdown("""
<div class="hero"><h1>🤖 Grounded — Citation-Enforced RAG for RBI Compliance</h1>
<p>Ask a banking-compliance question over real RBI Master Directions. You'll get a
page-cited answer — or an honest refusal when the evidence isn't there. 100% offline, zero API cost.</p></div>
""", unsafe_allow_html=True)

cols = st.columns(5)
for c, (color, v, l) in zip(cols, [
    ("#1565C0", "10", "RBI documents"), ("#6A1B9A", "720", "pages"),
    ("#00897B", "1,252", "chunks"), ("#2E7D32", "1.0", "recall@5"),
    ("#C2185B", "0.97", "faithfulness")]):
    c.markdown(f'<div class="kpi" style="background:{color}"><div class="v">{v}</div>'
               f'<div class="l">{l}</div></div>', unsafe_allow_html=True)

st.info("⏳ This runs a real language model on a free shared CPU — an answer takes about "
        "**30–60 seconds**. That's the honest cost of a fully-offline, zero-API demo.")

st.markdown("### 💬 Ask a compliance question")
examples = [
    "What must a digital lending app disclose to borrowers via the Key Fact Statement?",
    "What is the beneficial owner threshold for a trust under KYC rules?",
    "Can a card issuer send an unsolicited credit card to a customer?",
]
q = st.text_input("Your question", examples[0])
st.caption("Try: " + " · ".join(f"“{e}”" for e in examples[1:]))

if st.button("Ask Grounded", type="primary"):
    with st.spinner("Retrieving, re-ranking, and (if evidence is strong) writing a cited answer…"):
        from agent import ask_agent
        _, _, agent = load_pipeline()
        r = ask_agent(agent, q)
    if r["decision"] == "answer":
        st.success(f"✅ Answered — evidence score {r['top_score']:+.2f}, verified={r.get('verified')}")
        st.markdown(r["answer"])
        st.markdown("**Citations:** " +
                    " · ".join(f'<span class="cite">{c}</span>' for c in r["citations"]),
                    unsafe_allow_html=True)
    else:
        st.error(f"🛑 Declined — evidence score {r['top_score']:+.2f} (below threshold). "
                 "The corpus doesn't support a reliable answer.")
        st.markdown(r["answer"])

st.caption("Grounded · hybrid retrieval + cross-encoder re-ranking + citation enforcement + "
           "LangGraph agent + local Qwen2.5-3B · fully offline · zero API cost")
