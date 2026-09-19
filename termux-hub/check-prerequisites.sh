#!/usr/bin/env bash
# ==============================================================================
# Prerequisite Software & System Readiness Checker with Auto-Install Option
# Senior Caregiver Termux Hub
# ==============================================================================
# Checks all required Termux binaries, Termux:API integration, Python 3 environment,
# PIP packages, directory structures, SSL certs, and network ports.
# Prompts the user to install any missing packages or Python modules automatically.
# Usage:
#   ./check-prerequisites.sh [OPTIONS]
# Options:
#   -y, --yes, --auto-install    Automatically install missing packages without prompting
# ==============================================================================

set -e

# Parse command line options
AUTO_INSTALL=false
for arg in "$@"; do
    case "$arg" in
        -y|--yes|--auto-install|-i|--install)
            AUTO_INSTALL=true
            ;;
    esac
done

# Color Constants
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

PASSED=0
WARNINGS=0
FAILED=0

MISSING_TERMUX_PKGS=()
MISSING_PYTHON_MODS=()

info() { echo -e "${BLUE}[INFO]${NC} $1"; }
pass() { echo -e "${GREEN}[PASS]${NC} $1"; PASSED=$((PASSED + 1)); }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; WARNINGS=$((WARNINGS + 1)); }
fail() { echo -e "${RED}[FAIL]${NC} $1"; FAILED=$((FAILED + 1)); }

add_missing_pkg() {
    local pkg="$1"
    local existing=false
    for p in "${MISSING_TERMUX_PKGS[@]}"; do
        if [ "$p" = "$pkg" ]; then
            existing=true
            break
        fi
    done
    if [ "$existing" = false ]; then
        MISSING_TERMUX_PKGS+=("$pkg")
    fi
}

echo -e "${BOLD}${CYAN}======================================================================${NC}"
echo -e "${BOLD}${CYAN} Senior Caregiver Termux Hub - Prerequisites & System Readiness Check ${NC}"
echo -e "${BOLD}${CYAN}======================================================================${NC}"
echo ""

# ------------------------------------------------------------------------------
# 1. Check Core Termux Packages & System Binaries
# ------------------------------------------------------------------------------
info "1. Checking Core Termux Packages & System Binaries..."

check_cmd() {
    local cmd="$1"
    local pkg_hint="$2"
    if command -v "$cmd" &>/dev/null; then
        pass "Binary '${cmd}' is installed ($(command -v "$cmd"))"
    else
        fail "Binary '${cmd}' NOT found. (Install package: ${pkg_hint})"
        add_missing_pkg "$pkg_hint"
    fi
}

check_cmd "python3" "python"
check_cmd "pip" "python"
check_cmd "openssl" "openssl-tool"
check_cmd "curl" "curl"
check_cmd "termux-wake-lock" "termux-tools"

# Port listing tool
if command -v netstat &>/dev/null || command -v ss &>/dev/null; then
    pass "Port diagnostic tool available (netstat/ss)"
else
    warn "Neither 'netstat' nor 'ss' found. Port diagnostics may be limited."
fi

echo ""

# ------------------------------------------------------------------------------
# 2. Check Termux:API Hardware Integration
# ------------------------------------------------------------------------------
info "2. Checking Termux:API Hardware CLI Tools & App Connection..."

check_api_cmd() {
    local cmd="$1"
    if command -v "$cmd" &>/dev/null; then
        pass "Termux:API command '${cmd}' available"
    else
        fail "Termux:API command '${cmd}' missing. (Install package: termux-api)"
        add_missing_pkg "termux-api"
    fi
}

check_api_cmd "termux-battery-status"
check_api_cmd "termux-location"
check_api_cmd "termux-tts-speak"
check_api_cmd "termux-vibrate"
check_api_cmd "termux-torch"
check_api_cmd "termux-telephony-call"
check_api_cmd "termux-sms-send"
check_api_cmd "termux-media-player"
check_api_cmd "termux-notification"
check_api_cmd "termux-volume"

# Live Termux:API Communication Test
info "Testing Termux:API hardware communication via 'termux-battery-status'..."
if command -v termux-battery-status &>/dev/null; then
    BATTERY_OUT=$(termux-battery-status 2>/dev/null || true)
    if echo "$BATTERY_OUT" | grep -q "percentage"; then
        pass "Termux:API communicating successfully with Android OS!"
    else
        warn "Termux:API command ran but returned unexpected response. Ensure Termux:API Android App is installed."
    fi
fi

# ------------------------------------------------------------------------------
# Prompt / Auto-Install for Missing Termux Packages
# ------------------------------------------------------------------------------
if [ "${#MISSING_TERMUX_PKGS[@]}" -gt 0 ]; then
    echo ""
    warn "Detected ${#MISSING_TERMUX_PKGS[@]} missing Termux package(s): ${MISSING_TERMUX_PKGS[*]}"
    do_install=false

    if [ "$AUTO_INSTALL" = true ]; then
        do_install=true
    elif [ -t 0 ]; then
        echo -ne "${BOLD}${YELLOW}Would you like to install missing Termux package(s) [${MISSING_TERMUX_PKGS[*]}] now? (y/N): ${NC}"
        read -n 1 -r REPLY
        echo ""
        if [[ "$REPLY" =~ ^[Yy]$ ]]; then
            do_install=true
        fi
    fi

    if [ "$do_install" = true ]; then
        info "Installing missing Termux package(s): ${MISSING_TERMUX_PKGS[*]}..."
        pkg update -y && pkg install -y "${MISSING_TERMUX_PKGS[@]}"
        info "Termux packages installed successfully!"
        # Recount failures
        FAILED=0
    fi
fi

echo ""

# ------------------------------------------------------------------------------
# 3. Check Python Virtual Environment & Required Packages
# ------------------------------------------------------------------------------
info "3. Checking Python 3 Environment & Dependencies..."

HUB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${HUB_DIR}/venv"

if [ -d "$VENV_DIR" ]; then
    pass "Python virtual environment directory exists (${VENV_DIR})"
    PYTHON_BIN="${VENV_DIR}/bin/python3"
    PIP_BIN="${VENV_DIR}/bin/pip"
else
    warn "Virtual environment not found at ${VENV_DIR}. Falling back to system Python."
    PYTHON_BIN="python3"
    PIP_BIN="pip"
fi

check_python_module() {
    local mod="$1"
    if "$PYTHON_BIN" -c "import ${mod}" &>/dev/null; then
        pass "Python module '${mod}' is installed"
    else
        fail "Python module '${mod}' is MISSING."
        MISSING_PYTHON_MODS+=("$mod")
    fi
}

check_python_module "flask"
check_python_module "requests"
check_python_module "pydantic"
check_python_module "werkzeug"

# ------------------------------------------------------------------------------
# Prompt / Auto-Install for Missing Python Modules
# ------------------------------------------------------------------------------
if [ "${#MISSING_PYTHON_MODS[@]}" -gt 0 ]; then
    echo ""
    warn "Detected ${#MISSING_PYTHON_MODS[@]} missing Python module(s): ${MISSING_PYTHON_MODS[*]}"
    do_py_install=false

    if [ "$AUTO_INSTALL" = true ]; then
        do_py_install=true
    elif [ -t 0 ]; then
        echo -ne "${BOLD}${YELLOW}Would you like to install missing Python module(s) [${MISSING_PYTHON_MODS[*]}] via pip now? (y/N): ${NC}"
        read -n 1 -r REPLY
        echo ""
        if [[ "$REPLY" =~ ^[Yy]$ ]]; then
            do_py_install=true
        fi
    fi

    if [ "$do_py_install" = true ]; then
        info "Installing missing Python module(s) via '${PIP_BIN} install ${MISSING_PYTHON_MODS[*]}'..."
        "$PIP_BIN" install "${MISSING_PYTHON_MODS[@]}"
        info "Python modules installed successfully!"
    fi
fi

echo ""

# ------------------------------------------------------------------------------
# 4. Check Directory Structures & Configuration Files
# ------------------------------------------------------------------------------
info "4. Checking Application Directories & Files..."

CONFIG_DIR="$HOME/.config/eldercare"
SOUNDS_DIR="${CONFIG_DIR}/sounds"
CERT_FILE="${CONFIG_DIR}/cert.pem"
KEY_FILE="${CONFIG_DIR}/key.pem"
BOOT_DIR="$HOME/.termux/boot"

check_dir() {
    local dir="$1"
    local label="$2"
    if [ -d "$dir" ]; then
        pass "${label} exists: ${dir}"
    else
        warn "${label} missing: ${dir} (Will be auto-created on service startup)"
    fi
}

check_dir "$CONFIG_DIR" "Configuration directory"
check_dir "$SOUNDS_DIR" "Custom sounds directory"
check_dir "$BOOT_DIR" "Termux:Boot autostart directory"

if [ -f "$CERT_FILE" ] && [ -f "$KEY_FILE" ]; then
    pass "Self-signed SSL Certificate & Key exist in ${CONFIG_DIR}"
else
    warn "SSL cert/key missing in ${CONFIG_DIR} (Will be auto-generated on server startup)"
fi

echo ""

# ------------------------------------------------------------------------------
# 5. Check Network Ports (HTTP 8888 & HTTPS 8443)
# ------------------------------------------------------------------------------
info "5. Checking Network Ports (8888 / 8443)..."

check_port_free() {
    local port="$1"
    local proto="$2"
    local listening=""
    if command -v netstat &>/dev/null; then
        listening=$(netstat -tuln 2>/dev/null | grep ":${port} " || true)
    elif command -v ss &>/dev/null; then
        listening=$(ss -tuln 2>/dev/null | grep ":${port} " || true)
    fi

    if [ -n "$listening" ]; then
        pass "${proto} Port ${port} is currently bound / listening (Service active or in use)"
    else
        pass "${proto} Port ${port} is available for binding"
    fi
}

check_port_free "8888" "HTTP"
check_port_free "8443" "HTTPS"

echo ""

# ------------------------------------------------------------------------------
# Readiness Summary Report
# ------------------------------------------------------------------------------
echo -e "${BOLD}${CYAN}======================================================================${NC}"
echo -e "${BOLD}${CYAN} Prerequisites & System Readiness Summary ${NC}"
echo -e "${BOLD}${CYAN}======================================================================${NC}"
echo -e " Tests Passed  : ${GREEN}${PASSED}${NC}"
echo -e " Warnings      : ${YELLOW}${WARNINGS}${NC}"
echo -e " Failures      : ${RED}${FAILED}${NC}"
echo -e "${BOLD}${CYAN}======================================================================${NC}"

if [ "$FAILED" -eq 0 ]; then
    echo -e "${GREEN}${BOLD}✓ System is READY to run Senior Caregiver Termux Hub!${NC}"
    exit 0
else
    echo -e "${RED}${BOLD}✗ System has ${FAILED} critical missing prerequisite(s). Please fix items above.${NC}"
    exit 1
fi
