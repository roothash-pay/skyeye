#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional

import ccxt.async_support as async_ccxt

from apps.price_oracle.constants import STABLECOIN_SYMBOLS, EXCHANGE_PRIORITY
from common.helpers import getLogger

logger = getLogger(__name__)


@dataclass
class PriceData:
    """价格数据结构"""
    symbol: str  # BTC/USDT
    base_asset: str  # BTC
    quote_asset: str  # USDT
    price: Decimal
    volume_24h: Optional[Decimal] = None
    price_change_24h: Optional[Decimal] = None


class ExchangeAdapter(ABC):
    """交易所适配器基类"""

    def __init__(self, exchange_id: str):
        self.exchange_id = exchange_id
        self.client: Optional[async_ccxt.Exchange] = None

    @abstractmethod
    async def get_prices(self) -> List[PriceData]:
        """获取以稳定币计价的资产价格数据"""
        pass

    async def close(self):
        """关闭连接"""
        if self.client:
            try:
                await self.client.close()
            except Exception as e:
                logger.debug(f"关闭客户端时出错: {e}")


class CCXTAdapter(ExchangeAdapter):
    """通用CCXT适配器，支持所有交易所"""

    def __init__(self, exchange_id: str):
        super().__init__(exchange_id)
        self._create_client()

    def _create_client(self):
        """创建CCXT客户端"""
        try:
            if not hasattr(async_ccxt, self.exchange_id):
                logger.error(f"CCXT不支持交易所: {self.exchange_id}")
                return

            exchange_class = getattr(async_ccxt, self.exchange_id)

            # CCXT配置
            config = {
                'timeout': 30000,  # 30秒超时
                'enableRateLimit': True,  # 启用速率限制
                'verbose': False,
                'options': {
                    'defaultType': 'spot',  # 默认使用现货市场
                },
            }

            # 特殊配置
            if self.exchange_id == 'yobit':
                config['timeout'] = 120000  # YoBit需要更长超时

            self.client = exchange_class(config)
            logger.debug(f"创建CCXT客户端: {self.exchange_id}")

        except Exception as e:
            logger.error(f"创建CCXT客户端失败 {self.exchange_id}: {e}")
            self.client = None

    async def get_prices(self) -> List[PriceData]:
        """获取价格数据"""
        if not self.client:
            logger.warning(f"CCXT客户端未初始化: {self.exchange_id}")
            return []

        try:
            # 获取所有tickers
            logger.debug(f"开始获取 {self.exchange_id} tickers...")

            # YoBit 需要特殊参数
            if self.exchange_id == 'yobit':
                tickers = await self.client.fetch_tickers(params={"all": True})
            else:
                tickers = await self.client.fetch_tickers()

            logger.debug(f"{self.exchange_id} 原始获取到 {len(tickers)} 个tickers")

            prices = []
            stablecoin_pairs = 0

            for symbol, ticker in tickers.items():
                # 基础检查
                if not ticker or 'symbol' not in ticker or not ticker.get('last'):
                    continue

                # 分割交易对，例如：BTC/USDT -> (BTC, USDT)
                base, quote = symbol.split('/', 1)

                # 只保留稳定币计价的交易对
                if quote not in STABLECOIN_SYMBOLS:
                    continue

                stablecoin_pairs += 1

                # 提取价格信息
                try:
                    price = self._extract_price(ticker)
                    if price is None or price <= 0:
                        logger.debug(f"{self.exchange_id} {symbol}: 价格无效 {price}")
                        continue

                    price_data = PriceData(
                        symbol=symbol,  # 使用原始符号格式（现货）
                        base_asset=base,
                        quote_asset=quote,
                        price=Decimal(str(price)),
                        volume_24h=self._safe_decimal(ticker.get('quoteVolume')),
                        price_change_24h=self._safe_decimal(ticker.get('percentage'))
                    )
                    prices.append(price_data)

                except (ValueError, TypeError, Exception) as e:
                    logger.debug(f"解析价格数据失败 {symbol}: {e}")
                    continue

            logger.info(f"{self.exchange_id} 获取到 {len(prices)} 个资产价格 (共 {stablecoin_pairs} 个稳定币交易对)")

            # 如果没有价格数据，输出前几个ticker样例用于调试
            if len(prices) == 0 and len(tickers) > 0:
                sample_symbols = list(tickers.keys())[:3]
                logger.warning(f"{self.exchange_id} 未找到有效价格，样例交易对: {sample_symbols}")
                for symbol in sample_symbols:
                    ticker = tickers[symbol]
                    logger.debug(f"{self.exchange_id} {symbol}: {ticker}")

            return prices

        except Exception as e:
            logger.error(f"{self.exchange_id} 获取价格失败: {e}")
            return []

    def _extract_price(self, ticker: Dict) -> Optional[float]:
        """从ticker中提取价格，优先级: last > close > bid/ask平均"""
        if ticker.get('last') is not None:
            return float(ticker['last'])

        if ticker.get('close') is not None:
            return float(ticker['close'])

        bid = ticker.get('bid')
        ask = ticker.get('ask')
        if bid is not None and ask is not None:
            try:
                return (float(bid) + float(ask)) / 2
            except (ValueError, TypeError):
                pass

        return None

    def _safe_decimal(self, value) -> Optional[Decimal]:
        """安全转换为Decimal"""
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except (ValueError, TypeError, Exception):
            return None


class AdapterFactory:
    """适配器工厂"""

    # 支持所有 EXCHANGE_PRIORITY 中的交易所
    ADAPTERS = {exch: (lambda exch=exch: CCXTAdapter(exch)) for exch in EXCHANGE_PRIORITY if exch != 'coinup'}

    @classmethod
    def get_adapter(cls, exchange: str) -> Optional[ExchangeAdapter]:
        """获取交易所适配器"""
        exchange_lower = exchange.lower()
        
        # 特殊处理CoinUp - 使用开源API适配器
        if exchange_lower == 'coinup':
            try:
                from apps.price_oracle.coinup_adapter import CoinUpAdapter
                return CoinUpAdapter()
            except Exception as e:
                logger.error(f"创建CoinUp适配器失败: {e}")
                return None
        
        adapter_factory = cls.ADAPTERS.get(exchange_lower)
        if adapter_factory:
            return adapter_factory()

        # 如果没有找到具体的映射，尝试直接使用CCXTAdapter
        try:
            return CCXTAdapter(exchange_lower)
        except Exception as e:
            logger.error(f"创建适配器失败 {exchange}: {e}")
            return None

    @classmethod
    def get_supported_exchanges(cls) -> List[str]:
        """获取支持的交易所列表"""
        return list(cls.ADAPTERS.keys()) + ['coinup']

    @classmethod
    def get_priority_exchanges(cls) -> List[str]:
        """获取按优先级排序的交易所列表"""
        return [ex for ex in EXCHANGE_PRIORITY if ex in cls.ADAPTERS]


# 便捷函数
async def get_exchange_prices(exchange: str) -> List[PriceData]:
    """获取交易所价格的便捷函数"""
    adapter = AdapterFactory.get_adapter(exchange)
    if not adapter:
        return []

    try:
        prices = await adapter.get_prices()
        await adapter.close()
        return prices
    except Exception as e:
        logger.error(f"获取 {exchange} 价格失败: {e}")
        await adapter.close()
        return []


async def get_all_exchange_prices() -> Dict[str, List[PriceData]]:
    """获取所有支持交易所的价格数据"""
    results = {}

    # 按优先级获取交易所
    priority_exchanges = AdapterFactory.get_priority_exchanges()

    # 并发获取所有交易所的价格
    tasks = []
    for exchange in priority_exchanges:
        task = asyncio.create_task(get_exchange_prices(exchange))
        tasks.append((exchange, task))

    # 等待所有任务完成
    for exchange, task in tasks:
        try:
            prices = await task
            results[exchange] = prices
        except Exception as e:
            logger.error(f"获取 {exchange} 价格失败: {e}")
            results[exchange] = []

    return results
