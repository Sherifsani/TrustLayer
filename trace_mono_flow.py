#!/usr/bin/env python3
"""
Mono Data Flow Tracer — Run to see exactly what data flows through the system

Usage:
    python trace_mono_flow.py
"""

import sys
import json
from pprint import pprint

# Add TrustLayer to path
sys.path.insert(0, ".")

from integrations.mono import (
    create_connect_session,
    exchange_code_for_account,
    fetch_account_statement,
    fetch_account_income,
)
from ml.credit_scoring import summarize_financial_signals, calculate_trust_score


def print_header(title):
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}\n")


def print_json(data, indent=2):
    print(json.dumps(data, indent=indent, default=str))


def main():
    print_header("MONO DATA FLOW TRACER — Complete Journey")

    # ============ STEP 1: Create Session ============
    print_header("STEP 1: Create Mono Connect Session")
    print("Backend calls: create_connect_session('Adaeze Okafor', 'adaeze@trustlayer.demo')")
    print()

    session_result = create_connect_session("Adaeze Okafor", "adaeze@trustlayer.demo")
    print("✓ Result:")
    print_json(session_result)

    session_id = session_result["session_id"]
    print(f"\n📱 Frontend: Mono widget opens with session_id = '{session_id}'")
    print("👤 User: Reviews bank connection request...")
    print("✅ User: Clicks 'Approve & Continue'")
    print("🔐 Mono: Generates temporary code")

    # ============ STEP 2: Exchange Code for Account ============
    print_header("STEP 2: Exchange Code for Permanent Account ID")

    # In real flow, code comes from widget callback
    test_code = "user_approved_connection_xyz"
    print(f"Frontend sends: code = '{test_code}' to POST /mono/exchange-token")
    print()

    exchange_result = exchange_code_for_account(test_code)
    print("✓ Result:")
    print_json(exchange_result)

    account_id = exchange_result["account_id"]
    print(f"\n💾 Backend: Saves account_id to database")
    print(f"   users.mono_account_id = '{account_id}'")
    print(f"   (This is the permanent link to user's financial data)")

    # ============ STEP 3: Fetch Statement ============
    print_header("STEP 3: Fetch Bank Statement (Transactions)")
    print(f"Backend calls: fetch_account_statement('{account_id}')")
    print()

    statement_result = fetch_account_statement(account_id)
    print(f"Source: {statement_result['source']}")
    print(f"Account ID: {statement_result['account_id']}")
    print()

    transactions = statement_result["data"]["transactions"]
    print(f"✓ Transactions ({len(transactions)} items):")
    print()
    print("  Date         Amount (NGN)   Balance (NGN)")
    print("  " + "-" * 40)
    for txn in transactions:
        date = txn["date"]
        amount = txn["amount"]
        balance = txn["balance"]
        sign = "+" if amount > 0 else ""
        print(f"  {date}   {sign}{amount:>10,}     {balance:>10,}")

    # ============ STEP 4: Fetch Income ============
    print_header("STEP 4: Fetch Income Analytics")
    print(f"Backend calls: fetch_account_income('{account_id}')")
    print()

    income_result = fetch_account_income(account_id)
    print(f"Source: {income_result['source']}")
    print(f"Account ID: {income_result['account_id']}")
    print()

    income_data = income_result["data"]
    monthly_income = income_data.get("monthly_income", [])
    avg_balance = income_data.get("average_balance", 0)

    print(f"✓ Monthly Income (6 months, in NGN):")
    print()
    for i, income in enumerate(monthly_income, 1):
        print(f"  Month {i}: {income:>10,} NGN")

    print()
    print(f"✓ Average Account Balance: {avg_balance:>10,} NGN")

    # ============ STEP 5: Extract Signals ============
    print_header("STEP 5: ML — Extract Financial Signals")
    print("Backend calls: summarize_financial_signals(statement, income)")
    print()

    signals = summarize_financial_signals(statement_result, income_result)

    print("✓ Extracted Signals:")
    print()
    print(f"  transaction_volume        = {signals['transaction_volume']:.1f}")
    print(f"    → Count of transactions in statement")
    print()
    print(f"  income_consistency        = {signals['income_consistency']:.2f}")
    print(f"    → 0 = varies wildly, 1 = perfectly consistent")
    print(f"    → Calculated from monthly income variance")
    print()
    print(f"  avg_monthly_balance       = {signals['avg_monthly_balance']:,.0f} NGN")
    print(f"    → Average balance across the period")

    # ============ STEP 6: Calculate Trust Score ============
    print_header("STEP 6: ML — Calculate Trust Score (300-850)")
    print("Backend calls: calculate_trust_score(tx_volume, income_consistency, avg_balance)")
    print()

    score_result = calculate_trust_score(
        transaction_volume=signals["transaction_volume"],
        income_consistency=signals["income_consistency"],
        avg_monthly_balance=signals["avg_monthly_balance"],
    )

    trust_score = score_result["trust_score"]
    print(f"✓ Final Trust Score: {trust_score}/850")
    print()

    # Show component breakdown
    print("Component Breakdown (normalized to 0-100):")
    print()

    tx_vol_score = score_result["transaction_volume_score"]
    income_cons_score = score_result["income_consistency_score"]
    balance_score = score_result["avg_balance_score"]

    print(f"  Transaction Volume Score:  {tx_vol_score:>6.1f}/100 × 40% weight")
    print(f"  Income Consistency Score:   {income_cons_score:>6.1f}/100 × 35% weight")
    print(f"  Avg Balance Score:          {balance_score:>6.1f}/100 × 25% weight")
    print()

    weighted = (
        (tx_vol_score * 0.40) + (income_cons_score * 0.35) + (balance_score * 0.25)
    )
    print(f"  Weighted Sum:               {weighted:>6.1f}")
    print()
    print(f"  Score = 300 + (weighted / 100) × 550")
    print(f"        = 300 + ({weighted:.1f} / 100) × 550")
    print(f"        = {trust_score}")

    # ============ STEP 7: API Response ============
    print_header("STEP 7: API Response to Frontend")
    print("GET /api/user/credit-profile returns:")
    print()

    api_response = {
        "user_id": "usr_adaeze001",
        "mono_account_id": account_id,
        "trust_score": trust_score,
        "signals": signals,
        "component_scores": {
            "transaction_volume_score": tx_vol_score,
            "income_consistency_score": income_cons_score,
            "avg_balance_score": balance_score,
        },
        "statement_source": statement_result["source"],
        "income_source": income_result["source"],
    }

    print_json(api_response)

    # ============ STEP 8: Frontend Display ============
    print_header("STEP 8: Frontend Dashboard Display")
    print("React component (overview.tsx) receives the above JSON and displays:")
    print()

    print(f"  📊 TrustMeter Gauge:")
    print(f"     Score: {trust_score}/850")
    print()

    print(f"  📈 Component Breakdown Chart:")
    print(f"     • Transaction Volume:    {tx_vol_score:>6.1f}% (indicates frequency of activity)")
    print(f"     • Income Consistency:    {income_cons_score:>6.1f}% (indicates income stability)")
    print(f"     • Average Balance:       {balance_score:>6.1f}% (indicates financial cushion)")
    print()

    print(f"  🔗 Data Sources:")
    print(f"     • Transactions: {statement_result['source']}")
    print(f"     • Income: {income_result['source']}")

    # ============ Summary ============
    print_header("📋 COMPLETE DATA JOURNEY SUMMARY")
    print()
    print("┌─────────────────────────────────────────────────────────┐")
    print("│ What Mono Gives Us:                                     │")
    print("├─────────────────────────────────────────────────────────┤")
    print(f"│ 1. session_id          → Opens widget                  │")
    print(f"│ 2. account_id          → Permanent account link        │")
    print(f"│ 3. transactions[]      → 6 bank transactions           │")
    print(f"│ 4. monthly_income[]    → 6 months of income data       │")
    print(f"│ 5. average_balance     → Account balance metric        │")
    print("├─────────────────────────────────────────────────────────┤")
    print("│ What We Calculate:                                      │")
    print("├─────────────────────────────────────────────────────────┤")
    print(f"│ 1. Financial Signals   → 3 normalized metrics          │")
    print(f"│ 2. Trust Score         → Final 300-850 ranking         │")
    print("├─────────────────────────────────────────────────────────┤")
    print("│ Where It Goes:                                          │")
    print("├─────────────────────────────────────────────────────────┤")
    print(f"│ 1. Database            → account_id saved              │")
    print(f"│ 2. API Response        → Sent to frontend              │")
    print(f"│ 3. Browser             → Displayed on dashboard        │")
    print("└─────────────────────────────────────────────────────────┘")
    print()

    print("✅ Complete flow traced successfully!")
    print()
    print("💡 TIP: Run this script anytime you want to see the actual data")
    print("         flowing through the Mono integration.")
    print()


if __name__ == "__main__":
    main()
