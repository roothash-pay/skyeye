#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Django管理命令：关联价格数据到CMC资产
用于初始化现有数据的CMC关联
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.price_oracle.cmc_linking_service import CmcLinkingService
from common.helpers import getLogger

logger = getLogger(__name__)


class Command(BaseCommand):
    help = '关联现有的价格数据到CMC资产'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='只显示统计信息，不实际执行关联操作',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='强制重新关联所有记录（包括已关联的）',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='批处理大小（默认1000）',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']
        batch_size = options['batch_size']

        self.stdout.write("开始关联价格数据到CMC资产...")

        # 显示当前统计信息
        stats = CmcLinkingService.get_linking_statistics()
        self.stdout.write(f"当前统计信息:")
        self.stdout.write(f"  总价格记录: {stats.get('total_asset_prices', 0)}")
        self.stdout.write(f"  已关联CMC: {stats.get('linked_to_cmc', 0)}")
        self.stdout.write(f"  未关联: {stats.get('unlinked', 0)}")
        self.stdout.write(f"  关联率: {stats.get('link_rate', '0%')}")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN模式 - 不会执行实际操作"))
            return

        try:
            if force:
                # 强制模式：重新关联所有记录
                self.stdout.write("强制模式：重新关联所有记录...")
                result = self._force_relink_all(batch_size)
            else:
                # 常规模式：只关联未关联的记录
                result = CmcLinkingService.batch_link_asset_prices()

            # 显示结果
            self.stdout.write(self.style.SUCCESS(f"关联完成!"))
            self.stdout.write(f"  处理总数: {result.get('total', 0)}")
            self.stdout.write(f"  成功关联: {result.get('linked', 0)}")
            self.stdout.write(f"  关联失败: {result.get('failed', 0)}")
            self.stdout.write(f"  成功率: {result.get('success_rate', '0%')}")

            # 显示更新后的统计信息
            updated_stats = CmcLinkingService.get_linking_statistics()
            self.stdout.write(f"\n更新后统计:")
            self.stdout.write(f"  关联率: {updated_stats.get('link_rate', '0%')}")

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"关联操作失败: {e}")
            )
            logger.error(f"关联操作失败: {e}")

    def _force_relink_all(self, batch_size=1000):
        """强制重新关联所有记录"""
        from apps.price_oracle.models import AssetPrice

        # 获取所有价格记录
        all_prices = AssetPrice.objects.all()
        total = all_prices.count()
        linked_count = 0
        failed_count = 0

        self.stdout.write(f"开始强制重新关联，共 {total} 个记录")

        # 分批处理
        for i in range(0, total, batch_size):
            batch = all_prices[i:i + batch_size]
            batch_linked = 0
            batch_failed = 0

            with transaction.atomic():
                for asset_price in batch:
                    # 清除现有关联
                    asset_price.cmc_asset = None

                    # 重新关联
                    if CmcLinkingService.link_asset_price_to_cmc(asset_price):
                        batch_linked += 1
                        linked_count += 1
                    else:
                        batch_failed += 1
                        failed_count += 1

            self.stdout.write(f"  批次 {i//batch_size + 1}: 处理 {len(batch)} 条，成功 {batch_linked} 条")

        return {
            'total': total,
            'linked': linked_count,
            'failed': failed_count,
            'success_rate': f"{(linked_count/total*100):.1f}%" if total > 0 else "0%"
        }