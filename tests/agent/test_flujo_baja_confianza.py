"""Tests proving Blocker 1's ACTUAL fix (post-second-adversarial-review):
recopilar_datos resolves facturas_baja_confianza via a real interrupt()
loop, not a bare graph self-edge. These tests drive a COMPILED graph
(mirroring tests/agent/nodes/test_confirmar.py's MINIMAL-graph pattern —
recopilar_datos wired directly to END, skipping ocr_factura/calcular/etc.
to keep this scoped to recopilar_datos's own interrupt behavior) — never
call recopilar_datos() directly, since that would bypass interrupt()
entirely and prove nothing about the CRITICAL regression being fixed.

Every test invokes the graph AT LEAST TWICE for any scenario with pending
confirmations: once to trigger the interrupt, once (or more, for partial
resumes) with Command(resume=...) to resume it — per design.md SPEC-F3-06's
"Interrupt in a loop" subsection.
"""
from unittest.mock import MagicMock, patch
from uuid import uuid4

from dotenv import load_dotenv
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

load_dotenv()

from src.agent.checkpointer import crear_checkpointer
from src.agent.nodes.recopilar_datos import recopilar_datos
from src.agent.state import EstadoP04

PATH = "emitidas/user-1/factura-baja-confianza-test.png"


def _estado_con_pendientes(thread_id: str) -> dict:
    return {
        "thread_id": thread_id,
        "user_id": "user-1",
        "mensajes": [{"rol": "usuario", "contenido": "Aquí tienes la factura."}],
        "facturas_emitidas": [],
        "facturas_recibidas": [],
        "facturas_pendientes_ocr": [],
        "facturas_baja_confianza": [
            {"path": PATH, "tipo": "emitida", "campo": "fecha", "valor": "2026-02-10", "confianza": 0.95, "requiere_confirmacion": False},
            {"path": PATH, "tipo": "emitida", "campo": "base_imponible", "valor": 100.0, "confianza": 0.9, "requiere_confirmacion": True},
            {"path": PATH, "tipo": "emitida", "campo": "tipo_iva", "valor": 21, "confianza": 0.9, "requiere_confirmacion": True},
        ],
        "sin_actividad": None,
        "presentacion_duplicada": False,
        "csv_presentacion_previa": None,
    }


def _estado_sin_pendientes(thread_id: str) -> dict:
    estado = _estado_con_pendientes(thread_id)
    estado["facturas_baja_confianza"] = []
    return estado


def _construir_grafo_minimo(checkpointer):
    g = StateGraph(EstadoP04)
    g.add_node("recopilar_datos", recopilar_datos)
    g.add_edge(START, "recopilar_datos")
    g.add_edge("recopilar_datos", END)
    return g.compile(checkpointer=checkpointer)


def test_recopilar_datos_interrumpe_cuando_hay_baja_confianza_pendiente():
    """Driving the compiled graph (not recopilar_datos() directly): a
    pending facturas_baja_confianza entry must produce a genuine
    interrupt() pause, not a GraphRecursionError and not a silent
    proceed-past. The LLM must never be called on this pass."""
    cliente_mock = MagicMock()
    with patch("src.agent.nodes.recopilar_datos.crear_cliente_anthropic", return_value=cliente_mock):
        with crear_checkpointer() as checkpointer:
            checkpointer.setup()
            grafo = _construir_grafo_minimo(checkpointer)
            thread_id = f"test-interrupt-baja-confianza-{uuid4()}"
            config = {"configurable": {"thread_id": thread_id}}

            resultado = grafo.invoke(_estado_con_pendientes(thread_id), config=config)

    assert "__interrupt__" in resultado
    pendientes_en_interrupt = resultado["__interrupt__"][0].value["pendientes"]
    campos_pendientes = {e["campo"] for e in pendientes_en_interrupt}
    assert campos_pendientes == {"base_imponible", "tipo_iva"}
    cliente_mock.messages.create.assert_not_called()


def test_recopilar_datos_resume_confirmaciones_completas_ensambla_factura():
    """Resuming with confirmations for ALL pending fields must fully
    resolve facturas_baja_confianza, assemble the invoice into
    facturas_emitidas, and NOT call the LLM (habia_pendientes early
    return) — this is what prevents the CRITICAL regression: the
    Claude Sonnet 5 call is never a side effect of resuming a
    confirmation."""
    cliente_mock = MagicMock()
    with patch("src.agent.nodes.recopilar_datos.crear_cliente_anthropic", return_value=cliente_mock):
        with crear_checkpointer() as checkpointer:
            checkpointer.setup()
            grafo = _construir_grafo_minimo(checkpointer)
            thread_id = f"test-resume-completo-{uuid4()}"
            config = {"configurable": {"thread_id": thread_id}}

            grafo.invoke(_estado_con_pendientes(thread_id), config=config)  # invocation 1: triggers interrupt
            resultado = grafo.invoke(
                Command(resume={"confirmaciones": [
                    {"path": PATH, "campo": "base_imponible", "valor_confirmado": 100.0, "tipo": "emitida"},
                    {"path": PATH, "campo": "tipo_iva", "valor_confirmado": 21, "tipo": "emitida"},
                ]}),
                config=config,
            )  # invocation 2: resumes

    assert "__interrupt__" not in resultado
    assert resultado["facturas_baja_confianza"] == []
    assert len(resultado["facturas_emitidas"]) == 1
    factura = resultado["facturas_emitidas"][0]
    assert factura["base_imponible"] == 100.0
    assert factura["tipo_iva"] == 21
    assert factura["fecha"] == "2026-02-10"  # already-accepted non-fiscal field carried along
    cliente_mock.messages.create.assert_not_called()


def test_recopilar_datos_resume_parcial_interrumpe_de_nuevo():
    """A resume that only answers SOME pending fields must interrupt()
    again with the remaining ones — not raise, not silently drop them,
    not proceed as if everything were resolved."""
    cliente_mock = MagicMock()
    with patch("src.agent.nodes.recopilar_datos.crear_cliente_anthropic", return_value=cliente_mock):
        with crear_checkpointer() as checkpointer:
            checkpointer.setup()
            grafo = _construir_grafo_minimo(checkpointer)
            thread_id = f"test-resume-parcial-{uuid4()}"
            config = {"configurable": {"thread_id": thread_id}}

            grafo.invoke(_estado_con_pendientes(thread_id), config=config)  # invocation 1: triggers interrupt
            resultado_parcial = grafo.invoke(
                Command(resume={"confirmaciones": [
                    {"path": PATH, "campo": "base_imponible", "valor_confirmado": 100.0, "tipo": "emitida"},
                ]}),
                config=config,
            )  # invocation 2: partial resume — tipo_iva still pending

    assert "__interrupt__" in resultado_parcial
    pendientes_restantes = resultado_parcial["__interrupt__"][0].value["pendientes"]
    assert {e["campo"] for e in pendientes_restantes} == {"tipo_iva"}
    cliente_mock.messages.create.assert_not_called()

    # Resolve the last one — now it must fully resolve.
    with patch("src.agent.nodes.recopilar_datos.crear_cliente_anthropic", return_value=cliente_mock):
        with crear_checkpointer() as checkpointer:
            grafo = _construir_grafo_minimo(checkpointer)
            resultado_final = grafo.invoke(
                Command(resume={"confirmaciones": [
                    {"path": PATH, "campo": "tipo_iva", "valor_confirmado": 21, "tipo": "emitida"},
                ]}),
                config=config,
            )

    assert "__interrupt__" not in resultado_final
    assert resultado_final["facturas_baja_confianza"] == []
    assert len(resultado_final["facturas_emitidas"]) == 1
    cliente_mock.messages.create.assert_not_called()


def test_recopilar_datos_sin_pendientes_llama_al_llm_normalmente():
    """No facturas_baja_confianza pending at all — interrupt() must never
    be called, and the normal Claude Sonnet 5 conversational turn must
    still run exactly as before this fix."""
    respuesta_mock = MagicMock()
    respuesta_mock.content = []
    respuesta_mock.usage.input_tokens = 5
    respuesta_mock.usage.output_tokens = 5
    cliente_mock = MagicMock()
    cliente_mock.messages.create.return_value = respuesta_mock

    with patch("src.agent.nodes.recopilar_datos.crear_cliente_anthropic", return_value=cliente_mock):
        with crear_checkpointer() as checkpointer:
            checkpointer.setup()
            grafo = _construir_grafo_minimo(checkpointer)
            thread_id = f"test-sin-pendientes-{uuid4()}"
            config = {"configurable": {"thread_id": thread_id}}

            resultado = grafo.invoke(_estado_sin_pendientes(thread_id), config=config)

    assert "__interrupt__" not in resultado
    cliente_mock.messages.create.assert_called_once()
