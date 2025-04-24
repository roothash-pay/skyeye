from django.contrib import admin

from backoffice.models import (
    MgObPersistence,
    OtcAssetPrice
)


@admin.register(MgObPersistence)
class MgObPersistenceAdmin(admin.ModelAdmin):
    list_display = ('id', 'symbol', 'avg_price', 'ratio')


@admin.register(OtcAssetPrice)
class OtcAssetPriceAdmin(admin.ModelAdmin):
    list_display = ('id', 'asset', 'usd_price', 'cny_price')
