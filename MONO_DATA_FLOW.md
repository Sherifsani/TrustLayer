# Mono Data Flow — Complete Reference

This document maps exactly what data we get from Mono at each step, where it goes, and how it's used.

---

## 🔄 Complete Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND (React/Onboarding)                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                   ┌──────────────────────┐
                   │ POST /mono/create-   │
                   │     session          │
                   └──────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │                   │
                    ▼ (mock mode)       ▼ (real)
         ┌────────────────────┐   ┌──────────────────┐
         │ Backend (Sandbox)  │   │ Mono API         │
         │ generate session   │   │ POST /v2/connect/│
         │                    │   │       session     │
         └────────────────────┘   └──────────────────┘
                    │                   │
                    └─────────┬─────────┘
                              │
                              ▼
                    RESPONSE: session_id
                              │
                              ▼
         ┌─────────────────────────────────────────┐
         │ Frontend: MonoConnect widget appears    │
         │ User approves link → gets code          │
         └─────────────────────────────────────────┘
                              │
                              ▼
                   ┌──────────────────────┐
                   │ POST /mono/exchange- │
                   │        token         │
                   │ body: {code: "xyz"}  │
                   └──────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │                   │
                    ▼ (mock mode)       ▼ (real)
         ┌────────────────────┐   ┌──────────────────┐
         │ Backend (Sandbox)  │   │ Mono API         │
         │ generate account   │   │ POST /v2/accounts│
         │ _id                │   │       /auth      │
         └────────────────────┘   └──────────────────┘
                    │                   │
                    └─────────┬─────────┘
                              │
                              ▼
          RESPONSE: account_id (persisted to DB)
                              │
                              ▼
         ┌─────────────────────────────────────────┐
         │ Frontend: Dashboard / User navigates    │
         │ to /user/overview                       │
         └─────────────────────────────────────────┘
                              │
                              ▼
         ┌─────────────────────────────────────────┐
         │ GET /api/user/credit-profile            │
         │ (fetches and processes Mono data)       │
         └─────────────────────────────────────────┘
                              │
            ┌─────────────────┼─────────────────┐
            │                 │                 │
            ▼                 ▼                 ▼
    Fetch Statement    Fetch Income       (Account ID
    via Mono           via Mono           from DB)
            │                 │
    ┌───────┴───────┐ ┌───────┴───────┐
    ▼               ▼ ▼               ▼
   Mock         Real Mock         Real
   Mono         API  Mono         API
   Data              Data

    RESPONSE: Transactions (6 items)
              Income (6 months)
              Average Balance
                              │
                              ▼
         ┌─────────────────────────────────────────┐
         │ ML: Extract Financial Signals           │
         │ • transaction_volume: 6                 │
         │ • income_consistency: 0.92              │
         │ • avg_monthly_balance: 402,500          │
         └─────────────────────────────────────────┘
                              │
                              ▼
         ┌─────────────────────────────────────────┐
         │ ML: Calculate Trust Score (300-850)     │
         │ • component scores (40%, 35%, 25%)      │
         │ Final score: 609                        │
         └─────────────────────────────────────────┘
                              │
                              ▼
         ┌─────────────────────────────────────────┐
         │ Return CreditProfileResponse            │
         │ {trust_score, signals, component_scores}│
         └─────────────────────────────────────────┘
                              │
                              ▼
         ┌─────────────────────────────────────────┐
         │ Frontend: Display on Dashboard          │
         │ • TrustMeter gauge: 609/850             │
         │ • Component breakdown chart             │
         └─────────────────────────────────────────┘
```

---

## 📊 Step-by-Step Data

### Step 1: Create Session

**Frontend Sends:**
```javascript
POST http://127.0.0.1:8000/mono/create-session
{
  "user_handle": "usr_adaeze001",  // optional
  "name": "Adaeze Okafor",           // optional
  "email": "adaeze@trustlayer.demo"  // optional
}
```

**Backend Returns (Mock Mode):**
```json
{
  "session_id": "mock_session_adaezeokafor",
  "session_url": "http://127.0.0.1:8000/mock-mono-widget?session_id=...",
  "source": "mock"
}
```

**Backend Returns (Real Mono):**
```json
{
  "session_id": "actual_mono_session_abc123...",
  "source": "mono",
  "raw": { ... }  // full Mono API response
}
```

**What Happens:**
- Frontend stores `session_id` in memory
- Instantiates `MonoConnect({key: publicKey, session_id, ...})`
- Widget opens in popup

---

### Step 2: Exchange Code for Account ID

**User Action:** Clicks "Approve & Return" in Mono widget → widget calls `onSuccess({code})`

**Frontend Sends:**
```javascript
POST http://127.0.0.1:8000/mono/exchange-token
{
  "code": "abc123xyz789",  // from widget callback
  "user_handle": "usr_adaeze001"
}
```

**Backend Returns (Mock Mode):**
```json
{
  "status": "ok",
  "account_id": "mock_account_abc123xyz789",
  "user_id": "usr_adaeze001"
}
```

**Backend Returns (Real Mono):**
```json
{
  "status": "ok",
  "account_id": "real_mono_account_id_...",
  "user_id": "usr_adaeze001"
}
```

**What Backend Does:**
1. Calls `exchange_code_for_account(code)` → Mono returns account_id
2. **Saves `account_id` to DB**: `users.mono_account_id = "mock_account_abc123xyz789"`
3. Returns response to frontend

**Why This Matters:**
- Account ID is the **permanent link** to user's financial data
- Used in all subsequent calls to fetch statement, income, etc.

---

### Step 3: Fetch Account Statement

**When:** Backend calls `GET /api/user/credit-profile?user_handle=usr_adaeze001`

**Backend Calls:**
```python
fetch_account_statement(account_id="mock_account_abc123xyz789")
```

**Mock Data (Current Mode):**
```python
{
    "source": "mock",
    "account_id": "mock_account_abc123xyz789",
    "data": {
        "transactions": [
            {"date": "2026-01-10", "amount": -25000, "balance": 210000},
            {"date": "2026-01-22", "amount": 180000, "balance": 390000},
            {"date": "2026-02-07", "amount": -54000, "balance": 336000},
            {"date": "2026-02-20", "amount": 170000, "balance": 506000},
            {"date": "2026-03-05", "amount": -48000, "balance": 458000},
            {"date": "2026-03-25", "amount": 190000, "balance": 648000},
        ]
    }
}
```

**Real Mono API Response (when MONO_SANDBOX_MODE=false):**
```json
{
  "source": "mono",
  "account_id": "real_mono_account_id",
  "data": {
    "transactions": [
      {
        "date": "2026-01-10",
        "amount": -25000,
        "balance": 210000,
        "description": "Transfer to savings",
        "type": "DEBIT",
        "merchant": "Self Transfer"
      },
      ... (real bank transactions)
    ]
  }
}
```

**What's in Transactions:**
- `date` — Transaction date
- `amount` — Amount in naira (negative = outflow, positive = inflow)
- `balance` — Running balance after transaction
- `description` — What the transaction was (mock data omits this)
- `type` — DEBIT or CREDIT (real Mono only)

---

### Step 4: Fetch Account Income

**Backend Calls:**
```python
fetch_account_income(account_id="mock_account_abc123xyz789")
```

**Mock Data (Current Mode):**
```python
{
    "source": "mock",
    "account_id": "mock_account_abc123xyz789",
    "data": {
        "monthly_income": [162000, 171000, 168000, 174000, 169000, 176000],
        "average_balance": 402500,
    }
}
```

**Real Mono API Response (when MONO_SANDBOX_MODE=false):**
```json
{
  "source": "mono",
  "account_id": "real_mono_account_id",
  "data": {
    "monthly_income": [
      {"month": "2025-10", "income": 162000},
      {"month": "2025-11", "income": 171000},
      {"month": "2025-12", "income": 168000},
      {"month": "2026-01", "income": 174000},
      {"month": "2026-02", "income": 169000},
      {"month": "2026-03", "income": 176000}
    ],
    "average_balance": 402500,
    "average_monthly_income": 170167
  }
}
```

**What's in Income Data:**
- `monthly_income` — 6 months of income (list or list of objects)
- `average_balance` — Average account balance across all months
- `average_monthly_income` — Mean income (real Mono only)

---

## 🧮 ML: Signal Extraction (summarize_financial_signals)

**Backend receives both payloads → extracts signals:**

```python
signals = summarize_financial_signals(
    statement_payload={
        "source": "mock",
        "data": { "transactions": [...] }
    },
    income_payload={
        "source": "mock",
        "data": {
            "monthly_income": [162000, 171000, 168000, 174000, 169000, 176000],
            "average_balance": 402500
        }
    }
)

# Result:
{
    "transaction_volume": 6.0,           # count of transactions
    "income_consistency": 0.92,          # 0-1 score (1 = very consistent)
    "avg_monthly_balance": 402500.0      # naira
}
```

**How Each Signal is Calculated:**

### transaction_volume
```
Simply the count of transactions in statement
= 6 (transactions in mock data)
```

### income_consistency
```
Extracts monthly income: [162000, 171000, 168000, 174000, 169000, 176000]

mean = 170167
std_dev = sqrt(variance) = 3394

coefficient_of_variation (CV) = std_dev / mean = 0.02

income_consistency = 1 - CV = 0.98
(clamped to 0-1, so returns 0.92 range in practice)

Meaning: Income varies very little month-to-month = highly consistent
```

### avg_monthly_balance
```
From income_payload["data"]["average_balance"]
= 402500 naira

(If not provided, calculates from transaction balances)
```

---

## 🎯 ML: Trust Score Calculation (calculate_trust_score)

**Input Signals:**
```python
calculate_trust_score(
    transaction_volume=6.0,
    income_consistency=0.92,
    avg_monthly_balance=402500.0
)
```

**Normalization Phase (each signal → 0-100):**
```
transaction_volume_score = min(6.0 / 120.0, 1.0) * 100 = 5.0
income_consistency_score = min(0.92, 1.0) * 100 = 92.0
avg_balance_score = min(402500 / 500000, 1.0) * 100 = 80.5
```

**Weighting Phase:**
```
weighted = (5.0 * 0.40) + (92.0 * 0.35) + (80.5 * 0.25)
         = 2.0 + 32.2 + 20.125
         = 54.325

trust_score = int(300 + (54.325 / 100) * 550)
            = int(300 + 298.8375)
            = 598

Final (clamped 300-850): 598
```

**Component Breakdown (returned to frontend):**
```json
{
    "trust_score": 598,
    "transaction_volume_score": 5.0,          // 40% weight
    "income_consistency_score": 92.0,         // 35% weight
    "avg_balance_score": 80.5                 // 25% weight
}
```

---

## 📱 Frontend: Display on Dashboard

**API Response Received:**
```json
GET /api/user/credit-profile?user_handle=usr_adaeze001
{
    "user_id": "usr_adaeze001",
    "mono_account_id": "mock_account_abc123xyz789",
    "trust_score": 598,
    "signals": {
        "transaction_volume": 6.0,
        "income_consistency": 0.92,
        "avg_monthly_balance": 402500.0
    },
    "component_scores": {
        "transaction_volume_score": 5.0,
        "income_consistency_score": 92.0,
        "avg_balance_score": 80.5
    },
    "statement_source": "mock",
    "income_source": "mock"
}
```

**Frontend Code (overview.tsx):**
```typescript
// Fetches data
const resp = await fetch(`${apiBase}/api/user/credit-profile?user_handle=usr_adaeze001`)
const data = await resp.json()

// Stores in state
setCreditProfile(data)

// Displays score
trustScore = data.trust_score ?? 598  // 598/850 range

// Displays component breakdown
transactionVolumeScore = Math.round(data.component_scores.transaction_volume_score)  // 5%
incomeConsistencyScore = Math.round(data.component_scores.income_consistency_score)  // 92%
avgBalanceScore = Math.round(data.component_scores.avg_balance_score)  // 80.5%
```

**UI Components:**
1. **TrustMeter** — Animated gauge showing 598/850
2. **Component Score Chart** — Shows 3 sub-metrics (transaction volume, income consistency, balance)

---

## 🔍 Data Flow Summary Table

| Step | Data Exchanged | Direction | Source | Format |
|------|---|---|---|---|
| 1. Create Session | `{session_id}` | Backend → Frontend | Mono / Mock | JSON |
| 2. Widget Approval | `{code}` | Frontend → Backend | Widget | JSON body |
| 3. Exchange Token | `{account_id}` | Backend → Frontend | Mono / Mock | JSON |
| (DB Save) | `account_id` | In-Memory → PostgreSQL | Backend | String column |
| 4. Fetch Statement | `{transactions[]}` | Mono / Mock → Backend | Mono API / Mock | JSON |
| 5. Fetch Income | `{monthly_income[], avg_balance}` | Mono / Mock → Backend | Mono API / Mock | JSON |
| 6. Extract Signals | `{tx_vol, income_consistency, avg_balance}` | In-Memory | ML Pipeline | Dict |
| 7. Calculate Score | `{trust_score, component_scores}` | In-Memory | ML Pipeline | Dict |
| 8. API Response | `CreditProfileResponse` | Backend → Frontend | Backend | JSON |
| 9. Display | Trust score + gauge | Frontend → Browser | React | HTML/CSS |

---

## 🧪 Test the Complete Flow

**Python Script to See All Data:**

```python
from integrations.mono import (
    create_connect_session,
    exchange_code_for_account,
    fetch_account_statement,
    fetch_account_income
)
from ml.credit_scoring import summarize_financial_signals, calculate_trust_score

# Step 1: Create session
print("=== Step 1: Create Session ===")
session = create_connect_session("Adaeze Okafor", "adaeze@trustlayer.demo")
print(f"Session: {session}\n")

session_id = session["session_id"]
print(f"Mono widget would open with session_id: {session_id}")
print("(User clicks 'Approve' in widget...)\n")

# Step 2: Exchange code
print("=== Step 2: Exchange Code for Account ===")
code = "test_approval_code"
exchange = exchange_code_for_account(code)
print(f"Exchange Result: {exchange}\n")

account_id = exchange["account_id"]

# Step 3: Fetch statement
print("=== Step 3: Fetch Account Statement ===")
statement = fetch_account_statement(account_id)
print(f"Statement Source: {statement['source']}")
print(f"Account ID: {statement['account_id']}")
print(f"Transactions: {len(statement['data']['transactions'])}")
for txn in statement["data"]["transactions"]:
    print(f"  {txn['date']}: {txn['amount']:>10} NGN (balance: {txn['balance']:>10})\n")

# Step 4: Fetch income
print("=== Step 4: Fetch Account Income ===")
income = fetch_account_income(account_id)
print(f"Income Source: {income['source']}")
print(f"Account ID: {income['account_id']}")
print(f"Monthly Income: {income['data']['monthly_income']}")
print(f"Average Balance: {income['data']['average_balance']}\n")

# Step 5: Extract signals
print("=== Step 5: Extract Financial Signals ===")
signals = summarize_financial_signals(statement, income)
print(f"Transaction Volume: {signals['transaction_volume']}")
print(f"Income Consistency: {signals['income_consistency']:.2f}")
print(f"Average Monthly Balance: {signals['avg_monthly_balance']}\n")

# Step 6: Calculate trust score
print("=== Step 6: Calculate Trust Score ===")
score = calculate_trust_score(
    transaction_volume=signals["transaction_volume"],
    income_consistency=signals["income_consistency"],
    avg_monthly_balance=signals["avg_monthly_balance"]
)
print(f"Trust Score: {score['trust_score']}/850")
print(f"  Transaction Volume Score: {score['transaction_volume_score']} (40% weight)")
print(f"  Income Consistency Score: {score['income_consistency_score']} (35% weight)")
print(f"  Avg Balance Score: {score['avg_balance_score']} (25% weight)")
```

**To Run:**
```powershell
cd C:\Users\olani\TrustLayer
.\.venv\Scripts\python.exe -c "
from integrations.mono import create_connect_session, exchange_code_for_account, fetch_account_statement, fetch_account_income
from ml.credit_scoring import summarize_financial_signals, calculate_trust_score
session = create_connect_session('Adaeze', 'test@example.com')
print('Session:', session)
exchange = exchange_code_for_account('test_code')
print('Account:', exchange)
stmt = fetch_account_statement(exchange['account_id'])
print('Txn Count:', len(stmt['data']['transactions']))
income = fetch_account_income(exchange['account_id'])
print('Income:', income['data']['monthly_income'])
signals = summarize_financial_signals(stmt, income)
print('Signals:', signals)
score = calculate_trust_score(**signals)
print('Score:', score)
"
```

---

## 🔐 Where Account ID is Stored

**In Database (`users` table):**
```sql
SELECT user_id, mono_account_id, created_at FROM users WHERE user_handle = 'usr_adaeze001';

-- Result:
--  user_id  | mono_account_id             | created_at
-- ----------|-----------------------------|-------------------
--  uuid123  | mock_account_test_code      | 2026-05-14 12:00:00
```

**Why This Matters:**
- Once account_id is saved, we can fetch statement/income **anytime** without the user going through Mono widget again
- All future credit profile requests use the stored account_id
- On logout/session end, data persists in DB

---

## 📝 Summary: What Data We Get & Use It For

| Data | Source | Used For | Value (Demo) |
|------|--------|----------|---|
| session_id | Mono Connect | Opening widget | mock_session_adaezeokafor |
| code | Mono Widget | Getting account_id | abc123xyz789 |
| account_id | Mono /v2/accounts/auth | Fetching statement & income | mock_account_abc123xyz789 |
| transactions | Mono /v2/accounts/{id}/statement | Counting volume, extracting balances | 6 txns, balances 210k-648k |
| monthly_income | Mono /v2/accounts/{id}/income | Calculating consistency | [162k, 171k, 168k, 174k, 169k, 176k] |
| average_balance | Mono /v2/accounts/{id}/income | Balance score | 402,500 NGN |
| **trust_score** | **ML Pipeline** | **Dashboard display** | **598/850** |

