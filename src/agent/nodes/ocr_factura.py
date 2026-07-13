"""ocr_factura — drains facturas_pendientes_ocr through Claude Vision.
Acceptance criteria: CA-F3-03.

Fiscal numeric fields (base_imponible, tipo_iva, cuota_iva) feed
calcular_m303() directly — an OCR misreading here is a wrong tax figure, not
a cosmetic error. Per Principle 1 (legal correctness before speed), these
fields ALWAYS go to facturas_baja_confianza for mandatory user confirmation,
regardless of the model's reported confidence. A confident-but-wrong OCR
reading of an amount must never reach the fiscal engine unconfirmed.

Non-fiscal fields (nif_emisor, nif_proveedor, fecha, categoria_gasto) keep
the confianza < 0.8 rule — they don't feed a tax calculation directly.

Path convention: {emitidas|recibidas}/{user_id}/{filename} (Supabase Storage).
A pending path starting with 'emitidas/' is a factura emitida; 'recibidas/'
is a factura recibida. The {user_id} segment is required by the RLS policy
on storage.objects (src/db/migrations/20260713_140000_facturas_storage_rls.sql,
post-adversarial-review Blocker 2) — see _descargar_bytes below.

Blocker 1 fix (post-adversarial-review): every extracted field — not only
the ones needing review — is stored in facturas_baja_confianza, tagged with
requiere_confirmacion. Fields accepted at high confidence (requiere_confirmacion
=False) are carried along so recopilar_datos can assemble a complete invoice
once every requiere_confirmacion=True entry for a given path is resolved via
its interrupt()-driven confirmation loop — see src/agent/nodes/recopilar_datos.py.
Dropping accepted fields (as the previous version did) left no way to
reconstruct the invoice later, which meant OCR-extracted invoices could never
actually reach the fiscal engine even after the user confirmed everything.
"""
from src.agent.ocr import extraer_factura_ocr
from src.agent.supabase_client import crear_cliente_usuario

UMBRAL_CONFIANZA = 0.8

# Fiscal amounts/rates that feed calcular_m303() — always require explicit
# user confirmation, never auto-accepted regardless of OCR confidence.
CAMPOS_FISCALES_SIEMPRE_REVISAR = {"base_imponible", "tipo_iva", "cuota_iva"}


def _descargar_bytes(path: str, user_jwt: str) -> bytes:
    client = crear_cliente_usuario(user_jwt)
    return client.storage.from_("facturas").download(path)


def _tipo_de_path(path: str) -> str:
    return "emitida" if path.startswith("emitidas/") else "recibida"


def ocr_factura(estado: dict) -> dict:
    facturas_emitidas = list(estado.get("facturas_emitidas", []))
    facturas_recibidas = list(estado.get("facturas_recibidas", []))
    facturas_baja_confianza = list(estado.get("facturas_baja_confianza", []))

    for path in estado.get("facturas_pendientes_ocr", []):
        tipo = _tipo_de_path(path)
        imagen_bytes = _descargar_bytes(path, estado["user_jwt"])
        extraccion = extraer_factura_ocr(imagen_bytes, tipo=tipo)

        campos_con_confianza = [k[len("confianza_"):] for k in extraccion if k.startswith("confianza_")]

        for campo in campos_con_confianza:
            requiere_confirmacion = (
                campo in CAMPOS_FISCALES_SIEMPRE_REVISAR
                or extraccion.get(f"confianza_{campo}", 0.0) < UMBRAL_CONFIANZA
            )
            facturas_baja_confianza.append({
                "path": path,
                "tipo": tipo,
                "campo": campo,
                "valor": extraccion.get(campo),
                "confianza": extraccion.get(f"confianza_{campo}"),
                "requiere_confirmacion": requiere_confirmacion,
            })

    return {
        "facturas_emitidas": facturas_emitidas,
        "facturas_recibidas": facturas_recibidas,
        "facturas_baja_confianza": facturas_baja_confianza,
        "facturas_pendientes_ocr": [],
    }
