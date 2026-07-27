"""
llm_provider.py
===============
A thin, provider-SWAPPABLE wrapper around the language model that writes answers.

Why swappable: the brief requires no hard-coded provider. The default is a fully
LOCAL, offline model (llama.cpp running a quantized GGUF on CPU) at zero API cost.
The same `LLM.chat(system, user)` interface could later be backed by Gemini or
Groq without touching the rest of the pipeline — only this file changes.

Default model: Qwen2.5-3B-Instruct (Q4_K_M) — a small, capable instruction model
that runs on CPU. Answers are short (a cited compliance answer), so CPU latency
of tens of seconds is acceptable; generation is a "run-it-yourself" long job.
"""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_MODEL_PATH = str(
    Path(r"D:\grounded_rag_cache\llm_models\Qwen2.5-3B-Instruct-Q4_K_M.gguf")
)


class LocalLLM:
    """Local llama.cpp-backed provider. Loaded once, reused for every answer."""

    def __init__(self, model_path: str = DEFAULT_MODEL_PATH, n_ctx: int = 4096):
        from llama_cpp import Llama  # imported lazily so the module is light

        self.model_path = model_path
        self.llm = Llama(
            model_path=model_path,
            n_ctx=n_ctx,                       # context window (fits our prompt + answer)
            n_threads=max(1, (os.cpu_count() or 4) - 1),
            verbose=False,
        )

    def chat(self, system: str, user: str,
             max_tokens: int = 512, temperature: float = 0.1) -> str:
        """
        Low temperature (0.1) keeps answers factual and near-deterministic — we do
        NOT want a compliance assistant being 'creative'.
        """
        out = self.llm.create_chat_completion(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return out["choices"][0]["message"]["content"].strip()


def get_llm(provider: str = "local", **kwargs):
    """Factory. Only 'local' is wired now; the seam for other providers exists."""
    if provider == "local":
        return LocalLLM(**kwargs)
    raise ValueError(f"Unknown provider '{provider}'. Only 'local' is configured.")


if __name__ == "__main__":
    llm = get_llm()
    print("Model loaded. Generating a short test answer...\n")
    ans = llm.chat(
        system="You are a concise assistant. Answer in one sentence.",
        user="In one sentence, what is the purpose of a KYC process in banking?",
        max_tokens=80,
    )
    print("ANSWER:", ans)
