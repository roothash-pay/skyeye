#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import logging
import pickle
import time
from typing import Optional

from django.db import models

from common.models import BaseModel
from common.redis_client import local_redis

CommonStatus = [(x, x) for x in ['Active', 'Down']]
ExchangeCate = [(x, x) for x in ['Cex', 'Dex']]
SymbolCat = [(x, x) for x in ['Spot', 'Future', 'Option']]

logger = logging.getLogger(__name__)


class CacheManager(models.Manager):
    def filter(self, *args, expire: Optional[int] = None, **kwargs):
        if not expire:
            return super().filter(*args, **kwargs)
        r = local_redis()
        sub_keys = ",".join(f"{k}={v}" for k, v in kwargs.items())
        try:
            pickle_data = r.get(sub_keys)
            assert pickle_data, f'{self} did not get pickle data by {sub_keys} '
            json_data = pickle.loads(pickle_data)
            res = json_data['data']
        except:
            res = super().filter(*args, **kwargs)
            json_data = {'timestamp': time.time(), 'data': res.all()[:]}
            pickle_data = pickle.dumps(json_data)
            if len(pickle_data) < 5E7:
                r.set(sub_keys, pickle_data, ex=expire)
            else:
                logger.warning(f'Cache too large for query {sub_keys}')
        finally:
            return res


class Asset(BaseModel):
    IsStableCoin = [(x, x) for x in ['Yes', 'No']]
    name = models.CharField(
        max_length=100,
        unique=True,
        default='BTC',
        verbose_name='资产名称'
    )
    unit = models.SmallIntegerField(
        default=8,
        verbose_name='资产精度'
    )
    is_stable = models.CharField(
        max_length=100,
        choices=IsStableCoin,
        default='No',
        verbose_name='是否为稳定币'
    )
    status = models.CharField(
        max_length=100,
        choices=CommonStatus,
        default='Active',
        verbose_name='状态'
    )

    class Meta:
        pass

    def __str__(self):
        return self.name

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "unit": self.unit,
            "status": self.status
        }


class Exchange(BaseModel):
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='交易所名称'
    )
    config = models.TextField(
        blank=True,
        verbose_name='配置信息'
    )
    market_type = models.CharField(
        max_length=100,
        choices=ExchangeCate,
        default="Cex",
        verbose_name='交易所类别'
    )
    status = models.CharField(
        max_length=100,
        choices=CommonStatus,
        default='Active',
        verbose_name='状态'
    )

    class Meta:
        pass

    @property
    def is_active(self) -> bool:
        return self.status == 'Active'

    @property
    def is_down(self) -> bool:
        return not self.is_active

    def __str__(self):
        return self.name


class ExchangeAccount(BaseModel):
    exchange = models.ForeignKey(
        Exchange,
        related_name='accounts',
        on_delete=models.CASCADE
    )
    name = models.CharField(
        max_length=100,
        default='default',
        db_index=True
    )
    api_key = models.CharField(
        max_length=100,
        null=False
    )
    encrypted_secret = models.TextField(
        null=False,
        blank=True,
        default=''
    )
    secret = models.CharField(
        max_length=100,
        null=False,
        blank=True,
        default=''
    )
    password = models.CharField(
        max_length=100, null=True, default='', blank=True
    )
    alias = models.CharField(
        max_length=100, null=True, default='', blank=True
    )
    proxy = models.TextField(blank=True, null=True)
    testnet = models.BooleanField(default=False, blank=True)
    status = models.CharField(max_length=100, default='ACTIVE')
    enable = models.BooleanField(default=True)
    info = models.TextField(blank=True, null=True)

    class Meta:
        pass

    def __str__(self) -> str:
        return f'exchange: {self.exchange}, account: {self.name}'

    def to_dict(self):
        return {
            'name': self.exchange,
            'symbol': self.name,
            'api_key': self.api_key,
            'secret': self.secret,
            'alias': self.alias,
        }


class Symbol(BaseModel):
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='交易对名称'
    )
    base_asset = models.ForeignKey(
        Asset, blank=True,
        related_name='base_symbols',
        null=False,
        on_delete=models.CASCADE,
        verbose_name='base资产'
    )
    quote_asset = models.ForeignKey(
        Asset, blank=True,
        related_name='quote_symbols',
        null=False,
        on_delete=models.CASCADE,
        verbose_name='报价资产'
    )
    exchanges = models.ManyToManyField(
        Exchange,
        related_name='symbols',
        through='ExchangeSymbolShip',
        verbose_name='关联交易所'
    )
    status = models.CharField(
        max_length=100,
        choices=CommonStatus,
        default='Active',
        verbose_name='状态'
    )
    category = models.CharField(
        max_length=100,
        choices=SymbolCat,
        default="Spot"
    )

    class Meta:
        pass

    def __str__(self):
        return self.name


class ExchangeSymbolShip(BaseModel):
    symbol = models.ForeignKey(Symbol, db_index=True, on_delete=models.CASCADE)
    exchange = models.ForeignKey(Exchange, db_index=True, on_delete=models.CASCADE)

    class Meta:
        unique_together = [("exchange", "symbol")]

    def to_dict(self):
        return {
            "symbol": self.symbol,
            "exchange": self.exchange,
        }
