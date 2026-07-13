"""Shared Anthropic client wrapped for LangSmith tracing. Acceptance
criteria: CA-F3-10 (token budget observability). Every node that calls
Claude Sonnet 5 uses this client so all calls within one graph run appear
under the same LangSmith trace tree.
"""
import os

import anthropic
from langsmith.wrappers import wrap_anthropic


def crear_cliente_anthropic():
    cliente = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    if os.environ.get("LANGSMITH_API_KEY"):
        return wrap_anthropic(cliente)
    return cliente


def envolver_texto_con_cache(texto: str) -> dict:
    """Wraps a text block with an ephemeral cache_control marker (Anthropic
    prompt caching). Use this for a static, byte-for-byte-identical-across-calls
    prefix (e.g. the P04 system prompt's glossary/rules section) so repeated
    calls are served from Anthropic's cache instead of reprocessing the same
    tokens every time — see src/agent/prompts/p04_system_prompt.py.
    """
    return {"type": "text", "text": texto, "cache_control": {"type": "ephemeral"}}
