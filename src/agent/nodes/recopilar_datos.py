"""recopilar_datos — resolves OCR-flagged facturas_baja_confianza via a
real interrupt() loop (Blocker 1's actual fix, per the second adversarial-
review's CRITICAL finding — see specs/agente-conversacional/design.md
SPEC-F3-02 amendment and SPEC-F3-06 "Interrupt in a loop"), then makes a
Claude Sonnet 5 call using the P04 system prompt for the normal
conversational turn. Acceptance criteria: CA-F3-03, CA-F3-04, CA-F3-06,
CA-F3-08.

The interrupt() loop runs BEFORE the Claude Sonnet 5 call, never after and
never inside a graph self-edge — a bare conditional self-edge is not a
LangGraph pause point and previously caused a GraphRecursionError after
10,000+ redundant LLM calls. Confirming a flagged OCR field is a
structural gate now (like confirmar's own gate on confirmado), not an LLM
tool call the model could simply skip — confirmar_factura_baja_confianza
has been removed accordingly.

Uses Anthropic tool calling so classification decisions (deductibility
category, requiere_confirmacion, sin_actividad) come back as structured
data, never parsed from free text. The LLM never computes a euro amount
itself — every numeric field it reports came verbatim from the user's
message; the deterministic fiscal engine (src/fiscal/) does all arithmetic
downstream in the calcular node.
"""
from uuid import uuid4

from langgraph.types import interrupt

from src.agent.llm_client import crear_cliente_anthropic
from src.agent.prompts.p04_system_prompt import construir_system_prompt

_MODEL = "claude-sonnet-5"

_TOOLS = [
    {
        "name": "agregar_factura_emitida",
        "description": "Registra una factura emitida (venta) descrita por el usuario.",
        "input_schema": {
            "type": "object",
            "properties": {
                "base_imponible": {"type": "number"},
                "tipo_iva": {"type": "integer", "enum": [0, 4, 10, 21]},
                "cuota_iva": {"type": "number"},
                "nif_cliente": {"type": "string"},
            },
            "required": ["base_imponible", "tipo_iva", "cuota_iva"],
        },
    },
    {
        "name": "agregar_factura_recibida",
        "description": (
            "Registra una factura recibida (gasto) descrita por el usuario, "
            "clasificando su categoria_gasto segun la tabla de deducibilidad "
            "del system prompt y marcando requiere_confirmacion=True para las "
            "categorias dudosas listadas ahi."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "categoria_gasto": {"type": "string"},
                "base_imponible": {"type": "number"},
                "tipo_iva": {"type": "integer", "enum": [0, 4, 10, 21]},
                "cuota_iva": {"type": "number"},
                "requiere_confirmacion": {"type": "boolean"},
                "nif_proveedor": {"type": "string"},
            },
            "required": ["categoria_gasto", "base_imponible", "tipo_iva", "cuota_iva", "requiere_confirmacion"],
        },
    },
    {
        "name": "declarar_sin_actividad",
        "description": (
            "Se llama SOLO despues de que el usuario confirme explicitamente "
            "que no hubo ninguna factura (emitida ni recibida) este trimestre."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "declarar_intencion_rectificativa",
        "description": (
            "Se llama SOLO cuando ya se informo al usuario de que existe una "
            "presentacion previa para este periodo (presentacion_duplicada=True) "
            "y el usuario respondio explicitamente si quiere o no presentar una "
            "rectificativa. No presenta nada — solo registra la intencion."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"quiere_rectificativa": {"type": "boolean"}},
            "required": ["quiere_rectificativa"],
        },
    },
]


def _resolver_confirmaciones(
    baja_confianza: list[dict], confirmaciones: list[dict], user_id: str | None
) -> tuple[list[dict], list[dict], list[dict]]:
    """Applies interrupt()-resume confirmations to baja_confianza. Pure and
    independently testable. Once every requiere_confirmacion=True entry for
    a given path is resolved, assembles the invoice from ALL entries for
    that path (fiscal + already-accepted non-fiscal fields) and returns it
    for the caller to append to facturas_emitidas/facturas_recibidas.
    Returns (baja_confianza_actualizado, nuevas_emitidas, nuevas_recibidas).
    """
    baja_confianza = [dict(e) for e in baja_confianza]
    nuevas_emitidas: list[dict] = []
    nuevas_recibidas: list[dict] = []

    for c in confirmaciones:
        path, campo, tipo = c["path"], c["campo"], c["tipo"]

        for entrada in baja_confianza:
            if entrada["path"] == path and entrada["campo"] == campo:
                entrada["valor"] = c["valor_confirmado"]
                entrada["requiere_confirmacion"] = False
                break

        entradas_mismo_path = [e for e in baja_confianza if e["path"] == path]
        pendientes_mismo_path = [e for e in entradas_mismo_path if e["requiere_confirmacion"]]
        # entradas_mismo_path guards against a hallucinated/stale confirmation
        # for a path with zero matching entries — never assemble an empty invoice.
        if entradas_mismo_path and not pendientes_mismo_path:
            factura = {e["campo"]: e["valor"] for e in entradas_mismo_path}
            factura["id"] = str(uuid4())
            factura["user_id"] = user_id
            if tipo == "emitida":
                factura["numero_factura"] = f"OCR-{uuid4().hex[:8]}"
                nuevas_emitidas.append(factura)
            else:
                nuevas_recibidas.append(factura)
            baja_confianza = [e for e in baja_confianza if e["path"] != path]

    return baja_confianza, nuevas_emitidas, nuevas_recibidas


def _procesar_bloques_respuesta(
    bloques,
) -> tuple[list[dict], list[dict], bool | None, bool | None]:
    """Pure parsing of the tool_use blocks in an Anthropic response's
    content list, for the normal conversational turn. facturas_baja_confianza
    confirmation no longer flows through here — see the interrupt() loop in
    recopilar_datos()."""
    nuevas_emitidas: list[dict] = []
    nuevas_recibidas: list[dict] = []
    sin_actividad = None
    quiere_rectificativa = None

    for bloque in bloques:
        if bloque.type != "tool_use":
            continue
        if bloque.name == "agregar_factura_emitida":
            nuevas_emitidas.append(dict(bloque.input))
        elif bloque.name == "agregar_factura_recibida":
            nuevas_recibidas.append(dict(bloque.input))
        elif bloque.name == "declarar_sin_actividad":
            sin_actividad = True
        elif bloque.name == "declarar_intencion_rectificativa":
            quiere_rectificativa = bloque.input["quiere_rectificativa"]

    return nuevas_emitidas, nuevas_recibidas, sin_actividad, quiere_rectificativa


def recopilar_datos(estado: dict) -> dict:
    baja_confianza = [dict(e) for e in estado.get("facturas_baja_confianza", [])]
    facturas_emitidas = list(estado.get("facturas_emitidas", []))
    facturas_recibidas = list(estado.get("facturas_recibidas", []))
    user_id = estado.get("user_id")
    habia_pendientes = any(e["requiere_confirmacion"] for e in baja_confianza)

    while any(e["requiere_confirmacion"] for e in baja_confianza):
        pendientes = [e for e in baja_confianza if e["requiere_confirmacion"]]
        respuesta = interrupt({"tipo": "confirmacion_baja_confianza", "pendientes": pendientes})
        baja_confianza, nuevas_emitidas, nuevas_recibidas = _resolver_confirmaciones(
            baja_confianza, respuesta["confirmaciones"], user_id
        )
        facturas_emitidas = facturas_emitidas + nuevas_emitidas
        facturas_recibidas = facturas_recibidas + nuevas_recibidas

    if habia_pendientes:
        # Resolved this pass — return immediately. No LLM call happens here;
        # facturas_baja_confianza is now guaranteed empty, so the graph's
        # routing goes straight to calcular/ocr_factura with no self-edge.
        return {
            "facturas_emitidas": facturas_emitidas,
            "facturas_recibidas": facturas_recibidas,
            "facturas_baja_confianza": baja_confianza,
        }

    client = crear_cliente_anthropic()

    # D11 rolling window (SPEC-F5-06): a per-call view only — keeps the
    # first message (often the sin_actividad/duplicate-disclosure context)
    # plus the most recent 14 when the history grows past 15 turns. Never
    # mutates estado["mensajes"], which keeps the full history for display
    # and for the next call's own trim.
    historial = estado.get("mensajes", [])
    if len(historial) > 15:
        historial = [historial[0]] + historial[-14:]

    mensajes_api = [
        {"role": "user" if m["rol"] == "usuario" else "assistant", "content": m["contenido"]}
        for m in historial
    ]

    respuesta = client.messages.create(
        model=_MODEL,
        max_tokens=1024,
        system=construir_system_prompt(
            estado.get("presentacion_duplicada", False),
            estado.get("csv_presentacion_previa"),
        ),
        tools=_TOOLS,
        messages=mensajes_api,
    )

    nuevas_emitidas, nuevas_recibidas, sin_actividad, quiere_rectificativa = _procesar_bloques_respuesta(
        respuesta.content
    )

    texto_respuesta = "".join(bloque.text for bloque in respuesta.content if bloque.type == "text")

    resultado: dict = {
        "facturas_emitidas": facturas_emitidas + nuevas_emitidas,
        "facturas_recibidas": facturas_recibidas + nuevas_recibidas,
        "facturas_baja_confianza": baja_confianza,
        "tokens_usados": estado.get("tokens_usados", 0) + respuesta.usage.input_tokens + respuesta.usage.output_tokens,
    }
    if texto_respuesta:
        resultado["mensajes"] = estado.get("mensajes", []) + [{"rol": "agente", "contenido": texto_respuesta}]
    if sin_actividad is not None:
        resultado["sin_actividad"] = sin_actividad
    if quiere_rectificativa is not None:
        resultado["quiere_rectificativa"] = quiere_rectificativa

    return resultado
