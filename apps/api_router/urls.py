from typing import Any, List

from django.urls import path

from apps.cmc_proxy.views import CmcKlinesView, CmcMarketDataView
from apps.price_oracle.views import get_price
from apps.token_economics.views import TokenAllocationView
from apps.token_holdings.views import token_holdings_api
from apps.token_unlocks.views import TokenUnlockView
from apps.api_router.views import health_check, ping

urlpatterns: List[Any] = [
    path(r'health', health_check, name='health_check'),
    path(r'ping', ping, name='ping'),
    path(r'cmc/market-data', CmcMarketDataView.as_view(), name='cmc_market_data'),
    path(r'cmc/token-unlocks', TokenUnlockView.as_view(), name='token_unlocks_list'),
    path(r'cmc/token-allocations', TokenAllocationView.as_view(), name='token_allocations'),
    path(r'cmc/klines', CmcKlinesView.as_view(), name='cmc_klines'),
    path(r'cmc/holdings', token_holdings_api, name='cmc_token_holdings'),
    path(r'ccxt/price', get_price, name='ccxt_price'),
]
