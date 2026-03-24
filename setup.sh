#!/usr/bin/env bash
# =============================================================
#  FinParse - Complete Setup Script
#  Run once on a fresh Ubuntu/Debian machine.
#  Usage: bash setup.sh
# =============================================================
set -e
RED='\033[0;31m'; GREEN='\033[0;32m'; AMBER='\033[0;33m'; BLUE='\033[0;34m'; NC='\033[0m'
BOLD='\033[1m'

info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC}   $1"; }
warn()    { echo -e "${AMBER}[WARN]${NC} $1"; }
error()   { echo -e "${RED}[ERR]${NC}  $1"; exit 1; }
step()    { echo -e "\n${BOLD}━━━  $1  ━━━${NC}"; }

# ── Detect network IP ─────────────────────────────────────────────────────────
step "Detecting network IP"
# Try multiple methods to find the right LAN IP
HOST_IP=$(ip route get 8.8.8.8 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src") print $(i+1)}' | head -1)
if [ -z "$HOST_IP" ]; then
  HOST_IP=$(hostname -I | awk '{print $1}')
fi
if [ -z "$HOST_IP" ]; then
  warn "Could not detect IP automatically."
  read -rp "Enter your machine's LAN IP address: " HOST_IP
fi
success "Using IP: ${BOLD}$HOST_IP${NC}"

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
info "Project root: $PROJECT_DIR"

# # ── 1. System packages ────────────────────────────────────────────────────────
# step "Installing system packages"
# sudo apt-get update -qq
# sudo apt-get install -y -qq \
#   python3 python3-pip python3-venv \
#   openjdk-21-jdk maven \
#   nodejs \
#   postgresql postgresql-contrib \
#   ghostscript \
#   curl wget unzip

# success "System packages installed"

# # ── 2. Node / Angular CLI ─────────────────────────────────────────────────────
# step "Installing Angular CLI"
# sudo npm install -g @angular/cli@17
# success "Angular CLI installed: $(ng version 2>/dev/null | head -1)"

# # ── 3. PostgreSQL ─────────────────────────────────────────────────────────────
# step "Setting up PostgreSQL"
# sudo systemctl start postgresql
# sudo systemctl enable postgresql

# # Run setup SQL
# sudo -u postgres psql -f "$PROJECT_DIR/setup_db.sql" 2>/dev/null || \
#   warn "DB may already exist - continuing"

# success "PostgreSQL ready  (db=bankparser  user=bankparser)"

# # ── 4. Python virtual environment ─────────────────────────────────────────────
step "Setting up Python environment"
PYDIR="$PROJECT_DIR/python-service"
# python3 -m venv "$PYDIR/venv"
# "$PYDIR/venv/bin/pip" install --quiet --upgrade pip
# "$PYDIR/venv/bin/pip" install --quiet -r "$PYDIR/requirements.txt"
success "Python venv ready"

# ── 5. Patch IP into all config files ─────────────────────────────────────────
step "Patching IP address: $HOST_IP"

# Angular environment
for ENV_FILE in \
  "$PROJECT_DIR/frontend/src/environments/environment.ts" \
  "$PROJECT_DIR/frontend/src/environments/environment.prod.ts"; do
  cat > "$ENV_FILE" << ENVEOF
export const environment = {
  production: false,
  apiUrl: 'http://${HOST_IP}:8080'
};
ENVEOF
done
success "Angular env patched"

# Spring Boot application.properties
PROPS="$PROJECT_DIR/backend/src/main/resources/application.properties"
sed -i "s|cors.allowed.origins=.*|cors.allowed.origins=http://${HOST_IP}:4200,http://localhost:4200|g" "$PROPS"
success "Spring Boot CORS patched"

# ── 6. Build Spring Boot backend ──────────────────────────────────────────────
step "Building Spring Boot backend"
cd "$PROJECT_DIR/backend"
mvn clean package -q -DskipTests
success "Backend JAR built: $(ls target/*.jar)"

# ── 7. Build Angular frontend ─────────────────────────────────────────────────
step "Building Angular frontend"
cd "$PROJECT_DIR/frontend"
npm install
ng build --configuration=production
success "Frontend built → dist/frontend"

# ── 8. Create systemd service files ──────────────────────────────────────────
step "Creating systemd services"
CURRENT_USER=$(whoami)

# Python service
sudo tee /etc/systemd/system/finparse-python.service > /dev/null << SVCEOF
[Unit]
Description=FinParse Python Parser Service
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$PYDIR
ExecStart=$PYDIR/venv/bin/python app.py
Restart=on-failure
RestartSec=5
Environment=PORT=5050

[Install]
WantedBy=multi-user.target
SVCEOF

# Spring Boot service
JARFILE=$(ls "$PROJECT_DIR/backend/target/"*.jar | head -1)
sudo tee /etc/systemd/system/finparse-backend.service > /dev/null << SVCEOF
[Unit]
Description=FinParse Spring Boot Backend
After=network.target postgresql.service finparse-python.service

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$PROJECT_DIR/backend
ExecStart=/usr/bin/java -jar $JARFILE
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
SVCEOF

sudo systemctl daemon-reload
success "Systemd services created"

# ── 9. Start everything ───────────────────────────────────────────────────────
step "Starting all services"
sudo systemctl enable --now finparse-python
sudo systemctl enable --now finparse-backend

sleep 3
# Quick health check
PYTHON_OK=$(curl -sf http://localhost:5050/health | grep -c "ok" || echo 0)
SPRING_OK=$(curl -sf http://localhost:8080/api/statements | grep -c "\[" || echo 0)

if [ "$PYTHON_OK" -gt 0 ]; then success "Python parser  → http://localhost:5050"; else warn "Python parser may still be starting"; fi
if [ "$SPRING_OK" -gt 0 ]; then success "Spring Boot    → http://localhost:8080"; else warn "Spring Boot may still be starting"; fi

# ── 10. Angular dev server (foreground) ───────────────────────────────────────
step "Summary"
echo ""
echo -e "  ${GREEN}${BOLD}Setup complete!${NC}"
echo ""
echo -e "  ${BOLD}Services running:${NC}"
echo -e "    Parser API  → http://${HOST_IP}:5050"
echo -e "    Backend API → http://${HOST_IP}:8080"
echo ""
echo -e "  ${BOLD}To start the Angular frontend:${NC}"
echo -e "    cd $PROJECT_DIR/frontend"
echo -e "    ng serve --host 0.0.0.0 --port 4200"
echo ""
echo -e "  ${BOLD}Then open in browser:${NC}"
echo -e "    ${BLUE}http://${HOST_IP}:4200${NC}"
echo ""
echo -e "  ${BOLD}Or serve the production build:${NC}"
echo -e "    npx serve -s dist/frontend/browser -l 4200"
echo ""
