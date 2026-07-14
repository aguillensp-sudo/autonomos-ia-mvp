"""SPEC-F4-02 — Cl@ve PIN authentication (Modelo B only). Modelo A
(certificate vault) is explicitly out of scope for MVP per
openspec/config.yaml -> out_of_scope.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

SESION_TIMEOUT = timedelta(minutes=10)


class AutenticacionError(Exception):
    """Raised when the NIF shown by AEAT after login doesn't match the
    profile's NIF — never proceed past authentication in that case."""


class SesionExpiradaError(Exception):
    """Raised when a SesionAEAT is used more than SESION_TIMEOUT after
    authentication — the Cl@ve PIN window is 10 minutes from PIN generation,
    not from AEAT login."""


@dataclass
class SesionAEAT:
    activa: bool
    timestamp_autenticacion: datetime


def autenticar_clave_pin(nif: str, pin: str, page: Any, selectores: dict) -> SesionAEAT:
    """Logs into the AEAT Sede Electrónica via Cl@ve PIN (Modelo B) and
    verifies the authenticated NIF matches the caller's own NIF before
    returning an active session."""
    sel = selectores["clave_pin"]

    page.locator(sel["login_button"]).click()
    page.locator(sel["nif_input"]).fill(nif)
    page.locator(sel["pin_input"]).fill(pin)
    page.locator(sel["submit_button"]).click()

    nif_autenticado = page.locator(sel["nif_autenticado_label"]).text_content()
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
        raise SesionExpiradaError("La sesión Cl@ve PIN ha caducado (10 minutos)")
