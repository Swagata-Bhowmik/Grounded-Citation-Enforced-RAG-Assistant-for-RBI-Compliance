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

Two providers are wired:
  * "local"  — llama.cpp + Qwen GGUF, fully offline, zero cost (the default).
  * "gemini" — Google Gemini via the free API tier, used for the public cloud
               demo where a multi-GB local model won't fit the free hosting RAM.
Both expose the SAME `chat(system, user)` interface, so nothing else changes.
"""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_MODEL_PATH = os.environ.get(
    "GROUNDED_LLM_PATH",
    str(Path(r"D:\grounded_rag_cache\llm_models\Qwen2.5-3B-Instruct-Q4_K_M.gguf")),
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


class GeminiLLM:
    """
    Google Gemini provider (free API tier). Used for the public cloud demo.

    Reads the API key from the arg or the GEMINI_API_KEY / GOOGLE_API_KEY env var
    (Streamlit Community Cloud injects secrets as env vars). The key is NEVER
    hard-coded or committed. Model is overridable via the GEMINI_MODEL env var.
    """

    # A stable alias that always points to a current Gemini Flash model, so this
    # never breaks when a specific dated version is retired. Overridable via env.
    DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-flash-latest")

    def __init__(self, api_key: str | None = None, model: str | None = None):
        from google import genai  # imported lazily so the module stays light

        api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError(
                "No Gemini API key found. Set GEMINI_API_KEY (env or Streamlit secret)."
            )
        self.client = genai.Client(api_key=api_key)
        self.model = model or self.DEFAULT_MODEL

    def chat(self, system: str, user: str,
             max_tokens: int = 2048, temperature: float = 0.1) -> str:
        """
        Low temperature (0.1) keeps answers factual — a compliance assistant must
        not be 'creative'.

        A generous max_output_tokens is used because current Gemini Flash models
        may spend some of the budget on internal "thinking" tokens before the
        visible answer; too small a cap can yield an empty response. We try to
        minimise that thinking with a config hint, but fall back gracefully for
        model generations that don't accept the hint (they use a different knob).
        """
        from google.genai import types

        base = dict(
            system_instruction=system,
            temperature=temperature,
            max_output_tokens=max_tokens,
        )

        def _call(cfg_kwargs):
            return self.client.models.generate_content(
                model=self.model, contents=user,
                config=types.GenerateContentConfig(**cfg_kwargs),
            )

        # Best effort: hint low thinking; if the model rejects that argument
        # (newer generations use a different knob), retry without it.
        try:
            hinted = dict(base, thinking_config=types.ThinkingConfig(thinking_budget=0))
            resp = _call(hinted)
        except Exception:
            resp = _call(base)

        return (resp.text or "").strip()


def get_llm(provider: str | None = None, **kwargs):
    """
    Factory. Chooses the provider explicitly, or via the GROUNDED_LLM_PROVIDER env
    var, or auto-detects: if a Gemini API key is present use 'gemini', else 'local'.
    """
    if provider is None:
        provider = os.environ.get("GROUNDED_LLM_PROVIDER")
    if provider is None:
        provider = ("gemini"
                    if (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))
                    else "local")

    if provider == "local":
        return LocalLLM(**kwargs)
    if provider == "gemini":
        gk = {k: v for k, v in kwargs.items() if k in ("api_key", "model")}
        return GeminiLLM(**gk)
    raise ValueError(f"Unknown provider '{provider}'. Use 'local' or 'gemini'.")


if __name__ == "__main__":
    llm = get_llm()
    print("Model loaded. Generating a short test answer...\n")
    ans = llm.chat(
        system="You are a concise assistant. Answer in one sentence.",
        user="In one sentence, what is the purpose of a KYC process in banking?",
        max_tokens=80,
    )
    print("ANSWER:", ans)
