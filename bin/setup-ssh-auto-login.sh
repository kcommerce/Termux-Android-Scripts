#!/usr/bin/env bash
# ==============================================================================
# Setup Auto SSH Login for Termux (Samsung S7 Edge / Android)
# ==============================================================================
# Usage:
#   ./bin/setup-ssh-auto-login.sh [IP_ADDRESS] [PORT] [USER]
#
# Examples:
#   ./bin/setup-ssh-auto-login.sh
#   ./bin/setup-ssh-auto-login.sh 10.81.8.161 8022 root
# ==============================================================================

set -e

# Default settings
DEFAULT_IP="10.81.8.161"
DEFAULT_PORT="8022"
DEFAULT_USER="root"
DEFAULT_ALIAS="termux-s7"

# Color constants
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
Usage: $(basename "$0") [OPTIONS] [IP_ADDRESS] [PORT] [USER]

Setup passwordless SSH login to Termux on Android device.

Options:
  -h, --help           Show this help message and exit
  -a, --alias ALIAS    SSH host alias for ~/.ssh/config (default: ${DEFAULT_ALIAS})
  -k, --key PATH       Path to SSH public key to copy

Arguments:
  IP_ADDRESS           IP address of the Termux device (default: ${DEFAULT_IP})
  PORT                 SSH port of Termux (default: ${DEFAULT_PORT})
  USER                 Remote SSH user (default: ${DEFAULT_USER})

Examples:
  ./bin/setup-ssh-auto-login.sh
  ./bin/setup-ssh-auto-login.sh 10.81.8.161 8022 root
  ./bin/setup-ssh-auto-login.sh --alias s7-edge 10.81.8.161
EOF
}

# Parse options
ALIAS="${DEFAULT_ALIAS}"
KEY_PATH=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help)
            show_help
            exit 0
            ;;
        -a|--alias)
            ALIAS="$2"
            shift 2
            ;;
        -k|--key)
            KEY_PATH="$2"
            shift 2
            ;;
        -*)
            error "Unknown option: $1. Use --help for usage."
            ;;
        *)
            break
            ;;
    esac
done

TARGET_IP="${1:-$DEFAULT_IP}"
TARGET_PORT="${2:-$DEFAULT_PORT}"
TARGET_USER="${3:-$DEFAULT_USER}"

info "Target Device : ${TARGET_USER}@${TARGET_IP}:${TARGET_PORT}"
info "SSH Alias     : ${ALIAS}"

# 1. Locate or generate SSH key pair
if [[ -n "$KEY_PATH" ]]; then
    PUB_KEY="$KEY_PATH"
    PRIV_KEY="${KEY_PATH%.pub}"
else
    if [[ -f "$HOME/.ssh/id_ed25519.pub" ]]; then
        PUB_KEY="$HOME/.ssh/id_ed25519.pub"
        PRIV_KEY="$HOME/.ssh/id_ed25519"
    elif [[ -f "$HOME/.ssh/id_rsa.pub" ]]; then
        PUB_KEY="$HOME/.ssh/id_rsa.pub"
        PRIV_KEY="$HOME/.ssh/id_rsa"
    else
        info "No existing SSH key found. Generating a new ed25519 SSH key pair..."
        mkdir -p "$HOME/.ssh"
        chmod 700 "$HOME/.ssh"
        ssh-keygen -t ed25519 -N "" -f "$HOME/.ssh/id_ed25519" -C "termux-auto-login"
        PUB_KEY="$HOME/.ssh/id_ed25519.pub"
        PRIV_KEY="$HOME/.ssh/id_ed25519"
        success "Generated key at $PRIV_KEY"
    fi
fi

if [[ ! -f "$PUB_KEY" ]]; then
    error "Public key file not found at: $PUB_KEY"
fi

info "Using SSH public key: $PUB_KEY"

# 2. Copy SSH key to Termux device
info "Copying public key to ${TARGET_USER}@${TARGET_IP}:${TARGET_PORT}..."
info "(You will be asked for the Termux user password one last time)"

if command -v ssh-copy-id &>/dev/null; then
    ssh-copy-id -o StrictHostKeyChecking=accept-new -i "$PUB_KEY" -p "$TARGET_PORT" "${TARGET_USER}@${TARGET_IP}" || {
        warn "ssh-copy-id encountered an error. Attempting manual key transfer..."
        cat "$PUB_KEY" | ssh -o StrictHostKeyChecking=accept-new -p "$TARGET_PORT" "${TARGET_USER}@${TARGET_IP}" \
            "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
    }
else
    cat "$PUB_KEY" | ssh -o StrictHostKeyChecking=accept-new -p "$TARGET_PORT" "${TARGET_USER}@${TARGET_IP}" \
        "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
fi

# Ensure correct permissions on remote device
ssh -o StrictHostKeyChecking=accept-new -p "$TARGET_PORT" "${TARGET_USER}@${TARGET_IP}" \
    "chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys" 2>/dev/null || true

success "Public key successfully installed on Termux."

# 3. Test passwordless SSH login
info "Testing passwordless SSH login..."
if ssh -o BatchMode=yes -o ConnectTimeout=5 -i "$PRIV_KEY" -p "$TARGET_PORT" "${TARGET_USER}@${TARGET_IP}" "echo 'Termux SSH connection OK! User: \$(whoami)'"; then
    success "Auto SSH login verified successfully!"
else
    warn "Automated test failed. Please verify network connectivity and password."
fi

# 4. Configure ~/.ssh/config alias
SSH_CONFIG="$HOME/.ssh/config"
info "Checking SSH config entry in $SSH_CONFIG..."

if ! grep -q "^Host ${ALIAS}\$" "$SSH_CONFIG" 2>/dev/null; then
    mkdir -p "$HOME/.ssh"
    cat << EOF >> "$SSH_CONFIG"

# Termux Android Device (Samsung S7 Edge)
Host ${ALIAS}
    HostName ${TARGET_IP}
    User ${TARGET_USER}
    Port ${TARGET_PORT}
    IdentityFile ${PRIV_KEY}
EOF
    chmod 600 "$SSH_CONFIG"
    success "Added '${ALIAS}' alias to $SSH_CONFIG"
else
    info "Host entry '${ALIAS}' already exists in $SSH_CONFIG"
fi

echo ""
echo -e "${GREEN}======================================================================${NC}"
echo -e "${GREEN} Setup Complete! You can now log into Termux without a password using:${NC}"
echo -e "${YELLOW}   ssh ${ALIAS}${NC}"
echo -e " Or directly with:"
echo -e "${YELLOW}   ssh -p ${TARGET_PORT} ${TARGET_USER}@${TARGET_IP}${NC}"
echo -e "${GREEN}======================================================================${NC}"
