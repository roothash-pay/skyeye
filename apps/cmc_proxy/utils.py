import json
from typing import Optional, List, Dict, Any

import redis.asyncio as aioredis

from apps.cmc_proxy.consts import CMC_QUOTE_DATA_KEY, CMC_SUPPLEMENT_POOL_KEY
from common.helpers import getLogger
from common.redis_client import get_async_redis_client

logger = getLogger(__name__)


class CMCRedisClient(aioredis.Redis):
    """CoinMarketCap专用Redis客户端，处理代币数据缓存和检索"""

    @classmethod
    async def create(cls, redis_url: str):
        """创建CMCRedisClient实例的工厂方法"""
        try:
            raw_client = get_async_redis_client(redis_url)
            return cls(connection_pool=raw_client.connection_pool, decode_responses=True)
        except Exception as e:
            logger.error(f"Failed to create CMCRedisClient: {e}", exc_info=True)
            raise

    async def cache_token_quote_data(self, symbol_id: str, data: Dict[str, Any], ttl: int) -> None:
        """缓存代币报价数据"""
        try:
            key = CMC_QUOTE_DATA_KEY % {"symbol_id": symbol_id}
            await self.set(key, json.dumps(data), ex=ttl)
        except Exception as e:
            logger.error(f"Failed to cache token quote data for {symbol_id}: {e}", exc_info=True)

    async def get_token_quote_data(self, symbol_id: str) -> Optional[Dict[str, Any]]:
        """获取缓存的代币报价数据"""
        if not symbol_id:
            return None

        try:
            key = CMC_QUOTE_DATA_KEY % {"symbol_id": symbol_id}
            data = await self.get(key)
            if data:
                try:
                    return json.loads(data)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to decode JSON data for {key}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting token quote data for {symbol_id}: {e}", exc_info=True)
            return None

    async def update_supplement_pool(self, tokens_data_list: List[Dict[str, Any]]) -> None:
        """更新补充池"""
        if not tokens_data_list:
            return

        try:
            # 提取ID和市值
            token_ids_with_market_cap = []
            for token_data in tokens_data_list:
                try:
                    cmc_id = token_data.get('id')
                    market_cap = token_data.get('quote', {}).get('USD', {}).get('market_cap', 0) or 0
                    if cmc_id:
                        token_ids_with_market_cap.append((str(cmc_id), float(market_cap)))
                except (TypeError, ValueError) as e:
                    logger.error(f"Error processing token data for supplement pool: {e}")

            # 清空现有的补充池
            await self.delete(CMC_SUPPLEMENT_POOL_KEY)

            # 添加新的数据
            if token_ids_with_market_cap:
                # 按市值降序排序
                token_ids_with_market_cap.sort(key=lambda x: x[1], reverse=True)

                # 添加到有序集合
                for i, (token_id, market_cap) in enumerate(token_ids_with_market_cap):
                    await self.zadd(CMC_SUPPLEMENT_POOL_KEY, {token_id: -i})  # 使用负索引作为分数，确保排序
        except Exception as e:
            logger.error(f"Failed to update supplement pool: {e}", exc_info=True)

    async def get_from_supplement_pool(self, count: int) -> List[str]:
        """从补充池中获取代币ID"""
        if count <= 0:
            return []

        try:
            # 从有序集合中获取前N个元素
            token_ids = await self.zrange(CMC_SUPPLEMENT_POOL_KEY, 0, count - 1)
            return token_ids
        except Exception as e:
            logger.error(f"Failed to get IDs from supplement pool: {e}", exc_info=True)
            return []


async def acquire_lock(redis_client, lock_key, timeout=30):
    """获取Redis分布式锁"""
    try:
        lock_value = "1"  # 简单的锁值
        success = await redis_client.set(lock_key, lock_value, ex=timeout, nx=True)
        return bool(success)
    except Exception as e:
        logger.error(f"Error acquiring lock {lock_key}: {e}", exc_info=True)
        return False


async def release_lock(redis_client, lock_key):
    """释放Redis分布式锁"""
    try:
        return await redis_client.delete(lock_key)
    except Exception as e:
        logger.error(f"Error releasing lock {lock_key}: {e}", exc_info=True)
        return False
