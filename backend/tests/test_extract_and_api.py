import os

from fea.extract.cbam_doc import normalise
from fea.llm import parse_json


def test_normalise_model_output():
    raw = parse_json('''```json
{"fields": {"installation_country": {"value": "Indonesia (ID)", "evidence": "Indonesia (ID)"},
 "specific_direct_emissions": {"value": "2,10 tCO2e / t", "evidence": "2,10 tCO2e / t"},
 "total_direct_emissions_t": {"value": "3 360 000", "evidence": "3 360 000 tCO2e"},
 "production_route": {"value": "BF-BOF — CBAM route (C)", "evidence": "..."},
 "verified": {"value": "Verified", "evidence": "Diverifikasi"},
 "cn_code": {"value": "—", "evidence": null}}, "language": "id"}
```''')
    v, ev = normalise(raw)
    assert v["specific_direct_emissions"] == 2.10 and v["total_direct_emissions_t"] == 3360000
    assert v["production_route"] == "C" and v["verified"] is True and v["cn_code"] is None
    assert v["installation_country"] == "ID"
    assert ev["total_direct_emissions_t"] == "3 360 000 tCO2e"


def test_api_demo_portfolio():
    os.environ["DEMO_MODE"] = "1"
    from fastapi.testclient import TestClient
    from fea.server import app
    c = TestClient(app)
    assert c.get("/api/status").json()["demo_mode"] is True
    r = c.post("/api/analyze/06_ukraine_implausible").json()
    assert r["assessment"]["decision"] == "NEEDS_HUMAN" and r["letter"] is not None
    p = c.get("/api/portfolio").json()["totals"]
    assert p["eur_default"] > p["eur_with_evidence"] > p["eur_if_suppliers_verify"] > 0


def test_number_parsing_edge_cases():
    from fea.extract.cbam_doc import _num, _country
    assert _num("2,10 tCO2e / t") == 2.10 and _num("1.95 tCO2e/吨") == 1.95 and _num("3 360 000 tCO2e") == 3360000
    assert _num("1,234.5") == 1234.5 and _num("1.234,5") == 1234.5 and _num("0,42 tCO2e/t") == 0.42 and _num("—") is None
    assert _country("Indonesia (ID)") == "ID" and _country("中国 (CN)") == "CN" and _country("India") == "IN" and _country("Україна (UA)") == "UA"
