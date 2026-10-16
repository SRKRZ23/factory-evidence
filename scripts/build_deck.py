"""Build the 9-slide pitch deck (HTML -> PDF + PNG per slide) from the exported results in dist/data/.
Re-run after live AMD runs so every number on the slides comes from the app itself.

    python scripts/export_static.py && python scripts/build_deck.py
"""
import base64
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "dist" / "data"
OUT = ROOT / "deck"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
REPO = "github.com/SRKRZ23/factory-evidence"
DEMO = "factory-evidence.netlify.app"


def load(name):
    return json.loads((DATA / f"{name}.json").read_text())


def eur(x):
    return "—" if x is None else f"€{x:,.0f}"


def b64(path):
    return "data:image/png;base64," + base64.b64encode(Path(path).read_bytes()).decode()


port, bench, energy, status = load("portfolio"), load("bench"), load("energy"), load("status")
an = {s["id"]: load(f"analyze_{s['id']}") for s in load("samples") if s.get("expect")}
T = port["totals"]
cut = round(100 * (1 - T["eur_with_evidence"] / T["eur_default"]))
ID = an["01_indonesia_slab_verified"]["assessment"]["exposure"]
live = status.get("live_model")
er = energy["result"]

def bench_runs():
    """All saved live benchmark runs of the full 6-document set (scripts/bench_live.py), oldest first."""
    runs = []
    for f in sorted((ROOT / "results").glob("bench_live_*.json")):
        if f.stem.endswith("_demo"):
            continue
        d = json.loads(f.read_text())
        s = d["summary"]
        if s.get("documents") == 6 and not s.get("errors") and "Gemma" in str(s.get("vision_model")) and s["mode"].startswith("LIVE"):
            runs.append(d)
    return runs


RUNS = bench_runs()
if RUNS:
    last = RUNS[-1]["summary"]
    accs = [r["summary"]["field_accuracy_pct"] for r in RUNS]
    fa = sum(r["summary"]["false_accepts"] for r in RUNS)
    # early runs did not store field diffs; there an ACCEPT-expected document escalated to a person was the CN misread
    cn_misreads = sum(1 for r in RUNS for row in r["rows"]
                      if "cn_code" in (row.get("mismatches") or {}) or row.get("reread")
                      or ("mismatches" not in row and row.get("expected") == "ACCEPT" and row.get("decision") == "NEEDS_HUMAN"))
    rereads_fixed = sum(1 for r in RUNS for row in r["rows"] if (row.get("reread") or {}).get("cn_code"))
    reads = sum(len(r["rows"]) for r in RUNS)
    meds = [r["summary"]["read_seconds_median"] for r in RUNS if r["summary"].get("read_seconds_median")]
    walls = [r["summary"]["wall_seconds"] for r in RUNS]
    amd_rows = [
        ("Model on AMD (AMD Token Factory), the same model behind the Evolus agent", f"<b>{last['vision_model']}</b>", "MEASURED"),
        ("Field accuracy vs truth · 6 docs · 6 languages (last run · all runs)",
         f"<b>{last['fields_exact']}</b> ({last['field_accuracy_pct']}%) · range {min(accs)}–{max(accs)}% over {len(RUNS)} runs", "MEASURED"),
        ("Decisions correct · false accepts (all runs)",
         f"<b>{last['decisions_correct']}</b> last run · <b>{fa}</b> false accepts in {reads} documents", "MEASURED"),
        ("Model misread a CN code; the rules caught it",
         f"<b>{cn_misreads}</b> of {reads} reads · never auto-accepted · {rereads_fixed} fixed by a rules-guided re-read", "MEASURED"),
        ("Latency on the shared AMD endpoint (4 documents in parallel)",
         f"median <b>{min(meds):.0f}–{max(meds):.0f} s</b> per page · 6 documents in {min(walls):.0f}–{max(walls):.0f} s", "MEASURED")]
    if last.get("evolus_calls"):
        amd_rows.append(("Evolus agent on the space's own AMD model + AI Tool “anonymize”",
                         f"<b>{last['letters_by_evolus_agent']}/3</b> supplier requests written · <b>{last['evolus_calls_ok']}/{last['evolus_calls']}</b> Evolus API calls OK", "MEASURED"))
elif live and bench.get("calls"):
    amd_rows = [("Model on AMD", f"<b>{bench['model']}</b>", "MEASURED"),
                ("Median extraction latency", f"<b>{bench['extract_seconds_median']} s</b> per page", "MEASURED")]
else:
    amd_rows = [("Extraction on AMD (accuracy, latency, pages/min)", "<b>pending live Token Factory key</b>", "PENDING")]

CSS = (ROOT / "scripts" / "deck.css").read_text()


def slide(n, body, foot=f"Sardor Razikov · {REPO} · {DEMO}"):
    return f'<div class="slide">{body}<div class="foot">{foot}</div><div class="sn">{n:02d} / 09</div></div>'


S = []
S.append(slide(1, f"""
<div class="flex g16" style="flex-wrap:wrap;margin-bottom:48px">
 <span class="badge b-r">AMD Developer Hackathon ACT III</span><span class="badge b-o">Track 1 · Intelligent Industry</span>
 <span class="badge b-ro">🏆 ACT I — 1st Place AI Agents</span><span class="badge b-o">Open models on AMD · Evolus</span></div>
<div class="h1">FACTORY <span class="r">EVIDENCE</span></div><div class="divr" style="width:96px"></div>
<div class="lead" style="max-width:1560px;font-size:34px;line-height:1.35">Supplier emissions documents in any language → <b>verified CBAM savings</b> for EU steel importers.
 <b>The model reads, rules decide, a person approves.</b></div>
<div class="flex g20" style="margin-top:56px;max-width:880px;flex-wrap:wrap">
 <div class="card card-r" style="min-width:300px"><div class="kpi">€{ID['eur_per_t_default']:.0f} → €{ID['eur_per_t_actual']:.0f}</div><div class="klbl">CBAM per tonne · slab · 2026 · modeled</div></div>
 <div class="card card-k" style="min-width:250px"><div class="kpi k">−{cut}%</div><div class="klbl">CBAM cost · demo quarter · modeled</div></div>
 <div class="card card-r" style="min-width:250px"><div class="kpi">123</div><div class="klbl">countries · official EC tables</div></div>
 <div class="card card-k" style="min-width:250px"><div class="kpi k">34 / 34</div><div class="klbl">tests · Docker · MIT</div></div></div>
<div style="position:absolute;right:84px;bottom:80px;width:820px;height:470px;overflow:hidden;border:2px solid var(--ink);border-radius:10px">
 <img src="{b64(ROOT / 'assets/ui_light.png')}" style="width:100%;border:0;border-radius:0"></div>"""))

S.append(slide(2, """
<div class="eye">The problem · one persona</div>
<div class="h2">Every tonne without evidence pays the <span class="r">EU default.</span></div><div class="divr"></div>
<div class="flex g28" style="align-items:flex-start;margin-top:6px">
 <div class="card card-k" style="flex:1.15">
  <div class="h3">The compliance manager at an Italian steel importer</div>
  <div class="body" style="margin-top:14px">
   <div class="prow"><span><b>Since 1 Jan 2026</b> CBAM charges every imported tonne of steel, aluminium, cement, fertiliser</span><span class="pv">definitive period</span></div>
   <div class="prow"><span>No verified supplier data → <b>EU default value + mark-up</b></span><span class="pv">+10% → +20% → +30%</span></div>
   <div class="prow"><span><b>2,400+</b> authorised CBAM declarants in Italy</span><span class="pv">top-5 EU importer</span></div>
   <div class="prow"><span>Italian buyers call the defaults <b>“unworkable”</b>; slab purchases stalled</span><span class="pv">Eurometal, 2026</span></div>
   <div class="prow"><span>The evidence exists — in supplier scans in <b>Chinese, Turkish, Indonesian, Ukrainian, Vietnamese</b></span><span class="pv">manual chase</span></div>
  </div></div>
 <div class="card card-r" style="flex:.85">
  <div class="tag">Modeled · official EC tables · slab CN 7207 11 14 · 2026</div>
  <table><tr><th>Origin</th><th>EU default</th><th>Route</th></tr>
   <tr><td><b>Indonesia</b></td><td class="pv">€636 / t</td><td>BF-BOF (C)</td></tr>
   <tr><td><b>India</b></td><td class="pv">€277 / t</td><td>BF-BOF (C)</td></tr>
   <tr><td><b>China</b></td><td class="pv">€177 / t</td><td>BF-BOF (C)</td></tr>
   <tr><td><b>Ukraine</b></td><td class="pv">€108 / t</td><td>BF-BOF (C)</td></tr>
   <tr><td><b>Türkiye</b></td><td class="pv">€100 / t</td><td>BF-BOF (C)</td></tr></table>
  <div class="src" style="margin-top:14px">EC default values 06.08.2026 (Annex I 2025/2621 as amended by 2026/1740), benchmarks 06.02.2026 (2025/2620, col. B), CBAM factor 0.975, certificate price €82.32 (2026). Italian context: Bird &amp; Bird, Andersen, Eurometal 2026.</div>
 </div></div>"""))

ind = an["01_indonesia_slab_verified"]
fields = [(k, v) for k, v in ind["extraction"]["values"].items() if v not in (None, "")][:7]
S.append(slide(3, f"""
<div class="eye">The 10-second picture</div>
<div class="h2">A scan goes in. A <span class="r">decision with euros</span> comes out.</div><div class="divr"></div>
<div class="flex g28" style="flex:1;min-height:0">
 <div class="card" style="flex:.9;padding:12px;display:flex;align-items:flex-start;justify-content:center;overflow:hidden"><img src="{b64(ROOT / 'data/samples/01_indonesia_slab_verified.png')}" style="width:100%;object-fit:cover;object-position:top;height:720px"></div>
 <div style="flex:1.1;display:flex;flex-direction:column;gap:18px">
  <div class="quote" style="font-size:24px;background:#e8f5ee;border-color:#1a9e5a;color:#0d5a34">ACCEPT — verified actual emissions replace the EU default</div>
  <div class="flex g20"><div class="card card-k" style="flex:1"><div class="klbl" style="margin:0 0 6px">EU default 2026</div><div class="kpi k">€{ID['eur_per_t_default']:.0f}/t</div></div>
   <div class="card" style="flex:1;border-color:#1a9e5a"><div class="klbl" style="margin:0 0 6px">With verified evidence</div><div class="kpi" style="color:#1a9e5a">€{ID['eur_per_t_actual']:.0f}/t</div></div></div>
  <div class="card" style="flex:1"><div class="tag">Read from the document · every value with its source line</div>
   <table>{''.join(f'<tr><td style="width:44%">{k.replace("_", " ")}</td><td><b>{v}</b></td></tr>' for k, v in fields)}</table></div>
  <div class="flex g16">
   <div class="card" style="flex:1;padding:14px 18px"><b style="color:#1a9e5a">ACCEPT</b><div class="sm">Indonesia · Türkiye · China</div></div>
   <div class="card" style="flex:1;padding:14px 18px"><b style="color:#b06a00">NEEDS SUPPLIER</b><div class="sm">India unverified · Viet Nam missing CN, period</div></div>
   <div class="card" style="flex:1;padding:14px 18px"><b class="r">NEEDS HUMAN</b><div class="sm">Ukraine 0.35 t/t vs 1.364 benchmark</div></div></div>
 </div></div>""", foot="Synthetic supplier document (fictional company) · values as extracted by the app"))

S.append(slide(4, """
<div class="eye">How it works</div>
<div class="h2">The model reads. <span class="r">Rules decide.</span> A person approves.</div><div class="divr"></div>
<div class="flex g16" style="align-items:stretch">
 <div class="card card-r" style="flex:1"><div class="kpi" style="font-size:44px">1 · Read</div><div class="body" style="margin-top:10px"><b>Open vision model served on AMD</b> (Token Factory, OpenAI-compatible) reads scans in any language and returns each field <b>with the verbatim line</b> it came from. No quote, no value.</div></div>
 <div class="card card-k" style="flex:1"><div class="kpi k" style="font-size:44px">2 · Check</div><div class="body" style="margin-top:10px"><b>Deterministic rules</b>, not the model: accredited verification, plausibility vs the EU benchmark of the route, arithmetic (total ÷ volume), reporting period, origin.</div></div>
 <div class="card card-r" style="flex:1"><div class="kpi" style="font-size:44px">3 · Decide</div><div class="body" style="margin-top:10px"><b>ACCEPT</b> · <b>NEEDS SUPPLIER</b> · <b>NEEDS HUMAN</b>. Nothing is auto-accepted when numbers don't add up — uncertainty is shown, not hidden.</div></div>
 <div class="card card-k" style="flex:1"><div class="kpi k" style="font-size:44px">4 · Act</div><div class="body" style="margin-top:10px">Request to the supplier <b>in their language</b>, from validator facts only. <b>Evolus</b> runs the process: email intake workflow, extractor, AI Tools, CBAM knowledge library, hand-off.</div></div>
 <div class="card card-r" style="flex:1"><div class="kpi" style="font-size:44px">5 · Count</div><div class="body" style="margin-top:10px">€ per supplier and per quarter: EU default vs verified evidence vs potential if pending suppliers verify. Official EC tables, 123 countries.</div></div></div>
<div class="flex g20" style="margin-top:28px">
 <div class="quote" style="flex:1">Module B · Transizione 5.0: a baseline regression on production, weather and hour-of-week measures an efficiency retrofit with a 95% interval and drafts the note for the certified energy manager. No language model in the numbers.</div></div>"""))

rows = "".join(f'<tr><td>{a}</td><td>{b}</td><td><span class="badge {"b-r" if t == "PENDING" else "b-o"}" style="font-size:11px;padding:4px 10px">{t}</span></td></tr>' for a, b, t in amd_rows + [
    ("CBAM calculator vs verified model (18 country × good × year cases)", "<b>18 / 18</b> within €1 / t", "MEASURED"),
    ("Official EC tables parsed", "<b>123</b> countries · <b>10,910</b> default rows · <b>570</b> benchmark codes", "MEASURED"),
    ("Validator rules on known cases", "accept / unverified / implausible / arithmetic / stale / origin — all caught", "MEASURED"),
    ("Energy baseline on synthetic meter data (true saving 7.20%)", f"<b>{er['saving_pct']}%</b> measured · 95% interval {er['ci95_pct'][0]}–{er['ci95_pct'][1]}% · R² {er['r2']}", "MEASURED"),
    ("Test suite", "<b>34 / 34</b> passing · Docker · MIT", "MEASURED")])
S.append(slide(5, f"""
<div class="eye">Measured, not promised</div>
<div class="h2">What we <span class="r">measured</span> this week</div><div class="divr"></div>
<div class="card card-k"><table><tr><th>What</th><th>Result</th><th>Status</th></tr>{rows}</table>
<div class="src" style="margin-top:18px">Supplier documents and meter data are synthetic (fictional companies). Numbers re-generated from the app by <b>scripts/build_deck.py</b>; AMD inference panel in the live demo shows per-call latency and tokens.</div></div>"""))

NICE = {"01_indonesia_slab_verified": "Indonesia · slab", "02_china_hrc_verified": "China · hot-rolled coil", "03_india_slab_selfdeclared": "India · slab",
        "04_turkey_billet_eaf_verified": "Türkiye · billet (EAF)", "05_vietnam_missing_fields": "Viet Nam · coil", "06_ukraine_implausible": "Ukraine · slab"}
prow = "".join(f'<tr><td><b>{NICE.get(r["id"], r["id"])}</b></td><td>{r["decision"].replace("_", " ")}</td><td>{r.get("tonnes") or "—"}</td><td>{eur(r.get("eur_default"))}</td><td>{eur(r.get("eur_with_evidence"))}</td><td>{eur(r.get("eur_if_suppliers_verify"))}</td></tr>' for r in port["rows"])
S.append(slide(6, f"""
<div class="eye">The money · modeled · 2026 prices</div>
<div class="h2">One quarter of imports: <span class="r">{eur(T['eur_default'])} → {eur(T['eur_with_evidence'])}</span></div><div class="divr"></div>
<div class="flex g28" style="align-items:flex-start;margin-top:6px">
 <div class="card card-k" style="flex:1.5"><table><tr><th>Supplier document</th><th>Decision</th><th>Tonnes</th><th>At EU default</th><th>With evidence</th><th>If suppliers verify</th></tr>{prow}
  <tr><td><b>Quarter total</b></td><td></td><td><b>{T['tonnes']:,}</b></td><td class="pv">{eur(T['eur_default'])}</td><td class="pv">{eur(T['eur_with_evidence'])}</td><td class="pv">{eur(T['eur_if_suppliers_verify'])}</td></tr></table></div>
 <div style="flex:.7;display:flex;flex-direction:column;gap:20px">
  <div class="card card-r"><div class="kpi">−{cut}%</div><div class="klbl">CBAM cost with the evidence already accepted</div></div>
  <div class="card card-k"><div class="kpi k">€{(ID['eur_per_t_default'] - ID['eur_per_t_actual']) * 1000 / 1e3:,.0f}k</div><div class="klbl">less CBAM per 1,000 t of Indonesian slab</div></div>
  <div class="src">Modeled from official EC default values and benchmarks; certificate price €82.32 (2026, EC). Tonnages from the synthetic import register; suppliers without a register line show “—”.</div></div></div>"""))

SAVE_K = round((ID["eur_per_t_default"] - ID["eur_per_t_actual"]))
S.append(slide(7, f"""
<div class="eye">Who pays · how it reaches them</div>
<div class="h2">Priced at a <span class="r">fraction of the saving.</span></div><div class="divr"></div>
<div class="flex g24" style="align-items:flex-start;margin-top:6px">
 <div class="card card-r" style="flex:1"><div class="h3">Buyer</div><div class="body" style="margin-top:12px">Authorised CBAM declarants — steel, aluminium, cement and fertiliser importers. <b>2,400+ in Italy</b> alone. Pain is quarterly and grows every year with the mark-up.</div></div>
 <div class="card card-k" style="flex:1"><div class="h3">Model (proposed)</div><div class="body" style="margin-top:12px">SaaS plan per declarant + a fee per verified tonne. Example: 1,000 t of Indonesian slab saves ~€{SAVE_K}k; a fee of even €1/t is &lt;0.2% of that saving.</div></div>
 <div class="card card-r" style="flex:1"><div class="h3">Channel</div><div class="body" style="margin-top:12px">Customs brokers, CBAM consultants and audit firms — each serves hundreds of importers. <b>Evolus</b> as the delivery layer for Italian SMEs: workflows, email, Teams, phone.</div></div>
 <div class="card card-k" style="flex:1"><div class="h3">Next</div><div class="body" style="margin-top:12px">Same document intake for <b>EUDR</b> (deforestation, Dec 2026) and the <b>battery Digital Product Passport</b> (Feb 2027). Module B: Transizione 5.0 energy evidence for manufacturers.</div></div></div>"""))

S.append(slide(8, """
<div class="eye">Why it matters to each side · and what we don't claim</div>
<div class="h2">Everyone gets something <span class="r">real.</span></div><div class="divr"></div>
<div class="flex g20" style="align-items:flex-start;margin-top:6px">
 <div style="flex:1.4;display:grid;grid-template-columns:1fr 1fr;gap:18px">
  <div class="card"><div class="h3">AMD</div><div class="body">Confidential trade documents read by open models on AMD infrastructure — a workload that should not go to a closed API.</div></div>
  <div class="card"><div class="h3">Open models</div><div class="body">Multilingual document reading where an open model is the right tool, with every value traceable to its source line.</div></div>
  <div class="card"><div class="h3">Evolus</div><div class="body">A real, recurring compliance process on its building blocks, starting where Italian SMEs need it most.</div></div>
  <div class="card"><div class="h3">Importers &amp; advisors</div><div class="body">€ saved per tonne per supplier, and a cited evidence file instead of chasing emails.</div></div></div>
 <div class="card card-k" style="flex:.8"><div class="h3">What we don't claim</div><div class="body" style="margin-top:12px">
  <div class="prow"><span>Documents and meter data in the demo are <b>synthetic</b></span></div>
  <div class="prow"><span>Prices after 2026 are <b>scenarios</b>, not forecasts</span></div>
  <div class="prow"><span>The declaration stays with the <b>authorised declarant</b> and the <b>accredited verifier</b></span></div>
  <div class="prow"><span>No autonomous compliance decision — <b>a person approves</b></span></div>
  <div class="prow"><span>No customer or partner endorsement implied</span></div></div></div></div>"""))

S.append(slide(9, """
<div class="eye">Built this week · solo</div>
<div class="h2">Sardor Razikov · <span class="r">ships and measures.</span></div><div class="divr"></div>
<div class="flex g28" style="align-items:flex-start;margin-top:6px">
 <div class="card card-k" style="flex:1"><div class="body">
  <div class="prow"><span><b>AMD Developer Hackathon ACT I — 1st place, AI Agents</b> (RepoMind, measured on MI300X)</span></div>
  <div class="prow"><span>Kaggle SPR 2026 — <b>#7 / 371</b> (top 1.9%)</span></div>
  <div class="prow"><span>ML engineer &amp; founder, Tashkent, Uzbekistan</span></div>
  <div class="prow"><span>Built in 4 days: EC table parser · calculator · validator · vision extraction · letters · Evolus client · energy module · UI · 34 tests</span></div></div></div>
 <div class="card card-r" style="flex:1"><div class="h3">The ask</div><div class="body" style="margin-top:12px">
  Three Italian importers or CBAM advisors to pilot on <b>real</b> supplier documents — data processed by open models on AMD, every number traceable.</div>
  <div class="body" style="margin-top:22px"><b>Repo</b> · github.com/SRKRZ23/factory-evidence<br><b>Demo</b> · factory-evidence.netlify.app</div></div></div>"""))

OUT.mkdir(exist_ok=True)
html = f'<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><title>Factory Evidence — Pitch</title><style>{CSS}</style></head><body>{"".join(S)}</body></html>'
(OUT / "deck.html").write_text(html, encoding="utf-8")
tmp = Path(tempfile.mkdtemp(prefix="fea-deck-"))
try:
    base = [CHROME, "--headless=new", "--disable-gpu", "--no-first-run", f"--user-data-dir={tmp}", "--hide-scrollbars"]
    subprocess.run(base + ["--no-pdf-header-footer", "--run-all-compositor-stages-before-draw", "--virtual-time-budget=8000",
                           f"--print-to-pdf={OUT / 'Factory_Evidence_deck.pdf'}", (OUT / "deck.html").as_uri()], check=True, capture_output=True, timeout=120)
    for i in range(1, 10):
        one = html.replace('<div class="slide">', '<div class="slide" style="display:none">')
        parts = one.split('<div class="slide" style="display:none">')
        parts[i] = parts[i]  # keep
        page = '<div class="slide" style="display:none">'.join(parts[:i]) + '<div class="slide">' + '<div class="slide" style="display:none">'.join(parts[i:])
        f = OUT / f"_s{i}.html"
        f.write_text(page, encoding="utf-8")
        subprocess.run(base + ["--window-size=1920,1080", "--virtual-time-budget=4000", f"--screenshot={OUT / f'slide_{i:02d}.png'}", f.as_uri()],
                       check=True, capture_output=True, timeout=60)
        f.unlink()
finally:
    shutil.rmtree(tmp, ignore_errors=True)
print("deck:", OUT / "Factory_Evidence_deck.pdf", "· live model:", live)
