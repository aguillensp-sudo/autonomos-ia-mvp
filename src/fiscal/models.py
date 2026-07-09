"""Pydantic models mirroring the Supabase schema in docs/data-model.md exactly.
Acceptance criteria: CA-F1-04.
"""
import re
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

NIF_NIE_PATTERN = re.compile(r"^(\d{8}[A-Za-z]|[XYZxyz]\d{7}[A-Za-z])$")


def _validar_nif(value: str | None) -> str | None:
    if value is None:
        return value
    if not NIF_NIE_PATTERN.match(value):
        raise ValueError(f"'{value}' is not a valid Spanish NIF/NIE")
    return value


def _validar_fecha_no_futura(value: date) -> date:
    if value > date.today():
        raise ValueError(f"fecha {value} is in the future")
    return value


class PerfilFiscal(BaseModel):
    id: UUID
    user_id: UUID
    nif: str
    nombre: str
    epigrafe_iae: str
    cnae: str | None = None
    regimen_iva: Literal["general", "simplificado", "recargo_equivalencia", "criterio_caja"]
    regimen_irpf: Literal["ed_normal", "ed_simplificada", "modulos"]
    domicilio_fiscal: dict
    iban: str | None = None
    fecha_inicio: date
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    _validar_nif = field_validator("nif")(_validar_nif)


class FacturaEmitida(BaseModel):
    id: UUID
    user_id: UUID
    numero_factura: str
    fecha: date
    nif_cliente: str | None = None
    nombre_cliente: str | None = None
    base_imponible: Decimal
    tipo_iva: Literal[0, 4, 10, 21]
    cuota_iva: Decimal
    retencion_irpf: Decimal = Decimal("0")
    cuota_retencion: Decimal = Decimal("0")
    es_isp: bool = False
    es_intracomunitaria: bool = False
    es_exportacion: bool = False
    cobrada: bool = True
    fecha_cobro: date | None = None
    periodo_declarado: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    _validar_nif_cliente = field_validator("nif_cliente")(_validar_nif)
    _validar_fecha = field_validator("fecha")(_validar_fecha_no_futura)

    @field_validator("base_imponible")
    @classmethod
    def _base_imponible_no_negativa(cls, value: Decimal) -> Decimal:
        if value < 0:
            raise ValueError("base_imponible must be >= 0")
        return value


class FacturaRecibida(BaseModel):
    id: UUID
    user_id: UUID
    numero_factura: str | None = None
    fecha: date
    nif_proveedor: str | None = None
    nombre_proveedor: str | None = None
    descripcion: str | None = None
    categoria_gasto: str
    base_imponible: Decimal
    tipo_iva: Literal[0, 4, 10, 21] | None = None
    cuota_iva: Decimal | None = None
    porcentaje_deducible: Decimal
    cuota_deducible: Decimal | None = None
    es_bien_inversion: bool = False
    es_isp: bool = False
    es_intracomunitaria: bool = False
    requiere_confirmacion: bool = False
    pagada: bool = True
    fecha_pago: date | None = None
    periodo_declarado: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    _validar_nif_proveedor = field_validator("nif_proveedor")(_validar_nif)
    _validar_fecha = field_validator("fecha")(_validar_fecha_no_futura)

    @field_validator("base_imponible")
    @classmethod
    def _base_imponible_no_negativa(cls, value: Decimal) -> Decimal:
        if value < 0:
            raise ValueError("base_imponible must be >= 0")
        return value


class Presentacion(BaseModel):
    id: UUID
    user_id: UUID
    proceso: str
    modelo: str
    ejercicio: int
    periodo: Literal["1T", "2T", "3T", "4T", "ANUAL"]
    estado: Literal[
        "pendiente", "calculado", "confirmado", "presentando", "presentado", "error", "cancelado"
    ] = "pendiente"
    resultado: Decimal | None = None
    tipo_resultado: (
        Literal["a_ingresar", "a_compensar", "a_devolver", "sin_actividad", "negativa"] | None
    ) = None
    csv_aeat: str | None = None
    nrc: str | None = None
    justificante_path: str | None = None
    log_confirmacion: dict | None = None
    rpa_job_id: str | None = None
    error_code: str | None = None
    error_detail: str | None = None
    screenshot_path: str | None = None
    total_devengado: Decimal | None = None
    total_deducible: Decimal | None = None
    saldo_compensar_aplicado: Decimal = Decimal("0")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SaldoIVACompensar(BaseModel):
    id: UUID
    user_id: UUID
    ejercicio: int
    saldo: Decimal = Decimal("0")


class ResultadoDevengado(BaseModel):
    """Breakdown of accrued VAT by rate. Art. 88-90 LIVA."""

    por_tipo: dict[int, Decimal]
    cuotas: dict[int, Decimal]
    total: Decimal


class ResultadoDeducible(BaseModel):
    """Breakdown of deductible input VAT by expense category. Art. 95 LIVA."""

    por_categoria: dict[str, Decimal]
    total: Decimal


class ResultadoM303(BaseModel):
    ejercicio: int
    periodo: str
    total_devengado: Decimal
    total_deducible: Decimal
    saldo_compensar_anterior: Decimal
    resultado: Decimal
    tipo_resultado: Literal["a_ingresar", "a_compensar", "a_devolver", "sin_actividad"]
    casillas: dict[str, Decimal] = {}
