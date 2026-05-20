# ERP / API Monitoring Dashboard

A self-hosted API health monitoring dashboard built with Flask, SQLite/PostgreSQL, and a dark industrial-style HTML frontend.

---

## Features

| Feature | Details |
|---|---|
| **API health checks** | HTTP GET/POST/HEAD checks against any URL |
| **Response time tracking** | Per-check ms latency, rolling average per endpoint |
| **Uptime percentage** | Calculated from all historical checks |
| **Dashboard** | Live-updating dark UI with status cards and logs table |
| **Failure logs** | Filterable check history with error messages |
| **Email alert simulation** | Logs simulated alerts when endpoints go down (no real email sent) |
| **JWT + API key auth** | All REST endpoints protected; choose either auth method |
| **Scheduler** | Background job checks all active endpoints on a configurable interval |
| **REST API** | Full CRUD for endpoints, manual triggers, stats, logs |
| **Docker ready** | Dockerfile + docker-compose with optional PostgreSQL |
| **Test suite** | pytest tests covering auth, CRUD, stats, and the dashboard |

---

## Quick Start (Local)

### 1. Clone and enter the directory

```bash
git clone <your-repo-url>
cd erp-monitor
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up environment variables

```bash
cp .env.example .env
```

Open `.env` and change at minimum:

```
SECRET_KEY=your-random-secret-here
API_KEY=your-api-key-here
ADMIN_PASSWORD=your-admin-password
```

> **Defaults work fine for local development** — just leave `.env` as-is to get started.

### 5. Run the app

```bash
python run.py
```

Open [http://localhost:5000](http://localhost:5000) in your browser.

The scheduler will start automatically and run health checks every 60 seconds (configurable via `CHECK_INTERVAL_SECONDS` in `.env`).

---

## Run with Docker

### Single container (SQLite)

```bash
cp .env.example .env
docker build -t erp-monitor .
docker run -p 5000:5000 --env-file .env erp-monitor
```

### With Docker Compose (includes PostgreSQL)

```bash
cp .env.example .env

# Edit .env and uncomment the PostgreSQL DATABASE_URL line:
# DATABASE_URL=postgresql://monitor:monitor@db:5432/erp_monitor

docker-compose up --build
```

---

## Configuration (`.env`)

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | `dev-secret-change-me` | JWT signing key |
| `API_KEY` | `dev-api-key-change-me` | Static API key for REST auth |
| `ADMIN_PASSWORD` | `admin` | Password for `/auth/token` |
| `DATABASE_URL` | `sqlite:///monitor.db` | SQLAlchemy DB URL |
| `CHECK_INTERVAL_SECONDS` | `60` | Background check frequency |
| `JWT_EXPIRY_HOURS` | `8` | JWT token lifetime |
| `PORT` | `5000` | HTTP port |
| `FLASK_DEBUG` | `false` | Enable Flask debug mode |

---

## REST API

### Authentication

Every API endpoint requires one of:

**Option A — API Key header:**
```
X-API-Key: your-api-key
```

**Option B — JWT Bearer token:**
```
Authorization: Bearer <token>
```

Get a token:
```bash
curl -X POST http://localhost:5000/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin"}'
```

---

### Endpoints

#### `GET /api/endpoints`
List all monitored endpoints with current status and uptime.

#### `POST /api/endpoints`
Add a new endpoint.

```json
{
  "name": "My Service",
  "url": "https://api.example.com/health",
  "method": "GET",
  "expected_status": 200,
  "timeout": 10,
  "alert_email": "ops@example.com"
}
```

#### `GET /api/endpoints/:id`
Get a single endpoint.

#### `PUT /api/endpoints/:id`
Update an endpoint (any fields from the create payload).

#### `DELETE /api/endpoints/:id`
Delete an endpoint and all its check history.

#### `POST /api/endpoints/:id/check`
Manually trigger an immediate health check for one endpoint.

#### `POST /api/checks/run-all`
Trigger a health check on all active endpoints immediately.

#### `GET /api/logs?page=1&per_page=50&endpoint_id=1&failures_only=true`
Paginated check history. Query params are all optional.

#### `GET /api/alerts`
Last 100 simulated alert logs.

#### `GET /api/stats`
Overall summary: total endpoints, up/down counts, overall uptime %, total checks.

---

### Example curl workflow

```bash
# Set your API key
export KEY="dev-api-key-change-me"

# Add an endpoint
curl -X POST http://localhost:5000/api/endpoints \
  -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{"name":"JSONPlaceholder","url":"https://jsonplaceholder.typicode.com/posts/1"}'

# Manually check it (replace 1 with the returned id)
curl -X POST http://localhost:5000/api/endpoints/1/check \
  -H "X-API-Key: $KEY"

# View logs
curl http://localhost:5000/api/logs \
  -H "X-API-Key: $KEY"

# Get stats
curl http://localhost:5000/api/stats \
  -H "X-API-Key: $KEY"
```

---

## Running Tests

```bash
pip install pytest
pytest tests/ -v
```

---

## Project Structure

```
erp-monitor/
├── app/
│   ├── __init__.py          # App factory, DB init, scheduler setup, seed data
│   ├── models.py            # SQLAlchemy models (MonitoredEndpoint, CheckResult, AlertLog)
│   ├── routes/
│   │   ├── api.py           # REST API blueprint (/api/*)
│   │   ├── auth.py          # Auth blueprint (/auth/token)
│   │   └── dashboard.py     # Dashboard page (/)
│   ├── services/
│   │   ├── auth.py          # JWT generation, decode, require_auth decorator
│   │   └── checker.py       # HTTP check logic, alert simulation, scheduler job
│   └── templates/
│       └── dashboard.html   # Frontend dashboard (single-page, no JS framework)
├── tests/
│   └── test_app.py          # pytest test suite
├── run.py                   # App entry point
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── pytest.ini
├── .env.example
└── .gitignore
```

---

## Alert Simulation

When an endpoint with an `alert_email` set fails, the app logs a simulated alert to the `alert_logs` table (visible in the **Alert Simulations** tab on the dashboard and at `GET /api/alerts`).

To send real emails, replace the body of `maybe_send_alert()` in `app/services/checker.py` with an SMTP call or a service like SendGrid/Mailgun.

---

## Switching to PostgreSQL

1. Set `DATABASE_URL` in `.env`:
   ```
   DATABASE_URL=postgresql://user:password@localhost:5432/erp_monitor
   ```
2. Install the driver:
   ```bash
   pip install psycopg2-binary
   ```
3. Restart the app — tables are created automatically on startup.
