#!/usr/bin/env bash
# ==============================================================================
# Operations & Maintenance (O&M) Script for Senior Caregiver Termux Hub
# ==============================================================================
# Usage:
#   ./manage-service.sh [COMMAND] [OPTIONS]
#
# Commands:
#   status     Check service process, listening port, and API health
#   start      Start the Senior Caregiver Termux Hub backend
#   stop       Stop the backend service
#   restart    Restart the service
#   enable     Enable autostart on Android reboot (Termux:Boot)
#   disable    Disable autostart on Android reboot
#   logs       Tail live server execution logs
#
# Options:
#   -r, --remote HOST_OR_ALIAS   Execute command on remote device over SSH
# ==============================================================================

set -e

# Default Local Directories & Files
HUB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$HOME/.config/eldercare"
LOG_FILE="$LOG_DIR/app.log"
BOOT_SCRIPT="$HOME/.termux/boot/start-eldercare-hub"
PORT=8888
HTTPS_PORT=8443

# Color Constants
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

show_help() {
    cat << EOF
Usage: $(basename "$0") COMMAND [OPTIONS]

Operations & Maintenance (O&M) Tool for ElderCare Termux Hub

Commands:
  status       Check process, port 8080, and HTTP endpoint status
  start        Start the backend server
  stop         Stop the backend server
  restart      Restart the backend server
  enable       Enable autostart on Android phone reboot
  disable      Disable autostart on Android phone reboot
  logs         Tail live server log stream

Options:
  -r, --remote TARGET   Execute command on remote host/alias over SSH (e.g. -r termux-s7)
  -h, --help            Show this help menu
EOF
}

# Remote Execution Wrapper
REMOTE_TARGET=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        -r|--remote)
            REMOTE_TARGET="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        status|start|stop|restart|enable|disable|logs)
            COMMAND="$1"
            shift
            ;;
        *)
            error "Unknown command or option: $1. Use --help for usage."
            ;;
    esac
done

if [[ -z "$COMMAND" ]]; then
    show_help
    exit 1
fi

# Delegate to SSH if --remote specified
if [[ -n "$REMOTE_TARGET" ]]; then
    info "Executing '${COMMAND}' on remote target '${REMOTE_TARGET}'..."
    exec ssh "$REMOTE_TARGET" "~/eldercare-hub/manage-service.sh ${COMMAND}"
fi

# ==============================================================================
# Local Service O&M Actions
# ==============================================================================

get_pid() {
    pgrep -f "python3.*app.py" || true
}

check_status() {
    info "======================================================================"
    info " ElderCare Termux Hub - Service Status Check"
    info "======================================================================"

    PID=$(get_pid)
    if [[ -n "$PID" ]]; then
        success "Backend Process : RUNNING (PID: ${PID})"
    else
        warn "Backend Process : STOPPED"
    fi

    # Port Check
    if command -v netstat &>/dev/null; then
        PORT_LISTENING=$(netstat -tuln 2>/dev/null | grep ":${PORT} " || true)
        HTTPS_LISTENING=$(netstat -tuln 2>/dev/null | grep ":${HTTPS_PORT} " || true)
    else
        PORT_LISTENING=$(ss -tuln 2>/dev/null | grep ":${PORT} " || true)
        HTTPS_LISTENING=$(ss -tuln 2>/dev/null | grep ":${HTTPS_PORT} " || true)
    fi

    if [[ -n "$PORT_LISTENING" ]]; then
        success "HTTP Port ${PORT} Status  : LISTENING"
    else
        warn "HTTP Port ${PORT} Status  : NOT LISTENING"
    fi

    if [[ -n "$HTTPS_LISTENING" ]]; then
        success "HTTPS Port ${HTTPS_PORT} Status : LISTENING"
    else
        warn "HTTPS Port ${HTTPS_PORT} Status : NOT LISTENING"
    fi

    # Autostart Check
    if [[ -x "$BOOT_SCRIPT" ]]; then
        success "Autostart Boot  : ENABLED (${BOOT_SCRIPT})"
    else
        warn "Autostart Boot  : DISABLED"
    fi

    # Health Check via HTTP & HTTPS API
    info "Testing REST API endpoints..."
    if command -v curl &>/dev/null; then
        HTTP_RESP=$(curl -s --max-time 3 "http://127.0.0.1:${PORT}/api/status" || true)
        if echo "$HTTP_RESP" | grep -q "timestamp"; then
            success "HTTP Health Check (port ${PORT}) : OK"
        else
            warn "HTTP Health Check (port ${PORT}) : UNRESPONSIVE"
        fi

        HTTPS_RESP=$(curl -k -s --max-time 3 "https://127.0.0.1:${HTTPS_PORT}/api/status" || true)
        if echo "$HTTPS_RESP" | grep -q "timestamp"; then
            success "HTTPS Health Check (port ${HTTPS_PORT}): OK"
        else
            warn "HTTPS Health Check (port ${HTTPS_PORT}): UNRESPONSIVE"
        fi
    fi
    info "======================================================================"
}

start_service() {
    PID=$(get_pid)
    if [[ -n "$PID" ]]; then
        warn "Service is already running (PID: ${PID}). Use 'restart' to reload."
        return 0
    fi

    info "Starting ElderCare Termux Hub..."
    mkdir -p "$LOG_DIR"

    # Acquire Termux Wake Lock to prevent CPU sleep
    if command -v termux-wake-lock &>/dev/null; then
        termux-wake-lock || true
        info "Acquired termux-wake-lock."
    fi

    cd "$HUB_DIR"
    if [[ -d "venv" ]]; then
        source venv/bin/activate
    fi

    export PORT=8888
    export HTTPS_PORT=8443
    export HOST=0.0.0.0
    nohup python3 app.py >> "$LOG_FILE" 2>&1 &
    NEW_PID=$!
    sleep 2

    if kill -0 "$NEW_PID" 2>/dev/null; then
        success "Senior Caregiver Termux Hub started successfully (PID: ${NEW_PID})"
        info "HTTP Dashboard : http://localhost:${PORT}"
        info "HTTPS Dashboard: https://localhost:${HTTPS_PORT}"
    else
        error "Failed to start service. Check logs at: ${LOG_FILE}"
    fi
}

stop_service() {
    info "Stopping ElderCare Termux Hub..."
    PID=$(get_pid)
    if [[ -z "$PID" ]]; then
        info "Service is not running."
        return 0
    fi

    kill -15 $PID 2>/dev/null || kill -9 $PID 2>/dev/null
    sleep 1
    success "Service stopped successfully."
}

enable_autostart() {
    info "Enabling autostart on phone reboot..."
    mkdir -p "$HOME/.termux/boot"
    cat << EOF > "$BOOT_SCRIPT"
#!/data/data/com.termux/files/usr/bin/bash
# Senior Caregiver Termux Hub Autostart
termux-wake-lock
mkdir -p \$HOME/.config/eldercare
cd \$HOME/eldercare-hub
if [ -d "venv" ]; then
    source venv/bin/activate
fi
export PORT=8888
export HTTPS_PORT=8443
export HOST=0.0.0.0
python3 app.py >> \$HOME/.config/eldercare/app.log 2>&1 &
EOF
    chmod +x "$BOOT_SCRIPT"
    success "Autostart enabled! Script created at: ${BOOT_SCRIPT}"
}

disable_autostart() {
    info "Disabling autostart on phone reboot..."
    if [[ -f "$BOOT_SCRIPT" ]]; then
        chmod -x "$BOOT_SCRIPT"
        success "Autostart script disabled (removed execution permission)."
    else
        info "Autostart script does not exist."
    fi
}

view_logs() {
    if [[ ! -f "$LOG_FILE" ]]; then
        error "Log file does not exist at: ${LOG_FILE}"
    fi
    info "Tailing live logs from ${LOG_FILE} (Ctrl+C to exit)..."
    tail -f -n 50 "$LOG_FILE"
}

# Execute Requested Action
case "$COMMAND" in
    status)
        check_status
        ;;
    start)
        start_service
        ;;
    stop)
        stop_service
        ;;
    restart)
        stop_service
        start_service
        ;;
    enable)
        enable_autostart
        ;;
    disable)
        disable_autostart
        ;;
    logs)
        view_logs
        ;;
esac
