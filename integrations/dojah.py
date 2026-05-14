import os

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("DOJAH_BASE_URL", "https://sandbox.dojah.io")


def _headers() -> dict:
    return {
        "AppId": os.getenv("DOJAH_APP_ID", ""),
        "Authorization": os.getenv("DOJAH_PRIVATE_KEY", ""),
        "Content-Type": "application/json",
    }


async def verify_bvn(bvn: str, first_name: str, last_name: str) -> dict:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{BASE_URL}/api/v1/kyc/bvn",
                headers=_headers(),
                params={"bvn": bvn, "first_name": first_name, "last_name": last_name},
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json().get("entity", {})
    except Exception as e:
        return {"error": str(e), "success": False}


async def lookup_nin(nin: str) -> dict:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{BASE_URL}/api/v1/kyc/nin",
                headers=_headers(),
                params={"nin": nin},
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json().get("entity", {})
    except Exception as e:
        return {"error": str(e), "success": False}


async def liveness_check(selfie_base64: str, bvn: str) -> dict:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{BASE_URL}/api/v1/ml/liveness/",
                headers=_headers(),
                json={"image": selfie_base64},
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json().get("entity", {})
    except Exception as e:
        return {"error": str(e), "success": False}


async def analyse_bank_statement(pdf_base64: str) -> dict:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{BASE_URL}/api/v1/financial/bank-statement",
                headers=_headers(),
                json={"file": pdf_base64},
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json().get("entity", {})
    except Exception as e:
        return {"error": str(e), "success": False}


async def check_phone(phone_number: str) -> dict:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{BASE_URL}/api/v1/kyc/phone-number",
                headers=_headers(),
                params={"phone_number": phone_number},
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json().get("entity", {})
    except Exception as e:
        return {"error": str(e), "success": False}


async def screen_aml(first_name: str, last_name: str, dob: str) -> dict:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{BASE_URL}/api/v1/aml/screening",
                headers=_headers(),
                json={"first_name": first_name, "last_name": last_name, "dob": dob},
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json().get("entity", {})
    except Exception as e:
        return {"error": str(e), "success": False}
