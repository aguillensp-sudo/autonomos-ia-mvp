"""SPEC-F5-01 — thin LangGraph HTTP wrapper. Every P04 endpoint operates on
the same checkpointed EstadoP04 (thread_id = proceso_id) through this
module; no endpoint calls graph.invoke()/update_state()/Command directly.

Amendment (found during implementation): the graph has no pause point
between verificar_duplicado and recopilar_datos's first LLM call, and that
call rejects an empty `mensajes` list. iniciar_graph() therefore seeds the
checkpoint via detectar_periodo/verificar_duplicado called as plain
functions + graph.update_state(as_node="verificar_duplicado") — it never
invokes the graph far enough to reach recopilar_datos. See design.md
SPEC-F5-01's amendment for the full reasoning.
"""
from typing import Any

from langgraph.types import Command

from src.agent.checkpointer import construir_thread_id, crear_checkpointer
from src.agent.graph import construir_grafo
from src.agent.nodes.detectar_periodo import detectar_periodo
from src.agent.nodes.verificar_duplicado import verificar_duplicado

_ESTADO_BASE: dict[str, Any] = {
    "sin_actividad": None,
    "facturas_emitidas": [],
    "facturas_recibidas": [],
    "facturas_pendientes_ocr": [],
    "facturas_baja_confianza": [],
    "resultado_m303": None,
    "errores_coherencia": [],
    "mensaje_resumen": None,
    "confirmado": False,
    "quiere_revisar": False,
    "cancelado": False,
    "mensajes": [],
    "tokens_usados": 0,
    "quiere_rectificativa": None,
}


class PresentacionDuplicadaError(Exception):
    """Raised when a presentacion row with a real AEAT csv_aeat already
    exists for the detected (user_id, ejercicio, periodo) — mapped to a 409
    at the router layer. An incomplete prior attempt (no csv yet) does not
    raise this; it's a resumable thread, not a true duplicate."""

    def __init__(self, csv_presentacion_previa: str):
        self.csv_presentacion_previa = csv_presentacion_previa
        super().__init__("Ya existe una presentación para este período")


def _config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def _pendiente_de_estado(resultado: dict) -> str:
    """Classifies the current interrupt (if any) into the frontend-facing
    `pendiente` field: none | revision_ocr | confirmacion."""
    interrupts = resultado.get("__interrupt__") or []
    if not interrupts:
        return "none"
    payload = interrupts[0].value if hasattr(interrupts[0], "value") else interrupts[0]
    tipo = payload.get("tipo") if isinstance(payload, dict) else None
    if tipo == "confirmacion_baja_confianza":
        return "revision_ocr"
    if tipo == "confirmacion_p04":
        return "confirmacion"
    return "none"


def _interrupt_pendiente_de_tasks(tasks) -> dict | None:
    for task in tasks or []:
        for interrupt in getattr(task, "interrupts", None) or []:
            return interrupt.value if hasattr(interrupt, "value") else interrupt
    return None


def iniciar_graph(user_id: str, user_jwt: str) -> dict:
    periodo_info = detectar_periodo({})
    ejercicio = periodo_info["ejercicio"]
    periodo = periodo_info["periodo"]
    thread_id = construir_thread_id(user_id, ejercicio, periodo)

    estado_parcial = {
        "thread_id": thread_id, "user_id": user_id, "user_jwt": user_jwt,
        **periodo_info,
    }

    dup_info = verificar_duplicado(estado_parcial)
    if dup_info.get("presentacion_duplicada") and dup_info.get("csv_presentacion_previa"):
        raise PresentacionDuplicadaError(dup_info["csv_presentacion_previa"])

    estado_completo = {**_ESTADO_BASE, **estado_parcial, **dup_info}

    with crear_checkpointer() as checkpointer:
        grafo = construir_grafo(checkpointer=checkpointer)
        grafo.update_state(_config(thread_id), estado_completo, as_node="verificar_duplicado")

    return {
        "proceso_id": thread_id,
        "ejercicio": ejercicio,
        "periodo": periodo,
        "fecha_limite": periodo_info["fecha_limite_presentacion"],
    }


def enviar_mensaje(thread_id: str, payload: dict) -> dict:
    with crear_checkpointer() as checkpointer:
        grafo = construir_grafo(checkpointer=checkpointer)
        config = _config(thread_id)

        if payload["tipo"] == "factura_confirmada":
            estado_actual = grafo.get_state(config).values
            destino = payload.get("destino", "facturas_emitidas")
            facturas = list(estado_actual.get(destino, [])) + [payload["factura"]]
            grafo.update_state(config, {destino: facturas})
            return {"mensajes": [], "pendiente": "none"}

        estado_actual = grafo.get_state(config)
        interrupt_pendiente = _interrupt_pendiente_de_tasks(estado_actual.tasks)

        if interrupt_pendiente is not None:
            resultado = grafo.invoke(Command(resume={"mensaje": payload["contenido"]}), config)
        else:
            mensajes = list(estado_actual.values.get("mensajes", [])) + [
                {"rol": "usuario", "contenido": payload["contenido"]}
            ]
            grafo.update_state(config, {"mensajes": mensajes})
            resultado = grafo.invoke(None, config)

        return {
            "mensajes": resultado.get("mensajes", []),
            "pendiente": _pendiente_de_estado(resultado),
        }


def calcular_graph(thread_id: str, facturas_emitidas: list[dict] | None, facturas_recibidas: list[dict] | None) -> dict:
    with crear_checkpointer() as checkpointer:
        grafo = construir_grafo(checkpointer=checkpointer)
        config = _config(thread_id)
        estado_actual = grafo.get_state(config).values

        if estado_actual.get("resultado_m303") is not None:
            return estado_actual["resultado_m303"]

        mensajes = list(estado_actual.get("mensajes", [])) + [
            {"rol": "usuario", "contenido": "He terminado de introducir mis facturas, calcula mi IVA."}
        ]
        grafo.update_state(config, {
            "facturas_emitidas": facturas_emitidas or [],
            "facturas_recibidas": facturas_recibidas or [],
            "sin_actividad": False,
            "mensajes": mensajes,
        })
        resultado = grafo.invoke(None, config)
        return resultado["resultado_m303"]


def confirmar_graph(thread_id: str, metodo_pago: str | None, iban: str | None) -> dict:
    with crear_checkpointer() as checkpointer:
        grafo = construir_grafo(checkpointer=checkpointer)
        config = _config(thread_id)
        resultado = grafo.invoke(
            Command(resume={"accion": "confirmar", "metodo_pago": metodo_pago, "iban": iban}),
            config,
        )
        return resultado
