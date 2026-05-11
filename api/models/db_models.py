import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bvn_hash = Column(String, nullable=False)
    nin_hash = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    email = Column(String, nullable=False)
    kyc_status = Column(String, default="pending")   # pending | verified | failed | blocked
    identity_confidence = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    user_handle = Column(String, nullable=True, unique=True, index=True)  # e.g. usr_adaeze001

    squad_events = relationship("SquadEvent", back_populates="user")
    trust_scores = relationship("TrustScore", back_populates="user")
    consents = relationship("Consent", back_populates="user")


class SquadEvent(Base):
    __tablename__ = "squad_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    txn_ref = Column(String, nullable=False)
    amount = Column(Integer, nullable=False)          # kobo
    txn_type = Column(String, nullable=False)         # Card | Transfer | Bank | Ussd | VirtualAccount
    status = Column(String, nullable=False)           # Success | Failed | Abandoned
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="squad_events")


class TrustScore(Base):
    __tablename__ = "trust_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    score = Column(Integer, nullable=False)           # 0–100
    risk_level = Column(String, nullable=False)       # low | medium | high | blocked
    drivers = Column(JSON, default=list)
    signals_used = Column(JSON, default=list)
    computed_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="trust_scores")


class Consent(Base):
    __tablename__ = "consents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    business_id = Column(String, nullable=False)
    granted_signals = Column(JSON, default=list)
    denied_signals = Column(JSON, default=list)
    granted_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    revoked = Column(Boolean, default=False)

    user = relationship("User", back_populates="consents")
