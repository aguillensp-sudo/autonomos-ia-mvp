"""SPEC-F4-05: justificante download, verification, storage. Acceptance
criteria: CA-F4-09.
"""
import io
from unittest.mock import MagicMock

import pytest
from pypdf import PdfWriter

from src.rpa.aeat.justificante import (
    JustificanteNoCoincideError,
    descargar_justificante,
    extraer_texto_pdf,
    verificar_justificante,
)


def _texto_justificante_valido() -> str:
    return (
        "AGENCIA TRIBUTARIA\nModelo 303\nNIF: 12345678Z\n"
        "Ejercicio: 2026 Periodo: 1T\nCSV: ABCD1234EFGH5678\n"
        "Resultado de la liquidacion: 160.00"
    )


def test_verificar_justificante_campos_coinciden_no_lanza():
    verificar_justificante(
        texto_pdf=_texto_justificante_valido(),
        nif="12345678Z", modelo="303", ejercicio=2026, periodo="1T",
        csv="ABCD1234EFGH5678", resultado="160.00",
    )


def test_verificar_justificante_detecta_discrepancia_periodo():
    texto = _texto_justificante_valido().replace("Periodo: 1T", "Periodo: 2T")
    with pytest.raises(JustificanteNoCoincideError):
        verificar_justificante(
            texto_pdf=texto,
            nif="12345678Z", modelo="303", ejercicio=2026, periodo="1T",
            csv="ABCD1234EFGH5678", resultado="160.00",
        )


def test_verificar_justificante_detecta_discrepancia_csv():
    with pytest.raises(JustificanteNoCoincideError):
        verificar_justificante(
            texto_pdf=_texto_justificante_valido(),
            nif="12345678Z", modelo="303", ejercicio=2026, periodo="1T",
            csv="ZZZZ0000ZZZZ0000", resultado="160.00",
        )


def test_extraer_texto_pdf_no_falla_con_pdf_minimo():
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buffer = io.BytesIO()
    writer.write(buffer)
    texto = extraer_texto_pdf(buffer.getvalue())
    assert isinstance(texto, str)


def test_descargar_justificante_sube_a_storage_path_correcto_y_actualiza_presentacion(monkeypatch):
    monkeypatch.setattr(
        "src.rpa.aeat.justificante.extraer_texto_pdf",
        lambda pdf_bytes: _texto_justificante_valido(),
    )
    client = MagicMock()

    ruta = descargar_justificante(
        pdf_bytes=b"fake-pdf-bytes", client=client, user_id="u1", ejercicio=2026, periodo="1T",
        nif="12345678Z", modelo="303", csv="ABCD1234EFGH5678", resultado="160.00", nrc=None,
    )

    assert ruta == "justificantes/u1/2026_1T.pdf"
    client.storage.from_.assert_called_once_with("justificantes")
    client.storage.from_.return_value.upload.assert_called_once()

    update_kwargs = client.table.return_value.update.call_args[0][0]
    assert update_kwargs["estado"] == "presentado"
    assert update_kwargs["csv_aeat"] == "ABCD1234EFGH5678"
    assert update_kwargs["justificante_path"] == "justificantes/u1/2026_1T.pdf"


def test_descargar_justificante_discrepancia_no_sube_a_storage(monkeypatch):
    monkeypatch.setattr(
        "src.rpa.aeat.justificante.extraer_texto_pdf",
        lambda pdf_bytes: _texto_justificante_valido().replace("2026", "2099"),
    )
    client = MagicMock()

    with pytest.raises(JustificanteNoCoincideError):
        descargar_justificante(
            pdf_bytes=b"fake-pdf-bytes", client=client, user_id="u1", ejercicio=2026, periodo="1T",
            nif="12345678Z", modelo="303", csv="ABCD1234EFGH5678", resultado="160.00", nrc=None,
        )

    client.storage.from_.assert_not_called()
