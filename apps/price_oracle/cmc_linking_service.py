#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CMC和CCXT数据关联服务
用于将价格数据与CMC资产信息关联
"""

from typing import Optional, List, Dict
from django.db import transaction
from common.helpers import getLogger

logger = getLogger(__name__)


class CmcLinkingService:
    """CMC资产关联服务"""
    
    @staticmethod
    def link_asset_price_to_cmc(asset_price):
        """
        将AssetPrice实例关联到CMC资产
        
        Args:
            asset_price: AssetPrice实例
            
        Returns:
            bool: 是否成功关联
        """
        if asset_price.cmc_asset:
            # 已经有关联，跳过
            return True
            
        try:
            from apps.cmc_proxy.models import CmcAsset
            
            # 通过symbol直接匹配
            cmc_asset = CmcAsset.objects.filter(
                symbol__iexact=asset_price.base_asset
            ).first()
            
            if cmc_asset:
                asset_price.cmc_asset = cmc_asset
                asset_price.save(update_fields=['cmc_asset'])
                logger.debug(f"成功关联 {asset_price.base_asset} -> CMC资产 {cmc_asset.name}")
                return True
            else:
                logger.debug(f"未找到CMC资产匹配: {asset_price.base_asset}")
                return False
                
        except Exception as e:
            logger.error(f"关联CMC资产失败 {asset_price.base_asset}: {e}")
            return False
    
    @staticmethod
    def batch_link_asset_prices():
        """
        批量关联所有未关联的AssetPrice
        
        Returns:
            Dict: 关联结果统计
        """
        from apps.price_oracle.models import AssetPrice
        
        # 获取所有未关联CMC的价格记录
        unlinked_prices = AssetPrice.objects.filter(cmc_asset__isnull=True)
        
        total = unlinked_prices.count()
        linked_count = 0
        failed_count = 0
        
        logger.info(f"开始批量关联，共 {total} 个未关联的价格记录")
        
        for asset_price in unlinked_prices:
            if CmcLinkingService.link_asset_price_to_cmc(asset_price):
                linked_count += 1
            else:
                failed_count += 1
        
        result = {
            'total': total,
            'linked': linked_count,
            'failed': failed_count,
            'success_rate': f"{(linked_count/total*100):.1f}%" if total > 0 else "0%"
        }
        
        logger.info(f"批量关联完成: {result}")
        return result
    
    @staticmethod
    def get_cmc_asset_by_symbol(symbol: str) -> Optional:
        """
        通过symbol查找CMC资产（增强版匹配算法）
        
        Args:
            symbol: 资产符号
            
        Returns:
            CmcAsset实例或None
        """
        try:
            from apps.cmc_proxy.models import CmcAsset
            from django.db.models import Q
            
            original_symbol = symbol.upper()
            
            # 1. 直接匹配
            asset = CmcAsset.objects.filter(symbol__iexact=original_symbol).first()
            if asset:
                return asset
            
            # 2. 符号标准化匹配（去除特殊字符）
            normalized_symbol = original_symbol.replace('-', '').replace('_', '').replace('.', '')
            asset = CmcAsset.objects.filter(symbol__iexact=normalized_symbol).first()
            if asset:
                return asset
            
            # 3. 去除特殊符号前缀 ($, $$, #, @等)
            cleaned_symbol = original_symbol
            if original_symbol.startswith('$$'):
                cleaned_symbol = original_symbol[2:]
            elif original_symbol.startswith(('$', '#', '@', '&')):
                cleaned_symbol = original_symbol[1:]
            
            if cleaned_symbol != original_symbol:
                asset = CmcAsset.objects.filter(symbol__iexact=cleaned_symbol).first()
                if asset:
                    logger.debug(f"使用前缀清理匹配: {symbol} -> {cleaned_symbol}")
                    return asset
            
            # 4. 去除数字后缀 (PEPE2 -> PEPE, TRUMP404 -> TRUMP)
            import re
            no_suffix_symbol = re.sub(r'\d+$', '', original_symbol)
            if no_suffix_symbol != original_symbol and len(no_suffix_symbol) >= 2:
                # 优先选择CMC ID较小的（通常是原始项目）
                asset = CmcAsset.objects.filter(symbol__iexact=no_suffix_symbol).order_by('cmc_id').first()
                if asset:
                    logger.debug(f"使用数字后缀清理匹配: {symbol} -> {no_suffix_symbol}")
                    return asset
            
            # 5. 包装代币映射
            wrapper_mapping = {
                'WBTC': 'BTC',      # Wrapped Bitcoin
                'WETH': 'ETH',      # Wrapped Ethereum
                'WBNB': 'BNB',      # Wrapped BNB
                'WMATIC': 'MATIC',  # Wrapped MATIC
                'WAVAX': 'AVAX',    # Wrapped AVAX
                'WSOL': 'SOL',      # Wrapped SOL
                'WDOGE': 'DOGE',    # Wrapped DOGE
                'WADA': 'ADA',      # Wrapped ADA
                'WDOT': 'DOT',      # Wrapped DOT
            }
            
            mapped_symbol = wrapper_mapping.get(original_symbol)
            if mapped_symbol:
                asset = CmcAsset.objects.filter(symbol__iexact=mapped_symbol).first()
                if asset:
                    logger.debug(f"使用包装代币映射: {symbol} -> {mapped_symbol}")
                    return asset
            
            # 6. 组合清理策略（去前缀+去后缀）
            combined_cleaned = re.sub(r'\d+$', '', cleaned_symbol)
            if combined_cleaned != original_symbol and len(combined_cleaned) >= 2:
                asset = CmcAsset.objects.filter(symbol__iexact=combined_cleaned).order_by('cmc_id').first()
                if asset:
                    logger.debug(f"使用组合清理匹配: {symbol} -> {combined_cleaned}")
                    return asset
            
            # 7. 模糊匹配（通过name字段）
            if len(original_symbol) >= 3:
                # 查找name中包含symbol的资产
                fuzzy_assets = CmcAsset.objects.filter(
                    Q(name__icontains=original_symbol) | 
                    Q(slug__icontains=original_symbol.lower())
                ).order_by('cmc_id')[:3]  # 限制结果数量
                
                for asset in fuzzy_assets:
                    # 简单的相似度检查
                    if (original_symbol.lower() in asset.name.lower() or 
                        original_symbol.lower() in asset.slug.lower()):
                        logger.debug(f"使用模糊匹配: {symbol} -> {asset.name}")
                        return asset
            
            return None
            
        except Exception as e:
            logger.error(f"查找CMC资产失败 {symbol}: {e}")
            return None
    
    @staticmethod
    def create_asset_price_with_cmc_link(price_data_dict: Dict) -> Optional:
        """
        创建AssetPrice并自动关联CMC资产
        
        Args:
            price_data_dict: 价格数据字典
            
        Returns:
            AssetPrice实例或None
        """
        try:
            from apps.price_oracle.models import AssetPrice
            
            base_asset = price_data_dict.get('base_asset')
            if not base_asset:
                logger.error("price_data_dict缺少base_asset字段")
                return None
            
            # 查找CMC资产
            cmc_asset = CmcLinkingService.get_cmc_asset_by_symbol(base_asset)
            
            # 添加CMC关联到数据字典
            if cmc_asset:
                price_data_dict['cmc_asset'] = cmc_asset
                logger.debug(f"为 {base_asset} 找到CMC资产: {cmc_asset.name}")
            
            # 创建或更新AssetPrice
            asset_price, created = AssetPrice.objects.update_or_create(
                base_asset=base_asset,
                defaults=price_data_dict
            )
            
            action = "创建" if created else "更新"
            logger.debug(f"{action}价格记录: {base_asset} = ${asset_price.price}")
            
            return asset_price
            
        except Exception as e:
            logger.error(f"创建AssetPrice失败: {e}")
            return None
    
    @staticmethod
    def get_linking_statistics() -> Dict:
        """
        获取关联统计信息
        
        Returns:
            Dict: 统计信息
        """
        try:
            from apps.price_oracle.models import AssetPrice
            
            total_prices = AssetPrice.objects.count()
            linked_prices = AssetPrice.objects.filter(cmc_asset__isnull=False).count()
            unlinked_prices = total_prices - linked_prices
            
            return {
                'total_asset_prices': total_prices,
                'linked_to_cmc': linked_prices,
                'unlinked': unlinked_prices,
                'link_rate': f"{(linked_prices/total_prices*100):.1f}%" if total_prices > 0 else "0%"
            }
            
        except Exception as e:
            logger.error(f"获取关联统计失败: {e}")
            return {}


# 便捷函数
def link_asset_price_to_cmc(asset_price):
    """便捷函数：关联单个AssetPrice到CMC"""
    return CmcLinkingService.link_asset_price_to_cmc(asset_price)


def batch_link_all_prices():
    """便捷函数：批量关联所有价格"""
    return CmcLinkingService.batch_link_asset_prices()


def create_price_with_cmc_link(price_data):
    """便捷函数：创建带CMC关联的价格记录"""
    return CmcLinkingService.create_asset_price_with_cmc_link(price_data)