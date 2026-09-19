#!/usr/bin/env bash
# ==============================================================================
# Deploy Senior Caregiver Termux Hub to Samsung S7 Edge / Termux
# ==============================================================================
# Usage:
#   ./deploy.sh [HOST_IP] [PORT] [USER]
#
# Default:
#   ./deploy.sh 10.81.8.161 8022 root
# ==============================================================================

set -e

# Default Target Configuration
TARGET_IP="${1:-10.81.8.161}"
TARGET_PORT="${2:-8022}"
TARGET_USER="${3:-root}"
TARGET_ALIAS="termux-s7"
REMOTE_DIR="~/eldercare-hub"

# Color formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

info "======================================================================"
info " Deploying Senior Caregiver Termux Hub to ${TARGET_USER}@${TARGET_IP}:${TARGET_PORT}"
info "======================================================================"

# 1. Test SSH Connection
info "Testing SSH connection to target device..."
if ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=5 -p "${TARGET_PORT}" "${TARGET_USER}@${TARGET_IP}" "echo SSH_CONNECTED" &>/dev/null; then
    success "SSH connection established successfully!"
else
    warn "Direct SSH test failed. Checking SSH alias '${TARGET_ALIAS}'..."
    if ssh -o BatchMode=yes -o ConnectTimeout=5 "${TARGET_ALIAS}" "echo SSH_CONNECTED" &>/dev/null; then
        success "SSH connection via alias '${TARGET_ALIAS}' established!"
        SSH_CMD="ssh ${TARGET_ALIAS}"
        SCP_CMD="scp -P ${TARGET_PORT}"
    else
        error "Could not connect to ${TARGET_USER}@${TARGET_IP}:${TARGET_PORT}. Please run setup-ssh-auto-login.sh first."
    fi
fi

SSH_TARGET="-o StrictHostKeyChecking=accept-new -p ${TARGET_PORT} ${TARGET_USER}@${TARGET_IP}"
SSH_BASE="ssh ${SSH_TARGET}"
SCP_BASE="scp -o StrictHostKeyChecking=accept-new -P ${TARGET_PORT}"

# 2. Create Remote Target Directory
info "Creating remote installation directory: ${REMOTE_DIR}..."
${SSH_BASE} "mkdir -p ${REMOTE_DIR} ~/.termux/boot ~/.config/eldercare"

# 3. Copy Application Files via SCP
info "Transferring application files..."
${SCP_BASE} "${SCRIPT_DIR}/app.py" \
           "${SCRIPT_DIR}/senior_caregiver_termux_hub.html" \
           "${SCRIPT_DIR}/requirements.txt" \
           "${SCRIPT_DIR}/manage-service.sh" \
           "${SCRIPT_DIR}/check-prerequisites.sh" \
           "${SCRIPT_DIR}/README.md" \
           "${TARGET_USER}@${TARGET_IP}:${REMOTE_DIR}/"

success "Files transferred successfully."

# 4. Remote Dependency Setup & Service Configuration
info "Configuring Termux environment and installing Python packages remotely..."
${SSH_BASE} bash -c "'
    set -e
    echo \"---> Installing required Termux packages...\"
    pkg update -y && pkg install python termux-api termux-tools termux-services openssl-tool -y

    echo \"---> Creating Python virtual environment...\"
    cd ${REMOTE_DIR}
    if [ ! -d \"venv\" ]; then
        python3 -m venv venv
    fi

    echo \"---> Installing Python dependencies inside venv...\"
    ./venv/bin/pip install --upgrade pip
    ./venv/bin/pip install -r requirements.txt

    echo \"---> Setting executable permissions...\"
    chmod +x manage-service.sh check-prerequisites.sh

    echo \"---> Configuring Termux:Boot autostart script...\"
    BOOT_SCRIPT=\"\$HOME/.termux/boot/start-eldercare-hub\"
    cat << \"EOF_BOOT\" > \"\$BOOT_SCRIPT\"
#!/data/data/com.termux/files/usr/bin/bash
# Senior Caregiver Termux Hub Autostart Script
termux-wake-lock
mkdir -p \$HOME/.config/eldercare
cd \$HOME/eldercare-hub
if [ -d \"venv\" ]; then
    source venv/bin/activate
fi
export PORT=8888
export HTTPS_PORT=8443
export HOST=0.0.0.0
python3 app.py >> \$HOME/.config/eldercare/app.log 2>&1 &
EOF_BOOT
    chmod +x \"\$BOOT_SCRIPT\"
    echo \"---> Termux:Boot script configured at \$BOOT_SCRIPT\"
'"

# 5. Start / Restart Service via O&M Script
info "Starting Senior Caregiver Termux Hub service..."
${SSH_BASE} "cd ${REMOTE_DIR} && ./manage-service.sh restart"

# 6. Verify Deployment Response
info "Verifying service availability on HTTP (8888) and HTTPS (8443)..."
sleep 3
if curl -s --max-time 5 "http://${TARGET_IP}:8888/api/status" | grep -q "timestamp"; then
    success "HTTP (8888) endpoint responding normally."
else
    warn "HTTP (8888) endpoint check timed out."
fi

if curl -k -s --max-time 5 "https://${TARGET_IP}:8443/api/status" | grep -q "timestamp"; then
    success "HTTPS (8443) endpoint responding normally."
else
    warn "HTTPS (8443) endpoint check timed out."
fi

echo ""
echo -e "${GREEN}======================================================================${NC}"
echo -e "${GREEN} ElderCare Termux Hub Deployed Successfully!${NC}"
echo -e "${GREEN}======================================================================${NC}"
echo -e " Caregiver Dashboard (HTTP) : ${YELLOW}http://${TARGET_IP}:8888/${NC}"
echo -e " Caregiver Dashboard (HTTPS): ${YELLOW}https://${TARGET_IP}:8443/${NC}"
echo -e " REST API Status Endpoint   : ${YELLOW}http://${TARGET_IP}:8888/api/status${NC}"
echo -e " O&M Remote Control         : ${YELLOW}ssh ${TARGET_ALIAS} '~/eldercare-hub/manage-service.sh status'${NC}"
echo -e "${GREEN}======================================================================${NC}"
