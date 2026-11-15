from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.main import app
from tests.test_advisor_api import GOOD_EXPLAIN_JSON, LIVE_ANALYSIS, _mock_live_sources

client = TestClient(app)


def _assert_valid_pdf(content: bytes, min_pages: int = 1, max_pages: int = 3):
    assert content.startswith(b"%PDF")
    page_count = content.count(b"/Type /Page")
    assert min_pages <= page_count <= max_pages, f"expected {min_pages}-{max_pages} pages, got {page_count}"


def test_report_pdf_demo_mode_returns_2_to_3_page_pdf():
    resp = client.post("/report/pdf?demo=true", json={"current_crops": ["wheat", "cotton"], "top_n": 3})
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    # No Content-Disposition: verified live that a cross-origin fetch() of a
    # response carrying `Content-Disposition: attachment` gets blocked by at
    # least one current Chrome build (see app/routers/report.py). The
    # frontend sets its own filename via the blob anchor's `download`
    # attribute, so this header is intentionally omitted.
    assert "content-disposition" not in resp.headers
    _assert_valid_pdf(resp.content, min_pages=1, max_pages=3)


def test_report_pdf_live_mode_requires_analysis_body():
    resp = client.post("/report/pdf", json={"current_crops": ["wheat"]})
    assert resp.status_code == 422


def test_report_pdf_live_mode_end_to_end_with_mocked_groq(monkeypatch):
    _mock_live_sources(monkeypatch)
    monkeypatch.setattr("app.advisor.graph.complete_json", AsyncMock(return_value=(GOOD_EXPLAIN_JSON, "openai/gpt-oss-120b")))

    resp = client.post("/report/pdf", json={"analysis": LIVE_ANALYSIS, "current_crops": ["wheat", "cotton"], "top_n": 1})
    assert resp.status_code == 200
    _assert_valid_pdf(resp.content, min_pages=1, max_pages=3)
