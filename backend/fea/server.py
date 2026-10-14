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
from .extract.cbam_doc import extract, extract_demo
from .extract.letters import draft
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
FORCE_DEMO = os.getenv("DEMO_MODE", "") == "1"


def register() -> dict:
    """Importer's quarterly register (from the Italian fattura sample): supplier country+CN -> tonnes."""
    t = json.loads((SAMPLES / "07_fattura_acciai_liguri.truth.json").read_text())["truth"]["shipments"]
    return {(s["country"], s["cn"][:4]): s for s in t}


def live() -> bool:
    return MODEL.live and not FORCE_DEMO


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
    letter = None
    if a["decision"] != "ACCEPT":
        letter = draft(v, a, ex.get("language") or "en", MODEL if live() else None, tonnes=tonnes)
        if EVOLUS.connected and letter["source"] == "demo":
            try:
                letter = {**letter, "body": EVOLUS.translate(letter["body"], ex.get("language") or "en"), "source": "evolus-translate"}
            except Exception as e:
                letter["evolus_error"] = str(e)[:200]
    out = {"id": key, "extraction": ex, "assessment": a, "letter": letter, "tonnes": tonnes, "seconds": round(time.perf_counter() - t0, 2)}
    CACHE[key] = out
    return out


@app.get("/api/status")
def status():
    return {"live_model": live(), "model": MODEL.model or None, "vision_model": MODEL.vision_model or None,
            "endpoint": MODEL.base_url.split("//")[-1].split("/")[0] if MODEL.base_url else None,
            "evolus_connected": EVOLUS.connected, "demo_mode": not live()}


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


@app.get("/api/evolus-log")
def evolus_log():
    return EVOLUS.log[-50:]


if WEB.exists():
    app.mount("/", StaticFiles(directory=str(WEB), html=True), name="web")
