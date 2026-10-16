"""HTTP API + static UI.

  GET  /api/status              live AMD model? Evolus connected? which models
  GET  /api/samples             synthetic supplier documents
  GET  /api/samples/{id}.png    the scan
  POST /api/analyze/{id}        read -> validate -> € exposure -> supplier letter (cached per run)
  POST /api/upload              same for an uploaded image
  GET  /api/portfolio           importer view: all shipments, € default vs usable actual vs potential
  GET  /api/bench               per-call latency / tokens on the AMD-served model
"""
from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .cbam.validator import assess
from .evolus import Evolus
from .extract.cbam_doc import extract, extract_demo, reread_cn
from .extract.letters import LANG_NAME, draft
from .extract.letters import facts as letter_facts
from .llm import AMDModel

ROOT = Path(__file__).resolve().parents[2]
SAMPLES = ROOT / "data" / "samples"
WEB = ROOT / "web"

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

app = FastAPI(title="Factory Evidence Agent")
MODEL = AMDModel()
EVOLUS = Evolus()
CACHE: dict[str, dict] = {}
APPROVALS: dict[str, dict] = {}   # the person's decision on each supplier request (never automatic)
FORCE_DEMO = os.getenv("DEMO_MODE", "") == "1"


def register() -> dict:
    """Importer's quarterly register (from the Italian fattura sample): supplier country+CN -> tonnes."""
    t = json.loads((SAMPLES / "07_fattura_acciai_liguri.truth.json").read_text())["truth"]["shipments"]
    return {(s["country"], s["cn"][:4]): s for s in t}


def live() -> bool:
    return MODEL.live and not FORCE_DEMO


def cn_candidates(country: str | None, code: str) -> list[str]:
    """Real CN codes of the same 6-digit heading in the official default-value table for this country."""
    from .cbam import calculator as C
    d = "".join(ch for ch in str(code) if ch.isdigit())[:6]
    if len(d) < 6 or not country:
        return []
    try:
        keys = C.tables()["default_values"][C._country_sheet(country)]
    except KeyError:
        return []
    fmt = lambda k: " ".join([k[:4], k[4:6], k[6:8]] + ([k[8:10]] if len(k) >= 10 else []))  # noqa: E731
    return [fmt(k) for k in sorted(keys) if k.startswith(d) and len(k) >= 8][:12]


def analyze_path(path: Path, key: str) -> dict:
    t0 = time.perf_counter()
    if live():
        try:
            ex = extract(path, MODEL)
        except Exception as e:  # never break the demo: fall back, and say so
            ex = {**extract_demo(path), "error": f"live model failed: {type(e).__name__}: {str(e)[:200]}"} if path.name[:2].isdigit() else {"error": str(e)}
    else:
        ex = extract_demo(path)
    v = ex.get("values") or {}
    reg = register().get((str(v.get("installation_country") or ""), str(v.get("cn_code") or "")[:4]))
    tonnes = reg["tonnes"] if reg else None
    a = assess(v, import_year=2026, tonnes=tonnes).to_json()
    # Rules-guided re-read: a CN code that does not exist in the official tables is almost always a misread digit.
    if live() and v.get("cn_code") and any(f.get("code") == "unknown_good_or_country" and f.get("field") == "cn_code" for f in a["findings"]):
        cands = cn_candidates(v.get("installation_country"), v["cn_code"])
        if cands:
            try:
                rr = reread_cn(path, MODEL, v["cn_code"], cands)
            except Exception as e:
                rr = {"cn_code": None, "printed": None, "error": f"{type(e).__name__}: {str(e)[:150]}"}
            ex["reread"] = {"field": "cn_code", "first_read": v["cn_code"], "candidates": cands, **rr}
            if rr.get("cn_code"):
                first = v["cn_code"]
                v = {**v, "cn_code": rr["cn_code"]}
                ex["values"] = v
                a = assess(v, import_year=2026, tonnes=tonnes).to_json()
                a["findings"].append({"severity": "info", "code": "cn_code_corrected_on_reread", "field": "cn_code",
                                      "message": f"First reading {first} is not in the official EU tables; a second, closed-set reading "
                                                 f"chose {rr['cn_code']} (printed: {rr.get('printed')}). Check against the document."})
    letter = None
    if a["decision"] != "ACCEPT":
        lang = ex.get("language") or "en"
        if live() and EVOLUS.agent_ready:
            # The Evolus agent "CBAM Supplier Follow-up" writes the request, on the space's own model (Gemma on AMD),
            # from the validator's facts only. Falls back to a direct model call if Evolus does not answer.
            f = letter_facts(v, a, "Acciai Liguri S.r.l.", tonnes)
            try:
                body = EVOLUS.agent_reply(f"Language: {LANG_NAME.get(lang, 'English')}\n\nFACTS:\n{f}")
                letter = {"language": LANG_NAME.get(lang, "English"), "body": body.strip(), "facts": f,
                          "source": "evolus-agent", "model": f"{MODEL.model} on AMD via Evolus agent"}
            except Exception as e:
                letter = {**draft(v, a, lang, MODEL, tonnes=tonnes), "evolus_error": f"{type(e).__name__}: {str(e)[:150]}"}
        else:
            letter = draft(v, a, lang, MODEL if live() else None, tonnes=tonnes)
            if EVOLUS.connected and letter["source"] == "demo":
                try:
                    letter = {**letter, "body": EVOLUS.translate(letter["body"], lang), "source": "evolus-translate"}
                except Exception as e:
                    letter["evolus_error"] = str(e)[:200]
    pack = None
    if EVOLUS.connected and not key.startswith("upload:"):
        # Evidence file for the auditor: values with their verbatim quotes, personal data removed by Evolus AI Tool "anonymize".
        lines = [f"Supplier evidence file · decision {a['decision']}"] + [
            f"- {k.replace('_', ' ')}: {val}" + (f'  (quote: "{(ex.get("evidence") or {}).get(k)}")' if (ex.get("evidence") or {}).get(k) else "")
            for k, val in v.items() if val not in (None, "")] + [f"- check: {fd['message']}" for fd in a["findings"]]
        try:
            pack = {"body": EVOLUS.anonymize("\n".join(lines)), "source": "evolus-anonymize"}
        except Exception as e:
            pack = {"body": None, "source": "evolus-anonymize", "error": f"{type(e).__name__}: {str(e)[:150]}"}
    out = {"id": key, "extraction": ex, "assessment": a, "letter": letter, "auditor_pack": pack, "tonnes": tonnes,
           "approval": APPROVALS.get(key), "seconds": round(time.perf_counter() - t0, 2)}
    CACHE[key] = out
    return out


@app.get("/api/status")
def status():
    return {"live_model": live(), "model": MODEL.model or None, "vision_model": MODEL.vision_model or None,
            "endpoint": MODEL.base_url.split("//")[-1].split("/")[0] if MODEL.base_url else None,
            "evolus_connected": EVOLUS.connected, "evolus_agent": EVOLUS.agent_ready, "demo_mode": not live()}


@app.get("/api/samples")
def samples():
    return json.loads((SAMPLES / "manifest.json").read_text())


@app.get("/api/samples/{sid}.png")
def sample_png(sid: str):
    p = SAMPLES / f"{sid}.png"
    if not p.exists():
        raise HTTPException(404)
    return FileResponse(p, media_type="image/png")


@app.post("/api/analyze/{sid}")
def analyze(sid: str, refresh: bool = False):
    p = SAMPLES / f"{sid}.png"
    if not p.exists():
        raise HTTPException(404)
    if sid in CACHE and not refresh:
        return CACHE[sid]
    return analyze_path(p, sid)


@app.post("/api/upload")
async def upload(file: UploadFile):
    if not live():
        raise HTTPException(400, "uploads need the live AMD model (demo mode only analyses the bundled samples)")
    suffix = Path(file.filename or "doc.png").suffix.lower() or ".png"
    if suffix not in (".png", ".jpg", ".jpeg"):
        raise HTTPException(400, "send a PNG or JPEG scan/photo")
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(await file.read())
    return analyze_path(Path(f.name), f"upload:{file.filename}")


@app.get("/api/portfolio")
def portfolio():
    rows, tot = [], {"tonnes": 0, "eur_default": 0.0, "eur_with_evidence": 0.0, "eur_if_suppliers_verify": 0.0}
    for m in samples():
        if not m.get("expect"):
            continue
        r = CACHE.get(m["id"]) or analyze(m["id"])
        a, t = r["assessment"], r["tonnes"]
        e = a.get("exposure") or {}
        if not t or not e:
            rows.append({"id": m["id"], "decision": a["decision"], "tonnes": t})
            continue
        d = e["eur_per_t_default"] * t
        act = (e["eur_per_t_actual"] if e.get("eur_per_t_actual") is not None else e["eur_per_t_default"]) * t
        pot = (e.get("potential_eur_per_t_if_verified") or e.get("eur_per_t_actual") or e["eur_per_t_default"]) * t
        tot["tonnes"] += t; tot["eur_default"] += d; tot["eur_with_evidence"] += act; tot["eur_if_suppliers_verify"] += pot
        rows.append({"id": m["id"], "decision": a["decision"], "tonnes": t, "eur_default": round(d), "eur_with_evidence": round(act),
                     "eur_if_suppliers_verify": round(pot)})
    return {"rows": rows, "totals": {k: round(v) for k, v in tot.items()}}


@app.get("/api/bench")
def bench():
    s = MODEL.stats
    if not s:
        return {"calls": 0}
    ex = [c for c in s if c.task == "extract"]
    return {"calls": len(s), "model": MODEL.vision_model, "endpoint": status()["endpoint"],
            "extract_seconds_median": sorted(c.seconds for c in ex)[len(ex) // 2] if ex else None,
            "pages_per_minute": round(60 / (sum(c.seconds for c in ex) / len(ex)), 1) if ex else None,
            "completion_tok_per_s_median": sorted(c.tok_per_s for c in s)[len(s) // 2],
            "tokens": sum(c.prompt_tokens + c.completion_tokens for c in s),
            "recent": [c.__dict__ for c in s[-10:]]}


ENERGY_CSV = SAMPLES / "energy_line3_15min.csv"
DOSSIER_SYSTEM = """You draft a short technical note (Italian, then a 3-line English summary) for a certified energy manager (EGE)
preparing the Transizione 5.0 ex-post energy-saving certification. Use ONLY the measured figures given; do not invent numbers or legal
claims; state the method (baseline regression on production, weather and hour-of-week; IPMVP Option C style) and the 95% interval;
end with what the EGE still has to check on site. Max 200 words."""


@app.get("/api/energy")
def energy():
    from dataclasses import asdict
    from .energy.baseline import load, measure, synth
    if not ENERGY_CSV.exists():
        synth(ENERGY_CSV)
    r = {k: (float(v) if hasattr(v, "dtype") else (tuple(float(x) for x in v) if isinstance(v, tuple) else v))
         for k, v in asdict(measure(load(ENERGY_CSV))).items()}
    r = {k: (bool(v) if k.startswith("meets") else v) for k, v in r.items()}
    facts = (f"Line 3 (compressed air + extrusion), inverter retrofit. Post period {r['days']} days, {r['intervals']} intervals of 15 min. "
             f"Baseline {r['baseline_mwh']} MWh, metered {r['metered_mwh']} MWh, saving {r['saving_mwh']} MWh = {r['saving_pct']} % "
             f"(95% interval {r['ci95_pct'][0]}–{r['ci95_pct'][1]} %), baseline model R2 {r['r2']}. "
             f"Thresholds: process 3 % {'met' if r['meets_process_3pct'] else 'not met'}, site 5 % {'met' if r['meets_site_5pct'] else 'not met'}. "
             f"Energy cost saved ~EUR {r['eur_saved_year']:,} per year at EUR 146.6/MWh.")
    if live():
        note = MODEL.chat("dossier", [{"role": "system", "content": DOSSIER_SYSTEM}, {"role": "user", "content": facts}], temperature=0.2, max_tokens=700)
        src = "live"
    else:
        note = ("Nota tecnica per l'EGE — Linea 3 (aria compressa + estrusione), retrofit inverter.\n" + facts +
                "\nVerifiche in sito a cura dell'EGE: perimetro di misura, taratura contatori, assenza di altre modifiche nel periodo.")
        src = "demo"
    return {"result": r, "facts": facts, "dossier": note, "source": src, "data": "synthetic 15-min meter data (fictional plant)"}


@app.post("/api/approve/{sid}")
def approve(sid: str, who: str = "compliance officer"):
    """A person approves the supplier request before anything is sent: the human step is recorded, never automatic."""
    if sid not in CACHE:
        raise HTTPException(404, "analyse the document first")
    APPROVALS[sid] = {"by": who, "at": time.strftime("%Y-%m-%d %H:%M:%S")}
    CACHE[sid]["approval"] = APPROVALS[sid]
    return APPROVALS[sid]


@app.get("/api/evolus-log")
def evolus_log():
    return EVOLUS.log[-50:]


if WEB.exists():
    app.mount("/", StaticFiles(directory=str(WEB), html=True), name="web")
