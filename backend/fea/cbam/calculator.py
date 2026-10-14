"""CBAM certificate cost per tonne of imported good — default values vs verified actual emissions.

certificates/t = max(0, SEE − CBAM_factor(year) × Benchmark_ColumnB(CN, route))
  default SEE = DV_total(country, CN) × (1 + markup(sector, year))     (Impl. Reg. 2025/2621 Art. 4, as amended)
  actual SEE  = verified specific embedded emissions reported by the installation
cost/t = certificates/t × certificate price(year)

Sources (official EC files in data/eu, parsed by scripts/build_cbam_tables.py):
  default values: DV correcting act final update 06.08.2026 (Annex I 2025/2621 as amended by 2026/1740)
  benchmarks:     CBAM Benchmarks 2026-02-06 (Impl. Reg. 2025/2620), Column B
  CBAM factor:    Directive 2003/87/EC Art. 10a(1a) phase-out schedule
  price:          2026 = EC published CBAM certificate price; later years = Reuters analyst poll 31.07.2026 (scenario)
Ported from ~/Alish/cbam-presentation/cbam-model.js (verified against the research tables to ±€1/t).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

TABLES = Path(__file__).resolve().parents[3] / "data" / "eu" / "cbam_tables.json"
YEARS = list(range(2026, 2035))
MARKUP_METAL = {2026: 0.10, 2027: 0.20}           # 0.30 from 2028 on (cement, iron & steel, aluminium, hydrogen)
MARKUP_FERT = 0.01                                 # fertilisers: 1 % every year
CBAM_FACTOR = {2026: 0.975, 2027: 0.95, 2028: 0.90, 2029: 0.775, 2030: 0.515, 2031: 0.39, 2032: 0.265, 2033: 0.14, 2034: 0.0}
PRICE = {
    "base": {2026: 82.32, 2027: 89.13, 2028: 95.37, 2029: 100.43, 2030: 109.11, 2031: 114, 2032: 119, 2033: 124, 2034: 129},
    "low": {y: 75.0 for y in YEARS},
    "high": {2026: 82.32, 2027: 100, 2028: 115, 2029: 130, 2030: 145, 2031: 155, 2032: 165, 2033: 175, 2034: 185},
}
# ISO-2 -> sheet name in the EC default-value workbook (extend as needed)
COUNTRY = {"CN": "China", "IN": "India", "ID": "Indonesia", "TR": "Türkiye", "UA": "Ukraine", "KR": "Korea, Republic of (South Korea",
           "VN": "Viet Nam", "EG": "Egypt", "BR": "Brazil", "RU": "Russian Federation", "UZ": "Uzbekistan", "KZ": "Kazakhstan",
           "AZ": "Azerbaijan", "TW": "Taiwan", "JP": "Japan", "US": "United States", "GB": "United Kingdom", "ZA": "South Africa",
           "MY": "Malaysia", "TH": "Thailand", "SA": "Saudi Arabia", "AE": "United Arab Emirates", "DZ": "Algeria", "MA": "Morocco",
           "TN": "Tunisia", "RS": "Serbia", "BA": "Bosnia and Herzegovina", "MK": "North Macedonia", "AL": "Albania", "ME": "Montenegro"}


@lru_cache(maxsize=1)
def tables() -> dict:
    return json.loads(TABLES.read_text())


def sector(cn: str) -> str:
    return "fertiliser" if cn[:4] in ("2808", "2814", "3102", "3105") else "metal"


def markup(cn: str, year: int) -> float:
    return MARKUP_FERT if sector(cn) == "fertiliser" else MARKUP_METAL.get(year, 0.30)


def _country_sheet(country: str) -> str:
    t = tables()["default_values"]
    if country in t:
        return country
    name = COUNTRY.get(country.upper())
    if name and name in t:
        return name
    for k in t:  # tolerant match, e.g. "Turkey" vs "Türkiye"
        if k.lower().startswith(country.lower()[:5]):
            return k
    raise KeyError(f"no CBAM default values for country {country!r}")


def _prefix_lookup(table: dict, cn: str):
    d = "".join(ch for ch in cn if ch.isdigit())
    for n in (len(d), 10, 8, 6, 4):
        if d[:n] in table:
            return d[:n], table[d[:n]]
    # heading-level code (e.g. 7208) against a table keyed by CN8: take the first more specific entry
    for k in sorted(table):
        if k.startswith(d):
            return k, table[k]
    return None, None


def default_value(country: str, cn: str) -> dict:
    sheet = _country_sheet(country)
    code, row = _prefix_lookup(tables()["default_values"][sheet], cn)
    fallback = False
    if row is None:  # country has no value for this good -> EC "Other Countries and Territories" table applies
        other = next(k for k in tables()["default_values"] if k.startswith("_Other"))
        code, row = _prefix_lookup(tables()["default_values"][other], cn)
        fallback = True
        if row is None:
            raise KeyError(f"no default value for CN {cn} ({sheet} or other countries)")
    return {**row, "cn_matched": code, "country": sheet, "other_countries_fallback": fallback}


def benchmark(cn: str, route: str | None) -> tuple[float, str]:
    code, row = _prefix_lookup(tables()["benchmarks_b"], cn)
    if row is None:
        raise KeyError(f"no CBAM benchmark for CN {cn}")
    route = (route or "").strip("() ").upper()
    if route in row:
        return row[route], route
    if "" in row:
        return row[""], ""
    first = next(iter(row))
    return row[first], first


@dataclass
class Exposure:
    cn: str
    country: str
    year: int
    default_see: float          # tCO2e/t after mark-up
    actual_see: float | None
    benchmark: float
    route: str
    certs_default: float        # certificates per tonne
    certs_actual: float | None
    eur_per_t_default: float
    eur_per_t_actual: float | None
    saving_eur_per_t: float | None
    price: float

    def total(self, tonnes: float) -> dict:
        d = self.eur_per_t_default * tonnes
        a = None if self.eur_per_t_actual is None else self.eur_per_t_actual * tonnes
        return {"tonnes": tonnes, "eur_default": round(d, 2), "eur_actual": None if a is None else round(a, 2),
                "eur_saving": None if a is None else round(d - a, 2)}


def exposure(country: str, cn: str, year: int = 2026, actual_see: float | None = None, route: str | None = None,
             scenario: str = "base") -> Exposure:
    dv = default_value(country, cn)
    bm_default, r_default = benchmark(cn, dv["route"])
    see_def = dv["total"] * (1 + markup(cn, year))
    f = CBAM_FACTOR[year]
    p = PRICE[scenario][year]
    c_def = max(0.0, see_def - f * bm_default)
    c_act = None
    bm, r = bm_default, r_default
    if actual_see is not None:
        bm, r = benchmark(cn, route or dv["route"])
        c_act = max(0.0, actual_see - f * bm)
    e_def = c_def * p
    e_act = None if c_act is None else c_act * p
    return Exposure(dv["cn_matched"], dv["country"], year, round(see_def, 4), actual_see, bm, r, round(c_def, 4),
                    None if c_act is None else round(c_act, 4), round(e_def, 2), None if e_act is None else round(e_act, 2),
                    None if e_act is None else round(e_def - e_act, 2), p)


def trajectory(country: str, cn: str, actual_see: float | None = None, route: str | None = None, scenario: str = "base") -> list[dict]:
    return [{"year": y, **{k: v for k, v in exposure(country, cn, y, actual_see, route, scenario).__dict__.items()
                           if k in ("eur_per_t_default", "eur_per_t_actual", "saving_eur_per_t")}} for y in YEARS]
