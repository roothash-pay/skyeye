from datetime import timedelta
from typing import Dict, Any, List, Optional

from django.apps import apps
from django.utils import timezone
from common.helpers import getLogger
from apps.cmc_proxy.consts import CMC_PRICE_FALLBACK_WARNING_THRESHOLD, CCXT_PRICE_STALE_THRESHOLD

logger = getLogger(__name__)


class TimeRangeCalculator:
    """时间范围计算工具"""

    @staticmethod
    def calculate_kline_time_range(hours=24):
        """计算K线时间范围"""
        end_time = timezone.now().replace(minute=0, second=0, microsecond=0)
        start_time = end_time - timedelta(hours=hours)
        start_time_24h = end_time - timedelta(hours=24)
        return start_time, end_time, start_time_24h


class MarketDataFormatter:
    """市场数据格式化工具"""

    @staticmethod
    def safe_float(value) -> Optional[float]:
        """安全转换为float，None或0返回None"""
        if value is None:
            return None
        try:
            result = float(value)
            return result if result != 0 else None
        except (ValueError, TypeError):
            return None

    @staticmethod
    def format_market_data_item(item) -> Dict[str, Any]:
        """格式化单个市场数据项，使用CCXT价格替换CMC价格"""
        # 尝试获取CCXT价格
        ccxt_data = MarketDataFormatter.get_ccxt_price_for_cmc_asset(item.asset)
        
        # 使用CCXT价格（如果可用），否则回退到CMC价格
        if ccxt_data:
            price_usd = ccxt_data['price_usd']
            volume_24h = ccxt_data['volume_24h'] or (float(item.volume_24h) if item.volume_24h else None)
            timestamp = ccxt_data['price_timestamp'].isoformat() if ccxt_data['price_timestamp'] else item.timestamp.isoformat()
            exchange = ccxt_data['exchange']
        else:
            price_usd = float(item.price_usd) if item.price_usd else None
            volume_24h = float(item.volume_24h) if item.volume_24h else None
            timestamp = item.timestamp.isoformat()
            exchange = None
        
        return {
            'cmc_id': item.asset.cmc_id,
            'symbol': item.asset.symbol,
            'price_usd': price_usd,
            'cmc_rank': item.cmc_rank,
            'percent_change_24h': item.percent_change_24h,
            'volume_24h': volume_24h,
            'updated_at': timestamp,
            'price_source': "ccxt" if ccxt_data else "cmc",
            'exchange': exchange,
        }

    @staticmethod
    def format_asset_info(asset) -> Dict[str, Any]:
        """格式化资产基本信息"""
        return {
            'cmc_id': asset.cmc_id,
            'symbol': asset.symbol,
            'name': asset.name,
        }

    @staticmethod
    def get_ccxt_price_for_cmc_asset(cmc_asset) -> Optional[Dict[str, Any]]:
        """通过CMC资产获取对应的CCXT价格数据（绕过缓存获取最新数据）"""
        if not cmc_asset:
            return None
            
        try:
            # 使用Django apps registry获取模型，避免循环导入
            AssetPrice = apps.get_model('price_oracle', 'AssetPrice')
            
            # 直接查询数据库获取最新价格，绕过任何缓存
            price_obj = AssetPrice.objects.filter(cmc_asset=cmc_asset).order_by('-updated_at').first()
            
            if not price_obj:
                # 如果没有找到关联，尝试通过symbol查找最新价格
                base_asset = cmc_asset.symbol.lower()
                price_obj = AssetPrice.objects.filter(base_asset=base_asset).order_by('-updated_at').first()
            
            if price_obj:
                # 检查价格数据的新鲜度
                age_minutes = (timezone.now() - price_obj.updated_at).total_seconds() / 60
                age_seconds = (timezone.now() - price_obj.updated_at).total_seconds()
                if age_seconds > CCXT_PRICE_STALE_THRESHOLD:
                    logger.info(f"CCXT price for {cmc_asset.symbol} is {age_minutes:.1f} minutes old, may be stale")
                
                return {
                    'price_usd': float(price_obj.price),
                    'price_change_24h': float(price_obj.price_change_24h) if price_obj.price_change_24h else None,
                    'volume_24h': float(price_obj.volume_24h) if price_obj.volume_24h else None,
                    'price_timestamp': price_obj.price_timestamp,
                    'exchange': price_obj.exchange,
                    'data_age_minutes': age_minutes
                }
        except Exception as e:
            # 如果CCXT价格获取失败，记录错误但不影响主流程
            logger.warning(f"Failed to get CCXT price for CMC asset {cmc_asset.symbol} (cmc_id: {cmc_asset.cmc_id}): {e}")
        return None

    @staticmethod
    def format_market_data_from_db(market_data) -> Dict[str, Any]:
        """
        混合数据源格式化：
        - CMC数据：市值、排名、供应量等（来自缓存的CMC数据，节省credit）
        - 价格数据：实时CCXT价格（无缓存，保证时效性）
        """
        # 获取实时CCXT价格数据
        ccxt_data = MarketDataFormatter.get_ccxt_price_for_cmc_asset(market_data.asset)
        
        # 价格相关字段：优先使用CCXT实时数据
        if ccxt_data:
            price_usd = ccxt_data['price_usd']
            # 交易量优先使用CCXT数据（更准确）
            volume_24h = ccxt_data['volume_24h'] or MarketDataFormatter.safe_float(market_data.volume_24h)
            price_timestamp = ccxt_data['price_timestamp'].isoformat()
            price_source = "ccxt"
            exchange = ccxt_data['exchange']
            data_age = ccxt_data.get('data_age_minutes', 0)
        else:
            # 回退到CMC价格，但检查数据新鲜度
            cmc_age_minutes = (timezone.now() - market_data.timestamp).total_seconds() / 60
            
            # 如果CMC数据太旧，记录警告
            cmc_age_seconds = (timezone.now() - market_data.timestamp).total_seconds()
            if cmc_age_seconds > CMC_PRICE_FALLBACK_WARNING_THRESHOLD:
                logger.warning(f"Fallback to CMC price for {market_data.asset.symbol}, but data is {cmc_age_minutes:.1f} minutes old")
            
            price_usd = MarketDataFormatter.safe_float(market_data.price_usd)
            volume_24h = MarketDataFormatter.safe_float(market_data.volume_24h)
            price_timestamp = market_data.timestamp.isoformat()
            price_source = "cmc"
            exchange = None
            data_age = cmc_age_minutes
        
        # 市场数据字段：使用CMC缓存数据（10分钟缓存，节省credit）
        return {
            # 价格数据 - 实时CCXT
            "price_usd": price_usd,
            "volume_24h": volume_24h,
            "price_timestamp": price_timestamp,
            "price_source": price_source,
            "exchange": exchange,
            "price_data_age_minutes": data_age,
            
            # 市场数据 - CMC缓存（可安全缓存10分钟）
            "fully_diluted_market_cap": MarketDataFormatter.safe_float(market_data.fully_diluted_market_cap),
            "market_cap": MarketDataFormatter.safe_float(market_data.market_cap),
            "circulating_supply": MarketDataFormatter.safe_float(market_data.circulating_supply),
            "total_supply": MarketDataFormatter.safe_float(market_data.total_supply),
            "cmc_rank": market_data.cmc_rank,
            "percent_change_24h": market_data.percent_change_24h,
            "volume_24h_token_count": MarketDataFormatter.safe_float(market_data.volume_24h_token_count),
            
            # 元数据
            "cmc_timestamp": market_data.timestamp.isoformat(),
            "cmc_id": market_data.asset.cmc_id,
            "symbol": market_data.asset.symbol,
            "name": market_data.asset.name,
        }

    @staticmethod
    def format_market_data_from_api(data) -> Dict[str, Any]:
        """从CMC API响应格式化完整市场数据"""
        quote_usd = data.get('quote', {}).get('USD', {})
        return {
            "price_usd": MarketDataFormatter.safe_float(quote_usd.get('price')),
            "fully_diluted_market_cap": MarketDataFormatter.safe_float(quote_usd.get('fully_diluted_market_cap')),
            "market_cap": MarketDataFormatter.safe_float(quote_usd.get('market_cap')),
            "volume_24h": MarketDataFormatter.safe_float(quote_usd.get('volume_24h')),
            "volume_24h_token_count": MarketDataFormatter.safe_float(quote_usd.get('volume_change_24h')),
            "circulating_supply": MarketDataFormatter.safe_float(data.get('circulating_supply')),
            "total_supply": MarketDataFormatter.safe_float(data.get('total_supply')),
            "cmc_rank": data.get('cmc_rank'),
            "percent_change_24h": quote_usd.get('percent_change_24h'),
            "timestamp": data.get('last_updated', timezone.now().isoformat()),
        }


class KlineDataProcessor:
    """K线数据处理工具"""

    @staticmethod
    async def serialize_klines_data(klines_qs):
        """序列化K线数据"""
        return [
            {
                'timestamp': k.timestamp.isoformat(),
                'open': float(k.open),
                'high': float(k.high),
                'low': float(k.low),
                'close': float(k.close),
                'volume': float(k.volume),
                'volume_token_count': float(k.volume_token_count) if k.volume_token_count else None,
            }
            async for k in klines_qs
        ]

    @staticmethod
    def calculate_high_low_24h(klines: List[Dict[str, Any]], start_time_24h) -> tuple:
        """从K线数据中计算24小时高低价"""
        if not klines:
            return None, None

        klines_24h = [k for k in klines if k['timestamp'] >= start_time_24h.isoformat()]
        if not klines_24h:
            return None, None

        return max(k['high'] for k in klines_24h), min(k['low'] for k in klines_24h)


class ViewParameterValidator:
    """视图参数验证工具"""

    @staticmethod
    def validate_and_parse_cmc_id(cmc_id_str: str) -> tuple:
        """验证并解析cmc_id参数
        
        Returns:
            (success: bool, value_or_error: int or str)
        """
        try:
            return True, int(cmc_id_str)
        except ValueError:
            return False, "cmc_id 格式错误，应为整数"

    @staticmethod
    def validate_and_parse_cmc_ids(cmc_ids_str: str) -> tuple:
        """验证并解析cmc_ids参数
        
        Returns:
            (success: bool, value_or_error: List[int] or str)
        """
        try:
            id_list = [int(x) for x in cmc_ids_str.split(',') if x.strip()]
            return True, id_list
        except ValueError:
            return False, "cmc_ids 格式错误，应为逗号分隔的整数列表"
