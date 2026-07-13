"""detectar_periodo — pure function of the current date, no LLM/DB call.
Acceptance criteria: CA-F3-02. Per Hoja 3 T04-01 of the P04 functional spec.

Deferred (documented, not silently omitted): the deadline-shift rule only
accounts for weekends. Spanish national holiday calendar lookup (also
required by T04-01: "sabado, domingo o festivo nacional") is not implemented
this phase — no holiday-calendar data source has been approved yet.
"""
from datetime import date, timedelta

# (month, periodo, meses_del_periodo_offset_años, dia_limite)
_VENTANAS = {
    1: ("4T", -1, (1, 1), (12, 31), (1, 30)),
    2: ("4T", -1, (1, 1), (12, 31), (1, 30)),
    3: ("4T", -1, (1, 1), (12, 31), (1, 30)),
    4: ("1T", 0, (1, 1), (3, 31), (4, 20)),
    5: ("1T", 0, (1, 1), (3, 31), (4, 20)),
    6: ("1T", 0, (1, 1), (3, 31), (4, 20)),
    7: ("2T", 0, (4, 1), (6, 30), (7, 20)),
    8: ("2T", 0, (4, 1), (6, 30), (7, 20)),
    9: ("2T", 0, (4, 1), (6, 30), (7, 20)),
    10: ("3T", 0, (7, 1), (9, 30), (10, 20)),
    11: ("3T", 0, (7, 1), (9, 30), (10, 20)),
    12: ("3T", 0, (7, 1), (9, 30), (10, 20)),
}


def _siguiente_dia_habil(fecha: date) -> date:
    """Shifts forward past Saturday/Sunday. Holiday calendar not implemented
    this phase — see module docstring."""
    while fecha.weekday() >= 5:  # 5=Saturday, 6=Sunday
        fecha += timedelta(days=1)
    return fecha


def detectar_periodo(estado: dict) -> dict:
    """Determines ejercicio/periodo/fechas from the current date. Pure
    function — takes no fiscal decision, only a calendar lookup."""
    hoy = date.today()
    periodo, offset_ejercicio, inicio_md, fin_md, limite_md = _VENTANAS[hoy.month]

    ejercicio_del_periodo = hoy.year + offset_ejercicio
    fecha_inicio = date(ejercicio_del_periodo, *inicio_md)
    fecha_fin = date(ejercicio_del_periodo, *fin_md)

    ejercicio_limite = hoy.year if periodo != "4T" else hoy.year
    fecha_limite = date(ejercicio_limite, *limite_md)
    fecha_limite = _siguiente_dia_habil(fecha_limite)

    dias_para_vencimiento = (fecha_limite - hoy).days

    return {
        "ejercicio": ejercicio_del_periodo,
        "periodo": periodo,
        "fecha_inicio_periodo": fecha_inicio.isoformat(),
        "fecha_fin_periodo": fecha_fin.isoformat(),
        "fecha_limite_presentacion": fecha_limite.isoformat(),
        "dias_para_vencimiento": dias_para_vencimiento,
    }
