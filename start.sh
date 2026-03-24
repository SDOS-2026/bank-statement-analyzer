#!/usr/bin/env bash
# FinParse - Start all services
# Usage: bash start.sh [your-ip]
# If IP not provided, auto-detects

set -e
GREEN='\033[0;32m'; BLUE='\033[0;34m'; NC='\033[0m'; BOLD='\033[1m'

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Detect IP
HOST_IP="${1:-$(ip route get 8.8.8.8 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src") print $(i+1)}' | head -1)}"
[ -z "$HOST_IP" ] && HOST_IP=$(hostname -I | awk '{print $1}')

echo -e "\n${BOLD}FinParse — Starting services${NC}"
echo -e "IP: ${BLUE}$HOST_IP${NC}\n"

# ── 1. Python parser ──────────────────────────────────────────────────────────
echo -e "${GREEN}[1/3]${NC} Starting Python parser (port 5050)…"
pkill -f "python.*app.py" 2>/dev/null || true
cd "$PROJECT_DIR/python-service"
nohup ./venv/bin/python app.py > /tmp/finparse-python.log 2>&1 &
PYTHON_PID=$!
echo "      PID $PYTHON_PID  →  tail -f /tmp/finparse-python.log"

# ── 2. Spring Boot ───────────────────────────────────────────────────────────
echo -e "${GREEN}[2/3]${NC} Starting Spring Boot backend (port 8080)…"
pkill -f "bank-parser-backend" 2>/dev/null || true
JAR=$(ls "$PROJECT_DIR/backend/target/"*.jar 2>/dev/null | head -1)
if [ -z "$JAR" ]; then
  echo "      JAR not found — building first…"
  cd "$PROJECT_DIR/backend" && mvn clean package -q -DskipTests
  JAR=$(ls "$PROJECT_DIR/backend/target/"*.jar | head -1)
fi
nohup java -jar "$JAR" > /tmp/finparse-backend.log 2>&1 &
BACKEND_PID=$!
echo "      PID $BACKEND_PID  →  tail -f /tmp/finparse-backend.log"

# ── 3. Angular ───────────────────────────────────────────────────────────────
echo -e "${GREEN}[3/3]${NC} Starting Angular dev server (port 4200)…"
# Patch IP in env file
cat > "$PROJECT_DIR/frontend/src/environments/environment.ts" << ENVEOF
export const environment = {
  production: false,
  apiUrl: 'http://${HOST_IP}:8080'
};
ENVEOF

cd "$PROJECT_DIR/frontend"
pkill -f "ng serve" 2>/dev/null || true
nohup ng serve --host 0.0.0.0 --port 4200 > /tmp/finparse-angular.log 2>&1 &
ANGULAR_PID=$!
echo "      PID $ANGULAR_PID  →  tail -f /tmp/finparse-angular.log"

# ── Wait & Health check ───────────────────────────────────────────────────────
echo -e "\nWaiting for services to start…"
sleep 8

PYTHON_UP=$(curl -sf http://localhost:5050/health 2>/dev/null | grep -c ok || true)
SPRING_UP=$(curl -sf http://localhost:8080/api/statements 2>/dev/null | grep -c "\[" || true)

echo ""
echo -e "  Python parser  : $([ "$PYTHON_UP" -gt 0 ] && echo "${GREEN}UP${NC}" || echo "starting…")"
echo -e "  Spring Boot    : $([ "$SPRING_UP" -gt 0 ] && echo "${GREEN}UP${NC}" || echo "starting (takes ~20s)…")"
echo -e "  Angular        : compiling (takes ~30s)…"
echo ""
echo -e "  ${BOLD}Open in browser → ${BLUE}http://${HOST_IP}:4200${NC}"
echo ""
echo -e "  Logs:"
echo -e "    tail -f /tmp/finparse-python.log"
echo -e "    tail -f /tmp/finparse-backend.log"
echo -e "    tail -f /tmp/finparse-angular.log"
echo ""
echo -e "  Stop all:  bash stop.sh"
echo ""
