import datetime as dt

import pytest

from app.clients.modis_client import MAX_CHUNK_DAYS, _chunk_date_range, _to_modis_date, fetch_ndvi_timeseries
from app.core.http import UpstreamError


def test_to_modis_date_formats_correctly():
    assert _to_modis_date("2023-01-17") == "A2023017"
    assert _to_modis_date("2023-12-31") == "A2023365"


def test_chunk_date_range_single_chunk_when_short():
    chunks = _chunk_date_range("2023-01-01", "2023-03-01")
    assert len(chunks) == 1
    assert chunks[0] == ("2023-01-01", "2023-03-01")


def test_chunk_date_range_splits_long_window_under_the_api_cap():
    # The ORNL subset endpoint rejects windows over 10 composites (160 days);
    # a 2-year request must split into multiple <=150-day chunks.
    chunks = _chunk_date_range("2022-01-01", "2023-12-31")
    assert len(chunks) > 1
    for start, end in chunks:
        span = (dt.date.fromisoformat(end) - dt.date.fromisoformat(start)).days
        assert span <= MAX_CHUNK_DAYS


def test_chunk_date_range_chunks_are_contiguous_and_cover_full_range():
    chunks = _chunk_date_range("2022-01-01", "2023-12-31")
    assert chunks[0][0] == "2022-01-01"
    assert chunks[-1][1] == "2023-12-31"
    for i in range(len(chunks) - 1):
        this_end = dt.date.fromisoformat(chunks[i][1])
        next_start = dt.date.fromisoformat(chunks[i + 1][0])
        assert next_start == this_end + dt.timedelta(days=1)


@pytest.mark.asyncio
async def test_fetch_ndvi_timeseries_tolerates_one_failed_chunk(monkeypatch):
    """A multi-year fetch spans many chunks; one transient failure (e.g. a
    503 from ORNL rate limiting) must not zero out the whole result."""
    import app.clients.modis_client as modis_client

    monkeypatch.setattr(modis_client, "cache_get", lambda key: None)
    monkeypatch.setattr(modis_client, "cache_set", lambda key, value: None)

    call_count = {"n": 0}

    async def fake_fetch_band(lat, lon, band, start_modis, end_modis):
        call_count["n"] += 1
        if start_modis == "A2018001":
            raise UpstreamError("simulated 503")
        return {
            "subset": [
                {
                    "modis_date": start_modis,
                    "calendar_date": "2019-01-01",
                    "data": [5000 if band == modis_client.NDVI_BAND else 0],
                }
            ]
        }

    monkeypatch.setattr(modis_client, "_fetch_band", fake_fetch_band)

    # Exactly two chunks over this range: the first raises, the second succeeds.
    result = await fetch_ndvi_timeseries(1.2345, 6.789, "2018-01-01", "2018-08-01")
    assert result["ok"] is True
    assert len(result["points"]) == 1
    assert result["points"][0]["ndvi"] == 0.5


@pytest.mark.asyncio
async def test_fetch_ndvi_timeseries_fails_only_if_every_chunk_fails(monkeypatch):
    import app.clients.modis_client as modis_client

    monkeypatch.setattr(modis_client, "cache_get", lambda key: None)
    monkeypatch.setattr(modis_client, "cache_set", lambda key, value: None)

    async def always_fails(lat, lon, band, start_modis, end_modis):
        raise UpstreamError("simulated total outage")

    monkeypatch.setattr(modis_client, "_fetch_band", always_fails)

    result = await fetch_ndvi_timeseries(1.2345, 6.789, "2018-01-01", "2018-06-30")
    assert result["ok"] is False
