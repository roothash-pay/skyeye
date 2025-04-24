# type: ignore

from typing import Any, List

from django.urls import path

from frontend.api_v1.chainup import market_price, asset_otc_price, symbol_market_price

urlpatterns: List[Any] = [
    path(r'market_price', market_price, name='market_price'),
    path(r'asset_otc_price', asset_otc_price, name='asset_otc_price'),
    path(r'symbol_market_price', symbol_market_price, name='symbol_market_price')
]
