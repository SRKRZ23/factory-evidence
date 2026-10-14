"""Deterministic checks on what the model extracted from a supplier document. The model reads; this
module decides whether the numbers can be used in a CBAM declaration, need the supplier, or need a person.

Decision per document
  ACCEPT          all required fields present, verified by an accredited verifier, plausible, consistent
  NEEDS_SUPPLIER  something is missing or unverified -> the agent drafts a request to the supplier
  NEEDS_HUMAN     contradiction or implausible value -> a compliance officer must look (never auto-accepted)
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date

from .calculator import benchmark, default_value, exposure

REQUIRED = ["installation_name", "installation_country", "cn_code", "production_route", "specific_direct_emissions",
            "reporting_period_start", "reporting_period_end", "verified"]
ROUTES = {"C": "blast furnace / basic oxygen furnace", "D": "direct reduced iron + electric arc furnace",
          "E": "scrap-based electric arc furnace", "K": "primary aluminium (electrolysis)", "L": "secondary aluminium (scrap)",
          "A": "grey clinker", "B": "white clinker"}


@dataclass
class Finding:
    severity: str          # info | supplier | human
    code: str
    message: str
    field: str | None = None


@dataclass
class Assessment:
    decision: str
    findings: list[Finding] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    exposure: dict | None = None
    usable_actual_see: float | None = None

    def to_json(self) -> dict:
        return asdict(self)


def _f(x):
    try:
        return None if x in (None, "", "null") else float(str(x).replace(",", "."))
    except ValueError:
        return None


def _d(x):
    try:
        return date.fromisoformat(str(x)[:10]) if x else None
    except ValueError:
        return None


def assess(doc: dict, import_year: int = 2026, tonnes: float | None = None, origin_country: str | None = None) -> Assessment:
    """`doc` = extracted fields (plain values). Returns decision, findings and € exposure (default vs usable actual)."""
    F: list[Finding] = []
    missing = [k for k in REQUIRED if doc.get(k) in (None, "", "null")]
    for k in missing:
        F.append(Finding("supplier", "missing_field", f"{k.replace('_', ' ')} is not stated in the document", k))

    country, cn = doc.get("installation_country"), doc.get("cn_code")
    route = (doc.get("production_route") or "").strip("() ").upper() or None
    see = _f(doc.get("specific_direct_emissions"))
    usable = None
    exp = None

    if country and cn:
        try:
            dv = default_value(country, cn)
        except KeyError as e:
            F.append(Finding("human", "unknown_good_or_country", str(e), "cn_code"))
            dv = None
        if dv:
            if dv.get("other_countries_fallback"):
                F.append(Finding("info", "other_countries_default", f"no country-specific default for {country}; EC 'other countries' value applies"))
            if route and route not in ROUTES:
                F.append(Finding("supplier", "unknown_route", f"production route '{route}' is not a CBAM route code", "production_route"))
            if see is not None:
                bm, r = benchmark(cn, route or dv["route"])
                if see <= 0:
                    F.append(Finding("human", "non_positive", "specific emissions must be positive", "specific_direct_emissions"))
                elif bm and see < 0.5 * bm:
                    F.append(Finding("human", "implausibly_low",
                                     f"{see} tCO2e/t is below half of the EU benchmark for route {r or '-'} ({bm}); "
                                     "too good to accept without a person checking the monitoring plan", "specific_direct_emissions"))
                elif see > dv["total"] * 1.5:
                    F.append(Finding("human", "implausibly_high", f"{see} tCO2e/t is far above the EU default ({dv['total']}); unit error?",
                                     "specific_direct_emissions"))
                elif see >= dv["total"]:
                    F.append(Finding("info", "above_default", "actual emissions are not lower than the default value; the default is cheaper"))
            # arithmetic cross-check if the supplier also gives totals
            tot, prod = _f(doc.get("total_direct_emissions_t")), _f(doc.get("production_volume_t"))
            if see is not None and tot and prod:
                calc = tot / prod
                if abs(calc - see) / calc > 0.02:
                    F.append(Finding("human", "arithmetic_mismatch",
                                     f"stated {see} tCO2e/t but totals give {calc:.3f} ({tot:g} t / {prod:g} t)", "specific_direct_emissions"))

    # verification: in the definitive period actual emissions must be verified by an accredited verifier
    verified = str(doc.get("verified", "")).lower() in ("true", "yes", "1", "verified")
    if doc.get("verified") not in (None, "") and not verified:
        F.append(Finding("supplier", "not_verified", "emissions are self-declared; only values verified by an accredited verifier "
                                                     "can replace the default", "verified"))
    if verified and not doc.get("verifier_name"):
        F.append(Finding("supplier", "verifier_unknown", "document says verified but does not name the verifier / accreditation", "verifier_name"))

    # reporting period
    p0, p1 = _d(doc.get("reporting_period_start")), _d(doc.get("reporting_period_end"))
    if p0 and p1:
        if p1 <= p0:
            F.append(Finding("human", "period_inverted", "reporting period ends before it starts", "reporting_period_end"))
        elif (p1 - p0).days < 300:
            F.append(Finding("supplier", "short_period", f"reporting period covers {(p1 - p0).days} days; a full year is expected",
                             "reporting_period_start"))
        if p1.year < import_year - 2:
            F.append(Finding("supplier", "stale_period", f"emissions data is from {p1.year}; too old for {import_year} imports",
                             "reporting_period_end"))

    if origin_country and country and origin_country.upper() != str(country).upper():
        F.append(Finding("human", "origin_mismatch", f"invoice origin {origin_country} differs from installation country {country}",
                         "installation_country"))
    if cn and str(cn).startswith(("72", "73", "76")) and _f(doc.get("specific_indirect_emissions")):
        F.append(Finding("info", "indirect_ignored", "indirect emissions are not counted for iron/steel/aluminium in the definitive period"))

    blocking_human = any(f.severity == "human" for f in F)
    blocking_supplier = any(f.severity == "supplier" for f in F)
    decision = "NEEDS_HUMAN" if blocking_human else ("NEEDS_SUPPLIER" if blocking_supplier else "ACCEPT")
    if decision == "ACCEPT" and see is not None:
        usable = see
    if country and cn:
        try:
            e = exposure(country, cn, import_year, actual_see=usable, route=route)
            exp = {**e.__dict__, **({"totals": e.total(tonnes)} if tonnes else {})}
            if usable is None:  # show what verified data WOULD save, clearly labelled as potential
                pot = see if (see is not None and not blocking_human) else None
                if pot is not None:
                    ep = exposure(country, cn, import_year, actual_see=pot, route=route)
                    exp["potential_eur_per_t_if_verified"] = ep.eur_per_t_actual
                    exp["potential_saving_eur_per_t"] = ep.saving_eur_per_t
        except KeyError:
            pass
    return Assessment(decision, F, missing, exp, usable)
