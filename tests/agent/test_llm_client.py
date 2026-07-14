"""Covers the non-LangSmith fallback branch of crear_cliente_anthropic, and
the prompt-caching helper (T01 fix)."""
import anthropic
from dotenv import load_dotenv

load_dotenv()

from src.agent.llm_client import crear_cliente_anthropic, envolver_texto_con_cache


def test_crear_cliente_anthropic_sin_langsmith_devuelve_cliente_sin_envolver(monkeypatch):
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    cliente = crear_cliente_anthropic()
    assert type(cliente) is anthropic.Anthropic


def test_envolver_texto_con_cache_incluye_cache_control_ephemeral():
    bloque = envolver_texto_con_cache("contenido estatico del system prompt")
    assert bloque == {
        "type": "text",
        "text": "contenido estatico del system prompt",
        "cache_control": {"type": "ephemeral"},
    }
