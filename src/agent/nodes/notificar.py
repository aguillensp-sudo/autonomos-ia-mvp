"""notificar — final message + cancellation bookkeeping. If confirmado: this
graph hands off to Phase 4 (RPA) from a confirmed, un-filed state — it
upserts a presentacion row in estado='confirmado' (SPEC-F4-00, rpa-aeat) so
Phase 4's ARQ worker has a row to pick up; it does NOT file anything with
AEAT itself. If cancelado: marks presentacion.estado='cancelado'.
"""
from uuid import uuid4

from src.agent.supabase_client import crear_cliente_usuario


def notificar(estado: dict) -> dict:
    mensajes = list(estado.get("mensajes", []))

    if estado.get("cancelado"):
        client = crear_cliente_usuario(estado["user_jwt"])
        client.table("presentacion").upsert({
            "id": str(uuid4()),
            "user_id": estado["user_id"],
            "proceso": "P04",
            "modelo": "303",
            "ejercicio": estado["ejercicio"],
            "periodo": estado["periodo"],
            "estado": "cancelado",
        }, on_conflict="user_id,proceso,ejercicio,periodo").execute()
        mensajes.append({"rol": "agente", "contenido": "Proceso cancelado. No se ha presentado nada."})
        return {"mensajes": mensajes}

    if estado.get("confirmado"):
        resultado = estado.get("resultado_m303") or {}
        client = crear_cliente_usuario(estado["user_jwt"])
        client.table("presentacion").upsert({
            "id": str(uuid4()),
            "user_id": estado["user_id"],
            "proceso": "P04",
            "modelo": "303",
            "ejercicio": estado["ejercicio"],
            "periodo": estado["periodo"],
            "estado": "confirmado",
            "total_devengado": resultado.get("total_devengado"),
            "total_deducible": resultado.get("total_deducible"),
            "saldo_compensar_aplicado": resultado.get("saldo_compensar_anterior"),
            "log_confirmacion": resultado,
        }, on_conflict="user_id,proceso,ejercicio,periodo").execute()
        mensajes.append({"rol": "agente", "contenido": "Confirmación registrada. Tu declaración está lista y pendiente de presentación."})
        return {"mensajes": mensajes}

    return {"mensajes": mensajes}
