# Allerac Health - Development Plan

## Overview

Multi-user portal for collecting and visualizing health data from Garmin Connect.
Each user can connect their Garmin account and view their data in personalized dashboards.

---

## Progress Tracking

### Phase 1: Foundation (MVP)
- [x] Setup Docker Compose with all services
- [x] Backend: basic FastAPI structure
- [x] Backend: User models and JWT authentication
- [x] Backend: PostgreSQL connection + schema (init-db.sql)
- [x] Frontend: Next.js setup with Tailwind CSS
- [x] Frontend: Landing page created
- [x] Frontend: login/register pages
- [x] Frontend: NextAuth.js integration

### Phase 2: Garmin Integration
- [x] Backend: GarminCredentials model (encrypted)
- [x] Backend: endpoints to connect Garmin
- [x] Backend: Garmin authentication service
- [x] Frontend: Garmin configuration page
- [x] Frontend: MFA input flow
- [x] Worker: basic Celery setup
- [x] Worker: initial fetch task

### Phase 3: Data Collection
- [x] Worker: garminconnect library integration
- [x] Worker: fetch all metrics
- [x] Worker: InfluxDB persistence with user_id
- [x] Backend: endpoints to query data
- [x] Backend: aggregations and filters

### Phase 4: Visualization
- [x] Frontend: main dashboard
- [x] Frontend: metric charts (recharts)
- [x] Frontend: date filters
- [ ] Frontend: temporal comparisons

### Phase 5: Polish
- [ ] Rate limiting and throttling
- [ ] Robust retry logic
- [ ] Notifications (email when sync fails)
- [ ] Logs and monitoring
- [ ] Automated tests

---

## Architecture

```
                                    [User]
                                        |
                                        v
+-----------------------------------------------------------------------------------+
|                              FRONTEND (Next.js)                                   |
|  - Landing page                                                                   |
|  - Authentication (NextAuth.js)                                                   |
|  - Health data dashboard                                                          |
|  - Garmin account configuration                                                   |
|  - MFA input page                                                                 |
+-----------------------------------------------------------------------------------+
                                        |
                                        v
+-----------------------------------------------------------------------------------+
|                              BACKEND API (FastAPI)                                |
|  - REST API                                                                       |
|  - JWT Authentication                                                             |
|  - User management                                                                |
|  - Garmin credentials management                                                  |
|  - Health data endpoints                                                          |
+-----------------------------------------------------------------------------------+
                |                       |                       |
                v                       v                       v
+-------------------+       +-------------------+       +-------------------+
|     PostgreSQL    |       |       Redis       |       |     InfluxDB      |
|                   |       |                   |       |                   |
| - Users           |       | - Session cache   |       | - Health metrics  |
| - Garmin tokens   |       | - Job queue       |       | - Tags: user_id   |
| - Settings        |       | - Rate limiting   |       |                   |
+-------------------+       +-------------------+       +-------------------+
                                        |
                                        v
+-----------------------------------------------------------------------------------+
|                              WORKER (Python/Celery)                               |
|  - Fetch Garmin data per user                                                     |
|  - Process job queue                                                              |
|  - Retry with exponential backoff                                                 |
|  - Respect Garmin rate limits                                                     |
+-----------------------------------------------------------------------------------+
```

---

## Technology Stack

| Component | Technology | Justification |
|-----------|------------|---------------|
| Frontend | Next.js 14 (App Router) | SSR, React Server Components, excellent DX |
| Auth Frontend | NextAuth.js | Ready OAuth, secure sessions |
| UI Components | shadcn/ui + Tailwind | Beautiful and customizable components |
| Backend API | FastAPI (Python) | Async, fast, typed, automatic OpenAPI |
| Auth Backend | JWT + OAuth2 | Stateless, scalable |
| Database | PostgreSQL | Robust, JSONB for flexibility |
| Cache/Queue | Redis | Fast, pub/sub, queues |
| Time Series DB | InfluxDB 1.x | Optimized for temporal metrics |
| Worker | Celery + Redis | Distributed jobs, retry, scheduling |
| Containers | Docker Compose | Simplicity for dev/MVP |

---

## Folder Structure

```
allerac-health/
├── docker-compose.yml
├── .env.example
├── PLANNING.md
│
├── frontend/                    # Next.js App
│   ├── Dockerfile
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.js
│   ├── src/
│   │   ├── app/                 # App Router
│   │   │   ├── page.tsx         # Landing
│   │   │   ├── layout.tsx
│   │   │   ├── (auth)/
│   │   │   │   ├── login/
│   │   │   │   └── register/
│   │   │   ├── dashboard/
│   │   │   │   ├── page.tsx
│   │   │   │   └── settings/
│   │   │   └── api/
│   │   │       └── auth/
│   │   ├── components/
│   │   │   ├── ui/              # shadcn components
│   │   │   ├── charts/
│   │   │   └── layout/
│   │   └── lib/
│   │       ├── api.ts           # API client
│   │       └── auth.ts
│   └── public/
│
├── backend/                     # FastAPI
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic/                 # DB migrations
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── models/
│   │   │   ├── user.py
│   │   │   └── garmin.py
│   │   ├── schemas/
│   │   │   ├── user.py
│   │   │   └── health.py
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── auth.py
│   │   │   │   ├── users.py
│   │   │   │   ├── garmin.py
│   │   │   │   └── health.py
│   │   │   └── deps.py
│   │   ├── services/
│   │   │   ├── garmin.py
│   │   │   └── influxdb.py
│   │   └── core/
│   │       ├── security.py
│   │       └── database.py
│   └── tests/
│
├── worker/                      # Celery Worker
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── celery_app.py
│       ├── tasks/
│       │   ├── garmin_fetch.py
│       │   └── cleanup.py
│       └── services/
│           └── garmin.py
│
└── scripts/
    ├── init-db.sql
    └── seed-data.py
```

---

## Data Model

### PostgreSQL

```sql
-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),  -- NULL if OAuth
    name VARCHAR(255),
    avatar_url TEXT,
    oauth_provider VARCHAR(50),  -- 'google', 'github', NULL
    oauth_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Garmin Credentials (encrypted)
CREATE TABLE garmin_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    email_encrypted BYTEA NOT NULL,
    oauth1_token_encrypted BYTEA,  -- Garmin OAuth1 token
    oauth2_token_encrypted BYTEA,  -- Garmin OAuth2 token
    is_connected BOOLEAN DEFAULT FALSE,
    last_sync_at TIMESTAMP,
    last_error TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id)
);

-- Sync Jobs (history)
CREATE TABLE sync_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL,  -- 'pending', 'running', 'completed', 'failed'
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    records_fetched INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### InfluxDB

All metrics include `user_id` tag for isolation:

```
# Example measurements
daily_stats,user_id=abc123 steps=10000,calories=2500,distance=8.5 1704067200000000000
heart_rate,user_id=abc123 resting=58,max=180,avg=72 1704067200000000000
sleep,user_id=abc123 duration=28800,deep=7200,light=14400,rem=7200 1704067200000000000
stress,user_id=abc123 avg=35,max=75,rest=120 1704067200000000000
hrv,user_id=abc123 weekly_avg=45,last_night=52 1704067200000000000
```

---

## Garmin Authentication Flow

```
1. User clicks "Connect Garmin"
         |
         v
2. Frontend opens config modal/page
         |
         v
3. User enters Garmin email and password
         |
         v
4. Backend tries to authenticate via garminconnect
         |
         +---> Success: Save tokens, mark as connected
         |
         +---> MFA Required:
                    |
                    v
               5. Backend returns status "mfa_required"
                    |
                    v
               6. Frontend shows MFA code input
                    |
                    v
               7. User receives code via email/SMS
                    |
                    v
               8. User enters code in frontend
                    |
                    v
               9. Backend completes authentication
                    |
                    v
               10. Tokens saved, sync starts
```

---

## Environment Variables

```env
# Database
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=allerac_health
POSTGRES_USER=allerac
POSTGRES_PASSWORD=secure_password

# Redis
REDIS_URL=redis://redis:6379/0

# InfluxDB
INFLUXDB_HOST=influxdb
INFLUXDB_PORT=8086
INFLUXDB_DB=health_metrics
INFLUXDB_USER=allerac
INFLUXDB_PASSWORD=secure_password

# Backend
SECRET_KEY=your-super-secret-key-change-in-production
ENCRYPTION_KEY=32-byte-key-for-credential-encryption
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your-nextauth-secret

# OAuth (optional)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
```

---

## Next Steps

To continue development in a new session:

1. **Frontend**: Create login and register pages
2. **Frontend**: Implement NextAuth.js
3. **Frontend**: Create Garmin connection page with MFA flow
4. **Frontend**: Build dashboard with charts
5. **Testing**: Add unit and integration tests

---

## Important Notes

- **Security**: Garmin credentials are ALWAYS encrypted in the database
- **Rate Limiting**: Garmin has limits - respect them to avoid bans
- **Tokens**: Garmin OAuth tokens expire - implement refresh
- **Backups**: Health data is sensitive - regular backups needed
- **LGPD/GDPR**: Allow data export and deletion
