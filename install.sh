#!/usr/bin/env bash
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

info()  { echo -e "${CYAN}[INFO]${RESET}  $*"; }
ok()    { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
fail()  { echo -e "${RED}[FAIL]${RESET}  $*"; exit 1; }

echo ""
echo -e "${BOLD}╔══════════════════════════════════════╗${RESET}"
echo -e "${BOLD}║         Zero Ichi Installer           ║${RESET}"
echo -e "${BOLD}║       WhatsApp Bot built with 💖      ║${RESET}"
echo -e "${BOLD}╚══════════════════════════════════════╝${RESET}"
echo ""

INSTALL_DIR="${INSTALL_DIR:-$HOME/zero-ichi}"
REPO_URL="https://github.com/MhankBarBar/zero-ichi.git"
BRANCH="${BRANCH:-main}"

OS="$(uname -s)"
case "$OS" in
    Linux*)  PLATFORM="linux";;
    Darwin*) PLATFORM="macos";;
    *)       fail "Unsupported OS: $OS";;
esac
info "Detected platform: ${BOLD}$PLATFORM${RESET}"

has() { command -v "$1" &>/dev/null; }

check_python() {
    if has python3; then
        PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
        PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)
        if [ "$PY_MAJOR" -ge 3 ] && [ "$PY_MINOR" -ge 11 ]; then
            ok "Python $PY_VER found"
            return
        fi
    fi
    fail "Python 3.11+ is required. Install it from https://python.org or your package manager."
}

check_uv() {
    if has uv; then
        ok "uv found ($(uv --version))"
    else
        info "Installing uv..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        export PATH="$HOME/.local/bin:$PATH"
        if has uv; then
            ok "uv installed ($(uv --version))"
        else
            fail "Failed to install uv. Install manually: https://docs.astral.sh/uv/"
        fi
    fi
}

check_ffmpeg() {
    if has ffmpeg; then
        ok "FFmpeg found"
    else
        warn "FFmpeg not found. Attempting to install..."
        if [ "$PLATFORM" = "linux" ]; then
            if has apt-get; then
                sudo apt-get update -qq && sudo apt-get install -y -qq ffmpeg
            elif has dnf; then
                sudo dnf install -y ffmpeg
            elif has pacman; then
                sudo pacman -S --noconfirm ffmpeg
            else
                fail "Cannot auto-install FFmpeg. Install it manually."
            fi
        elif [ "$PLATFORM" = "macos" ]; then
            if has brew; then
                brew install ffmpeg
            else
                fail "Homebrew not found. Install FFmpeg manually: brew install ffmpeg"
            fi
        fi
        has ffmpeg && ok "FFmpeg installed" || fail "FFmpeg installation failed."
    fi
}

check_bun() {
    if has bun; then
        ok "Bun found ($(bun --version))"
    else
        info "Installing Bun (needed for YouTube downloads)..."
        curl -fsSL https://bun.sh/install | bash
        export PATH="$HOME/.bun/bin:$PATH"
        has bun && ok "Bun installed ($(bun --version))" || warn "Bun installation failed. YouTube downloads may not work."
    fi
}

check_git() {
    has git && ok "Git found" || fail "Git is required. Install it from https://git-scm.com"
}

info "Checking dependencies..."
echo ""
check_git
check_python
check_uv
check_ffmpeg
check_bun
echo ""

if [ -d "$INSTALL_DIR" ]; then
    info "Directory $INSTALL_DIR already exists, pulling latest..."
    cd "$INSTALL_DIR"
    git pull --ff-only origin "$BRANCH" || warn "Git pull failed, continuing with existing code."
else
    info "Cloning Zero Ichi to $INSTALL_DIR..."
    git clone --depth 1 --branch "$BRANCH" "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

info "Installing Python dependencies..."
uv sync --quiet
ok "Dependencies installed"

if [ ! -f .env ]; then
    cp .env.example .env
    ok "Created .env from .env.example"
    warn "Edit ${BOLD}$INSTALL_DIR/.env${RESET} to configure your bot."
else
    ok ".env already exists, skipping."
fi

echo ""
echo -e "${GREEN}${BOLD}✅ Installation complete!${RESET}"
echo ""
echo -e "  ${BOLD}To start the bot:${RESET}"
echo -e "    cd $INSTALL_DIR"
echo -e "    uv run zero-ichi"
echo ""
echo -e "  ${BOLD}First run:${RESET}"
echo -e "    Scan the QR code with WhatsApp → Settings → Linked Devices"
echo ""
echo -e "  ${BOLD}Docs:${RESET} https://zeroichi.mhankbarbar.dev"
echo ""
