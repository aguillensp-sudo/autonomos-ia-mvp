"""SPEC-F4-05 — justificante download, verification, Storage upload.
"""
import io
import re
from typing import Any

from pypdf import PdfReader


class JustificanteNoCoincideError(Exception):
    """The downloaded justificante's own text doesn't match the values just
    submitted (NIF, modelo, ejercicio, periodo, CSV, resultado). The filing
    may have succeeded, but the artifact can't be trusted — never silently
    accepted, flagged for manual verification."""

    codigo_error = "justificante_no_coincide"


def extraer_texto_pdf(pdf_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _valor_anclado_presente(texto: str, valor: str) -> bool:
    """Anchored match: valor must appear as a complete alphanumeric token,
    not merely as a substring. Adversarial review MEDIUM-1: raw `in`
    containment let a wrong resultado sharing trailing digits with the
    correct one (e.g. expected "0.00", PDF actually shows "160.00") pass
    verification undetected, since "0.00" is a literal substring of
    "160.00". Requiring non-alphanumeric boundaries on both sides closes
    that gap for every field, not just resultado.
    """
    patron = r"(?<![A-Za-z0-9])" + re.escape(valor) + r"(?![A-Za-z0-9])"
    return re.search(patron, texto) is not None


def verificar_justificante(
    texto_pdf: str, nif: str, modelo: str, ejercicio: int, periodo: str, csv: str, resultado: str
) -> None:
    campos_esperados = {
        "nif": nif,
        "modelo": modelo,
        "ejercicio": str(ejercicio),
        "periodo": periodo,
        "csv": csv,
        "resultado": resultado,
    }
    faltantes = [nombre for nombre, valor in campos_esperados.items() if not _valor_anclado_presente(texto_pdf, valor)]
    if faltantes:
        raise JustificanteNoCoincideError(
            f"El justificante no contiene los valores esperados para: {faltantes}"
        )


def descargar_justificante(
    pdf_bytes: bytes,
    client: Any,
    user_id: str,
    ejercicio: int,
    periodo: str,
    nif: str,
    modelo: str,
    csv: str,
    resultado: str,
    nrc: str | None,
) -> str:
    """Verifies the justificante's own text matches the submitted values,
    then uploads it to Supabase Storage and updates presentacion. Never
    uploads/updates if verification fails (SPEC-F4-05).
    """
    texto = extraer_texto_pdf(pdf_bytes)
    verificar_justificante(texto, nif=nif, modelo=modelo, ejercicio=ejercicio, periodo=periodo, csv=csv, resultado=resultado)

    ruta = f"justificantes/{user_id}/{ejercicio}_{periodo}.pdf"
    client.storage.from_("justificantes").upload(ruta, pdf_bytes)

    client.table("presentacion").update({
        "estado": "presentado",
        "csv_aeat": csv,
        "nrc": nrc,
        "justificante_path": ruta,
    }).eq("user_id", user_id).eq("ejercicio", ejercicio).eq("periodo", periodo).execute()

    return ruta
