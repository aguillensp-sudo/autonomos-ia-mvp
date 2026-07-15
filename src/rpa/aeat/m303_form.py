"""SPEC-F4-04 — form navigation, filling, validation, submission. Never
hardcodes selectors (all come from the selectores dict, loaded via
src.rpa.aeat.selectores.cargar_selectores()). No fiscal arithmetic here:
every casilla value is read verbatim from the mapa_casillas produced by
src.rpa.casilla_map.construir_mapa_casillas().
"""
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from src.fiscal.models import PerfilFiscal
from src.rpa.aeat.autenticacion import SesionAEAT, verificar_sesion_activa

TOLERANCIA_DISCREPANCIA = Decimal("0.02")
NRC_PATTERN = re.compile(r"^[A-Za-z0-9]{22}$")


class ValidacionError(Exception):
    """AEAT's own 'Validar' step returned a non-empty error list — the
    caller must not proceed to presentar()."""

    codigo_error = "validacion_fallida"

    def __init__(self, errores: list[str]):
        self.errores = errores
        super().__init__(f"AEAT reportó {len(errores)} error(es) de validación: {errores}")


class DiscrepanciaResultadoError(Exception):
    """T04-E3 — the agent's computed casilla 27/45 differs from AEAT's own
    calculation by more than TOLERANCIA_DISCREPANCIA. Hard stop, never
    auto-corrected."""

    codigo_error = "discrepancia_resultado"

    def __init__(self, casilla: str, esperado: Decimal, calculado_aeat: Decimal):
        self.casilla = casilla
        self.esperado = esperado
        self.calculado_aeat = calculado_aeat
        super().__init__(
            f"Discrepancia en casilla {casilla}: agente={esperado}, AEAT={calculado_aeat}"
        )


class NRCInvalidoError(Exception):
    """T04-E2 — the supplied NRC doesn't match the required 22-character
    alphanumeric format. Never guessed or auto-corrected."""

    codigo_error = "nrc_invalido"


@dataclass
class PresentacionResult:
    csv: str
    nrc: str | None
    timestamp: datetime


def navegar_a_modelo_303(page: Any, ejercicio: int, periodo: str, nif_esperado: str, selectores: dict) -> None:
    sel = selectores["navegacion"]
    page.locator(sel["menu_iva"]).click()
    page.locator(sel["modelo_303"]).click()
    page.locator(sel["selector_ejercicio"]).fill(str(ejercicio))
    page.locator(sel["selector_periodo"]).fill(periodo)

    nif_prellenado = page.locator(sel["nif_titular_prellenado"]).text_content()
    if nif_prellenado != nif_esperado:
        raise ValueError(
            f"NIF prellenado por AEAT ({nif_prellenado!r}) no coincide con perfil.nif ({nif_esperado!r})"
        )


def rellenar_pagina_identificacion(page: Any, perfil: PerfilFiscal, selectores: dict) -> None:
    sel = selectores["pagina_1_identificacion"]
    page.locator(sel["regimen_general_checkbox"]).click()
    if perfil.regimen_iva == "criterio_caja":
        page.locator(sel["criterio_caja_checkbox"]).click()


def rellenar_pagina_devengado(page: Any, mapa_casillas: dict[str, Decimal], selectores: dict) -> None:
    sel = selectores["pagina_2_devengado"]
    for casilla, valor in mapa_casillas.items():
        clave = f"casilla_{casilla}"
        if clave in sel:
            page.locator(sel[clave]).fill(str(valor))

    esperado = mapa_casillas.get("27", Decimal("0.00"))
    calculado_texto = page.locator(sel["casilla_27_aeat_calculada"]).text_content()
    if calculado_texto is not None:
        calculado_aeat = Decimal(calculado_texto)
        if abs(calculado_aeat - esperado) > TOLERANCIA_DISCREPANCIA:
            raise DiscrepanciaResultadoError("27", esperado, calculado_aeat)


def rellenar_pagina_deducible(page: Any, mapa_casillas: dict[str, Decimal], selectores: dict) -> None:
    sel = selectores["pagina_3_deducible"]
    for casilla, valor in mapa_casillas.items():
        clave = f"casilla_{casilla}"
        if clave in sel:
            page.locator(sel[clave]).fill(str(valor))

    esperado = mapa_casillas.get("45", Decimal("0.00"))
    calculado_texto = page.locator(sel["casilla_45_aeat_calculada"]).text_content()
    if calculado_texto is not None:
        calculado_aeat = Decimal(calculado_texto)
        if abs(calculado_aeat - esperado) > TOLERANCIA_DISCREPANCIA:
            raise DiscrepanciaResultadoError("45", esperado, calculado_aeat)


def rellenar_pagina_resultado(
    page: Any,
    mapa_casillas: dict[str, Decimal],
    tipo_resultado: str,
    metodo_pago: str | None,
    nrc: str | None,
    iban: str | None,
    selectores: dict,
) -> dict:
    sel = selectores["pagina_4_resultado"]
    for casilla in ("46", "66", "69", "70", "71", "72", "110"):
        if casilla in mapa_casillas:
            page.locator(sel[f"casilla_{casilla}"]).fill(str(mapa_casillas[casilla]))

    if tipo_resultado == "a_ingresar":
        if metodo_pago == "domiciliacion":
            page.locator(sel["iban_domiciliacion_input"]).fill(iban or "")
        elif metodo_pago == "nrc":
            if not nrc or not NRC_PATTERN.match(nrc):
                raise NRCInvalidoError(f"NRC con formato inválido: {nrc!r} (debe ser 22 caracteres alfanuméricos)")
            page.locator(sel["nrc_input"]).fill(nrc)
        elif metodo_pago == "tarjeta":
            return {"requiere_accion_manual": True}
    elif tipo_resultado == "a_compensar":
        page.locator(sel["a_compensar_radio"]).click()
    elif tipo_resultado == "a_devolver":
        page.locator(sel["a_devolver_radio"]).click()
        if iban:
            page.locator(sel["iban_devolucion_input"]).fill(iban)
    elif tipo_resultado == "sin_actividad":
        page.locator(sel["sin_actividad_checkbox"]).click()

    return {"requiere_accion_manual": False}


def rellenar_bloque_informativo(page: Any, mapa_casillas: dict[str, Decimal], selectores: dict) -> None:
    sel = selectores["pagina_4_resultado"]
    for casilla in ("59", "60", "61", "62", "63"):
        valor = mapa_casillas.get(casilla)
        if valor is not None and valor != Decimal("0.00"):
            page.locator(sel[f"casilla_{casilla}"]).fill(str(valor))


def validar_formulario(page: Any, selectores: dict) -> None:
    sel = selectores["acciones"]
    page.locator(sel["validar_button"]).click()
    errores = page.locator(sel["errores_validacion_lista"]).all_text_contents()
    if errores:
        raise ValidacionError(errores)


def presentar(page: Any, sesion: SesionAEAT, selectores: dict) -> PresentacionResult:
    verificar_sesion_activa(sesion)

    sel = selectores["acciones"]
    page.locator(sel["presentar_button"]).click()
    page.locator(sel["confirmar_firma_button"]).click()

    csv = page.locator(sel["csv_presentacion_label"]).text_content()
    nrc = page.locator(sel["nrc_resultado_label"]).text_content()

    return PresentacionResult(csv=csv, nrc=nrc, timestamp=datetime.now())
