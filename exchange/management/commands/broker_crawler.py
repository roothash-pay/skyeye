#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import sys

from django.conf import settings
from django.core.management.base import BaseCommand

from common.helpers import getLogger
from exchange.models import Exchange, ExchangeSymbolShip, Symbol
from exchange.service import CrawlerService

logger = getLogger(__name__)


async def sleep_quit(timeout: int = 3600):
    await asyncio.sleep(timeout)
    logger.info('sleep timeout, quit')
    sys.exit(0)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('action', type=str)

    def handle(self, *args, **options):
        if options['action']:
            self.run(**options)

    def fetchable_exchanges(self, require_active: bool = True):
        qs = Exchange.objects.filter(name__in=settings.FETCHABLE_EXCHANGES)
        if require_active:
            # TODO 统一status的大小写
            qs = qs.filter(status='Active')
        return qs

    def run(self, *args, **options):
        loop = asyncio.get_event_loop()
        tasks = [loop.create_task(sleep_quit())]
        if options['action'] == 'crawler_merge_orderbooks':
            for exchange in self.fetchable_exchanges(require_active=False):
                srv = CrawlerService(exchange_name=exchange.name)
                srv.init_symbols_of_exchange()
                tasks.append(loop.create_task(srv.crawler_merge_orderbooks()))

        elif options['action'] == 'crawler_fetch_orderbooks':
            for exchange in self.fetchable_exchanges(require_active=False):
                srv = CrawlerService(exchange_name=exchange.name)
                srv.init_symbols_of_exchange()
                tasks.append(loop.create_task(srv.crawler_fetch_orderbooks()))

        elif options['action'] == 'crawler_fetch_24tickers':
            self.ensure_symbols()
            for exchange in self.fetchable_exchanges():
                srv = CrawlerService(exchange_name=exchange.name)
                srv.init_symbols_of_exchange()
                tasks.append(loop.create_task(srv.crawler_fetch_24tickers()))
        loop.run_until_complete(asyncio.wait(tasks))

    def ensure_symbols(self):
        exsymbols = [
            ('bitmex', ['BTC/USDT']),
            ('huobi', ['BTC/USDT', 'ETH/USDT']),
            ('binance', ['BTC/USDT', 'ETH/USDT'])
        ]
        for exname, symnames in exsymbols:
            exchange = Exchange.objects.get(name=exname)
            for sym in symnames:
                symbol = Symbol.objects.get(name=sym)
                ExchangeSymbolShip.objects.get_or_create(
                    exchange=exchange,
                    symbol=symbol
                )
