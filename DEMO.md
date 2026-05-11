# TrustLayer — Demo Script (5 minutes)

## Pre-demo checklist (do before presenting)
- [ ] `python db/seed.py` — confirm Adaeze and Emeka are seeded
- [ ] Redis container running (`docker ps` to verify)
- [ ] `celery -A api.celery_app worker --loglevel=info` running in Terminal 1
- [ ] `uvicorn api.main:app --reload --port 8000` running in Terminal 2
- [ ] ngrok running, Squad dashboard webhook URL is current (`https://caravan-tweed-pointy.ngrok-free.dev/webhook/squad`)
- [ ] `localhost:4040` open in browser (ngrok inspector)
- [ ] Squad sandbox dashboard open in browser
- [ ] Postman or curl commands loaded and ready to fire
- [ ] `curl http://localhost:8000/health` returns `"db": "connected"`

---

## Minute 1 — Problem (verbal, no switching tabs)

> "Nigeria lost ₦52 billion to financial fraud in 2024.
> Every fintech is making lending decisions blind — they can't see across providers.
> TrustLayer gives them a single trust score: 0 to 100, explainable, real-time,
> powered by Squad payment history, Dojah KYC, and telco signals.
> One API call. Before money moves."

---

## Minute 2 — Live onboarding

- [ ] Fire `POST /onboard` (Postman or curl below):

```bash
curl -X POST http://localhost:8000/onboard \
  -H "Content-Type: application/json" \
  -d '{
    "bvn": "22222222222",
    "nin": "70123456789",
    "phone": "09011111111",
    "selfie_base64": "data:image/jpeg;base64,/9j/test",
    "first_name": "Adaeze",
    "last_name": "Okafor",
    "email": "live@trustlayer.demo"
  }'
```

- [ ] Point out: BVN + NIN verified via Dojah in parallel
- [ ] Point out: liveness check passed
- [ ] Show `identity_confidence` in response (e.g. 0.94)
- [ ] Say: *"This is the identity layer. SHA-256 hashed before hitting our DB — raw BVN never stored."*

---

## Minute 3 — Live scoring (Adaeze — approve path)

```bash
curl -X POST http://localhost:8000/score \
  -H "Authorization: Bearer biz_key_kwikloans_demo" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "usr_adaeze001"}'
```

- [ ] Score appears: `trust_score: 78–100`, `risk_level: "low"`, `recommendation: "approve"`
- [ ] Read the 3 drivers out loud — point at SHAP explainability
- [ ] Say: *"Every score is explainable. A risk officer always knows why. This is not a black box."*
- [ ] Show `signals_used`: squad_history, telco_data, kyc

---

## Minute 4 — Squad payment gate + Emeka (decline path)

**Transfer fires for Adaeze:**
- [ ] Show Squad Transfer API call firing (or point at the approve button in the UI)
- [ ] Switch to ngrok inspector (`localhost:4040`) — Squad webhook incoming
- [ ] Celery terminal shows `recompute_score` task processing

**Score Emeka:**
```bash
curl -X POST http://localhost:8000/score \
  -H "Authorization: Bearer biz_key_kwikloans_demo" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "usr_emeka001"}'
```

- [ ] Score: `trust_score: 8–31`, `risk_level: "high"`, `recommendation: "decline"`
- [ ] Point at drivers: `"Unusual transaction pattern detected"` — anomaly flag
- [ ] Show `"Transaction failure rate → -99 pts"`
- [ ] Say: *"Transfer blocked. The AI controlled whether money moved. Zero manual review."*

---

## Minute 5 — Consent graph + roadmap

- [ ] Show `POST /consent` toggle (or screenshot if dashboard not built):

```bash
curl -X POST http://localhost:8000/consent \
  -H "Authorization: Bearer <user_jwt>" \
  -H "Content-Type: application/json" \
  -d '{"business_id": "kwik_loans", "action": "grant", "signals": ["trust_score", "squad_history"], "expires_days": 30}'
```

- [ ] Say: *"Users control what lenders see. NDPR compliant by design. Data sovereignty built in."*
- [ ] Say: *"API today. SDK in Q1. Self-serve PaaS by Q3 2026.*
        *430 fintechs in Nigeria need this infrastructure.*
        *TrustLayer is the trust layer."*

---

## Squad webhook live demo (if time allows after Minute 4)

```bash
# Simulate a Squad payment event hitting the webhook
curl -X POST https://caravan-tweed-pointy.ngrok-free.dev/webhook/squad \
  -H "Content-Type: application/json" \
  -H "x-squad-encrypted-body: <compute_with_squad_key>" \
  -d '{
    "Event": "charge_successful",
    "TransactionRef": "SQTEST_DEMO_001",
    "Body": {
      "amount": 500000,
      "transaction_ref": "SQTEST_DEMO_001",
      "transaction_status": "Success",
      "email": "adaeze@trustlayer.demo",
      "transaction_type": "Card",
      "merchant_amount": 500000,
      "created_at": "2025-08-24T15:26:38.994"
    }
  }'
```

- [ ] Webhook returns `{"status": "ok"}` in < 100ms
- [ ] Celery terminal shows: `[tasks] recompute_score` running
- [ ] Score Adaeze again — score updated from new event

---

## If something breaks

| Problem | Recovery |
|---|---|
| Score endpoint fails | Open Swagger UI at `localhost:8000/docs` and demo from there |
| Webhook fails | Show ngrok inspector with a pre-captured request screenshot |
| DB connection fails | Show `GET /health` error, explain architecture, pivot to slides |
| Celery not processing | Show the task queue in Redis, explain async decoupling |
| ngrok URL changed | `curl http://localhost:4040/api/tunnels \| jq '.tunnels[0].public_url'` → update Squad dashboard |

---

## Key numbers to cite

- **₦52bn** lost to financial fraud in Nigeria in 2024
- **430+** licensed fintechs in Nigeria (CBN 2024)
- **15 features** across Squad, Dojah, and Mono telco signals
- **< 200ms** average scoring latency
- **0 raw PII** stored — BVN/NIN SHA-256 hashed at ingestion
