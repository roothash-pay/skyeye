#!/bin/bash

# Beat健康监控脚本 - 生产环境紧急修复
set -euo pipefail

# 配置
BEAT_LOG="/app/logs/celery-beat.log"
HEALTH_CHECK_INTERVAL=60  # 检查间隔（秒）
MAX_IDLE_TIME=300        # 最大空闲时间（5分钟）
RESTART_SCRIPT="/app/skyeye/scripts/k3s/manage_celery_k3s.sh"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# 检查Beat是否健康
check_beat_health() {
    if [[ ! -f "$BEAT_LOG" ]]; then
        error "Beat日志文件不存在: $BEAT_LOG"
        return 1
    fi
    
    # 获取最后一行调度任务的时间戳
    local last_activity=$(grep "Scheduler: Sending due task" "$BEAT_LOG" | tail -1 | cut -d' ' -f1-2 | tr -d '[]' || echo "")
    
    if [[ -z "$last_activity" ]]; then
        error "无法获取Beat最后活动时间"
        return 1
    fi
    
    # 转换时间戳
    local last_timestamp=$(date -d "$last_activity" +%s 2>/dev/null || echo "0")
    local current_timestamp=$(date +%s)
    local idle_time=$((current_timestamp - last_timestamp))
    
    log "Beat最后活动: $last_activity (空闲时间: ${idle_time}秒)"
    
    if [[ $idle_time -gt $MAX_IDLE_TIME ]]; then
        error "Beat调度器已空闲 ${idle_time} 秒，超过阈值 ${MAX_IDLE_TIME} 秒"
        return 1
    fi
    
    return 0
}

# 检查关键任务是否在调度
check_critical_tasks() {
    local recent_tasks=$(tail -50 "$BEAT_LOG" | grep -E "(collect_prices|persist_prices)" | wc -l)
    
    if [[ $recent_tasks -eq 0 ]]; then
        error "最近50行日志中未发现关键价格任务调度"
        return 1
    fi
    
    log "发现 $recent_tasks 个关键任务调度记录"
    return 0
}

# 重启Beat服务
restart_beat() {
    error "🚨 检测到Beat调度器异常，执行紧急重启..."
    
    # 记录重启事件
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] EMERGENCY RESTART: Beat scheduler health check failed" >> /app/logs/beat-restart.log
    
    # 执行重启
    if "$RESTART_SCRIPT" restart; then
        log "✅ Beat服务重启成功"
        
        # 等待服务稳定
        sleep 30
        
        # 验证重启后状态
        if check_beat_health && check_critical_tasks; then
            log "✅ 重启后Beat服务运行正常"
            return 0
        else
            error "❌ 重启后Beat服务仍有问题"
            return 1
        fi
    else
        error "❌ Beat服务重启失败"
        return 1
    fi
}

# 发送告警（可扩展）
send_alert() {
    local message="$1"
    
    # 记录到告警日志
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ALERT: $message" >> /app/logs/alerts.log
    
    # 这里可以添加更多告警方式：
    # - 发送邮件
    # - 推送到监控系统
    # - 调用Webhook
    
    warn "告警: $message"
}

# 主循环
main() {
    log "🔍 Beat健康监控启动 (检查间隔: ${HEALTH_CHECK_INTERVAL}s, 最大空闲: ${MAX_IDLE_TIME}s)"
    
    while true; do
        if check_beat_health && check_critical_tasks; then
            log "✅ Beat调度器运行正常"
        else
            send_alert "Beat调度器异常检测"
            
            if restart_beat; then
                send_alert "Beat调度器已自动恢复"
            else
                send_alert "Beat调度器自动恢复失败，需要人工介入"
                # 可以选择退出或继续监控
            fi
        fi
        
        sleep $HEALTH_CHECK_INTERVAL
    done
}

# 信号处理
trap 'log "收到退出信号，停止监控..."; exit 0' SIGTERM SIGINT

# 启动监控
main "$@"