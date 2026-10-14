from pathlib import Path

from fea.energy.baseline import load, measure, synth


def test_recovers_known_saving(tmp_path: Path):
    p = tmp_path / "m.csv"
    synth(p, saving=0.072)
    r = measure(load(p))
    assert 6.0 < r.saving_pct < 8.5 and r.r2 > 0.9
    assert r.meets_process_3pct and r.ci95_pct[0] > 3.0


def test_no_saving_is_not_certified(tmp_path: Path):
    p = tmp_path / "m.csv"
    synth(p, saving=0.0)
    r = measure(load(p))
    assert abs(r.saving_pct) < 1.5 and not r.meets_process_3pct
