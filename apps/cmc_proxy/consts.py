import os
from django.conf import settings

# CoinMarketCap API 配置
COINMARKETCAP_API_KEY = getattr(settings, 'COINMARKETCAP_API_KEY', os.environ.get('COINMARKETCAP_API_KEY', ''))
CMC_N1 = 200  # 获取的"主要热门代币"数量
CMC_TTL_HOT = 600  # 获取的"主要热门代币"在Redis中的缓存时间（秒）
CMC_T1_MERGE_WINDOW_SECONDS = 1  # 合并用户请求的最大等待时间窗口（秒）
CMC_N2_BATCH_TARGET_SIZE = 100  # 批量查询的目标代币数量
CMC_N3_SUPPLEMENT_POOL_RANGE = 200  # "次热门补充池"的代币数量
CMC_TTL_WARM_COLD = 600  # 获取的代币在Redis中的缓存时间（秒）
CMC_TTL_BASE = 3600  # 每日全量更新的代币在Redis中的基础缓存时间（秒）
CMC_MARKET_DATA_TTL = 600  # 市场数据缓存时间（秒） - 10分钟
CMC_PRICE_FALLBACK_WARNING_THRESHOLD = 900  # CMC价格回退警告阈值（秒） - 15分钟
CCXT_PRICE_STALE_THRESHOLD = 300  # CCXT价格过期阈值（秒） - 5分钟
CMC_DAILY_FULL_SYNC_SCHEDULE = "0 3 * * *"  # 每日全量更新任务的执行时间（Cron格式）

# CoinMarketCap Redis 键名模式
CMC_QUOTE_DATA_KEY = "cmc:quote_data:%(symbol_id)s"
CMC_SUPPLEMENT_POOL_KEY = "cmc:supplement_pool_by_marketcap"
CMC_BATCH_REQUESTS_PENDING_KEY = "cmc:batch_requests_pending"  # Key for Redis list storing pending requests
CMC_BATCH_PROCESSING_LOCK_KEY = "cmc:lock:batch_processing"  # Lock for the batch processing task
