"""GET /health — per docs/openspec-tasks-mandatory-steps.md, expected shape:
{"status": "ok", "db": "ok", "redis": "ok"}
"""
import os

from fastapi import APIRouter
from supabase import create_client

router = APIRouter()


@router.get("/health")
def health():
    db_status = "ok"
    try:
        client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_ANON_KEY"])
        client.table("perfil_fiscal").select("id").limit(1).execute()
    except Exception:
        db_status = "error"

    # Redis check is a Phase 5 concern (ARQ workers not wired yet this phase) —
    # reported as "not_configured" rather than faking "ok".
    return {"status": "ok", "db": db_status, "redis": "not_configured"}
