"""End-to-end M303 orchestration for one quarter. The only function in
src/fiscal/ that touches Supabase (for saldo_iva_compensar read/write) —
everything it calls remains pure. Per docs/backend-standards.md: no fiscal
ARITHMETIC happens outside src/fiscal/; this module's own arithmetic (merging
ISP into devengado/deducible) stays inside src/fiscal/ too.
"""
from datetime import date

from supabase import Client

from src.fiscal.iva.actualizar_saldo_iva_compensar import (
    actualizar_saldo_iva_compensar,
    leer_saldo_compensar,
)
from src.fiscal.iva.calcular_bloque_informativo import calcular_bloque_informativo
from src.fiscal.iva.calcular_deducible import calcular_iva_deducible
from src.fiscal.iva.calcular_devengado import calcular_iva_devengado
from src.fiscal.iva.calcular_isp import calcular_isp
from src.fiscal.iva.calcular_resultado import calcular_resultado_m303
from src.fiscal.iva.criterio_caja import filtrar_por_criterio_caja
from src.fiscal.iva.prorrata_alerta import detectar_alerta_prorrata
from src.fiscal.iva.tabla_deducibilidad import TABLA_DEDUCIBILIDAD
from src.fiscal.iva.validar_coherencia import validar_coherencia_m303
from src.fiscal.models import FacturaEmitida, FacturaRecibida, PerfilFiscal, ResultadoM303


def calcular_m303(
    client: Client,
    user_id: str,
    ejercicio: int,
    periodo: str,
    perfil_fiscal: PerfilFiscal,
    facturas_emitidas: list[FacturaEmitida],
    facturas_recibidas: list[FacturaRecibida],
    fecha_inicio_periodo: date,
    fecha_fin_periodo: date,
    solicita_devolucion: bool = False,
) -> tuple[ResultadoM303, list[str]]:
    """Orchestrates the full P04 pipeline for one quarter:
    1. Read saldo_iva_compensar from the previous quarter.
    2. Filter invoices by criterio de caja if applicable (casuística C06).
    3. Compute ISP (Art. 84.Uno.2º LIVA) and merge into devengado/deducible.
    4. Compute devengado (includes rectificativa routing, casuística C04).
    5. Compute deducible.
    6. Compute bloque informativo (casillas 59-63).
    7. Compute the quarter's result.
    8. Validate internal coherence (never raises — returns error list).
    9. Write the new saldo_iva_compensar for next quarter.

    Returns (resultado, errores_coherencia). The caller (Phase 3's
    human-in-the-loop node) decides what to do with errores_coherencia —
    this function only surfaces them.
    """
    saldo_anterior = leer_saldo_compensar(client, user_id, ejercicio)

    emitidas_filtradas, recibidas_filtradas = filtrar_por_criterio_caja(
        facturas_emitidas, facturas_recibidas, perfil_fiscal.regimen_iva,
        fecha_inicio_periodo, fecha_fin_periodo,
    )

    resultado_isp = calcular_isp(recibidas_filtradas)

    devengado = calcular_iva_devengado(emitidas_filtradas)
    devengado.total += resultado_isp.cuota_isp_devengada

    deducible = calcular_iva_deducible(recibidas_filtradas, TABLA_DEDUCIBILIDAD)
    deducible.total += resultado_isp.cuota_isp_deducible

    bloque = calcular_bloque_informativo(emitidas_filtradas)  # casillas 59-63, informational only

    resultado = calcular_resultado_m303(
        ejercicio, periodo, devengado, deducible, saldo_anterior, solicita_devolucion=solicita_devolucion
    )
    resultado.casillas["12"] = resultado_isp.base_isp
    resultado.casillas["13"] = resultado_isp.cuota_isp_devengada
    resultado.casillas["59"] = bloque.casilla_59
    resultado.casillas["60"] = bloque.casilla_60
    resultado.casillas["61"] = bloque.casilla_61
    resultado.casillas["62"] = bloque.casilla_62

    errores = validar_coherencia_m303(resultado, devengado, deducible)

    alerta_prorrata = detectar_alerta_prorrata(perfil_fiscal)
    if alerta_prorrata is not None:
        errores.append(alerta_prorrata)

    actualizar_saldo_iva_compensar(client, user_id, ejercicio, resultado)

    return resultado, errores
