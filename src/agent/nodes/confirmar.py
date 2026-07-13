"""confirmar — the only path to confirmado=True. Uses LangGraph's interrupt()
to pause the graph and wait for the user's decision. Acceptance criteria:
CA-F3-06, CA-F3-07. Per docs/backend-standards.md: "Human-in-the-loop is
mandatory. Every presentation to AEAT requires explicit user confirmation.
LangGraph interrupt node handles this — never skip it."
"""
from langgraph.types import interrupt


def confirmar(estado: dict) -> dict:
    respuesta = interrupt({
        "tipo": "confirmacion_p04",
        "mensaje": estado.get("mensaje_resumen"),
    })
    accion = respuesta.get("accion")
    return {
        "confirmado": accion == "confirmar",
        "quiere_revisar": accion == "revisar",
        "cancelado": accion == "cancelar",
    }
