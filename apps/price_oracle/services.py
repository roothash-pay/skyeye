#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from decimal import Decimal
from typing import Dict, List, Optional

from django.db import transaction
from django.utils import timezone
from datetime import timedelta

from apps.price_oracle.models import AssetPrice
from apps.price_oracle.cmc_linking_service import CmcLinkingService
from common.helpers import getLogger

logger = getLogger(__name__)


class PriceService:
    def save_prices_to_db_batch(self, prices: List[Dict]) -> int:
        """批量保存价格数据到数据库"""
        if not prices:
            return 0

        try:
            # 预处理数据
            update_records = []
            create_records = []
            existing_assets = set()

            # 获取已存在的资产
            price_assets = [p.get('base_asset', '').upper() for p in prices if p.get('base_asset')]
            if price_assets:
                existing_assets = set(
                    AssetPrice.objects.filter(
                        base_asset__in=price_assets
                    ).values_list('base_asset', flat=True)
                )

            # 分离更新和创建
            for price_data in prices:
                base_asset = price_data.get('base_asset', '').upper()
                if not base_asset:
                    continue

                # 查找CMC资产关联
                cmc_asset = CmcLinkingService.get_cmc_asset_by_symbol(base_asset)
                
                record_data = {
                    'base_asset': base_asset,
                    'symbol': price_data.get('symbol', ''),
                    'quote_asset': price_data.get('quote_asset', ''),
                    'exchange': price_data.get('exchange', ''),
                    'price': self._safe_decimal(price_data.get('price')),
                    'price_change_24h': self._safe_decimal(price_data.get('price_change_24h')),
                    'volume_24h': self._safe_decimal(price_data.get('volume_24h')),
                    'exchange_priority': price_data.get('exchange_priority', 999),
                    'quote_priority': price_data.get('quote_priority', 999),
                    'price_timestamp': timezone.now(),
                    'cmc_asset': cmc_asset,  # 自动关联CMC资产
                }

                if base_asset in existing_assets:
                    update_records.append(record_data)
                else:
                    create_records.append(AssetPrice(**record_data))

            saved_count = 0

            with transaction.atomic():
                # 批量创建新记录
                if create_records:
                    AssetPrice.objects.bulk_create(
                        create_records,
                        batch_size=1000,
                        ignore_conflicts=True
                    )
                    saved_count += len(create_records)
                    logger.debug(f"批量创建 {len(create_records)} 条新记录")

                # 批量更新现有记录
                if update_records:
                    for record in update_records:
                        AssetPrice.objects.filter(
                            base_asset=record['base_asset']
                        ).update(**{k: v for k, v in record.items() if k != 'base_asset'})
                    saved_count += len(update_records)
                    logger.debug(f"批量更新 {len(update_records)} 条记录")

            if saved_count > 0:
                logger.info(f"批量保存 {saved_count} 个价格到数据库")

            return saved_count

        except Exception as e:
            logger.error(f"批量保存价格失败: {e}")
            return 0

    def save_prices_to_db_upsert(self, prices: List[Dict]) -> int:
        """使用UPSERT操作"""
        if not prices:
            return 0

        try:
            # 预处理数据，去重（同一批次中如果有多个相同base_asset，只保留最优的）
            deduplicated_prices = {}

            for price_data in prices:
                base_asset = price_data.get('base_asset', '').upper()
                if not base_asset:
                    continue

                # 如果已存在相同base_asset，比较优先级（更小的优先级更好）
                if base_asset in deduplicated_prices:
                    existing = deduplicated_prices[base_asset]
                    current_exchange_priority = price_data.get('exchange_priority', 999)
                    current_quote_priority = price_data.get('quote_priority', 999)

                    existing_exchange_priority = existing.get('exchange_priority', 999)
                    existing_quote_priority = existing.get('quote_priority', 999)

                    # 先比较交易所优先级，再比较报价货币优先级
                    if (current_exchange_priority < existing_exchange_priority or
                            (current_exchange_priority == existing_exchange_priority and
                             current_quote_priority < existing_quote_priority)):
                        deduplicated_prices[base_asset] = price_data
                else:
                    deduplicated_prices[base_asset] = price_data

            if not deduplicated_prices:
                return 0

            # 创建记录对象并关联CMC资产
            upsert_records = []
            for price_data in deduplicated_prices.values():
                base_asset = price_data.get('base_asset', '').upper()
                
                # 查找CMC资产关联
                cmc_asset = CmcLinkingService.get_cmc_asset_by_symbol(base_asset)
                
                record = AssetPrice(
                    base_asset=base_asset,
                    symbol=price_data.get('symbol', ''),
                    quote_asset=price_data.get('quote_asset', ''),
                    exchange=price_data.get('exchange', ''),
                    price=self._safe_decimal(price_data.get('price')),
                    price_change_24h=self._safe_decimal(price_data.get('price_change_24h')),
                    volume_24h=self._safe_decimal(price_data.get('volume_24h')),
                    exchange_priority=price_data.get('exchange_priority', 999),
                    quote_priority=price_data.get('quote_priority', 999),
                    price_timestamp=timezone.now(),
                    cmc_asset=cmc_asset,  # 自动关联CMC资产
                )
                upsert_records.append(record)

            # PostgreSQL UPSERT 操作
            with transaction.atomic():
                AssetPrice.objects.bulk_create(
                    upsert_records,
                    update_conflicts=True,
                    update_fields=[
                        'symbol', 'quote_asset', 'exchange', 'price',
                        'price_change_24h', 'volume_24h', 'exchange_priority',
                        'quote_priority', 'price_timestamp', 'cmc_asset'
                    ],
                    unique_fields=['base_asset'],
                    batch_size=2000
                )

            saved_count = len(upsert_records)
            logger.info(f"UPSERT操作保存 {saved_count} 个价格到数据库 (去重后 {len(prices)}->{saved_count})")
            return saved_count

        except Exception as e:
            logger.error(f"UPSERT保存价格失败: {e}")
            # 回退到批量操作
            return self.save_prices_to_db_batch(prices)

    def _safe_decimal(self, value) -> Decimal:
        """安全转换为Decimal类型"""
        if value is None or value == '':
            return Decimal('0')
        try:
            return Decimal(str(value))
        except (ValueError, TypeError):
            return Decimal('0')

    def get_asset_price(self, base_asset: str) -> Optional[AssetPrice]:
        """获取指定资产的最优价格"""
        try:
            return AssetPrice.objects.filter(base_asset=base_asset.upper()).first()
        except Exception as e:
            logger.error(f"获取价格失败 {base_asset}: {e}")
            return None

    def get_all_prices(self) -> List[AssetPrice]:
        """获取所有资产的最优价格"""
        try:
            return list(AssetPrice.objects.all().order_by('base_asset'))
        except Exception as e:
            logger.error(f"获取所有价格失败: {e}")
            return []

    def get_best_price(self, base_asset: str) -> Optional[AssetPrice]:
        """获取最佳价格（最新且有效的价格）"""
        try:
            recent_cutoff = timezone.now() - timedelta(minutes=10)
            price_obj = AssetPrice.objects.filter(
                base_asset=base_asset.upper(),
                price_timestamp__gte=recent_cutoff
            ).first()

            if price_obj:
                return price_obj

            return AssetPrice.objects.filter(
                base_asset=base_asset.upper()
            ).first()
        except Exception as e:
            logger.error(f"获取最佳价格失败 {base_asset}: {e}")
            return None

    def get_supported_assets(self) -> List[str]:
        """获取支持的资产列表"""
        try:
            return list(
                AssetPrice.objects.values_list('base_asset', flat=True)
                    .distinct().order_by('base_asset')
            )
        except Exception as e:
            logger.error(f"获取支持资产列表失败: {e}")
            return []


# 全局服务实例
price_service = PriceService()
