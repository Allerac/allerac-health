#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────
#  Allerac Health — Installation Script
# ─────────────────────────────────────────────

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

echo ""
echo -e "${BLUE}╔══════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       Allerac Health  Installer      ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════╝${NC}"
echo ""

# ─── Prerequisites ────────────────────────────
info "Checking prerequisites..."

command -v docker  >/dev/null 2>&1 || error "Docker is not installed. Visit https://docs.docker.com/get-docker/"
command -v openssl >/dev/null 2>&1 || error "openssl is required but not found."

# Docker Compose (v2 plugin or standalone)
if docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_CMD="docker-compose"
else
  error "Docker Compose not found. Install it with: sudo apt install docker-compose-plugin"
fi

success "Docker found: $(docker --version)"
success "Docker Compose found: $($COMPOSE_CMD version --short 2>/dev/null || echo 'v1')"

# ─── Port conflict check ───────────────────────
info "Checking for port conflicts..."

PORTS_NEEDED=(8000 3002 8086)
CONFLICT=0
for port in "${PORTS_NEEDED[@]}"; do
  if ss -tlnp 2>/dev/null | grep -q ":${port} " || \
     netstat -tlnp 2>/dev/null | grep -q ":${port} "; then
    warn "Port ${port} is already in use."
    CONFLICT=1
  fi
done

# Ports that are internal (redis, postgres) — just informational
for port in 5432 6379; do
  if ss -tlnp 2>/dev/null | grep -q ":${port} " || \
     netstat -tlnp 2>/dev/null | grep -q ":${port} "; then
    warn "Port ${port} is in use on host (OK — allerac-health uses it internally only)."
  fi
done

if [ "$CONFLICT" -eq 1 ]; then
  echo ""
  warn "One or more required ports are in use. Please free them before continuing."
  echo "  Port 8000  → Backend API"
  echo "  Port 3002  → Frontend"
  echo "  Port 8086  → InfluxDB (optional external access)"
  echo ""
  read -r -p "Continue anyway? [y/N] " response
  [[ "$response" =~ ^[Yy]$ ]] || exit 1
fi

# ─── Shared Docker network (allerac-one integration) ──
info "Ensuring shared Docker network 'allerac' exists..."
if ! docker network inspect allerac >/dev/null 2>&1; then
  docker network create allerac
  success "Created Docker network 'allerac'."
else
  success "Docker network 'allerac' already exists."
fi

# ─── Environment file ─────────────────────────
if [ -f .env ]; then
  warn ".env already exists — skipping generation."
else
  info "Generating .env from .env.example..."
  cp .env.example .env

  SECRET_KEY=$(openssl rand -hex 32)
  ENCRYPTION_KEY=$(openssl rand -hex 32)
  NEXTAUTH_SECRET=$(openssl rand -hex 32)
  DB_PASSWORD=$(openssl rand -hex 16)
  INFLUX_PASSWORD=$(openssl rand -hex 16)

  # Cross-platform sed (macOS uses '' after -i, Linux does not)
  SED_INPLACE="sed -i"
  if [[ "$(uname)" == "Darwin" ]]; then
    SED_INPLACE="sed -i ''"
  fi

  $SED_INPLACE "s|your_secure_password_here|${DB_PASSWORD}|g"     .env
  $SED_INPLACE "s|your-super-secret-key-minimum-32-characters|${SECRET_KEY}|" .env
  $SED_INPLACE "s|32-byte-key-for-encrypting-garmin-creds|${ENCRYPTION_KEY}|" .env
  $SED_INPLACE "s|your-nextauth-secret-key|${NEXTAUTH_SECRET}|"   .env

  success ".env generated with random secrets."
fi

# ─── Build & start ────────────────────────────
info "Building Docker images (this may take a few minutes on first run)..."
$COMPOSE_CMD build

info "Starting services..."
$COMPOSE_CMD up -d

# ─── Wait for backend ─────────────────────────
info "Waiting for backend to be ready..."
RETRIES=30
until curl -sf http://localhost:8000/health >/dev/null 2>&1 || [ "$RETRIES" -eq 0 ]; do
  sleep 2
  RETRIES=$((RETRIES - 1))
done

if [ "$RETRIES" -eq 0 ]; then
  warn "Backend did not respond in time. Check logs with: docker logs allerac-health-backend"
else
  success "Backend is up."
fi

# ─── Done ─────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════╗${NC}"
echo -e "${GREEN}║         Installation complete!       ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════╝${NC}"
echo ""
echo "  Frontend  →  http://localhost:3002"
echo "  API       →  http://localhost:8000"
echo "  API docs  →  http://localhost:8000/docs"
echo ""
echo "  Useful commands:"
echo "    docker compose logs -f              # Follow all logs"
echo "    docker compose logs -f backend      # Backend logs only"
echo "    docker compose logs -f worker       # Worker logs only"
echo "    docker compose down                 # Stop all services"
echo "    docker compose down -v              # Stop and delete all data"
echo ""
echo "  allerac-one integration:"
echo "    Both projects share the 'allerac' Docker network."
echo "    allerac-health backend is reachable at http://allerac-health-backend:8000"
echo "    from any container in the allerac-one stack."
echo ""
echo "  Cloudflare Tunnel (health.allerac.ai):"
echo "    1. Create a tunnel at https://one.dash.cloudflare.com → Networks → Tunnels"
echo "    2. Add HEALTH_TUNNEL_TOKEN=<token> to your .env"
echo "    3. Configure public hostnames in Cloudflare dashboard:"
echo "         health.allerac.ai     → http://localhost:3002"
echo "         health-api.allerac.ai → http://localhost:8000  (optional)"
echo "    4. Start tunnel:  docker compose --profile tunnel up -d tunnel"
echo ""
