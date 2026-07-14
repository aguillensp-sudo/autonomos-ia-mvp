"""SPEC-F4-02: Cl@ve PIN authentication (Modelo B only — Modelo A is out of
scope per openspec/config.yaml). Playwright is fully mocked here; no real
browser session against AEAT (see test_autenticar_clave_pin_sesion_real,
marked @pytest.mark.integration, Task 4.7 — manual Product Owner execution
only). Acceptance criteria: CA-F4-01.
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from src.rpa.aeat.autenticacion import (
    AutenticacionError,
    SesionAEAT,
    SesionExpiradaError,
    autenticar_clave_pin,
    verificar_sesion_activa,
)
from src.rpa.aeat.selectores import cargar_selectores

SELECTORES = cargar_selectores()


def _mock_page(nif_autenticado: str) -> MagicMock:
    page = MagicMock()
    locator = MagicMock()
    locator.text_content.return_value = nif_autenticado
    page.locator.return_value = locator
    return page


def test_autenticar_clave_pin_verifica_nif_coincide():
    page = _mock_page("12345678Z")
    sesion = autenticar_clave_pin(nif="12345678Z", pin="123456", page=page, selectores=SELECTORES)

    assert sesion.activa is True
    assert isinstance(sesion.timestamp_autenticacion, datetime)
    page.locator.assert_any_call(SELECTORES["clave_pin"]["login_button"])
    page.locator.assert_any_call(SELECTORES["clave_pin"]["nif_input"])
    page.locator.assert_any_call(SELECTORES["clave_pin"]["pin_input"])
    page.locator.assert_any_call(SELECTORES["clave_pin"]["submit_button"])


def test_autenticar_clave_pin_nif_no_coincide_lanza_error():
    page = _mock_page("87654321X")
    with pytest.raises(AutenticacionError):
        autenticar_clave_pin(nif="12345678Z", pin="123456", page=page, selectores=SELECTORES)


def test_sesion_expira_tras_10_minutos():
    sesion = SesionAEAT(
        activa=True,
        timestamp_autenticacion=datetime.now(timezone.utc) - timedelta(minutes=11),
    )
    with pytest.raises(SesionExpiradaError):
        verificar_sesion_activa(sesion)


def test_sesion_dentro_de_10_minutos_no_lanza_error():
    sesion = SesionAEAT(
        activa=True,
        timestamp_autenticacion=datetime.now(timezone.utc) - timedelta(minutes=5),
    )
    verificar_sesion_activa(sesion)  # must not raise


@pytest.mark.integration
def test_autenticar_clave_pin_sesion_real():
    """Task 4.7 (tasks.md): exercises a REAL Cl@ve PIN login against the
    live AEAT Sede Electrónica with a real NIF and a real, freshly-generated
    Cl@ve PIN. This cannot be run by the agent — it requires a human to
    generate their own Cl@ve PIN (10-minute window) and supply their real
    NIF at execution time. It is written here, correctly marked
    @pytest.mark.integration so `pytest -m "not integration"` never runs it,
    and is NOT executed as part of this change. The Product Owner must run
    it manually (e.g. `pytest tests/rpa/aeat/test_autenticacion.py -m integration -v`)
    with a real browser (playwright's sync_api, headed) and their own
    credentials, then confirm the result before this test may be considered
    verified. See specs/rpa-aeat/tasks.md Task 4.7 and the Step 10 report.
    """
    pytest.skip(
        "Manual Product Owner execution required: real NIF + real Cl@ve PIN "
        "against live AEAT. Not run by the agent — see docstring."
    )
