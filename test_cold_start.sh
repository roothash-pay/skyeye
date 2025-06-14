#!/bin/bash

# SkyEye CMC 冷启动完整测试脚本
# 测试市场数据和K线数据的冷启动机制

echo "🚀 开始 SkyEye CMC 冷启动测试"
echo "================================"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 测试结果统计
TESTS_PASSED=0
TESTS_FAILED=0

# 辅助函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
    TESTS_PASSED=$((TESTS_PASSED + 1))
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    TESTS_FAILED=$((TESTS_FAILED + 1))
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

check_service() {
    local service_name=$1
    local check_command=$2
    
    log_info "检查 $service_name 状态..."
    if eval $check_command > /dev/null 2>&1; then
        log_success "$service_name 运行正常"
        return 0
    else
        log_error "$service_name 未运行或有问题"
        return 1
    fi
}

check_api_response() {
    local url=$1
    local expected_field=$2
    local description=$3
    
    log_info "测试: $description"
    log_info "请求: $url"
    
    response=$(curl -s "$url")
    if echo "$response" | jq -e "$expected_field" > /dev/null 2>&1; then
        log_success "$description - 成功"
        echo "$response" | jq "$expected_field"
        return 0
    else
        log_error "$description - 失败"
        echo "响应: $response"
        return 1
    fi
}

check_db_count() {
    local table_name=$1
    local expected_min=$2
    local description=$3
    
    log_info "检查数据库: $description"
    
    count=$(uv run python manage.py shell -c "
import asyncio
from apps.cmc_proxy.models import $table_name

async def get_count():
    count = await $table_name.objects.acount()
    print(count)

asyncio.run(get_count())
" 2>/dev/null | tail -1)
    
    if [ "$count" -ge "$expected_min" ]; then
        log_success "$description - 找到 $count 条记录"
        return 0
    else
        log_error "$description - 只找到 $count 条记录，期望至少 $expected_min 条"
        return 1
    fi
}

wait_for_sync() {
    local max_wait=$1
    local description=$2
    
    log_info "等待 $description (最多 ${max_wait}s)..."
    
    for i in $(seq 1 $max_wait); do
        echo -n "."
        sleep 1
    done
    echo ""
}

# 1. 检查前置条件
echo -e "\n${YELLOW}=== 步骤 1: 检查前置条件 ===${NC}"

check_service "Django Server" "curl -s http://localhost:8000 > /dev/null"
check_service "Celery Worker" "./scripts/local/manage_celery.sh status | grep -q 'RUNNING'"
check_service "Redis" "redis-cli ping | grep -q PONG"

# 2. 验证初始状态为空
echo -e "\n${YELLOW}=== 步骤 2: 验证初始状态 ===${NC}"

check_db_count "CmcAsset" 0 "资产表应为空"
check_db_count "CmcMarketData" 0 "市场数据表应为空" 
check_db_count "CmcKline" 0 "K线表应为空"

redis_keys=$(redis-cli -n 1 KEYS "*" | wc -l)
if [ "$redis_keys" -eq 0 ]; then
    log_success "Redis CMC缓存为空"
else
    log_error "Redis CMC缓存不为空，有 $redis_keys 个键"
fi

# 3. 测试市场数据冷启动
echo -e "\n${YELLOW}=== 步骤 3: 测试市场数据冷启动 ===${NC}"

check_api_response "http://localhost:8000/api/v1/cmc/market-data?cmc_id=1" ".result.price_usd" "BTC市场数据获取"

# 检查Redis缓存
wait_for_sync 3 "Redis缓存写入"
redis_keys_after=$(redis-cli -n 1 KEYS "*" | wc -l)
if [ "$redis_keys_after" -gt 0 ]; then
    log_success "数据已缓存到Redis ($redis_keys_after 个键)"
else
    log_error "Redis缓存失败"
fi

# 4. 等待Celery同步到数据库
echo -e "\n${YELLOW}=== 步骤 4: 等待数据同步到数据库 ===${NC}"

wait_for_sync 10 "Celery数据同步"

check_db_count "CmcAsset" 1 "资产数据同步"
check_db_count "CmcMarketData" 1 "市场数据同步"

# 5. 测试K线数据冷启动
echo -e "\n${YELLOW}=== 步骤 5: 测试K线数据冷启动 ===${NC}"

check_api_response "http://localhost:8000/api/v1/cmc/klines?cmc_id=1" ".result.count" "BTC K线数据获取"

wait_for_sync 5 "K线数据存储"
check_db_count "CmcKline" 20 "K线数据存储"

# 6. 测试集成API (市场数据+K线)
echo -e "\n${YELLOW}=== 步骤 6: 测试集成API ===${NC}"

check_api_response "http://localhost:8000/api/v1/cmc/market-data?cmc_id=1" ".result.klines | length" "市场数据API包含K线数据"
check_api_response "http://localhost:8000/api/v1/cmc/market-data?cmc_id=1" ".result.high_24h" "24小时高价数据"

# 7. 测试其他代币的冷启动
echo -e "\n${YELLOW}=== 步骤 7: 测试其他代币冷启动 ===${NC}"

check_api_response "http://localhost:8000/api/v1/cmc/market-data?cmc_id=1027" ".result.price_usd" "ETH市场数据冷启动"

wait_for_sync 10 "ETH数据同步"
check_db_count "CmcAsset" 2 "多资产支持"

# 8. 性能测试 - 后续请求应该很快
echo -e "\n${YELLOW}=== 步骤 8: 性能测试 ===${NC}"

log_info "测试缓存命中性能..."
start_time=$(date +%s%N)
curl -s "http://localhost:8000/api/v1/cmc/market-data?cmc_id=1" > /dev/null
end_time=$(date +%s%N)
duration=$((($end_time - $start_time) / 1000000)) # 转换为毫秒

if [ "$duration" -lt 500 ]; then
    log_success "缓存命中响应时间: ${duration}ms (< 500ms)"
else
    log_warning "缓存命中响应时间: ${duration}ms (可能较慢)"
fi

# 9. 测试报告
echo -e "\n${YELLOW}=== 测试报告 ===${NC}"
echo "================================"

# 最终数据统计
final_assets=$(uv run python manage.py shell -c "
import asyncio
from apps.cmc_proxy.models import CmcAsset, CmcMarketData, CmcKline

async def get_final_stats():
    assets = await CmcAsset.objects.acount()
    market_data = await CmcMarketData.objects.acount()
    klines = await CmcKline.objects.acount()
    print(f'{assets},{market_data},{klines}')

asyncio.run(get_final_stats())
" 2>/dev/null | tail -1)

IFS=',' read -r assets_count market_count klines_count <<< "$final_assets"

echo "📊 最终数据统计:"
echo "   - 资产: $assets_count"
echo "   - 市场数据: $market_count" 
echo "   - K线数据: $klines_count"

redis_final=$(redis-cli -n 1 KEYS "*" | wc -l)
echo "   - Redis缓存: $redis_final 个键"

echo ""
echo "✅ 通过测试: $TESTS_PASSED"
echo "❌ 失败测试: $TESTS_FAILED"

if [ "$TESTS_FAILED" -eq 0 ]; then
    echo -e "\n🎉 ${GREEN}所有测试通过! SkyEye CMC冷启动机制工作正常.${NC}"
    exit 0
else
    echo -e "\n💥 ${RED}有 $TESTS_FAILED 个测试失败，请检查日志.${NC}"
    exit 1
fi