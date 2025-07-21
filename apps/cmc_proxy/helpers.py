from datetime import timedelta
from typing import Dict, Any, List, Optional

from django.utils import timezone


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
        """格式化单个市场数据项"""
        return {
            'cmc_id': item.asset.cmc_id,
            'symbol': item.asset.symbol,
            'price_usd': float(item.price_usd) if item.price_usd else None,
            'cmc_rank': item.cmc_rank,
            'percent_change_24h': item.percent_change_24h,
            'volume_24h': float(item.volume_24h) if item.volume_24h else None,
            'updated_at': item.timestamp.isoformat(),
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
    def format_market_data_from_db(market_data) -> Dict[str, Any]:
        """从数据库记录格式化完整市场数据"""
        return {
            "price_usd": MarketDataFormatter.safe_float(market_data.price_usd),
            "fully_diluted_market_cap": MarketDataFormatter.safe_float(market_data.fully_diluted_market_cap),
            "market_cap": MarketDataFormatter.safe_float(market_data.market_cap),
            "volume_24h": MarketDataFormatter.safe_float(market_data.volume_24h),
            "volume_24h_token_count": MarketDataFormatter.safe_float(market_data.volume_24h_token_count),
            "circulating_supply": MarketDataFormatter.safe_float(market_data.circulating_supply),
            "total_supply": MarketDataFormatter.safe_float(market_data.total_supply),
            "cmc_rank": market_data.cmc_rank,
            "percent_change_24h": market_data.percent_change_24h,
            "timestamp": market_data.timestamp.isoformat(),
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
