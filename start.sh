#!/bin/bash

# Pride Discord Bot - Advanced Startup Script
# Features: Auto-recovery, health checks, clear logging, error handling

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%H:%M:%S') - $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $(date '+%H:%M:%S') - ${BOLD}$1${NC}"
}

log_warning() {
    echo -e "${YELLOW}[⚠]${NC} $(date '+%H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $(date '+%H:%M:%S') - ${BOLD}$1${NC}"
}

log_section() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
}

# Error handler
handle_error() {
    log_error "Script failed on line $1"
    log_error "Attempting recovery..."
    cleanup
    exit 1
}

trap 'handle_error $LINENO' ERR

# Cleanup function
cleanup() {
    log_warning "Performing cleanup..."
    # Kill any orphaned processes
    pkill -f "redis-server" 2>/dev/null || true
}

# Check and configure ImageMagick
configure_imagemagick() {
    log_info "Configuring ImageMagick..."
    
    # Try to find ImageMagick automatically
    MAGICK_PATH=$(find /nix/store -name "imagemagick-*" -type d 2>/dev/null | head -1 || echo "")
    
    if [ -n "$MAGICK_PATH" ]; then
        export MAGICK_HOME="$MAGICK_PATH"
        export LD_LIBRARY_PATH="${MAGICK_HOME}/lib:${LD_LIBRARY_PATH:-}"
        log_success "ImageMagick configured at: $MAGICK_PATH"
    else
        log_warning "ImageMagick path not found, using default path"
        export MAGICK_HOME="/nix/store/w9393s0xnbdy4v0dqlb1i5iv305bdnz9-imagemagick-7.1.1-47"
        export LD_LIBRARY_PATH="${MAGICK_HOME}/lib:${LD_LIBRARY_PATH:-}"
    fi
}

# Start Redis with retry logic
start_redis() {
    log_info "Starting Redis server..."
    
    # Check if Redis is already running
    if redis-cli ping >/dev/null 2>&1; then
        log_warning "Redis already running, stopping it first..."
        redis-cli shutdown 2>/dev/null || pkill -9 redis-server 2>/dev/null || true
        sleep 1
    fi
    
    # Start Redis with optimized settings for Replit
    redis-server \
        --daemonize yes \
        --port 6379 \
        --bind 127.0.0.1 \
        --loglevel warning \
        --maxmemory 256mb \
        --maxmemory-policy allkeys-lru \
        --save "" \
        --appendonly no \
        --dir /tmp \
        2>/dev/null || {
            log_error "Failed to start Redis server"
            return 1
        }
    
    # Wait for Redis to be ready (with timeout)
    local max_attempts=10
    local attempt=0
    while [ $attempt -lt $max_attempts ]; do
        if redis-cli ping >/dev/null 2>&1; then
            log_success "Redis server started successfully"
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 0.5
    done
    
    log_error "Redis server failed to start after $max_attempts attempts"
    return 1
}

# Check Python dependencies
check_dependencies() {
    log_info "Checking Python dependencies..."
    
    # Check critical packages
    local critical_packages=("discord" "asyncpg" "redis" "aiohttp")
    local missing_packages=()
    
    for package in "${critical_packages[@]}"; do
        if ! python -c "import $package" 2>/dev/null; then
            missing_packages+=("$package")
        fi
    done
    
    if [ ${#missing_packages[@]} -gt 0 ]; then
        log_warning "Missing packages detected: ${missing_packages[*]}"
        log_info "Installing missing packages..."
        pip install -q -r requirements.txt || {
            log_error "Failed to install dependencies"
            return 1
        }
        log_success "Dependencies installed"
    else
        log_success "All critical dependencies available"
    fi
}

# Check database connectivity
check_database() {
    log_info "Checking database connectivity..."
    
    if [ -z "${DATABASE_URL:-}" ]; then
        log_warning "DATABASE_URL not set, skipping database check"
        return 0
    fi
    
    # Simple connectivity check using Python
    python3 -c "
import asyncio
import asyncpg
import os
import sys

async def check():
    try:
        conn = await asyncpg.connect(os.getenv('DATABASE_URL'), timeout=5)
        await conn.close()
        return True
    except Exception as e:
        print(f'Database check failed: {e}', file=sys.stderr)
        return False

if asyncio.run(check()):
    sys.exit(0)
else:
    sys.exit(1)
" 2>/dev/null && {
        log_success "Database connection verified"
    } || {
        log_warning "Database check failed (bot will retry on startup)"
    }
}

# Check Discord token
check_token() {
    log_info "Checking Discord token..."
    
    if [ -z "${DISCORD_TOKEN:-}" ]; then
        log_error "DISCORD_TOKEN not set!"
        log_error "Please add your Discord bot token to Replit Secrets"
        return 1
    fi
    
    log_success "Discord token configured"
}

# Check Playwright browsers
check_playwright() {
    log_info "Checking Playwright browsers..."
    
    if [ ! -d "$HOME/.cache/ms-playwright/chromium-1187" ]; then
        log_warning "Playwright browsers not installed"
        log_info "Installing Playwright browsers (this may take a while)..."
        playwright install chromium >/dev/null 2>&1 || {
            log_warning "Failed to install Playwright browsers (non-critical)"
            log_warning "Browser features will be disabled"
        }
    fi
    
    if [ -d "$HOME/.cache/ms-playwright/chromium-1187" ]; then
        log_success "Playwright browsers available"
    else
        log_warning "Playwright browsers not available (browser features disabled)"
    fi
}

# Monitor bot health
monitor_bot() {
    log_info "Starting bot health monitor..."
    
    # Run bot with auto-restart on crash
    local restart_count=0
    local max_restarts=5
    
    while [ $restart_count -lt $max_restarts ]; do
        if [ $restart_count -gt 0 ]; then
            log_warning "Restarting bot (attempt $((restart_count + 1))/$max_restarts)..."
            sleep 5
        fi
        
        # Run the bot
        python main.py
        
        local exit_code=$?
        
        if [ $exit_code -eq 0 ]; then
            log_success "Bot exited cleanly"
            break
        else
            log_error "Bot crashed with exit code $exit_code"
            restart_count=$((restart_count + 1))
            
            if [ $restart_count -ge $max_restarts ]; then
                log_error "Maximum restart attempts reached"
                log_error "Please check the logs for errors"
                return 1
            fi
        fi
    done
}

# Main execution
main() {
    log_section "Pride Discord Bot - Startup Sequence"
    
    log_info "Environment: $(uname -s) $(uname -m)"
    log_info "Python: $(python --version 2>&1)"
    log_info "Working Directory: $(pwd)"
    
    # Pre-flight checks
    log_section "Phase 1: Pre-flight Checks"
    configure_imagemagick
    check_token || exit 1
    check_dependencies || exit 1
    check_playwright
    
    # Service initialization
    log_section "Phase 2: Service Initialization"
    start_redis || exit 1
    check_database
    
    # Bot startup
    log_section "Phase 3: Starting Discord Bot"
    log_success "All systems ready!"
    echo ""
    
    # Start bot with monitoring
    monitor_bot
    
    # Cleanup on exit
    log_section "Shutdown Sequence"
    cleanup
    log_success "Bot stopped cleanly"
}

# Run main function
main "$@"
