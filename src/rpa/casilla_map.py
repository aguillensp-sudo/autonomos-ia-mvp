"""SPEC-F4-03 — casilla mapping adapter. Pure function, no I/O, no new
fiscal arithmetic: reshapes already-computed Decimal values from
ResultadoM303/ResultadoDevengado/ResultadoDeducible (all Phase 2,
src/fiscal/models.py) into the full AEAT-form casilla dict Phase 4's
m303_form.py needs. Never reopens Phase 2's arithmetic.

TABLA_CASILLA_DEDUCIBLE is DATA, not logic — mirrors
src/fiscal/iva/tabla_deducibilidad.py's philosophy. Update this file when new
categoria_gasto values are added, never hunt through m303_form.py.
Product-Owner-approved mapping (see design.md SPEC-F4-03).
"""
from decimal import Decimal

from src.fiscal.models import ResultadoM303

_RATE_CASILLAS: dict[int, tuple[str, str, str]] = {
    0: ("150", "151", "152"),
    4: ("01", "02", "03"),
    10: ("04", "05", "06"),
    21: ("07", "08", "09"),
}

TABLA_CASILLA_DEDUCIBLE: dict[str, str] = {
    # corriente interior (28-29) — default group
    "software_saas": "corriente",
    "material_oficina": "corriente",
    "servicios_profesionales": "corriente",
    "telefono_mixto": "corriente",
    "alquiler_local": "corriente",
    "suministros_local": "corriente",
    "suministros_domicilio": "corriente",
    "formacion": "corriente",
    "publicidad_marketing": "corriente",
    "seguro_rc_profesional": "corriente",
    "comida_profesional": "corriente",
    "ropa_profesional": "corriente",
    "gastos_representacion": "corriente",
    "cuota_reta": "corriente",
    "intereses_prestamo": "corriente",
    "alimentacion_personal": "corriente",
    "multas_sanciones": "corriente",
    "ropa_personal": "corriente",
    # bienes de inversion interiores (30-31)
    "equipo_informatico_exclusivo": "inversion",
    "vehiculo_estandar": "inversion",
    "vehiculo_transportista": "inversion",
    "combustible_vehiculo": "inversion",
}

_GRUPO_DEDUCIBLE_CASILLAS: dict[str, tuple[str, str]] = {
    "corriente": ("28", "29"),
    "inversion": ("30", "31"),
}


def construir_mapa_casillas(resultado: ResultadoM303) -> dict[str, Decimal]:
    """Derives every AEAT-form casilla from an already-computed ResultadoM303.
    Only rates/categories present with a non-zero base are set — inapplicable
    fields are left unset (never written as 0), per T04-20's explicit
    warning: the form-filling step (SPEC-F4-04) must leave those fields
    blank, not zero-filled.
    """
    mapa: dict[str, Decimal] = {}

    if resultado.devengado is not None:
        for tipo, base in resultado.devengado.por_tipo.items():
            if base == Decimal("0.00"):
                continue
            casilla_base, casilla_tipo, casilla_cuota = _RATE_CASILLAS[tipo]
            mapa[casilla_base] = base
            mapa[casilla_tipo] = Decimal(tipo)
            mapa[casilla_cuota] = resultado.devengado.cuotas[tipo]

        if resultado.devengado.cuota_modificacion != Decimal("0.00"):
            mapa["14"] = resultado.devengado.base_modificacion
            mapa["15"] = resultado.devengado.cuota_modificacion

    if resultado.deducible is not None:
        for categoria, cuota in resultado.deducible.por_categoria.items():
            base = resultado.deducible.base_por_categoria.get(categoria, Decimal("0.00"))
            if base == Decimal("0.00") and cuota == Decimal("0.00"):
                continue
            grupo = TABLA_CASILLA_DEDUCIBLE.get(categoria, "corriente")
            casilla_base, casilla_cuota = _GRUPO_DEDUCIBLE_CASILLAS[grupo]
            mapa[casilla_base] = mapa.get(casilla_base, Decimal("0.00")) + base
            mapa[casilla_cuota] = mapa.get(casilla_cuota, Decimal("0.00")) + cuota

    for casilla in ("12", "13", "27", "45"):
        if casilla in resultado.casillas:
            mapa[casilla] = resultado.casillas[casilla]

    mapa["69"] = resultado.casillas.get("70", resultado.resultado)
    if resultado.tipo_resultado == "a_ingresar":
        mapa["71"] = mapa["69"]
    elif resultado.tipo_resultado == "a_devolver":
        mapa["72"] = resultado.casillas.get("72", abs(mapa["69"]))

    if "110" in resultado.casillas and resultado.casillas["110"] != Decimal("0.00"):
        mapa["110"] = resultado.casillas["110"]

    for casilla in ("59", "60", "61", "62", "63"):
        valor = resultado.casillas.get(casilla)
        if valor is not None and valor != Decimal("0.00"):
            mapa[casilla] = valor

    return mapa
