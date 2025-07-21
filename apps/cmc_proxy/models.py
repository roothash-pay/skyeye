from django.db import models
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.price_oracle.models import AssetPrice
from common.model_fields import DecField
from common.models import BaseModel


class CmcAssetManager(models.Manager):
    async def update_or_create_from_api_data(self, api_data: dict):
        cmc_id = api_data.get('id')
        if not cmc_id:
            return None, False

        defaults = {
            'name': api_data.get('name'),
            'symbol': api_data.get('symbol'),
            'slug': api_data.get('slug'),
            'platform': api_data.get('platform'),
            'num_market_pairs': api_data.get('num_market_pairs'),
            'date_added': api_data.get('date_added'),
            'tags': api_data.get('tags', []),
            'max_supply': api_data.get('max_supply'),
            'infinite_supply': api_data.get('infinite_supply', False),
            'self_reported_circulating_supply': api_data.get('self_reported_circulating_supply'),
            'self_reported_market_cap': api_data.get('self_reported_market_cap'),
            'tvl_ratio': api_data.get('tvl_ratio'),
        }
        # 过滤掉None值，避免用None覆盖已有数据
        defaults = {k: v for k, v in defaults.items() if v is not None}

        return await self.aupdate_or_create(cmc_id=cmc_id, defaults=defaults)


class CmcMarketDataManager(models.Manager):
    async def update_or_create_from_api_data(self, asset, api_data: dict):
        timestamp_str = api_data.get('last_updated')
        timestamp = timezone.now()
        if timestamp_str:
            # 解析 ISO 8601 时间字符串
            dt = parse_datetime(timestamp_str)
            if dt is not None:
                timestamp = timezone.make_aware(dt) if timezone.is_naive(dt) else dt

        defaults = {
            'timestamp': timestamp,
            'circulating_supply': api_data.get('circulating_supply'),
            'total_supply': api_data.get('total_supply'),
            'cmc_rank': api_data.get('cmc_rank'),
        }

        quote_data = api_data.get('quote', {}).get('USD', {})
        if quote_data:
            # 计算 volume_24h_token_count: token 成交量 = volume_24h / price
            price = quote_data.get('price')
            volume_24h = quote_data.get('volume_24h')
            volume_24h_token_count = None
            if price and volume_24h and price > 0:
                volume_24h_token_count = volume_24h / price

            defaults.update({
                'price_usd': quote_data.get('price'),
                'market_cap': quote_data.get('market_cap'),
                'fully_diluted_market_cap': quote_data.get('fully_diluted_market_cap'),
                'volume_24h': quote_data.get('volume_24h'),
                'volume_change_24h': quote_data.get('volume_change_24h'),
                'percent_change_1h': quote_data.get('percent_change_1h'),
                'percent_change_24h': quote_data.get('percent_change_24h'),
                'percent_change_7d': quote_data.get('percent_change_7d'),
                'percent_change_30d': quote_data.get('percent_change_30d'),
                'percent_change_60d': quote_data.get('percent_change_60d'),
                'percent_change_90d': quote_data.get('percent_change_90d'),
                'market_cap_dominance': quote_data.get('market_cap_dominance'),
                'tvl': quote_data.get('tvl'),
                'volume_24h_token_count': volume_24h_token_count,
            })

        # 过滤掉None值，避免用None覆盖已有数据
        defaults = {k: v for k, v in defaults.items() if v is not None}

        # 如果除了时间戳之外没有任何有效数据，可能就不需要更新
        if len(defaults) <= 1:
            return None, False

        return await self.aupdate_or_create(
            asset=asset,
            defaults=defaults,
        )


class CmcKlineManager(models.Manager):
    async def update_or_create_from_api_data(self, asset, quote_data: dict, timeframe='1h'):
        time_open_str = quote_data.get('time_open')
        if not time_open_str:
            return None, False
            
        # 解析开盘时间
        dt = parse_datetime(time_open_str)
        if dt is None:
            return None, False
        timestamp = timezone.make_aware(dt) if timezone.is_naive(dt) else dt
            
        usd_quote = quote_data.get('quote', {}).get('USD', {})
        if not usd_quote:
            return None, False
            
        # 计算token数量交易量
        price = usd_quote.get('close') or usd_quote.get('open')
        volume_usd = usd_quote.get('volume')
        volume_token_count = None
        if price and volume_usd and price > 0:
            volume_token_count = volume_usd / price
            
        defaults = {
            'open': usd_quote.get('open'),
            'high': usd_quote.get('high'),
            'low': usd_quote.get('low'),
            'close': usd_quote.get('close'),
            'volume': volume_usd,
            'volume_token_count': volume_token_count,
        }
        
        # 过滤掉None值
        defaults = {k: v for k, v in defaults.items() if v is not None}
        
        if not defaults:
            return None, False
            
        return await self.aupdate_or_create(
            asset=asset,
            timeframe=timeframe,
            timestamp=timestamp,
            defaults=defaults,
        )


class CmcAsset(BaseModel):
    cmc_id = models.BigIntegerField(unique=True, db_index=True)
    name = models.CharField(max_length=64)
    symbol = models.CharField(max_length=16)
    slug = models.CharField(max_length=64, blank=True, null=True)
    platform = models.JSONField(blank=True, null=True)
    num_market_pairs = models.IntegerField(null=True, blank=True, help_text="Number of market pairs")
    date_added = models.DateTimeField(null=True, blank=True, help_text="Date when asset was added on CMC")
    tags = models.JSONField(default=list, blank=True, help_text="List of tags from CMC")
    max_supply = DecField(null=True, blank=True, decimal_places=0, max_digits=65, help_text="Max supply of the asset")
    infinite_supply = models.BooleanField(default=False, help_text="Whether the supply is infinite")
    self_reported_circulating_supply = DecField(decimal_places=8, max_digits=65, null=True, blank=True, help_text="Self-reported circulating supply")
    self_reported_market_cap = DecField(decimal_places=8, max_digits=65, null=True, blank=True, help_text="Self-reported market cap")
    tvl_ratio = models.FloatField(null=True, blank=True, help_text="TVL ratio")
    # # 关联你自己的 TradingPair（通过 symbol 约定），方便查询
    # trading_pair = models.ForeignKey(
    #     AssetPrice, blank=True, null=True,
    #     on_delete=models.SET_NULL, related_name="cmc_assets"
    # )
    objects = CmcAssetManager()

    class Meta:
        db_table = 'cmc_assets'
        verbose_name = "CMC 币种元信息"
        verbose_name_plural = "CMC 币种元信息"


class CmcMarketData(BaseModel):
    asset = models.OneToOneField(CmcAsset, on_delete=models.CASCADE, related_name="market_data", primary_key=True)
    timestamp = models.DateTimeField(db_index=True, help_text="cmc_api 最后更新时间")
    price_usd = DecField(decimal_places=18, max_digits=40, null=True, blank=True)
    market_cap = DecField(decimal_places=8, max_digits=40, null=True, blank=True)
    fully_diluted_market_cap = DecField(decimal_places=8, max_digits=40, null=True, blank=True)
    volume_24h = DecField(decimal_places=8, max_digits=40, null=True, blank=True)
    volume_change_24h = models.FloatField(null=True, blank=True)
    percent_change_1h = models.FloatField(null=True, blank=True)
    percent_change_24h = models.FloatField(null=True, blank=True)  # 24h 价格变化率，已经是百分比了
    percent_change_7d = models.FloatField(null=True, blank=True)
    percent_change_30d = models.FloatField(null=True, blank=True)
    percent_change_60d = models.FloatField(null=True, blank=True)
    percent_change_90d = models.FloatField(null=True, blank=True)
    market_cap_dominance = models.FloatField(null=True, blank=True)
    tvl = DecField(decimal_places=8, max_digits=40, null=True, blank=True)
    volume_24h_token_count = DecField(decimal_places=8, max_digits=40, null=True)
    circulating_supply = DecField(decimal_places=8, max_digits=40, null=True, blank=True)
    total_supply = DecField(decimal_places=8, max_digits=40, null=True, blank=True)
    cmc_rank = models.IntegerField(null=True, blank=True)
    objects = CmcMarketDataManager()

    class Meta:
        db_table = 'cmc_market_data'
        verbose_name = "CMC 最新行情"
        verbose_name_plural = "CMC 最新行情"
        indexes = [
            models.Index(
                fields=['-market_cap'],
                name='cmc_mktdata_cap_desc_idx',
                condition=models.Q(market_cap__isnull=False, market_cap__gt=0),
            ),
        ]


class CmcKline(BaseModel):
    asset = models.ForeignKey(CmcAsset, on_delete=models.CASCADE, related_name="klines")
    timeframe = models.CharField(max_length=10, db_index=True)  # '1h'
    timestamp = models.DateTimeField(db_index=True)  # 开盘时间
    open = DecField(decimal_places=18, max_digits=40)
    high = DecField(decimal_places=18, max_digits=40)
    low = DecField(decimal_places=18, max_digits=40)
    close = DecField(decimal_places=18, max_digits=40)
    volume = DecField(decimal_places=8, max_digits=40)
    volume_token_count = DecField(decimal_places=8, max_digits=40, null=True)
    objects = CmcKlineManager()

    class Meta:
        db_table = 'cmc_klines'
        unique_together = ("asset", "timeframe", "timestamp")
        verbose_name = "CMC K 线"
        verbose_name_plural = "CMC K 线"
