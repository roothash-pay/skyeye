#!/bin/bash

# Celery服务重启脚本
# 用法: 
#   ./restart_celery_only.sh              # 仅重启Celery（保持监控）
#   ./restart_celery_only.sh --with-monitor # 重启Celery并启动监控

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date '+%H:%M:%S')] ERROR${NC} $1"
}

log "🔄 重启Celery服务（保持监控运行）..."

# 解析参数
WITH_MONITOR=false
if [[ "${1:-}" == "--with-monitor" ]]; then
    WITH_MONITOR=true
    log "🔄 重启Celery服务（包含监控）..."
    
    # 停止监控脚本
    log "停止监控脚本..."
    pkill -f "monitor_beat_health.sh" || true
else
    log "🔄 重启Celery服务（保持监控运行）..."
fi

# 1. 停止所有celery进程
log "停止Celery进程..."
pkill -f "celery.*skyeye" || true
sleep 3
pkill -9 -f "celery.*skyeye" || true

# 2. 清理PID文件
log "清理PID文件..."
rm -f /tmp/celery-*.pid

# 3. 切换到工作目录
cd /app

# 4. 重新初始化Beat任务
log "初始化Beat定时任务..."
python3 manage.py initialize_beat_tasks

# 5. 启动所有服务
log "启动Price队列Worker..."
celery -A skyeye worker --pool=solo --queues=price --loglevel=INFO --detach --pidfile=/tmp/celery-price.pid --logfile=/tmp/celery-price.log

log "启动默认队列Worker..."
celery -A skyeye worker --pool=solo --queues=celery --loglevel=INFO --detach --pidfile=/tmp/celery-default.pid --logfile=/tmp/celery-default.log

log "启动Beat调度器..."
celery -A skyeye beat --loglevel=INFO --detach --pidfile=/tmp/celery-beat.pid --logfile=/tmp/celery-beat.log

# 6. 等待服务稳定
sleep 5

# 7. 简单验证
# 8. 启动监控（如果需要）
if $WITH_MONITOR; then
    log "🔍 启动监控进程..."
    
    # 检查是否在K8s环境
    if [[ -n "${KUBERNETES_SERVICE_HOST:-}" ]]; then
        log "⚠️  在K8s环境中，监控应该由启动脚本自动启动"
    else
        nohup /app/skyeye/scripts/k3s/monitor_beat_health.sh > /tmp/beat-monitor.log 2>&1 &
        sleep 2
        
        if pgrep -f "monitor_beat_health.sh" > /dev/null; then
            log "✅ 监控进程启动成功"
        else
            error "❌ 监控进程启动失败"
        fi
    fi
fi

# 9. 验证结果
local_count=$(ps aux | grep 'celery.*skyeye' | grep -v grep | wc -l)
if [[ $local_count -ge 3 ]]; then
    log "✅ Celery服务重启成功 ($local_count 个进程)"
    
    # 显示使用说明
    echo
    echo "📋 使用说明:"
    echo "  - 查看Beat日志: tail -f /tmp/celery-beat.log"
    echo "  - 查看监控日志: tail -f /tmp/beat-monitor.log"
    echo "  - 检查健康状态: curl http://localhost:8201/api/v1/beat/health | python3 -m json.tool"
    echo "  - 检查监控状态: ps aux | grep monitor_beat_health"
    
    exit 0
else
    error "❌ Celery服务重启失败 (只有 $local_count 个进程)"
    exit 1
fi
