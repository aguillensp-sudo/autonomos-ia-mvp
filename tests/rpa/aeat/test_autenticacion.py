"""SPEC-F4-02: Cl@ve Móvil (QR) authentication (Modelo B only — Modelo A is
out of scope per openspec/config.yaml; SMS PIN fallback not implemented this
phase, documented as a known limitation). Playwright is mocked in every test
except test_autenticar_clave_movil_sesion_real, which drives a REAL browser
against the live AEAT Sede Electrónica — @pytest.mark.integration, excluded
from `pytest -m "not integration"`, Task 4.0.11 — manual Product Owner
execution only, never run by the agent. Acceptance criteria: CA-F4-01.
"""
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from src.rpa.aeat.autenticacion import (
    AutenticacionError,
    SesionAEAT,
    SesionExpiradaError,
    autenticar_clave_movil,
    capturar_qr_clave,
    verificar_sesion_activa,
)
from src.rpa.aeat.selectores import cargar_selectores

SELECTORES = cargar_selectores()
QR_BYTES = b"fake-qr-png-bytes"


def _mock_page(nif_autenticado: str) -> MagicMock:
    page = MagicMock()
    locator = MagicMock()
    locator.text_content.return_value = nif_autenticado
    locator.screenshot.return_value = QR_BYTES
    page.locator.return_value = locator
    return page


def test_capturar_qr_clave_retorna_screenshot_del_elemento():
    page = _mock_page("12345678Z")
    resultado = capturar_qr_clave(page, SELECTORES)

    assert resultado == QR_BYTES
    page.locator.assert_any_call(SELECTORES["clave_movil"]["qr_elemento"])


def test_autenticar_clave_movil_captura_qr_y_llama_notificacion_fn():
    page = _mock_page("12345678Z")
    notificacion_fn = MagicMock()

    autenticar_clave_movil(nif="12345678Z", page=page, selectores=SELECTORES, notificacion_fn=notificacion_fn)

    notificacion_fn.assert_called_once_with(QR_BYTES)


def test_autenticar_clave_movil_espera_redireccion_con_timeout_120s():
    page = _mock_page("12345678Z")
    autenticar_clave_movil(nif="12345678Z", page=page, selectores=SELECTORES, notificacion_fn=MagicMock())

    page.wait_for_url.assert_called_once_with(
        SELECTORES["clave_movil"]["url_autenticada_patron"], timeout=120_000
    )


def test_autenticar_clave_movil_verifica_nif_coincide():
    page = _mock_page("12345678Z")
    sesion = autenticar_clave_movil(nif="12345678Z", page=page, selectores=SELECTORES, notificacion_fn=MagicMock())

    assert sesion.activa is True
    assert isinstance(sesion.timestamp_autenticacion, datetime)
    page.locator.assert_any_call(SELECTORES["clave_movil"]["boton_acceso"])


def test_autenticar_clave_movil_nif_no_coincide_lanza_error():
    page = _mock_page("87654321X")
    with pytest.raises(AutenticacionError):
        autenticar_clave_movil(nif="12345678Z", page=page, selectores=SELECTORES, notificacion_fn=MagicMock())


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


# Real AEAT Sede Electrónica entry point. The exact deep-link to the Modelo
# 303 Cl@ve Móvil login step is not hardcoded here — AEAT's own procedure
# URLs shift between campaigns/years. Override AEAT_M303_URL if you have the
# current direct link; otherwise this lands on the public Sede home page and
# you navigate to "Modelo 303. IVA. Autoliquidación" > Cl@ve manually before
# autenticar_clave_movil() takes over from the QR-display step onward.
AEAT_SEDE_URL = os.environ.get("AEAT_M303_URL", "https://sede.agenciatributaria.gob.es")


@pytest.mark.integration
def test_autenticar_clave_movil_sesion_real():
    """Task 4.0.11 (tasks.md): exercises a REAL Cl@ve Móvil QR login against
    the live AEAT Sede Electrónica with a real NIF.

    Run manually by the Product Owner ONLY — the agent does not and cannot
    execute this (no real NIF, no phone with the Cl@ve Móvil app installed):

        pytest tests/rpa/aeat/test_autenticacion.py -m integration -v -s

    `-s` is required so pytest doesn't capture stdin/stdout — the NIF prompt
    needs it. Unlike a typed PIN, there is nothing else to enter: the browser
    opens headed (not headless) so you can see the QR AEAT displays and scan
    it yourself with your phone's Cl@ve Móvil app within the 120-second wait
    window below. `notificacion_fn` here is just a print — Task 8/9's real
    QR-to-Storage notification path is exercised separately, not by this test.

    IMPORTANT — read before running: the selectors in
    src/rpa/selectors/aeat_m303.yml were authored from the functional spec,
    never verified against the real AEAT DOM (no access to it during
    development). This first real run is expected to be the actual
    verification step — if it fails on a selector mismatch, update
    aeat_m303.yml (never m303_form.py or autenticacion.py) and re-run.
    """
    from playwright.sync_api import sync_playwright

    nif = input("NIF (e.g. 12345678Z): ").strip()
    assert nif, "NIF cannot be empty"

    selectores = cargar_selectores()

    def _notificar_qr_a_consola(qr_bytes: bytes) -> None:
        print(f"\nQR mostrado en el navegador ({len(qr_bytes)} bytes capturados). "
              "Escanéalo con la app Cl@ve Móvil ahora — tienes 120 segundos.")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        try:
            page = browser.new_page()
            page.goto(AEAT_SEDE_URL)

            sesion = autenticar_clave_movil(
                nif=nif, page=page, selectores=selectores, notificacion_fn=_notificar_qr_a_consola,
            )

            assert sesion.activa is True
            print(f"\nAutenticación OK. Sesión activa desde {sesion.timestamp_autenticacion.isoformat()}")
            verificar_sesion_activa(sesion)  # confirms the 10-min check itself doesn't misfire immediately
        finally:
            browser.close()
