#!/bin/bash

# Ubuntu Compatible Celery Management Script
# Simplified version for Ubuntu server deployment

# --- Error Handling ---
set -euo pipefail

# --- Color Definitions ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# --- Configuration ---
LOGS_DIR="./logs"
CELERY_LOG="$LOGS_DIR/celery.log"
CELERY_PID="$LOGS_DIR/celery.pid"
CELERY_BEAT_LOG="$LOGS_DIR/celery-beat.log"
CELERY_BEAT_PID="$LOGS_DIR/celery-beat.pid"

# --- Environment Setup ---
setup_environment() {
    # Development environment configuration
    export PYTHONWARNINGS="ignore:Unverified HTTPS request"
    export PYTHONIOENCODING=utf-8
    export PYTHONNOUSERSITE=1
    
    # Ensure logs directory exists
    mkdir -p "$LOGS_DIR"
}

# --- Worker Configuration ---
get_worker_config() {
    # Get CPU cores, Ubuntu compatible
    local cpu_cores
    if command -v nproc &> /dev/null; then
        cpu_cores=$(nproc 2>/dev/null || echo "2")
    else
        cpu_cores="2"
    fi
    
    # 限制最大并发数为2，避免资源过度消耗
    WORKER_COUNT=2
    echo -e "${GREEN}[INFO]${NC} Using $WORKER_COUNT worker processes (CPU cores: $cpu_cores, limited to 2 for stability)"
}

# --- Help Function ---
show_help() {
    cat << EOF
Ubuntu Celery Management Script - Usage:

Main Commands:
  ./manage_celery_k3s.sh start         Start all Celery services (worker + beat)
  ./manage_celery_k3s.sh stop          Stop all Celery services (worker + beat)
  ./manage_celery_k3s.sh restart       Restart all Celery services
  ./manage_celery_k3s.sh status        Check status of all services

Utilities:
  ./manage_celery_k3s.sh init-tasks    Initialize scheduled tasks
  ./manage_celery_k3s.sh logs          View recent worker logs
  ./manage_celery_k3s.sh help          Show this help message

EOF
}

# --- Worker Functions ---

start_worker_bg() {
    # 强力清理所有现有的worker进程
    echo -e "${YELLOW}[INFO]${NC} Cleaning up any existing worker processes..."
    
    # 使用更强力的清理方式
    pkill -TERM -f "celery.*skyeye.*worker" 2>/dev/null || true
    sleep 3
    pkill -KILL -f "celery.*skyeye.*worker" 2>/dev/null || true
    
    # 清理PID文件
    [[ -f "$CELERY_PID" ]] && rm -f "$CELERY_PID"
    
    # 等待确保所有进程都被清理
    local count=0
    while [[ $count -lt 10 ]] && pgrep -f "celery.*skyeye.*worker" > /dev/null; do
        echo -e "${YELLOW}[INFO]${NC} Waiting for processes to terminate... ($count/10)"
        sleep 1
        ((count++))
    done
    
    # 最终检查
    local remaining=$(pgrep -f "celery.*skyeye.*worker" | wc -l)
    if [[ $remaining -gt 0 ]]; then
        echo -e "${RED}[WARNING]${NC} $remaining worker processes still running, forcing kill..."
        pkill -KILL -f "celery.*skyeye.*worker" 2>/dev/null || true
        sleep 2
    fi
    
    get_worker_config
    echo -e "${GREEN}[INFO]${NC} Starting Celery worker in background..."
    echo -e "${GREEN}[INFO]${NC} Log file: $CELERY_LOG"
    
    # Start worker in background
    celery -A skyeye worker \
        --concurrency="$WORKER_COUNT" \
        --loglevel=INFO \
        --without-gossip \
        --without-heartbeat \
        --without-mingle \
        --max-tasks-per-child=20 \
        --task-events \
        --pidfile="$CELERY_PID" \
        --logfile="$CELERY_LOG" \
        --detach
    
    echo -e "${GREEN}[SUCCESS]${NC} Celery worker started in background"
    echo -e "${GREEN}[INFO]${NC} View logs: ./manage_celery_k3s.sh logs"
}

stop_worker() {
    echo -e "${YELLOW}[INFO]${NC} Stopping Celery worker..."
    
    # 直接使用强力清理，在容器环境中更可靠
    echo -e "${YELLOW}[INFO]${NC} Force stopping all worker processes..."
    
    # 清理PID文件
    [[ -f "$CELERY_PID" ]] && rm -f "$CELERY_PID"
    
    # 强力终止所有相关进程
    pkill -TERM -f "celery.*skyeye.*worker" 2>/dev/null || true
    sleep 3
    pkill -KILL -f "celery.*skyeye.*worker" 2>/dev/null || true
    
    # 等待进程完全终止
    local count=0
    while [[ $count -lt 5 ]] && pgrep -f "celery.*skyeye.*worker" > /dev/null; do
        echo -e "${YELLOW}[INFO]${NC} Waiting for worker processes to terminate..."
        sleep 1
        ((count++))
    done
    
    # 最终状态检查
    local remaining=$(pgrep -f "celery.*skyeye.*worker" | wc -l)
    if [[ $remaining -eq 0 ]]; then
        echo -e "${GREEN}[SUCCESS]${NC} All worker processes stopped"
    else
        echo -e "${RED}[WARNING]${NC} $remaining worker processes may still be running"
    fi
}

stop_beat() {
    echo -e "${YELLOW}[INFO]${NC} Stopping Celery beat..."
    
    # Stop beat process
    if [[ -f "$CELERY_BEAT_PID" ]]; then
        local pid
        pid=$(cat "$CELERY_BEAT_PID" 2>/dev/null || echo "")
        if [[ -n "$pid" ]] && kill -TERM "$pid" 2>/dev/null; then
            echo -e "${GREEN}[INFO]${NC} Sent SIGTERM to beat PID $pid"
            sleep 2
        fi
        rm -f "$CELERY_BEAT_PID"
    fi
    
    # Force stop beat processes - use pkill instead of killall
    pkill -TERM -f "celery.*skyeye.*beat" 2>/dev/null || true
    sleep 1
    pkill -KILL -f "celery.*skyeye.*beat" 2>/dev/null || true
    
    echo -e "${GREEN}[SUCCESS]${NC} Beat stop completed"
}

start_all() {
    echo -e "${GREEN}[INFO]${NC} Starting all Celery services..."
    
    # Start worker first
    start_worker_bg
    
    # Wait a moment for worker to initialize
    sleep 2
    
    # Start beat
    echo -e "${GREEN}[INFO]${NC} Starting Celery Beat..."
    start_beat_bg
    
    echo -e "${GREEN}[SUCCESS]${NC} All Celery services started"
    echo -e "${GREEN}[INFO]${NC} Use './manage_celery_k3s.sh status' to check status"
    echo -e "${GREEN}[INFO]${NC} Use './manage_celery_k3s.sh logs' to view logs"
}

stop_all() {
    echo -e "${YELLOW}[INFO]${NC} Stopping all Celery services..."
    stop_worker
    stop_beat
    echo -e "${GREEN}[SUCCESS]${NC} All Celery services stopped"
}

restart_all() {
    echo -e "${GREEN}[INFO]${NC} Restarting all Celery services..."
    stop_all
    sleep 3
    start_all
    echo -e "${GREEN}[SUCCESS]${NC} All Celery services restarted"
}

# --- Beat Functions ---

start_beat_bg() {
    echo -e "${GREEN}[INFO]${NC} Starting Celery Beat in background..."
    echo -e "${GREEN}[INFO]${NC} Log file: $CELERY_BEAT_LOG"
    
    celery -A skyeye beat \
        --loglevel=INFO \
        --scheduler=django_celery_beat.schedulers:DatabaseScheduler \
        --pidfile="$CELERY_BEAT_PID" \
        --logfile="$CELERY_BEAT_LOG" \
        --detach
    
    echo -e "${GREEN}[SUCCESS]${NC} Celery Beat started in background"
}

# --- Monitoring Functions ---
check_status() {
    local worker_running=false
    local beat_running=false
    
    # 检查worker进程
    local worker_count=$(pgrep -f "celery.*skyeye.*worker" | wc -l)
    if [[ $worker_count -gt 0 ]]; then
        echo -e "${GREEN}[STATUS]${NC} Celery worker: RUNNING ($worker_count processes)"
        worker_running=true
        
        # 如果进程数异常，给出警告
        if [[ $worker_count -gt 3 ]]; then
            echo -e "${RED}[WARNING]${NC} Too many worker processes detected! Expected: 3 (1 main + 2 workers), Found: $worker_count"
            echo -e "${YELLOW}[SUGGESTION]${NC} Consider running: ./manage_celery_k3s.sh restart"
        fi
    else
        echo -e "${RED}[STATUS]${NC} Celery worker: STOPPED"
    fi
    
    # 检查beat进程
    if pgrep -f "celery.*skyeye.*beat" > /dev/null; then
        echo -e "${GREEN}[STATUS]${NC} Celery beat: RUNNING"
        beat_running=true
    else
        echo -e "${RED}[STATUS]${NC} Celery beat: STOPPED"
    fi
    
    echo ""
    echo -e "${GREEN}[INFO]${NC} Detailed worker status:"
    celery -A skyeye status 2>/dev/null || echo "No workers available"
    
    return $($worker_running || $beat_running)
}

view_logs() {
    if [[ -f "$CELERY_LOG" ]]; then
        echo -e "${GREEN}[INFO]${NC} Recent worker logs:"
        tail -n 50 "$CELERY_LOG"
    else
        echo -e "${YELLOW}[WARNING]${NC} Worker log file not found: $CELERY_LOG"
    fi
}

# --- Utility Functions ---
init_tasks() {
    echo -e "${GREEN}[INFO]${NC} Initializing scheduled tasks..."
    python3 manage.py initialize_beat_tasks
    echo -e "${GREEN}[SUCCESS]${NC} Scheduled tasks initialized"
}


# --- Main Script ---
main() {
    # Setup environment
    setup_environment
    
    # Check arguments
    if [[ $# -eq 0 ]]; then
        show_help
        exit 1
    fi
    
    # Execute command
    case "$1" in
        start)
            start_all
            ;;
        stop)
            stop_all
            ;;
        restart)
            restart_all
            ;;
        status)
            check_status
            ;;
        init-tasks)
            init_tasks
            ;;
        logs)
            view_logs
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            echo -e "${RED}[ERROR]${NC} Unknown command: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# Execute main function
main "$@"