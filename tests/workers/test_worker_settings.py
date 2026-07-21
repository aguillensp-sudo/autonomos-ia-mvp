"""SPEC-F5-02: ARQ WorkerSettings + selective retry. ARQ has no on_job_failed
hook — retry-only-for-sesion_expirada is implemented inside
procesar_presentacion itself (catch, inspect codigo_error, re-raise only for
that one code). Acceptance criteria: CA-F5-03.
"""
import asyncio
from unittest.mock import MagicMock, patch

import pytest

from src.workers.rpa_worker import WorkerSettings, procesar_presentacion


def _ctx_con_presentacion(estado_fila: dict) -> dict:
    ctx = _ctx()
    ctx["client"].table.return_value.select.return_value.eq.return_value.execute.return_value.data = [estado_fila]
    return ctx


class _ErrorConCodigo(Exception):
    def __init__(self, codigo_error: str):
        self.codigo_error = codigo_error
        super().__init__(f"fallo simulado: {codigo_error}")


def _ctx():
    return {
        "client": MagicMock(), "page": MagicMock(), "nif": "12345678Z",
        "perfil": MagicMock(), "resultado_m303": MagicMock(), "pdf_bytes": b"x",
    }


def test_worker_settings_registra_procesar_presentacion():
    assert procesar_presentacion in WorkerSettings.functions
    assert WorkerSettings.max_tries == 3


@patch("src.workers.rpa_worker.ejecutar_presentacion")
def test_procesar_presentacion_relanza_si_sesion_expirada(mock_ejecutar):
    mock_ejecutar.side_effect = _ErrorConCodigo("sesion_expirada")
    with pytest.raises(_ErrorConCodigo):
        asyncio.run(procesar_presentacion(_ctx(), "p1"))


@patch("src.workers.rpa_worker.ejecutar_presentacion")
def test_procesar_presentacion_no_relanza_si_error_code_distinto(mock_ejecutar):
    mock_ejecutar.side_effect = _ErrorConCodigo("discrepancia_resultado")
    resultado = asyncio.run(procesar_presentacion(_ctx(), "p1"))
    assert resultado["estado"] == "error"
    assert resultado["error_code"] == "discrepancia_resultado"


@patch("src.workers.rpa_worker.ejecutar_presentacion")
def test_procesar_presentacion_no_relanza_error_generico_sin_codigo(mock_ejecutar):
    """A truly unexpected exception (no codigo_error attribute at all) must
    not crash procesar_presentacion's own error-classification logic, and
    must not be retried (fail-safe default: swallow, don't retry blindly)."""
    mock_ejecutar.side_effect = RuntimeError("fallo totalmente inesperado")
    resultado = asyncio.run(procesar_presentacion(_ctx(), "p1"))
    assert resultado["estado"] == "error"
    assert resultado["error_code"] == "fallo_presentacion"


@patch("src.workers.rpa_worker.programar_alerta_siguiente_trimestre")
@patch("src.workers.rpa_worker.ejecutar_presentacion")
def test_procesar_presentacion_programa_alerta_tras_exito(mock_ejecutar, mock_programar_alerta):
    mock_ejecutar.return_value = {"estado": "presentado", "csv": "ABCD1234EFGH5678", "justificante_path": "j.pdf"}
    ctx = _ctx_con_presentacion({"user_id": "u1", "ejercicio": 2026, "periodo": "1T"})

    asyncio.run(procesar_presentacion(ctx, "p1"))

    mock_programar_alerta.assert_called_once_with(ctx["client"], user_id="u1", ejercicio=2026, periodo="1T")


@patch("src.workers.rpa_worker.programar_alerta_siguiente_trimestre")
@patch("src.workers.rpa_worker.ejecutar_presentacion")
def test_procesar_presentacion_no_programa_alerta_duplicada_si_ya_omitido(mock_ejecutar, mock_programar_alerta):
    """Regression: ejecutar_presentacion's own idempotent early-return (T04-E1
    precheck) also reports estado='presentado' for an already-filed row —
    scheduling an alert on THAT path too would duplicate it on every
    re-enqueued/replayed job."""
    mock_ejecutar.return_value = {"estado": "presentado", "omitido": True}
    ctx = _ctx_con_presentacion({"user_id": "u1", "ejercicio": 2026, "periodo": "1T"})

    asyncio.run(procesar_presentacion(ctx, "p1"))

    mock_programar_alerta.assert_not_called()


@patch("src.workers.rpa_worker.programar_alerta_siguiente_trimestre")
@patch("src.workers.rpa_worker.ejecutar_presentacion")
def test_procesar_presentacion_no_programa_alerta_si_falla(mock_ejecutar, mock_programar_alerta):
    mock_ejecutar.side_effect = _ErrorConCodigo("discrepancia_resultado")
    ctx = _ctx_con_presentacion({"user_id": "u1", "ejercicio": 2026, "periodo": "1T"})

    asyncio.run(procesar_presentacion(ctx, "p1"))

    mock_programar_alerta.assert_not_called()


@patch("src.workers.rpa_worker.programar_alerta_siguiente_trimestre")
@patch("src.workers.rpa_worker.ejecutar_presentacion")
def test_reintento_sesion_expirada_no_pierde_datos_ya_ingresados(mock_ejecutar, mock_programar_alerta):
    """CA-F5-03: a sesion_expirada failure followed by ARQ's automatic retry
    (simulated here as a second call to procesar_presentacion, exactly what
    ARQ itself does on an unswallowed exception) must reach 'presentado'
    using the SAME presentacion_id/resultado_m303 the first attempt was
    given — proving no data was lost or had to be re-entered."""
    ctx = _ctx_con_presentacion({"user_id": "u1", "ejercicio": 2026, "periodo": "1T"})
    mock_ejecutar.side_effect = [
        _ErrorConCodigo("sesion_expirada"),
        {"estado": "presentado", "csv": "ABCD1234EFGH5678", "justificante_path": "justificantes/u1/2026_1T.pdf"},
    ]

    with pytest.raises(_ErrorConCodigo):
        asyncio.run(procesar_presentacion(ctx, "p1"))

    resultado_reintento = asyncio.run(procesar_presentacion(ctx, "p1"))

    assert resultado_reintento["estado"] == "presentado"
    assert resultado_reintento["csv"] == "ABCD1234EFGH5678"
    # Both calls received the exact same context (same resultado_m303/perfil/
    # presentacion_id) — nothing was re-derived or re-entered between attempts.
    primera_llamada_kwargs = mock_ejecutar.call_args_list[0].kwargs
    segunda_llamada_kwargs = mock_ejecutar.call_args_list[1].kwargs
    assert primera_llamada_kwargs["resultado_m303"] is segunda_llamada_kwargs["resultado_m303"]
    assert primera_llamada_kwargs["perfil"] is segunda_llamada_kwargs["perfil"]
