"""T04-E1 / T04-E4 error handling helpers. Playwright and Supabase Storage
mocked — DB queries use a mocked Supabase client (unit-level; the full
worker integration against real Supabase is Task 9's
tests/workers/test_rpa_worker.py). Acceptance criteria: CA-F4-07, CA-F4-08.
"""
from unittest.mock import MagicMock

from src.workers.rpa_worker import (
    guardar_screenshot_y_marcar_error,
    manejar_periodo_ya_presentado,
)


def _mock_client_con_presentacion(existe: bool, csv: str | None = "ABCD1234EFGH5678"):
    client = MagicMock()
    resultado = MagicMock()
    resultado.data = [{"csv_aeat": csv, "justificante_path": "justificantes/u1/2026_1T.pdf"}] if existe else []
    client.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = resultado
    return client


def test_error_e1_periodo_ya_presentado_existe_en_bd():
    client = _mock_client_con_presentacion(existe=True)
    resultado = manejar_periodo_ya_presentado(client, user_id="u1", ejercicio=2026, periodo="1T")

    assert resultado["presentacion_existente"] is not None
    assert resultado["presentacion_existente"]["csv_aeat"] == "ABCD1234EFGH5678"
    assert resultado["error_code"] is None


def test_error_e1_periodo_ya_presentado_no_existe_en_bd():
    client = _mock_client_con_presentacion(existe=False)
    resultado = manejar_periodo_ya_presentado(client, user_id="u1", ejercicio=2026, periodo="1T")

    assert resultado["presentacion_existente"] is None
    assert resultado["error_code"] == "periodo_ya_presentado_externo"


def test_error_e4_guarda_screenshot_y_marca_estado_error():
    client = MagicMock()
    ruta = guardar_screenshot_y_marcar_error(
        client, user_id="u1", ejercicio=2026, periodo="1T",
        screenshot_bytes=b"fake-png-bytes", error_code="aeat_no_disponible",
    )

    assert ruta == "screenshots/u1/2026_1T.png"
    client.storage.from_.assert_called_once_with("screenshots")
    client.storage.from_.return_value.upload.assert_called_once()
    client.table.return_value.update.assert_called_once()
    update_kwargs = client.table.return_value.update.call_args[0][0]
    assert update_kwargs["estado"] == "error"
    assert update_kwargs["error_code"] == "aeat_no_disponible"
    assert update_kwargs["screenshot_path"] == "screenshots/u1/2026_1T.png"
