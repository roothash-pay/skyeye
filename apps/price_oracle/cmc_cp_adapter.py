#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
从CMC获取CP价格的适配器
直接从本地数据库读取CMC同步的CP数据
"""

import asyncio
from decimal import Decimal
from typing import List, Optional
from django.db import connection

from apps.price_oracle.adapters import ExchangeAdapter, PriceData
from common.helpers import getLogger

logger = getLogger(__name__)


class CmcCpAdapter(ExchangeAdapter):
    """CMC CP价格适配器 - 从CMC数据获取CP价格"""
    
    def __init__(self):
        super().__init__('cmc')
        self.cmc_id = 37639  # CP的CMC ID
    
    async def get_prices(self) -> List[PriceData]:
        """获取价格数据"""
        price_data = self.get_cp_price_from_cmc()
        return [price_data] if price_data else []
    
    def get_cp_price_from_cmc(self) -> Optional[PriceData]:
        """从CMC数据获取CP价格"""
        try:
            with connection.cursor() as cursor:
                # 直接从市场数据表获取最新价格
                cursor.execute("""
                    SELECT 
                        cmd.price_usd,
                        cmd.volume_24h,
                        cmd.percent_change_24h,
                        cmd.timestamp,
                        ca.symbol
                    FROM cmc_market_data cmd
                    JOIN cmc_assets ca ON cmd.asset_id = ca.id
                    WHERE ca.cmc_id = %s
                    ORDER BY cmd.timestamp DESC
                    LIMIT 1
                """, [self.cmc_id])
                
                row = cursor.fetchone()
                
                if row:
                    price, volume, change_24h, updated, symbol = row
                    logger.info(f"从CMC获取{symbol}价格: ${price} (更新时间: {updated})")
                    
                    return PriceData(
                        symbol='CP/USDT',
                        base_asset='CP',
                        quote_asset='USDT',
                        price=Decimal(str(price)) if price else Decimal('0'),
                        volume_24h=Decimal(str(volume)) if volume else None,
                        price_change_24h=Decimal(str(change_24h)) if change_24h else None
                    )
                else:
                    logger.error(f"CMC没有CP (cmc_id={self.cmc_id}) 的市场数据")
                    return None
                    
        except Exception as e:
            logger.error(f"从CMC获取CP价格失败: {e}")
            return None
    
    async def close(self):
        """关闭连接"""
        pass  # 数据库连接由Django管理


# 便捷函数
def get_cmc_cp_price() -> Optional[PriceData]:
    """获取CMC的CP价格"""
    adapter = CmcCpAdapter()
    try:
        prices = asyncio.run(adapter.get_prices())
        return prices[0] if prices else None
    finally:
        asyncio.run(adapter.close())


# 测试函数
def test_cmc_cp_adapter():
    """测试CMC CP适配器"""
    print("=== 测试CMC CP价格适配器 ===")
    print(f"CMC ID: 37639")
    print("-" * 40)
    
    adapter = CmcCpAdapter()
    price_data = adapter.get_cp_price_from_cmc()
    
    if price_data:
        print(f"✅ 成功获取CP价格:")
        print(f"   交易对: {price_data.symbol}")
        print(f"   价格: ${price_data.price:.6f}")
        if price_data.volume_24h:
            print(f"   24h成交量: ${price_data.volume_24h:,.2f}")
        else:
            print(f"   24h成交量: 无数据")
        if price_data.price_change_24h:
            print(f"   24h涨跌: {price_data.price_change_24h:.4f}%")
        print("\n数据来源: CMC (CoinMarketCap)")
    else:
        print("❌ 未获取到价格")
        print("\n可能的原因:")
        print("1. 数据库连接问题")
        print("2. CMC没有CP的市场数据")
        print("\n建议运行以下命令同步CMC数据:")
        print("uv run python manage.py sync_cmc_data --run-once")


if __name__ == "__main__":
    test_cmc_cp_adapter()