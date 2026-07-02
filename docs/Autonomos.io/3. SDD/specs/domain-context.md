# Domain Context — Spanish Fiscal Domain for Autonomous Workers (Autónomos)

This document is the reference for agents working on this project who need to understand the Spanish fiscal and social security domain. It is intentionally written in English (per base-standards.md §2) with Spanish legal terms preserved as proper nouns where precision requires it.

---

## Who is the user?

An **autónomo** is a self-employed worker in Spain registered as such with both the Spanish Tax Agency (AEAT) and the Social Security (Seguridad Social / TGSS). There are approximately 3.4 million autónomos in Spain.

The autónomo has two simultaneous fiscal obligations:
1. **Tax (AEAT):** Quarterly VAT declarations, quarterly income tax prepayments, annual income tax return.
2. **Social Security (TGSS):** Monthly contribution to the RETA (Régimen Especial de Trabajadores Autónomos).

This system replaces the traditional gestoría (accounting firm) that handles these obligations manually, with a conversational AI agent.

---

## Key institutions

| Institution | Spanish name | Role |
|---|---|---|
| Tax Agency | AEAT (Agencia Estatal de Administración Tributaria) | Collects VAT, income tax, issues NRC payment codes |
| Social Security Treasury | TGSS (Tesorería General de la Seguridad Social) | Collects monthly RETA contributions |
| Social Security portal | Importass | Online portal for RETA management |
| Electronic HQ | Sede Electrónica AEAT | Web portal for tax declarations |

---

## Proceso P04 — IVA Trimestral (Modelo 303) — MVP

This is the core process of the MVP.

### What is IVA?

IVA (Impuesto sobre el Valor Añadido) is Spain's Value Added Tax. It works like European VAT:
- The autónomo charges IVA to clients on issued invoices (**IVA repercutido** = accrued VAT).
- The autónomo pays IVA to suppliers on received invoices (**IVA soportado** = input VAT).
- Every quarter, the autónomo pays AEAT the difference: IVA repercutido − IVA soportado deducible.

### Standard IVA rates in Spain (2026)

| Rate | Applied to |
|---|---|
| 21% | General rate — most goods and services |
| 10% | Reduced — food (non-basic), restaurants, housing construction |
| 4% | Super-reduced — basic food, books, medicines |
| 0% | Exempt with deduction right — intra-EU services, exports |

### The Modelo 303

The M303 is the quarterly VAT declaration form filed with AEAT. Key concepts:

- **Casilla** = a numbered box/field in the form. The M303 has ~70 casillas.
- **Casilla 27** = total IVA devengado (sum of all accrued VAT by rate).
- **Casilla 45** = total IVA deducible (sum of all deductible input VAT).
- **Casilla 70** = net result (casilla 27 − casilla 45).
- **Casilla 110** = negative balance carried from previous quarter.
- **Casilla 71** = final result after applying casilla 110.

### Filing deadlines

| Period | Covers | Deadline |
|---|---|---|
| 1T (1st quarter) | January–March | April 20 |
| 2T (2nd quarter) | April–June | July 20 |
| 3T (3rd quarter) | July–September | October 20 |
| 4T (4th quarter) | October–December | January 30 (next year) |

If the deadline falls on a weekend or holiday, it moves to the next business day.

### Result types

- **A ingresar:** The autónomo owes money to AEAT. Must pay before the deadline via NRC, domiciliation, or card.
- **A compensar:** The result is negative. The negative balance carries forward to the next quarter's casilla 110.
- **A devolver:** Only available in Q4 (4T). The autónomo requests a refund of accumulated negative balance.
- **Sin actividad:** No invoices in the period. Still mandatory to file.

### ISP — Inversión del Sujeto Pasivo (Reverse Charge)

When an autónomo buys services from a foreign supplier without a Spanish NIF (e.g., Google Ireland, Adobe Systems):
- The foreign supplier does NOT charge Spanish IVA.
- The autónomo must self-assess the IVA: declare it as both devengado (charged) and soportado (deductible) in the same M303.
- Net effect is usually zero (it cancels out), but both sides must appear in the declaration.

### Deductibility rules

Not all IVA paid on purchases is deductible. Key rules:

| Expense | IVA deductible | Notes |
|---|---|---|
| Software / SaaS (professional use) | 100% | Must be exclusively professional |
| Mobile phone (mixed use) | 50% | Hacienda assumes 50/50 split |
| Vehicle (standard autónomo) | 50% | Only 100% if exclusively professional (hard to prove) |
| Restaurant / meals | 0% or 100% | 0% for general meals; 100% if strictly professional with documentation |
| Home office supplies | 100% | If exclusively professional use |
| RETA contribution | 0% | RETA has no IVA — but 100% deductible for IRPF |

**Critical:** the vehicle rule is a major source of user confusion. 50% IVA deductible but 0% IRPF deductible for most autónomos. The fiscal engine handles this separately.

---

## Proceso P09 — IRPF Fraccionado (Modelo 130)

Quarterly income tax prepayments. Key differences from P04:

- **Cumulative calculation:** M130 calculates from January 1st of the year, not just the current quarter.
- **Formula:** 20% of net income (ingresos − gastos including RETA contribution).
- **Subtracts previous payments:** Each quarter subtracts what was already paid in previous quarters of the same year.
- **No refund:** A negative M130 result carries to the next quarter (1T–3T) or to the annual tax return M100 (4T).
- **Exemption rule:** If ≥70% of the previous year's income had withholding tax (retención) applied by clients, the autónomo is exempt from M130 for the current year.

---

## Proceso P24 — Alta en RETA (Importass)

Registration with the Social Security as a self-employed worker. Key concepts:

- **RETA:** Régimen Especial de Trabajadores Autónomos — the special SS regime for self-employed workers.
- **NAF:** Número de Afiliación — unique SS identification number (12 digits).
- **Base de cotización:** Contribution base chosen by the autónomo within their income bracket. The monthly contribution is 31.5% of this base.
- **Tarifa plana:** Reduced flat fee of ~88.64€/month for the first 12 months for new autónomos. **CRITICAL: Must be requested at the time of registration — cannot be applied retroactively.**
- **Importass:** The TGSS digital portal where RETA registrations are processed.

### 2026 RETA contribution brackets (12 brackets)

The autónomo's monthly net income determines their bracket and minimum/maximum contribution base. The fiscal engine uses this table to suggest the appropriate bracket.

---

## Key Spanish fiscal terms (glossary)

| Spanish term | English equivalent | Context |
|---|---|---|
| Factura | Invoice | Standard commercial invoice |
| Factura emitida | Issued invoice | Invoice sent to a client |
| Factura recibida | Received invoice | Invoice from a supplier |
| Base imponible | Taxable base | Amount before VAT |
| Cuota / Cuota IVA | VAT amount | The tax amount itself |
| IVA repercutido | Output VAT / accrued VAT | VAT charged to clients |
| IVA soportado | Input VAT | VAT paid to suppliers |
| IVA deducible | Deductible input VAT | The portion of input VAT that can be offset |
| Rendimiento neto | Net income | Gross income minus deductible expenses |
| Retención | Withholding tax | Applied to professional invoices (7% or 15% IRPF) |
| Autoliquidación | Self-assessment | The autónomo calculates and pays their own tax |
| Presentación | Filing / Submission | Submitting a tax declaration to AEAT |
| Justificante | Proof of filing | PDF from AEAT confirming the submission |
| CSV | Secure verification code | 16-char code on the justificante PDF |
| NRC | Payment reference | 22-char code confirming payment to AEAT |
| Cl@ve PIN | Digital identity PIN | Short-lived PIN for authenticating with AEAT |
| Gestoría | Accounting firm | Traditional professional that handles tax compliance |
| Epígrafe IAE | Business activity code | 4-digit code classifying the autónomo's activity |
| CNAE | Industry classification code | 4-digit code (separate from IAE) |
| M036 | Census declaration form | Used to register with AEAT — process P01 |
| M303 | Quarterly VAT form | Process P04 |
| M130 | Quarterly income tax prepayment form | Process P09 |
| M100 | Annual income tax return | Process P14 (out of MVP scope) |
| M390 | Annual VAT summary | Process P08 (out of MVP scope) |

---

## What the agent must never do

- **Never calculate taxes using the LLM.** All calculations use the deterministic Python fiscal engine (`src/fiscal/`). The LLM explains results, it does not compute them.
- **Never present a declaration without explicit user confirmation.** The ConfirmacionModal click is mandatory. No exceptions.
- **Never assume deductibility.** When a purchase category is ambiguous, flag it with `requiere_confirmacion=True` and ask the user.
- **Never confuse the filing period with the coverage period.** The M130 filed in April covers January–March (acumulado desde enero). The M303 filed in April also covers January–March, but each quarter independently.

---

## Out of scope for MVP

These processes are documented in their Excel files but not implemented in V1:

- P01/P02 — AEAT census registration and modifications (M036)
- P05/P06/P07 — Q2/Q3/Q4 IVA (same logic as P04, different periods — implement after P04)
- P08 — Annual VAT summary (M390)
- P13 — Módulos regime (M131) — different calculation method
- P14 — Annual income tax return (M100)
- P25/P26 — Monthly RETA payment and contribution base changes
- Régimen foral (País Vasco, Navarra) — different tax authority, different forms
