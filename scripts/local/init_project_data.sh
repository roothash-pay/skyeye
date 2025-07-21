#!/bin/bash

# SkyEye项目数据初始化脚本
# 适用于首次部署时初始化数据库

set -e  # 脚本遇到错误时立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

if [ ! -f "$PROJECT_ROOT/manage.py" ]; then
    log_error "项目根目录不正确，找不到 manage.py 文件"
    exit 1
fi

cd "$PROJECT_ROOT"

log_info "开始 SkyEye 项目数据初始化..."
log_info "项目路径: $PROJECT_ROOT"

# 1. 检查数据库连接
log_info "检查数据库连接..."
if ! uv run python manage.py check --database default; then
    log_error "数据库连接失败，请检查数据库配置"
    exit 1
fi

# 2. 运行数据库迁移
log_info "执行数据库迁移..."
uv run python manage.py migrate

# 3. 初始化 Celery Beat 任务
log_info "初始化 Celery Beat 定时任务..."
if command -v uv run python manage.py initialize_beat_tasks &> /dev/null; then
    uv run python manage.py initialize_beat_tasks
    log_success "Celery Beat 任务初始化完成"
else
    log_warning "未找到 initialize_beat_tasks 命令，跳过"
fi

# 4. 执行 CMC 全量数据同步
log_info "开始执行 CoinMarketCap 全量数据同步..."
log_warning "这个过程可能需要几分钟时间，请耐心等待..."

if uv run python manage.py full_sync_cmc_data; then
    log_success "CMC 全量数据同步完成"
else
    log_error "CMC 全量数据同步失败"
    exit 1
fi

# 5. 初始化 K线数据（可选）
read -p "是否要初始化 K线历史数据？这将为热门代币获取24小时的K线数据 (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "开始初始化 K线历史数据..."
    log_warning "这个过程可能需要较长时间，请耐心等待..."
    
    if uv run python manage.py update_cmc_klines --run-once --initialize --count=24 --top-n=500; then
        log_success "K线历史数据初始化完成"
    else
        log_warning "K线历史数据初始化失败，但不影响主要功能"
    fi
else
    log_info "跳过 K线历史数据初始化"
fi

# 6. 检查数据状态
log_info "检查数据初始化状态..."

ASSET_COUNT=$(uv run python manage.py shell -c "from apps.cmc_proxy.models import CmcAsset; print(CmcAsset.objects.count())" 2>/dev/null | tail -n 1)
MARKET_DATA_COUNT=$(uv run python manage.py shell -c "from apps.cmc_proxy.models import CmcMarketData; print(CmcMarketData.objects.count())" 2>/dev/null | tail -n 1)
KLINE_COUNT=$(uv run python manage.py shell -c "from apps.cmc_proxy.models import CmcKline; print(CmcKline.objects.count())" 2>/dev/null | tail -n 1)

log_success "数据初始化完成！"
echo
echo "======== 数据统计 ========"
echo "代币资产数量: $ASSET_COUNT"
echo "市场数据数量: $MARKET_DATA_COUNT"  
echo "K线数据数量: $KLINE_COUNT"
echo "=========================="
echo

log_info "初始化完成！你现在可以："
echo "1. 启动开发服务器: uv run python manage.py runserver"
echo "2. 启动 Celery 服务: ./scripts/local/manage_celery.sh start"
echo "3. 测试 API 接口: curl http://localhost:8000/api/v1/cmc/market-data?cmc_id=1"
echo

log_success "SkyEye 项目数据初始化完成！"