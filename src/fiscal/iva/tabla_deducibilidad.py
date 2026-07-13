"""Deductibility table — DATA ONLY, never logic. Update percentages here, never
in calcular_deducible.py. Art. 95 LIVA.

Full 22-category table per Hoja 4 of
docs/Autonomos.io/1. ANALISIS FUNCIONAL/.md/P04_IVA_trimestral_v1_completo_1.md,
mirrored in specs/calculo-iva-completo/design.md SPEC-F2-01. This is the
authoritative source — do not change a percentage here without updating that
source first.
"""
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class DeducibilidadRule:
    porcentaje: Decimal  # 0-100. For rule-based categories (see module docstring
                         # notes below) this is the DEFAULT the agent proposes —
                         # the engine always trusts the invoice's own
                         # porcentaje_deducible over this table value.
    descripcion: str


TABLA_DEDUCIBILIDAD: dict[str, DeducibilidadRule] = {
    "software_saas": DeducibilidadRule(
        porcentaje=Decimal("100"),
        descripcion="Software/SaaS/hosting de uso exclusivamente profesional — Art. 95 LIVA",
    ),
    "material_oficina": DeducibilidadRule(
        porcentaje=Decimal("100"),
        descripcion="Material de oficina afecto a la actividad — Art. 95 LIVA",
    ),
    "servicios_profesionales": DeducibilidadRule(
        porcentaje=Decimal("100"),
        descripcion="Servicios profesionales contratados (gestoría, abogado, diseñador) — Art. 95 LIVA",
    ),
    "equipo_informatico_exclusivo": DeducibilidadRule(
        porcentaje=Decimal("100"),
        descripcion="Equipos informáticos de uso exclusivo profesional — Art. 95 LIVA",
    ),
    "telefono_mixto": DeducibilidadRule(
        porcentaje=Decimal("50"),
        descripcion="Teléfono móvil de uso mixto — Hacienda presume 50/50 — Criterio AEAT",
    ),
    "alquiler_local": DeducibilidadRule(
        porcentaje=Decimal("100"),
        descripcion="Alquiler de local de actividad — Art. 95 LIVA",
    ),
    "suministros_local": DeducibilidadRule(
        porcentaje=Decimal("100"),
        descripcion="Suministros del local de negocio (luz/agua/internet) — Art. 95 LIVA",
    ),
    "suministros_domicilio": DeducibilidadRule(
        porcentaje=Decimal("0"),  # rule-based — see module docstring; the engine
        # NEVER uses this default, it always reads porcentaje_deducible from the
        # invoice (computed at ingestion as m2 despacho / m2 vivienda).
        descripcion=(
            "Suministros del domicilio si se trabaja desde casa — porcentaje "
            "PROPORCIONAL (m2 despacho / m2 vivienda), NUNCA un valor fijo de "
            "tabla. requiere_confirmacion=True siempre. Art. 30 LIRPF / DGT V2439-18"
        ),
    ),
    "formacion": DeducibilidadRule(
        porcentaje=Decimal("100"),
        descripcion="Formación relacionada con la actividad profesional declarada — Art. 95 LIVA",
    ),
    "publicidad_marketing": DeducibilidadRule(
        porcentaje=Decimal("100"),
        descripcion="Publicidad y marketing relacionados con la actividad — Art. 95 LIVA",
    ),
    "vehiculo_estandar": DeducibilidadRule(
        porcentaje=Decimal("50"),
        descripcion="Vehículo de uso mixto (autónomo estándar) — 50% IVA, 0% IRPF salvo transportistas — Art. 95.3 LIVA / Art. 29 LIRPF",
    ),
    "vehiculo_transportista": DeducibilidadRule(
        porcentaje=Decimal("100"),
        descripcion="Vehículo de transportista/agente comercial, uso exclusivo profesional necesario — Art. 95.3 LIVA excepción",
    ),
    "combustible_vehiculo": DeducibilidadRule(
        porcentaje=Decimal("0"),  # rule-based — proportional to the linked vehicle
        descripcion=(
            "Combustible del vehículo — el porcentaje es proporcional al del "
            "vehículo al que está vinculado (50% si vehiculo_estandar, 100% si "
            "vehiculo_transportista). No es un valor fijo de tabla."
        ),
    ),
    "comida_profesional": DeducibilidadRule(
        porcentaje=Decimal("0"),  # default when not confirmed — see requiere_confirmacion
        descripcion=(
            "Comidas en restaurante con finalidad profesional documentada — "
            "posible 100% IVA solo si estrictamente profesional, en día laborable, "
            "con anotación de comensales; 0% por defecto sin confirmación — Art. 96.2 LIVA / AEAT"
        ),
    ),
    "ropa_profesional": DeducibilidadRule(
        porcentaje=Decimal("100"),
        descripcion="Ropa de seguridad (EPI) o uniforme con logo de empresa — Art. 95 LIVA / Criterio AEAT",
    ),
    "ropa_personal": DeducibilidadRule(
        porcentaje=Decimal("0"),
        descripcion="Ropa civil sin logo empresarial — no deducible aunque se use para trabajar — Criterio AEAT DGT",
    ),
    "gastos_representacion": DeducibilidadRule(
        porcentaje=Decimal("0"),  # default when not confirmed
        descripcion=(
            "Regalos a clientes, eventos, detalles — posible 100% IVA si "
            "estrictamente relacionado con la actividad; IRPF con tope 1% del "
            "volumen de operaciones — Art. 96.2 LIVA"
        ),
    ),
    "seguro_rc_profesional": DeducibilidadRule(
        porcentaje=Decimal("100"),
        descripcion="Seguro de responsabilidad civil profesional — Art. 95 LIVA",
    ),
    "alimentacion_personal": DeducibilidadRule(
        porcentaje=Decimal("0"),
        descripcion="Alimentación personal (supermercado) — no deducible en ningún caso — Criterio AEAT",
    ),
    "multas_sanciones": DeducibilidadRule(
        porcentaje=Decimal("0"),
        descripcion="Multas y sanciones — no deducibles por ley — Art. 14 LIRPF",
    ),
    "cuota_reta": DeducibilidadRule(
        porcentaje=Decimal("0"),
        descripcion="Cuota RETA — no lleva IVA (100% deducible en IRPF, fuera de alcance de este módulo) — Art. 30 LIRPF",
    ),
    "intereses_prestamo": DeducibilidadRule(
        porcentaje=Decimal("0"),
        descripcion="Intereses de préstamos profesionales — exentos de IVA (Art. 20 LIVA); deducibles en IRPF según financiación — Art. 30 LIRPF",
    ),
}
