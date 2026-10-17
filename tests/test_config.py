import pytest

from policypilot.config import get_settings


def test_unknown_environment_fails_closed(monkeypatch):
    monkeypatch.setenv("PP_ENV", "production-typo")
    with pytest.raises(ValueError, match="PP_ENV"):
        get_settings()
