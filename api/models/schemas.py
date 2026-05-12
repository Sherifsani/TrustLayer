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
    reliability_score: int
    authenticity_score: int
    drivers: List[str]
    signals_used: List[str]


# --- Report (legacy GET /report/:user_id endpoint) ---

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


# --- Internal pipeline return type ---

class TrustScoreResult(BaseModel):
    user_id: str
    score: int
    risk_level: str
    recommendation: str
    reliability_score: int = 0
    authenticity_score: int = 0
    drivers: List[str]
    signals_used: List[str]
    computed_at: datetime
    raw_features: Optional[dict] = None


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


# --- User profile ---

class UserProfileResponse(BaseModel):
    user_id: str
    first_name: Optional[str]
    last_name: Optional[str]
    email: str
    phone: str
    location: Optional[str]
    kyc_status: str
    identity_confidence: float
    joined: datetime
    nin_masked: str
    bvn_masked: str


# --- Score history ---

class ScorePoint(BaseModel):
    score: int
    computed_at: datetime


class ScoreHistoryResponse(BaseModel):
    user_id: str
    history: List[ScorePoint]
    current_score: int
    change_since_start: int


# --- Activity feed ---

class ActivityEvent(BaseModel):
    id: str
    description: str
    source: str
    source_type: str
    timestamp: datetime
    score_impact: Optional[int]
    type: str


class ActivityResponse(BaseModel):
    user_id: str
    events: List[ActivityEvent]


# --- Reports list ---

class ReportItem(BaseModel):
    id: str
    title: str
    report_type: str
    recipient_name: Optional[str]
    pages: Optional[int]
    status: str
    created_at: datetime
    file_url: Optional[str]


class ReportsListResponse(BaseModel):
    reports: List[ReportItem]


class InitiatePaymentRequest(BaseModel):
    user_id: str
    report_type: str
    recipient_id: Optional[str] = None


class InitiatePaymentResponse(BaseModel):
    report_id: str
    checkout_url: str
    txn_ref: str
    amount: int


# --- Auth ---

class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: str
