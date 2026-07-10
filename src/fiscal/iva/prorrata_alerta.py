"""Casuística C07 — prorrata para actividades mixtas (exenta + sujeta).
Art. 102-106 LIVA (regla de prorrata).

Source spec status: 'MVP: ALERTAR. V2: IMPLEMENTAR'. This module deliberately
does NOT compute a proportional deduction — it only detects the case and
returns an alert message so the caller can surface it and route the user to
manual calculation, per docs/Autonomos.io/1. ANALISIS FUNCIONAL/.md/
P04_IVA_trimestral_v1_completo_1.md casuística C07.
"""
from src.fiscal.models import PerfilFiscal


def detectar_alerta_prorrata(perfil_fiscal: PerfilFiscal) -> str | None:
    """Returns an alert message if the autónomo has mixed exempt + taxable
    activity (prorrata applies), or None if not applicable.

    Never attempts the proportional-deduction calculation itself — that is
    out of scope for the MVP (V2 per the source spec).
    """
    if not perfil_fiscal.tiene_actividad_mixta:
        return None
    return (
        "Este perfil tiene actividad mixta (exenta + sujeta a IVA). La deducibilidad "
        "del IVA soportado no es del 100% sino proporcional (regla de prorrata, "
        "Art. 102-106 LIVA). El cálculo automático de la prorrata no está disponible "
        "en esta versión — deriva este trimestre a cálculo manual."
    )
