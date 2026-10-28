"""Database integration tests."""

import pytest

from src.core.config import SupabaseSettings
from src.integrations.database import session


def test_create_supabase_client_uses_service_role_key(monkeypatch) -> None:
    expected_client = object()
    create_client_calls: list[tuple[str, str]] = []

    def fake_create_client(url: str, api_key: str) -> object:
        create_client_calls.append((url, api_key))
        return expected_client

    monkeypatch.setattr(session, "create_client", fake_create_client)
    settings = SupabaseSettings(
        url="https://example.supabase.co",
        service_role_key="server-secret",
        anon_key="public-key",
    )

    client = session.create_supabase_client(settings)

    assert client is expected_client
    assert create_client_calls == [
        ("https://example.supabase.co/", "server-secret"),
    ]


def test_create_supabase_client_rejects_unconfigured_settings() -> None:
    settings = SupabaseSettings()

    with pytest.raises(ValueError, match="Supabase URL and an API key are required"):
        session.create_supabase_client(settings)
