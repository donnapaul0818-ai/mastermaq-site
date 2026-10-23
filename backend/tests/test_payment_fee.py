# Read-only tests: visit fee, payment status, brands, brick pay with invalid token (no charge)
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
OS_NUM = "73100641"
NEW_BRANDS = ["Invisacook", "Viking", "Daikin", "Elettromec", "Tecno"]


@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": "admin@mastermaq.com", "password": "mastermaq@2026"})
    if r.status_code != 200:
        pytest.skip(f"login failed {r.status_code}")
    return s


# Brands
def test_brands_include_new():
    r = requests.get(f"{BASE_URL}/api/equipment/brands")
    assert r.status_code == 200
    for b in NEW_BRANDS:
        assert b in r.json()


# Payment status / fee rule
def test_payment_status_distance(admin):
    r = admin.get(f"{BASE_URL}/api/service-orders/{OS_NUM}/payment-status", timeout=40)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["amount"] == 150
    assert d["rule"] == "distancia"
    assert abs(d["km"] - 37.2) < 1
    assert d["status"] == "unpaid"


def test_payment_status_unauth():
    r = requests.get(f"{BASE_URL}/api/service-orders/{OS_NUM}/payment-status")
    assert r.status_code == 401


def test_payment_status_404(admin):
    r = admin.get(f"{BASE_URL}/api/service-orders/99999999999/payment-status")
    assert r.status_code == 404


# Brick pay with invalid token -> 400 PT message
def test_pay_invalid_token(admin):
    r = admin.post(f"{BASE_URL}/api/service-orders/{OS_NUM}/pay", json={
        "payment_method_id": "visa", "token": "invalid_token_TEST", "installments": 1,
        "payer": {"email": "admin@mastermaq.com"}}, timeout=40)
    assert r.status_code == 400, r.text
    assert "Mercado Pago" in r.json()["detail"]


def test_pay_unauth():
    r = requests.post(f"{BASE_URL}/api/service-orders/{OS_NUM}/pay", json={"payment_method_id": "visa"})
    assert r.status_code == 401


def test_pay_missing_method(admin):
    r = admin.post(f"{BASE_URL}/api/service-orders/{OS_NUM}/pay", json={})
    assert r.status_code == 422


def test_status_after_failed_pay_still_unpaid(admin):
    r = admin.get(f"{BASE_URL}/api/service-orders/{OS_NUM}/payment-status", timeout=40)
    assert r.status_code == 200
    assert r.json()["status"] == "unpaid"
    assert r.json()["amount"] == 150
