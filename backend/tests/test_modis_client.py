import datetime as dt

from app.clients.modis_client import MAX_CHUNK_DAYS, _chunk_date_range, _to_modis_date


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
