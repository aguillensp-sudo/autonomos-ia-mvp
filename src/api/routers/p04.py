"""Minimal CRUD for facturas — Phase 1 scope only (manual entry, no OCR yet).
Per docs/backend-standards.md: no fiscal arithmetic here, this router only
persists what the client sends; cuota_iva/cuota_deducible are computed
client-side or defaulted, never recalculated by this endpoint.
"""
from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ValidationError

from src.api.dependencies import AuthedRequest, get_authed_request

router = APIRouter(prefix="/api/proceso/p04")


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
