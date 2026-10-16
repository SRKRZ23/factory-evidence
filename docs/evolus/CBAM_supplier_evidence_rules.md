# CBAM supplier evidence — rules used by Factory Evidence

Knowledge library for the Evolus agent "CBAM Supplier Follow-up". It states exactly what the Factory Evidence
validator checks, so the agent's answers and the app's decisions are the same. Sources at the end.

## 1. What CBAM costs per tonne (definitive period, from 1 January 2026)

certificates per tonne = max(0, SEE − CBAM factor(year) × benchmark Column B (CN code, production route))
cost per tonne = certificates per tonne × CBAM certificate price(year)

- **SEE** = specific embedded emissions in tCO2e per tonne of good.
- **If the supplier cannot prove its emissions**, the EU default value is used:
  default SEE = default value for the country and CN code × (1 + mark-up).
- **Mark-up on default values** (iron and steel, aluminium, cement, hydrogen): +10% in 2026, +20% in 2027, +30% from 2028.
  Fertilisers: +1% every year.
- **CBAM factor** (phase-out of free allocation): 2026 0.975 · 2027 0.95 · 2028 0.90 · 2029 0.775 · 2030 0.515 ·
  2031 0.39 · 2032 0.265 · 2033 0.14 · 2034 0.
- **Certificate price 2026**: €82.32 per tCO2e (EC published price, Q3 2026). Later years are scenarios, not facts.
- **Indirect emissions** are not counted for iron, steel and aluminium in the definitive period.

Worked example — steel slab from Indonesia, CN 7207 11 14, route C (blast furnace / basic oxygen furnace), 2026:
default value 8.23 × 1.10 = 9.053; benchmark 1.364; deduction 0.975 × 1.364 = 1.330.
EU default: (9.053 − 1.330) × €82.32 = **€635.77 per tonne**.
Verified supplier value 2.10: (2.10 − 1.330) × €82.32 = **€63.39 per tonne**.
Saving €572.37 per tonne, about €572,000 per 1,000 tonnes.

## 2. What the supplier must state (required fields)

installation name · installation country · CN code · production route (C, D, E for steel; K, L for aluminium) ·
specific direct embedded emissions (tCO2e/t) · reporting period start and end · whether the emissions are verified.
If verified: the name of the verification body (accredited verifier).
Helpful, used for cross-checks: total direct emissions of the installation (tCO2e), production volume (t),
carbon price effectively paid in the country of origin (€/tCO2e).

## 3. Decision rules (deterministic — no model decides)

Every supplier document ends in exactly one outcome:

- **ACCEPT** — all required fields present, verified by a named verifier, plausible, arithmetic consistent.
  The verified value replaces the EU default.
- **NEEDS_SUPPLIER** — something is missing or not verified. The agent writes to the supplier, in the supplier's
  language, listing exactly what is missing and what it costs per tonne to keep paying the default.
- **NEEDS_HUMAN** — a contradiction or an implausible value. A compliance officer must look. Never auto-accepted.

Checks:
| Check | Outcome if it fails |
|---|---|
| A required field is not stated | NEEDS_SUPPLIER |
| Emissions are self-declared (not verified) | NEEDS_SUPPLIER — only verified values can replace the default |
| "Verified" but no verifier named | NEEDS_SUPPLIER |
| Reporting period shorter than ~300 days, or older than two years before the import year | NEEDS_SUPPLIER |
| CN code or country not in the official EU default-value tables | NEEDS_HUMAN |
| Specific emissions ≤ 0 | NEEDS_HUMAN |
| Specific emissions below half of the EU benchmark for the route | NEEDS_HUMAN — too good to accept without checking the monitoring plan |
| Specific emissions above 1.5 × the EU default | NEEDS_HUMAN — probable unit error |
| Total emissions ÷ production differs from the stated specific value by more than 2% | NEEDS_HUMAN |
| Reporting period ends before it starts | NEEDS_HUMAN |
| Invoice origin differs from the installation country | NEEDS_HUMAN |

If actual emissions are not lower than the default value, the default is cheaper (information only).

## 4. How to write to a supplier

- Write in the supplier's language. Be short and specific.
- Name each missing or unverified item, the reporting period needed, and the CN code concerned.
- State the cost of inaction per tonne (EU default) and the cost with verified data, using only the figures given.
- Never invent numbers, deadlines or regulations. Never promise acceptance: a person approves every file.

## 5. Sources

- Default values: Commission Implementing Regulation (EU) 2025/2621, Annex I, as amended by (EU) 2026/1740
  (final update 06.08.2026).
- Benchmarks: Commission Implementing Regulation (EU) 2025/2620, Column B (CBAM Benchmarks 2026-02-06).
- CBAM factor: Directive 2003/87/EC, Article 10a(1a) phase-out schedule.
- Certificate price: European Commission published CBAM certificate price, 2026.
