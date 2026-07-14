"""ARQ worker for Phase 4 RPA presentations. Picks up presentacion rows in
estado='confirmado' (written by src/agent/nodes/notificar.py, SPEC-F4-00) and
drives them through autenticacion -> m303_form -> justificante. T04-E1/T04-E4
error handling per design.md SPEC-F4-04's error table.
"""
import asyncio
from typing import Any

from src.fiscal.models import PerfilFiscal, ResultadoM303
from src.rpa.aeat.autenticacion import autenticar_clave_movil
from src.rpa.aeat.justificante import descargar_justificante
from src.rpa.aeat.m303_form import (
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
from src.rpa.casilla_map import construir_mapa_casillas


def manejar_periodo_ya_presentado(client: Any, user_id: str, ejercicio: int, periodo: str) -> dict:
    """T04-E1 — período ya presentado. Checks whether a local presentacion
    row already exists for this (user_id, ejercicio, periodo) in
    estado='presentado'. If it does, the caller must surface its CSV/
    justificante and never resubmit. If it doesn't (AEAT reports one exists
    but we have no record), the caller is flagged for manual review — the
    user may have filed outside the system.
    """
    resultado = (
        client.table("presentacion")
        .select("csv_aeat, justificante_path")
        .eq("user_id", user_id)
        .eq("ejercicio", ejercicio)
        .eq("periodo", periodo)
        .eq("estado", "presentado")
        .execute()
    )

    if resultado.data:
        return {"presentacion_existente": resultado.data[0], "error_code": None}

    return {"presentacion_existente": None, "error_code": "periodo_ya_presentado_externo"}


def guardar_screenshot_y_marcar_error(
    client: Any, user_id: str, ejercicio: int, periodo: str, screenshot_bytes: bytes, error_code: str
) -> str:
    """T04-E4 — general submission failure. Saves a screenshot to Supabase
    Storage (per docs/backend-standards.md's RPA-failure convention) and
    sets presentacion.estado='error' with the given error_code, so the
    retry path (Task 9) can re-authenticate from scratch rather than
    resubmitting against a stale session.
    """
    ruta = f"screenshots/{user_id}/{ejercicio}_{periodo}.png"
    client.storage.from_("screenshots").upload(ruta, screenshot_bytes)

    client.table("presentacion").update({
        "estado": "error",
        "error_code": error_code,
        "screenshot_path": ruta,
    }).eq("user_id", user_id).eq("ejercicio", ejercicio).eq("periodo", periodo).execute()

    return ruta


def guardar_qr_clave(client: Any, user_id: str, ejercicio: int, periodo: str, qr_bytes: bytes) -> str:
    """Saves the Cl@ve Móvil QR to Supabase Storage so the user can be
    notified to scan it (SPEC-F4-02 amendment). Phase 5 will display it
    directly in the chat UI instead of this Storage round-trip — the
    notificacion_fn callback shape autenticar_clave_movil() expects doesn't
    change either way.
    """
    ruta = f"qr-clave/{user_id}/{ejercicio}_{periodo}.png"
    client.storage.from_("qr-clave").upload(ruta, qr_bytes)
    return ruta


def ejecutar_presentacion(
    client: Any,
    page: Any,
    presentacion_id: str,
    nif: str,
    perfil: PerfilFiscal,
    resultado_m303: ResultadoM303,
    metodo_pago: str | None,
    nrc: str | None,
    iban: str | None,
    pdf_bytes: bytes,
    selectores: dict | None = None,
) -> dict:
    """Drives one presentacion row (estado='confirmado') through the full
    RPA flow: autenticacion -> m303_form -> justificante. Idempotent: a row
    already in estado='presentado' is a no-op (the UNIQUE(user_id, proceso,
    ejercicio, periodo) constraint means this row IS the prior successful
    run's result, so a re-enqueued job never resubmits).
    """
    selectores = selectores or cargar_selectores()

    fila = client.table("presentacion").select("*").eq("id", presentacion_id).execute().data[0]
    if fila["estado"] != "confirmado":
        return {"estado": fila["estado"], "omitido": True}

    user_id, ejercicio, periodo = fila["user_id"], fila["ejercicio"], fila["periodo"]
    client.table("presentacion").update({"estado": "presentando"}).eq("id", presentacion_id).execute()

    def _notificar_qr(qr_bytes: bytes) -> None:
        guardar_qr_clave(client, user_id, ejercicio, periodo, qr_bytes)

    try:
        sesion = autenticar_clave_movil(nif=nif, page=page, selectores=selectores, notificacion_fn=_notificar_qr)
        navegar_a_modelo_303(page, ejercicio=ejercicio, periodo=periodo, nif_esperado=nif, selectores=selectores)
        rellenar_pagina_identificacion(page, perfil, selectores)

        mapa = construir_mapa_casillas(resultado_m303)
        rellenar_pagina_devengado(page, mapa, selectores)
        rellenar_pagina_deducible(page, mapa, selectores)
        rellenar_pagina_resultado(page, mapa, resultado_m303.tipo_resultado, metodo_pago, nrc, iban, selectores)
        rellenar_bloque_informativo(page, mapa, selectores)

        validar_formulario(page, selectores)
        resultado_presentacion = presentar(page, sesion, selectores)

        ruta = descargar_justificante(
            pdf_bytes=pdf_bytes, client=client, user_id=user_id, ejercicio=ejercicio, periodo=periodo,
            nif=nif, modelo="303", csv=resultado_presentacion.csv, resultado=str(resultado_m303.resultado),
            nrc=resultado_presentacion.nrc,
        )
        return {"estado": "presentado", "csv": resultado_presentacion.csv, "justificante_path": ruta}
    except Exception as exc:
        guardar_screenshot_y_marcar_error(
            client, user_id, ejercicio, periodo, screenshot_bytes=b"", error_code=type(exc).__name__
        )
        raise


async def procesar_presentacion(ctx: dict, presentacion_id: str) -> dict:
    """ARQ job entrypoint. Thin registration wrapper — pulls the shared
    Playwright page/Supabase client and per-declaration inputs from the ARQ
    context (set up by the worker process at startup) and runs the
    (synchronous, Playwright sync API) flow in a worker thread so it doesn't
    block the event loop.
    """
    return await asyncio.to_thread(
        ejecutar_presentacion,
        client=ctx["client"],
        page=ctx["page"],
        presentacion_id=presentacion_id,
        nif=ctx["nif"],
        perfil=ctx["perfil"],
        resultado_m303=ctx["resultado_m303"],
        metodo_pago=ctx.get("metodo_pago"),
        nrc=ctx.get("nrc"),
        iban=ctx.get("iban"),
        pdf_bytes=ctx["pdf_bytes"],
        selectores=ctx.get("selectores"),
    )
