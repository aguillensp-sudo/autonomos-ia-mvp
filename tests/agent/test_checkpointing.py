"""Checkpoint recovery test. Acceptance criteria: CA-F3-06.
Verifies that a NEW graph instance (simulating a process restart), built with
a fresh PostgresSaver connection but the SAME thread_id, recovers the exact
pre-interrupt state from the real local Supabase Postgres.
"""
from uuid import uuid4

from dotenv import load_dotenv

load_dotenv()

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from src.agent.checkpointer import crear_checkpointer
from src.agent.nodes.confirmar import confirmar
from src.agent.state import EstadoP04


def _estado_inicial(thread_id: str) -> dict:
    return {
        "thread_id": thread_id,
        "user_id": "user-1",
        "ejercicio": 2026,
        "periodo": "1T",
        "fecha_inicio_periodo": "2026-01-01",
        "fecha_fin_periodo": "2026-03-31",
        "fecha_limite_presentacion": "2026-04-20",
        "dias_para_vencimiento": 10,
        "presentacion_duplicada": False,
        "csv_presentacion_previa": None,
        "quiere_rectificativa": None,
        "sin_actividad": False,
        "facturas_emitidas": [{"numero_factura": "F-1", "base_imponible": 100.0}],
        "facturas_recibidas": [{"categoria_gasto": "software_saas", "base_imponible": 50.0}],
        "facturas_pendientes_ocr": [],
        "facturas_baja_confianza": [],
        "resultado_m303": {"resultado": "50.00", "tipo_resultado": "a_ingresar"},
        "errores_coherencia": [],
        "mensaje_resumen": "Resumen exacto de prueba con datos especificos",
        "confirmado": False,
        "quiere_revisar": False,
        "cancelado": False,
        "mensajes": [{"rol": "usuario", "contenido": "hola"}],
        "tokens_usados": 1234,
    }


def _construir_grafo(checkpointer):
    g = StateGraph(EstadoP04)
    g.add_node("confirmar", confirmar)
    g.add_edge(START, "confirmar")
    g.add_edge("confirmar", END)
    return g.compile(checkpointer=checkpointer)


def test_checkpoint_recupera_estado_exacto_tras_interrupcion():
    thread_id = f"test-checkpoint-recovery-{uuid4()}"
    config = {"configurable": {"thread_id": thread_id}}
    estado_original = _estado_inicial(thread_id)

    # "Process 1": run until interrupt, then close its checkpointer connection.
    with crear_checkpointer() as checkpointer_1:
        checkpointer_1.setup()
        grafo_1 = _construir_grafo(checkpointer_1)
        grafo_1.invoke(estado_original, config=config)
        estado_tras_interrupcion = grafo_1.get_state(config).values

    # "Process 2": brand new checkpointer connection and graph instance,
    # same thread_id — simulates a restart.
    with crear_checkpointer() as checkpointer_2:
        grafo_2 = _construir_grafo(checkpointer_2)
        estado_recuperado = grafo_2.get_state(config).values

        assert estado_recuperado["facturas_emitidas"] == estado_original["facturas_emitidas"]
        assert estado_recuperado["facturas_recibidas"] == estado_original["facturas_recibidas"]
        assert estado_recuperado["resultado_m303"] == estado_original["resultado_m303"]
        assert estado_recuperado["mensaje_resumen"] == estado_original["mensaje_resumen"]
        assert estado_recuperado["mensajes"] == estado_original["mensajes"]
        assert estado_recuperado == estado_tras_interrupcion

        resultado_final = grafo_2.invoke(Command(resume={"accion": "confirmar"}), config=config)
        assert resultado_final["confirmado"] is True
