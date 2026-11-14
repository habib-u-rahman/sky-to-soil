"""LangGraph pipeline for the AI Agronomist.

collect_facts -> retrieve -> write -> verify -> (rewrite once if verify
fails) -> fallback_template if still failing -> END.

Two modes share this graph: "explain" (POST /advisor/explain) and "chat"
(POST /advisor/chat) -- they differ only in which prompt builder `write`
uses and which output field ("farmer_text"/"technical_note" vs "answer")
gets checked.
"""

from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from app.advisor import fallback_template, prompts
from app.advisor.facts import assemble_facts
from app.advisor.groq_client import complete_json
from app.advisor.kb import build_retrieval_query, retrieve
from app.advisor.verify import verify_output

MAX_REWRITES = 1


class AdvisorState(TypedDict, total=False):
    mode: str  # "explain" | "chat"
    bundle: dict
    question: str | None
    language: str
    current_crops: list[str]

    facts: dict
    kb: list[dict]

    farmer_text: str
    technical_note: str
    answer: str
    answerable: bool

    model_used: str
    rewrites_used: int
    used_fallback: bool
    verified: bool
    issues: list[str]
    first_attempt_verified: bool


def _node_collect_facts(state: AdvisorState) -> dict:
    facts = assemble_facts(state["bundle"])
    return {"facts": facts}


def _node_retrieve(state: AdvisorState) -> dict:
    query = build_retrieval_query(state["facts"], state.get("question"))
    kb_entries = retrieve(query, top_k=6)
    return {"kb": kb_entries}


async def _node_write(state: AdvisorState) -> dict:
    facts, kb, language, current_crops = state["facts"], state["kb"], state["language"], state["current_crops"]
    issues = state.get("issues")

    if state["mode"] == "explain":
        if issues:
            messages = prompts.build_explain_rewrite_messages(facts, kb, current_crops, language, issues)
        else:
            messages = prompts.build_explain_messages(facts, kb, current_crops, language)
        try:
            parsed, model_used = await complete_json(messages)
        except Exception:  # noqa: BLE001 - a total Groq outage should degrade to fallback_template, not 500 the request
            return {"farmer_text": "", "technical_note": "", "model_used": "groq_error"}
        return {
            "farmer_text": str(parsed.get("farmer_text", "")),
            "technical_note": str(parsed.get("technical_note", "")),
            "model_used": model_used,
        }

    question = state["question"] or ""
    if issues:
        messages = prompts.build_chat_rewrite_messages(facts, kb, current_crops, language, question, issues)
    else:
        messages = prompts.build_chat_messages(facts, kb, current_crops, language, question)
    try:
        parsed, model_used = await complete_json(messages)
    except Exception:  # noqa: BLE001 - see above
        return {"answer": "", "answerable": False, "model_used": "groq_error"}
    return {
        "answer": str(parsed.get("answer", "")),
        "answerable": bool(parsed.get("answerable", True)),
        "model_used": model_used,
    }


def _node_verify(state: AdvisorState) -> dict:
    if state["mode"] == "explain":
        result = verify_output(state["farmer_text"], state["technical_note"], state["facts"], state["kb"])
    else:
        result = verify_output(state["answer"], "", state["facts"], state["kb"])
    update = {"verified": result["verified"], "issues": result["issues"]}
    # Recorded once, on the very first verify() call for this request, so
    # eval tooling can report "passed before any rewrite" vs. the final
    # (post-rewrite/fallback) pass rate separately.
    if "first_attempt_verified" not in state:
        update["first_attempt_verified"] = result["verified"]
    return update


def _node_fallback_template(state: AdvisorState) -> dict:
    facts, language, current_crops = state["facts"], state["language"], state["current_crops"]

    if state["mode"] == "explain":
        farmer_text, technical_note, kb_used = fallback_template.build_fallback_explain(facts, current_crops, language)
        return {
            "farmer_text": farmer_text,
            "technical_note": technical_note,
            "kb": kb_used,
            "model_used": "fallback_template",
            "used_fallback": True,
        }

    answer, answerable, kb_used = fallback_template.build_fallback_chat(facts, state.get("question") or "", language)
    return {
        "answer": answer,
        "answerable": answerable,
        "kb": kb_used,
        "model_used": "fallback_template",
        "used_fallback": True,
    }


def _route_after_verify(state: AdvisorState) -> str:
    if state.get("verified") or state.get("used_fallback"):
        return "end"
    if state.get("rewrites_used", 0) < MAX_REWRITES:
        return "write"
    return "fallback_template"


def _increment_rewrites(state: AdvisorState) -> dict:
    return {"rewrites_used": state.get("rewrites_used", 0) + 1}


def build_graph():
    graph = StateGraph(AdvisorState)
    graph.add_node("collect_facts", _node_collect_facts)
    graph.add_node("retrieve", _node_retrieve)
    graph.add_node("write", _node_write)
    graph.add_node("verify", _node_verify)
    graph.add_node("count_rewrite", _increment_rewrites)
    graph.add_node("fallback_template", _node_fallback_template)

    graph.set_entry_point("collect_facts")
    graph.add_edge("collect_facts", "retrieve")
    graph.add_edge("retrieve", "write")
    graph.add_edge("write", "verify")
    graph.add_conditional_edges(
        "verify", _route_after_verify, {"write": "count_rewrite", "fallback_template": "fallback_template", "end": END}
    )
    graph.add_edge("count_rewrite", "write")
    # Re-verify after the fallback too (not a straight edge to END): the
    # final verified/issues fields must describe the text actually being
    # returned, not whatever the last failed LLM attempt left behind.
    # _route_after_verify's `used_fallback` check guarantees this terminates.
    graph.add_edge("fallback_template", "verify")

    return graph.compile()


_COMPILED_GRAPH = None


def get_graph():
    global _COMPILED_GRAPH
    if _COMPILED_GRAPH is None:
        _COMPILED_GRAPH = build_graph()
    return _COMPILED_GRAPH


async def run_explain(bundle: dict, current_crops: list[str], language: str) -> dict:
    graph = get_graph()
    result: dict[str, Any] = await graph.ainvoke(
        {"mode": "explain", "bundle": bundle, "current_crops": current_crops, "language": language, "rewrites_used": 0}
    )
    return result


async def run_chat(bundle: dict, current_crops: list[str], language: str, question: str) -> dict:
    graph = get_graph()
    result: dict[str, Any] = await graph.ainvoke(
        {
            "mode": "chat",
            "bundle": bundle,
            "current_crops": current_crops,
            "language": language,
            "question": question,
            "rewrites_used": 0,
        }
    )
    return result
