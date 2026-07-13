# Change: agente-conversacional

## Phase

F3 — Agente conversacional (`docs/Autonomos.io/3. SDD/specs/fases_desarrollo_criterios_aceptacion_MVP_2.md` §5). Maps to `openspec/config.yaml` → `acceptance_criteria.phase_3`.

## Objective

Build the LangGraph StateGraph for P04 with Claude Sonnet 5 as the conversational LLM. At the end of this change, a user can talk to the agent in natural language, upload invoices, review the calculation, and confirm the presentation — with the graph stopping cleanly at the confirmation step. The RPA that actually files the M303 with AEAT is **not** wired yet (Phase 4); this phase's graph ends at "user confirmed" and would hand off to Phase 4 from there.

## Agents involved (per `openspec/config.yaml`)

- **orchestrator** (`claude-opus-4-8`) — plans this change, evaluates exit criteria, runs `fiscal_integrity_checks`
- **backend_developer** (`claude-sonnet-4-6`, GLM-5.2 via DeepInfra once the harness exists) — implements all tasks below; this phase has no frontend work (no UI exists yet — the graph is exercised via tests and direct invocation, not a chat UI, which is Phase 5 scope)

## Naming conflict resolved before this change

`docs/backend-standards.md`'s "Project structure" section (lines 36-42, written during Phase 1) places this phase's runtime graph (`graphs/p04_graph.py`, `state.py`) inside `src/agents/` — the same path `CLAUDE.md` §5 already reserved for the **external, build-time-only** LangGraph harness (Opus 4.8 + GLM-5.2, per `docs/development_guide.md` § Agent architecture). Those are two unrelated systems that must not share a path.

**Resolution:** the Phase 3 runtime conversational agent lives in `src/agent/` (singular). `src/agents/` (plural) remains reserved exclusively for the external build harness, which is tooling — not part of the shipped product — and is out of scope for this change. This change includes a documentation task to fix `docs/backend-standards.md`'s project structure accordingly (see `tasks.md`).

## Scope

In scope:
- `src/agent/state.py` — `EstadoP04` TypedDict with every field the graph's nodes read or write.
- `src/agent/graph.py` — the LangGraph `StateGraph` wiring all nodes and conditional edges for P04.
- Nodes: `detectar_periodo`, `verificar_duplicado`, `recopilar_datos`, `ocr_factura`, `calcular`, `resumir`, `confirmar` (interrupt), `notificar`.
- `src/agent/ocr.py` — Claude Vision invoice extraction (NIF emisor, fecha, base imponible, tipo IVA, confidence per field).
- `src/agent/prompts/p04_system_prompt.py` — the Claude Sonnet 5 system prompt for the P04 conversation.
- Human-in-the-loop: a real LangGraph `interrupt()` at the confirmation node — no path reaches "confirmed" without it.
- Checkpointing: LangGraph `PostgresSaver` against Supabase, keyed by `thread_id`, so an interrupted session resumes exactly where it stopped.
- Duplicate declaration detection: query `presentacion` for an existing row matching `(user_id, proceso='P04', ejercicio, periodo)` before starting a new declaration.
- Casuística C01 (sin actividad) handling inside the graph.

Out of scope (later phases, per `openspec/config.yaml` → `out_of_scope` and the roadmap):
- Playwright RPA against AEAT (Phase 4) — the graph ends at the `confirmar` interrupt; nothing after it exists yet.
- Frontend / chat UI (Phase 5) — this phase's graph is invoked directly (via tests / a thin script), not through a web interface.
- The external build harness in `src/agents/` (Opus 4.8 + GLM-5.2 via DeepInfra) — unrelated system, see naming conflict note above.
- Real VIES validation, full prorrata calculation, P04-R — already out of scope since Phase 2, unaffected by this change.
- Any process other than P04 (P01, P05-P09, P13, P14, P24-P26, régimen foral).

## Acceptance criteria

Maps directly to CA-F3-01 through CA-F3-10:

| ID | Criterion |
|---|---|
| CA-F3-01 | The graph instantiates without errors; initial state is valid; every node declared in SPEC-F3-02 is present and connected; no unreachable nodes |
| CA-F3-02 | Correct period detection from current date: abril → 1T, julio → 2T, octubre → 3T, enero → 4T of the previous year |
| CA-F3-03 | OCR extracts NIF emisor, fecha, base imponible, tipo IVA with confidence > 0.8 for a clean invoice; a low-quality image yields confidence < 0.8 and sets the manual-review flag |
| CA-F3-04 | Dudoso expense classification: a restaurant invoice sets `requiere_confirmacion=True`; a software invoice sets `requiere_confirmacion=False` |
| CA-F3-05 | The summary node's message includes: total IVA repercutido, total IVA deducible, final result (a_ingresar/a_compensar), invoice count, filing deadline |
| CA-F3-06 | The graph interrupts correctly at the confirmation node and persists state in Supabase via `PostgresSaver`; restarting with the same `thread_id` recovers the exact state |
| CA-F3-07 | User responds "revisar" → graph returns to data collection without losing already-loaded invoices; "cancelar" → process marked `CANCELADO` in DB, thread ends |
| CA-F3-08 | Casuística C01 (sin actividad): if the user declares no operations, the agent proposes a sin-actividad declaration and confirms before continuing |
| CA-F3-09 | Duplicate presentation detection: if an M303 already exists for the detected period, the agent informs the user and asks whether they want a rectificativa |
| CA-F3-10 | Full P04 flow token cost (first question to confirmation) does not exceed 20,000 tokens with Claude Sonnet 5, measured via LangSmith |

## References

- `openspec/config.yaml` — mandatory backend steps, fiscal integrity checks, agent/model assignment
- `docs/openspec-tasks-mandatory-steps.md` — exact task structure and report templates followed in `tasks.md`
- `docs/backend-standards.md` — stack (LangGraph 0.4+, Claude Sonnet 5), architecture principles (LLM never calculates taxes, human-in-the-loop mandatory, stateful via checkpointing)
- `docs/data-model.md` — `presentacion` schema (for duplicate detection), `factura_emitida`/`factura_recibida` (OCR targets)
- `docs/domain-context.md` — glossary the system prompt must stay within; "what the agent must never do" section
- `docs/Autonomos.io/1. ANALISIS FUNCIONAL/.md/P04_IVA_trimestral_v1_completo_1.md` — Bloque 0 (T04-00, T04-01: prerequisites, period detection), Bloque 1 (T04-02 to T04-05: invoice collection + OCR), Bloque 4 (T04-13, T04-14: coherence validation, user summary), C01 and C09 casuísticas
- `specs/archive/fiscal-engine-fundamentos/design.md` — Phase 1 context: the deterministic fiscal engine this graph's `calcular` node calls, never reimplements
- `specs/archive/calculo-iva-completo/design.md` — Phase 2 context: `calcular_m303()` is the single entry point the `calcular` node uses
- `docs/Autonomos.io/3. SDD/specs/fases_desarrollo_criterios_aceptacion_MVP_2.md` §5 — Phase 3 objective, SPEC-F3-01..06, and CA-F3-01..10 source
