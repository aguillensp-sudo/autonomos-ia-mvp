"""SPEC-F5-03: next-quarter alert scheduling. Acceptance criteria: CA-F5-07.
Pure date arithmetic + one Supabase insert — mocked client, no real DB call.
"""
from datetime import date
from unittest.mock import MagicMock

from src.fiscal.alertas.programar_siguiente_trimestre import programar_alerta_siguiente_trimestre


def test_programar_alerta_siguiente_trimestre_1t_a_2t():
    client = MagicMock()
    programar_alerta_siguiente_trimestre(client, user_id="u1", ejercicio=2026, periodo="1T")

    client.table.assert_called_with("alerta")
    fila = client.table.return_value.insert.call_args[0][0]
    assert fila["ejercicio"] == 2026
    assert fila["periodo"] == "2T"
    assert fila["fecha_limite"] == date(2026, 7, 20).isoformat()
    assert fila["fecha_alerta"] == date(2026, 7, 5).isoformat()
    assert fila["tipo"] == "vencimiento_m303"
    assert fila["proceso"] == "P04"


def test_programar_alerta_siguiente_trimestre_2t_a_3t():
    client = MagicMock()
    programar_alerta_siguiente_trimestre(client, user_id="u1", ejercicio=2026, periodo="2T")

    fila = client.table.return_value.insert.call_args[0][0]
    assert fila["periodo"] == "3T"
    assert fila["ejercicio"] == 2026
    assert fila["fecha_limite"] == date(2026, 10, 20).isoformat()


def test_programar_alerta_siguiente_trimestre_3t_a_4t():
    client = MagicMock()
    programar_alerta_siguiente_trimestre(client, user_id="u1", ejercicio=2026, periodo="3T")

    fila = client.table.return_value.insert.call_args[0][0]
    assert fila["periodo"] == "4T"
    assert fila["ejercicio"] == 2026
    # Jan 30 2027 is a Saturday -> shifts to the next business day, Monday Feb 1
    assert fila["fecha_limite"] == date(2027, 2, 1).isoformat()


def test_programar_alerta_siguiente_trimestre_4t_a_1t_ano_siguiente():
    client = MagicMock()
    programar_alerta_siguiente_trimestre(client, user_id="u1", ejercicio=2026, periodo="4T")

    fila = client.table.return_value.insert.call_args[0][0]
    assert fila["periodo"] == "1T"
    assert fila["ejercicio"] == 2027
    assert fila["fecha_limite"] == date(2027, 4, 20).isoformat()


def test_programar_alerta_desplaza_fin_de_semana():
    """2025 -> 2T deadline July 20 2025 is a Sunday; must shift to Monday 21."""
    client = MagicMock()
    programar_alerta_siguiente_trimestre(client, user_id="u1", ejercicio=2025, periodo="1T")

    fila = client.table.return_value.insert.call_args[0][0]
    assert date.fromisoformat(fila["fecha_limite"]).weekday() < 5
