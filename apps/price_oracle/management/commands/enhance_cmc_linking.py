#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Django管理命令：使用增强算法重新关联未关联的价格数据
"""

from django.core.management.base import BaseCommand
from django.db import transaction
import re

from apps.price_oracle.models import AssetPrice
from apps.cmc_proxy.models import CmcAsset
from common.helpers import getLogger

logger = getLogger(__name__)


class Command(BaseCommand):
    help = '使用增强算法重新关联未关联的价格数据'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='只显示可以关联的记录，不实际执行',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=100,
            help='处理的记录数量限制（默认100）',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        limit = options['limit']

        self.stdout.write("开始使用增强算法关联未关联的价格数据...")

        # 获取未关联的记录
        unlinked_prices = AssetPrice.objects.filter(cmc_asset_id__isnull=True)[:limit]
        
        self.stdout.write(f"找到 {unlinked_prices.count()} 个未关联记录（限制处理 {limit} 个）")

        linked_count = 0
        mapping_results = []

        for price in unlinked_prices:
            original_symbol = price.base_asset
            matched_asset = None
            match_method = None

            # 1. 去除$符号前缀
            if original_symbol.startswith('$$'):
                cleaned_symbol = original_symbol[2:]
                if cleaned_symbol:  # 确保清理后不为空
                    matched_asset = CmcAsset.objects.filter(symbol__iexact=cleaned_symbol).order_by('cmc_id').first()
                    if matched_asset:
                        match_method = f'去除$$前缀: {original_symbol} -> {cleaned_symbol}'
            elif original_symbol.startswith('$'):
                cleaned_symbol = original_symbol[1:]
                if cleaned_symbol:  # 确保清理后不为空
                    matched_asset = CmcAsset.objects.filter(symbol__iexact=cleaned_symbol).order_by('cmc_id').first()
                    if matched_asset:
                        match_method = f'去除$前缀: {original_symbol} -> {cleaned_symbol}'

            # 2. 去除数字后缀
            if not matched_asset:
                no_suffix_symbol = re.sub(r'\d+$', '', original_symbol)
                if no_suffix_symbol != original_symbol and len(no_suffix_symbol) >= 2:
                    matched_asset = CmcAsset.objects.filter(symbol__iexact=no_suffix_symbol).order_by('cmc_id').first()
                    match_method = f'去除数字后缀: {original_symbol} -> {no_suffix_symbol}'

            # 3. 包装代币映射
            if not matched_asset:
                wrapper_mapping = {
                    'WBTC': 'BTC', 'WETH': 'ETH', 'WBNB': 'BNB',
                    'WMATIC': 'MATIC', 'WAVAX': 'AVAX', 'WSOL': 'SOL'
                }
                mapped_symbol = wrapper_mapping.get(original_symbol)
                if mapped_symbol:
                    matched_asset = CmcAsset.objects.filter(symbol__iexact=mapped_symbol).first()
                    match_method = f'包装代币映射: {original_symbol} -> {mapped_symbol}'

            # 4. 组合策略（先去前缀再去后缀）
            if not matched_asset and original_symbol.startswith('$'):
                cleaned = original_symbol[1:]
                combined_cleaned = re.sub(r'\d+$', '', cleaned)
                if combined_cleaned != original_symbol and len(combined_cleaned) >= 2:
                    matched_asset = CmcAsset.objects.filter(symbol__iexact=combined_cleaned).order_by('cmc_id').first()
                    match_method = f'组合清理: {original_symbol} -> {combined_cleaned}'

            if matched_asset:
                mapping_results.append({
                    'original': original_symbol,
                    'matched': matched_asset.symbol,
                    'name': matched_asset.name,
                    'cmc_id': matched_asset.cmc_id,
                    'method': match_method,
                    'price_obj': price
                })

                if not dry_run:
                    price.cmc_asset = matched_asset
                    price.save(update_fields=['cmc_asset'])
                    linked_count += 1

        # 显示结果
        self.stdout.write(f"\n找到 {len(mapping_results)} 个可以关联的记录:")
        for result in mapping_results[:20]:  # 只显示前20个
            self.stdout.write(f"  {result['method']} -> {result['name']} (CMC ID: {result['cmc_id']})")

        if len(mapping_results) > 20:
            self.stdout.write(f"  ... 还有 {len(mapping_results) - 20} 个匹配")

        if dry_run:
            self.stdout.write(self.style.WARNING(f"\nDRY RUN模式 - 发现可关联 {len(mapping_results)} 个记录"))
        else:
            self.stdout.write(self.style.SUCCESS(f"\n成功关联 {linked_count} 个记录！"))

        # 显示更新后的统计
        if not dry_run:
            from apps.price_oracle.cmc_linking_service import CmcLinkingService
            stats = CmcLinkingService.get_linking_statistics()
            self.stdout.write(f"更新后关联率: {stats.get('link_rate', '0%')}")