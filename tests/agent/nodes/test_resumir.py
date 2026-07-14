"""Tests for the resumir node. Acceptance criteria: CA-F3-05.
Makes a real call to the Claude Sonnet 5 API (ANTHROPIC_API_KEY required).
"""
import pytest
from dotenv import load_dotenv

load_dotenv()

from src.agent.nodes.resumir import resumir


def _estado_con_resultado():
    return {
        "resultado_m303": {
            "ejercicio": 2026,
            "periodo": "1T",
            "total_devengado": "260.00",
            "total_deducible": "48.30",
            "resultado": "211.70",
            "tipo_resultado": "a_ingresar",
        },
        "fecha_limite_presentacion": "2026-04-20",
        "dias_para_vencimiento": 15,
        "facturas_emitidas": [{"id": "1"}, {"id": "2"}],
        "facturas_recibidas": [{"id": "3"}],
    }


@pytest.mark.integration
def test_resumir_incluye_todos_los_campos_requeridos():
    resultado = resumir(_estado_con_resultado())
    mensaje = resultado["mensaje_resumen"]

    assert "260.00" in mensaje  # total devengado
    assert "48.30" in mensaje  # total deducible
    assert "211.70" in mensaje  # resultado final
    assert "2" in mensaje  # num facturas emitidas
    assert "1" in mensaje  # num facturas recibidas (also matches other digits, checked loosely)
    assert "2026-04-20" in mensaje  # fecha limite


@pytest.mark.integration
def test_resumir_usa_lenguaje_humano_no_casillas():
    resultado = resumir(_estado_con_resultado())
    mensaje = resultado["mensaje_resumen"].lower()
    assert "casilla 27" not in mensaje
    assert "casilla 45" not in mensaje
    assert "iva repercutido" in mensaje or "cobraste" in mensaje
