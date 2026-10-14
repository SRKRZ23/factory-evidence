"""Export a static, always-on version of the demo (for Netlify): every API response is precomputed by the real backend
(live AMD model if keys are set, otherwise demo data) and written as JSON next to the UI.

    python scripts/export_static.py  ->  dist/  (deploy with: netlify deploy --prod --dir dist)
"""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
from fastapi.testclient import TestClient  # noqa: E402

from fea.server import app  # noqa: E402

DIST = ROOT / "dist"
if DIST.exists():
    shutil.rmtree(DIST)
(DIST / "data").mkdir(parents=True)
(DIST / "samples").mkdir()
c = TestClient(app)


def dump(name, obj):
    (DIST / "data" / f"{name}.json").write_text(json.dumps(obj, ensure_ascii=False))


samples = c.get("/api/samples").json()
dump("samples", samples)
for s in samples:
    shutil.copy(ROOT / "data" / "samples" / f"{s['id']}.png", DIST / "samples" / f"{s['id']}.png")
    shutil.copy(ROOT / "data" / "samples" / f"{s['id']}.pdf", DIST / "samples" / f"{s['id']}.pdf")
    if s.get("expect"):
        dump(f"analyze_{s['id']}", c.post(f"/api/analyze/{s['id']}").json())
dump("portfolio", c.get("/api/portfolio").json())
dump("energy", c.get("/api/energy").json())
dump("bench", c.get("/api/bench").json())
st = c.get("/api/status").json()
st["static_snapshot"] = True
dump("status", st)
html = (ROOT / "web" / "index.html").read_text()
html = html.replace("<script>", "<script>window.STATIC_SNAPSHOT = true;</script>\n<script>", 1)
(DIST / "index.html").write_text(html)
(DIST / "_headers").write_text("/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n")
print("exported", len(list(DIST.rglob("*"))), "files; live model:", st["live_model"])
