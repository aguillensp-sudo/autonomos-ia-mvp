"""Tests for extraer_factura_ocr. Acceptance criteria: CA-F3-03.
Makes real calls to Claude Vision (ANTHROPIC_API_KEY required).
"""
from dotenv import load_dotenv

load_dotenv()

from tests.agent._fixtures_ocr import crear_imagen_factura_baja_calidad, crear_imagen_factura_clara

from src.agent.ocr import extraer_factura_ocr


def test_extraer_factura_ocr_factura_limpia_confianza_alta():
    imagen = crear_imagen_factura_clara()
    resultado = extraer_factura_ocr(imagen, tipo="emitida")

    assert resultado["nif_emisor"] == "12345678Z"
    assert resultado["confianza_nif_emisor"] > 0.8
    assert resultado["confianza_fecha"] > 0.8
    assert resultado["confianza_base_imponible"] > 0.8
    assert resultado["confianza_tipo_iva"] > 0.8


def test_extraer_factura_ocr_imagen_baja_calidad_confianza_baja():
    imagen = crear_imagen_factura_baja_calidad()
    resultado = extraer_factura_ocr(imagen, tipo="emitida")

    confianzas = [
        resultado["confianza_nif_emisor"],
        resultado["confianza_fecha"],
        resultado["confianza_base_imponible"],
        resultado["confianza_tipo_iva"],
    ]
    assert any(c < 0.8 for c in confianzas), f"esperaba al menos un campo con confianza < 0.8, obtuve {confianzas}"
