from __future__ import annotations

import os
import urllib.parse
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

MONO_SECRET_KEY = os.getenv("MONO_SECRET_KEY", "")
MONO_PUBLIC_KEY = os.getenv("MONO_PUBLIC_KEY", "")
MONO_BASE_URL = os.getenv("MONO_BASE_URL", "https://api.withmono.com")
BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://127.0.0.1:8000")
MONO_SANDBOX_MODE = os.getenv("MONO_SANDBOX_MODE", "true").lower() in {"1", "true", "yes", "on"}


def _url_encode(value: str) -> str:
    return urllib.parse.quote_plus(value)


def _auth_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {MONO_SECRET_KEY}",
        "Content-Type": "application/json",
    }


def _statement_mock(account_id: str) -> dict[str, Any]:
    return {
        "source": "mock",
        "account_id": account_id,
        "data": {
            "transactions": [
                {"date": "2026-01-10", "amount": -25000, "balance": 210000},
                {"date": "2026-01-22", "amount": 180000, "balance": 390000},
                {"date": "2026-02-07", "amount": -54000, "balance": 336000},
                {"date": "2026-02-20", "amount": 170000, "balance": 506000},
                {"date": "2026-03-05", "amount": -48000, "balance": 458000},
                {"date": "2026-03-25", "amount": 190000, "balance": 648000},
            ]
        },
    }


def _income_mock(account_id: str) -> dict[str, Any]:
    return {
        "source": "mock",
        "account_id": account_id,
        "data": {
            "monthly_income": [162000, 171000, 168000, 174000, 169000, 176000],
            "average_balance": 402500,
        },
    }


def get_telco_data(phone: str, network: str = "MTN") -> dict[str, Any]:
    """Mocked telco response for hackathon demo."""
    return {
        "topup_count_30d": 8,
        "avg_topup_amount": 500,
        "data_plan_tier": "1GB_weekly",
        "borrow_repaid_ontime": True,
        "account_age_months": 24,
    }


def create_connect_session(name: str, email: str) -> dict[str, Any]:
    """Create Mono Connect v2 session.

    Returns at least {'session_id': '...'} and in mock mode also a local session_url.
    """
    if MONO_SANDBOX_MODE:
        session_id = f"mock_session_{name.replace(' ', '').lower()}"
        return {
            "session_id": session_id,
            "session_url": (
                f"{BACKEND_BASE_URL}/mock-mono-widget?session_id={session_id}"
                f"&name={_url_encode(name)}&email={_url_encode(email)}"
            ),
            "source": "mock",
        }

    url = f"{MONO_BASE_URL}/v2/connect/session"
    payload = {"name": name, "email": email}
    with httpx.Client(timeout=12) as client:
        resp = client.post(url, json=payload, headers=_auth_headers())
        resp.raise_for_status()
        data = resp.json()

    session_id = data.get("id") or data.get("session_id") or data.get("data", {}).get("id")
    if not session_id:
        raise ValueError("Mono session response missing session_id")
    return {"session_id": session_id, "source": "mono", "raw": data}


def exchange_code_for_account(code: str) -> dict[str, Any]:
    """Exchange temporary code for permanent Mono account ID."""
    if MONO_SANDBOX_MODE:
        return {"account_id": f"mock_account_{code}", "source": "mock"}

    url = f"{MONO_BASE_URL}/v2/accounts/auth"
    payload = {"code": code}
    with httpx.Client(timeout=12) as client:
        resp = client.post(url, json=payload, headers=_auth_headers())
        resp.raise_for_status()
        data = resp.json()

    account_id = data.get("id") or data.get("account_id") or data.get("data", {}).get("id")
    if not account_id:
        raise ValueError("Mono auth response missing account_id")
    return {"account_id": account_id, "source": "mono", "raw": data}


def fetch_account_statement(account_id: str) -> dict[str, Any]:
    """Fetch statement from Mono or return sandbox mock data."""
    if MONO_SANDBOX_MODE or not MONO_SECRET_KEY or str(account_id).startswith("mock_account_"):
        return _statement_mock(account_id)

    url = f"{MONO_BASE_URL}/v2/accounts/{account_id}/statement"
    with httpx.Client(timeout=15) as client:
        resp = client.get(url, headers=_auth_headers())
        resp.raise_for_status()
        data = resp.json()
    return {"source": "mono", "account_id": account_id, "data": data.get("data", data)}


def fetch_account_income(account_id: str) -> dict[str, Any]:
    """Fetch income analytics from Mono or return sandbox mock data."""
    if MONO_SANDBOX_MODE or not MONO_SECRET_KEY or str(account_id).startswith("mock_account_"):
        return _income_mock(account_id)

    url = f"{MONO_BASE_URL}/v2/accounts/{account_id}/income"
    with httpx.Client(timeout=15) as client:
        resp = client.get(url, headers=_auth_headers())
        resp.raise_for_status()
        data = resp.json()
    return {"source": "mono", "account_id": account_id, "data": data.get("data", data)}


def verify_webhook_signature(raw_body: bytes, signature_header: str) -> bool:
    """Mono webhook verification placeholder for lightweight dev mode."""
    if not MONO_SECRET_KEY:
        return True
    return True

