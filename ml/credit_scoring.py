from __future__ import annotations

from math import sqrt
from typing import Any, Iterable


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _extract_list(payload: dict[str, Any], keys: Iterable[str]) -> list[dict[str, Any]]:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            nested = value.get("data")
            if isinstance(nested, list):
                return [item for item in nested if isinstance(item, dict)]
    data = payload.get("data")
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("transactions", "statement", "records", "items"):
            nested = data.get(key)
            if isinstance(nested, list):
                return [item for item in nested if isinstance(item, dict)]
    return []


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    avg = _mean(values)
    variance = sum((v - avg) ** 2 for v in values) / len(values)
    return sqrt(variance)


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def summarize_financial_signals(statement_payload: dict[str, Any], income_payload: dict[str, Any]) -> dict[str, float]:
    transactions = _extract_list(statement_payload, ("transactions", "statement", "records"))
    transaction_volume = float(len(transactions))

    balance_candidates: list[float] = []
    for txn in transactions:
        balance_candidates.append(_to_float(txn.get("balance")))
        balance_candidates.append(_to_float(txn.get("running_balance")))
        balance_candidates.append(_to_float(txn.get("current_balance")))
    balance_candidates = [v for v in balance_candidates if v > 0]

    income_data = income_payload.get("data") if isinstance(income_payload.get("data"), dict) else income_payload
    avg_monthly_balance = _to_float(income_data.get("average_balance"), 0.0)
    if avg_monthly_balance <= 0:
        avg_monthly_balance = _to_float(income_data.get("avg_monthly_balance"), 0.0)
    if avg_monthly_balance <= 0 and balance_candidates:
        avg_monthly_balance = _mean(balance_candidates)

    monthly_inflows: list[float] = []
    if isinstance(income_data, dict):
        for key in ("monthly_income", "income_history", "monthly", "inflows"):
            candidate = income_data.get(key)
            if isinstance(candidate, list):
                for item in candidate:
                    if isinstance(item, dict):
                        monthly_inflows.append(_to_float(item.get("amount"), 0.0))
                        monthly_inflows.append(_to_float(item.get("income"), 0.0))
                    else:
                        monthly_inflows.append(_to_float(item, 0.0))
                break
    monthly_inflows = [v for v in monthly_inflows if v > 0]

    if len(monthly_inflows) >= 2:
        mean_income = _mean(monthly_inflows)
        cv = _std(monthly_inflows) / mean_income if mean_income > 0 else 1.0
        income_consistency = _clamp(1 - cv)
    elif len(monthly_inflows) == 1:
        income_consistency = 0.7
    else:
        income_consistency = 0.5

    return {
        "transaction_volume": transaction_volume,
        "income_consistency": income_consistency,
        "avg_monthly_balance": avg_monthly_balance,
    }


def calculate_trust_score(
    transaction_volume: float,
    income_consistency: float,
    avg_monthly_balance: float,
) -> dict[str, float | int]:
    # Normalize each signal into 0-100 before applying weights.
    transaction_volume_score = _clamp(transaction_volume / 120.0) * 100.0
    income_consistency_score = _clamp(income_consistency) * 100.0
    avg_balance_score = _clamp(avg_monthly_balance / 500000.0) * 100.0

    weighted = (
        transaction_volume_score * 0.40
        + income_consistency_score * 0.35
        + avg_balance_score * 0.25
    )

    trust_score = int(round(300 + (weighted / 100.0) * 550))

    return {
        "trust_score": max(300, min(850, trust_score)),
        "transaction_volume_score": round(transaction_volume_score, 2),
        "income_consistency_score": round(income_consistency_score, 2),
        "avg_balance_score": round(avg_balance_score, 2),
    }
