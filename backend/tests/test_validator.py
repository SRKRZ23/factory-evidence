from fea.cbam.validator import assess

BASE = dict(installation_name="PT Baja Nusantara Slab Works", installation_country="ID", cn_code="7207 11 14",
            production_route="C", specific_direct_emissions=2.10, reporting_period_start="2025-01-01",
            reporting_period_end="2025-12-31", verified=True, verifier_name="Accredited Verifier Ltd (ISO 14065)")


def test_verified_indonesian_slab_is_accepted_with_big_saving():
    a = assess(BASE, tonnes=1000)
    assert a.decision == "ACCEPT", a.findings
    assert a.usable_actual_see == 2.10
    assert a.exposure["eur_per_t_default"] > 600 and a.exposure["eur_per_t_actual"] < 80
    assert a.exposure["totals"]["eur_saving"] > 500_000


def test_unverified_needs_supplier_but_shows_potential():
    a = assess({**BASE, "installation_country": "IN", "verified": False, "verifier_name": None})
    assert a.decision == "NEEDS_SUPPLIER"
    assert any(f.code == "not_verified" for f in a.findings)
    assert a.usable_actual_see is None and a.exposure["potential_saving_eur_per_t"] > 0


def test_implausibly_low_goes_to_a_person():
    a = assess({**BASE, "installation_country": "UA", "specific_direct_emissions": 0.35})
    assert a.decision == "NEEDS_HUMAN" and any(f.code == "implausibly_low" for f in a.findings)
    assert "potential_saving_eur_per_t" not in a.exposure


def test_arithmetic_mismatch():
    a = assess({**BASE, "total_direct_emissions_t": 1_000_000, "production_volume_t": 400_000})
    assert a.decision == "NEEDS_HUMAN" and any(f.code == "arithmetic_mismatch" for f in a.findings)


def test_missing_fields_and_stale_period():
    a = assess({**BASE, "cn_code": None, "reporting_period_start": "2021-01-01", "reporting_period_end": "2021-12-31"})
    assert a.decision == "NEEDS_SUPPLIER"
    assert "cn_code" in a.missing and any(f.code == "stale_period" for f in a.findings)


def test_origin_mismatch_needs_human():
    a = assess(BASE, origin_country="CN")
    assert a.decision == "NEEDS_HUMAN" and any(f.code == "origin_mismatch" for f in a.findings)


def test_scrap_eaf_route_uses_route_e_benchmark():
    a = assess({**BASE, "installation_country": "TR", "production_route": "E", "specific_direct_emissions": 0.42})
    assert a.decision == "ACCEPT" and a.exposure["route"] == "E"
