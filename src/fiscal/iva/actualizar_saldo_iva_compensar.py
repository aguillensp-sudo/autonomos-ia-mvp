"""Art. 99.Cinco LIVA — persistencia real del saldo a compensar entre trimestres.

This is the only module in src/fiscal/ that performs I/O (reads/writes Supabase).
No fiscal ARITHMETIC happens outside src/fiscal/ (per docs/backend-standards.md) —
this is the deliberate boundary where the deterministic engine touches the
database, closing the gap Phase 1 left open (the fiscal_integrity_check in
openspec/config.yaml: "saldo_iva_compensar is read at calculation start and
written at calculation end").
"""
from decimal import Decimal

from supabase import Client

from src.fiscal.models import ResultadoM303


def leer_saldo_compensar(client: Client, user_id: str, ejercicio: int) -> Decimal:
    """Reads the current saldo_iva_compensar for this user/ejercicio.
    Returns Decimal('0.00') if no row exists yet.
    """
    result = (
        client.table("saldo_iva_compensar")
        .select("saldo")
        .eq("user_id", user_id)
        .eq("ejercicio", ejercicio)
        .execute()
    )
    if not result.data:
        return Decimal("0.00")
    return Decimal(str(result.data[0]["saldo"]))


def actualizar_saldo_iva_compensar(
    client: Client, user_id: str, ejercicio: int, resultado: ResultadoM303
) -> Decimal:
    """Art. 99.Cinco LIVA (compensación de cuotas). Writes the new saldo:
    - tipo_resultado == 'a_compensar': nuevo_saldo = saldo_anterior + abs(resultado.resultado)
    - tipo_resultado == 'a_ingresar': nuevo_saldo = 0
    - tipo_resultado == 'sin_actividad': nuevo_saldo = saldo_anterior (unchanged)
    - tipo_resultado == 'a_devolver': nuevo_saldo = 0
    Upserts on the (user_id, ejercicio) unique constraint from docs/data-model.md.
    Returns the new saldo.
    """
    saldo_anterior = leer_saldo_compensar(client, user_id, ejercicio)

    if resultado.tipo_resultado == "a_compensar":
        nuevo_saldo = saldo_anterior + abs(resultado.resultado)
    elif resultado.tipo_resultado in ("a_ingresar", "a_devolver"):
        nuevo_saldo = Decimal("0.00")
    else:  # sin_actividad
        nuevo_saldo = saldo_anterior

    client.table("saldo_iva_compensar").upsert(
        {"user_id": user_id, "ejercicio": ejercicio, "saldo": str(nuevo_saldo)},
        on_conflict="user_id,ejercicio",
    ).execute()

    return nuevo_saldo
