#!/bin/bash

# K8s Pod中的Celery状态检查脚本
set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 日志函数
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING${NC} $1"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR${NC} $1"
}

info() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] INFO${NC} $1"
}

section() {
    echo
    echo -e "${BLUE}======================================${NC}"
    echo -e "${BLUE} $1 ${NC}"
    echo -e "${BLUE}======================================${NC}"
}

# 检查进程状态
check_processes() {
    section "1. Celery进程状态检查"
    
    info "查找所有Celery进程:"
    if ps aux | grep -E "(celery|skyeye)" | grep -v grep; then
        log "✅ 找到Celery相关进程"
    else
        error "❌ 未找到Celery相关进程"
    fi
    
    echo
    info "分别检查各个组件:"
    
    # Beat进程
    local beat_count=$(ps aux | grep "celery.*beat" | grep -v grep | wc -l)
    if [[ $beat_count -eq 0 ]]; then
        error "❌ Beat调度器未运行"
    else
        log "✅ Beat调度器运行中 ($beat_count个进程)"
    fi
    
    # Worker进程
    local worker_count=$(ps aux | grep "celery.*worker" | grep -v grep | wc -l)
    if [[ $worker_count -eq 0 ]]; then
        error "❌ Worker未运行"
    else
        log "✅ Worker运行中 ($worker_count个进程)"
    fi
    
    # Django服务器
    local django_count=$(ps aux | grep "manage.py.*runserver" | grep -v grep | wc -l)
    if [[ $django_count -eq 0 ]]; then
        warn "⚠️  Django服务器可能未运行"
    else
        log "✅ Django服务器运行中"
    fi
}

# 检查PID文件
check_pid_files() {
    section "2. PID文件检查"
    
    info "查找PID文件:"
    find /tmp -name "celery-*.pid" -exec ls -la {} \; 2>/dev/null || echo "未找到PID文件"
    
    echo
    info "验证PID文件有效性:"
    for pid_file in /tmp/celery-*.pid; do
        if [[ -f "$pid_file" ]]; then
            local pid=$(cat "$pid_file" 2>/dev/null || echo "")
            if [[ -n "$pid" ]]; then
                if ps -p "$pid" > /dev/null 2>&1; then
                    log "✅ $(basename "$pid_file"): PID $pid 有效"
                else
                    error "❌ $(basename "$pid_file"): PID $pid 无效（进程已死）"
                fi
            else
                warn "⚠️  $(basename "$pid_file"): 无法读取PID"
            fi
        fi
    done
}

# 检查日志文件
check_log_files() {
    section "3. 日志文件检查"
    
    info "查找Celery日志文件:"
    find /tmp -name "celery-*.log" -exec ls -la {} \; 2>/dev/null || echo "未找到日志文件"
    
    echo
    info "Beat日志内容检查:"
    local beat_log="/tmp/celery-beat.log"
    if [[ -f "$beat_log" ]]; then
        log "✅ Beat日志存在: $beat_log"
        echo "文件大小: $(du -h "$beat_log" | cut -f1)"
        echo "最后修改: $(stat -c %y "$beat_log" 2>/dev/null || stat -f %Sm "$beat_log")"
        
        echo
        info "最近10行Beat日志:"
        tail -10 "$beat_log"
        
        echo
        info "查找错误信息:"
        grep -i "error\|exception\|traceback" "$beat_log" | tail -5 || echo "未找到错误信息"
        
        echo
        info "最近的任务调度:"
        grep "Sending due task" "$beat_log" | tail -5 || echo "未找到任务调度记录"
    else
        error "❌ Beat日志不存在: $beat_log"
    fi
    
    echo
    info "Worker日志检查:"
    for log_file in /tmp/celery-*.log; do
        if [[ -f "$log_file" && "$log_file" != "$beat_log" ]]; then
            echo "$(basename "$log_file"): $(tail -1 "$log_file" 2>/dev/null || echo '无内容')"
        fi
    done
}

# 检查API健康状态
check_api_health() {
    section "4. API健康状态检查"
    
    info "检查Django服务是否响应:"
    if curl -s http://localhost:8201/api/v1/ping > /dev/null; then
        log "✅ Django服务响应正常"
    else
        error "❌ Django服务无响应"
    fi
    
    echo
    info "检查Beat健康API:"
    if curl -s http://localhost:8201/api/v1/beat/health; then
        echo
        log "✅ Beat健康API响应"
    else
        error "❌ Beat健康API无响应"
    fi
}

# 检查数据库连接
check_database() {
    section "5. 数据库连接检查"
    
    cd /app || {
        error "❌ 无法切换到 /app 目录"
        return
    }
    
    info "测试数据库连接:"
    python3 manage.py shell -c "
from django.db import connection
try:
    with connection.cursor() as cursor:
        cursor.execute('SELECT 1')
    print('✅ 数据库连接正常')
except Exception as e:
    print(f'❌ 数据库连接失败: {e}')
"
    
    echo
    info "检查定时任务状态:"
    python3 manage.py shell -c "
from django_celery_beat.models import PeriodicTask
from django.utils import timezone

critical_tasks = ['collect_prices_frequently', 'persist_prices_frequently', 'process_pending_cmc_batch_requests']
for task_name in critical_tasks:
    try:
        task = PeriodicTask.objects.get(name=task_name, enabled=True)
        if task.last_run_at:
            time_since_run = (timezone.now() - task.last_run_at).total_seconds()
            status = '✅ 正常' if time_since_run < 300 else '❌ 超时'
            print(f'{task_name}: {status} (上次运行: {int(time_since_run)}秒前)')
        else:
            print(f'{task_name}: ❌ 从未运行')
    except PeriodicTask.DoesNotExist:
        print(f'{task_name}: ❌ 任务不存在')
"
}

# 主函数
main() {
    log "🔍 开始检查K8s Pod中的Celery状态..."
    
    check_processes
    check_pid_files
    check_log_files
    check_api_health
    check_database
    
    log "🎯 状态检查完成！"
}

# 运行主函数
main "$@"