#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CoinUp价格收集器 - 基于开源API
使用CoinUp官方开源API接口，毫秒级响应，高稳定性
API文档: https://openapi.coinup.io/open/api/get_ticker?symbol=cpusdt
"""

import time
import requests
from decimal import Decimal
from typing import Dict, Optional
from dataclasses import dataclass

from apps.price_oracle.adapters import ExchangeAdapter, PriceData
from common.helpers import getLogger

logger = getLogger(__name__)


@dataclass
class CoinUpConfig:
    """CoinUp API配置"""
    timeout: int = 10
    max_retries: int = 3
    cache_duration: int = 5  # 缓存5秒，支持高频更新
    base_url: str = "https://openapi.coinup.io"


class CoinUpAdapter(ExchangeAdapter):
    """CoinUp价格适配器 - 基于开源API"""
    
    def __init__(self):
        super().__init__('coinup')
        self.config = CoinUpConfig()
        self.session = requests.Session()
        self.session.timeout = self.config.timeout
        self.cached_price: Optional[Dict] = None
        self.last_update: float = 0
        
        # 设置请求头
        self.session.headers.update({
            'User-Agent': 'SkyEye/1.0 (Price Oracle)',
            'Accept': 'application/json',
        })
    
    async def get_prices(self) -> list[PriceData]:
        """获取价格数据 - 主要接口"""
        price_data = self.get_cp_usdt_price()
        return [price_data] if price_data else []
    
    def get_cp_usdt_price(self) -> Optional[PriceData]:
        """获取CP/USDT价格 - 基于开源API"""
        
        # 检查缓存
        if self._is_cache_valid():
            logger.debug("使用缓存价格")
            return self._get_cached_price()
        
        for attempt in range(self.config.max_retries):
            try:
                logger.info(f"获取CP价格 (尝试 {attempt + 1}/{self.config.max_retries})")
                
                # 调用开源API
                url = f"{self.config.base_url}/open/api/get_ticker"
                params = {'symbol': 'cpusdt'}
                
                response = self.session.get(url, params=params)
                response.raise_for_status()
                
                data = response.json()
                
                # 检查响应状态
                if data.get('code') != '0' or not data.get('succ'):
                    logger.warning(f"API返回错误: {data.get('msg', '未知错误')}")
                    continue
                
                # 解析价格数据
                ticker_data = data.get('data', {})
                price_data = self._parse_ticker_data(ticker_data)
                
                if price_data:
                    # 缓存结果
                    self._cache_price(price_data)
                    logger.info(f"成功获取价格: ${price_data.price}")
                    return price_data
                
                logger.warning(f"第{attempt + 1}次尝试解析数据失败")
                
            except requests.exceptions.RequestException as e:
                logger.error(f"API请求失败 (尝试 {attempt + 1}): {e}")
            except Exception as e:
                logger.error(f"获取价格失败 (尝试 {attempt + 1}): {e}")
            
            if attempt < self.config.max_retries - 1:
                time.sleep(1)  # 重试前等待
        
        logger.error("所有尝试都失败")
        return None
    
    def _parse_ticker_data(self, data: Dict) -> Optional[PriceData]:
        """解析ticker数据"""
        try:
            # API返回的数据格式:
            # {
            #   "amount": "271512883.0290797743126",  // 24h成交额
            #   "high": "0.78409",                    // 24h最高价
            #   "vol": "352380374.56219226",          // 24h成交量
            #   "last": 0.7612100000000000,           // 最新价格
            #   "low": "0.75795",                     // 24h最低价
            #   "buy": 0.76076,                       // 买一价
            #   "sell": 0.76289,                      // 卖一价
            #   "rose": "-0.0054612681",              // 24h涨跌幅
            #   "time": 1753156829000                 // 时间戳
            # }
            
            last_price = data.get('last')
            if last_price is None:
                logger.error("API数据中缺少价格字段 'last'")
                return None
            
            # 验证价格合理性
            price = float(last_price)
            if not (0.0001 < price < 100):
                logger.error(f"价格超出合理范围: {price}")
                return None
            
            # 解析24h涨跌幅
            rose = data.get('rose')
            price_change_24h = None
            if rose:
                try:
                    # rose是小数形式，转换为百分比
                    price_change_24h = float(rose) * 100
                except (ValueError, TypeError):
                    logger.warning(f"无法解析24h涨跌幅: {rose}")
            
            # 解析24h成交量
            volume_24h = None
            vol = data.get('vol')
            if vol:
                try:
                    volume_24h = float(vol)
                except (ValueError, TypeError):
                    logger.warning(f"无法解析24h成交量: {vol}")
            
            return PriceData(
                symbol='CP/USDT',
                base_asset='CP',
                quote_asset='USDT',
                price=Decimal(str(price)),
                volume_24h=Decimal(str(volume_24h)) if volume_24h else None,
                price_change_24h=Decimal(str(price_change_24h)) if price_change_24h else None
            )
            
        except Exception as e:
            logger.error(f"解析ticker数据失败: {e}")
            return None
    
    def _is_cache_valid(self) -> bool:
        """检查缓存是否有效"""
        return (
            self.cached_price and 
            time.time() - self.last_update < self.config.cache_duration
        )
    
    def _get_cached_price(self) -> Optional[PriceData]:
        """获取缓存价格"""
        try:
            cached = self.cached_price
            return PriceData(
                symbol=cached['symbol'],
                base_asset=cached['base_asset'],
                quote_asset=cached['quote_asset'],
                price=Decimal(str(cached['price'])),
                volume_24h=Decimal(str(cached['volume_24h'])) if cached.get('volume_24h') else None,
                price_change_24h=Decimal(str(cached['price_change_24h'])) if cached.get('price_change_24h') else None
            )
        except Exception as e:
            logger.error(f"获取缓存价格失败: {e}")
            return None
    
    def _cache_price(self, price_data: PriceData):
        """缓存价格"""
        self.cached_price = {
            'symbol': price_data.symbol,
            'base_asset': price_data.base_asset,
            'quote_asset': price_data.quote_asset,
            'price': float(price_data.price),
            'volume_24h': float(price_data.volume_24h) if price_data.volume_24h else None,
            'price_change_24h': float(price_data.price_change_24h) if price_data.price_change_24h else None,
        }
        self.last_update = time.time()
    
    async def close(self):
        """关闭会话"""
        try:
            self.session.close()
            logger.info("HTTP会话已关闭")
        except Exception as e:
            logger.error(f"关闭会话失败: {e}")


# 便捷函数
def get_coinup_price() -> Optional[PriceData]:
    """获取CoinUp价格（API版本）"""
    adapter = CoinUpAdapter()
    
    try:
        return adapter.get_cp_usdt_price()
    finally:
        import asyncio
        asyncio.run(adapter.close())


# 测试函数
def test_coinup_api_adapter():
    """测试CoinUp API适配器"""
    print("=== 测试CoinUp API适配器 ===")
    
    adapter = CoinUpAdapter()
    
    try:
        start_time = time.time()
        price_data = adapter.get_cp_usdt_price()
        elapsed = time.time() - start_time
        
        if price_data:
            print(f"✅ 价格: {price_data.symbol} = ${price_data.price}")
            print(f"   响应时间: {elapsed:.3f}秒 ⚡")
            if price_data.volume_24h:
                print(f"   24h成交量: {price_data.volume_24h}")
            if price_data.price_change_24h:
                print(f"   24h变化: {price_data.price_change_24h:.4f}%")
        else:
            print("❌ 未获取到价格")
            
        # 测试缓存
        print("\n=== 测试缓存机制 ===")
        start_time = time.time()
        cached_price = adapter.get_cp_usdt_price()
        cached_elapsed = time.time() - start_time
        
        if cached_price:
            print(f"✅ 缓存价格: ${cached_price.price}")
            print(f"   缓存响应时间: {cached_elapsed:.3f}秒 ⚡")
        
    finally:
        import asyncio
        asyncio.run(adapter.close())


if __name__ == "__main__":
    test_coinup_api_adapter()