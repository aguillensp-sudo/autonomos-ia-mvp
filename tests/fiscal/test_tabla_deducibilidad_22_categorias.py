"""Full 22-category deductibility table. Acceptance criteria: CA-F2-01.
Source of truth: docs/Autonomos.io/1. ANALISIS FUNCIONAL/.md/P04_IVA_trimestral_v1_completo_1.md
Hoja 4, mirrored in specs/calculo-iva-completo/design.md SPEC-F2-01.
"""
from decimal import Decimal

from src.fiscal.iva.tabla_deducibilidad import TABLA_DEDUCIBILIDAD

# (categoria, porcentaje_iva_esperado)
# Categories whose % is a rule rather than a constant (suministros_domicilio,
# combustible_vehiculo, comida_profesional, gastos_representacion) are checked
# separately for their special-case behavior, not a fixed percentage here.
CASOS_PORCENTAJE_FIJO = [
    ("software_saas", Decimal("100")),
    ("material_oficina", Decimal("100")),
    ("servicios_profesionales", Decimal("100")),
    ("equipo_informatico_exclusivo", Decimal("100")),
    ("telefono_mixto", Decimal("50")),
    ("alquiler_local", Decimal("100")),
    ("suministros_local", Decimal("100")),
    ("formacion", Decimal("100")),
    ("publicidad_marketing", Decimal("100")),
    ("vehiculo_estandar", Decimal("50")),
    ("vehiculo_transportista", Decimal("100")),
    ("ropa_profesional", Decimal("100")),
    ("ropa_personal", Decimal("0")),
    ("seguro_rc_profesional", Decimal("100")),
    ("alimentacion_personal", Decimal("0")),
    ("multas_sanciones", Decimal("0")),
    ("cuota_reta", Decimal("0")),
    ("intereses_prestamo", Decimal("0")),
]


def test_tabla_deducibilidad_tiene_22_categorias():
    assert len(TABLA_DEDUCIBILIDAD) == 22


def test_tabla_deducibilidad_porcentajes_fijos():
    for categoria, porcentaje_esperado in CASOS_PORCENTAJE_FIJO:
        rule = TABLA_DEDUCIBILIDAD[categoria]
        assert rule.porcentaje == porcentaje_esperado, f"{categoria}: esperado {porcentaje_esperado}, obtenido {rule.porcentaje}"


def test_tabla_deducibilidad_todas_las_categorias_tienen_descripcion():
    for categoria, rule in TABLA_DEDUCIBILIDAD.items():
        assert rule.descripcion, f"{categoria} no tiene descripcion"


def test_tabla_deducibilidad_categorias_condicionales_especiales_presentes():
    # These 4 are rules, not fixed constants — verified structurally here,
    # behaviorally in test_calcular_deducible.py
    for categoria in ("suministros_domicilio", "combustible_vehiculo", "comida_profesional", "gastos_representacion"):
        assert categoria in TABLA_DEDUCIBILIDAD, f"falta la categoria {categoria}"
