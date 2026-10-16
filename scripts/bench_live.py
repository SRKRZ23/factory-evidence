#!/usr/bin/env python3
"""Live benchmark: the full Factory Evidence pipeline on AMD-served open models.

Each supplier document goes through exactly what the app does:
read (vision model on AMD) -> deterministic validation against official EU tables -> € exposure ->
supplier letter in the supplier's language (live model) when the document is not accepted.

Prints one row per document as it finishes, then a summary, and saves results/bench_live_<ts>.json.
The API key is never printed.

    python3 scripts/bench_live.py            # live run on AMD (uses .env)
    python3 scripts/bench_live.py --demo     # offline dry run on bundled demo data (no model calls)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

# Token Factory price list (points per 1M tokens); used only to report the share of the daily cap spent.
PRICE_PTS = {"Gemma-4-31B-IT": (0.50, 3.00), "Qwen3.8-27B": (0.50, 3.00)}


def norm(v):
    if isinstance(v, str):
        return "".join(v.replace("—", "-").replace("–", "-").split()).casefold()
    if isinstance(v, float) and v.is_integer():
        return int(v)
    return v


def same(a, b) -> bool:
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool) and not isinstance(b, bool):
        return abs(float(a) - float(b)) <= 1e-6 * max(1.0, abs(float(b)))
    return norm(a) == norm(b)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="dry run on bundled demo data, no model calls")
    ap.add_argument("--workers", type=int, default=4, help="parallel documents (Token Factory allows 8 concurrent)")
    ap.add_argument("--model", help="override the model for this run (vision + text), e.g. DeepSeek-V4.1-Flash")
    ap.add_argument("--only", help="comma-separated id prefixes, e.g. 01,04")
    ap.add_argument("--compact", action="store_true", help="compact extraction output: omit absent fields, minified JSON")
    args = ap.parse_args()

    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    if args.demo:
        os.environ["DEMO_MODE"] = "1"
    if args.model:
        os.environ["AMD_TF_MODEL"] = os.environ["AMD_TF_VISION_MODEL"] = args.model
    if args.compact:
        os.environ["FEA_COMPACT"] = "1"

    from fea import server  # noqa: E402  (reads env at import)

    st = server.status()
    mode = "DEMO DATA (no model calls)" if st["demo_mode"] else "LIVE on AMD"
    print(f"Factory Evidence · live benchmark · {datetime.now():%Y-%m-%d %H:%M}")
    print(f"mode: {mode}")
    print(f"endpoint: {st['endpoint']}   vision model: {st['vision_model']}   text model: {st['model']}")
    print()

    samples = [m for m in server.samples() if m.get("expect")]
    if args.only:
        samples = [m for m in samples if any(m["id"].startswith(p) for p in args.only.split(","))]
    hdr = f"{'document':34} {'lang':4} {'fields':>7} {'decision':15} {'expected':15} {'ok':3} {'read s':>7} {'letter':>7}"
    print(hdr)
    print("-" * len(hdr))

    rows = []
    t_all = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(server.analyze_path, server.SAMPLES / f"{m['id']}.png", m["id"]): m for m in samples}
        for f in as_completed(futs):
            m = futs[f]
            try:
                r = f.result()
            except Exception as e:  # keep the run going; report the failure honestly
                print(f"{m['id']:34} ERROR {type(e).__name__}: {str(e)[:80]}")
                rows.append({"id": m["id"], "error": str(e)[:300]})
                continue
            truth = json.loads((server.SAMPLES / f"{m['id']}.truth.json").read_text())["truth"]
            vals = (r["extraction"].get("values") or {})
            eq = lambda k, g, t: same(g, t) or (k == "carbon_price_paid" and g in (0, 0.0, None) and t in (0, 0.0, None))  # noqa: E731
            exact = sum(1 for k, v in truth.items() if eq(k, vals.get(k), v))
            dec = r["assessment"]["decision"]
            ok = dec == m["expect"]
            letter = r.get("letter") or {}
            read_s = next((c.seconds for c in reversed(server.MODEL.stats) if c.task == "extract"), None) if not st["demo_mode"] else None
            row = {"id": m["id"], "lang": m["lang"], "fields_exact": exact, "fields_total": len(truth),
                   "decision": dec, "expected": m["expect"], "decision_ok": ok,
                   "false_accept": dec == "ACCEPT" and m["expect"] != "ACCEPT",
                   "mismatches": {k: {"got": vals.get(k), "truth": v} for k, v in truth.items() if not eq(k, vals.get(k), v)},
                   "reread": r["extraction"].get("reread"),
                   "findings": [f if isinstance(f, str) else {kk: f.get(kk) for kk in ("code", "severity", "message", "field") if kk in f}
                                for f in (r["assessment"].get("findings") or [])],
                   "extraction_source": r["extraction"].get("source"), "extraction_error": r["extraction"].get("error"),
                   "letter_lang": ((letter.get("language") or "").split(" (")[0] + (" (tmpl)" if letter.get("source") == "demo" else "")) if letter else None,
                   "letter_source": letter.get("source"), "pipeline_seconds": r["seconds"]}
            rows.append(row)
            print(f"{m['id']:34} {m['lang']:4} {exact:>3}/{len(truth):<3} {dec:15} {m['expect']:15} {'yes' if ok else 'NO':3} "
                  f"{r['seconds']:>7.1f} {(row['letter_lang'] or '-'):>7}", flush=True)
    wall = time.perf_counter() - t_all

    good = [r for r in rows if "error" not in r]
    f_ok = sum(r["fields_exact"] for r in good)
    f_tot = sum(r["fields_total"] for r in good)
    d_ok = sum(r["decision_ok"] for r in good)
    fa = sum(r["false_accept"] for r in good)
    stats = server.MODEL.stats
    ex = [c for c in stats if c.task == "extract"]
    p_tok = sum(c.prompt_tokens for c in stats)
    c_tok = sum(c.completion_tokens for c in stats)
    price = PRICE_PTS.get(st["vision_model"] or "", (0.5, 3.0))
    pts = p_tok / 1e6 * price[0] + c_tok / 1e6 * price[1]
    med = lambda xs: sorted(xs)[len(xs) // 2] if xs else None  # noqa: E731

    summary = {
        "mode": mode, "endpoint": st["endpoint"], "vision_model": st["vision_model"], "text_model": st["model"],
        "documents": len(rows), "errors": len(rows) - len(good),
        "fields_exact": f"{f_ok}/{f_tot}", "field_accuracy_pct": round(100 * f_ok / f_tot, 1) if f_tot else None,
        "decisions_correct": f"{d_ok}/{len(good)}", "false_accepts": fa,
        "model_calls": len(stats), "read_seconds_median": med([c.seconds for c in ex]),
        "completion_tok_per_s_median": med([c.tok_per_s for c in stats]),
        "wall_seconds": round(wall, 1), "pages_per_minute_effective": round(60 * len(good) / wall, 1) if wall else None,
        "prompt_tokens": p_tok, "completion_tokens": c_tok, "points_spent_estimate": round(pts, 4),
        "evolus_calls": len(server.EVOLUS.log), "evolus_calls_ok": sum(1 for c in server.EVOLUS.log if c.get("status") == 200),
        "letters_by_evolus_agent": sum(1 for r in good if r.get("letter_source") == "evolus-agent"),
        "note": "fields compared whitespace/case/dash-insensitive; numbers rel. tol 1e-6; carbon_price_paid 0 == not paid (null)",
    }
    print()
    print("SUMMARY")
    for k in ("mode", "fields_exact", "field_accuracy_pct", "decisions_correct", "false_accepts", "model_calls",
              "read_seconds_median", "completion_tok_per_s_median", "wall_seconds", "pages_per_minute_effective",
              "prompt_tokens", "completion_tokens", "points_spent_estimate", "evolus_calls", "evolus_calls_ok", "letters_by_evolus_agent"):
        print(f"  {k:30} {summary[k]}")

    out = ROOT / "results" / f"bench_live_{datetime.now():%Y%m%d_%H%M%S}{'_demo' if args.demo else ''}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"summary": summary, "rows": rows, "calls": [c.__dict__ for c in stats], "evolus_log": server.EVOLUS.log}, ensure_ascii=False, indent=1))
    print(f"\nsaved {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
