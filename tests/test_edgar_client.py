import pytest

from policypilot.ingestion.edgar_client import EdgarClient


def test_missing_sec_contact_fails_before_network():
    with pytest.raises(ValueError, match="contact email"):
        EdgarClient("PolicyPilot no contact")


def test_sec_retry_policy_only_retries_get():
    client = EdgarClient("PolicyPilot research owner@example.org")
    retry = client._session.get_adapter("https://www.sec.gov").max_retries
    assert retry.total == 3
    assert 429 in retry.status_forcelist
    assert retry.allowed_methods == ["GET"]
