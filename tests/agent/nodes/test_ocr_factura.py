"""Tests for the ocr_factura node's routing logic. Acceptance criteria: CA-F3-03.
extraer_factura_ocr itself is mocked here — its real behavior is already
covered by tests/agent/test_ocr.py; this test verifies the node never
auto-accepts a low-confidence field into facturas_emitidas/facturas_recibidas.

Mandatory contract fix (architecture review, Principle 1 — legal correctness
before speed): fiscal numeric fields (base_imponible, tipo_iva, cuota_iva)
that feed calcular_m303() ALWAYS require explicit user confirmation, even at
confidence 0.99 — a confident-but-wrong OCR reading of a tax amount must
never reach the fiscal engine unconfirmed. Non-fiscal fields (nif_emisor,
fecha, nif_proveedor, categoria_gasto) keep the confianza < 0.8 rule.

Blocker 1 fix (post-adversarial-review): every extracted field — not just
the ones needing review — is now stored in facturas_baja_confianza, tagged
with requiere_confirmacion. This is what lets recopilar_datos later assemble
a complete invoice once all requiere_confirmacion=True entries for a given
path are resolved (see tests/agent/nodes/test_recopilar_datos.py). Fields
accepted at high confidence carry requiere_confirmacion=False and never
block the graph's routing (src/agent/graph.py checks for that flag).
"""
from unittest.mock import patch

from src.agent.nodes.ocr_factura import ocr_factura


def _estado(paths):
    return {
        "facturas_pendientes_ocr": paths,
        "facturas_emitidas": [],
        "facturas_recibidas": [],
        "facturas_baja_confianza": [],
        "user_jwt": "fake-jwt-not-used-because-_descargar_bytes-is-mocked",
    }


def _entradas_por_campo(resultado):
    return {c["campo"]: c for c in resultado["facturas_baja_confianza"]}


@patch("src.agent.nodes.ocr_factura._descargar_bytes", return_value=b"fake-image-bytes")
@patch("src.agent.nodes.ocr_factura.extraer_factura_ocr")
def test_ocr_factura_node_marca_baja_confianza_para_revision(mock_extraer, _mock_descargar):
    mock_extraer.return_value = {
        "nif_emisor": "12345678Z", "confianza_nif_emisor": 0.95,
        "fecha": "2026-03-15", "confianza_fecha": 0.4,  # low confidence, non-fiscal
        "base_imponible": 100.0, "confianza_base_imponible": 0.9,
        "tipo_iva": 21, "confianza_tipo_iva": 0.9,
    }

    resultado = ocr_factura(_estado(["emitidas/factura1.png"]))

    assert resultado["facturas_emitidas"] == []  # never auto-accepted
    entradas = _entradas_por_campo(resultado)
    assert entradas["fecha"]["requiere_confirmacion"] is True  # genuinely low confidence
    assert resultado["facturas_pendientes_ocr"] == []  # drained


@patch("src.agent.nodes.ocr_factura._descargar_bytes", return_value=b"fake-image-bytes")
@patch("src.agent.nodes.ocr_factura.extraer_factura_ocr")
def test_ocr_factura_node_campos_fiscales_siempre_requieren_confirmacion(mock_extraer, _mock_descargar):
    """Even with 0.99 confidence on every field, base_imponible and tipo_iva
    must still be flagged for mandatory review — they feed calcular_m303()."""
    mock_extraer.return_value = {
        "nif_emisor": "12345678Z", "confianza_nif_emisor": 0.99,
        "fecha": "2026-03-15", "confianza_fecha": 0.99,
        "base_imponible": 100.0, "confianza_base_imponible": 0.99,
        "tipo_iva": 21, "confianza_tipo_iva": 0.99,
    }

    resultado = ocr_factura(_estado(["emitidas/factura1.png"]))

    assert resultado["facturas_emitidas"] == []  # never auto-accepted
    entradas = _entradas_por_campo(resultado)
    assert entradas["base_imponible"]["requiere_confirmacion"] is True
    assert entradas["tipo_iva"]["requiere_confirmacion"] is True
    # Non-fiscal fields with genuinely high confidence are stored (for later
    # invoice assembly) but do NOT require confirmation.
    assert entradas["nif_emisor"]["requiere_confirmacion"] is False
    assert entradas["fecha"]["requiere_confirmacion"] is False


@patch("src.agent.nodes.ocr_factura._descargar_bytes", return_value=b"fake-image-bytes")
@patch("src.agent.nodes.ocr_factura.extraer_factura_ocr")
def test_ocr_factura_node_procesa_recibida(mock_extraer, _mock_descargar):
    mock_extraer.return_value = {
        "nif_proveedor": "12345678Z", "confianza_nif_proveedor": 0.95,
        "fecha": "2026-03-15", "confianza_fecha": 0.9,
        "base_imponible": 50.0, "confianza_base_imponible": 0.9,
        "tipo_iva": 21, "confianza_tipo_iva": 0.9,
        "categoria_gasto": "software_saas",
    }
    resultado = ocr_factura(_estado(["recibidas/factura1.png"]))
    # Fiscal fields still mandatory-review even for facturas_recibidas
    assert resultado["facturas_recibidas"] == []
    entradas = _entradas_por_campo(resultado)
    assert entradas["base_imponible"]["requiere_confirmacion"] is True
    assert entradas["tipo_iva"]["requiere_confirmacion"] is True
    assert entradas["nif_proveedor"]["requiere_confirmacion"] is False
    # categoria_gasto has no confianza_categoria_gasto pair in the OCR schema
    # (it's a categorization, not something read with confidence) — it is not
    # tracked per-field here and is out of scope for this fix.
