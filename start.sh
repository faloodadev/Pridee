#!/bin/bash

# Pride Discord Bot - Professional Startup Script
# Features: Progress bars, animations, auto-recovery, health monitoring

set -euo pipefail

# ============================================================================
# COLOR DEFINITIONS & STYLING
# ============================================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
WHITE='\033[1;37m'
NC='\033[0m'
BOLD='\033[1m'
DIM='\033[2m'

# Unicode symbols
CHECK_MARK="✓"
CROSS_MARK="✗"
WARNING_MARK="⚠"
INFO_MARK="ℹ"
LOADING_MARK="◉"
ARROW="→"

# ============================================================================
# LOGGING FUNCTIONS
# ============================================================================
log_info() {
    echo -e "${BLUE}${INFO_MARK}${NC} ${DIM}$(date '+%H:%M:%S')${NC} ${ARROW} $1"
}

log_success() {
    echo -e "${GREEN}${CHECK_MARK}${NC} ${DIM}$(date '+%H:%M:%S')${NC} ${ARROW} ${BOLD}$1${NC}"
}

log_warning() {
    echo -e "${YELLOW}${WARNING_MARK}${NC} ${DIM}$(date '+%H:%M:%S')${NC} ${ARROW} $1"
}

log_error() {
    echo -e "${RED}${CROSS_MARK}${NC} ${DIM}$(date '+%H:%M:%S')${NC} ${ARROW} ${BOLD}$1${NC}"
}

log_section() {
    echo ""
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${WHITE}${BOLD}$1${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

log_subsection() {
    echo -e "\n${MAGENTA}┌─ $1${NC}"
}

# ============================================================================
# PROGRESS BAR FUNCTION
# ============================================================================
show_progress() {
    local current=$1
    local total=$2
    local message=$3
    local width=50
    local percentage=$((current * 100 / total))
    local filled=$((width * current / total))
    local empty=$((width - filled))
    
    # Create the bar
    local bar=""
    for ((i=0; i<filled; i++)); do
        bar+="█"
    done
    for ((i=0; i<empty; i++)); do
        bar+="░"
    done
    
    # Color based on percentage
    local color="${CYAN}"
    if [ $percentage -ge 100 ]; then
        color="${GREEN}"
    elif [ $percentage -ge 50 ]; then
        color="${BLUE}"
    fi
    
    # Print the progress bar
    printf "\r${color}▶${NC} [${color}%s${NC}] %3d%% ${DIM}│${NC} %s" "$bar" "$percentage" "$message"
    
    # New line if complete
    if [ $current -eq $total ]; then
        echo ""
    fi
}

# ============================================================================
# ANIMATED SPINNER
# ============================================================================
spin() {
    local pid=$1
    local message=$2
    local spinstr='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
    local temp
    
    while kill -0 $pid 2>/dev/null; do
        temp=${spinstr#?}
        printf "\r${CYAN}%c${NC} ${message}..." "$spinstr"
        spinstr=$temp${spinstr%"$temp"}
        sleep 0.1
    done
    printf "\r"
}

# ============================================================================
# ERROR HANDLING
# ============================================================================
handle_error() {
    log_error "Fatal error on line $1"
    log_error "Initiating emergency cleanup..."
    cleanup
    exit 1
}

trap 'handle_error $LINENO' ERR

# ============================================================================
# CLEANUP FUNCTION
# ============================================================================
cleanup() {
    log_subsection "Cleanup Operations"
    pkill -f "redis-server" 2>/dev/null && log_info "Stopped Redis server" || true
    log_success "Cleanup completed"
}

# ============================================================================
# IMAGEMAGICK CONFIGURATION
# ============================================================================
configure_imagemagick() {
    log_info "Configuring ImageMagick libraries..."
    
    # Find ImageMagick in Nix store with timeout
    local magick_path=$(timeout 3 find /nix/store -maxdepth 1 -name "*imagemagick*" -type d 2>/dev/null | head -1 || echo "")
    
    if [ -n "$magick_path" ] && [ -d "$magick_path" ]; then
        export MAGICK_HOME="$magick_path"
        export LD_LIBRARY_PATH="${MAGICK_HOME}/lib:${LD_LIBRARY_PATH:-}"
        log_success "ImageMagick configured: ${MAGICK_HOME##*/}"
    else
        log_info "ImageMagick auto-detect skipped (system default will be used)"
    fi
}

# ============================================================================
# REDIS STARTUP
# ============================================================================
start_redis() {
    log_subsection "Redis Server Initialization"
    
    # Check if already running
    if redis-cli ping >/dev/null 2>&1; then
        log_warning "Redis already running, restarting..."
        redis-cli shutdown 2>/dev/null || pkill -9 redis-server 2>/dev/null || true
        sleep 1
    fi
    
    # Start Redis in background
    log_info "Starting Redis server..."
    redis-server \
        --daemonize yes \
        --port 6379 \
        --bind 127.0.0.1 \
        --loglevel warning \
        --maxmemory 256mb \
        --maxmemory-policy allkeys-lru \
        --save "" \
        --appendonly no \
        --dir /tmp 2>/dev/null &
    
    local redis_pid=$!
    
    # Wait with progress bar
    local attempts=0
    local max_attempts=20
    while [ $attempts -lt $max_attempts ]; do
        if redis-cli ping >/dev/null 2>&1; then
            show_progress $max_attempts $max_attempts "Redis server startup"
            log_success "Redis server online (localhost:6379)"
            return 0
        fi
        show_progress $attempts $max_attempts "Redis server startup"
        sleep 0.2
        attempts=$((attempts + 1))
    done
    
    log_error "Redis failed to start"
    return 1
}

# ============================================================================
# DEPENDENCY CHECK
# ============================================================================
check_dependencies() {
    log_subsection "Python Dependencies Verification"
    
    local packages=("discord" "asyncpg" "redis" "aiohttp" "pillow" "dotenv")
    local total=${#packages[@]}
    local current=0
    local missing=()
    
    for package in "${packages[@]}"; do
        current=$((current + 1))
        show_progress $current $total "Checking $package"
        
        if ! python -c "import $package" 2>/dev/null; then
            missing+=("$package")
        fi
        sleep 0.05
    done
    
    if [ ${#missing[@]} -gt 0 ]; then
        log_warning "Missing packages: ${missing[*]}"
        log_info "Installing dependencies (this may take a moment)..."
        
        # Install with progress indicator
        pip install -q -r requirements.txt 2>&1 &
        local pip_pid=$!
        spin $pip_pid "Installing Python packages"
        wait $pip_pid
        
        log_success "All dependencies installed"
    else
        log_success "All dependencies available"
    fi
}

# ============================================================================
# DATABASE CHECK
# ============================================================================
check_database() {
    log_subsection "Database Connectivity"
    
    if [ -z "${DATABASE_URL:-}" ]; then
        log_warning "DATABASE_URL not configured"
        return 0
    fi
    
    log_info "Testing PostgreSQL connection..."
    
    python3 -c "
import asyncio
import asyncpg
import os
import sys

async def check():
    try:
        conn = await asyncpg.connect(os.getenv('DATABASE_URL'), timeout=10)
        version = await conn.fetchval('SELECT version()')
        await conn.close()
        print(f'Connected: {version.split()[0]} {version.split()[1]}')
        return True
    except Exception as e:
        print(f'Connection failed: {e}', file=sys.stderr)
        return False

sys.exit(0 if asyncio.run(check()) else 1)
" 2>/dev/null && {
        log_success "Database connection verified"
    } || {
        log_warning "Database unreachable (will retry on bot startup)"
    }
}

# ============================================================================
# DISCORD TOKEN CHECK
# ============================================================================
check_token() {
    log_subsection "Discord Authentication"
    
    if [ -z "${DISCORD_TOKEN:-}" ]; then
        log_error "DISCORD_TOKEN not configured!"
        log_error "Add your bot token to Replit Secrets"
        return 1
    fi
    
    local token_preview="${DISCORD_TOKEN:0:10}...${DISCORD_TOKEN: -4}"
    log_success "Discord token configured ($token_preview)"
}

# ============================================================================
# PLAYWRIGHT BROWSER CHECK
# ============================================================================
check_playwright() {
    log_subsection "Playwright Browser Engine"
    
    local browser_path="$HOME/.cache/ms-playwright/chromium-1187"
    
    if [ ! -d "$browser_path" ]; then
        log_info "Installing Chromium browser..."
        playwright install chromium >/dev/null 2>&1 &
        local playwright_pid=$!
        spin $playwright_pid "Downloading Chromium"
        wait $playwright_pid && {
            log_success "Chromium browser installed"
        } || {
            log_warning "Browser installation failed (browser features disabled)"
        }
    else
        log_success "Chromium browser available"
    fi
}

# ============================================================================
# SYSTEM INFO DISPLAY
# ============================================================================
show_system_info() {
    log_subsection "System Information"
    
    log_info "OS: $(uname -s) $(uname -m)"
    log_info "Python: $(python --version 2>&1)"
    log_info "Pip: $(pip --version | cut -d' ' -f2)"
    log_info "Working Directory: $(pwd)"
    
    # Show resource info if available
    if command -v free >/dev/null 2>&1; then
        local mem=$(free -h | awk '/^Mem:/ {print $2}')
        log_info "Memory: $mem"
    fi
}

# ============================================================================
# BOT HEALTH MONITOR
# ============================================================================
monitor_bot() {
    log_subsection "Discord Bot Process Monitor"
    
    local restart_count=0
    local max_restarts=3
    
    while [ $restart_count -lt $max_restarts ]; do
        if [ $restart_count -gt 0 ]; then
            log_warning "Auto-restart triggered (attempt $((restart_count + 1))/$max_restarts)"
            sleep 3
        fi
        
        log_info "Launching bot process..."
        echo ""
        echo -e "${CYAN}╭─────────────────────────────────────────────────────────────────────╮${NC}"
        echo -e "${CYAN}│${NC}                    ${WHITE}${BOLD}BOT CONSOLE OUTPUT${NC}                            ${CYAN}│${NC}"
        echo -e "${CYAN}╰─────────────────────────────────────────────────────────────────────╯${NC}"
        echo ""
        
        python main.py
        local exit_code=$?
        
        if [ $exit_code -eq 0 ]; then
            log_success "Bot exited gracefully"
            break
        else
            log_error "Bot crashed (exit code: $exit_code)"
            restart_count=$((restart_count + 1))
            
            if [ $restart_count -ge $max_restarts ]; then
                log_error "Maximum restart limit reached"
                log_error "Check logs for error details"
                return 1
            fi
        fi
    done
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================
main() {
    clear
    
    # Header
    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════════════════╗"
    echo "║                                                                       ║"
    echo "║                    ${WHITE}${BOLD}PRIDE DISCORD BOT${NC}${CYAN}                                 ║"
    echo "║                   ${DIM}Professional Startup System${NC}${CYAN}                       ║"
    echo "║                                                                       ║"
    echo "╚═══════════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    # Phase 1: System Checks
    log_section "PHASE 1 │ System Checks & Configuration"
    show_system_info
    configure_imagemagick
    check_token || exit 1
    
    # Phase 2: Dependencies
    log_section "PHASE 2 │ Dependency Verification"
    check_dependencies || exit 1
    check_playwright
    
    # Phase 3: Services
    log_section "PHASE 3 │ Service Initialization"
    start_redis || exit 1
    check_database
    
    # Phase 4: Launch
    log_section "PHASE 4 │ Bot Launch Sequence"
    log_success "All systems operational!"
    echo ""
    sleep 1
    
    monitor_bot
    
    # Shutdown
    echo ""
    log_section "SHUTDOWN SEQUENCE"
    cleanup
    log_success "System shutdown complete"
}

# ============================================================================
# ENTRY POINT
# ============================================================================
main "$@"
