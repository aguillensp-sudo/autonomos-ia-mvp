"""PostgresSaver setup against Supabase. Acceptance criteria: CA-F3-06.
Per docs/backend-standards.md: "Stateful agents via checkpointing. LangGraph
state persists in PostgreSQL via PostgresSaver. If a session is interrupted,
it resumes exactly where it stopped using thread_id."
"""
import os

from langgraph.checkpoint.postgres import PostgresSaver


def crear_checkpointer():
    """Returns a context-managed PostgresSaver against SUPABASE_DB_URL, with
    its tables created (setup() is idempotent — safe to call every time)."""
    return PostgresSaver.from_conn_string(os.environ["SUPABASE_DB_URL"])


def construir_thread_id(user_id: str, ejercicio: int, periodo: str) -> str:
    """Deterministic thread_id — resuming the same user/period always hits
    the same checkpoint. CA-F3-06."""
    return f"{user_id}:P04:{ejercicio}:{periodo}"
