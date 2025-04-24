#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import random
from typing import Optional

import ccxt.async_support as async_ccxt
from ccxt.async_support.base.exchange import Exchange as ASYNCCCXTExchange
from django.conf import settings

from common.helpers import getLogger

logger = getLogger(__name__)


def get_async_client(exchange_name: str) -> Optional[ASYNCCCXTExchange]:
    exchange_class = getattr(async_ccxt, exchange_name)
    exchange_client = exchange_class()
    select_proxy(exchange_client)
    return exchange_client


def select_proxy(exchange_client):
    if settings.C_PROXIES:
        selected = random.choice(settings.C_PROXIES)
        logger.info("async client %s selected proxy %s", exchange_client, selected)
        exchange_client.aiohttp_proxy = "http://%s" % selected
