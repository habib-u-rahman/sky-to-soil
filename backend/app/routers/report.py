from fastapi import APIRouter, HTTPException, Query, Response

from app.advisor import facts as advisor_facts
from app.advisor import fallback_template
from app.advisor.graph import run_explain
from app.core.demo import load_demo_analysis
from app.report.pdf_builder import build_pdf_bytes
from app.schemas import ReportPdfRequest

router = APIRouter()


@router.post("/report/pdf")
async def post_report_pdf(body: ReportPdfRequest, demo: bool = Query(False)):
    if demo:
        analysis = load_demo_analysis()
        if not analysis:
            raise HTTPException(status_code=503, detail="Demo data not built yet. Run: python -m app.scripts.build_demo")

        cached = (analysis.get("advisor_explain") or {}).get("top_0", {}).get("en")
        if cached:
            advisor_text, technical_note, kb_sources = cached["text"], cached["technical_note"], cached["kb_sources"]
        else:
            bundle = advisor_facts.resolve_from_demo(analysis, "top_0", body.current_crops)
            facts = advisor_facts.assemble_facts(bundle)
            advisor_text, technical_note, kb_used = fallback_template.build_fallback_explain(facts, body.current_crops, "en")
            kb_sources = sorted({e["source"] for e in kb_used})
    else:
        analysis = body.analysis.model_dump() if body.analysis else None
        if analysis is None:
            raise HTTPException(status_code=422, detail="'analysis' is required in the request body unless demo=true")

        try:
            rotation_entry = advisor_facts.find_rotation_entry(analysis["rotations"], "top_0")
        except (ValueError, KeyError) as exc:
            raise HTTPException(status_code=422, detail=f"analysis has no scored rotations to report on: {exc}") from exc
        stress_entry = advisor_facts.find_stress_entry(analysis.get("stress_test"), rotation_entry["rotation"])
        bundle = await advisor_facts.build_bundle_live(
            analysis["location"]["lat"], analysis["location"]["lon"], body.current_crops, rotation_entry, stress_entry
        )
        result = await run_explain(bundle, body.current_crops, "en")
        advisor_text = result.get("farmer_text", "")
        technical_note = result.get("technical_note", "")
        kb_sources = sorted({e["source"] for e in result.get("kb", [])})

    pdf_bytes = build_pdf_bytes(analysis, body.current_crops, body.top_n, advisor_text, technical_note, kb_sources)
    # No Content-Disposition header: verified live (2026-11-14) that at
    # least one current Chrome build fails a cross-origin fetch() reading a
    # response that carries `Content-Disposition: attachment` -- the
    # response never reaches JS (fetch rejects with a misleading
    # "MissingAllowOriginHeader" CORS error) even though the server's
    # Access-Control-Allow-Origin header is present and correct (confirmed
    # with curl/http.client against the identical response). Reproduced in
    # an isolated minimal FastAPI app, so it's Chrome's handling of
    # attachment-disposition cross-origin fetches, not anything specific to
    # this backend. The frontend sets its own filename via the anchor
    # `download` attribute on the blob URL, so this header isn't needed.
    return Response(content=pdf_bytes, media_type="application/pdf")
