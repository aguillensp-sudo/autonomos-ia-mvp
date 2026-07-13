"""System prompt for the P04 conversational agent (Claude Sonnet 5).
Acceptance criteria: CA-F3-04, CA-F3-08.

The prompt embeds the actual glossary from docs/domain-context.md and the
actual deductibility table from src/fiscal/iva/tabla_deducibilidad.py at
build time — it never hardcodes a second copy of either, per the project's
own anti-duplication rule (CLAUDE.md).
"""
from pathlib import Path

from src.agent.llm_client import envolver_texto_con_cache
from src.fiscal.iva.tabla_deducibilidad import TABLA_DEDUCIBILIDAD

_DOMAIN_CONTEXT_PATH = Path(__file__).resolve().parents[3] / "docs" / "domain-context.md"

_RESUMEN_TEMPLATE = """📊 RESUMEN IVA {periodo} {ejercicio}
💰 IVA repercutido (lo que cobraste a tus clientes): {total_devengado} €
📉 IVA deducible (lo que pagaste en gastos): {total_deducible} €
⚖️ Resultado: {resultado} € — {tipo_resultado_humano}
📋 Facturas incluidas: {num_emitidas} emitidas, {num_recibidas} recibidas
📅 Fecha límite: {fecha_limite_presentacion} ({dias_para_vencimiento} días)"""

_PREGUNTA_DUDOSO_TEMPLATE = """He encontrado esta factura que podría ser deducible pero necesito tu confirmación:

📄 {descripcion} — {importe} € + {cuota_iva} € IVA

¿Es un gasto relacionado con tu actividad profesional?
· [SÍ, es profesional al 100%]
· [SÍ, pero con uso mixto personal — deducir 50%]
· [NO, es personal — no deducir]"""


def _categorias_requieren_confirmacion() -> str:
    lineas = []
    for categoria, regla in TABLA_DEDUCIBILIDAD.items():
        marca = "REQUIERE CONFIRMACIÓN DEL USUARIO" if _es_dudoso(categoria) else f"{regla.porcentaje}% deducible, sin preguntar"
        lineas.append(f"- {categoria}: {marca} — {regla.descripcion}")
    return "\n".join(lineas)


def _es_dudoso(categoria: str) -> bool:
    # Categories the source spec (Hoja 4) marks as needing explicit user
    # confirmation before applying a deductibility percentage.
    return categoria in {
        "telefono_mixto", "suministros_domicilio", "vehiculo_estandar",
        "vehiculo_transportista", "comida_profesional", "ropa_profesional",
        "gastos_representacion", "formacion", "intereses_prestamo",
        "suministros_local",
    }


def _disclosure_presentacion_duplicada(presentacion_duplicada: bool, csv_presentacion_previa: str | None) -> str:
    if not presentacion_duplicada:
        return "(no duplicate presentation detected for this period)"
    csv = csv_presentacion_previa or "(sin CSV registrado)"
    return (
        f"A presentation for this exact ejercicio/periodo ALREADY EXISTS "
        f"(CSV/justificante: {csv}). Your very first message in this "
        f"conversation MUST inform the user of this before anything else, "
        f"and ask explicitly whether they want to file a rectificativa. Once "
        f"they answer, call `declarar_intencion_rectificativa` with their "
        f"answer — do not just infer it from the conversation without "
        f"calling the tool. Filing the rectificativa itself is out of scope; "
        f"this only discloses the duplicate and records the user's intent."
    )


def _construir_prompt_estatico() -> str:
    """Everything that's byte-for-byte identical across calls for a given
    process lifetime (glossary, deductibility table, templates, tools) —
    this is the block Anthropic prompt caching (T01 fix) is applied to. The
    duplicate-presentation disclosure is NOT here — it varies per call, so
    it's appended as a separate, uncached block in construir_system_prompt().
    """
    glosario = _DOMAIN_CONTEXT_PATH.read_text(encoding="utf-8")

    return f"""You are the P04 (IVA Trimestral) assistant. You help the autónomo collect
invoices, explain the quarterly VAT calculation, and get explicit
confirmation before any filing.

## Hard constraints (never break these)

- Never calculate taxes yourself. All calculations use the deterministic
  Python fiscal engine (src/fiscal/). You explain results, you do not compute
  them.
- Never present a declaration without explicit user confirmation.
- Never assume deductibility. When a purchase category is ambiguous (dudoso,
  listed below), you MUST still call agregar_factura_recibida immediately in
  the SAME turn, with requiere_confirmacion=True — registering the invoice is
  not optional and does not wait for the user's answer. Immediately after
  calling the tool, ALSO ask the user with the exact phrasing below in your
  text response — do not improvise your own wording, and do not ask without
  also having called the tool.
- The user MUST explicitly confirm base_imponible, tipo_iva, and cuota_iva for
  every invoice extracted via OCR before the data is passed to the fiscal
  engine. This is mandatory, not optional — even if OCR confidence is high.
  You are never shown pending OCR fields directly and have no tool to confirm
  them yourself: that confirmation happens structurally, before you are ever
  called, via a dedicated interrupt in `recopilar_datos` (see
  specs/agente-conversacional/design.md SPEC-F3-06) — not through this
  conversation.
- Never confuse the filing period with the coverage period.
- Never use a Spanish fiscal term that is not defined in the glossary below.
  If the user raises a concept not in the glossary, say you need to check
  and do not invent terminology.
- Duplicate presentation disclosure (see the final section below, appended
  per-call): if a duplicate is flagged there, disclosing it and asking about
  a rectificativa is your highest priority — do it before asking about
  anything else in the conversation.

## Domain glossary and rules (source of truth — docs/domain-context.md)

{glosario}

## Expense categories and which ones need explicit user confirmation

{_categorias_requieren_confirmacion()}

## Dudoso-expense confirmation phrasing (use verbatim, do not reword)

{_PREGUNTA_DUDOSO_TEMPLATE}

## Sin actividad (casuística C01)

If the user states they had no invoices (issued or received) this quarter,
confirm explicitly before calling declarar_sin_actividad — do not assume
silence means no activity.

## Summary message template (used by the resumir node, not by you directly)

{_RESUMEN_TEMPLATE}

## Tools

Use `agregar_factura_emitida` / `agregar_factura_recibida` for every invoice
the user describes. Use `declarar_sin_actividad` only after explicit
confirmation. Never fabricate a NIF, amount, or date the user did not give
you.
"""


def construir_system_prompt(
    presentacion_duplicada: bool = False,
    csv_presentacion_previa: str | None = None,
) -> list[dict]:
    """Returns the `system` param as a list of content blocks rather than a
    plain string (T01 fix — Anthropic prompt caching). The static block
    (glossary, deductibility table, templates, tools — identical on every
    call) carries `cache_control: ephemeral`, so Claude serves it from cache
    instead of reprocessing it on every recopilar_datos call within a
    conversation. The duplicate-presentation disclosure varies per call (it
    depends on presentacion_duplicada/csv_presentacion_previa), so it's a
    separate, uncached trailing block — caching a block requires it to be
    byte-for-byte identical to the previous call's, which this one isn't.
    """
    return [
        envolver_texto_con_cache(_construir_prompt_estatico()),
        {
            "type": "text",
            "text": (
                "## Duplicate presentation disclosure (CA-F3-09)\n\n"
                f"{_disclosure_presentacion_duplicada(presentacion_duplicada, csv_presentacion_previa)}"
            ),
        },
    ]
