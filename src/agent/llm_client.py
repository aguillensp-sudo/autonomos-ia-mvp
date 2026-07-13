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
