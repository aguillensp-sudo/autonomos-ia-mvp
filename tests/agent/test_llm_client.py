"""Covers the non-LangSmith fallback branch of crear_cliente_anthropic."""
import anthropic
from dotenv import load_dotenv

load_dotenv()

from src.agent.llm_client import crear_cliente_anthropic


def test_crear_cliente_anthropic_sin_langsmith_devuelve_cliente_sin_envolver(monkeypatch):
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    cliente = crear_cliente_anthropic()
    assert type(cliente) is anthropic.Anthropic
