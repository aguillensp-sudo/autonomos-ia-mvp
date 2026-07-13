"""notificar — final message + cancellation bookkeeping. If confirmado: this
graph hands off to Phase 4 (RPA) from a confirmed, un-filed state — it does
NOT write to presentacion itself (that's Phase 4's job once it actually
files with AEAT). If cancelado: marks presentacion.estado='cancelado'.
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
        # Phase 4 owns the actual AEAT filing — this graph ends here, handing
        # off a confirmed-but-unfiled state. No presentacion write happens here.
        mensajes.append({"rol": "agente", "contenido": "Confirmación registrada. Tu declaración está lista y pendiente de presentación."})
        return {"mensajes": mensajes}

    return {"mensajes": mensajes}
