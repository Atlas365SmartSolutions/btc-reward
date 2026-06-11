# BTC Loyalty Infrastructure

Django modular monolith for merchant-funded BTC loyalty rewards.

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Open `http://127.0.0.1:8000/`.

Run tests:

```bash
pytest -q
```

## Configuration

`manage.py` defaults to `config.settings.development`. Production entry points
use `config.settings.production`.

Create `.env` from `.env.example` for local overrides. Custom production
deploys should set:

```bash
SECRET_KEY=replace-me
DEBUG=False
ALLOWED_HOSTS=example.com
CSRF_TRUSTED_ORIGINS=https://example.com
```

Optional settings:

- `DATABASE_URL`; local development defaults to SQLite.
- `PAYMENT_PROCESSOR_BACKEND`; defaults to `mock`.
- `BTC_PRICE_ORACLE_BACKEND`; defaults to `mock`.
- `DRF_ANON_THROTTLE_RATE` and `DRF_USER_THROTTLE_RATE`.

## Run With Gunicorn

```bash
python manage.py collectstatic --noinput
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

## Admin Users

```bash
ADMIN_BOOTSTRAP_PASSWORD=temporary-password \
python manage.py ensure_admins --admin admin:admin@example.com
```

Admin login accepts username or email when the email is unique.

## Project Shape

```text
apps/
  common/        auth, adapters, admin dashboard context
  merchants/     merchant and customer records
  rewards/       reward policy API and deterministic reward math
  transactions/  BTC transaction ingestion and idempotency
  receipts/      reward receipt and calculation persistence
  treasury/      wallet snapshots, payout batches, reserve health
  ui/            operator pages and signed-cookie public demo
config/          Django settings and URL entry points
templates/       server-rendered UI
tests/           pytest coverage for API, math, security, and UI
```

Views and serializers stay thin. Services orchestrate workflows. Domain modules
own deterministic Decimal-first financial math. Models own persistence,
relationships, constraints, and indexes.

## How It Works

Purchases create BTC transactions and reward receipts. Reward policies define
merchant participation, customer upside share, and treasury coverage thresholds.

Rewards share BTC appreciation rather than purchase principal, using a
high-water mark so the same upside is not paid twice. Reserve health compares
current reward liabilities with treasury wallet snapshots and can pause accrual
when coverage falls below policy.

External payment and BTC price integrations are adapter-backed and currently
mocked for local development. The public demo is browser-session backed; the
operator API and admin surfaces use the database as the system of record.
