"""Deductibility table — DATA ONLY, never logic. Update percentages here, never
in calcular_deducible.py. Art. 95 LIVA.

Phase 1 (fiscal-engine-fundamentos) implements only the 5 categories required by
CA-F1-07. The full 22-category table with ISP/intracomunitario/criterio de caja
rules is Phase 2 scope (SPEC-F2-01).
"""
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class DeducibilidadRule:
    porcentaje: Decimal  # 0-100
    descripcion: str


TABLA_DEDUCIBILIDAD: dict[str, DeducibilidadRule] = {
    "vehiculo": DeducibilidadRule(
        porcentaje=Decimal("50"),
        descripcion="Vehículo de uso mixto — 50% deducible salvo prueba de uso exclusivamente profesional",
    ),
    "software": DeducibilidadRule(
        porcentaje=Decimal("100"),
        descripcion="Software/SaaS de uso profesional exclusivo",
    ),
    "comida": DeducibilidadRule(
        porcentaje=Decimal("0"),
        descripcion="Comidas/restaurante — 0% por defecto salvo justificación estrictamente profesional",
    ),
    "telefono_mixto": DeducibilidadRule(
        porcentaje=Decimal("50"),
        descripcion="Teléfono móvil de uso mixto — Hacienda asume reparto 50/50",
    ),
    "cuota_reta": DeducibilidadRule(
        porcentaje=Decimal("0"),
        descripcion="Cuota RETA — no lleva IVA (100% deducible en IRPF, fuera de alcance de este módulo)",
    ),
}
