"""Draft the request to the supplier, in the supplier's language, from the validator's findings only.
The model phrases; the facts (what is missing, why, what it costs) come from deterministic code."""
from __future__ import annotations

from ..llm import AMDModel

LANG_NAME = {"zh": "Chinese (Simplified)", "tr": "Turkish", "id": "Indonesian", "vi": "Vietnamese", "uk": "Ukrainian", "en": "English",
             "it": "Italian", "hi": "English", "ru": "Russian", "ar": "Arabic", "ko": "Korean"}

SYSTEM = """You write short, polite, precise business emails from an EU steel importer's compliance team to a foreign supplier.
Write in the requested language only. Use ONLY the facts given; do not invent numbers, deadlines or regulations.
Structure: greeting; one sentence of context (EU CBAM, definitive period 2026); a numbered list of exactly what is needed and why;
one sentence on the cost impact for the buyer; ask for the corrected/verified communication using the EU template; sign-off.
Max 180 words. Return only the email body."""


def facts(values: dict, assessment: dict, buyer: str, tonnes: float | None) -> str:
    asks = [f["message"] for f in assessment["findings"] if f["severity"] in ("supplier", "human")]
    exp = assessment.get("exposure") or {}
    lines = [f"Buyer: {buyer}", f"Supplier installation: {values.get('installation_name')}", f"Good: CN {values.get('cn_code') or 'unknown'}",
             "What is needed:"] + [f"- {a}" for a in asks]
    if exp.get("eur_per_t_default") is not None:
        lines.append(f"Without usable verified data the buyer must apply the EU default: EUR {exp['eur_per_t_default']:.0f} per tonne in {exp['year']}.")
    if exp.get("potential_saving_eur_per_t"):
        lines.append(f"With verified data at the stated level the cost would fall by about EUR {exp['potential_saving_eur_per_t']:.0f} per tonne.")
    if tonnes:
        lines.append(f"Quarterly volume from this supplier: {tonnes:,.0f} t.")
    return "\n".join(lines)


def draft(values: dict, assessment: dict, lang: str, model: AMDModel | None, buyer: str = "Acciai Liguri S.r.l.", tonnes: float | None = None) -> dict:
    f = facts(values, assessment, buyer, tonnes)
    language = LANG_NAME.get(lang or "en", "English")
    if model is not None and model.live:
        body = model.chat("letter", [{"role": "system", "content": SYSTEM},
                                     {"role": "user", "content": f"Language: {language}\n\nFACTS:\n{f}"}], temperature=0.2, max_tokens=600)
        return {"language": language, "body": body.strip(), "facts": f, "source": "live", "model": model.model}
    body = (f"Dear colleagues,\n\nUnder the EU CBAM definitive period (2026) we need the following from {values.get('installation_name')}:\n"
            + "\n".join(f"{i+1}. {a}" for i, a in enumerate(l[2:] for l in f.splitlines() if l.startswith("- ")))
            + "\n\nPlease send a corrected communication using the EU template for installations.\n\nKind regards,\nCBAM compliance team, " + buyer)
    return {"language": "English (template; live model translates to " + language + ")", "body": body, "facts": f, "source": "demo", "model": None}
