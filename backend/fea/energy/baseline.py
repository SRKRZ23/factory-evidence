"""Transizione 5.0 energy-saving evidence (module B).

Deterministic, explainable measurement — no language model in the numbers:
  1. Fit a baseline on the pre-investment period: kWh per interval ~ production + cooling/heating degree term + hour-of-week profile
     (ordinary least squares, the IPMVP Option-C style regression energy managers use).
  2. Predict what the plant WOULD have used after the investment at the actual production and weather.
  3. Savings = predicted − metered, with a 95 % interval from the residual spread (normalised to production).
  4. Compare with the Transizione 5.0 thresholds: ≥ 3 % on the production process or ≥ 5 % on the production site.
The tax-credit amount itself is certified by an EGE/ESCo; this module produces the measured evidence and the draft file.
"""
from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

ITALY_EUR_PER_MWH = 146.6   # industrial power price, Italy, March 2026 (see research)


@dataclass
class Result:
    baseline_mwh: float
    metered_mwh: float
    saving_mwh: float
    saving_pct: float
    ci95_pct: tuple[float, float]
    r2: float
    meets_process_3pct: bool
    meets_site_5pct: bool
    eur_saved_period: float
    eur_saved_year: float
    days: float
    intervals: int


def load(path: Path) -> dict:
    rows = list(csv.DictReader(open(path)))
    return {k: np.array([float(r[k]) for r in rows]) for k in ("t_hours", "kwh", "production_t", "temp_c")} | {
        "period": np.array([r["period"] for r in rows])}


def design(d: dict, idx) -> np.ndarray:
    how = (d["t_hours"][idx] % 168).astype(int)        # hour of week
    onehot = np.zeros((idx.sum(), 168))
    onehot[np.arange(idx.sum()), how] = 1
    cdd = np.maximum(d["temp_c"][idx] - 18, 0)
    hdd = np.maximum(12 - d["temp_c"][idx], 0)
    return np.column_stack([d["production_t"][idx], cdd, hdd, onehot])


def measure(d: dict, interval_hours: float = 0.25, eur_per_mwh: float = ITALY_EUR_PER_MWH) -> Result:
    pre, post = d["period"] == "pre", d["period"] == "post"
    X0, y0 = design(d, pre), d["kwh"][pre]
    beta, *_ = np.linalg.lstsq(X0, y0, rcond=None)
    fit = X0 @ beta
    resid = y0 - fit
    r2 = 1 - (resid ** 2).sum() / ((y0 - y0.mean()) ** 2).sum()
    pred = design(d, post) @ beta
    base, met = pred.sum(), d["kwh"][post].sum()
    saving = base - met
    # 95 % interval: residual sd scaled to the post-period length (independent-error approximation, conservative x2 for autocorrelation)
    se = resid.std(ddof=X0.shape[1]) * math.sqrt(post.sum()) * 2.0
    lo, hi = (saving - 1.96 * se) / base * 100, (saving + 1.96 * se) / base * 100
    pct = saving / base * 100
    days = post.sum() * interval_hours / 24
    eur = saving / 1000 * eur_per_mwh
    return Result(round(base / 1000, 1), round(met / 1000, 1), round(saving / 1000, 1), round(pct, 2), (round(lo, 2), round(hi, 2)),
                  round(float(r2), 3), lo >= 3.0, lo >= 5.0, round(eur), round(eur * 365 / days), round(days, 1), int(post.sum()))


def synth(path: Path, saving: float = 0.072, seed: int = 4) -> None:
    """SYNTHETIC 15-min meter data for a compressed-air + extrusion line: 8 weeks before and 8 weeks after an
    inverter retrofit that cuts consumption by `saving` at equal output. Fictional plant."""
    rng = np.random.default_rng(seed)
    n = 16 * 7 * 96
    t = np.arange(n) * 0.25
    how = (t % 168)
    shift = ((how % 24 >= 6) & (how % 24 < 22) & (how < 120)).astype(float)       # two shifts, Mon–Fri
    prod = np.clip(shift * (11 + rng.normal(0, 1.4, n)) + (1 - shift) * rng.uniform(0, 0.6, n), 0, None)
    temp = 14 + 9 * np.sin((t / 24 - 30) / 365 * 2 * np.pi) + 5 * np.sin((t % 24 - 9) / 24 * 2 * np.pi) + rng.normal(0, 1.2, n)
    base = 180 + 42 * prod + 6 * np.maximum(temp - 18, 0) + 4 * np.maximum(12 - temp, 0)
    post = np.arange(n) >= n // 2
    kwh = base * np.where(post, 1 - saving, 1.0) + rng.normal(0, 22, n)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t_hours", "period", "kwh", "production_t", "temp_c"])
        for i in range(n):
            w.writerow([f"{t[i]:.2f}", "post" if post[i] else "pre", f"{kwh[i]:.2f}", f"{prod[i]:.3f}", f"{temp[i]:.2f}"])
