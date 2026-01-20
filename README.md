# Allerac Health

Multi-user portal for collecting and visualizing health data from Garmin Connect.

## Quick Start

```bash
# 1. Copy environment file
cp .env.example .env

# 2. Edit .env with your settings
# (at least change the passwords!)

# 3. Start all services
docker compose up -d

# 4. Access
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

## Architecture

- **Frontend**: Next.js 14 with App Router
- **Backend**: FastAPI (Python)
- **Worker**: Celery for background jobs
- **Database**: PostgreSQL (users, configs)
- **Cache/Queue**: Redis
- **Time Series**: InfluxDB (health metrics)

## Structure

```
allerac-health/
├── frontend/          # Next.js app
├── backend/           # FastAPI API
├── worker/            # Celery worker
├── scripts/           # Initialization scripts
├── docker-compose.yml
└── PLANNING.md        # Development plan document
```

## Development

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Worker

```bash
cd worker
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
celery -A app.celery_app worker --loglevel=info
```

## Roadmap

See [PLANNING.md](PLANNING.md) for the complete development plan.

## License

MIT
