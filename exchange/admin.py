from django.contrib import admin

from exchange.models import (
    Asset,
    Exchange,
    ExchangeAccount,
    Symbol,
    ExchangeSymbolShip
)


@admin.register(Asset)
class AssettAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')


@admin.register(Exchange)
class ExchangeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'market_type', 'status', 'created_at')
    list_per_page = 50
    ordering = ('-created_at',)
    list_display_links = ('id', 'name')


@admin.register(ExchangeAccount)
class ExchangeAccountAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'status')


@admin.register(Symbol)
class SymbolAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')


@admin.register(ExchangeSymbolShip)
class ExchangeSymbolShipAdmin(admin.ModelAdmin):
    list_display = ('id', 'symbol', 'exchange', 'created_at')
