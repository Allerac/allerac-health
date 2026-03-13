# Allerac Health — Architecture

## Overview

Allerac Health is a multi-user health data aggregation portal that connects to Garmin Connect, fetches biometric data in the background, and presents it through an interactive dashboard.

The system follows a microservices architecture with clear separation between the frontend, API, background worker, and data stores.

---

## System Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                          User Browser                           │
└────────────────────────────┬────────────────────────────────────┘
                             │
                ┌────────────▼─────────────┐
                │   Frontend (Next.js 14)   │
                │   Port 3002               │
                └────────────┬──────────────┘
                             │ HTTP/REST + JWT
                ┌────────────▼─────────────┐
                │   Backend API (FastAPI)   │
                │   Port 8000               │
                └────┬──────────┬───────────┘
                     │          │
          ┌──────────┤    ┌─────▼──────┐
          │          │    │   Redis     │
          │          │    └─────┬──────┘
    ┌─────▼──────┐   │          │
    │ PostgreSQL  │   │   ┌──────▼──────┐
    └─────────────┘   │   │   Worker    │
                      │   │  (Celery)   │
    ┌─────────────┐   │   └──────┬──────┘
    │  InfluxDB   │◄──┘          │
    └─────────────┘◄─────────────┘
                             │
                ┌────────────▼─────────────┐
                │    Garmin Connect API     │
                │    (External)             │
                └───────────────────────────┘
```

---

## Services

| Service | Technology | Port | Responsibility |
|---|---|---|---|
| **frontend** | Next.js 14, Tailwind CSS | 3002 | UI, session management |
| **backend** | FastAPI, Python 3.11 | 8000 | REST API, authentication, orchestration |
| **worker** | Celery, Python 3.11 | — | Background Garmin data fetching |
| **postgres** | PostgreSQL 16 | 5432 | Users, credentials, sync history |
| **influxdb** | InfluxDB 1.11 | 8086 | Health metrics (time-series) |
| **redis** | Redis 7 | 6379 | Celery task queue and broker |

All services are orchestrated with Docker Compose and communicate over an internal Docker network.

---

## Authentication

### User Authentication (JWT)

1. User registers or logs in via `POST /api/v1/auth/login`
2. Backend validates credentials (bcrypt) and issues two tokens:
   - **Access token** — 30-minute expiry, used for API calls
   - **Refresh token** — 7-day expiry, used to obtain new access tokens
3. Frontend stores tokens in `localStorage` and attaches them via `Authorization: Bearer {token}` on every request (Axios interceptor)
4. On 401 responses, the interceptor automatically calls `POST /api/v1/auth/refresh` and retries the original request
5. If refresh fails, the user is redirected to `/login`

### Session Management (Frontend)

NextAuth.js handles the browser session using a JWT strategy. It wraps the backend login flow through a `CredentialsProvider`, stores tokens in the NextAuth JWT cookie, and exposes them via `useSession`.

---

## Garmin Integration

### Connection Flow

```
User enters Garmin credentials (Settings page)
        │
        ▼
POST /api/v1/garmin/connect
        │
        ▼
Backend spawns login thread
        │
        ├─── No MFA ──► Login succeeds
        │                     │
        │               Session dump encrypted
        │               and saved to PostgreSQL
        │
        └─── MFA required ──► Returns { mfa_pending: true } to frontend
                                     │
                               User enters code
                                     │
                               POST /api/v1/garmin/mfa
                                     │
                               Code sent to thread via Queue
                                     │
                               Login completes
                                     │
                               Session dump encrypted
                               and saved to PostgreSQL
```

The MFA flow uses a `threading.Queue` pattern: the login thread blocks waiting for the code while the API returns immediately to the frontend. When the user submits the code, it is placed on the queue and the login thread resumes.

### Credential Storage

- Garmin session dump (OAuth tokens) is encrypted with **Fernet** symmetric encryption
- The encryption key is derived from the `ENCRYPTION_KEY` environment variable via SHA256
- Encrypted bytes are stored in the `garmin_credentials` table in PostgreSQL
- Decryption only happens in-memory within the worker/backend processes

---

## Data Pipeline

### Initial Sync

Triggered immediately after a successful Garmin connection:

```
POST /api/v1/garmin/sync
        │
        ▼
Backend enqueues Celery task: initial_sync(user_id)
        │
        ▼
Worker decrypts credentials from PostgreSQL
        │
        ▼
Worker authenticates with Garmin Connect
        │
        ▼
Fetches last 30 days of data:
  - get_stats(date)         → steps, calories, distance, active minutes
  - get_sleep_data(date)    → sleep duration, deep / light / REM / awake
  - get_heart_rates(date)   → resting, average, max heart rate
  - get_body_battery(date)  → battery level min / max / end of day
        │
        ▼
Writes time-series points to InfluxDB (tagged with user_id)
        │
        ▼
Updates sync_jobs and garmin_credentials in PostgreSQL
```

### Incremental Sync (Scheduled)

Celery Beat runs scheduled tasks:

| Schedule | Task | Description |
|---|---|---|
| Every hour (minute 0) | `sync_all_users` | Queues incremental sync for all connected users (last 1–2 days) |
| Every hour (minute 30) | `cleanup_mfa_sessions` | Removes expired MFA sessions (>10 min) |
| Daily at 3 AM UTC | `cleanup_old_jobs` | Removes old sync job records |

---

## Data Storage

### Why two databases?

| | PostgreSQL | InfluxDB |
|---|---|---|
| **Type** | Relational | Time-series |
| **Stores** | Users, credentials, sync history, settings | Health metrics (steps, sleep, heart rate, etc.) |
| **Query pattern** | Lookup by ID, joins | Time-range queries, aggregations |
| **Optimized for** | Transactional consistency | High-frequency writes, time-based reads |

### PostgreSQL Schema

```
users
  id (UUID PK), email (unique), password_hash
  name, avatar_url
  is_active, created_at, updated_at

garmin_credentials
  id (UUID PK), user_id (FK, unique)
  email_encrypted, oauth1_token_encrypted (session dump)
  is_connected, mfa_pending
  last_sync_at, last_error, sync_enabled

sync_jobs
  id (UUID PK), user_id (FK)
  status (pending | running | completed | failed)
  job_type (full | incremental | manual)
  started_at, completed_at, records_fetched, error_message

mfa_sessions
  id (UUID PK), user_id (FK, unique)
  garmin_email, session_data (encrypted)
  expires_at (10 min TTL)

user_settings
  id (UUID PK), user_id (FK, unique)
  timezone, sync_interval_minutes
  notifications_enabled, fetch_selection (JSONB)
```

### InfluxDB Schema

All measurements include the tag `user_id` for per-user data isolation.

| Measurement | Fields |
|---|---|
| `daily_stats` | steps, calories, distance, active_minutes, floors_climbed |
| `sleep` | duration, deep, light, rem, awake, score |
| `heart_rate` | resting, avg, max |
| `body_battery` | min, max, end, charged, drained |
| `stress` | avg, max, rest_duration |
| `hrv` | weekly_avg, last_night, status |

---

## API Endpoints

### Auth — `/api/v1/auth`

| Method | Path | Description |
|---|---|---|
| POST | `/register` | Create a new user account |
| POST | `/login` | Authenticate and receive JWT tokens |
| POST | `/refresh` | Exchange refresh token for new tokens |

### Users — `/api/v1/users`

| Method | Path | Description |
|---|---|---|
| GET | `/me` | Get current user profile |
| PUT | `/me` | Update profile |
| DELETE | `/me` | Delete account |

### Garmin — `/api/v1/garmin`

| Method | Path | Description |
|---|---|---|
| GET | `/status` | Check Garmin connection status |
| POST | `/connect` | Initiate Garmin authentication |
| POST | `/mfa` | Submit MFA code |
| POST | `/sync` | Trigger a manual sync |
| DELETE | `/disconnect` | Revoke Garmin connection |

### Health Data — `/api/v1/health`

| Method | Path | Description |
|---|---|---|
| GET | `/metrics` | Fetch metrics for a date range |
| GET | `/daily/{date}` | Single-day snapshot |
| GET | `/summary` | Aggregated stats by period (day / week / month / year) |

---

## Frontend Structure

```
src/
├── app/
│   ├── dashboard/
│   │   ├── page.tsx          # Main dashboard with charts and filters
│   │   ├── layout.tsx        # Auth guard + nav wrapper
│   │   └── settings/
│   │       └── page.tsx      # Garmin connection + theme settings
│   ├── login/page.tsx
│   └── register/page.tsx
├── components/
│   ├── charts/
│   │   ├── activity-chart.tsx
│   │   ├── heart-rate-chart.tsx
│   │   ├── sleep-chart.tsx
│   │   ├── body-battery-chart.tsx
│   │   └── metric-card.tsx
│   ├── layout/
│   │   └── dashboard-nav.tsx  # Sidebar (desktop) + bottom nav (mobile)
│   └── ui/                    # Shared primitives (Button, Card, Input, etc.)
├── lib/
│   ├── api.ts                 # Axios client with JWT interceptors
│   └── use-chart-theme.ts     # Dark/light theme values for Recharts
└── providers/
    ├── index.tsx              # Root provider wrapper
    ├── theme-provider.tsx     # next-themes ThemeProvider
    ├── session-provider.tsx   # NextAuth SessionProvider
    └── query-provider.tsx     # React Query QueryClientProvider
```

---

## Security

- **Passwords** hashed with bcrypt (salted)
- **JWT tokens** signed with HS256, short-lived access tokens
- **Garmin credentials** encrypted at rest with Fernet (AES-128-CBC)
- **User isolation** enforced at every API endpoint via `get_current_user` dependency; InfluxDB queries always filtered by `user_id` tag
- **CORS** configured on the backend to restrict allowed origins

---

## Environment Variables

```env
# PostgreSQL
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=allerac_health
POSTGRES_USER=allerac
POSTGRES_PASSWORD=...

# Redis
REDIS_URL=redis://redis:6379/0

# InfluxDB
INFLUXDB_HOST=influxdb
INFLUXDB_PORT=8086
INFLUXDB_DB=health_metrics
INFLUXDB_USER=allerac
INFLUXDB_PASSWORD=...

# Backend
SECRET_KEY=...
ENCRYPTION_KEY=...
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXTAUTH_URL=http://localhost:3002
NEXTAUTH_SECRET=...
```

---

## Technology Stack

| Layer | Technology | Version |
|---|---|---|
| Frontend | Next.js | 14.1.0 |
| | React | 18.2.0 |
| | Tailwind CSS | 3.4.1 |
| | NextAuth.js | 4.24.5 |
| | Recharts | 2.10.4 |
| | Axios | 1.6.5 |
| | React Query | 5.17.19 |
| Backend | FastAPI | 0.109.0 |
| | Python | 3.11+ |
| | SQLAlchemy (async) | 2.0.25 |
| | Alembic | 1.13.1 |
| Worker | Celery | 5.3.6 |
| | garminconnect | 0.2.38 |
| Databases | PostgreSQL | 16 |
| | InfluxDB | 1.11 |
| | Redis | 7 |
| Security | python-jose | 3.3.0 |
| | bcrypt | 4.1.2 |
| | cryptography (Fernet) | 42.0.1 |
| Infrastructure | Docker Compose | — |
