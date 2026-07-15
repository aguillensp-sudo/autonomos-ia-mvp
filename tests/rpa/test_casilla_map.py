"""SPEC-F4-03: casilla mapping adapter. Pure function, no I/O, no new fiscal
arithmetic — reshapes already-computed ResultadoM303/ResultadoDevengado/
ResultadoDeducible values into the full AEAT-form casilla dict.
Acceptance criteria: CA-F4-03, CA-F4-04, CA-F4-05, supports CA-F4-06.
"""
from decimal import Decimal

from src.fiscal.models import ResultadoDeducible, ResultadoDevengado, ResultadoM303
from src.rpa.casilla_map import TABLA_CASILLA_DEDUCIBLE, construir_mapa_casillas


def _resultado(
    devengado: ResultadoDevengado | None = None,
    deducible: ResultadoDeducible | None = None,
    tipo_resultado: str = "a_ingresar",
    casillas: dict | None = None,
) -> ResultadoM303:
    return ResultadoM303(
        ejercicio=2026,
        periodo="1T",
        total_devengado=devengado.total if devengado else Decimal("0.00"),
        total_deducible=deducible.total if deducible else Decimal("0.00"),
        saldo_compensar_anterior=Decimal("0.00"),
        resultado=Decimal("0.00"),
        tipo_resultado=tipo_resultado,
        casillas=casillas or {},
        devengado=devengado,
        deducible=deducible,
    )


def test_construir_mapa_casillas_devengado_solo_21_deja_otros_tipos_sin_fijar():
    devengado = ResultadoDevengado(
        por_tipo={21: Decimal("1000.00")},
        cuotas={21: Decimal("210.00")},
        total=Decimal("210.00"),
    )
    mapa = construir_mapa_casillas(_resultado(devengado=devengado, casillas={"27": Decimal("210.00")}))

    assert mapa["07"] == Decimal("1000.00")
    assert mapa["08"] == Decimal("21")
    assert mapa["09"] == Decimal("210.00")
    for casilla in ("01", "02", "03", "04", "05", "06", "150", "151", "152"):
        assert casilla not in mapa, f"casilla {casilla} no debe fijarse cuando no hay operaciones a ese tipo"


def test_construir_mapa_casillas_devengado_multiples_tipos():
    devengado = ResultadoDevengado(
        por_tipo={4: Decimal("500.00"), 21: Decimal("1000.00")},
        cuotas={4: Decimal("20.00"), 21: Decimal("210.00")},
        total=Decimal("230.00"),
    )
    mapa = construir_mapa_casillas(_resultado(devengado=devengado, casillas={"27": Decimal("230.00")}))

    assert mapa["01"] == Decimal("500.00")
    assert mapa["03"] == Decimal("20.00")
    assert mapa["07"] == Decimal("1000.00")
    assert mapa["09"] == Decimal("210.00")


def test_construir_mapa_casillas_isp_casillas_12_13_distintas_de_regimen_general():
    devengado = ResultadoDevengado(
        por_tipo={21: Decimal("800.00")},
        cuotas={21: Decimal("168.00")},
        total=Decimal("176.40"),
    )
    mapa = construir_mapa_casillas(_resultado(
        devengado=devengado,
        casillas={"27": Decimal("176.40"), "12": Decimal("40.00"), "13": Decimal("8.40")},
    ))

    assert mapa["12"] == Decimal("40.00")
    assert mapa["13"] == Decimal("8.40")
    assert mapa["07"] == Decimal("800.00")
    assert mapa["09"] == Decimal("168.00")


def test_construir_mapa_casillas_modificacion_rectificativa_casillas_14_15():
    devengado = ResultadoDevengado(
        por_tipo={21: Decimal("1000.00")},
        cuotas={21: Decimal("210.00")},
        base_modificacion=Decimal("-100.00"),
        cuota_modificacion=Decimal("-21.00"),
        total=Decimal("189.00"),
    )
    mapa = construir_mapa_casillas(_resultado(devengado=devengado, casillas={"27": Decimal("189.00")}))

    assert mapa["14"] == Decimal("-100.00")
    assert mapa["15"] == Decimal("-21.00")
    assert mapa["27"] == Decimal("189.00") == devengado.cuotas[21] + devengado.cuota_modificacion


def test_construir_mapa_casillas_modificacion_ausente_no_fija_14_15():
    devengado = ResultadoDevengado(
        por_tipo={21: Decimal("1000.00")},
        cuotas={21: Decimal("210.00")},
        total=Decimal("210.00"),
    )
    mapa = construir_mapa_casillas(_resultado(devengado=devengado, casillas={"27": Decimal("210.00")}))
    assert "14" not in mapa
    assert "15" not in mapa


def test_construir_mapa_casillas_deducible_corriente_default():
    deducible = ResultadoDeducible(
        por_categoria={"cuota_reta": Decimal("0.00"), "multas_sanciones": Decimal("0.00")},
        base_por_categoria={"cuota_reta": Decimal("300.00"), "multas_sanciones": Decimal("50.00")},
        total=Decimal("0.00"),
    )
    mapa = construir_mapa_casillas(_resultado(deducible=deducible, casillas={"45": Decimal("0.00")}))

    assert mapa["28"] == Decimal("350.00")
    assert mapa["29"] == Decimal("0.00")
    for casilla in ("30", "31", "32", "33", "34", "35", "36", "37"):
        assert casilla not in mapa


def test_construir_mapa_casillas_deducible_grupos_explicitos():
    deducible = ResultadoDeducible(
        por_categoria={
            "software_saas": Decimal("21.00"),
            "equipo_informatico_exclusivo": Decimal("189.00"),
            "vehiculo_estandar": Decimal("21.00"),
        },
        base_por_categoria={
            "software_saas": Decimal("100.00"),
            "equipo_informatico_exclusivo": Decimal("900.00"),
            "vehiculo_estandar": Decimal("100.00"),
        },
        total=Decimal("231.00"),
    )
    mapa = construir_mapa_casillas(_resultado(deducible=deducible, casillas={"45": Decimal("231.00")}))

    # corriente interior (28-29): software_saas
    assert mapa["28"] == Decimal("100.00")
    assert mapa["29"] == Decimal("21.00")
    # bienes de inversion interiores (30-31): equipo_informatico_exclusivo + vehiculo_estandar
    assert mapa["30"] == Decimal("1000.00")
    assert mapa["31"] == Decimal("210.00")


def test_construir_mapa_casillas_devengado_ignora_tipo_con_base_cero():
    devengado = ResultadoDevengado(
        por_tipo={21: Decimal("1000.00"), 10: Decimal("0.00")},
        cuotas={21: Decimal("210.00"), 10: Decimal("0.00")},
        total=Decimal("210.00"),
    )
    mapa = construir_mapa_casillas(_resultado(devengado=devengado, casillas={"27": Decimal("210.00")}))
    assert "04" not in mapa
    assert "05" not in mapa
    assert "06" not in mapa


def test_construir_mapa_casillas_deducible_ignora_categoria_base_y_cuota_cero():
    deducible = ResultadoDeducible(
        por_categoria={"comida_profesional": Decimal("0.00")},
        base_por_categoria={"comida_profesional": Decimal("0.00")},
        total=Decimal("0.00"),
    )
    mapa = construir_mapa_casillas(_resultado(deducible=deducible, casillas={"45": Decimal("0.00")}))
    assert "28" not in mapa
    assert "29" not in mapa


def test_construir_mapa_casillas_saldo_compensar_anterior_no_cero():
    mapa = construir_mapa_casillas(_resultado(
        tipo_resultado="a_compensar",
        casillas={"27": Decimal("50.00"), "45": Decimal("210.00"), "70": Decimal("-160.00"), "110": Decimal("30.00")},
    ))
    assert mapa["110"] == Decimal("30.00")


def test_tabla_casilla_deducible_grupos_esperados():
    assert TABLA_CASILLA_DEDUCIBLE["software_saas"] == "corriente"
    assert TABLA_CASILLA_DEDUCIBLE["equipo_informatico_exclusivo"] == "inversion"
    assert TABLA_CASILLA_DEDUCIBLE["vehiculo_estandar"] == "inversion"
    assert TABLA_CASILLA_DEDUCIBLE["vehiculo_transportista"] == "inversion"
    assert TABLA_CASILLA_DEDUCIBLE["combustible_vehiculo"] == "inversion"
    for categoria in (
        "material_oficina", "servicios_profesionales", "telefono_mixto", "alquiler_local",
        "suministros_local", "suministros_domicilio", "formacion", "publicidad_marketing",
        "seguro_rc_profesional", "comida_profesional", "ropa_profesional", "gastos_representacion",
        "cuota_reta", "intereses_prestamo", "alimentacion_personal", "multas_sanciones", "ropa_personal",
    ):
        assert TABLA_CASILLA_DEDUCIBLE[categoria] == "corriente"


def test_construir_mapa_casillas_resultado_a_ingresar():
    mapa = construir_mapa_casillas(_resultado(
        tipo_resultado="a_ingresar",
        casillas={"27": Decimal("210.00"), "45": Decimal("50.00"), "70": Decimal("160.00")},
    ))
    assert mapa["27"] == Decimal("210.00")
    assert mapa["45"] == Decimal("50.00")
    assert mapa["69"] == Decimal("160.00")
    assert mapa["71"] == Decimal("160.00")
    assert "72" not in mapa
    assert "110" not in mapa or mapa["110"] == Decimal("0.00")


def test_construir_mapa_casillas_resultado_a_compensar():
    mapa = construir_mapa_casillas(_resultado(
        tipo_resultado="a_compensar",
        casillas={"27": Decimal("50.00"), "45": Decimal("210.00"), "70": Decimal("-160.00")},
    ))
    assert mapa["69"] == Decimal("-160.00")
    assert "71" not in mapa
    assert "72" not in mapa


def test_construir_mapa_casillas_resultado_a_devolver():
    mapa = construir_mapa_casillas(_resultado(
        tipo_resultado="a_devolver",
        casillas={"27": Decimal("50.00"), "45": Decimal("210.00"), "70": Decimal("-160.00"), "72": Decimal("160.00")},
    ))
    assert mapa["69"] == Decimal("-160.00")
    assert mapa["72"] == Decimal("160.00")
    assert "71" not in mapa


def test_construir_mapa_casillas_sin_actividad():
    mapa = construir_mapa_casillas(_resultado(
        tipo_resultado="sin_actividad",
        casillas={"27": Decimal("0.00"), "45": Decimal("0.00"), "70": Decimal("0.00")},
    ))
    assert mapa["69"] == Decimal("0.00")
    assert "71" not in mapa
    assert "72" not in mapa


def test_construir_mapa_casillas_bloque_informativo_solo_positivos():
    mapa = construir_mapa_casillas(_resultado(
        casillas={"59": Decimal("1000.00"), "60": Decimal("0.00"), "61": Decimal("0.00"), "62": Decimal("2000.00")},
    ))
    assert mapa["59"] == Decimal("1000.00")
    assert mapa["62"] == Decimal("2000.00")
    assert "60" not in mapa
    assert "61" not in mapa


def test_construir_mapa_casillas_no_reimplementa_aritmetica_fiscal():
    """Every value in the map must trace back verbatim to an already-computed
    ResultadoM303/ResultadoDevengado/ResultadoDeducible field, or be a
    documented additive rollup of such values (e.g. summing two categories
    already scaled by Phase 2) — never a new base*tipo or similar fiscal
    computation performed inside casilla_map.py."""
    devengado = ResultadoDevengado(
        por_tipo={21: Decimal("1000.00")}, cuotas={21: Decimal("210.00")}, total=Decimal("210.00"),
    )
    deducible = ResultadoDeducible(
        por_categoria={"software_saas": Decimal("21.00")},
        base_por_categoria={"software_saas": Decimal("100.00")},
        total=Decimal("21.00"),
    )
    mapa = construir_mapa_casillas(_resultado(devengado=devengado, deducible=deducible, casillas={"27": Decimal("210.00"), "45": Decimal("21.00")}))
    assert mapa["07"] == devengado.por_tipo[21]
    assert mapa["09"] == devengado.cuotas[21]
    assert mapa["28"] == deducible.base_por_categoria["software_saas"]
    assert mapa["29"] == deducible.por_categoria["software_saas"]
