from fastapi import APIRouter, HTTPException, Query

from app.advisor import facts as advisor_facts
from app.advisor import fallback_template
from app.advisor.graph import run_chat, run_explain
from app.advisor.verify import verify_output
from app.core.demo import load_demo_analysis
from app.schemas import (
    AdvisorChatRequest,
    AdvisorChatResponse,
    AdvisorExplainRequest,
    AdvisorExplainResponse,
)

router = APIRouter()


def _resolve_analysis(body_analysis, demo: bool) -> tuple[dict, bool]:
    if demo:
        demo_data = load_demo_analysis()
        if not demo_data:
            raise HTTPException(status_code=503, detail="Demo data not built yet. Run: python -m app.scripts.build_demo")
        return demo_data, True
    if body_analysis is None:
        raise HTTPException(status_code=422, detail="'analysis' is required in the request body unless demo=true")
    return body_analysis.model_dump(), False


async def _live_bundle(analysis_dict: dict, current_crops: list[str], rotation_id: str) -> dict:
    lat, lon = analysis_dict["location"]["lat"], analysis_dict["location"]["lon"]
    try:
        rotation_entry = advisor_facts.find_rotation_entry(analysis_dict["rotations"], rotation_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    stress_entry = advisor_facts.find_stress_entry(analysis_dict.get("stress_test"), rotation_entry["rotation"])
    return await advisor_facts.build_bundle_live(lat, lon, current_crops, rotation_entry, stress_entry)


def _demo_bundle(analysis_dict: dict, current_crops: list[str], rotation_id: str) -> dict:
    try:
        return advisor_facts.resolve_from_demo(analysis_dict, rotation_id, current_crops)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/advisor/explain", response_model=AdvisorExplainResponse)
async def post_advisor_explain(body: AdvisorExplainRequest, demo: bool = Query(False)):
    analysis_dict, is_demo = _resolve_analysis(body.analysis, demo)

    if is_demo:
        cached = (analysis_dict.get("advisor_explain") or {}).get(body.rotation_id, {}).get(body.language)
        if cached:
            return cached

        bundle = _demo_bundle(analysis_dict, body.current_crops, body.rotation_id)
        facts = advisor_facts.assemble_facts(bundle)
        farmer_text, technical_note, kb_used = fallback_template.build_fallback_explain(
            facts, body.current_crops, body.language
        )
        check = verify_output(farmer_text, technical_note, facts, kb_used)
        return AdvisorExplainResponse(
            text=farmer_text,
            technical_note=technical_note,
            language=body.language,
            verified=check["verified"],
            issues=check["issues"],
            rewrites_used=0,
            facts_used=facts,
            kb_sources=sorted({e["source"] for e in kb_used}),
            model_used="fallback_template",
        )

    bundle = await _live_bundle(analysis_dict, body.current_crops, body.rotation_id)
    result = await run_explain(bundle, body.current_crops, body.language)
    return AdvisorExplainResponse(
        text=result.get("farmer_text", ""),
        technical_note=result.get("technical_note", ""),
        language=body.language,
        verified=result.get("verified", False),
        issues=result.get("issues", []),
        rewrites_used=result.get("rewrites_used", 0),
        facts_used=result["facts"],
        kb_sources=sorted({e["source"] for e in result.get("kb", [])}),
        model_used=result.get("model_used", "fallback_template"),
    )


@router.post("/advisor/chat", response_model=AdvisorChatResponse)
async def post_advisor_chat(body: AdvisorChatRequest, demo: bool = Query(False)):
    analysis_dict, is_demo = _resolve_analysis(body.analysis, demo)
    rotation_id = body.rotation_id or "top_0"

    if is_demo:
        if rotation_id == "top_0":
            cached_list = (analysis_dict.get("advisor_chat") or {}).get(body.language, [])
            normalized_q = body.question.strip().lower()
            for item in cached_list:
                if item["question"].strip().lower() == normalized_q:
                    return item["response"]

        bundle = _demo_bundle(analysis_dict, body.current_crops, rotation_id)
        facts = advisor_facts.assemble_facts(bundle)
        answer, answerable, kb_used = fallback_template.build_fallback_chat(facts, body.question, body.language)
        check = verify_output(answer, "", facts, kb_used)
        return AdvisorChatResponse(
            answer=answer,
            language=body.language,
            verified=check["verified"],
            issues=check["issues"],
            answerable=answerable,
            rewrites_used=0,
            facts_used=facts,
            kb_sources=sorted({e["source"] for e in kb_used}),
            model_used="fallback_template",
        )

    bundle = await _live_bundle(analysis_dict, body.current_crops, rotation_id)
    result = await run_chat(bundle, body.current_crops, body.language, body.question)
    return AdvisorChatResponse(
        answer=result.get("answer", ""),
        language=body.language,
        verified=result.get("verified", False),
        issues=result.get("issues", []),
        answerable=result.get("answerable", False),
        rewrites_used=result.get("rewrites_used", 0),
        facts_used=result["facts"],
        kb_sources=sorted({e["source"] for e in result.get("kb", [])}),
        model_used=result.get("model_used", "fallback_template"),
    )
