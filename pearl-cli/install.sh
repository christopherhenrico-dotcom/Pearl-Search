#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  Pearl CLI — Arch Linux Installer
#  ☠  Hoist the flag and set sail  ☠
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
DIM='\033[2m'
BOLD='\033[1m'
RESET='\033[0m'

SKULL="☠"
ANCHOR="⚓"

banner() {
    echo -e "${RED}"
    cat << 'EOF'
██████╗ ███████╗ █████╗ ██████╗ ██╗     
██╔══██╗██╔════╝██╔══██╗██╔══██╗██║     
██████╔╝█████╗  ███████║██████╔╝██║     
██╔═══╝ ██╔══╝  ██╔══██║██╔══██╗██║     
██║     ███████╗██║  ██║██║  ██║███████╗
╚═╝     ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝
EOF
    echo -e "${RESET}"
    echo -e "  ${RED}${SKULL}${RESET}  ${BOLD}Pearl CLI Installer${RESET}  ${RED}${SKULL}${RESET}"
    echo -e "  ${DIM}The Pirate's Media CLI for Arch Linux${RESET}"
    echo
}

info()    { echo -e "  ${CYAN}${ANCHOR}${RESET}  $*"; }
success() { echo -e "  ${GREEN}✓${RESET}  $*"; }
warn()    { echo -e "  ${YELLOW}⚠${RESET}  $*"; }
die()     { echo -e "  ${RED}${SKULL}  ERROR: $*${RESET}" >&2; exit 1; }

check_arch() {
    if ! command -v pacman &>/dev/null; then
        die "This installer is for Arch Linux (pacman required)."
    fi
}

check_python() {
    local ver
    ver=$(python3 -c 'import sys; print(sys.version_info[:2] >= (3,11))' 2>/dev/null || echo "False")
    if [[ "$ver" != "True" ]]; then
        die "Python 3.11+ is required. Install: sudo pacman -S python"
    fi
    success "Python $(python3 --version)"
}

install_system_deps() {
    info "Installing system dependencies via pacman…"

    local pkgs=()

    if ! command -v vlc &>/dev/null; then
        pkgs+=("vlc")
    else
        success "VLC already installed"
    fi

    if ! command -v yt-dlp &>/dev/null; then
        pkgs+=("yt-dlp")
    else
        success "yt-dlp already installed"
    fi

    if [[ ${#pkgs[@]} -gt 0 ]]; then
        echo -e "  ${DIM}Installing: ${pkgs[*]}${RESET}"
        sudo pacman -S --noconfirm --needed "${pkgs[@]}"
    fi
}

install_pip_deps() {
    info "Installing Python dependencies…"

    local pip_cmd
    if command -v pip3 &>/dev/null; then
        pip_cmd="pip3"
    elif python3 -m pip --version &>/dev/null 2>&1; then
        pip_cmd="python3 -m pip"
    else
        # Try to install pip via pacman
        warn "pip not found — installing python-pip…"
        sudo pacman -S --noconfirm --needed python-pip
        pip_cmd="pip3"
    fi

    # Install Pearl and its dependencies
    $pip_cmd install --user --upgrade pip --quiet
    $pip_cmd install --user . --quiet
    success "Pearl installed"
}

install_pipx() {
    # Preferred: use pipx for isolated install
    if ! command -v pipx &>/dev/null; then
        info "Installing pipx for isolated install…"
        if python3 -m pip install --user pipx --quiet 2>/dev/null; then
            python3 -m pipx ensurepath --quiet 2>/dev/null || true
        else
            return 1
        fi
    fi
    pipx install . --force --quiet
    success "Pearl installed via pipx (isolated environment)"
    return 0
}

write_default_config() {
    local cfg_dir="$HOME/.config/pearl"
    local cfg_file="$cfg_dir/config.toml"

    if [[ -f "$cfg_file" ]]; then
        info "Config already exists: $cfg_file"
        return
    fi

    mkdir -p "$cfg_dir"
    # Run Pearl once to write default config
    python3 -c "from pearl.config import write_default_config; write_default_config()" 2>/dev/null || true
    success "Default config written: $cfg_file"
}

check_path() {
    local pearl_path
    pearl_path=$(command -v pearl 2>/dev/null || true)
    if [[ -z "$pearl_path" ]]; then
        warn "pearl not found in PATH."
        warn "Add ~/.local/bin to your PATH:"
        echo
        echo -e "    ${DIM}# Add to ~/.bashrc or ~/.zshrc:${RESET}"
        echo -e "    ${CYAN}export PATH=\"\$HOME/.local/bin:\$PATH\"${RESET}"
        echo
    else
        success "pearl is in PATH: $pearl_path"
    fi
}

run_doctor() {
    info "Running pearl doctor…"
    python3 -m pearl.cli doctor 2>/dev/null || pearl doctor 2>/dev/null || true
}

main() {
    banner

    check_arch
    check_python

    echo
    info "Installing Pearl CLI…"
    echo

    install_system_deps
    echo

    # Try pipx first (cleanest), fall back to pip --user
    if ! install_pipx 2>/dev/null; then
        install_pip_deps
    fi

    echo
    write_default_config
    check_path

    echo
    echo -e "  ${RED}─────────────────────────────────────────────────────${RESET}"
    echo -e "  ${GREEN}${SKULL}  Pearl is ready to sail, Cap'n!  ${SKULL}${RESET}"
    echo -e "  ${RED}─────────────────────────────────────────────────────${RESET}"
    echo
    echo -e "  ${BOLD}Quick start:${RESET}"
    echo -e "    ${CYAN}pearl search \"Breaking Bad\" 1080p${RESET}"
    echo -e "    ${CYAN}pearl play <any-url>${RESET}"
    echo -e "    ${CYAN}pearl config${RESET}   ${DIM}# add your sources${RESET}"
    echo -e "    ${CYAN}pearl help${RESET}"
    echo
    echo -e "  ${DIM}Config: ~/.config/pearl/config.toml${RESET}"
    echo

    run_doctor
    echo
}

main "$@"
