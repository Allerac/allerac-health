# allerac-one Integration

This document explains how allerac-one can call the allerac-health API on behalf of its users.

## How it works

allerac-health accepts two types of Bearer tokens:

1. **Local tokens** — issued by allerac-health itself (standalone mode)
2. **allerac-one tokens** — issued by allerac-one, verified with a shared secret key

When a valid allerac-one token arrives, allerac-health automatically creates a local user account linked to that allerac-one user (identified by email). This happens transparently on the first request — no manual registration required.

## Setup

### 1. allerac-health `.env`

```env
# Must match SECRET_KEY in your allerac-one instance
ALLERAC_ONE_SECRET_KEY=<copy the SECRET_KEY value from allerac-one .env>
```

### 2. allerac-one — generating health API tokens

allerac-one must generate a short-lived JWT before calling the health API.
The token **must** include these fields:

| Field | Value | Required |
|-------|-------|----------|
| `iss` | `"allerac-one"` | Yes — identifies the token source |
| `sub` | allerac-one user UUID | Yes |
| `email` | user email | Yes — used to match/create the health user |
| `name` | user display name | No — used when creating the account |
| `type` | `"access"` | No — ignored for allerac-one tokens |
| `exp` | expiration timestamp | Yes — keep short (5–15 minutes) |

**Example (TypeScript / jose library):**

```typescript
import { SignJWT } from 'jose'

const secret = new TextEncoder().encode(process.env.SECRET_KEY)

export async function createHealthToken(user: { id: string; email: string; name: string }) {
  return new SignJWT({
    iss: 'allerac-one',
    sub: user.id,
    email: user.email,
    name: user.name,
  })
    .setProtectedHeader({ alg: 'HS256' })
    .setExpirationTime('10m')
    .sign(secret)
}
```

**Example API call from allerac-one:**

```typescript
const token = await createHealthToken(session.user)

const response = await fetch('http://allerac-health-backend:8000/api/v1/health/summary?period=week', {
  headers: { Authorization: `Bearer ${token}` },
})
const data = await response.json()
```

> The URL `http://allerac-health-backend:8000` works because both services
> share the `allerac` Docker network.

## Auto-provisioning

On the first request from an allerac-one user, allerac-health creates a local user:

```
email        → copied from token
name         → copied from token (or derived from email)
oauth_provider → "allerac-one"
oauth_id     → sub from token (allerac-one user UUID)
password_hash → null (cannot log in via allerac-health login form)
is_active    → true
is_verified  → true
```

Subsequent requests from the same user are matched by email — no additional setup needed.

## Health Skill — suggested tool calls

These are the endpoints allerac-one should expose as tool calls for the Health Skill:

| Tool | Method | Endpoint | Description |
|------|--------|----------|-------------|
| `get_health_summary` | GET | `/api/v1/health/summary?period={period}` | Avg steps, calories, HR, sleep for a period |
| `get_daily_metrics` | GET | `/api/v1/health/metrics?start_date=&end_date=` | Full metrics for a date range |
| `get_daily_snapshot` | GET | `/api/v1/health/daily/{date}` | All metrics for a single day |
| `get_garmin_status` | GET | `/api/v1/garmin/status` | Whether the user has Garmin connected |

### Example skill prompt context

```
The user has a Garmin device connected. You have access to their health data
through the following tools: get_health_summary, get_daily_metrics, get_daily_snapshot.

Use these tools when the user asks about:
- Sleep quality, duration, or stages (deep/REM/light)
- Steps, activity, or calories burned
- Heart rate (resting, average, max)
- Body battery levels and recovery
- Training readiness or VO2 max planning
- Weekly or monthly health trends
```
