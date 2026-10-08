<<<<<<< HEAD
# NetPulse — Broadband Recharge & Revenue Intelligence Platform

A Flask + SQLite MVP built for the Codegnan Data Dynamos hackathon.

## Features

1. **Customer recharge & billing history** — pick a connection, view the current plan and due date, recharge online (with a "simulate failed payment" toggle for the demo), and see the last 10 transactions.
2. **Staff follow-up queue** — customers whose plan expires within 7 days, with a one-click "Mark Followed Up" action.
3. **Admin revenue dashboard** — total revenue, customer count, payment recovery rate, and customers nearing expiry as stat cards, plus three Chart.js visualizations: monthly revenue trend, plan-wise subscriber distribution, and renewal vs. lapse rate — all fed by simple JSON APIs (`/api/summary`, `/api/revenue_trend`, `/api/plan_distribution`, `/api/renewal_rate`).

## Tech stack

- **Backend:** Python, Flask
- **Database:** SQLite (file-based, zero setup)
- **Frontend:** Jinja2 templates, Bootstrap 5, Chart.js (both via CDN)
- No authentication — role is chosen by navigation only, to keep the demo fast.

## Setup (Replit or local)

```bash
pip install -r requirements.txt
python app.py
```

The app seeds a fresh `broadband.db` with 3 plans, 6 customers, ~30 transactions
(spread over the last 5 months), and usage logs every time it starts, so the
dashboard always has data to show. Two customers are deliberately set to
expire within the next week so the follow-up queue and reminder logic are
visible immediately.

Visit `http://localhost:5000` (or the Replit webview URL). Start at the
homepage and use the three cards to jump into the Customer, Staff, or Admin
views.

## Design decisions

- Kept to 3 core flows only (recharge, follow-up, analytics) to stay within
  the hackathon time budget — no auth, no ML, no test suite.
- All chart data is served through small JSON API endpoints rather than
  rendered server-side, so the dashboard updates live and the endpoints can
  be reused (e.g., for a future mobile app or export feature).
- Revenue trend, plan distribution, and renewal rate are computed directly
  with SQL aggregation (`GROUP BY`, `SUM`, `COUNT`) — no external analytics
  library needed for this data size.
- Visual identity: a deep-teal telecom palette (`#0F3443` / `#17B8A6`)
  instead of default Bootstrap blue, to feel distinct in the demo lineup.

## Demo flow

1. Home → Customer → pick a connection → view plan/due date → recharge.
2. Home → Follow-ups → see the customer set to expire soon → mark followed up.
3. Home → Admin → revenue trend updates, plan distribution, renewal rate.
=======
# netpulse-broadband-app-
>>>>>>> 360aef2e70d48052f96bd39100dd14d9f87c2fbc
