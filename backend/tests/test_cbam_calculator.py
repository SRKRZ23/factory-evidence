"""The Python calculator must reproduce the verified JS model (~/Alish/cbam-presentation/cbam-model.js)
to within €1/t, using the official EC tables parsed from data/eu/*.xlsx."""
import pytest

from fea.cbam.calculator import default_value, exposure, trajectory

JS = [  # (iso, CN, year, €/t from cbam-model.js)
    ("UZ", "7207 11 14", 2026, 285.37), ("UZ", "7207 11 14", 2028, 392.31), ("UZ", "7207 11 14", 2030, 451.61),
    ("CN", "7207 11 14", 2026, 177.48), ("CN", "7207 11 14", 2028, 275.82), ("CN", "7207 11 14", 2030, 372.86),
    ("KZ", "7208", 2026, 369.06), ("KZ", "7208", 2028, 538.27), ("KZ", "7208", 2030, 673.37),
    ("TR", "7601", 2026, 39.73), ("TR", "7601", 2028, 88.63), ("TR", "7601", 2030, 161.17),
    ("CN", "3102 10 19", 2026, 164.56), ("CN", "3102 10 19", 2028, 197.10), ("CN", "3102 10 19", 2030, 263.39),
    ("UZ", "2523 29 00", 2026, 74.22), ("UZ", "2523 29 00", 2028, 117.65), ("UZ", "2523 29 00", 2030, 162.57),
]


@pytest.mark.parametrize("iso,cn,year,ref", JS)
def test_matches_verified_js_model(iso, cn, year, ref):
    assert abs(exposure(iso, cn, year).eur_per_t_default - ref) <= 1.0


def test_actual_emissions_saving():
    e = exposure("UZ", "7207 11 14", 2026, actual_see=1.9, route="E")
    assert abs(e.eur_per_t_actual - 151.11) <= 1.0
    assert e.saving_eur_per_t == pytest.approx(e.eur_per_t_default - e.eur_per_t_actual, abs=0.01)


def test_indonesia_slab_is_the_italian_pain_point():
    dv = default_value("ID", "7207 11 14")
    assert dv["total"] == pytest.approx(8.23) and dv["route"] == "C"
    assert exposure("ID", "7207 11 14", 2026).eur_per_t_default > 600


def test_markup_and_factor_raise_cost_over_time():
    tr = trajectory("IN", "7207 11 14")
    assert [r["year"] for r in tr][0] == 2026 and tr[-1]["eur_per_t_default"] > tr[0]["eur_per_t_default"] * 2


def test_unknown_country_raises():
    with pytest.raises(KeyError):
        exposure("XX-nowhere", "7207 11 14")
