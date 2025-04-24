from django.db import models

from common.model_fields import DecField
from common.models import BaseModel
from exchange.models import Symbol, Asset, Exchange


class MgObPersistence(BaseModel):
    symbol = models.ForeignKey(
        Symbol, related_name='price_symbol',
        null=True, blank=True,
        on_delete=models.CASCADE
    )
    exchange = models.ForeignKey(
        Exchange, related_name='price_exchange',
        null=True, blank=True,
        on_delete=models.CASCADE
    )
    base_asset = models.ForeignKey(
        Asset, related_name='base_asset',
        null=True, blank=True,
        on_delete=models.CASCADE
    )
    quote_asset = models.ForeignKey(
        Asset, related_name='quote_asset',
        null=True, blank=True,
        on_delete=models.CASCADE
    )
    sell_price = DecField(default=0)
    buy_price = DecField(default=0)
    usd_price = DecField(default=0)
    cny_price = DecField(default=0)
    avg_price = DecField(default=0)
    margin = DecField(default=0)
    ratio = DecField(default=0)

    class Meta:
        pass

    def as_dict(self):
        return {
            'symbol': self.symbol.name,
            'base_asset': self.base_asset.name,
            'quote_asset': self.quote_asset.name,
            'sell_price': format(self.sell_price, ".4f"),
            'buy_price': format(self.buy_price, ".4f"),
            'avg_price': format(self.avg_price, ".4f"),
            'usd_price': format(self.usd_price, ".4f"),
            'cny_price': format(self.cny_price, ".4f"),
            'margin': format(self.margin, ".2f"),
        }


class OtcAssetPrice(BaseModel):
    asset = models.ForeignKey(
        Asset, related_name='otc_asset',
        null=True, blank=True,
        on_delete=models.CASCADE
    )
    usd_price = DecField(default=0)
    cny_price = DecField(default=0)
    margin = DecField(default=0)

    class Meta:
        pass

    def as_dict(self):
        return {
            'asset': self.asset.name if self.asset else None,
            'usd_price': format(self.usd_price, ".4f"),
            'cny_price': format(self.cny_price, ".4f"),
            'margin': format(self.margin, ".4f")
        }


class ExchangeRate(BaseModel):
    """Stores exchange rates between currencies."""
    base_currency = models.CharField(max_length=10, db_index=True, help_text="e.g., USD")
    quote_currency = models.CharField(max_length=10, db_index=True, help_text="e.g., CNY")
    rate = DecField(default=0, help_text="The exchange rate (1 base_currency = rate * quote_currency)")
    last_updated = models.DateTimeField(auto_now=True, help_text="Timestamp when the rate was last updated")

    class Meta:
        unique_together = ('base_currency', 'quote_currency')  # Ensure only one rate per pair
        verbose_name = "Exchange Rate"
        verbose_name_plural = "Exchange Rates"

    def __str__(self):
        return f"{self.base_currency}/{self.quote_currency}: {self.rate}"
