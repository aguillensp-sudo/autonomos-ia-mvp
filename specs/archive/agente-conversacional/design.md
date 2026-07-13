# Design: agente-conversacional

## Folder structure (resolves the naming conflict — see `feature.md`)

```
src/
  agent/                        # NEW — runtime P04 conversational agent (this phase)
    state.py                    # EstadoP04 TypedDict
    graph.py                    # StateGraph wiring
    nodes/
      detectar_periodo.py
      verificar_duplicado.py
      recopilar_datos.py
      ocr_factura.py
      calcular.py
      resumir.py
      confirmar.py
      notificar.py
    ocr.py                      # Claude Vision extraction
    prompts/
      p04_system_prompt.py
    checkpointer.py             # PostgresSaver setup against Supabase
  agents/                       # UNCHANGED — external build-time-only harness
    ...                         # (Opus 4.8 + GLM-5.2, per CLAUDE.md §5 — out of scope here)
```

`src/agent/` (singular) is the shipped product's conversational agent. `src/agents/` (plural) stays reserved for the external build harness — see `feature.md` "Naming conflict resolved before this change" and the `docs/backend-standards.md` fix in `tasks.md`.

## SPEC-F3-01 — State definition (`EstadoP04`)

All fields are JSON-serializable (str/int/float/bool/list/dict only — no Pydantic model instances, no `date` objects) because LangGraph's `PostgresSaver` checkpoints the state by serializing it. Nodes convert to/from `src/fiscal/models.py` Pydantic models at their own boundary, never store them in state directly.

```python
from typing import TypedDict

class MensajeChat(TypedDict):
    rol: str            # 'usuario' | 'agente'
    contenido: str

class EstadoP04(TypedDict):
    # Identity / thread
    thread_id: str                          # f"{user_id}:P04:{ejercicio}:{periodo}"
    user_id: str

    # Period (set by detectar_periodo)
    ejercicio: int | None
    periodo: str | None                     # '1T' | '2T' | '3T' | '4T'
    fecha_inicio_periodo: str | None        # ISO date
    fecha_fin_periodo: str | None
    fecha_limite_presentacion: str | None
    dias_para_vencimiento: int | None

    # Duplicate detection (set by verificar_duplicado)
    presentacion_duplicada: bool
    csv_presentacion_previa: str | None
    quiere_rectificativa: bool | None       # None = not yet asked

    # Sin actividad (casuistica C01)
    sin_actividad: bool | None              # None = not yet determined

    # Invoice collection (set by recopilar_datos / ocr_factura)
    facturas_emitidas: list[dict]           # each dict matches FacturaEmitida field shape
    facturas_recibidas: list[dict]          # each dict matches FacturaRecibida field shape
    facturas_pendientes_ocr: list[str]      # Supabase Storage paths not yet processed
    facturas_baja_confianza: list[dict]     # {factura_index, campo, valor, confianza} needing user review

    # Calculation (set by calcular — calls calcular_m303(), never computes itself)
    resultado_m303: dict | None             # serialized ResultadoM303
    errores_coherencia: list[str]

    # Summary / confirmation (set by resumir / confirmar)
    mensaje_resumen: str | None
    confirmado: bool
    quiere_revisar: bool
    cancelado: bool

    # Conversation
    mensajes: list[MensajeChat]

    # Observability (CA-F3-10)
    tokens_usados: int
```

## SPEC-F3-02 — Node definitions

Every node function has the signature `(estado: EstadoP04) -> dict` (LangGraph merges the returned partial dict into state — nodes never mutate `estado` in place).

| Node | Reads | Writes | Notes |
|---|---|---|---|
| `detectar_periodo` | (current date) | `ejercicio`, `periodo`, `fecha_inicio_periodo`, `fecha_fin_periodo`, `fecha_limite_presentacion`, `dias_para_vencimiento` | Pure function of `date.today()` — no LLM call. CA-F3-02. |
| `verificar_duplicado` | `user_id`, `ejercicio`, `periodo` | `presentacion_duplicada`, `csv_presentacion_previa` | Queries `presentacion` table (Supabase). No LLM call. CA-F3-09. |
| `recopilar_datos` | `mensajes`, `facturas_emitidas`, `facturas_recibidas`, `facturas_baja_confianza`, `presentacion_duplicada`, `csv_presentacion_previa` | `mensajes` (appends, only on the LLM-turn path), `facturas_emitidas`/`facturas_recibidas` (new manual entries **and** entries assembled from resolved `facturas_baja_confianza`), `facturas_pendientes_ocr`, `facturas_baja_confianza` (drained on resolution), `sin_actividad`, `quiere_rectificativa` | **Interrupt() node as of the second adversarial-review pass (post-Section-18 CRITICAL fix) — see SPEC-F3-06.** Resolves any pending `facturas_baja_confianza` entries via a structural `interrupt()` loop *before* ever calling Claude Sonnet 5 — the LLM never sees pending OCR fields, so it cannot be a soft/skippable gate. Only once `facturas_baja_confianza` has no `requiere_confirmacion=True` entries left (or never had any) does it proceed to the normal Claude Sonnet 5 conversational turn (system prompt SPEC-F3-04). Handles casuística C01 (asks "¿ninguna operación este trimestre?") and CA-F3-09 duplicate disclosure (asking about a detected duplicate presentation when `presentacion_duplicada=True`, still LLM/conversational — see SPEC-F3-04/SPEC-F3-07 amendments) in that conversational-turn path. CA-F3-03, CA-F3-06, CA-F3-08, CA-F3-09. |
| `ocr_factura` | `facturas_pendientes_ocr` | `facturas_emitidas`/`facturas_recibidas` (extracted), `facturas_baja_confianza`, `facturas_pendientes_ocr` (drained) | Claude Vision call (SPEC-F3-05). CA-F3-03. |
| `calcular` | `facturas_emitidas`, `facturas_recibidas`, `ejercicio`, `periodo` | `resultado_m303`, `errores_coherencia` | Calls `src.fiscal.iva.calcular_m303.calcular_m303()` — the only fiscal computation in this graph. No LLM call. Per `docs/backend-standards.md`: "LLM never calculates taxes." |
| `resumir` | `resultado_m303` | `mensaje_resumen` | Claude Sonnet 5 call, human-language summary per SPEC-F3-04 template. CA-F3-05. |
| `confirmar` | `mensaje_resumen` | `confirmado`, `quiere_revisar`, `cancelado` | `interrupt()` node — see SPEC-F3-06. CA-F3-06, CA-F3-07. |
| `notificar` | `confirmado`/`cancelado`, `resultado_m303` | `mensajes` (final message) | If `cancelado`: updates `presentacion.estado='cancelado'` in Supabase. If `confirmado`: hands off (this graph ends here — Phase 4 picks up from a confirmed, un-filed state). **The `confirmado` message must never imply filing has started or is in progress** — this graph does not file anything; Phase 4 (not yet built) does. Use neutral "your declaration is ready and pending submission" phrasing, not "presenting to the AEAT..." or similar. |

### Amendment — `facturas_baja_confianza` resolution (post-adversarial-review, Blocker 1, revised after second review's CRITICAL finding)

The original SPEC-F3-02/SPEC-F3-03 text described `facturas_baja_confianza` as a list the user "must review/confirm ... before the conversation can move to `calcular`," but neither the routing function nor `recopilar_datos` actually enforced or implemented that — flagged fields were written once by `ocr_factura` and never read again, so any OCR-extracted invoice was silently dropped from the calculation forever.

**First fix attempt (superseded — do not implement)**: a `confirmar_factura_baja_confianza` *tool* the LLM could call, plus a `recopilar_datos -> recopilar_datos` self-edge in the graph for "still pending, ask again." The second adversarial-review pass found this **CRITICAL**: a bare conditional self-edge is not a pause point in LangGraph — only `interrupt()` suspends a run. Without a real interrupt anywhere in that loop, a single `graph.invoke()` re-executed `recopilar_datos` (including a full Claude Sonnet 5 call each time) immediately and repeatedly whenever the LLM's one call per pass didn't resolve every flagged field — empirically confirmed to make 10,000+ calls before hitting LangGraph's recursion limit and crashing. This also silently retrapped the *pre-existing* `ocr_factura -> recopilar_datos` edge, since OCR always flags fiscal fields now — meaning the entire OCR flow became unusable end-to-end through the real compiled graph, not just the newly-added self-edge.

**Actual fix — `interrupt()` inside `recopilar_datos`, no self-edge, no LLM-facing tool:**

`confirmar_factura_baja_confianza` is removed from `_TOOLS` entirely — the LLM never sees pending OCR fields and is never the mechanism that resolves them. This isn't a naming change, it's a category change: an LLM tool call is a *soft* gate (the model can simply choose not to call it); `interrupt()` is a *structural* one the graph cannot proceed past without an explicit external answer, exactly like `confirmar`'s own gate on `confirmado`. Fiscal-field confirmation deserves the same guarantee.

`recopilar_datos`'s new shape (see SPEC-F3-06 for the interrupt mechanics that make this safe to call in a loop):

```python
def recopilar_datos(estado: EstadoP04) -> dict:
    baja_confianza = [dict(e) for e in estado.get("facturas_baja_confianza", [])]
    facturas_emitidas = list(estado.get("facturas_emitidas", []))
    facturas_recibidas = list(estado.get("facturas_recibidas", []))
    habia_pendientes = any(e["requiere_confirmacion"] for e in baja_confianza)

    while any(e["requiere_confirmacion"] for e in baja_confianza):
        pendientes = [e for e in baja_confianza if e["requiere_confirmacion"]]
        respuesta = interrupt({"tipo": "confirmacion_baja_confianza", "pendientes": pendientes})
        for c in respuesta["confirmaciones"]:
            # locate the matching (path, campo) entry, set its valor to
            # c["valor_confirmado"], mark requiere_confirmacion=False;
            # once every entry for that path is resolved, assemble the
            # invoice from ALL its entries (fiscal + already-accepted
            # non-fiscal) and move it into facturas_emitidas/recibidas,
            # purging those entries from baja_confianza — same assembly
            # logic as the superseded tool-based version, just triggered
            # by the resume payload instead of a tool_use block.
            ...

    if habia_pendientes:
        # Resolved this pass — return immediately. No LLM call happens in
        # this invocation. facturas_baja_confianza is now guaranteed empty,
        # so the graph's routing (SPEC-F3-03) goes straight to calcular
        # (or ocr_factura, if new pending_ocr paths exist) without ever
        # touching recopilar_datos's self-edge, because there isn't one.
        return {
            "facturas_emitidas": facturas_emitidas,
            "facturas_recibidas": facturas_recibidas,
            "facturas_baja_confianza": baja_confianza,
        }

    # No pending confirmations (none now, none ever this pass) — proceed
    # with the normal Claude Sonnet 5 conversational turn exactly as before.
    client = crear_cliente_anthropic()
    ...
```

Key properties this gives us:
- **The `interrupt()` call happens strictly before the Claude Sonnet 5 API call.** On resume, LangGraph re-enters `recopilar_datos` from the top and replays every already-resumed `interrupt()` call in the loop instantly (cached, no re-pause, no re-execution of their side effects) until it reaches the next not-yet-resumed one. Because the LLM call sits *after* the entire while-loop, it is never re-executed as a side effect of resuming a field confirmation — it only runs once, and only after `facturas_baja_confianza` has no pending entries left for this pass.
- **The `habia_pendientes` early return means recopilar_datos never both resolves OCR fields and processes a new chat turn in the same invocation** — avoiding a second-order risk noticed while designing this fix: calling the LLM again immediately after a structural confirmation, with `mensajes` unchanged, could have caused it to non-deterministically re-emit tool calls (e.g. re-registering an already-registered invoice) against a conversation it had already fully processed.
- **Multiple rounds of confirmation are handled by the `while` loop calling `interrupt()` again**, not by a graph edge. Each iteration's `interrupt()` is a genuine pause — the caller must round-trip through `Command(resume=...)` for every round, exactly as `confirmar` already requires for its own decision. No graph self-edge exists or is needed.
- The user may correct a flagged value instead of confirming the OCR reading verbatim — `valor_confirmado` in each `confirmaciones` entry is the value that ends up in the invoice; it does not have to equal the OCR-extracted value.

## SPEC-F3-03 — Conditional edges

```
START -> detectar_periodo -> verificar_duplicado

verificar_duplicado:
  if presentacion_duplicada -> recopilar_datos
    (the agent still collects the "¿quieres presentar una rectificativa?"
     answer via conversation — quiere_rectificativa is set inside
     recopilar_datos when presentacion_duplicada is True; the actual
     rectificativa FILING flow is out of scope, P04-R, per feature.md)
  else -> recopilar_datos

recopilar_datos:
  if sin_actividad is True -> calcular  (routes through calcular with empty
                                          invoice lists — see design note below)
  elif facturas_pendientes_ocr is not empty -> ocr_factura
  else -> calcular
  (facturas_baja_confianza is NOT checked here — see amended design note
   below. There is no recopilar_datos -> recopilar_datos self-edge.)

ocr_factura -> recopilar_datos
  (always loops back. recopilar_datos's first action on re-entry is its
   own internal interrupt() loop over any facturas_baja_confianza entries
   ocr_factura just populated — see SPEC-F3-02 amendment / SPEC-F3-06.
   By the time recopilar_datos returns control to the graph's routing
   function, facturas_baja_confianza is guaranteed to have no
   requiere_confirmacion=True entries left, so the plain check above
   is sufficient — no separate routing branch for it is needed, and none
   exists.)

calcular -> resumir
resumir -> confirmar

confirmar (after interrupt() resumes):
  if confirmado -> notificar -> END
  if quiere_revisar -> recopilar_datos
  if cancelado -> notificar -> END
```

Design note on `sin_actividad`: rather than special-casing "no calculation" (which would create a second code path that could silently drift from `calcular_m303()`'s own zero-invoice behavior), `sin_actividad=True` still routes through `calcular` with empty `facturas_emitidas`/`facturas_recibidas` — `calcular_m303()` already produces `tipo_resultado='sin_actividad'` for that input (verified in Phase 1/2 tests). This keeps a single source of truth for what "sin actividad" means numerically.

Design note on `facturas_baja_confianza` (post-adversarial-review, Blocker 1 — **revised after the second review's CRITICAL finding**): the original fix for Blocker 1 added a `facturas_baja_confianza is not empty -> recopilar_datos` routing branch (a bare conditional self-edge) and justified it with a claim that "the graph naturally comes to rest there for the caller's next turn." That claim was **factually wrong about LangGraph's execution model** — a conditional edge back to a node is not a pause point; only `interrupt()` suspends a run and returns control to the caller. Without any interrupt in that loop, a single `graph.invoke()` would re-execute `recopilar_datos` (full Claude Sonnet 5 call included) immediately and repeatedly, confirmed empirically to make 10,000+ calls before crashing with `GraphRecursionError`. The fix moves the pause into `recopilar_datos` itself as a real `interrupt()` (SPEC-F3-02 amendment, SPEC-F3-06) that resolves *before* the graph's routing function is ever consulted — so by construction, `facturas_baja_confianza` is always empty by the time routing runs, and the self-edge (and the routing branch that fed it) is removed entirely rather than fixed in place.

## SPEC-F3-04 — System prompt (Claude Sonnet 5, `claude-sonnet-5`)

`src/agent/prompts/p04_system_prompt.py`. Required content (all sourced from already-approved docs — the prompt does not introduce new fiscal rules):

1. **Role statement**: "You are the P04 (IVA Trimestral) assistant for [autónomo name]. You help collect invoices, explain the calculation, and get explicit confirmation before any filing. You never calculate taxes yourself — the number always comes from the deterministic engine."
2. **Hard constraints** (verbatim from `docs/domain-context.md` § "What the agent must never do"):
   - Never calculate taxes using the LLM.
   - Never present a declaration without explicit user confirmation.
   - Never assume deductibility — flag ambiguous categories with `requiere_confirmacion=True` (casuística C05/T04-07 dudoso flow) and ask.
   - Never confuse the filing period with the coverage period.
3. **Glossary boundary**: only use Spanish fiscal terms defined in `docs/domain-context.md`'s glossary. If a concept the user raises needs a term not in the glossary, escalate (don't invent Spanish fiscal vocabulary) — same rule already enforced on the frontend agent persona (`ai-specs/agents/frontend-developer.md`), now also binding on the runtime conversational agent.
4. **Summary format template** (CA-F3-05), in human language, not raw casilla codes:
   ```
   📊 RESUMEN IVA [periodo] [ejercicio]
   💰 IVA repercutido (lo que cobraste a tus clientes): [total_devengado] €
   📉 IVA deducible (lo que pagaste en gastos): [total_deducible] €
   ⚖️ Resultado: [resultado] € — [A INGRESAR / A COMPENSAR / SIN ACTIVIDAD]
   📋 Facturas incluidas: [n] emitidas, [n] recibidas
   📅 Fecha límite: [fecha_limite_presentacion] ([dias_para_vencimiento] días)
   ```
   (Adapted from Hoja 3 T04-14 of the source functional spec.)
5. **Dudoso-expense confirmation phrasing** (casuística C05/T04-07): the exact 3-option prompt pattern from T04-07 ("¿Es un gasto relacionado con tu actividad profesional? Sí 100% / Sí mixto 50% / No, personal") — reused verbatim, not reinvented per conversation.
6. ~~**Fiscal-field confirmation for OCR-flagged invoices**~~ — **removed** (post-second-adversarial-review, superseding the item that used to live here). Confirming `facturas_baja_confianza` fields is no longer a system-prompt / LLM-tool concern at all: `recopilar_datos` now resolves them via a structural `interrupt()` loop *before* the LLM is ever called (SPEC-F3-02 amendment, SPEC-F3-06). The LLM is never shown pending OCR fields and has no tool to confirm them — there is nothing for the prompt to instruct here, by construction rather than by convention. This also removes the "highest priority" framing that used to contradict item 7 below.
7. **Duplicate presentation disclosure** (post-adversarial-review, Blocker 3, CA-F3-09): the system prompt receives `presentacion_duplicada` and `csv_presentacion_previa` as part of the conversation context (see SPEC-F3-07 amendment). When `presentacion_duplicada=True`, the agent's **first message of the conversation** must inform the user a presentation for this `ejercicio`/`periodo` already exists (referencing the prior CSV/justificante if available) and ask explicitly whether they want to file a rectificativa, before addressing anything else conversational (a new invoice, a dudoso classification, sin actividad). The user's answer is captured via a tool, `declarar_intencion_rectificativa` (`{"quiere_rectificativa": bool}`), which sets `quiere_rectificativa` in state. Actually filing the rectificativa (casuística C09, P04-R) remains out of scope — this is disclosure and intent-capture only. (This is now the *only* conversational priority claim in the prompt — nothing competes with it since item 6 above was removed, closing the second review's MEDIUM prompt-contradiction finding.)

## SPEC-F3-05 — OCR module (`src/agent/ocr.py`)

Claude Vision (via the same Claude Sonnet 5 model, vision-capable) extracts structured data from an uploaded invoice PDF/image.

```python
def extraer_factura_ocr(pdf_bytes: bytes, tipo: str) -> ResultadoOCR:
    """tipo: 'emitida' | 'recibida'. Calls Claude Vision with a prompt
    requesting a strict JSON response:
    {
      "nif_emisor": str | null, "confianza_nif_emisor": float,
      "fecha": str | null,      "confianza_fecha": float,
      "base_imponible": float | null, "confianza_base_imponible": float,
      "tipo_iva": int | null,   "confianza_tipo_iva": float,
      ... (categoria_gasto, nif_proveedor for 'recibida')
    }
    Fields with confianza < 0.8 are added to facturas_baja_confianza in the
    calling node (ocr_factura) — this function itself never decides what
    counts as "good enough", it only reports the confidence per field.
    """
```

**Confidence threshold: 0.8** (matches `factura_emitida.ocr_confidence`/`factura_recibida.ocr_confidence` columns already in `docs/data-model.md`, and the frontend agent persona's existing rule). A field below threshold is never auto-accepted — CA-F3-03.

**Mandatory exception — fiscal fields always require confirmation** (architecture review, Principle 1: legal correctness before speed): `base_imponible`, `tipo_iva`, and `cuota_iva` feed `calcular_m303()` directly, so a confident-but-wrong OCR reading of one of these is a wrong tax figure, not a cosmetic error. `ocr_factura` therefore routes these three fields to `facturas_baja_confianza` **unconditionally**, regardless of the confidence the model reports — the 0.8 threshold only governs non-fiscal fields (`nif_emisor`, `nif_proveedor`, `fecha`, `categoria_gasto`, `descripcion`). No invoice can be auto-accepted into `facturas_emitidas`/`facturas_recibidas` via OCR without the user explicitly confirming these three fields. `p04_system_prompt.py` states this as a hard constraint so the conversational agent never implies otherwise to the user.

## SPEC-F3-06 — Human-in-the-loop (`confirmar` **and** `recopilar_datos` nodes)

As of the second adversarial-review pass, `interrupt()` is used in **two** places in this graph, not one: `confirmar` (the final declaration gate, CA-F3-06/CA-F3-07, unchanged) and `recopilar_datos` (the per-field OCR confirmation gate, added to fix Blocker 1's CRITICAL regression — see the SPEC-F3-02 amendment and the design note under SPEC-F3-03). Both follow the exact same two-invocation mechanics described below; `recopilar_datos`'s usage additionally calls `interrupt()` **in a loop** (see "Interrupt in a loop" subsection further down), since more than one round of field confirmation may be needed.

### How LangGraph `interrupt()` works — two invocations, not one

**This is the most critical implementation detail of Phase 3.** `interrupt()` does NOT work
like a blocking `input()` call. It operates across two separate graph invocations:

**Invocation 1 — the interrupt:**
```python
def confirmar(estado: EstadoP04) -> dict:
    respuesta = interrupt({
        "tipo": "confirmacion_p04",
        "mensaje": estado["mensaje_resumen"],
    })
    # CODE BELOW THIS LINE DOES NOT EXECUTE IN INVOCATION 1
    # interrupt() raises an InterruptException internally.
    # LangGraph catches it, persists the FULL state to PostgresSaver,
    # and returns control to the caller with the interrupt payload.
    # The node function is suspended at this line.
```

**Between invocations:**
The caller (a test, or a future Phase 5 API endpoint) receives the interrupt signal,
shows the summary to the user, collects their decision, and then resumes the graph:
```python
graph.invoke(
    Command(resume={"accion": "confirmar"}),  # or "revisar" or "cancelar"
    config={"configurable": {"thread_id": thread_id}}
)
```

**Invocation 2 — the resume:**
LangGraph restores the EXACT pre-interrupt state from PostgresSaver (same
`facturas_emitidas`, `resultado_m303`, `mensaje_resumen` — everything) and
re-enters `confirmar`. Now `interrupt()` returns the resume value instead of raising:
```python
def confirmar(estado: EstadoP04) -> dict:
    respuesta = interrupt(...)
    # In Invocation 2, interrupt() returns {"accion": "confirmar"}
    # (or "revisar" or "cancelar") — execution continues normally here.
    accion = respuesta.get("accion")
    return {
        "confirmado": accion == "confirmar",
        "quiere_revisar": accion == "revisar",
        "cancelado": accion == "cancelar",
    }
```

**Implementation consequences:**
- The graph MUST be compiled with `checkpointer=postgres_saver` — without a checkpointer,
  `interrupt()` raises but the state is not persisted, so resuming is impossible.
- The `thread_id` MUST be the same in both invocations — it is the key LangGraph uses
  to look up the saved state in PostgresSaver.
- Tests MUST invoke the graph twice for the `confirmar` step: once to trigger the interrupt,
  once (with `Command(resume=...)`) to resume it. A test that only does one invocation
  is not testing the real human-in-the-loop flow. See tasks.md Steps 9.1-9.5.
- **No path to `confirmado=True` can bypass `interrupt()`** — this is the fiscal integrity
  check: the user's explicit decision must be the gate, not a programmatic shortcut.

### Interrupt in a loop (`recopilar_datos`, Blocker 1's actual fix)

`confirmar` calls `interrupt()` exactly once per graph run — the pattern above covers it fully. `recopilar_datos` needs to potentially confirm *several* OCR-flagged fields across *several* rounds (the user might not answer every pending field in one reply), so it wraps `interrupt()` in a `while` loop instead of a single call:

```python
while any(e["requiere_confirmacion"] for e in baja_confianza):
    pendientes = [e for e in baja_confianza if e["requiere_confirmacion"]]
    respuesta = interrupt({"tipo": "confirmacion_baja_confianza", "pendientes": pendientes})
    for c in respuesta["confirmaciones"]:
        ...  # resolve, possibly assemble + move the completed invoice
```

This is a documented, supported LangGraph pattern (multiple `interrupt()` calls within one node, in a loop), and it composes correctly with the two-invocation model above:

- **Each loop iteration's `interrupt()` call is a genuine pause.** The first time the loop reaches an `interrupt()` that hasn't been resumed yet, the run suspends exactly as `confirmar`'s does — full state persisted, control returned to the caller with `pendientes` in the interrupt payload.
- **On resume, already-resumed iterations replay instantly.** LangGraph tracks interrupts within a node by call order. Re-entering `recopilar_datos` from the top after a resume, the loop re-evaluates its condition and re-reaches each `interrupt()` call in sequence; every call that was already resumed in a *previous* round returns its cached resume value immediately (no re-pause, and critically, no re-execution of anything that happened before it in the function — the loop body's confirmation-processing logic for an earlier round is not re-run, since it's inside the `for` block that already executed and returned control past that point). Execution only actually pauses again at the first *not-yet-resumed* `interrupt()` — i.e., if there are still pending fields after processing the latest round's confirmations.
- **The expensive Claude Sonnet 5 call lives entirely after this `while` loop**, never inside it and never before it. This placement is deliberate and is what prevents the CRITICAL regression: since the loop's interrupts always resolve (or keep pausing) before that call is reached, resuming a field confirmation never triggers a redundant LLM call. The function returns immediately after the loop if it had any pending fields at all (`habia_pendientes`), skipping the LLM call for that invocation entirely — the graph's routing (SPEC-F3-03) then proceeds directly to `calcular`/`ocr_factura` without needing a self-edge back into `recopilar_datos`.
- **Resume payload shape**: `Command(resume={"confirmaciones": [{"path": str, "campo": str, "valor_confirmado": number | string, "tipo": "emitida" | "recibida"}, ...]}}`. The caller (chat UI in Phase 5, tests today) is expected to collect and submit answers for **all** fields shown in the interrupt payload's `pendientes` in one resume where possible, but the loop correctly handles a partial resume too — it will simply pause again for whatever remains.
- Tests MUST invoke the graph (or call `recopilar_datos` directly, if testing it in isolation) at least twice for any scenario with pending `facturas_baja_confianza`: once to trigger the interrupt, once with `Command(resume={"confirmaciones": [...]})` to resume it — mirroring the existing rule for `confirmar` (tasks.md Steps 9.1-9.5 precedent). A test that resolves confirmations by calling `recopilar_datos()` directly with a mocked Anthropic client (as the original `test_flujo_baja_confianza.py` did) does **not** exercise the interrupt mechanism at all and must be replaced/extended with a real two-invocation test through the compiled graph.

### Known limitation — `user_jwt` expiry across a long pause (TODO, Phase 5)

`EstadoP04.user_jwt` (Blocker 2) is a Supabase-issued JWT with a limited lifetime (~1 hour by default). Because `confirmar` and now `recopilar_datos` both use `interrupt()`, and checkpointing is explicitly designed to support a pause of arbitrary length (CA-F3-06 — a user can close the app and resume days later), the stored `user_jwt` can expire while a run sits interrupted. On resume, `verificar_duplicado`/`calcular`/`ocr_factura`/`notificar` would then fail with an authentication error against Supabase, not a domain-meaningful one. This phase does not fix it — there is no refresh-token handling anywhere in `src/agent/`. **TODO for Phase 5**: the calling layer (chat UI / API endpoint) must detect an expired `user_jwt` at resume time and inject a freshly-refreshed one into the `Command(resume=...)` call (or into state directly) before resuming a long-paused thread, rather than reusing whatever JWT was current when the interrupt first fired.

### Checkpointing

`src/agent/checkpointer.py` configures `PostgresSaver` against the Supabase Postgres
connection string (`SUPABASE_DB_URL` — add to `.env` as the direct Postgres URL from
Supabase dashboard → Settings → Database → Connection string → URI mode).
The graph is compiled with `checkpointer=postgres_saver`.

**`thread_id`**: `f"{user_id}:P04:{ejercicio}:{periodo}"` — deterministic, so resuming
the same user/period always hits the same checkpoint. CA-F3-06.

**"revisar" / "cancelar"** (CA-F3-07): both are valid `interrupt()` resume values, routed
by the conditional edge after `confirmar` (SPEC-F3-03). "cancelar" additionally updates
`presentacion.estado='cancelado'` inside `notificar`.

## SPEC-F3-07 — Duplicate declaration detection (`verificar_duplicado`)

```python
def verificar_duplicado(client: Client, user_id: str, ejercicio: int, periodo: str) -> tuple[bool, str | None]:
    """Queries presentacion for an existing row matching
    (user_id, proceso='P04', ejercicio, periodo). Returns
    (presentacion_duplicada, csv_presentacion_previa).
    This is a process-state check, not a fiscal calculation —
    lives in src/agent/, not src/fiscal/.
    """
```

If a match exists, `recopilar_datos`'s system-prompt-driven conversation informs the user
and asks whether they want a rectificativa (CA-F3-09) — sets `quiere_rectificativa` in state.
Actually filing a rectificativa (casuística C09, P04-R) remains out of scope (Phase 2's
`feature.md` already deferred it; this phase only detects and asks, per the acceptance
criterion's literal wording).

**Amendment (post-adversarial-review, Blocker 3):** the original wording above described
the intended behavior but the implementation never wired it — `verificar_duplicado` wrote
`presentacion_duplicada`/`csv_presentacion_previa` to state, but nothing passed those values
into `recopilar_datos`'s system prompt or gave the LLM a way to act on them, so the user was
never actually told about the duplicate. `recopilar_datos` must read `presentacion_duplicada`
and `csv_presentacion_previa` from `estado` and pass them into `construir_system_prompt()` (or
equivalent context injection) on every call, and the system prompt (SPEC-F3-04, item 7) must
instruct the LLM to raise the duplicate in its first message whenever `presentacion_duplicada`
is `True`. This is verified by an integration test asserting the agent's first response
mentions the existing presentation when `presentacion_duplicada=True` — a node-level unit test
of `verificar_duplicado` alone (as existed before this amendment) cannot catch this gap, since
the omission is in what happens to the flag *after* `verificar_duplicado` runs, not inside it.

## Token budget observability (CA-F3-10)

Every Claude Sonnet 5 call (`recopilar_datos`, `resumir`) increments `tokens_usados`
in state from the API response's `usage` field. All calls go through the
`langsmith`-wrapped Anthropic client (`src/agent/llm_client.py`), so every call is
traced to LangSmith when `LANGSMITH_API_KEY` is set.

**Implementation note (deviation from the original wording, applied during `/apply`
per CLAUDE.md §7):** the CA-F3-10 test asserts the `<= 20000` budget against the
**local `tokens_usados` accumulator**, not a synchronous LangSmith API query.
Querying LangSmith's backend for a run's token total inside a test is subject to
server-side ingestion latency (a run may not be queryable for several seconds after
the call returns), which would make the test flaky. The local counter is
synchronous and reliable; the test additionally does a lightweight check that at
least one recent run reached LangSmith (`list_runs`), as an observability
confirmation, not as the pass/fail mechanism. Every trace remains available in the
LangSmith UI for manual/deeper inspection regardless.

Note: `confirmar` itself does not make an LLM call — it only calls `interrupt()`.

## Fiscal integrity checks applicable this phase (from `openspec/config.yaml`)

- **"LLM never calculates taxes"** — `calcular` node's only job is to call `calcular_m303()`;
  no arithmetic in `src/agent/`. Verified by: grep for arithmetic operators in `src/agent/`
  must return zero results in fiscal calculation context.
- **"Human-in-the-loop is mandatory"** — `confirmar`'s `interrupt()` is the ONLY path to
  `confirmado=True`; no conditional edge bypasses it. Verified by: code review of
  `graph.py` confirming every path to `notificar` with `confirmado=True` passes through
  `confirmar`.
- **"An OCR-extracted fiscal field is never auto-accepted"** (post-second-adversarial-review,
  new explicit rule replacing the superseded tool-call-based version): `recopilar_datos`'s
  `interrupt()` loop over `facturas_baja_confianza` is the ONLY path by which an OCR-flagged
  field's value reaches `facturas_emitidas`/`facturas_recibidas`. There is no LLM tool that
  can do this instead — `confirmar_factura_baja_confianza` was removed for exactly this
  reason (an LLM tool call is a soft gate the model can simply skip; `interrupt()` is a
  structural one the graph cannot proceed past). Verified by: code review of
  `recopilar_datos.py` confirming the only place `requiere_confirmacion` is ever set to
  `False` is inside the `interrupt()`-driven confirmation loop.
- **"LangGraph interrupt node present in every graph that leads to AEAT submission"** —
  satisfied: `confirmar` is the terminal gate before any future Phase 4 handoff.
  Phase 4 will ONLY read `estado["confirmado"]` — it will never set it.
- **"No fiscal arithmetic in FastAPI route handlers"** — not applicable this phase
  (no route changes).
- **"RLS enabled on every new Supabase table"** — no new tables this phase;
  `verificar_duplicado` and `notificar` read/write `presentacion`, already RLS-protected
  since Phase 1.
- **"All Supabase queries in `src/agent/` use the anon key + the user's JWT, never the
  service role key"** (post-adversarial-review, Blocker 2 — new explicit rule). RLS being
  enabled on a table (previous bullet) is meaningless if application code queries it with
  a key that bypasses RLS by design. `verificar_duplicado.py`, `calcular.py`,
  `ocr_factura.py`, and `notificar.py` were found using `SUPABASE_SERVICE_KEY` directly,
  relying solely on an application-level `.eq("user_id", ...)` filter with no database-level
  backstop — this contradicts `docs/backend-standards.md`'s own rule ("Never use service
  role key in application code — only in migrations") and is a cross-tenant data-safety
  risk if `user_id` is ever wrong upstream (a state-merge bug, a future API layer mis-binding
  a session). All four nodes must be changed to build their Supabase client from the anon
  key plus the authenticated user's JWT (mirroring how Phase 1/2's RLS integration tests in
  `tests/integration/test_rls.py` already exercise user-scoped clients), so RLS is the actual
  enforcement mechanism, not just a filter clause that happens to be correct today. Verified
  by: grep for `SUPABASE_SERVICE_KEY` in `src/agent/` must return zero results outside
  migration-only contexts (there are none in this phase).
