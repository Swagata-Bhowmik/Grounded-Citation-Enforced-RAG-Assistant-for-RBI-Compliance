"""
agent.py
========
The Phase-3 AGENT: a LangGraph state machine that turns retrieval + enforcement +
generation into a decision-making flow, rather than one fixed straight line.

THE GRAPH
---------
    START -> retrieve -> assess --(answerable?)--> generate -> verify -> END
                              \--(no)-------------> decline -----------> END

  * retrieve : hybrid (BM25 + semantic) candidates, cross-encoder re-ranked
  * assess   : citation-enforcement gate — is the top evidence strong enough?
  * generate : local LLM writes an answer grounded ONLY in the cited context
  * verify   : confirm the answer actually contains page citations
  * decline  : return the standard refusal (no hallucination)

Why an agent and not a function? The conditional edge (answer vs decline) IS the
agentic decision. The graph structure also makes it trivial to add more tools or
steps later (e.g., a query-rewrite node) without rewriting the control flow.
"""

from __future__ import annotations

import re
from typing import TypedDict, Optional

from langgraph.graph import StateGraph, START, END

from citation_guard import guard

_CITATION_RE = re.compile(r"\[[^\]]+p\.\d+\]")


class AgentState(TypedDict, total=False):
    query: str
    hits: list
    decision: str
    top_score: float
    context: str
    citations: list
    answer: str
    verified: bool


def build_agent(retriever, llm, cfg, top_k: int = 3):
    """Compile a LangGraph agent that closes over the retriever, LLM, and config."""

    def retrieve_node(state: AgentState) -> AgentState:
        hits = retriever.retrieve(state["query"], top_k=top_k)
        return {"hits": hits}

    def assess_node(state: AgentState) -> AgentState:
        g = guard(state["hits"], cfg)
        out: AgentState = {"decision": g["decision"], "top_score": g["top_score"]}
        if g["decision"] == "answer":
            out["context"] = g["context"]
            out["citations"] = g["citations"]
        return out

    def route(state: AgentState) -> str:
        return "generate" if state["decision"] == "answer" else "decline"

    def generate_node(state: AgentState) -> AgentState:
        user_prompt = cfg["answer_template"].format(
            context=state["context"], question=state["query"]
        )
        answer = llm.chat(cfg["system_prompt"], user_prompt)
        return {"answer": answer}

    def verify_node(state: AgentState) -> AgentState:
        # Confirm the model actually cited pages (grounding check).
        return {"verified": bool(_CITATION_RE.search(state.get("answer", "")))}

    def decline_node(state: AgentState) -> AgentState:
        return {"answer": cfg["refusal_message"].strip(),
                "citations": [], "verified": False}

    g = StateGraph(AgentState)
    g.add_node("retrieve", retrieve_node)
    g.add_node("assess", assess_node)
    g.add_node("generate", generate_node)
    g.add_node("verify", verify_node)
    g.add_node("decline", decline_node)

    g.add_edge(START, "retrieve")
    g.add_edge("retrieve", "assess")
    g.add_conditional_edges("assess", route, {"generate": "generate", "decline": "decline"})
    g.add_edge("generate", "verify")
    g.add_edge("verify", END)
    g.add_edge("decline", END)
    return g.compile()


def ask_agent(agent, query: str) -> dict:
    """Run the agent on a query and return the final state as a plain dict."""
    return dict(agent.invoke({"query": query}))
