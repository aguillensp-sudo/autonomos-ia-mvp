"""Tests for detectar_periodo node. Acceptance criteria: CA-F3-02.
Per Hoja 3 T04-01: abril -> 1T, julio -> 2T, octubre -> 3T, enero -> 4T (ano anterior).
"""
from datetime import date
from unittest.mock import patch

from src.agent.nodes.detectar_periodo import detectar_periodo


def _estado_base():
    return {"user_id": "user-1", "thread_id": "user-1:P04:pending"}


@patch("src.agent.nodes.detectar_periodo.date")
def test_detectar_periodo_abril_detecta_1t(mock_date):
    mock_date.today.return_value = date(2026, 4, 15)
    mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
    resultado = detectar_periodo(_estado_base())
    assert resultado["periodo"] == "1T"
    assert resultado["ejercicio"] == 2026


@patch("src.agent.nodes.detectar_periodo.date")
def test_detectar_periodo_julio_detecta_2t(mock_date):
    mock_date.today.return_value = date(2026, 7, 10)
    mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
    resultado = detectar_periodo(_estado_base())
    assert resultado["periodo"] == "2T"
    assert resultado["ejercicio"] == 2026


@patch("src.agent.nodes.detectar_periodo.date")
def test_detectar_periodo_octubre_detecta_3t(mock_date):
    mock_date.today.return_value = date(2026, 10, 5)
    mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
    resultado = detectar_periodo(_estado_base())
    assert resultado["periodo"] == "3T"
    assert resultado["ejercicio"] == 2026


@patch("src.agent.nodes.detectar_periodo.date")
def test_detectar_periodo_enero_detecta_4t_ano_anterior(mock_date):
    mock_date.today.return_value = date(2027, 1, 10)
    mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
    resultado = detectar_periodo(_estado_base())
    assert resultado["periodo"] == "4T"
    assert resultado["ejercicio"] == 2026  # previous year, per CA-F3-02


@patch("src.agent.nodes.detectar_periodo.date")
def test_detectar_periodo_fechas_calculadas(mock_date):
    mock_date.today.return_value = date(2026, 4, 15)
    mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
    resultado = detectar_periodo(_estado_base())
    assert resultado["fecha_inicio_periodo"] == "2026-01-01"
    assert resultado["fecha_fin_periodo"] == "2026-03-31"
    assert resultado["fecha_limite_presentacion"] == "2026-04-20"
    assert isinstance(resultado["dias_para_vencimiento"], int)


@patch("src.agent.nodes.detectar_periodo.date")
def test_detectar_periodo_desplaza_fin_de_semana(mock_date):
    # 2027-04-20 is a Tuesday (no shift needed) — pick a year where the 20th
    # falls on a weekend to verify the shift. 2025-04-20 was a Sunday.
    mock_date.today.return_value = date(2025, 4, 10)
    mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
    resultado = detectar_periodo(_estado_base())
    # 2025-04-20 is Sunday -> shifts to Monday 2025-04-21
    assert resultado["fecha_limite_presentacion"] == "2025-04-21"
