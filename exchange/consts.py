# -*- coding: utf-8 -*-

from django.conf import settings

EXCHANGE_MARKETS_KEY = 'crawler:%s:markets'

EXCHANGE_TICKERS_KEY = 'crawler:%s:%s:tickers'
NRDS_EXCHANGE_TICKERS_KEY = 'new:redis:crawler:%s:%s:tickers'

EXCHANGE_ORDERBOOKS_KEY = 'crawler:%s:%s:orderbooks'
NRDS_EXCHANGE_ORDERBOOKS_KEY = 'new:redis:crawler:%s:%s:orderbooks'

HIST_VOLA_KEY = 'crawler:%s:histvolatilti'

SYMBOL_MERGE_ORDERBOOKS_KEY = 'crawler:%s:merge_orderbooks'
NRDS_SYMBOL_MERGE_ORDERBOOKS_KEY = 'new:redis:crawler:%s:merge_orderbooks'

SYMBOL_PRICE_KEY = 'crawler:%s:%s:price'
API_RESPONSE_KEY = 'crawler:%s:api_name'

EXPIRE_TIME_INTERVAL = 5

# unit second
SLEEP_CONFIG = {
    "crawler_fetch_24tickers": 30,
    "crawler_fetch_markets": 60,
    "crawler_fetch_orderbooks": 3,
    "crawler_merge_orderbooks": 2
}

SLEEP_CONFIG.update(settings.CRAWLER_SLEEP_CONFIG)

EXCHANGE_FUNDING_RATE_KEY = 'trade:%s:%s:funding_rates'  # exchange/symbol: trade:huobi:BTC-USD:funding_rates

EXCHANGE_BLOCKING = 'exchange:%s:%s'
EXCHANGE_SYMBOL_MARKETS = 'exchange_markets:%s'  # 'exchange_markets:bitmex'

PENALTY_UNFINISHED_ORDERS = 'penalty_unfinished_orders'
LAST_USDT_USDS_TIMESTAMP = 'last_usdt_usds_timestamp'
