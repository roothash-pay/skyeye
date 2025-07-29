#!/bin/bash

# Beat健康监控脚本 - 生产环境紧急修复
set -euo pipefail

# 检查依赖
if ! command -v jq &> /dev/null; then
    echo "错误: 需要安装jq来解析JSON响应"
    echo "请运行: apt-get install jq 或 yum install jq"
    exit 1
fi

# 配置
BEAT_LOG="/tmp/celery-beat.log"
HEALTH_CHECK_INTERVAL=60  # 检查间隔（秒）
MAX_IDLE_TIME=300        # 最大空闲时间（5分钟）
RESTART_SCRIPT="/app/skyeye/scripts/k3s/restart_celery.sh"
API_HEALTH_URL="http://localhost:8201/api/v1/beat/health"

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
    
    # 修复时间解析：处理Celery日志的时间格式 "2025-07-27 16:33:33,493:"
    # 移除毫秒和冒号，转换为标准格式
    local cleaned_time=$(echo "$last_activity" | sed 's/,.*$//' | sed 's/:$//')
    local last_timestamp=$(date -d "$cleaned_time" +%s 2>/dev/null)
    local current_timestamp=$(date +%s)
    
    # 如果时间解析失败，使用当前时间（表示刚刚活跃）
    if [[ -z "$last_timestamp" || "$last_timestamp" == "0" ]]; then
        log "时间解析失败，假设Beat刚刚活跃"
        local idle_time=0
    else
        local idle_time=$((current_timestamp - last_timestamp))
    fi
    
    log "Beat最后活动: $last_activity (空闲时间: ${idle_time}秒)"
    
    if [[ $idle_time -gt $MAX_IDLE_TIME ]]; then
        error "Beat调度器已空闲 ${idle_time} 秒，超过阈值 ${MAX_IDLE_TIME} 秒"
        return 1
    fi
    
    return 0
}

# 检查关键任务是否在调度
check_critical_tasks() {
    local recent_price_tasks=$(tail -50 "$BEAT_LOG" | grep -E "(collect_prices|persist_prices)" | wc -l)
    local recent_kline_tasks=$(tail -50 "$BEAT_LOG" | grep -E "update_cmc_klines" | wc -l)
    
    local errors=0
    
    if [[ $recent_price_tasks -eq 0 ]]; then
        error "最近50行日志中未发现关键价格任务调度"
        errors=$((errors + 1))
    fi
    
    if [[ $recent_kline_tasks -eq 0 ]]; then
        warn "最近50行日志中未发现K线任务调度（每小时15分执行一次）"
        # K线任务不算致命错误，因为执行频率较低
    fi
    
    if [[ $errors -gt 0 ]]; then
        return 1
    fi
    
    log "发现 $recent_price_tasks 个价格任务调度记录，$recent_kline_tasks 个K线任务调度记录"
    return 0
}

# 检查数据更新情况（基于API返回的数据新鲜度）
check_data_freshness() {
    if [[ -f "/tmp/beat_health.json" ]]; then
        # 检查各类数据的新鲜度
        local stale_count=$(jq -r '.data_freshness | to_entries[] | select(.value.status == "stale") | .key' /tmp/beat_health.json 2>/dev/null | wc -l)
        local no_data_count=$(jq -r '.data_freshness | to_entries[] | select(.value.status == "no_data") | .key' /tmp/beat_health.json 2>/dev/null | wc -l)
        
        if [[ $stale_count -eq 0 && $no_data_count -eq 0 ]]; then
            log "✅ 所有数据源都是新鲜的"
            return 0
        elif [[ $no_data_count -gt 0 ]]; then
            error "❌ 发现无数据的数据源，任务可能从未执行成功"
            return 1
        else
            warn "⚠️  发现 $stale_count 个数据源过期，任务可能执行缓慢或失败"
            return 1
        fi
    else
        warn "无法获取数据新鲜度信息"
        return 1
    fi
}

# 检查队列积压情况
check_queue_backlog() {
    if [[ -f "/tmp/beat_health.json" ]]; then
        # 检查队列长度
        local high_backlog=$(jq -r '.execution_stats.queue_lengths | to_entries[] | select(.value > 100) | .key' /tmp/beat_health.json 2>/dev/null | tr '\n' ' ')
        
        if [[ -n "$high_backlog" ]]; then
            warn "⚠️  发现队列积压: $high_backlog"
            return 1
        else
            log "✅ 所有队列积压正常"
            return 0
        fi
    else
        warn "无法获取队列积压信息"
        return 1
    fi
}

# 检查API健康状态（增强版）
check_api_health() {
    local response
    local status_code
    
    if response=$(curl -s -w "%{http_code}" "$API_HEALTH_URL" -o /tmp/beat_health.json --max-time 10); then
        status_code="${response: -3}"
        
        if [[ "$status_code" == "200" ]]; then
            # 解析API返回的详细状态
            local api_status=$(jq -r '.status // "unknown"' /tmp/beat_health.json 2>/dev/null || echo "unknown")
            local stale_data=$(jq -r '.data_freshness | to_entries[] | select(.value.status == "stale") | .key' /tmp/beat_health.json 2>/dev/null | tr '\n' ' ')
            
            if [[ "$api_status" == "healthy" ]]; then
                log "✅ Beat API健康检查通过"
                return 0
            elif [[ "$api_status" == "warning" ]]; then
                warn "⚠️  Beat API状态警告，可能有数据延迟: $stale_data"
                return 1
            else
                error "Beat API状态异常: $api_status"
                return 1
            fi
        else
            error "Beat API返回错误状态码: $status_code"
            return 1
        fi
    else
        error "无法连接到Beat健康检查API"
        return 1
    fi
}

# 重启Beat服务
restart_beat() {
    error "🚨 检测到Beat调度器异常，执行紧急重启..."
    
    # 记录重启事件
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] EMERGENCY RESTART: Beat scheduler health check failed" >> /tmp/beat-restart.log
    
    # 执行重启
    if "$RESTART_SCRIPT"; then
        log "✅ Beat服务重启成功"
        
        # 等待服务稳定
        sleep 30
        
        # 验证重启后状态
        if check_api_health && check_beat_health && check_critical_tasks; then
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
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ALERT: $message" >> /tmp/alerts.log
    
    # 这里可以添加更多告警方式：
    # - 发送邮件
    # - 推送到监控系统
    # - 调用Webhook
    
    warn "告警: $message"
}

# 主循环
main() {
    log "🔍 Beat健康监控启动 (检查间隔: ${HEALTH_CHECK_INTERVAL}s, 最大空闲: ${MAX_IDLE_TIME}s)"
    log "📊 监控API: $API_HEALTH_URL"
    log "📝 Beat日志: $BEAT_LOG"
    log "🔄 重启脚本: $RESTART_SCRIPT"
    
    while true; do
        local beat_healthy=true
        local kline_healthy=true
        
        # 综合检查：基础健康 + API健康 + 数据新鲜度 + 队列状态
        local basic_healthy=true
        local api_healthy=true
        local data_healthy=true
        local queue_healthy=true
        
        # 基础检查（Beat日志和关键任务）
        if ! check_beat_health || ! check_critical_tasks; then
            basic_healthy=false
        fi
        
        # API增强检查
        if ! check_api_health; then
            api_healthy=false
        fi
        
        # 数据新鲜度检查
        if ! check_data_freshness; then
            data_healthy=false
        fi
        
        # 队列积压检查
        if ! check_queue_backlog; then
            queue_healthy=false
        fi
        
        # 综合判断健康状态
        if $basic_healthy && $api_healthy && $data_healthy && $queue_healthy; then
            log "✅ 所有监控项目正常（调度器、API、数据、队列）"
        elif ! $basic_healthy || ! $api_healthy; then
            send_alert "Beat调度器或API异常检测"
            
            if restart_beat; then
                send_alert "Beat调度器已自动恢复"
            else
                send_alert "Beat调度器自动恢复失败，需要人工介入"
            fi
        elif ! $data_healthy; then
            send_alert "数据更新异常，任务可能执行失败或缓慢"
            # 数据异常不自动重启，需要人工分析
        elif ! $queue_healthy; then
            send_alert "队列积压异常，可能需要增加Worker或优化任务"
            # 队列积压不自动重启，需要人工处理
        else
            warn "⚠️  部分监控项目异常，但核心功能正常"
        fi
        
        sleep $HEALTH_CHECK_INTERVAL
    done
}

# 信号处理
trap 'log "收到退出信号，停止监控..."; exit 0' SIGTERM SIGINT

# 启动监控
main "$@"