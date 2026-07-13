"""Claude Vision invoice extraction. Acceptance criteria: CA-F3-03.
Confidence threshold 0.8 — matches factura_emitida/factura_recibida.ocr_confidence
columns in docs/data-model.md. A field below threshold is never auto-accepted;
this module only reports confidence per field, the caller (ocr_factura node)
decides what counts as good enough.
"""
import base64

from src.agent.llm_client import crear_cliente_anthropic

_MODEL = "claude-sonnet-5"

_TOOL_EMITIDA = {
    "name": "reportar_extraccion_emitida",
    "description": "Reporta los datos extraidos de una factura emitida junto con la confianza (0.0-1.0) de cada campo.",
    "input_schema": {
        "type": "object",
        "properties": {
            "nif_emisor": {"type": ["string", "null"]},
            "confianza_nif_emisor": {"type": "number"},
            "fecha": {"type": ["string", "null"], "description": "ISO date YYYY-MM-DD"},
            "confianza_fecha": {"type": "number"},
            "base_imponible": {"type": ["number", "null"]},
            "confianza_base_imponible": {"type": "number"},
            "tipo_iva": {"type": ["integer", "null"]},
            "confianza_tipo_iva": {"type": "number"},
        },
        "required": [
            "nif_emisor", "confianza_nif_emisor", "fecha", "confianza_fecha",
            "base_imponible", "confianza_base_imponible", "tipo_iva", "confianza_tipo_iva",
        ],
    },
}

_TOOL_RECIBIDA = {
    "name": "reportar_extraccion_recibida",
    "description": "Reporta los datos extraidos de una factura recibida junto con la confianza (0.0-1.0) de cada campo.",
    "input_schema": {
        "type": "object",
        "properties": {
            "nif_proveedor": {"type": ["string", "null"]},
            "confianza_nif_proveedor": {"type": "number"},
            "fecha": {"type": ["string", "null"]},
            "confianza_fecha": {"type": "number"},
            "base_imponible": {"type": ["number", "null"]},
            "confianza_base_imponible": {"type": "number"},
            "tipo_iva": {"type": ["integer", "null"]},
            "confianza_tipo_iva": {"type": "number"},
            "categoria_gasto": {"type": ["string", "null"]},
        },
        "required": [
            "nif_proveedor", "confianza_nif_proveedor", "fecha", "confianza_fecha",
            "base_imponible", "confianza_base_imponible", "tipo_iva", "confianza_tipo_iva",
        ],
    },
}

_PROMPT = (
    "Extrae los datos de esta factura. Para cada campo, reporta tambien tu "
    "confianza real (0.0 a 1.0) en la exactitud de lo que has leido — se honesto: "
    "si el texto esta borroso, pixelado, con poco contraste, o no puedes distinguir "
    "los caracteres con certeza, la confianza de ese campo debe ser baja (< 0.8), no "
    "una estimacion optimista. Llama a la herramienta con lo que puedas leer, "
    "usando null para lo que no puedas leer en absoluto."
)


def extraer_factura_ocr(imagen_bytes: bytes, tipo: str) -> dict:
    """tipo: 'emitida' | 'recibida'. Returns a dict with the extracted fields
    and a confianza_<campo> for each. Never decides what counts as "good
    enough" — that's the calling node's job (ocr_factura)."""
    client = crear_cliente_anthropic()
    imagen_b64 = base64.standard_b64encode(imagen_bytes).decode("utf-8")
    herramienta = _TOOL_EMITIDA if tipo == "emitida" else _TOOL_RECIBIDA

    respuesta = client.messages.create(
        model=_MODEL,
        max_tokens=1024,
        tools=[herramienta],
        tool_choice={"type": "tool", "name": herramienta["name"]},
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": imagen_b64}},
                {"type": "text", "text": _PROMPT},
            ],
        }],
    )

    for bloque in respuesta.content:
        if bloque.type == "tool_use":
            return dict(bloque.input)

    raise RuntimeError("Claude Vision did not return a tool_use block for OCR extraction")
