#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import socket
import sys
import time
from typing import Iterable, Optional, Set, List

from django.conf import settings

from common.decorators import retry_on
from common.helpers import search_limit, getLogger
from exchange import ccxt_client
from exchange.consts import SLEEP_CONFIG
from exchange.controllers import merge_orderbooks, set_24ticker, set_orderbook
from exchange.models import Exchange, Symbol
from exchange.types import Orderbook

HOSTNAME = socket.gethostname()


class CrawlerService(object):
    symbols: Iterable[Symbol]
    symbol_names: Set[str]
    exchange_name: str
    exchange_client: Optional[ccxt_client.ASYNCCCXTExchange]

    def __init__(self, exchange_name: str):
        self.exchange_name = exchange_name
        if self.exchange_name != 'platform':
            self.exchange = Exchange.objects.get(name=exchange_name)
        else:
            self.exchange = None
        self.logger = getLogger('crawler.service.{}'.format(self.exchange_name))
        self.symbols: List[Symbol] = []
        self.symbol_names: Set[str] = set()
        self.exchange_client = ccxt_client.get_async_client(exchange_name)

    def init_symbols_of_exchange(self):
        if self.exchange_name == 'platform':
            self.symbols = Symbol.objects.filter(status='Active', name__in=settings.MERGE_SYMBOL_CONFIG.keys())
        else:
            self.symbols = self.exchange.symbols.filter(status='Active')
        self.symbol_names = set([sym.name for sym in self.symbols])

    def run(self, action_func):
        self.init_symbols_of_exchange()
        loop = asyncio.get_event_loop()
        func = getattr(self, action_func)
        loop.run_until_complete(func())

    @retry_on()
    async def fetch_24ticker(self, symbol: Symbol) -> None:
        self.logger.debug(f"Attempting fetch_24ticker for {symbol.name}")
        assert self.exchange_client is not None, f'{self} attribute exchange_client is None'
        ccxt_client.select_proxy(self.exchange_client)
        try:
            ticker = await self.exchange_client.fetch_ticker(symbol.name)
            self.logger.debug(f"API call successful for {symbol.name}. Ticker data: {ticker}")
            ticker["timestamp"] = time.time() * 1000
            set_24ticker(self.exchange_name, symbol.name, ticker)
            self.logger.debug(f"set_24ticker completed for {symbol.name}")
        except Exception as e:
            self.logger.error(f"Error during fetch_ticker API call or processing for {symbol.name}", exc_info=True)
            raise

    @retry_on()
    async def fetch_orderbook(self, symbol: Symbol, limit: int) -> None:
        if not limit:
            limit = settings.QUOTE_ORDERBOOK_LIMIT
        assert self.exchange_client is not None, f'{self} attribute exchange_client is None'
        ccxt_client.select_proxy(self.exchange_client)
        if symbol.name in ['BTC-USD', 'ETH-USD']:
            params = {'market_type': 'swap'}
            data = await self.exchange_client.fetch_order_book(symbol.name, params=params)
        else:
            slimit = search_limit(limit)
            assert slimit >= limit, f'slimit {slimit} must be greater than limit {limit}'
            data = await self.exchange_client.fetch_order_book(symbol.name, limit=slimit)
        ob = Orderbook.from_json(data)
        ob.bids = ob.bids[:limit]
        ob.asks = ob.asks[:limit]
        ob.source = "crawler@{HOSTNAME}"
        set_orderbook(self.exchange_name, symbol.name, ob.as_json())

    @retry_on()
    async def fetch_markets(self):
        markets = await self.exchange_client.fetch_markets()
        for data in markets:
            if data['symbol'] not in self.symbol_names:
                self.logger.debug('symbol %s is not related', data['symbol'])
                continue

    async def crawler_fetch_markets(self):
        while True:
            try:
                await self.fetch_markets()
                self.logger.debug('Crawler %s markets success', self.exchange_name)
            except Exception as e:
                self.logger.error('Crawler %s markets fail.', self.exchange_name, exc_info=True)
            await asyncio.sleep(SLEEP_CONFIG['crawler_fetch_markets'])

    async def crawler_fetch_24tickers(self):
        self.logger.info(f"Starting crawler_fetch_24tickers loop for exchange {self.exchange_name}")
        if not self.symbols:
            self.logger.warning("Symbols list is empty, crawler loop will not run.")
            return  # Exit if no symbols
        while True:
            self.logger.debug(f"Starting new ticker fetch cycle for symbols: {self.symbol_names}")
            for symbol in self.symbols:
                self.logger.debug(f"Processing symbol: {symbol.name}")
                try:
                    await self.fetch_24ticker(symbol)
                except Exception as e:
                    self.logger.error(f'Error processing symbol {symbol.name} in main loop.', exc_info=True)
            try:
                sleep_time = SLEEP_CONFIG['crawler_fetch_24tickers']
            except KeyError:
                self.logger.warning("'crawler_fetch_24tickers' not found in SLEEP_CONFIG, using default 60s")
                sleep_time = 60  # Default sleep time
            self.logger.debug(f"Ticker fetch cycle complete. Sleeping for {sleep_time} seconds.")
            await asyncio.sleep(sleep_time)

    async def crawler_fetch_orderbooks(self, limit: int = 15):
        cnt = 0
        while True:
            cnt += 1
            if cnt >= 10:
                self.exchange.refresh_from_db()
                cnt = 0
            if self.exchange.is_active:
                await self.fetch_symbols_orderbooks(limit)
            else:
                self.logger.error('exchange %s is not active', self.exchange_name)
            await asyncio.sleep(SLEEP_CONFIG['crawler_fetch_orderbooks'])

    async def fetch_symbols_orderbooks(self, limit: int):
        for symbol in self.symbols:
            try:
                await self.fetch_orderbook(symbol, limit)
                self.logger.debug(
                    'Crawler %s %s fetch orderbooks succeed',
                    self.exchange_name,
                    symbol.name
                )
            except Exception as e:
                self.logger.error(
                    'Crawler %s %s fetch orderbooks fail',
                    self.exchange_name,
                    symbol.name, exc_info=True
                )
                sys.exit(1)

    async def merge_orderbooks(self, symbol):
        await merge_orderbooks(symbol)

    async def crawler_merge_orderbooks(self):
        while True:
            for symbol in self.symbols:
                try:
                    await self.merge_orderbooks(symbol)
                    self.logger.debug('%s orderbook is merged' % symbol.name)
                except Exception as e:
                    self.logger.error('%s orderbook merging failed' % symbol.name, exc_info=True)
            await asyncio.sleep(SLEEP_CONFIG['crawler_merge_orderbooks'])
