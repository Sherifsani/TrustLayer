def get_telco_data(phone: str, network: str = "MTN") -> dict:
    """Mocked — returns realistic synthetic Mono telco response for hackathon demo."""
    return {
        "topup_count_30d": 8,
        "avg_topup_amount": 500,
        "data_plan_tier": "1GB_weekly",
        "borrow_repaid_ontime": True,
        "account_age_months": 24,
    }
