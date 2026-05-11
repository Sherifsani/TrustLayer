from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr


# --- Onboard ---

class OnboardRequest(BaseModel):
    bvn: str
    nin: str
    phone: str
    selfie_base64: str
    first_name: str
    last_name: str
    email: EmailStr


class OnboardResponse(BaseModel):
    user_id: str
    kyc_status: str
    identity_confidence: float
    flags: List[str]


# --- Score ---

class ScoreRequest(BaseModel):
    user_id: str


class ScoreResponse(BaseModel):
    trust_score: int
    risk_level: str
    recommendation: str
    drivers: List[str]
    signals_used: List[str]


# --- Report ---

class ReportResponse(BaseModel):
    user_id: str
    trust_score: int
    risk_level: str
    drivers: List[str]
    signals_used: List[str]
    computed_at: str


# --- Consent ---

class ConsentRequest(BaseModel):
    business_id: str
    action: str          # grant | revoke
    signals: List[str]
    expires_days: int = 30


class ConsentResponse(BaseModel):
    user_id: str
    business_id: str
    granted_signals: List[str]
    denied_signals: List[str]
    revoked: bool


# --- Webhook ---

# --- Internal pipeline return type ---

class TrustScoreResult(BaseModel):
    user_id: str
    score: int
    risk_level: str
    recommendation: str
    drivers: List[str]
    signals_used: List[str]
    computed_at: datetime


# --- Webhook ---

class SquadWebhookBody(BaseModel):
    amount: int
    transaction_ref: str
    transaction_status: str
    email: str
    transaction_type: str
    merchant_amount: int
    created_at: str


class SquadWebhookPayload(BaseModel):
    Event: str
    TransactionRef: str
    Body: SquadWebhookBody
