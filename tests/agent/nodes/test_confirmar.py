"""Tests for the confirmar node + interrupt/resume mechanics.
Acceptance criteria: CA-F3-06, CA-F3-07.

interrupt() only works inside a compiled, checkpointed StateGraph — it
cannot be exercised by calling confirmar() directly. Each test here builds a
MINIMAL graph (confirmar + a conditional edge to simple placeholder nodes)
rather than the full graph from Step 11, to keep this step scoped to
confirmar's own behavior. Every test invokes the graph TWICE: once to
trigger the interrupt, once with Command(resume=...) to resume it — per the
explicit instruction for this step.
"""
import os
from uuid import uuid4

import pytest
from dotenv import load_dotenv
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command
from supabase import create_client

from src.agent.checkpointer import crear_checkpointer
from src.agent.nodes.confirmar import confirmar
from src.agent.state import EstadoP04

load_dotenv()


def _estado_inicial(thread_id: str) -> dict:
    return {
        "thread_id": thread_id,
        "user_id": "user-1",
        "ejercicio": 2026,
        "periodo": "1T",
        "fecha_inicio_periodo": None,
        "fecha_fin_periodo": None,
        "fecha_limite_presentacion": None,
        "dias_para_vencimiento": None,
        "presentacion_duplicada": False,
        "csv_presentacion_previa": None,
        "quiere_rectificativa": None,
        "sin_actividad": None,
        "facturas_emitidas": [{"numero_factura": "F-1"}],
        "facturas_recibidas": [],
        "facturas_pendientes_ocr": [],
        "facturas_baja_confianza": [],
        "resultado_m303": None,
        "errores_coherencia": [],
        "mensaje_resumen": "Resumen de prueba",
        "confirmado": False,
        "quiere_revisar": False,
        "cancelado": False,
        "mensajes": [],
        "tokens_usados": 0,
    }


def _placeholder_recopilar(estado: dict) -> dict:
    return {}


def _placeholder_notificar(estado: dict) -> dict:
    return {}


def _ruta_tras_confirmar(estado: dict) -> str:
    if estado["confirmado"]:
        return "notificar"
    if estado["quiere_revisar"]:
        return "recopilar_datos"
    return "notificar"  # cancelado


def _construir_grafo_minimo(checkpointer):
    g = StateGraph(EstadoP04)
    g.add_node("confirmar", confirmar)
    g.add_node("recopilar_datos", _placeholder_recopilar)
    g.add_node("notificar", _placeholder_notificar)
    g.add_edge(START, "confirmar")
    g.add_conditional_edges("confirmar", _ruta_tras_confirmar, {"notificar": "notificar", "recopilar_datos": "recopilar_datos"})
    g.add_edge("recopilar_datos", END)
    g.add_edge("notificar", END)
    return g.compile(checkpointer=checkpointer)


def test_confirmar_interrumpe_el_grafo():
    with crear_checkpointer() as checkpointer:
        checkpointer.setup()
        grafo = _construir_grafo_minimo(checkpointer)
        thread_id = f"test-interrupt-{uuid4()}"
        config = {"configurable": {"thread_id": thread_id}}

        resultado = grafo.invoke(_estado_inicial(thread_id), config=config)

        assert "__interrupt__" in resultado
        assert resultado["confirmado"] is False


def test_confirmar_resume_confirmado_persiste_thread():
    with crear_checkpointer() as checkpointer:
        checkpointer.setup()
        grafo = _construir_grafo_minimo(checkpointer)
        thread_id = f"test-confirmado-{uuid4()}"
        config = {"configurable": {"thread_id": thread_id}}

        grafo.invoke(_estado_inicial(thread_id), config=config)  # invocation 1: triggers interrupt
        resultado = grafo.invoke(Command(resume={"accion": "confirmar"}), config=config)  # invocation 2: resumes

        assert resultado["confirmado"] is True
        assert "__interrupt__" not in resultado


def test_confirmar_resume_revisar_vuelve_a_recopilar_datos():
    with crear_checkpointer() as checkpointer:
        checkpointer.setup()
        grafo = _construir_grafo_minimo(checkpointer)
        thread_id = f"test-revisar-{uuid4()}"
        config = {"configurable": {"thread_id": thread_id}}

        grafo.invoke(_estado_inicial(thread_id), config=config)
        resultado = grafo.invoke(Command(resume={"accion": "revisar"}), config=config)

        assert resultado["quiere_revisar"] is True
        assert resultado["confirmado"] is False
        # Facturas already collected are NOT cleared (CA-F3-07)
        assert resultado["facturas_emitidas"] == [{"numero_factura": "F-1"}]


def _get_or_create_user(admin, email: str) -> str:
    for user in admin.auth.admin.list_users():
        if user.email == email:
            return user.id
    created = admin.auth.admin.create_user({"email": email, "password": "confirmar-test-123!", "email_confirm": True})
    return created.user.id


def test_confirmar_resume_cancelar_marca_presentacion_cancelado():
    with crear_checkpointer() as checkpointer:
        checkpointer.setup()

        def notificar_test(estado: dict) -> dict:
            if estado["cancelado"]:
                client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
                client.table("presentacion").upsert({
                    "id": str(uuid4()),
                    "user_id": estado["user_id"],
                    "proceso": "P04",
                    "modelo": "303",
                    "ejercicio": estado["ejercicio"],
                    "periodo": estado["periodo"],
                    "estado": "cancelado",
                }, on_conflict="user_id,proceso,ejercicio,periodo").execute()
            return {}

        g = StateGraph(EstadoP04)
        g.add_node("confirmar", confirmar)
        g.add_node("notificar", notificar_test)
        g.add_edge(START, "confirmar")
        g.add_conditional_edges("confirmar", lambda s: "notificar", {"notificar": "notificar"})
        g.add_edge("notificar", END)
        grafo = g.compile(checkpointer=checkpointer)

        client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
        user_id = _get_or_create_user(client, "confirmar-cancelar-test@test.autonomos.local")

        thread_id = f"test-cancelar-{uuid4()}"
        config = {"configurable": {"thread_id": thread_id}}
        estado = _estado_inicial(thread_id)
        estado["user_id"] = user_id
        estado["ejercicio"] = 2035

        client.table("presentacion").delete().eq("user_id", user_id).eq("ejercicio", 2035).execute()

        grafo.invoke(estado, config=config)
        grafo.invoke(Command(resume={"accion": "cancelar"}), config=config)

        fila = client.table("presentacion").select("estado").eq("user_id", user_id).eq("ejercicio", 2035).execute()
        assert fila.data[0]["estado"] == "cancelado"

        client.table("presentacion").delete().eq("user_id", user_id).eq("ejercicio", 2035).execute()
