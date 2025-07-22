#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CoinUp价格收集器 - 基于页面标题解析（备用方案）
⚠️ 注意：此版本为浏览器自动化备用方案，已被API版本替代
仅在API不可用时使用，正常情况下使用 coinup_adapter.py (API版本)
高效的标题解析方案，6秒内完成价格收集
"""

import re
import time
from decimal import Decimal
from typing import Dict, Optional
from dataclasses import dataclass

from DrissionPage import ChromiumPage, ChromiumOptions
from apps.price_oracle.adapters import ExchangeAdapter, PriceData
from common.helpers import getLogger

logger = getLogger(__name__)


@dataclass
class CoinUpConfig:
    """CoinUp配置"""
    headless: bool = True
    timeout: int = 30
    max_retries: int = 3
    cache_duration: int = 10  # 缓存10秒，支持实时价格


class CoinUpBrowserAdapter(ExchangeAdapter):
    """CoinUp价格适配器 - 基于标题解析"""
    
    def __init__(self):
        super().__init__('coinup')
        self.config = CoinUpConfig()
        self.page: Optional[ChromiumPage] = None
        self.cached_price: Optional[Dict] = None
        self.last_update: float = 0
        self._init_browser()
    
    def _init_browser(self):
        """初始化浏览器 - 最小化配置"""
        try:
            co = ChromiumOptions()
            co.headless(self.config.headless)
            
            # 性能优化配置
            co.set_argument('--no-sandbox')
            co.set_argument('--disable-dev-shm-usage')
            co.set_argument('--disable-gpu')
            co.set_argument('--disable-images')  # 不加载图片
            # 注意：不能禁用JavaScript，因为标题可能是动态生成的
            # co.set_argument('--disable-javascript')  
            co.set_argument('--disable-css')  # 不需要CSS
            co.set_argument('--disable-plugins')
            co.set_argument('--disable-extensions')
            
            # 反检测
            co.set_argument('--disable-blink-features=AutomationControlled')
            co.set_user_agent("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36")
            
            self.page = ChromiumPage(addr_or_opts=co)
            self.page.set.timeouts(base=self.config.timeout)
            
            logger.info("CoinUp浏览器初始化成功")
            
        except Exception as e:
            logger.error(f"初始化浏览器失败: {e}")
            raise
    
    async def get_prices(self) -> list[PriceData]:
        """获取价格数据 - 主要接口"""
        price_data = self.get_cp_usdt_price()
        return [price_data] if price_data else []
    
    def get_cp_usdt_price(self) -> Optional[PriceData]:
        """获取CP/USDT价格 - 直接从标题解析"""
        
        # 检查缓存
        if self._is_cache_valid():
            logger.debug("使用缓存价格")
            return self._get_cached_price()
        
        for attempt in range(self.config.max_retries):
            try:
                logger.info(f"获取CP价格 (尝试 {attempt + 1}/{self.config.max_retries})")
                
                # 直接访问页面获取标题
                self.page.get("https://www.coinup.io/en_US/trade/CP_USDT")
                
                # 等待标题加载（标题可能是JS动态生成的）
                time.sleep(5)
                
                # 解析标题中的价格
                title = self.page.title
                logger.info(f"页面标题: {title}")
                
                if title:
                    price_data = self._extract_price_from_title(title)
                    if price_data:
                        # 缓存结果
                        self._cache_price(price_data)
                        logger.info(f"成功获取价格: ${price_data.price}")
                        return price_data
                
                logger.warning(f"第{attempt + 1}次尝试未获取到价格")
                
                if attempt < self.config.max_retries - 1:
                    time.sleep(2)  # 重试前等待
                    
            except Exception as e:
                logger.error(f"获取价格失败 (尝试 {attempt + 1}): {e}")
                if attempt < self.config.max_retries - 1:
                    time.sleep(2)
        
        logger.error("所有尝试都失败")
        return None
    
    def _extract_price_from_title(self, title: str) -> Optional[PriceData]:
        """从标题提取价格信息"""
        try:
            # 支持多种标题格式
            patterns = [
                r'(\d+\.\d+)\s+CP/USDT',        # "0.75982 CP/USDT"
                r'(\d+\.\d+)\s+cp/usdt',        # 小写版本
                r'CP/USDT\s+(\d+\.\d+)',        # "CP/USDT 0.75982"
                r'cp/usdt\s+(\d+\.\d+)',        # 小写版本
                r'(\d+\.\d+).*CP.*USDT',        # 更宽松的匹配
                r'CP.*USDT.*(\d+\.\d+)',        # CP在前，价格在后
            ]
            
            for pattern in patterns:
                match = re.search(pattern, title, re.IGNORECASE)
                if match:
                    try:
                        price = float(match.group(1))
                        # 验证价格合理性 (CP价格通常在0.001-100之间)
                        if 0.0001 < price < 100:
                            
                            # 尝试从标题提取更多信息
                            volume_24h = self._extract_volume_from_title(title)
                            change_24h = self._extract_change_from_title(title)
                            
                            return PriceData(
                                symbol='CP/USDT',
                                base_asset='CP',
                                quote_asset='USDT',
                                price=Decimal(str(price)),
                                volume_24h=Decimal(str(volume_24h)) if volume_24h else None,
                                price_change_24h=Decimal(str(change_24h)) if change_24h else None
                            )
                    except (ValueError, TypeError):
                        continue
            
            logger.warning(f"无法从标题提取价格: {title}")
            return None
            
        except Exception as e:
            logger.error(f"解析标题失败: {e}")
            return None
    
    def _extract_volume_from_title(self, title: str) -> Optional[float]:
        """从标题提取成交量（如果有）"""
        try:
            # 查找成交量信息
            volume_patterns = [
                r'volume[:\s]+(\d+\.?\d*[KMB]?)',
                r'vol[:\s]+(\d+\.?\d*[KMB]?)',
                r'(\d+\.?\d*[KMB]?)\s*vol',
            ]
            
            for pattern in volume_patterns:
                match = re.search(pattern, title, re.IGNORECASE)
                if match:
                    volume_str = match.group(1).upper()
                    
                    # 处理K/M/B后缀
                    multiplier = 1
                    if volume_str.endswith('K'):
                        multiplier = 1000
                        volume_str = volume_str[:-1]
                    elif volume_str.endswith('M'):
                        multiplier = 1000000
                        volume_str = volume_str[:-1]
                    elif volume_str.endswith('B'):
                        multiplier = 1000000000
                        volume_str = volume_str[:-1]
                    
                    return float(volume_str) * multiplier
            
            return None
            
        except Exception:
            return None
    
    def _extract_change_from_title(self, title: str) -> Optional[float]:
        """从标题提取24h变化（如果有）"""
        try:
            # 查找变化百分比
            change_patterns = [
                r'([+-]?\d+\.?\d*)%',
                r'change[:\s]+([+-]?\d+\.?\d*)',
                r'([+-]?\d+\.?\d*)\s*change',
            ]
            
            for pattern in change_patterns:
                match = re.search(pattern, title, re.IGNORECASE)
                if match:
                    return float(match.group(1))
            
            return None
            
        except Exception:
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
        """关闭浏览器"""
        try:
            if self.page:
                self.page.quit()
                logger.info("浏览器已关闭")
        except Exception as e:
            logger.error(f"关闭浏览器失败: {e}")


# 便捷函数
def get_coinup_price_browser(headless: bool = True) -> Optional[PriceData]:
    """获取CoinUp价格（浏览器版本 - 备用方案）"""
    adapter = CoinUpBrowserAdapter()
    adapter.config.headless = headless
    
    try:
        return adapter.get_cp_usdt_price()
    finally:
        import asyncio
        asyncio.run(adapter.close())


# 测试函数
def test_coinup_browser_adapter():
    """测试CoinUp浏览器适配器（备用方案）"""
    print("=== 测试CoinUp浏览器适配器（备用方案） ===")
    
    adapter = CoinUpBrowserAdapter()
    adapter.config.headless = False  # 便于观察
    
    try:
        price_data = adapter.get_cp_usdt_price()
        if price_data:
            print(f"✅ 价格: {price_data.symbol} = ${price_data.price}")
            if price_data.volume_24h:
                print(f"   成交量: {price_data.volume_24h}")
            if price_data.price_change_24h:
                print(f"   24h变化: {price_data.price_change_24h}%")
        else:
            print("❌ 未获取到价格")
    finally:
        import asyncio
        asyncio.run(adapter.close())


if __name__ == "__main__":
    test_coinup_browser_adapter()