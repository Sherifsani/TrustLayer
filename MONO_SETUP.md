Mono Connect v2 — local developer setup

1) Environment variables (add to `TrustLayer/.env`)

MONO_PUBLIC_KEY=your_mono_public_key_here
MONO_SECRET_KEY=your_mono_secret_key_here
MONO_BASE_URL=https://api.withmono.com
BACKEND_BASE_URL=http://127.0.0.1:8000
FRONTEND_BASE_URL=http://127.0.0.1:5173

2) Quick run commands (Windows PowerShell)

```powershell
# from repo root
Set-Location C:\Users\olani\TrustLayer
# install deps
pip install -r requirements.txt
# run alembic migrations
alembic upgrade head
# start backend
.\.venv\Scripts\python.exe -m uvicorn api.main:app --reload --port 8000
```

3) Frontend (open new terminal)

```powershell
Set-Location C:\Users\olani\TrustLayer_Client
pnpm dev -- --host 127.0.0.1 --port 5173
```

4) Testing the flow (local mock)

- In onboarding (Step 3) click "Connect" on the Bank row. A popup will open the mock Mono widget.
- Click "Approve & Return" in the popup — this will call `/mono/exchange-token` and persist `mono_account_id` to the `users` table.
- Verify in your DB that `mono_account_id` is populated for the demo user `usr_adaeze001`.

5) Webhook configuration

- If you want real Mono webhooks, set `FRONTEND_BASE_URL` or use ngrok to expose `BACKEND_BASE_URL` publicly and register `https://<your-public>/webhook/mono` in the Mono Dashboard.
