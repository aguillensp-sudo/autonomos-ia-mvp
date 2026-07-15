"""SPEC-F5-01: thin LangGraph HTTP wrapper. Unit tests here mock the
compiled graph/checkpointer entirely — no real Anthropic/Postgres call.
Real end-to-end tests against the live graph are in
test_graph_runtime_integration.py, marked @pytest.mark.integration.
"""
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from src.api.graph_runtime import (
    PresentacionDuplicadaError,
    calcular_graph,
    confirmar_graph,
    enviar_mensaje,
    iniciar_graph,
)


def _mock_grafo():
    grafo = MagicMock()
    grafo.get_state.return_value = MagicMock(values={}, tasks=[])
    return grafo


@patch("src.api.graph_runtime.crear_checkpointer")
@patch("src.api.graph_runtime.construir_grafo")
@patch("src.api.graph_runtime.verificar_duplicado")
@patch("src.api.graph_runtime.detectar_periodo")
def test_iniciar_graph_siembra_checkpoint_sin_invocar_recopilar_datos(
    mock_detectar, mock_verificar, mock_construir_grafo, mock_crear_checkpointer,
):
    mock_detectar.return_value = {
        "ejercicio": 2026, "periodo": "1T", "fecha_inicio_periodo": "2026-01-01",
        "fecha_fin_periodo": "2026-03-31", "fecha_limite_presentacion": "2026-04-20",
        "dias_para_vencimiento": 10,
    }
    mock_verificar.return_value = {"presentacion_duplicada": False, "csv_presentacion_previa": None}
    grafo = _mock_grafo()
    mock_construir_grafo.return_value = grafo
    mock_crear_checkpointer.return_value.__enter__.return_value = MagicMock()

    resultado = iniciar_graph(user_id=str(uuid4()), user_jwt="fake-jwt")

    assert resultado["ejercicio"] == 2026
    assert resultado["periodo"] == "1T"
    assert resultado["fecha_limite"] == "2026-04-20"
    assert "proceso_id" in resultado

    grafo.update_state.assert_called_once()
    _, kwargs = grafo.update_state.call_args
    assert kwargs.get("as_node") == "verificar_duplicado"
    grafo.invoke.assert_not_called()  # recopilar_datos never ran


@patch("src.api.graph_runtime.crear_checkpointer")
@patch("src.api.graph_runtime.construir_grafo")
@patch("src.api.graph_runtime.verificar_duplicado")
@patch("src.api.graph_runtime.detectar_periodo")
def test_iniciar_graph_detecta_presentacion_duplicada(
    mock_detectar, mock_verificar, mock_construir_grafo, mock_crear_checkpointer,
):
    mock_detectar.return_value = {
        "ejercicio": 2026, "periodo": "1T", "fecha_inicio_periodo": "2026-01-01",
        "fecha_fin_periodo": "2026-03-31", "fecha_limite_presentacion": "2026-04-20",
        "dias_para_vencimiento": 10,
    }
    mock_verificar.return_value = {"presentacion_duplicada": True, "csv_presentacion_previa": "ABCD1234EFGH5678"}

    with pytest.raises(PresentacionDuplicadaError) as exc_info:
        iniciar_graph(user_id=str(uuid4()), user_jwt="fake-jwt")

    assert exc_info.value.csv_presentacion_previa == "ABCD1234EFGH5678"
    mock_construir_grafo.assert_not_called()


@patch("src.api.graph_runtime.crear_checkpointer")
@patch("src.api.graph_runtime.construir_grafo")
def test_enviar_mensaje_primer_turno_avanza_hasta_confirmar(mock_construir_grafo, mock_crear_checkpointer):
    grafo = _mock_grafo()
    grafo.get_state.return_value = MagicMock(values={"mensajes": []}, tasks=[])
    grafo.invoke.return_value = {
        "__interrupt__": [MagicMock(value={"tipo": "confirmacion_p04", "mensaje": "Resumen: ..."})],
        "mensajes": [{"rol": "agente", "contenido": "Aqui tienes tu resumen"}],
    }
    mock_construir_grafo.return_value = grafo
    mock_crear_checkpointer.return_value.__enter__.return_value = MagicMock()

    resultado = enviar_mensaje(thread_id="u1:P04:2026:1T", payload={"tipo": "texto", "contenido": "Facture 500 euros a un cliente al 21%"})

    assert resultado["pendiente"] == "confirmacion"
    grafo.invoke.assert_called_once()


@patch("src.api.graph_runtime.crear_checkpointer")
@patch("src.api.graph_runtime.construir_grafo")
def test_enviar_mensaje_resume_con_texto_libre_cuando_pausado(mock_construir_grafo, mock_crear_checkpointer):
    grafo = _mock_grafo()
    grafo.get_state.return_value = MagicMock(
        values={"mensajes": []},
        tasks=[MagicMock(interrupts=[MagicMock(value={"tipo": "confirmacion_baja_confianza", "pendientes": []})])],
    )
    grafo.invoke.return_value = {"mensajes": []}
    mock_construir_grafo.return_value = grafo
    mock_crear_checkpointer.return_value.__enter__.return_value = MagicMock()

    enviar_mensaje(thread_id="u1:P04:2026:1T", payload={"tipo": "texto", "contenido": "confirmo el importe"})

    args, _ = grafo.invoke.call_args
    from langgraph.types import Command
    assert isinstance(args[0], Command)


@patch("src.api.graph_runtime.crear_checkpointer")
@patch("src.api.graph_runtime.construir_grafo")
def test_enviar_mensaje_factura_confirmada_actualiza_estado(mock_construir_grafo, mock_crear_checkpointer):
    grafo = _mock_grafo()
    grafo.get_state.return_value = MagicMock(values={"facturas_emitidas": [], "mensajes": []}, tasks=[])
    mock_construir_grafo.return_value = grafo
    mock_crear_checkpointer.return_value.__enter__.return_value = MagicMock()

    factura = {"numero_factura": "F-1", "base_imponible": "500.00", "tipo_iva": 21, "cuota_iva": "105.00"}
    resultado = enviar_mensaje(
        thread_id="u1:P04:2026:1T",
        payload={"tipo": "factura_confirmada", "factura": factura, "destino": "facturas_emitidas"},
    )

    grafo.update_state.assert_called_once()
    _, kwargs = grafo.update_state.call_args
    values = kwargs.get("values") or grafo.update_state.call_args[0][1]
    assert factura in values["facturas_emitidas"]
    grafo.invoke.assert_not_called()


@patch("src.api.graph_runtime.crear_checkpointer")
@patch("src.api.graph_runtime.construir_grafo")
def test_enviar_mensaje_pendiente_revision_ocr(mock_construir_grafo, mock_crear_checkpointer):
    grafo = _mock_grafo()
    grafo.get_state.return_value = MagicMock(values={"mensajes": []}, tasks=[])
    grafo.invoke.return_value = {
        "__interrupt__": [MagicMock(value={"tipo": "confirmacion_baja_confianza", "pendientes": []})],
        "mensajes": [],
    }
    mock_construir_grafo.return_value = grafo
    mock_crear_checkpointer.return_value.__enter__.return_value = MagicMock()

    resultado = enviar_mensaje(thread_id="u1:P04:2026:1T", payload={"tipo": "texto", "contenido": "una factura de 100 euros"})

    assert resultado["pendiente"] == "revision_ocr"


@patch("src.api.graph_runtime.crear_checkpointer")
@patch("src.api.graph_runtime.construir_grafo")
def test_enviar_mensaje_sin_interrupt_pendiente_es_none(mock_construir_grafo, mock_crear_checkpointer):
    grafo = _mock_grafo()
    grafo.get_state.return_value = MagicMock(values={"mensajes": []}, tasks=[])
    grafo.invoke.return_value = {"mensajes": [{"rol": "agente", "contenido": "sigo escuchando"}]}
    mock_construir_grafo.return_value = grafo
    mock_crear_checkpointer.return_value.__enter__.return_value = MagicMock()

    resultado = enviar_mensaje(thread_id="u1:P04:2026:1T", payload={"tipo": "texto", "contenido": "hola"})

    assert resultado["pendiente"] == "none"


@patch("src.api.graph_runtime.crear_checkpointer")
@patch("src.api.graph_runtime.construir_grafo")
def test_enviar_mensaje_tipo_interrupt_desconocido_es_none(mock_construir_grafo, mock_crear_checkpointer):
    grafo = _mock_grafo()
    grafo.get_state.return_value = MagicMock(values={"mensajes": []}, tasks=[])
    grafo.invoke.return_value = {"__interrupt__": [MagicMock(value={"tipo": "otro_tipo_desconocido"})], "mensajes": []}
    mock_construir_grafo.return_value = grafo
    mock_crear_checkpointer.return_value.__enter__.return_value = MagicMock()

    resultado = enviar_mensaje(thread_id="u1:P04:2026:1T", payload={"tipo": "texto", "contenido": "hola"})

    assert resultado["pendiente"] == "none"


@patch("src.api.graph_runtime.crear_checkpointer")
@patch("src.api.graph_runtime.construir_grafo")
def test_enviar_mensaje_omite_tasks_sin_interrupts(mock_construir_grafo, mock_crear_checkpointer):
    tarea_sin_interrupt = MagicMock(interrupts=[])
    tarea_con_interrupt = MagicMock(interrupts=[MagicMock(value={"tipo": "confirmacion_p04"})])
    grafo = _mock_grafo()
    grafo.get_state.return_value = MagicMock(values={"mensajes": []}, tasks=[tarea_sin_interrupt, tarea_con_interrupt])
    grafo.invoke.return_value = {"mensajes": []}
    mock_construir_grafo.return_value = grafo
    mock_crear_checkpointer.return_value.__enter__.return_value = MagicMock()

    enviar_mensaje(thread_id="u1:P04:2026:1T", payload={"tipo": "texto", "contenido": "confirmo"})

    args, _ = grafo.invoke.call_args
    from langgraph.types import Command
    assert isinstance(args[0], Command)


@patch("src.api.graph_runtime.crear_checkpointer")
@patch("src.api.graph_runtime.construir_grafo")
def test_calcular_graph_idempotente_si_ya_calculado(mock_construir_grafo, mock_crear_checkpointer):
    grafo = _mock_grafo()
    grafo.get_state.return_value = MagicMock(values={"resultado_m303": {"resultado": "160.00"}}, tasks=[])
    mock_construir_grafo.return_value = grafo
    mock_crear_checkpointer.return_value.__enter__.return_value = MagicMock()

    resultado = calcular_graph(thread_id="u1:P04:2026:1T", facturas_emitidas=None, facturas_recibidas=None)

    assert resultado == {"resultado": "160.00"}
    grafo.invoke.assert_not_called()
    grafo.update_state.assert_not_called()


@patch("src.api.graph_runtime.crear_checkpointer")
@patch("src.api.graph_runtime.construir_grafo")
def test_calcular_graph_estructurado_fusiona_facturas_y_agrega_mensaje_sintetico(mock_construir_grafo, mock_crear_checkpointer):
    grafo = _mock_grafo()
    grafo.get_state.return_value = MagicMock(values={"resultado_m303": None, "mensajes": []}, tasks=[])
    grafo.invoke.return_value = {
        "resultado_m303": {"resultado": "160.00"},
        "__interrupt__": [MagicMock(value={"tipo": "confirmacion_p04"})],
    }
    mock_construir_grafo.return_value = grafo
    mock_crear_checkpointer.return_value.__enter__.return_value = MagicMock()

    facturas_emitidas = [{"numero_factura": "F-1", "base_imponible": "500.00", "tipo_iva": 21, "cuota_iva": "105.00"}]

    resultado = calcular_graph(thread_id="u1:P04:2026:1T", facturas_emitidas=facturas_emitidas, facturas_recibidas=[])

    assert resultado == {"resultado": "160.00"}
    grafo.update_state.assert_called_once()
    grafo.invoke.assert_called_once()
    invoke_args, _ = grafo.invoke.call_args
    assert invoke_args[0] is None  # graph.invoke(None, config) continues forward, no resume needed


@patch("src.api.graph_runtime.crear_checkpointer")
@patch("src.api.graph_runtime.construir_grafo")
def test_confirmar_graph_resume_interrupt_y_devuelve_confirmado(mock_construir_grafo, mock_crear_checkpointer):
    grafo = _mock_grafo()
    grafo.invoke.return_value = {"confirmado": True}
    mock_construir_grafo.return_value = grafo
    mock_crear_checkpointer.return_value.__enter__.return_value = MagicMock()

    resultado = confirmar_graph(thread_id="u1:P04:2026:1T", metodo_pago="domiciliacion", iban="ES1234567890123456789012")

    assert resultado["confirmado"] is True
    args, _ = grafo.invoke.call_args
    from langgraph.types import Command
    assert isinstance(args[0], Command)
    assert args[0].resume["accion"] == "confirmar"
