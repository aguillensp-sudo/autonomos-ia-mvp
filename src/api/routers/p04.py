"""Minimal CRUD for facturas — Phase 1 scope only (manual entry, no OCR yet).
Per docs/backend-standards.md: no fiscal arithmetic here, this router only
persists what the client sends; cuota_iva/cuota_deducible are computed
client-side or defaulted, never recalculated by this endpoint.
"""
from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError

from src.agent.ocr import extraer_factura_ocr
from src.api import graph_runtime
from src.api.arq_client import get_arq_pool
from src.api.dependencies import AuthedRequest, get_authed_request
from src.api.graph_runtime import GrafoEstadoTerminalError, PresentacionDuplicadaError

router = APIRouter(prefix="/api/proceso/p04")

QR_BUCKET = "qr-clave"
JUSTIFICANTE_BUCKET = "justificantes"


def _presentacion_por_proceso_id(client, proceso_id: str):
    """proceso_id is the LangGraph thread_id ("{user_id}:P04:{ejercicio}:{periodo}",
    per construir_thread_id) — not presentacion.id (a separate server-generated
    UUID). Looks up by the same (user_id, proceso, ejercicio, periodo) key
    notificar.py's own upsert uses (on_conflict="user_id,proceso,ejercicio,periodo")."""
    user_id, proceso, ejercicio, periodo = proceso_id.split(":")
    return (
        client.table("presentacion")
        .select("*")
        .eq("user_id", user_id)
        .eq("proceso", proceso)
        .eq("ejercicio", int(ejercicio))
        .eq("periodo", periodo)
        .execute()
        .data
    )


class FacturaEmitidaCreate(BaseModel):
    tipo: Literal["emitida"]
    numero_factura: str
    fecha: date
    nif_cliente: str | None = None
    base_imponible: Decimal
    tipo_iva: Literal[0, 4, 10, 21]
    cuota_iva: Decimal


class FacturaRecibidaCreate(BaseModel):
    tipo: Literal["recibida"]
    categoria_gasto: str
    fecha: date
    nif_proveedor: str | None = None
    base_imponible: Decimal
    tipo_iva: Literal[0, 4, 10, 21] | None = None
    cuota_iva: Decimal | None = None
    porcentaje_deducible: Decimal


def _error(code: str, detail: str) -> dict:
    return {"error": code, "detail": detail, "proceso": "P04"}


@router.post("/facturas", status_code=201)
def crear_factura(payload: dict, req: AuthedRequest = Depends(get_authed_request)):
    tipo = payload.get("tipo")
    try:
        if tipo == "emitida":
            data = FacturaEmitidaCreate(**payload)
            row = data.model_dump(mode="json", exclude={"tipo"})
            row["id"] = str(uuid4())
            row["user_id"] = req.user_id
            result = req.client.table("factura_emitida").insert(row).execute()
        elif tipo == "recibida":
            data = FacturaRecibidaCreate(**payload)
            row = data.model_dump(mode="json", exclude={"tipo"})
            row["id"] = str(uuid4())
            row["user_id"] = req.user_id
            result = req.client.table("factura_recibida").insert(row).execute()
        else:
            raise HTTPException(status_code=422, detail=_error("TIPO_INVALIDO", "tipo must be 'emitida' or 'recibida'"))
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=_error("VALIDATION_ERROR", str(exc))) from exc

    return result.data[0]


@router.get("/facturas")
def listar_facturas(req: AuthedRequest = Depends(get_authed_request)):
    emitidas = req.client.table("factura_emitida").select("*").execute().data
    recibidas = req.client.table("factura_recibida").select("*").execute().data
    return {"emitidas": emitidas, "recibidas": recibidas}


# --- Phase 5 (integracion-mvp) — SPEC-F5-01: thin wrappers over graph_runtime ---


@router.post("/iniciar")
def iniciar(req: AuthedRequest = Depends(get_authed_request)):
    try:
        return graph_runtime.iniciar_graph(user_id=req.user_id, user_jwt=req.jwt)
    except PresentacionDuplicadaError as exc:
        raise HTTPException(
            status_code=409,
            detail=_error("PRESENTACION_DUPLICADA", str(exc)),
        ) from exc


@router.post("/facturas/ocr")
async def subir_factura_ocr(
    file: UploadFile = File(...), tipo: str = Form(...), req: AuthedRequest = Depends(get_authed_request)
):
    """Moved from /facturas per feature.md's documented path-collision
    resolution — Phase 1's JSON /facturas (above) is untouched."""
    contenido = await file.read()
    extraido = extraer_factura_ocr(contenido, tipo)

    ruta = f"{tipo}/{req.user_id}/{file.filename}"
    req.client.storage.from_("facturas").upload(ruta, contenido, {"upsert": "true"})

    requiere_revision = any(
        valor < 0.8 for clave, valor in extraido.items() if clave.startswith("confianza_")
    )
    return {"extracted": extraido, "requires_review": requiere_revision, "pdf_path": ruta}


@router.post("/mensaje/{proceso_id}")
def enviar_mensaje(proceso_id: str, payload: dict, req: AuthedRequest = Depends(get_authed_request)):
    return graph_runtime.enviar_mensaje(thread_id=proceso_id, payload=payload)


@router.post("/calcular")
def calcular(payload: dict, req: AuthedRequest = Depends(get_authed_request)):
    try:
        return graph_runtime.calcular_graph(
            thread_id=payload["proceso_id"],
            facturas_emitidas=payload.get("facturas_emitidas"),
            facturas_recibidas=payload.get("facturas_recibidas"),
        )
    except GrafoEstadoTerminalError as exc:
        raise HTTPException(
            status_code=409,
            detail=_error("ESTADO_TERMINAL", str(exc)),
        ) from exc


@router.post("/confirmar")
async def confirmar(payload: dict, req: AuthedRequest = Depends(get_authed_request)):
    proceso_id = payload["proceso_id"]
    resultado = graph_runtime.confirmar_graph(
        thread_id=proceso_id, metodo_pago=payload.get("metodo_pago"), iban=payload.get("iban"),
    )

    if not resultado.get("confirmado"):
        return {"proceso_id": proceso_id, "rpa_job_id": None, "mensaje": "No confirmado"}

    pool = await get_arq_pool()
    job = await pool.enqueue_job("procesar_presentacion", presentacion_id=proceso_id)
    return JSONResponse(
        status_code=202,
        content={
            "proceso_id": proceso_id,
            "rpa_job_id": job.job_id,
            "mensaje": "Presentación en curso. Te notificaremos cuando esté lista.",
        },
    )


@router.get("/estado/{proceso_id}")
def estado(proceso_id: str, req: AuthedRequest = Depends(get_authed_request)):
    fila = _presentacion_por_proceso_id(req.client, proceso_id)
    if not fila:
        raise HTTPException(status_code=404, detail=_error("NOT_FOUND", "Proceso no encontrado"))
    fila = fila[0]

    qr_url = None
    if fila["estado"] == "presentando":
        ruta = f"{QR_BUCKET}/{req.user_id}/{fila['ejercicio']}_{fila['periodo']}.png"
        try:
            firmado = req.client.storage.from_(QR_BUCKET).create_signed_url(ruta, 120)
            qr_url = firmado.get("signedURL") or firmado.get("signed_url")
        except Exception:
            qr_url = None

    return {**fila, "qr_url": qr_url}


@router.get("/justificante/{proceso_id}")
def justificante(proceso_id: str, req: AuthedRequest = Depends(get_authed_request)):
    fila = _presentacion_por_proceso_id(req.client, proceso_id)
    if not fila or fila[0]["estado"] != "presentado":
        raise HTTPException(status_code=404, detail=_error("NOT_FOUND", "Justificante no disponible"))
    fila = fila[0]

    firmado = req.client.storage.from_(JUSTIFICANTE_BUCKET).create_signed_url(fila["justificante_path"], 3600)
    return {
        "url": firmado.get("signedURL") or firmado.get("signed_url"),
        "csv_aeat": fila["csv_aeat"],
        "nrc": fila.get("nrc"),
    }
