# Documentation Standards

## Language

- **All code, comments, docstrings, commit messages, test names, variable names, and technical documentation: English.**
- **Domain context documents (docs/domain-context.md) and user-facing content: Spanish.** The domain is Spanish fiscal law — keeping it in Spanish avoids translation errors in legal terms.
- **This rule is absolute.** A Spanish comment in Python code is a bug. An English term in a fiscal domain document is acceptable as a proper noun (e.g., "Modelo 303", "AEAT").

## Docstrings

Every public function in `src/fiscal/` must have a docstring with:

```python
def calcular_iva_devengado(facturas: list[FacturaEmitida]) -> ResultadoDevengado:
    """
    Calculate accrued VAT (IVA devengado) from issued invoices.

    Groups invoices by VAT type (0%, 4%, 10%, 21%) and sums taxable bases
    and VAT amounts. Handles ISP (reverse charge) invoices separately.

    Legal reference: Art. 88-90 LIVA (Ley 37/1992).

    Args:
        facturas: List of issued invoices for the period.

    Returns:
        ResultadoDevengado with breakdown by VAT type and total.

    Raises:
        ValueError: If any invoice has an invalid VAT type.
    """
```

The **legal reference** field is mandatory for all fiscal functions. This is what makes the code auditable.

## OpenSpec artifacts

When creating or updating OpenSpec change artifacts, follow this structure:

```
specs/
  <change-name>/
    feature.md          # What and why (user story + acceptance criteria)
    design.md           # How (technical design, data model changes, API changes)
    tasks.md            # Step-by-step implementation tasks
    reports/            # Agent-generated test reports
      YYYY-MM-DD-step-N-unit-test-and-db-verification.md
      YYYY-MM-DD-step-N-curl-testing.md
      YYYY-MM-DD-step-N-e2e-playwright.md
```

- **feature.md** is written in English. Acceptance criteria map 1:1 to the CA-Fx-xx criteria in `docs/fases_desarrollo_criterios_aceptacion_MVP.docx`.
- **tasks.md** always starts with Step 0 (create feature branch) and ends with documentation update.
- **Reports are mandatory.** No task is marked complete without its report file.

## Git conventions

- **Branch naming:** `feature/<change-name>` or `fix/<change-name>`
- **Commit format:** Conventional Commits — `feat(p04): add ISP detection to deducibility engine`
- **Scope** matches the process or layer: `p04`, `p09`, `p24`, `rpa`, `fiscal`, `api`, `frontend`, `db`
- **Never commit directly to main.** All changes via PR. Orchestrator Opus 4.8 reviews before merge.

## API documentation

- FastAPI auto-generates OpenAPI docs at `/docs` (Swagger) and `/redoc`.
- All endpoint functions have summary and description strings.
- All Pydantic models have field-level descriptions with fiscal context.

```python
class FacturaEmitida(BaseModel):
    base_imponible: Decimal = Field(
        ...,
        description="Taxable base (IVA excluded). Must match the invoice amount without VAT.",
        ge=0
    )
    tipo_iva: Literal[0, 4, 10, 21] = Field(
        ...,
        description="VAT rate applied. Must be one of the Spanish standard rates."
    )
```

## Process documentation

- Each fiscal process (P04, P09, etc.) is fully documented in its Excel file (6 sheets).
- These Excels are the **source of truth for fiscal logic** — not the code.
- When fiscal rules change (e.g., new RETA brackets), update the Excel first, then the code.
- The `docs/domain-context.md` file contains the Spanish fiscal domain overview for agents that need to understand the business context.

## Changelog

- `CHANGELOG.md` at project root, updated per change following Keep a Changelog format.
- Every merged PR adds an entry under `[Unreleased]`.
- On release, `[Unreleased]` becomes `[version] - YYYY-MM-DD`.
