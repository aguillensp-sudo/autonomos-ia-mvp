"""Unit tests for get_authed_request. Acceptance criteria: none directly,
but a real bug (found during Task 9's manual curl testing) needs a
regression guard: the Storage sub-client must carry the user's JWT, not
just the anon key, or every Storage RLS check silently fails.
"""
import base64
import json
from unittest.mock import MagicMock, patch

from src.api.dependencies import get_authed_request


def _fake_jwt(sub: str = "user-1") -> str:
    payload = base64.urlsafe_b64encode(json.dumps({"sub": sub}).encode()).decode().rstrip("=")
    return f"header.{payload}.signature"


@patch("src.api.dependencies.create_client")
def test_get_authed_request_autentica_storage_con_el_jwt(mock_create_client, monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key")

    mock_client = MagicMock()
    mock_client.options.headers = {"apikey": "anon-key"}
    mock_client.storage_url = "https://example.supabase.co/storage/v1"
    mock_create_client.return_value = mock_client

    jwt = _fake_jwt("user-1")
    resultado = get_authed_request(authorization=f"Bearer {jwt}")

    assert resultado.user_id == "user-1"
    mock_client.postgrest.auth.assert_called_once_with(jwt)
    assert mock_client._storage._headers["Authorization"] == f"Bearer {jwt}"
    assert mock_client._storage._headers["apikey"] == "anon-key"
