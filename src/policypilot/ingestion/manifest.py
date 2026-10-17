"""Tracks which filings have been ingested. Backs the agent's structured
"filing metadata" tool (agent/tools.py) — the retriever handles unstructured text,
this handles the "when was X filed" kind of question a UC function would answer in prod.
"""

from __future__ import annotations

import json
import os
import tempfile

from policypilot.config import DATA_DIR

MANIFEST_PATH = DATA_DIR / "manifest.json"


def load_manifest() -> dict[str, dict]:
    if not MANIFEST_PATH.exists():
        return {}
    return json.loads(MANIFEST_PATH.read_text())


def record_filing(ticker: str, filing: dict) -> None:
    manifest = load_manifest()
    manifest[ticker] = {
        "company": filing["company"],
        "filing_date": filing["filing_date"],
        "accession_number": filing["accession_number"],
        "form": "10-K",
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    # Atomic replacement prevents partial JSON after an interrupted write.
    fd, temporary = tempfile.mkstemp(dir=DATA_DIR, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=2)
        os.replace(temporary, MANIFEST_PATH)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
