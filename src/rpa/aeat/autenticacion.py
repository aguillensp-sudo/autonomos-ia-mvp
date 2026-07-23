"""SPEC-F4-02 — Cl@ve Móvil (QR) authentication (Modelo B only). The RPA
never sees or types a PIN — AEAT displays a QR, the user scans it with their
phone's Cl@ve Móvil app, and the RPA waits for the resulting redirect. SMS
PIN (fallback, for users without the app) is not implemented this phase —
documented known limitation. Modelo A (certificate vault) is explicitly out
of scope for MVP per openspec/config.yaml -> out_of_scope.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

SESION_TIMEOUT = timedelta(minutes=10)
ESPERA_REDIRECCION_MS = 120_000


class AutenticacionError(Exception):
    """Raised when the NIF shown by AEAT after login doesn't match the
    profile's NIF — never proceed past authentication in that case."""

    codigo_error = "autenticacion_fallida"


class SesionExpiradaError(Exception):
    """Raised when a SesionAEAT is used more than SESION_TIMEOUT after
    authentication — the Cl@ve session window is treated as 10 minutes."""

    codigo_error = "sesion_expirada"


@dataclass
class SesionAEAT:
    activa: bool
    timestamp_autenticacion: datetime


def capturar_qr_clave(page: Any, selectores: dict) -> bytes:
    """Screenshots the QR element AEAT displays for Cl@ve Móvil login.

    AEAT's QR render latency after clicking boton_acceso has been observed
    ranging from ~2s to >60s (live testing against real AEAT, see design.md
    SPEC-F4-02 amendment), so this waits explicitly for visibility with a
    generous margin before attempting the screenshot."""
    sel = selectores["clave_movil"]
    locator = page.locator(sel["qr_elemento"])
    locator.wait_for(state="visible", timeout=120_000)
    return locator.screenshot()


def autenticar_clave_movil(
    nif: str, page: Any, selectores: dict, notificacion_fn: Callable[[bytes], None]
) -> SesionAEAT:
    """Logs into the AEAT Sede Electrónica via Cl@ve Móvil (Modelo B): clicks
    the Cl@ve access option, captures the resulting QR and hands it to
    notificacion_fn (e.g. save to Supabase Storage + notify the user — the
    actual notification channel is Phase 5's concern, injected here so this
    function stays testable and decoupled from it), then waits up to
    ESPERA_REDIRECCION_MS for AEAT to redirect to the authenticated session
    once the user scans the QR with their phone. Verifies the authenticated
    NIF matches the caller's own NIF before returning an active session."""
    sel = selectores["clave_movil"]

    page.locator(sel["boton_acceso"]).click()

    qr_bytes = capturar_qr_clave(page, selectores)
    notificacion_fn(qr_bytes)

    page.wait_for_url(
        sel["url_autenticada_patron"], timeout=ESPERA_REDIRECCION_MS, wait_until="domcontentloaded"
    )

    nif_autenticado = page.locator(sel["nif_autenticado_label"]).input_value()
    if nif_autenticado != nif:
        raise AutenticacionError(
            f"NIF autenticado ({nif_autenticado!r}) no coincide con perfil.nif ({nif!r})"
        )

    return SesionAEAT(activa=True, timestamp_autenticacion=datetime.now(timezone.utc))


def verificar_sesion_activa(sesion: SesionAEAT) -> None:
    """Raises SesionExpiradaError if more than SESION_TIMEOUT has elapsed
    since authentication. Called before every AEAT-facing step in
    m303_form.py (SPEC-F4-04)."""
    if datetime.now(timezone.utc) - sesion.timestamp_autenticacion >= SESION_TIMEOUT:
        raise SesionExpiradaError("La sesión Cl@ve ha caducado (10 minutos)")
