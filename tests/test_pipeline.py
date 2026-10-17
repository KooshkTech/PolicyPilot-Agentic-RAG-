import pytest

from policypilot.ingestion import pipeline


def test_manifest_not_recorded_when_index_write_fails(monkeypatch, tmp_path):
    filing = {"company": "Test", "filing_date": "2026-01-01", "accession_number": "test"}

    class Client:
        def __init__(self, **kwargs):
            pass

        def get_cik_for_ticker(self, ticker):
            return 1

        def get_recent_10k(self, cik):
            return filing

        def download_filing_text(self, filing):
            return "Source text"

    class BrokenStore:
        def upsert(self, **kwargs):
            raise RuntimeError("index unavailable")

    recorded = []
    monkeypatch.setenv("PP_ENV", "local")
    monkeypatch.setattr(pipeline, "EdgarClient", Client)
    monkeypatch.setattr(pipeline, "get_vector_store", lambda: BrokenStore())
    monkeypatch.setattr(pipeline, "RAW_DIR", tmp_path)
    monkeypatch.setattr(pipeline, "record_filing", lambda *args: recorded.append(args))
    with pytest.raises(RuntimeError, match="index unavailable"):
        pipeline.run_ingestion(["AAPL"])
    assert recorded == []
