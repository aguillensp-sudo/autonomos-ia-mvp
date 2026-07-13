"""verificar_duplicado — checks for an existing presentacion for this
user/proceso/ejercicio/periodo before starting a new declaration.
Acceptance criteria: CA-F3-09. Process-state check, not a fiscal
calculation — lives in src/agent/, not src/fiscal/.
"""
from src.agent.supabase_client import crear_cliente_usuario


def verificar_duplicado(estado: dict) -> dict:
    """Queries presentacion for a row matching
    (user_id, proceso='P04', ejercicio, periodo). Returns the partial state
    update: presentacion_duplicada, csv_presentacion_previa.
    """
    client = crear_cliente_usuario(estado["user_jwt"])

    result = (
        client.table("presentacion")
        .select("csv_aeat")
        .eq("user_id", estado["user_id"])
        .eq("proceso", "P04")
        .eq("ejercicio", estado["ejercicio"])
        .eq("periodo", estado["periodo"])
        .execute()
    )

    if not result.data:
        return {"presentacion_duplicada": False, "csv_presentacion_previa": None}

    return {
        "presentacion_duplicada": True,
        "csv_presentacion_previa": result.data[0].get("csv_aeat"),
    }
