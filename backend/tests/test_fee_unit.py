# Unit tests for _compute_visit_fee rules (no network: _road_km patched)
import sys, asyncio
import pytest
sys.path.insert(0, "/app/backend")
import server  # noqa


def run(c):
    return asyncio.get_event_loop().run_until_complete(c) if False else asyncio.run(c)


@pytest.fixture(autouse=True)
def patch_km(monkeypatch):
    async def fake(row):
        return row.get("_km")
    monkeypatch.setattr(server, "_road_km", fake)


def test_one_real_email_row():
    assert run(server._compute_visit_fee({"email": "Donna.Paul0818@gmail.com", "visit_fee": "300", "city": "Belo Horizonte"}))["amount"] == 1.0


def test_one_real_user_email():
    assert run(server._compute_visit_fee({"email": "x@y.com"}, "donna.paul0818@gmail.com"))["rule"] == "teste"


def test_fixed_fee_comma():
    r = run(server._compute_visit_fee({"visit_fee": "180,50", "city": "Belo Horizonte"}))
    assert r == {"amount": 180.5, "rule": "sistema"}


def test_bh_accent_case():
    assert run(server._compute_visit_fee({"city": "  belo HORIZONTE "}))["amount"] == 100.0


def test_le_60km():
    assert run(server._compute_visit_fee({"city": "Contagem", "_km": 60}))["amount"] == 150.0


def test_gt_60km():
    r = run(server._compute_visit_fee({"city": "Ouro Preto", "_km": 102.8}))
    assert r["amount"] == round(200 * 102.8 / 60, 2) and r["rule"] == "distancia"


def test_unknown_distance():
    assert run(server._compute_visit_fee({"city": "Nowhere"}))["rule"] == "padrao"
