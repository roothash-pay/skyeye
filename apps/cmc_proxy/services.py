import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

import httpx
from django.conf import settings
from django.utils import timezone
from tenacity import retry, stop_after_attempt, wait_exponential

from apps.cmc_proxy.consts import CMC_N1, CMC_BATCH_PROCESSING_LOCK_KEY, CMC_BATCH_REQUESTS_PENDING_KEY, \
    CMC_T1_MERGE_WINDOW_SECONDS, CMC_QUOTE_DATA_KEY, CMC_TTL_BASE
from apps.cmc_proxy.helpers import KlineDataProcessor
from apps.cmc_proxy.models import CmcAsset, CmcKline, CmcMarketData
from apps.cmc_proxy.utils import CMCRedisClient
from apps.cmc_proxy.utils import acquire_lock, release_lock
from common.helpers import getLogger

logger = getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)


class CoinMarketCapClient:
    BASE_URL = "https://pro-api.coinmarketcap.com"

    def __init__(self, timeout=20):
        self.api_key = settings.COINMARKETCAP_API_KEY
        if not self.api_key:
            logger.error("COINMARKETCAP_API_KEY is not configured in Django settings.")
            raise ValueError("COINMARKETCAP_API_KEY is not configured.")
        self.headers = {
            'X-CMC_PRO_API_KEY': self.api_key,
            'Accept': 'application/json'
        }
        self.timeout = timeout
        self._http_client = httpx.AsyncClient(timeout=self.timeout)

    async def _make_api_request(self, endpoint, params):
        logger.info(f"Calling CoinMarketCap API (async): {endpoint} with params: {params}")
        response = await self._http_client.get(endpoint, headers=self.headers, params=params)
        response.raise_for_status()
        # data = await to_thread(response.json)  # JSON数据量很大的时候使用
        return response.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def get_listings_latest(self, start=1, limit=None):
        endpoint = f"{self.BASE_URL}/v1/cryptocurrency/listings/latest"
        params = {
            'start': start,
            'limit': limit or CMC_N1
        }
        return await self._make_api_request(endpoint, params)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def get_quotes_latest(self, ids=None):
        endpoint = f"{self.BASE_URL}/v2/cryptocurrency/quotes/latest"
        params = {'id': ','.join(map(str, ids))}
        return await self._make_api_request(endpoint, params)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def get_ohlcv_historical(self, coin_ids, count=24):
        endpoint = f"{self.BASE_URL}/v2/cryptocurrency/ohlcv/historical"
        # 支持批量获取多个代币数据
        if isinstance(coin_ids, (list, tuple)):
            ids_param = ','.join(map(str, coin_ids))
        else:
            ids_param = str(coin_ids)

        params = {
            'id': ids_param,
            'time_period': 'hourly',
            'count': count,
            'interval': 'hourly'
        }
        return await self._make_api_request(endpoint, params)

    async def close(self):
        await self._http_client.aclose()


class SingletonMeta(type):
    _instances: Dict[Any, Any] = {}
    _init_lock = asyncio.Lock()

    async def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            async with cls._init_lock:
                if cls not in cls._instances:  # 再次检查，防止重复创建
                    instance = super(SingletonMeta, cls).__call__(*args, **kwargs)
                    if hasattr(instance, "async_init") and callable(instance.async_init):
                        await instance.async_init()
                    cls._instances[cls] = instance
        return cls._instances[cls]


class CoinMarketCapService(metaclass=SingletonMeta):
    def __init__(self, redis_url=None):
        logger.info("Initializing CoinMarketCapService")
        self.redis_url = redis_url or settings.REDIS_CMC_URL
        self._client = None
        self._cmc_redis = None
        self._initialized = False
        self._init_lock = asyncio.Lock()

    @property
    def client(self):
        """懒加载API客户端"""
        if self._client is None:
            self._client = CoinMarketCapClient()
        return self._client

    @property
    def cmc_redis(self) -> CMCRedisClient:
        """获取CMC专用Redis客户端"""
        if not self._initialized:
            raise RuntimeError("CoinMarketCapService not initialized. Call async_init() first.")
        return self._cmc_redis

    async def async_init(self):
        """异步初始化方法"""
        if not self._initialized:
            async with self._init_lock:
                if not self._initialized:  # 双重检查以防止并发初始化
                    logger.info("Async initializing CoinMarketCapService")
                    try:
                        self._cmc_redis = await CMCRedisClient.create(self.redis_url)
                        self._initialized = True
                    except Exception as e:
                        logger.error(f"Failed to initialize CoinMarketCapService: {e}", exc_info=True)
                        # 重置状态以允许重试
                        self._cmc_redis = None
                        self._initialized = False
                        raise

    async def _ensure_initialized(self):
        """确保服务已初始化，如果连接断开则重新初始化"""
        if not self._initialized or self._cmc_redis is None:
            await self.async_init()
        else:
            # 检查Redis连接是否仍然有效
            try:
                await self._cmc_redis.ping()
            except Exception as e:
                logger.warning(f"Redis connection appears to be broken, reinitializing: {e}")
                # 安全地关闭现有连接
                await self._safe_close_redis()
                self._cmc_redis = None
                self._initialized = False
                await self.async_init()

    async def _safe_close_redis(self):
        """安全地关闭Redis连接"""
        if self._cmc_redis:
            try:
                # 尝试关闭连接池
                if hasattr(self._cmc_redis, 'connection_pool') and self._cmc_redis.connection_pool:
                    await self._cmc_redis.connection_pool.aclose()
                # 关闭客户端
                await self._cmc_redis.aclose()
            except Exception as e:
                logger.debug(f"Error closing Redis connection (this is expected): {e}")
                # 不需要重新抛出错误，这在连接已关闭时是正常的

    async def fetch_and_cache_top_n1_listings(self, target_symbol_id, ttl_hot):
        """
        获取并缓存热门代币列表
        
        Args:
            target_symbol_id: 目标代币ID
            ttl_hot: 缓存TTL时间
            
        Returns:
            目标代币的数据（如果在热门列表中）
        """
        lock_acquired = False
        lock_value = None

        try:
            await self._ensure_initialized()

            # 尝试获取锁，增加重试次数
            lock_acquired = await acquire_lock(
                self.cmc_redis, 
                CMC_BATCH_PROCESSING_LOCK_KEY, 
                timeout=30, 
                retry_count=5, 
                retry_delay=0.5
            )
            if not lock_acquired:
                logger.warning("Failed to acquire lock for fetching top N1 listings after retries")
                return None

            response_data = await self.client.get_listings_latest()
            tokens_data = response_data.get('data', [])
            # 使用 Redis pipeline 批量缓存热门列表数据
            pipe = self.cmc_redis.pipeline()
            for token_item in tokens_data:
                cmc_id = token_item.get('id')
                symbol = token_item.get('symbol')
                if not cmc_id or not symbol:
                    continue
                key_data = CMC_QUOTE_DATA_KEY % {"symbol_id": str(cmc_id)}
                await pipe.set(key_data, json.dumps(token_item), ex=ttl_hot)
            await pipe.execute()

            # 尝试获取目标代币数据
            target_data = await self.cmc_redis.get_token_quote_data(target_symbol_id)
            return target_data

        except Exception as e:
            logger.error(f"Error fetching top N1 listings: {e}", exc_info=True)
            return None
        finally:
            if lock_acquired:
                try:
                    await release_lock(self.cmc_redis, CMC_BATCH_PROCESSING_LOCK_KEY)
                except Exception as e:
                    logger.error(f"Error releasing lock: {e}", exc_info=True)

    async def initiate_batch_request_processing(self, symbol_id):
        """
        将请求添加到待处理批次，等待合并窗口，然后尝试从缓存获取数据。
        Args:
            symbol_id: 代币ID
            
        Returns:
            代币数据或None
        """
        if not symbol_id:
            logger.warning("initiate_batch_request_processing called with invalid symbol_id")
            return None

        try:
            await self._ensure_initialized()

            symbol_id = str(symbol_id)
            position = await self.cmc_redis.lpos(CMC_BATCH_REQUESTS_PENDING_KEY, symbol_id)
            if position is not None:
                logger.debug(f"Request for {symbol_id} already in pending batch")
            else:
                await self.cmc_redis.rpush(CMC_BATCH_REQUESTS_PENDING_KEY, symbol_id)
                logger.debug(f"Added {symbol_id} to pending batch")

            await asyncio.sleep(CMC_T1_MERGE_WINDOW_SECONDS)

            data = await self.cmc_redis.get_token_quote_data(symbol_id)
            return data
        except Exception as e:
            logger.error(f"Error in initiate_batch_request_processing for symbol_id {symbol_id}: {e}", exc_info=True)
            return None

    async def get_token_market_data(self, symbol_id) -> Optional[Dict[str, Any]]:
        """
        获取代币市场数据，返回数据字典或 None。
        优化后的逻辑：对于特定ID请求，直接使用批处理，避免不必要的listings API调用
        """
        try:
            await self._ensure_initialized()

            # 步骤1: 直接检查缓存
            cached_data = await self.cmc_redis.get_token_quote_data(symbol_id)
            if cached_data:
                logger.info(f"Cache hit for {symbol_id} market data")
                return cached_data

            # 步骤2: 缓存未命中 - 直接启动批处理
            # 移除listings调用，让批处理任务自动从数据库获取热门ID补充到100个
            logger.info(f"Cache miss for {symbol_id}, adding to batch processing queue")
            data_from_batch = await self.initiate_batch_request_processing(symbol_id)
            if data_from_batch:
                logger.info(f"Got {symbol_id} from batch processing")
                return data_from_batch

            logger.info(f"No data found for cmc_id {symbol_id} after batch processing. The asset may not exist in CMC's database or may be delisted.")
            return None
        except Exception as e:
            logger.error(f"Error getting market data for symbol_id {symbol_id}: {e}", exc_info=True)
            return None

    async def fetch_and_store_klines_batch(self, cmc_ids, count=1, delay_between_calls=2.0, batch_size=100):
        """
        批量获取并存储K线数据，支持大批量处理和速率限制
        
        Args:
            cmc_ids: CMC代币ID列表 (支持大批量，内部分批处理)
            count: 获取的K线数据点数量 (初始化时24，增量更新时1)
            delay_between_calls: API调用间隔秒数 (避免触发速率限制)
            batch_size: 每批处理的资产数量 (默认100)
            
        Returns:
            dict: {成功数量, 失败数量, 总K线数}
        """
        try:
            if not cmc_ids:
                return {'success': 0, 'failed': 0, 'total_klines': 0}

            total_success = 0
            total_failed = 0
            total_klines = 0

            logger.info(f"Processing {len(cmc_ids)} assets in batches of {batch_size}")

            for i in range(0, len(cmc_ids), batch_size):
                batch_ids = cmc_ids[i:i + batch_size]
                batch_num = i // batch_size + 1
                total_batches = (len(cmc_ids) + batch_size - 1) // batch_size

                logger.info(f"Processing batch {batch_num}/{total_batches}: {len(batch_ids)} assets")

                # 获取存在的资产
                assets_qs = CmcAsset.objects.filter(cmc_id__in=batch_ids)
                assets_map = {asset.cmc_id: asset async for asset in assets_qs}

                missing_ids = set(batch_ids) - set(assets_map.keys())
                if missing_ids:
                    logger.warning(f"Assets not found for cmc_ids: {missing_ids}")

                if not assets_map:
                    logger.warning(f"No valid assets found in batch {batch_num}")
                    total_failed += len(batch_ids)
                    continue

                try:
                    # 批量获取K线数据
                    response_data = await self.client.get_ohlcv_historical(list(assets_map.keys()), count)

                    # 处理返回的数据
                    batch_result = await self._process_klines_response(response_data, assets_map)

                    total_success += batch_result['success']
                    total_failed += batch_result['failed']
                    total_klines += batch_result['total_klines']

                    logger.info(
                        f"Batch {batch_num} completed: success={batch_result['success']}, failed={batch_result['failed']}, klines={batch_result['total_klines']}")

                except Exception as e:
                    logger.error(f"Error processing batch {batch_num}: {e}", exc_info=True)
                    total_failed += len(batch_ids)

                # 添加延迟避免速率限制（除了最后一批）
                if i + batch_size < len(cmc_ids):
                    logger.debug(f"Waiting {delay_between_calls}s before next batch...")
                    await asyncio.sleep(delay_between_calls)

            logger.info(
                f"All batches completed: success={total_success}, failed={total_failed}, total_klines={total_klines}")
            return {'success': total_success, 'failed': total_failed, 'total_klines': total_klines}

        except Exception as e:
            logger.error(f"Error in batch klines update: {e}", exc_info=True)
            return {'success': 0, 'failed': len(cmc_ids), 'total_klines': 0}

    async def _process_klines_response(self, response_data, assets_map):
        """
        处理CMC API返回的K线数据
        
        Args:
            response_data: CMC API响应数据
            assets_map: 资产映射字典 {cmc_id: asset}
            
        Returns:
            dict: {success, failed, total_klines}
        """
        success_count = 0
        failed_count = 0
        total_klines_stored = 0

        data = response_data.get('data', {})

        # 处理不同的数据结构
        if isinstance(data, dict) and 'id' in data:
            # 单个资产的情况
            data = {str(data['id']): data}
        elif not isinstance(data, dict):
            logger.error(f"Unexpected data format from CMC API: {type(data)}")
            return {'success': 0, 'failed': len(assets_map), 'total_klines': 0}

        for cmc_id_str, asset_data in data.items():
            try:
                cmc_id = int(cmc_id_str)
                asset = assets_map.get(cmc_id)
                if not asset:
                    failed_count += 1
                    continue

                quotes_data = asset_data.get('quotes', [])
                if not quotes_data:
                    logger.warning(f"No quotes data for asset {asset.symbol} (cmc_id: {cmc_id})")
                    failed_count += 1
                    continue

                # 存储K线数据
                asset_klines_count = 0
                for quote_data in quotes_data:
                    kline, created = await CmcKline.objects.update_or_create_from_api_data(
                        asset, quote_data, timeframe='1h'
                    )
                    if kline:
                        asset_klines_count += 1

                if asset_klines_count > 0:
                    success_count += 1
                    total_klines_stored += asset_klines_count
                    logger.debug(f"Stored {asset_klines_count} klines for {asset.symbol}")
                else:
                    failed_count += 1

            except Exception as e:
                logger.error(f"Error processing klines for cmc_id {cmc_id_str}: {e}")
                failed_count += 1

        return {'success': success_count, 'failed': failed_count, 'total_klines': total_klines_stored}

    async def process_klines(
            self,
            cmc_ids: Optional[List[int]] = None,
            top_n: Optional[int] = None,
            count: int = 1,
            batch_size: int = 100,
            delay_between_calls: float = 2.0,
            only_missing: bool = False,
    ) -> Dict[str, int]:
        """
        公共 K 线处理方法：
          only_missing=False → 增量更新
          only_missing=True  → 初始化时只处理缺失的资产
        """
        # 1. 构建资产查询集
        qs = CmcAsset.objects.all()
        if cmc_ids:
            qs = qs.filter(cmc_id__in=cmc_ids)
        elif top_n:
            qs = qs.filter(market_data__cmc_rank__isnull=False).order_by('market_data__cmc_rank')[:top_n]
        else:
            qs = qs.filter(market_data__cmc_rank__isnull=False).order_by('market_data__cmc_rank')

        assets = [asset async for asset in qs.select_related('market_data')]
        if not assets:
            logger.warning("No assets found for process_klines")
            return {'success': 0, 'failed': 0, 'total_klines': 0}

        # 2. 如果初始化模式，只保留还没有任何 K 线数据的资产
        if only_missing:
            filtered = []
            for asset in assets:
                if await CmcKline.objects.filter(asset=asset).acount() == 0:
                    filtered.append(asset)
            assets = filtered
            if not assets:
                logger.info("All assets already have klines, skipping process_klines")
                return {'success': 0, 'failed': 0, 'total_klines': 0}

        # 3. 批量获取并存储
        asset_ids = [asset.cmc_id for asset in assets]
        return await self.fetch_and_store_klines_batch(
            asset_ids,
            count=count,
            batch_size=batch_size,
            delay_between_calls=delay_between_calls,
        )

    async def close(self):
        """关闭所有资源连接"""
        # 关闭Redis连接
        await self._safe_close_redis()
        self._cmc_redis = None

        # 关闭HTTP客户端
        if self._client:
            try:
                await self._client.close()
                self._client = None
            except Exception as e:
                logger.error(f"Error closing API client: {e}", exc_info=True)

        self._initialized = False


async def get_cmc_service() -> CoinMarketCapService:
    """获取CoinMarketCapService的单例实例"""
    return await CoinMarketCapService()


async def get_klines_for_asset(asset: CmcAsset, timeframe: str, start_time: datetime, end_time: datetime,
                               start_time_24h: datetime) -> Dict[str, Any]:
    """
    从数据库获取并处理单个资产的K线数据。
    如果数据库没有数据，尝试从CMC API获取。
    """
    klines_qs = CmcKline.objects.filter(
        asset=asset,
        timeframe=timeframe,
        timestamp__gte=start_time,
        timestamp__lte=end_time
    ).order_by('timestamp')

    klines = await KlineDataProcessor.serialize_klines_data(klines_qs)

    # 如果数据库没有K线数据，尝试从CMC API获取
    if not klines:
        logger.info(f"No klines found for asset {asset.symbol} (cmc_id: {asset.cmc_id}), attempting to fetch from CMC")
        try:
            service = await get_cmc_service()
            # 获取24小时的历史数据用于初始化
            result = await service.fetch_and_store_klines_batch([asset.cmc_id], count=24, batch_size=1)

            if result['success'] > 0:
                logger.info(f"Successfully fetched and stored {result['total_klines']} klines for {asset.symbol}")
                # 重新查询数据库获取刚存储的K线数据
                klines_qs = CmcKline.objects.filter(
                    asset=asset,
                    timeframe=timeframe,
                    timestamp__gte=start_time,
                    timestamp__lte=end_time
                ).order_by('timestamp')
                klines = await KlineDataProcessor.serialize_klines_data(klines_qs)
            else:
                logger.warning(f"Failed to fetch klines for {asset.symbol} from CMC API")

        except Exception as e:
            logger.error(f"Error fetching klines for asset {asset.symbol}: {e}", exc_info=True)

    high_24h, low_24h = KlineDataProcessor.calculate_high_low_24h(klines, start_time_24h)

    return {
        'klines': klines,
        'high_24h': high_24h,
        'low_24h': low_24h,
    }


async def get_latest_market_data(cmc_id: int) -> Optional[Dict[str, Any]]:
    """
    获取单个代币的最新市场数据。
    优先从数据库获取，数据不存在或过期时从CMC API获取。
    """
    logger.info(f"get_latest_market_data called for cmc_id: {cmc_id}")

    try:
        # 1. 尝试从数据库获取数据
        market_data = await CmcMarketData.objects.select_related('asset').aget(asset__cmc_id=cmc_id)
        age = (timezone.now() - market_data.timestamp).total_seconds()

        # 2. 如果数据过期，触发异步刷新
        if age > CMC_TTL_BASE:
            logger.info(f"Market data for cmc_id {cmc_id} is stale (age: {age}s), initiating async refresh")
            service = await get_cmc_service()
            asyncio.create_task(service.get_token_market_data(cmc_id))

        # 3. 返回数据库数据
        from apps.cmc_proxy.helpers import MarketDataFormatter
        return MarketDataFormatter.format_market_data_from_db(market_data)

    except CmcMarketData.DoesNotExist:
        # 4. 数据库没有数据，从CMC获取
        logger.info(f"Market data for cmc_id {cmc_id} not found in database, fetching from CMC")
        service = await get_cmc_service()
        data = await service.get_token_market_data(cmc_id)

        if data:
            from apps.cmc_proxy.helpers import MarketDataFormatter
            return MarketDataFormatter.format_market_data_from_api(data)
        else:
            return None
