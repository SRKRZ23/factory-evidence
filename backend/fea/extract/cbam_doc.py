"""Read a supplier emissions document (scan/photo/PDF page image) with an open vision model on AMD and
return normalised fields + verbatim evidence for each value. No value without evidence; no guessing."""
from __future__ import annotations

import json
import re
from pathlib import Path

from ..llm import AMDModel, image_part, parse_json

FIELDS = {
    "installation_name": "name of the production installation (as written)",
    "installation_country": "ISO 3166-1 alpha-2 code of the installation's country",
    "cn_code": "Combined Nomenclature code of the good, digits with spaces as written, e.g. '7207 11 14'",
    "good_description": "short description of the good",
    "production_route": "CBAM production route letter: C = BF-BOF, D = DRI-EAF, E = scrap EAF, K = primary aluminium, L = secondary aluminium; null if not stated",
    "specific_direct_emissions": "specific direct embedded emissions in tCO2e per tonne of good (number)",
    "specific_indirect_emissions": "specific indirect embedded emissions in tCO2e per tonne (number) if stated",
    "total_direct_emissions_t": "total direct emissions of the installation in tCO2e (number) if stated",
    "production_volume_t": "production volume in tonnes (number) if stated",
    "reporting_period_start": "ISO date YYYY-MM-DD",
    "reporting_period_end": "ISO date YYYY-MM-DD",
    "verified": "true if the emissions are verified by a third-party verifier, false if self-declared, null if not stated",
    "verifier_name": "name of the verification body",
    "carbon_price_paid": "carbon price effectively paid in the country of origin, in EUR per tCO2e (number) if stated",
}

SYSTEM = """You read supplier documents for EU CBAM compliance (Carbon Border Adjustment Mechanism). The document may be in any
language (Chinese, Turkish, Indonesian, Vietnamese, Ukrainian, English, Italian...). Extract the fields below.

Rules:
- Return ONLY a JSON object: {"fields": {<name>: {"value": ..., "evidence": "<verbatim text copied from the document>"}}, "language": "<ISO 639-1>", "document_type": "<short>"}
- evidence must be copied exactly as printed (original language). If a field is not present, use {"value": null, "evidence": null}.
- Never infer a value that is not printed. A dash "—" means not stated.
- Numbers: use a dot as decimal separator, no thousands separators (e.g. "3 360 000" -> 3360000, "2,10" -> 2.1).
- Dates: ISO YYYY-MM-DD; a fiscal year like "April 2025 – March 2026" -> start 2025-04-01, end 2026-03-31.
- Country: ISO alpha-2 of the installation (not of the buyer).
Fields:
""" + "\n".join(f"- {k}: {v}" for k, v in FIELDS.items())

NUM_FIELDS = {"specific_direct_emissions", "specific_indirect_emissions", "total_direct_emissions_t", "production_volume_t", "carbon_price_paid"}


def _num(v):
    """First number in the string: '2,10 tCO2e / t' -> 2.1; '3 360 000 tCO2e' -> 3360000; '1,234.5' -> 1234.5."""
    if v is None or isinstance(v, (int, float)):
        return v
    m = re.search(r"-?\d{1,3}(?:[ \u00a0\u202f]\d{3})+(?:[.,]\d+)?|-?\d+(?:[.,]\d+)*", str(v))
    if not m:
        return None
    s = re.sub(r"[ \u00a0\u202f]", "", m.group(0))
    if "," in s and "." in s:          # 1,234.5 or 1.234,5
        s = s.replace(",", "") if s.rfind(".") > s.rfind(",") else s.replace(".", "").replace(",", ".")
    elif s.count(",") == 1 and len(s.split(",")[1]) != 3:
        s = s.replace(",", ".")       # decimal comma
    else:
        s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


COUNTRY_NAMES = {"indonesia": "ID", "china": "CN", "中国": "CN", "india": "IN", "türkiye": "TR", "turkey": "TR", "turkiye": "TR",
                 "viet nam": "VN", "vietnam": "VN", "việt nam": "VN", "ukraine": "UA", "україна": "UA", "egypt": "EG", "korea": "KR",
                 "brazil": "BR", "italy": "IT", "italia": "IT", "uzbekistan": "UZ", "kazakhstan": "KZ", "russia": "RU"}


def _country(v: str) -> str | None:
    m = re.search(r"\(([A-Za-z]{2})\)", v)
    if m:
        return m.group(1).upper()
    t = v.strip()
    if re.fullmatch(r"[A-Za-z]{2}", t):
        return t.upper()
    low = t.lower()
    for name, code in COUNTRY_NAMES.items():
        if name in low:
            return code
    return None


def normalise(raw: dict) -> tuple[dict, dict]:
    """-> (values, evidence)"""
    fields = raw.get("fields", raw)
    values, evidence = {}, {}
    for k in FIELDS:
        item = fields.get(k)
        v, ev = (item.get("value"), item.get("evidence")) if isinstance(item, dict) else (item, None)
        if isinstance(v, str) and v.strip() in ("", "—", "-", "null", "N/A"):
            v = None
        if k in NUM_FIELDS:
            v = _num(v)
        if k == "verified" and isinstance(v, str):
            v = v.strip().lower() in ("true", "yes", "verified")
        if k == "production_route" and isinstance(v, str):
            m = re.search(r"\b([CDEKLAB])\b", v.upper())
            v = m.group(1) if m else None
        if k == "installation_country" and isinstance(v, str):
            v = _country(v)
        values[k], evidence[k] = v, ev
    return values, evidence


COMPACT_RULES = """
Output size rules (strict):
- OMIT every field that is not present in the document (do not write null entries).
- Output minified JSON on one line, no spaces after ':' or ','.
- evidence: the shortest verbatim span that contains the value (the number with its unit, or the name), not the whole line."""


def extract(path: Path, model: AMDModel) -> dict:
    import os
    system = SYSTEM + (COMPACT_RULES if os.getenv("FEA_COMPACT") == "1" else "")
    content = [{"type": "text", "text": "Extract the CBAM fields from this supplier document."}, image_part(path)]
    text = model.chat("extract", [{"role": "system", "content": system}, {"role": "user", "content": content}], vision=True, max_tokens=1800)
    raw = parse_json(text)
    values, evidence = normalise(raw)
    return {"values": values, "evidence": evidence, "language": raw.get("language"), "document_type": raw.get("document_type"),
            "source": "live", "model": model.vision_model}


REREAD_SYSTEM = """You re-read ONE field of a supplier document: the Combined Nomenclature (CN) code of the good.
A first reading produced a code that does not exist in the official EU CBAM tables. Look at the document again and read the CN code
digit by digit. Answer ONLY with a JSON object: {"cn_code": "<one of the candidates exactly as listed, or NONE>", "printed": "<the digits exactly as printed>"}.
Choose NONE if the printed code is not one of the candidates. Never pick a candidate that is not what is printed."""


def reread_cn(path: Path, model: AMDModel, first_read: str, candidates: list[str]) -> dict:
    """Rules-guided re-read: the validator found no such CN code in the official tables, so ask the model to choose
    among the real codes of the same 6-digit heading (closed set) or NONE. One extra call, only on flagged documents."""
    content = [{"type": "text", "text": f"First reading: {first_read}\nCandidates (official EU tables, same heading): {', '.join(candidates)}"},
               image_part(path)]
    text = model.chat("reread_cn", [{"role": "system", "content": REREAD_SYSTEM}, {"role": "user", "content": content}],
                      vision=True, max_tokens=200)
    raw = parse_json(text)
    digits = lambda s: "".join(ch for ch in str(s or "") if ch.isdigit())  # noqa: E731
    by_digits = {digits(c): c for c in candidates}
    # Accept only an official candidate: either the model's pick, or the digits it says are printed.
    choice = by_digits.get(digits(raw.get("cn_code"))) or by_digits.get(digits(raw.get("printed")))
    return {"cn_code": choice, "printed": raw.get("printed"), "model_pick": raw.get("cn_code")}


def extract_demo(path: Path) -> dict:
    """Offline demo: ground truth of the synthetic sample, clearly labelled as demo data."""
    t = json.loads(Path(str(path).rsplit(".", 1)[0] + ".truth.json").read_text())
    vals = {k: t["truth"].get(k) for k in FIELDS}
    return {"values": vals, "evidence": {k: None for k in FIELDS}, "language": t.get("lang"), "document_type": "supplier emissions communication",
            "source": "demo", "model": None}
