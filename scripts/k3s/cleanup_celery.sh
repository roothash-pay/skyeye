#!/bin/bash

# Celery 进程清理脚本
# 用于容器启动前彻底清理所有残留的 Celery 进程

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}[CLEANUP]${NC} Starting Celery process cleanup..."

# 检查当前进程数
current_count=$(pgrep -f "celery" 2>/dev/null | wc -l || echo "0")
echo -e "${GREEN}[INFO]${NC} Found $current_count Celery processes"

if [[ $current_count -eq 0 ]]; then
    echo -e "${GREEN}[SUCCESS]${NC} No Celery processes to clean up"
    exit 0
fi

# 强力清理所有 Celery 进程
echo -e "${YELLOW}[CLEANUP]${NC} Terminating all Celery processes..."
pkill -TERM -f "celery" 2>/dev/null || true
sleep 3

# 检查是否还有残留
remaining=$(pgrep -f "celery" 2>/dev/null | wc -l || echo "0")
if [[ $remaining -gt 0 ]]; then
    echo -e "${YELLOW}[CLEANUP]${NC} Force killing remaining $remaining processes..."
    pkill -KILL -f "celery" 2>/dev/null || true
    sleep 2
fi

# 清理PID文件
echo -e "${YELLOW}[CLEANUP]${NC} Cleaning up PID files..."
rm -f ./logs/celery*.pid 2>/dev/null || true

# 最终检查
final_count=$(pgrep -f "celery" 2>/dev/null | wc -l || echo "0")
if [[ $final_count -eq 0 ]]; then
    echo -e "${GREEN}[SUCCESS]${NC} All Celery processes cleaned up successfully"
else
    echo -e "${RED}[ERROR]${NC} $final_count processes still running!"
    echo -e "${YELLOW}[INFO]${NC} Remaining processes:"
    ps aux | grep celery | grep -v grep || true
    exit 1
fi

echo -e "${GREEN}[CLEANUP]${NC} Cleanup completed"