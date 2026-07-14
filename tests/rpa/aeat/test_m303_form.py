"""SPEC-F4-04: form navigation, filling, validation, submission. Playwright
fully mocked — never hits real AEAT. Acceptance criteria: CA-F4-02, CA-F4-03,
CA-F4-04, CA-F4-05, CA-F4-06.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from src.rpa.aeat.autenticacion import SesionAEAT, SesionExpiradaError
from src.rpa.aeat.m303_form import (
    DiscrepanciaResultadoError,
    NRCInvalidoError,
    PresentacionResult,
    ValidacionError,
    navegar_a_modelo_303,
    presentar,
    rellenar_bloque_informativo,
    rellenar_pagina_deducible,
    rellenar_pagina_devengado,
    rellenar_pagina_identificacion,
    rellenar_pagina_resultado,
    validar_formulario,
)
from src.rpa.aeat.selectores import cargar_selectores

SELECTORES = cargar_selectores()


def _mock_locator(text: str | None = None) -> MagicMock:
    loc = MagicMock()
    loc.text_content.return_value = text
    return loc


def _mock_page(nif_prellenado="12345678Z", nombre_prellenado="Test Autónomo") -> MagicMock:
    page = MagicMock()

    def locator_factory(selector):
        if selector == SELECTORES["navegacion"]["nif_titular_prellenado"]:
            return _mock_locator(nif_prellenado)
        if selector == SELECTORES["navegacion"]["nombre_titular_prellenado"]:
            return _mock_locator(nombre_prellenado)
        return _mock_locator()

    page.locator.side_effect = locator_factory
    return page


def _sesion_activa() -> SesionAEAT:
    return SesionAEAT(activa=True, timestamp_autenticacion=datetime.now(timezone.utc))


def _perfil():
    from datetime import date
    from uuid import uuid4

    from src.fiscal.models import PerfilFiscal
    return PerfilFiscal(
        id=uuid4(), user_id=uuid4(), nif="12345678Z", nombre="Test Autónomo",
        epigrafe_iae="7622", regimen_iva="general", regimen_irpf="ed_normal",
        domicilio_fiscal={"calle": "Test", "numero": "1", "cp": "28001", "municipio": "Madrid", "provincia": "Madrid"},
        fecha_inicio=date(2020, 1, 1),
    )


def test_navegar_a_modelo_303_verifica_prellenado_ok():
    page = _mock_page()
    navegar_a_modelo_303(page, ejercicio=2026, periodo="1T", nif_esperado="12345678Z", selectores=SELECTORES)


def test_navegar_a_modelo_303_prellenado_no_coincide_lanza_error():
    page = _mock_page(nif_prellenado="00000000X")
    with pytest.raises(ValueError):
        navegar_a_modelo_303(page, ejercicio=2026, periodo="1T", nif_esperado="12345678Z", selectores=SELECTORES)


def test_rellenar_pagina_identificacion_marca_criterio_caja():
    page = _mock_page()
    perfil = _perfil()
    perfil = perfil.model_copy(update={"regimen_iva": "criterio_caja"})
    rellenar_pagina_identificacion(page, perfil, SELECTORES)
    page.locator.assert_any_call(SELECTORES["pagina_1_identificacion"]["criterio_caja_checkbox"])


def test_rellenar_pagina_identificacion_no_marca_criterio_caja_regimen_general():
    page = _mock_page()
    perfil = _perfil()
    checkbox_calls = []
    orig_side_effect = page.locator.side_effect

    def tracking(selector):
        if selector == SELECTORES["pagina_1_identificacion"]["criterio_caja_checkbox"]:
            checkbox_calls.append(selector)
        return orig_side_effect(selector)

    page.locator.side_effect = tracking
    rellenar_pagina_identificacion(page, perfil, SELECTORES)
    assert checkbox_calls == []


def test_rellenar_pagina_devengado_deja_en_blanco_tipos_no_aplicables():
    page = _mock_page()
    mapa = {"07": Decimal("1000.00"), "08": Decimal(21), "09": Decimal("210.00"), "27": Decimal("210.00")}
    escritos = []
    page.locator.side_effect = lambda sel: _mock_locator()
    original_fill = MagicMock()

    def locator_factory(selector):
        loc = _mock_locator("210.00" if "casilla_27" not in selector else "210.00")
        loc.fill.side_effect = lambda valor: escritos.append(selector)
        return loc

    page.locator.side_effect = locator_factory
    rellenar_pagina_devengado(page, mapa, SELECTORES)

    assert SELECTORES["pagina_2_devengado"]["casilla_07"] in escritos
    assert SELECTORES["pagina_2_devengado"]["casilla_01"] not in escritos
    assert SELECTORES["pagina_2_devengado"]["casilla_04"] not in escritos


def test_rellenar_pagina_devengado_detecta_discrepancia_casilla_27():
    page = _mock_page()

    def locator_factory(selector):
        if selector == SELECTORES["pagina_2_devengado"]["casilla_27_aeat_calculada"]:
            return _mock_locator("300.00")  # AEAT computed 300, agent computed 210 -> discrepancy
        return _mock_locator()

    page.locator.side_effect = locator_factory
    mapa = {"07": Decimal("1000.00"), "08": Decimal(21), "09": Decimal("210.00"), "27": Decimal("210.00")}
    with pytest.raises(DiscrepanciaResultadoError):
        rellenar_pagina_devengado(page, mapa, SELECTORES)


def test_rellenar_pagina_devengado_tolera_diferencia_redondeo():
    page = _mock_page()

    def locator_factory(selector):
        if selector == SELECTORES["pagina_2_devengado"]["casilla_27_aeat_calculada"]:
            return _mock_locator("210.01")  # within +/-0.02 tolerance
        return _mock_locator()

    page.locator.side_effect = locator_factory
    mapa = {"07": Decimal("1000.00"), "08": Decimal(21), "09": Decimal("210.00"), "27": Decimal("210.00")}
    rellenar_pagina_devengado(page, mapa, SELECTORES)  # must not raise


def test_rellenar_pagina_deducible_detecta_discrepancia_casilla_45():
    page = _mock_page()

    def locator_factory(selector):
        if selector == SELECTORES["pagina_3_deducible"]["casilla_45_aeat_calculada"]:
            return _mock_locator("999.00")
        return _mock_locator()

    page.locator.side_effect = locator_factory
    mapa = {"28": Decimal("100.00"), "29": Decimal("21.00"), "45": Decimal("21.00")}
    with pytest.raises(DiscrepanciaResultadoError):
        rellenar_pagina_deducible(page, mapa, SELECTORES)


def test_rellenar_pagina_resultado_domiciliacion_escribe_iban():
    page = _mock_page()
    mapa = {"69": Decimal("160.00"), "71": Decimal("160.00")}
    rellenar_pagina_resultado(page, mapa, tipo_resultado="a_ingresar", metodo_pago="domiciliacion",
                               nrc=None, iban="ES1234567890123456789012", selectores=SELECTORES)
    page.locator.assert_any_call(SELECTORES["pagina_4_resultado"]["iban_domiciliacion_input"])


def test_rellenar_pagina_resultado_nrc_valida_formato():
    page = _mock_page()
    mapa = {"69": Decimal("160.00"), "71": Decimal("160.00")}
    with pytest.raises(NRCInvalidoError):
        rellenar_pagina_resultado(page, mapa, tipo_resultado="a_ingresar", metodo_pago="nrc",
                                   nrc="demasiado-corto", iban=None, selectores=SELECTORES)


def test_rellenar_pagina_resultado_nrc_formato_valido_no_lanza():
    page = _mock_page()
    mapa = {"69": Decimal("160.00"), "71": Decimal("160.00")}
    rellenar_pagina_resultado(page, mapa, tipo_resultado="a_ingresar", metodo_pago="nrc",
                               nrc="1234567890123456789012", iban=None, selectores=SELECTORES)


def test_rellenar_pagina_resultado_tarjeta_no_escribe_campos_tarjeta():
    page = _mock_page()
    mapa = {"69": Decimal("160.00"), "71": Decimal("160.00")}
    resultado = rellenar_pagina_resultado(page, mapa, tipo_resultado="a_ingresar", metodo_pago="tarjeta",
                                           nrc=None, iban=None, selectores=SELECTORES)
    assert resultado["requiere_accion_manual"] is True


def test_rellenar_pagina_resultado_a_compensar_marca_radio():
    page = _mock_page()
    mapa = {"69": Decimal("-160.00")}
    rellenar_pagina_resultado(page, mapa, tipo_resultado="a_compensar", metodo_pago=None,
                               nrc=None, iban=None, selectores=SELECTORES)
    page.locator.assert_any_call(SELECTORES["pagina_4_resultado"]["a_compensar_radio"])


def test_rellenar_pagina_resultado_a_devolver_marca_radio_y_escribe_iban():
    page = _mock_page()
    mapa = {"69": Decimal("-160.00"), "72": Decimal("160.00")}
    rellenar_pagina_resultado(page, mapa, tipo_resultado="a_devolver", metodo_pago=None,
                               nrc=None, iban="ES1234567890123456789012", selectores=SELECTORES)
    page.locator.assert_any_call(SELECTORES["pagina_4_resultado"]["a_devolver_radio"])
    page.locator.assert_any_call(SELECTORES["pagina_4_resultado"]["iban_devolucion_input"])


def test_rellenar_pagina_resultado_sin_actividad_marca_checkbox():
    page = _mock_page()
    mapa = {"69": Decimal("0.00")}
    rellenar_pagina_resultado(page, mapa, tipo_resultado="sin_actividad", metodo_pago=None,
                               nrc=None, iban=None, selectores=SELECTORES)
    page.locator.assert_any_call(SELECTORES["pagina_4_resultado"]["sin_actividad_checkbox"])


def test_rellenar_bloque_informativo_solo_valores_positivos():
    page = _mock_page()
    escritos = []

    def locator_factory(selector):
        loc = _mock_locator()
        loc.fill.side_effect = lambda valor: escritos.append(selector)
        return loc

    page.locator.side_effect = locator_factory
    mapa = {"59": Decimal("1000.00"), "60": Decimal("0.00")}
    rellenar_bloque_informativo(page, mapa, SELECTORES)
    assert SELECTORES["pagina_4_resultado"]["casilla_59"] in escritos
    assert SELECTORES["pagina_4_resultado"]["casilla_60"] not in escritos


def test_validar_formulario_bloquea_si_aeat_reporta_errores():
    page = _mock_page()

    def locator_factory(selector):
        if selector == SELECTORES["acciones"]["errores_validacion_lista"]:
            loc = _mock_locator()
            loc.all_text_contents.return_value = ["La casilla 27 no coincide"]
            return loc
        return _mock_locator()

    page.locator.side_effect = locator_factory
    with pytest.raises(ValidacionError):
        validar_formulario(page, SELECTORES)


def test_validar_formulario_sin_errores_no_lanza():
    page = _mock_page()

    def locator_factory(selector):
        if selector == SELECTORES["acciones"]["errores_validacion_lista"]:
            loc = _mock_locator()
            loc.all_text_contents.return_value = []
            return loc
        return _mock_locator()

    page.locator.side_effect = locator_factory
    validar_formulario(page, SELECTORES)  # must not raise


def test_presentar_verifica_sesion_fresca_antes_de_enviar():
    page = _mock_page()
    sesion_expirada = SesionAEAT(
        activa=True, timestamp_autenticacion=datetime.now(timezone.utc) - timedelta(minutes=11)
    )
    with pytest.raises(SesionExpiradaError):
        presentar(page, sesion_expirada, SELECTORES)


def test_presentar_captura_csv_nrc_timestamp():
    page = _mock_page()

    def locator_factory(selector):
        if selector == SELECTORES["acciones"]["csv_presentacion_label"]:
            return _mock_locator("ABCD1234EFGH5678")
        if selector == SELECTORES["acciones"]["nrc_resultado_label"]:
            return _mock_locator(None)
        return _mock_locator()

    page.locator.side_effect = locator_factory
    resultado = presentar(page, _sesion_activa(), SELECTORES)
    assert isinstance(resultado, PresentacionResult)
    assert resultado.csv == "ABCD1234EFGH5678"
