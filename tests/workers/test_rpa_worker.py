"""ARQ worker integration: ties casilla_map + autenticacion + m303_form +
justificante + T04-E1/E4 error handling into one end-to-end flow. Playwright
mocked throughout, using the Task 5 AEAT stubs. Acceptance criteria: CA-F4-01
through CA-F4-09.
"""
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from src.fiscal.models import PerfilFiscal, ResultadoDeducible, ResultadoDevengado, ResultadoM303
from src.rpa.aeat.m303_form import ValidacionError
from src.workers.rpa_worker import ejecutar_presentacion, guardar_qr_clave, procesar_presentacion
from tests.rpa._stubs_aeat import respuesta_exito, respuesta_validacion_error


def _perfil() -> PerfilFiscal:
    from datetime import date
    from uuid import uuid4
    return PerfilFiscal(
        id=uuid4(), user_id=uuid4(), nif="12345678Z", nombre="Test Autónomo",
        epigrafe_iae="7622", regimen_iva="general", regimen_irpf="ed_normal",
        domicilio_fiscal={"calle": "Test", "numero": "1", "cp": "28001", "municipio": "Madrid", "provincia": "Madrid"},
        fecha_inicio=date(2020, 1, 1),
    )


def _resultado_m303() -> ResultadoM303:
    devengado = ResultadoDevengado(por_tipo={21: Decimal("1000.00")}, cuotas={21: Decimal("210.00")}, total=Decimal("210.00"))
    deducible = ResultadoDeducible(por_categoria={"software_saas": Decimal("50.00")}, base_por_categoria={"software_saas": Decimal("238.10")}, total=Decimal("50.00"))
    return ResultadoM303(
        ejercicio=2026, periodo="1T", total_devengado=Decimal("210.00"), total_deducible=Decimal("50.00"),
        saldo_compensar_anterior=Decimal("0.00"), resultado=Decimal("160.00"), tipo_resultado="a_ingresar",
        casillas={"27": Decimal("210.00"), "45": Decimal("50.00"), "70": Decimal("160.00")},
        devengado=devengado, deducible=deducible,
    )


def _texto_justificante_valido() -> str:
    return (
        "AGENCIA TRIBUTARIA\nModelo 303\nNIF: 12345678Z\n"
        "Ejercicio: 2026 Periodo: 1T\nCSV: ABCD1234EFGH5678\n"
        "Resultado de la liquidacion: 160.00"
    )


def _mock_client(fila_estado: str = "confirmado"):
    client = MagicMock()
    select_result = MagicMock()
    select_result.data = [{
        "id": "p1", "user_id": "u1", "ejercicio": 2026, "periodo": "1T", "estado": fila_estado,
    }]
    client.table.return_value.select.return_value.eq.return_value.execute.return_value = select_result
    return client


def _mock_page(nif="12345678Z", csv="ABCD1234EFGH5678"):
    page = MagicMock()

    def locator_factory(selector):
        loc = MagicMock()
        if "nif" in selector.lower() or "Titular" in selector or "Autenticado" in selector:
            loc.text_content.return_value = nif
        elif "csv" in selector.lower():
            loc.text_content.return_value = csv
        elif "nrc" in selector.lower():
            loc.text_content.return_value = None
        else:
            loc.text_content.return_value = None
        loc.all_text_contents.return_value = []
        return loc

    page.locator.side_effect = locator_factory
    return page


def test_guardar_qr_clave_sube_a_storage_path_correcto():
    client = MagicMock()
    ruta = guardar_qr_clave(client, user_id="u1", ejercicio=2026, periodo="1T", qr_bytes=b"fake-qr")

    assert ruta == "qr-clave/u1/2026_1T.png"
    client.storage.from_.assert_called_once_with("qr-clave")
    client.storage.from_.return_value.upload.assert_called_once_with(ruta, b"fake-qr")


def test_ejecutar_presentacion_flujo_exito_guarda_qr_en_storage(monkeypatch):
    monkeypatch.setattr("src.rpa.aeat.justificante.extraer_texto_pdf", lambda pdf_bytes: _texto_justificante_valido())
    client = _mock_client("confirmado")
    page = _mock_page()

    ejecutar_presentacion(
        client=client, page=page, presentacion_id="p1", nif="12345678Z",
        perfil=_perfil(), resultado_m303=_resultado_m303(), metodo_pago=None, nrc=None, iban=None,
        pdf_bytes=b"fake-pdf",
    )

    client.storage.from_.assert_any_call("qr-clave")


def test_procesar_presentacion_flujo_completo_exito(monkeypatch):
    monkeypatch.setattr("src.rpa.aeat.justificante.extraer_texto_pdf", lambda pdf_bytes: _texto_justificante_valido())
    client = _mock_client("confirmado")
    page = _mock_page()

    resultado = ejecutar_presentacion(
        client=client, page=page, presentacion_id="p1", nif="12345678Z",
        perfil=_perfil(), resultado_m303=_resultado_m303(), metodo_pago=None, nrc=None, iban=None,
        pdf_bytes=b"fake-pdf",
    )

    assert resultado["estado"] == "presentado"
    assert resultado["csv"] == "ABCD1234EFGH5678"


def test_procesar_presentacion_flujo_error_marca_estado_error(monkeypatch):
    client = _mock_client("confirmado")
    page = _mock_page()
    # Force AEAT's own validation to report an error
    def locator_factory(selector):
        loc = MagicMock()
        if "errores" in selector.lower() or "erroresValidacion" in selector:
            loc.all_text_contents.return_value = ["La casilla 27 no coincide"]
        elif "nif" in selector.lower() or "Titular" in selector or "Autenticado" in selector:
            loc.text_content.return_value = "12345678Z"
        else:
            loc.text_content.return_value = None
        return loc
    page.locator.side_effect = locator_factory

    with pytest.raises(ValidacionError):
        ejecutar_presentacion(
            client=client, page=page, presentacion_id="p1", nif="12345678Z",
            perfil=_perfil(), resultado_m303=_resultado_m303(), metodo_pago=None, nrc=None, iban=None,
            pdf_bytes=b"fake-pdf",
        )

    update_calls = [c for c in client.table.return_value.update.call_args_list]
    estados_escritos = [c[0][0].get("estado") for c in update_calls if "estado" in c[0][0]]
    assert "error" in estados_escritos


def test_procesar_presentacion_idempotente_si_ya_presentado():
    client = _mock_client("presentado")
    page = _mock_page()

    resultado = ejecutar_presentacion(
        client=client, page=page, presentacion_id="p1", nif="12345678Z",
        perfil=_perfil(), resultado_m303=_resultado_m303(), metodo_pago=None, nrc=None, iban=None,
        pdf_bytes=b"fake-pdf",
    )

    assert resultado == {"estado": "presentado", "omitido": True}
    page.locator.assert_not_called()


def test_procesar_presentacion_arq_wrapper_delega_a_ejecutar_presentacion():
    import asyncio

    client = _mock_client("presentado")
    page = _mock_page()
    ctx = {
        "client": client, "page": page, "nif": "12345678Z",
        "perfil": _perfil(), "resultado_m303": _resultado_m303(),
        "pdf_bytes": b"fake-pdf",
    }
    resultado = asyncio.run(procesar_presentacion(ctx, "p1"))
    assert resultado == {"estado": "presentado", "omitido": True}
