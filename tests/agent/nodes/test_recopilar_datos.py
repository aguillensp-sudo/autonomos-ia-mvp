"""Tests for recopilar_datos node. Acceptance criteria: CA-F3-04, CA-F3-08.
Makes real calls to the Claude Sonnet 5 API (ANTHROPIC_API_KEY required).
"""
from dotenv import load_dotenv

load_dotenv()

from src.agent.nodes.recopilar_datos import recopilar_datos


def _estado_con_mensaje(texto: str) -> dict:
    return {
        "user_id": "user-1",
        "mensajes": [{"rol": "usuario", "contenido": texto}],
        "facturas_emitidas": [],
        "facturas_recibidas": [],
        "facturas_pendientes_ocr": [],
        "sin_actividad": None,
    }


def test_recopilar_datos_informa_presentacion_duplicada_en_primer_mensaje():
    """Blocker 3 fix (post-adversarial-review, CA-F3-09): when
    presentacion_duplicada=True, the agent's very first message must
    proactively mention the existing presentation — not silently drop the
    flag verificar_duplicado already computed."""
    estado = {
        "user_id": "user-1",
        "mensajes": [{"rol": "usuario", "contenido": "Hola, quiero presentar mi IVA de este trimestre."}],
        "facturas_emitidas": [],
        "facturas_recibidas": [],
        "facturas_pendientes_ocr": [],
        "sin_actividad": None,
        "presentacion_duplicada": True,
        "csv_presentacion_previa": "ABCD1234EFGH5678",
    }
    resultado = recopilar_datos(estado)
    mensajes = resultado.get("mensajes", [])
    assert len(mensajes) >= 1
    ultimo_mensaje_agente = mensajes[-1]
    assert ultimo_mensaje_agente["rol"] == "agente"
    assert "ABCD1234EFGH5678" in ultimo_mensaje_agente["contenido"] or "ya existe" in ultimo_mensaje_agente["contenido"].lower() or "ya presentaste" in ultimo_mensaje_agente["contenido"].lower()


def test_recopilar_datos_declarar_intencion_rectificativa_establece_estado():
    estado = {
        "user_id": "user-1",
        "mensajes": [
            {"rol": "usuario", "contenido": "Hola, quiero presentar mi IVA de este trimestre."},
            {"rol": "agente", "contenido": "Ya existe una presentación previa (CSV ABCD1234EFGH5678) para este período. ¿Quieres presentar una rectificativa?"},
            {"rol": "usuario", "contenido": "Sí, quiero hacer una rectificativa."},
        ],
        "facturas_emitidas": [],
        "facturas_recibidas": [],
        "facturas_pendientes_ocr": [],
        "sin_actividad": None,
        "presentacion_duplicada": True,
        "csv_presentacion_previa": "ABCD1234EFGH5678",
    }
    resultado = recopilar_datos(estado)
    assert resultado.get("quiere_rectificativa") is True


def test_recopilar_datos_clasifica_restaurante_requiere_confirmacion():
    estado = _estado_con_mensaje(
        "Tengo un gasto de una comida en un restaurante con un cliente, 50 euros de base más 10% de IVA, 5 euros."
    )
    resultado = recopilar_datos(estado)
    recibidas = resultado.get("facturas_recibidas", [])
    assert len(recibidas) >= 1
    factura = recibidas[0]
    assert factura["categoria_gasto"] == "comida_profesional"
    assert factura["requiere_confirmacion"] is True


def test_recopilar_datos_clasifica_software_no_requiere_confirmacion():
    estado = _estado_con_mensaje(
        "Pagué una suscripción de software profesional, 20 euros de base más 21% de IVA, 4.20 euros."
    )
    resultado = recopilar_datos(estado)
    recibidas = resultado.get("facturas_recibidas", [])
    assert len(recibidas) >= 1
    factura = recibidas[0]
    assert factura["categoria_gasto"] == "software_saas"
    assert factura["requiere_confirmacion"] is False


def test_recopilar_datos_detecta_sin_actividad():
    estado = _estado_con_mensaje(
        "No he tenido ninguna factura, ni emitida ni recibida, este trimestre. Confirmo que no ha habido ninguna operación."
    )
    resultado = recopilar_datos(estado)
    assert resultado.get("sin_actividad") is True


def test_recopilar_datos_no_declara_sin_actividad_sin_confirmacion_explicita():
    estado = _estado_con_mensaje("Todavía no he mirado mis facturas de este trimestre.")
    resultado = recopilar_datos(estado)
    assert resultado.get("sin_actividad") is not True


def test_recopilar_datos_registra_factura_emitida():
    estado = _estado_con_mensaje(
        "He emitido una factura a un cliente por 200 euros de base mas 21% de IVA, 42 euros."
    )
    resultado = recopilar_datos(estado)
    emitidas = resultado.get("facturas_emitidas", [])
    assert len(emitidas) >= 1
    assert emitidas[0]["base_imponible"] == 200


def test_procesar_bloques_respuesta_continua_tras_declarar_sin_actividad():
    """Forces the loop to continue past the declarar_sin_actividad branch
    to a subsequent block in the same response (a case the real LLM never
    produced in the tests above, but the parsing loop must still handle
    correctly if the model ever does emit tool calls after it)."""
    from unittest.mock import MagicMock

    from src.agent.nodes.recopilar_datos import _procesar_bloques_respuesta

    bloque_sin_actividad = MagicMock(type="tool_use", input={})
    bloque_sin_actividad.name = "declarar_sin_actividad"
    bloque_recibida = MagicMock(
        type="tool_use",
        input={"categoria_gasto": "software_saas", "base_imponible": 10.0, "tipo_iva": 21, "cuota_iva": 2.1, "requiere_confirmacion": False},
    )
    bloque_recibida.name = "agregar_factura_recibida"

    emitidas, recibidas, sin_actividad, quiere_rectificativa = _procesar_bloques_respuesta(
        [bloque_sin_actividad, bloque_recibida]
    )

    assert sin_actividad is True
    assert len(recibidas) == 1
    assert emitidas == []


def test_procesar_bloques_respuesta_ignora_tool_use_no_reconocido():
    """Closes branch coverage: a tool_use block whose name matches none of
    the known tools falls through silently and the loop continues."""
    from unittest.mock import MagicMock

    from src.agent.nodes.recopilar_datos import _procesar_bloques_respuesta

    bloque_desconocido = MagicMock(type="tool_use", input={})
    bloque_desconocido.name = "herramienta_no_reconocida"
    bloque_recibida = MagicMock(
        type="tool_use",
        input={"categoria_gasto": "software_saas", "base_imponible": 10.0, "tipo_iva": 21, "cuota_iva": 2.1, "requiere_confirmacion": False},
    )
    bloque_recibida.name = "agregar_factura_recibida"

    emitidas, recibidas, sin_actividad, quiere_rectificativa = _procesar_bloques_respuesta(
        [bloque_desconocido, bloque_recibida]
    )

    assert sin_actividad is None
    assert emitidas == []
    assert len(recibidas) == 1


def test_resolver_confirmaciones_ultimo_campo_ensambla_factura():
    """Blocker 1's actual fix: once the LAST requiere_confirmacion=True entry
    for a path is resolved (via the interrupt()-resume payload, not a tool
    call), the invoice must be assembled from ALL entries for that path
    (fiscal + already-accepted non-fiscal) — not left dropped in
    facturas_baja_confianza."""
    from src.agent.nodes.recopilar_datos import _resolver_confirmaciones

    baja_confianza_previa = [
        {"path": "emitidas/f1.png", "tipo": "emitida", "campo": "fecha", "valor": "2026-03-15", "confianza": 0.95, "requiere_confirmacion": False},
        {"path": "emitidas/f1.png", "tipo": "emitida", "campo": "tipo_iva", "valor": 21, "confianza": 0.9, "requiere_confirmacion": True},
        {"path": "emitidas/f1.png", "tipo": "emitida", "campo": "base_imponible", "valor": 100.0, "confianza": 0.9, "requiere_confirmacion": True},
    ]
    confirmaciones = [
        {"path": "emitidas/f1.png", "campo": "tipo_iva", "valor_confirmado": 21, "tipo": "emitida"},
        {"path": "emitidas/f1.png", "campo": "base_imponible", "valor_confirmado": 100.0, "tipo": "emitida"},
    ]

    baja_confianza, emitidas, recibidas = _resolver_confirmaciones(baja_confianza_previa, confirmaciones, "user-1")

    assert baja_confianza == []  # fully resolved and purged
    assert recibidas == []
    assert len(emitidas) == 1
    assert emitidas[0]["base_imponible"] == 100.0
    assert emitidas[0]["tipo_iva"] == 21
    assert emitidas[0]["fecha"] == "2026-03-15"
    assert emitidas[0]["user_id"] == "user-1"


def test_resolver_confirmaciones_permite_correccion():
    """The user may correct a flagged value instead of confirming the OCR
    reading verbatim — valor_confirmado does not have to equal the original
    OCR-extracted value."""
    from src.agent.nodes.recopilar_datos import _resolver_confirmaciones

    baja_confianza_previa = [
        {"path": "recibidas/f2.png", "tipo": "recibida", "campo": "base_imponible", "valor": 50.0, "confianza": 0.9, "requiere_confirmacion": True},
    ]
    confirmaciones = [
        {"path": "recibidas/f2.png", "campo": "base_imponible", "valor_confirmado": 45.0, "tipo": "recibida"},
    ]

    baja_confianza, emitidas, recibidas = _resolver_confirmaciones(baja_confianza_previa, confirmaciones, "user-1")

    assert baja_confianza == []
    assert emitidas == []
    assert len(recibidas) == 1
    assert recibidas[0]["base_imponible"] == 45.0  # corrected value, not 50.0


def test_resolver_confirmaciones_deja_pendientes_otros_campos():
    """If other requiere_confirmacion=True entries for the same path remain
    unresolved, the invoice must NOT be assembled yet."""
    from src.agent.nodes.recopilar_datos import _resolver_confirmaciones

    baja_confianza_previa = [
        {"path": "emitidas/f3.png", "tipo": "emitida", "campo": "tipo_iva", "valor": 21, "confianza": 0.9, "requiere_confirmacion": True},
        {"path": "emitidas/f3.png", "tipo": "emitida", "campo": "base_imponible", "valor": 100.0, "confianza": 0.9, "requiere_confirmacion": True},
    ]
    confirmaciones = [
        {"path": "emitidas/f3.png", "campo": "tipo_iva", "valor_confirmado": 21, "tipo": "emitida"},
    ]

    baja_confianza, emitidas, recibidas = _resolver_confirmaciones(baja_confianza_previa, confirmaciones, "user-1")

    assert emitidas == []  # base_imponible still unresolved — not assembled yet
    assert len(baja_confianza) == 2  # nothing purged until the whole invoice resolves
    pendientes = [e for e in baja_confianza if e["requiere_confirmacion"]]
    assert len(pendientes) == 1
    assert pendientes[0]["campo"] == "base_imponible"
    resuelto_tipo_iva = next(e for e in baja_confianza if e["campo"] == "tipo_iva")
    assert resuelto_tipo_iva["requiere_confirmacion"] is False


def test_resolver_confirmaciones_path_inexistente_no_ensambla_vacio():
    """Guards against a hallucinated/stale confirmation for a path with
    zero matching entries (e.g. already resolved or a model error): must
    not synthesize and append an empty invoice."""
    from src.agent.nodes.recopilar_datos import _resolver_confirmaciones

    confirmaciones = [
        {"path": "emitidas/no-existe.png", "campo": "base_imponible", "valor_confirmado": 10.0, "tipo": "emitida"},
    ]

    baja_confianza, emitidas, recibidas = _resolver_confirmaciones([], confirmaciones, "user-1")

    assert emitidas == []
    assert recibidas == []
    assert baja_confianza == []
