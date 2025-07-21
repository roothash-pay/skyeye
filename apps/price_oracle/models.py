#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from django.db import models
from django.utils import timezone
from datetime import timedelta
from common.models import BaseModel


class AssetPrice(BaseModel):
    """资产价格模型 - 每个资产只保留最优价格"""
    
    # 基础信息
    base_asset = models.CharField(max_length=20, unique=True, db_index=True, verbose_name='基础资产')  # BTC
    
    # CMC关联
    cmc_asset = models.ForeignKey(
        'cmc_proxy.CmcAsset', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='asset_prices',
        verbose_name='CMC资产关联'
    )
    
    # 最优价格信息
    symbol = models.CharField(max_length=50, db_index=True, verbose_name='最优交易对符号')  # BTC/USDT
    quote_asset = models.CharField(max_length=20, db_index=True, verbose_name='最优计价资产')  # USDT
    exchange = models.CharField(max_length=50, db_index=True, verbose_name='最优交易所')  # binance
    
    # 价格数据
    price = models.DecimalField(max_digits=20, decimal_places=8, verbose_name='最优价格')
    price_change_24h = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True, verbose_name='24小时价格变化率(%)'
    )
    volume_24h = models.DecimalField(
        max_digits=30, decimal_places=8, null=True, blank=True, verbose_name='24小时成交量'
    )
    
    # 优先级信息
    exchange_priority = models.PositiveIntegerField(default=999, verbose_name='交易所优先级')
    quote_priority = models.PositiveIntegerField(default=999, verbose_name='稳定币优先级')
    
    # 时间戳
    price_timestamp = models.DateTimeField(db_index=True, verbose_name='价格时间戳')
    
    class Meta:
        db_table = 'asset_prices'
        verbose_name = '资产价格'
        verbose_name_plural = '资产价格'
        indexes = [
            models.Index(fields=['base_asset']),
            models.Index(fields=['exchange_priority', 'quote_priority']),
            models.Index(fields=['price_timestamp']),
        ]
    
    def __str__(self):
        return f"{self.base_asset} = ${self.price} ({self.exchange}:{self.symbol})"
    
    @property
    def is_stale(self):
        """检查价格是否过期（超过10分钟）"""

        return timezone.now() - self.price_timestamp > timedelta(minutes=10)
