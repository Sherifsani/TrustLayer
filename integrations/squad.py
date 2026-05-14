import hashlib
import hmac
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("SQUAD_BASE_URL", "https://sandbox-api-d.squadco.com")


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {os.getenv('SQUAD_SECRET_KEY', '')}",
        "Content-Type": "application/json",
    }


def validate_webhook_signature(body_bytes: bytes, signature_header: str) -> bool:
    secret = os.getenv("SQUAD_SECRET_KEY", "")
    expected = hmac.new(secret.encode(), body_bytes, hashlib.sha512).hexdigest()
    return hmac.compare_digest(expected.lower(), signature_header.lower())


async def initiate_payment(amount_kobo: int, email: str, ref: str, callback_url: str) -> dict:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{BASE_URL}/transaction/initiate",
                headers=_headers(),
                json={
                    "amount": amount_kobo,
                    "email": email,
                    "transaction_ref": ref,
                    "callback_url": callback_url,
                },
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        return {"error": str(e), "success": False}


async def verify_transaction(txn_ref: str) -> dict:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{BASE_URL}/transaction/verify/{txn_ref}",
                headers=_headers(),
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        return {"error": str(e), "success": False}


async def lookup_account(bank_code: str, account_number: str) -> dict:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{BASE_URL}/payout/account/lookup",
                headers=_headers(),
                params={"bank_code": bank_code, "account_number": account_number},
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        return {"error": str(e), "success": False}


async def transfer(bank_code: str, account_number: str, amount_kobo: int, ref: str) -> dict:
    # always verify account exists before initiating transfer
    lookup = await lookup_account(bank_code, account_number)
    if "error" in lookup:
        return lookup

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{BASE_URL}/payout/transfer",
                headers=_headers(),
                json={
                    "bank_code": bank_code,
                    "account_number": account_number,
                    "amount": amount_kobo,
                    "transaction_reference": ref,
                    "currency_id": "NGN",
                },
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        return {"error": str(e), "success": False}
