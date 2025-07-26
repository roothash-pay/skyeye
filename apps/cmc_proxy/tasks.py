import asyncio
import json

from celery import shared_task
from django.conf import settings
from django_celery_beat.models import PeriodicTask

from apps.cmc_proxy import consts
from apps.cmc_proxy.models import CmcAsset, CmcKline, CmcMarketData
from apps.cmc_proxy.services import CoinMarketCapClient, get_cmc_service
from apps.cmc_proxy.utils import CMCRedisClient, acquire_lock, release_lock
from common.helpers import getLogger

logger = getLogger(__name__)


async def _get_top_market_cap_ids_from_db(count: int, exclude_ids: list = None) -> list:
    """
    从数据库获取按市值排序的热门代币ID作为补充
    
    Args:
        count: 需要获取的ID数量
        exclude_ids: 需要排除的ID列表
        
    Returns:
        热门代币ID列表（字符串格式）
    """
    if count <= 0:
        return []
    
    try:
        # 排除已有的ID
        exclude_ids = exclude_ids or []
        exclude_cmc_ids = [int(id_str) for id_str in exclude_ids if id_str.isdigit()]
        
        # 从数据库按市值降序获取热门代币ID
        qs = CmcMarketData.objects.select_related('asset').filter(
            market_cap__isnull=False,
            market_cap__gt=0
        ).exclude(
            asset__cmc_id__in=exclude_cmc_ids
        ).order_by('-market_cap')[:count]
        
        # 提取CMC ID并转换为字符串
        hot_ids = [str(item.asset.cmc_id) async for item in qs]
        
        logger.info(f"Retrieved {len(hot_ids)} hot IDs from database (market cap based)")
        return hot_ids
        
    except Exception as e:
        logger.error(f"Error getting top market cap IDs from database: {e}", exc_info=True)
        return []


def _run_async_with_new_loop(coro):
    """创建新的事件循环并运行异步协程的辅助函数"""
    loop = None
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        if loop and not loop.is_closed():
            loop.close()


async def _process_pending_cmc_batch_requests_with_lock(task_lock_key):
    """带任务级别锁的批量处理函数"""
    logger.info("Starting to process pending CMC batch requests with task lock")

    cmc_redis = None
    task_lock_acquired = False
    batch_lock_acquired = False

    try:
        cmc_redis = await CMCRedisClient.create(settings.REDIS_CMC_URL)

        # 尝试获取任务级别锁（防止同一定时任务的多个实例）
        task_lock_acquired = await acquire_lock(cmc_redis, task_lock_key, timeout=5)
        if not task_lock_acquired:
            logger.info("Task lock not acquired, another instance of this scheduled task is running")
            return

        # 尝试获取批量处理锁
        batch_lock_acquired = await acquire_lock(cmc_redis, consts.CMC_BATCH_PROCESSING_LOCK_KEY, timeout=30)
        if not batch_lock_acquired:
            logger.warning("Failed to acquire batch processing lock, another process might be running")
            return

        # 从Redis列表中获取待处理请求
        batch_size = consts.CMC_N2_BATCH_TARGET_SIZE
        pending_ids = []

        # 使用 LPOP 获取多个元素（Redis 6.2+）
        try:
            pending_ids_bytes = await cmc_redis.lpop(consts.CMC_BATCH_REQUESTS_PENDING_KEY, batch_size)
            if pending_ids_bytes:
                # 如果返回的是单个元素而不是列表，将其包装为列表
                if not isinstance(pending_ids_bytes, list):
                    pending_ids = [pending_ids_bytes]
                else:
                    pending_ids = pending_ids_bytes
        except Exception as e:
            logger.error(f"Error getting pending requests from Redis list: {e}", exc_info=True)
            # 如果上面的方法失败，尝试使用LRANGE和LTRIM组合来模拟批量LPOP
            pending_ids_bytes = await cmc_redis.lrange(consts.CMC_BATCH_REQUESTS_PENDING_KEY, 0, batch_size - 1)
            if pending_ids_bytes:
                pending_ids = [id_bytes for id_bytes in pending_ids_bytes]
                # 删除已获取的元素
                await cmc_redis.ltrim(consts.CMC_BATCH_REQUESTS_PENDING_KEY, len(pending_ids), -1)

        # 去重
        unique_ids = list(set(pending_ids))
        logger.info(f"Got {len(unique_ids)} unique IDs from pending requests")

        # 只有在有实际待处理请求时才从数据库获取热门ID补充，避免无限重复请求
        if len(unique_ids) > 0 and len(unique_ids) < batch_size:
            supplement_count = batch_size - len(unique_ids)
            supplement_ids = await _get_top_market_cap_ids_from_db(supplement_count, exclude_ids=unique_ids)

            # 确保不重复（双重保护）
            supplement_ids = [_id for _id in supplement_ids if _id not in unique_ids]
            unique_ids.extend(supplement_ids)

            logger.info(f"Added {len(supplement_ids)} IDs from database (top market cap)")
        elif len(unique_ids) == 0:
            logger.info("No pending requests found, skipping database supplement to avoid infinite requests")

        if not unique_ids:
            logger.info("No IDs to process in this batch")
            return

        client = CoinMarketCapClient()
        try:
            response_data = await client.get_quotes_latest(ids=unique_ids)
            quotes_data = response_data.get('data', {})

            for cmc_id_str, token_data in quotes_data.items():
                cmc_id = token_data.get('id')
                if not cmc_id:
                    logger.warning(f"Token data missing id for key {cmc_id_str}")
                    continue

                symbol = token_data.get('symbol')
                if not symbol:
                    logger.warning(f"Token data missing symbol for id: {cmc_id}")
                    continue

                await cmc_redis.cache_token_quote_data(str(cmc_id), token_data, consts.CMC_TTL_WARM_COLD)

            logger.info(f"Successfully processed {len(quotes_data)} tokens in this batch")

        except Exception as e:
            logger.error(f"Error fetching quotes from CMC API: {e}", exc_info=True)

    except Exception as e:
        logger.error(f"Critical error during batch processing: {e}", exc_info=True)
    finally:
        if task_lock_acquired and cmc_redis:
            await release_lock(cmc_redis, task_lock_key)
        if batch_lock_acquired and cmc_redis:
            await release_lock(cmc_redis, consts.CMC_BATCH_PROCESSING_LOCK_KEY)
        if cmc_redis:
            await cmc_redis.aclose()


async def _daily_full_data_sync_with_lock():
    """带锁的每日全量同步 CoinMarketCap 数据"""
    task_lock_key = "cmc:lock:daily_full_sync_task"
    cmc_redis = None
    lock_acquired = False

    try:
        cmc_redis = await CMCRedisClient.create(settings.REDIS_CMC_URL)

        # 尝试获取任务锁
        lock_acquired = await acquire_lock(cmc_redis, task_lock_key, timeout=10)
        if not lock_acquired:
            logger.info("Daily full sync task lock not acquired, another instance is running")
            return 0

        return await _daily_full_data_sync_implementation(cmc_redis)

    except Exception as e:
        logger.error(f"Error in daily_full_data_sync_with_lock: {e}", exc_info=True)
        return 0
    finally:
        if lock_acquired and cmc_redis:
            await release_lock(cmc_redis, task_lock_key)
        if cmc_redis:
            await cmc_redis.aclose()


async def _daily_full_data_sync_implementation(cmc_redis):
    """每日全量同步的具体实现"""
    logger.info("Starting daily full sync of CoinMarketCap data")

    # 暂停批量请求任务以避免冲突
    batch_task = None
    try:
        batch_task = await PeriodicTask.objects.aget(name='process_pending_cmc_batch_requests')
        if batch_task.enabled:
            batch_task.enabled = False
            await batch_task.asave()
            logger.info("Temporarily disabled batch request task during full sync")
    except PeriodicTask.DoesNotExist:
        logger.warning("Batch request task not found, continuing without disabling")

    client = CoinMarketCapClient()
    try:
        page_size = 5000
        start = 1
        all_tokens_data = []

        while True:
            try:
                response_data = await client.get_listings_latest(start=start, limit=page_size)
                tokens_page = response_data.get('data', [])

                if not tokens_page:
                    break

                all_tokens_data.extend(tokens_page)
                logger.info(f"Fetched {len(tokens_page)} tokens, total so far: {len(all_tokens_data)}")

                for token_item in tokens_page:
                    cmc_id = token_item.get('id')
                    symbol = token_item.get('symbol')
                    if not cmc_id or not symbol:
                        logger.warning(f"Token item missing id or symbol: {token_item.get('slug')}")
                        continue

                    await cmc_redis.cache_token_quote_data(str(cmc_id), token_item, consts.CMC_TTL_BASE)

                if len(tokens_page) < page_size:
                    break

                start += page_size
                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Error fetching a page during daily sync: {e}", exc_info=True)
                break

        if all_tokens_data:
            # 按市值排序（降序）
            def get_market_cap(token_dict):
                try:
                    return float(token_dict.get('quote', {}).get('USD', {}).get('market_cap', 0) or 0)
                except (ValueError, TypeError):
                    return 0.0

            all_tokens_data.sort(key=get_market_cap, reverse=True)

            n1 = consts.CMC_N1
            n3_range = consts.CMC_N3_SUPPLEMENT_POOL_RANGE
            supplement_tokens_data = all_tokens_data[n1: n1 + n3_range]

            if supplement_tokens_data:
                await cmc_redis.update_supplement_pool(supplement_tokens_data)
                logger.info(f"Updated supplement pool with {len(supplement_tokens_data)} tokens")

        logger.info(f"Daily full sync completed, processed {len(all_tokens_data)} tokens")
        return len(all_tokens_data)
    except Exception as e:
        logger.error(f"Critical error during daily_full_data_sync task: {e}", exc_info=True)
        return 0
    finally:
        # 重新启用批量请求任务
        if batch_task and not batch_task.enabled:
            try:
                batch_task.enabled = True
                await batch_task.asave()
                logger.info("Re-enabled batch request task after full sync")
            except Exception as e:
                logger.error(f"Failed to re-enable batch request task: {e}", exc_info=True)


async def _process_cmc_klines(count: int, only_missing: bool):
    """公共 CMC K 线处理异步函数"""
    mode = "initialization" if only_missing else "incremental update"
    logger.info(f"Starting CMC klines {mode} task")
    try:
        cmc_service = await get_cmc_service()
        # 如果是增量模式且尚未初始化任何 K 线，则首 run 自动初始化 24 小时历史数据
        if not only_missing:
            total = await CmcKline.objects.acount()
            if total == 0:
                logger.info("第一次运行，自动初始化 K 线历史数据")
                await cmc_service.process_klines(count=24, only_missing=True)
        # 执行请求的模式更新或初始化
        result = await cmc_service.process_klines(count=count, only_missing=only_missing)
        logger.info(
            f"CMC klines {mode} completed. Success: {result['success']}, Failed: {result['failed']}, Total klines: {result['total_klines']}")
        return result['total_klines']
    except Exception as e:
        logger.error(f"Critical error during klines {mode} task: {e}", exc_info=True)
        return 0


async def _process_cmc_klines_with_lock(task_lock_key, count: int, only_missing: bool):
    """带锁的K线处理函数"""
    cmc_redis = None
    lock_acquired = False

    try:
        cmc_redis = await CMCRedisClient.create(settings.REDIS_CMC_URL)

        # 尝试获取任务锁
        lock_acquired = await acquire_lock(cmc_redis, task_lock_key, timeout=10)
        if not lock_acquired:
            logger.info("Update klines task lock not acquired, another instance is running")
            return 0

        return await _process_cmc_klines(count, only_missing)

    except Exception as e:
        logger.error(f"Error in _process_cmc_klines_with_lock: {e}", exc_info=True)
        return 0
    finally:
        if lock_acquired and cmc_redis:
            await release_lock(cmc_redis, task_lock_key)
        if cmc_redis:
            await cmc_redis.aclose()


async def _sync_cmc_data_with_lock():
    """带锁的数据同步函数"""
    task_lock_key = "cmc:lock:sync_data_task"
    cmc_redis = None
    lock_acquired = False

    try:
        cmc_redis = await CMCRedisClient.create(settings.REDIS_CMC_URL)

        # 尝试获取任务锁
        lock_acquired = await acquire_lock(cmc_redis, task_lock_key, timeout=5)
        if not lock_acquired:
            logger.info("Sync data task lock not acquired, another instance is running")
            return

        # 直接执行同步逻辑，避免调用 management command 中的 asyncio.run()
        await _sync_data_from_redis_implementation(cmc_redis)

    except Exception as e:
        logger.error(f"Error in sync_cmc_data_with_lock: {e}", exc_info=True)
    finally:
        if lock_acquired and cmc_redis:
            await release_lock(cmc_redis, task_lock_key)
        if cmc_redis:
            await cmc_redis.aclose()


async def _sync_data_from_redis_implementation(cmc_redis):
    """直接实现数据同步逻辑，避免 asyncio.run() 冲突"""
    from apps.cmc_proxy.consts import CMC_QUOTE_DATA_KEY

    # 使用 scan_iter 高效地遍历所有代币数据的键
    pattern = CMC_QUOTE_DATA_KEY.replace("%(symbol_id)s", "*")
    keys = [key async for key in cmc_redis.scan_iter(match=pattern)]

    if not keys:
        logger.warning("No CMC data keys found in Redis to sync.")
        return

    logger.info(f"Found {len(keys)} CMC data keys in Redis.")

    assets_created_count = 0
    assets_updated_count = 0
    market_data_updated_count = 0
    failed_count = 0
    total_count = len(keys)

    for key in keys:
        try:
            raw_data = await cmc_redis.get(key)
            if not raw_data:
                failed_count += 1
                continue

            api_data = json.loads(raw_data)
            cmc_id = api_data.get('id')
            if not cmc_id:
                logger.warning(f"Skipping key {key} due to missing 'id' field.")
                failed_count += 1
                continue

            # 1. 同步 CmcAsset (资产元数据)
            asset, created = await CmcAsset.objects.update_or_create_from_api_data(api_data)
            if not asset:
                failed_count += 1
                continue

            if created:
                assets_created_count += 1
            else:
                assets_updated_count += 1

            # 2. 同步 CmcMarketData (最新行情)
            await CmcMarketData.objects.update_or_create_from_api_data(asset, api_data)
            market_data_updated_count += 1

        except json.JSONDecodeError:
            logger.error(f"Failed to decode JSON from key {key}.")
            failed_count += 1
        except Exception as e:
            logger.error(f"Error processing data for key {key}: {e}", exc_info=True)
            failed_count += 1

    logger.info(f'Successfully synchronized CMC data. '
                f'Total Processed: {total_count}, '
                f'Assets Created: {assets_created_count}, '
                f'Assets Updated: {assets_updated_count}, '
                f'Market Data Touched: {market_data_updated_count}, '
                f'Failed: {failed_count}')


# Celery任务包装器
@shared_task(bind=True)
def process_pending_cmc_batch_requests(self):
    """处理待处理的CoinMarketCap批量请求 (Celery任务)"""
    task_lock_key = f"cmc:lock:batch_processing_task"
    return _run_async_with_new_loop(_process_pending_cmc_batch_requests_with_lock(task_lock_key))


@shared_task(bind=True)
def daily_full_data_sync(self):
    """每日全量同步 CoinMarketCap 数据 (Celery任务)"""
    return _run_async_with_new_loop(_daily_full_data_sync_with_lock())


@shared_task(bind=True)
def update_cmc_klines(self, count=1, only_missing=False):
    """更新CMC K线数据 (Celery任务) - 增量更新"""
    task_lock_key = "cmc:lock:update_klines_task"
    return _run_async_with_new_loop(_process_cmc_klines_with_lock(task_lock_key, count, only_missing))


@shared_task(bind=True)
def initialize_missing_klines(self, count=24, only_missing=True):
    """初始化缺失的K线数据 (Celery任务) - 专门处理缺失数据"""
    task_lock_key = "cmc:lock:initialize_missing_klines_task"
    return _run_async_with_new_loop(_process_cmc_klines_with_lock(task_lock_key, count, only_missing))


@shared_task(bind=True)
def sync_cmc_data_task(self):
    """同步CMC数据到数据库 (Celery任务)"""
    return _run_async_with_new_loop(_sync_cmc_data_with_lock())
