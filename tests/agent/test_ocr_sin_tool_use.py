"""Covers extraer_factura_ocr's RuntimeError fallback when Claude Vision
returns no tool_use block."""
from unittest.mock import MagicMock, patch

import pytest

from src.agent.ocr import extraer_factura_ocr


@patch("src.agent.ocr.crear_cliente_anthropic")
def test_extraer_factura_ocr_sin_tool_use_lanza_error(mock_crear_cliente):
    bloque_texto = MagicMock()
    bloque_texto.type = "text"
    bloque_texto.text = "No puedo procesar esta imagen."

    respuesta_falsa = MagicMock()
    respuesta_falsa.content = [bloque_texto]

    cliente_falso = MagicMock()
    cliente_falso.messages.create.return_value = respuesta_falsa
    mock_crear_cliente.return_value = cliente_falso

    with pytest.raises(RuntimeError, match="did not return a tool_use"):
        extraer_factura_ocr(b"fake-bytes", tipo="emitida")
