#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import time
from itertools import groupby
from operator import attrgetter
from typing import Any, Dict, List, Optional, Tuple

from asgiref.sync import sync_to_async
from django.conf import settings

from common.helpers import dec, getLogger
from common.redis_client import global_redis, local_redis
from exchange.consts import (
    EXCHANGE_ORDERBOOKS_KEY,
    EXCHANGE_TICKERS_KEY,
    NRDS_EXCHANGE_ORDERBOOKS_KEY,
    NRDS_EXCHANGE_TICKERS_KEY,
    NRDS_SYMBOL_MERGE_ORDERBOOKS_KEY,
    SYMBOL_MERGE_ORDERBOOKS_KEY,
    EXCHANGE_BLOCKING
)
from exchange.exceptions import OrderbookNotFound
from exchange.models import Symbol
from exchange.types import Orderbook, OrderEntry

logger = getLogger(__name__)

EXCHANGE_BLOCKING_PERIOD = 60 * 5


def set_exchange_account_blocking(exg_name: str, api_account: str):
    key = EXCHANGE_BLOCKING % (exg_name, api_account)
    data = dict(blocking=True)
    value = json.dumps(data)
    global_redis().set(key, value, timeout=EXCHANGE_BLOCKING_PERIOD)


def get_exchange_account_blocking(exg_name: str, api_account: str):
    key = EXCHANGE_BLOCKING % (exg_name, api_account)
    value = global_redis().get(key)
    try:
        if value:
            data = json.loads(value)
            return data["blocking"]
        else:
            return False
    except (KeyError, ValueError):
        return False


def set_24ticker(
        exchange_name: str, symbol: str, data: Dict[str, Any], timeout: int = 120
) -> None:
    key = EXCHANGE_TICKERS_KEY % (exchange_name, symbol)
    zkey = NRDS_EXCHANGE_TICKERS_KEY % (exchange_name, symbol)
    if "timestamp" not in data or data["timestamp"] is None:
        tmstp = int(time.time() * 1000)
        data["timestamp"] = tmstp
    else:
        tmstp = int(data["timestamp"])

    tmstp_seconds = tmstp / 1000
    current_time_seconds = time.time()
    assert current_time_seconds - 300 < tmstp_seconds < current_time_seconds + 300, \
        f"incorrect timestamp {tmstp} (seconds: {tmstp_seconds}), current time {current_time_seconds}"

    tsmp_score = int(tmstp_seconds)
    ticker_json = json.dumps(data)
    tiker_map = {ticker_json: tsmp_score}

    redis_local = local_redis()
    redis_global = global_redis()

    logger.info(
        f"Attempting to ZADD to local Redis (DB 2). Key: {zkey}, Score: {tsmp_score}, Member: {ticker_json[:100]}...")
    try:
        zadd_result = redis_local.zadd(zkey, tiker_map)
        logger.info(f"ZADD result for key {zkey}: {zadd_result} (1 means new element added)")
    except Exception as e:
        logger.error(f"Error during ZADD to key {zkey}", exc_info=True)
        return

    remove_until_score = tsmp_score - 1200
    logger.info(f"Attempting to ZREMRANGEBYSCORE for key {zkey}. Removing scores from 0 to {remove_until_score}")
    try:
        removed_count = redis_local.zremrangebyscore(zkey, 0, remove_until_score)
        logger.info(f"ZREMRANGEBYSCORE result for key {zkey}: removed {removed_count} elements.")
    except Exception as e:
        logger.error(f"Error during ZREMRANGEBYSCORE for key {zkey}", exc_info=True)

    logger.info(f"Attempting to SET key in global_redis (Django Cache): {key}")
    try:
        redis_global.set(key, ticker_json, timeout=timeout)
        logger.info(f"SET completed for key {key} in global_redis (Django Cache)")
    except Exception as e:
        logger.error(f"Error during SET to key {key} in global_redis (Django Cache)", exc_info=True)


def get_24ticker(
        exchange_name: str, symbol: str, timeout: int = 120
) -> Optional[Dict[str, Any]]:
    key = EXCHANGE_TICKERS_KEY % (exchange_name, symbol)
    data = global_redis().get(key)
    if data:
        ticker = json.loads(data)
        if time.time() - ticker["timestamp"] < timeout:
            return ticker
        else:
            return ticker
    else:
        return None


def get_history_24ticker(
        exchange_name: str, symbol: str, timestamp: int = 0, timeout: int = 120
):
    zkey = NRDS_EXCHANGE_TICKERS_KEY % (exchange_name, symbol)
    score_end = timestamp or int(time.time())
    score_start = score_end - 1200
    data = local_redis().zrevrangebyscore(zkey, score_end, score_start)
    if len(data) > 0:
        ticker = json.loads(data[-1].decode())
        if time.time() - ticker["timestamp"] < timeout:
            return ticker
        else:
            return ticker
    else:
        return None


def get_orderbook(exchange_name: str, symbol_name: str) -> Orderbook:
    key = NRDS_EXCHANGE_ORDERBOOKS_KEY % (exchange_name, symbol_name)
    # key = EXCHANGE_ORDERBOOKS_KEY % (exchange_name, symbol_name)
    # data = global_redis().get(key)

    logger.info(f"get_orderbook_key: {key}")
    score_end = int(time.time())
    score_start = score_end - 1200
    data = local_redis().zrevrangebyscore(key, score_end, score_start)
    if not data:
        raise OrderbookNotFound(f"{exchange_name} {symbol_name}")
    p = json.loads(data[-1].decode())
    p.setdefault("exchange", exchange_name)
    return Orderbook.from_json(p)


def get_history_orderbook(
        exchange_name: str, symbol: str, timestamp: int = 0
) -> Orderbook:
    return get_history_orderbook_lst(exchange_name, symbol, timestamp)[-1]


def get_history_orderbook_lst(
        exchange_name: str, symbol: str, timestamp: Optional[int] = None
) -> List[Orderbook]:
    key = NRDS_EXCHANGE_ORDERBOOKS_KEY % (exchange_name, symbol)
    score_start = (timestamp or int(time.time())) - 1200
    score_end = int(time.time())
    data = local_redis().zrangebyscore(key, score_start, score_end)
    if not data:
        raise OrderbookNotFound(f"{exchange_name}.{symbol}")
    data2ob = lambda _data: Orderbook.from_json(dict(exchange=exchange_name, **json.loads(_data.decode())))
    return list(map(data2ob, data))


class OrderbookDelayError(Exception):
    pass


def set_orderbook(exchange_name: str, symbol: str, data: Dict[str, Any]) -> None:
    assert all(key in data for key in ("source", "bids", "asks", "timestamp")), \
        f'{data} must have attribute ' \
        f'("source", "bids", "asks", "timestamp")'
    assert data["timestamp"], f'{data} attribute "timestamp" is None'
    key = EXCHANGE_ORDERBOOKS_KEY % (exchange_name, symbol)
    logger.info(f"global_redis_key: {key}")
    ts_new = data.get("timestamp", None)
    try:
        existing = global_redis().get(key)
        if existing:
            ob_data = json.loads(existing)
            ts_cur = ob_data.get("timestamp", None)
            if ts_cur and ts_new and ts_cur > ts_new:
                raise OrderbookDelayError
    except OrderbookDelayError:
        logger.info(f"{exchange_name}.{symbol}: {data['source']} data rejected.")
    else:
        ts_lag = time.time() * 1000 - ts_new
        logger.info(f"{exchange_name}.{symbol}: {data['source']} data accepted. ts_lag {ts_lag:.4f} ms")
        global_redis().set(key, json.dumps(data))  # timeout=None)
    zkey = NRDS_EXCHANGE_ORDERBOOKS_KEY % (exchange_name, symbol)
    tsmp = int(int(data["timestamp"]) / 1000)  # milliseconds to seconds
    current = int(time.time())
    assert current - 300 < tsmp < current + 300, f"incorrect tsmp {tsmp}, current {current}"
    orderbook_map = {json.dumps(data): tsmp}
    logger.debug(f"orderbook_map: {orderbook_map}")
    local_redis().zadd(zkey, orderbook_map)
    local_redis().zremrangebyscore(zkey, 0, tsmp - 1200)


def get_merged_orderbook(symbol_name: str) -> Orderbook:
    key = SYMBOL_MERGE_ORDERBOOKS_KEY % symbol_name
    dbdata = global_redis().get(key)
    if not dbdata:
        raise OrderbookNotFound(f"merged {symbol_name}")
    data: Dict[str, Any] = json.loads(dbdata)
    return Orderbook.from_json(data)


def set_merged_orderbook(symbol_name: str, orderbook: Orderbook) -> None:
    logger.info(f"set_merged_orderbook: {symbol_name}")
    key = SYMBOL_MERGE_ORDERBOOKS_KEY % symbol_name
    global_redis().set(key, json.dumps(orderbook.as_json()))
    zkey = NRDS_SYMBOL_MERGE_ORDERBOOKS_KEY % symbol_name
    if orderbook.timestamp is None:
        tsmp = int(time.time())
    else:
        tsmp = int(int(orderbook.timestamp) / 1000)
    assert int(time.time()) - 300 < tsmp < int(time.time()) + 300, f"incorrect tsmp {tsmp}"
    merged_orderbook_map = {json.dumps(orderbook.as_json()): tsmp}
    logger.debug(f"merged_orderbook_map: {merged_orderbook_map}")
    local_redis().zadd(zkey, merged_orderbook_map)
    local_redis().zremrangebyscore(zkey, 0, tsmp - 1200)  # remove expired data


def get_history_merged_orderbook(symbol_name: str, timestamp: int = 0) -> Orderbook:
    zkey = NRDS_SYMBOL_MERGE_ORDERBOOKS_KEY % symbol_name
    score_end = timestamp or int(time.time())
    score_start = score_end - 1200
    dbdata = local_redis().zrevrangebyscore(zkey, score_end, score_start)
    if len(dbdata) == 0:
        raise OrderbookNotFound(f"merged {symbol_name}")
    data: Dict[str, Any] = json.loads(dbdata[-1].decode())
    return Orderbook.from_json(data)


def get_perpetual_orderbook() -> Orderbook:
    for ex_name, symbol_name in [
        ("bitmex", "BTC/USD"),
        ("okx", "BTC-USD-SWAP"),
        ("huobi", "BTC-USD"),
    ]:
        try:
            return get_orderbook(ex_name, symbol_name)
        except OrderbookNotFound:
            pass
    raise OrderbookNotFound(f"{ex_name} {symbol_name}")


def merge_order_list(old: List[OrderEntry], new: List[OrderEntry], reverse=False):
    output: List[OrderEntry] = []
    mixed = sorted(old + new, key=lambda ent: ent.price)
    for k, _ents in groupby(mixed, key=lambda ent: ent.price_str):
        ents = list(_ents)
        order = OrderEntry()
        order.price = dec(k)
        order.amount = dec(sum(e.amount for e in ents))
        output.append(order)
    return sorted(output, key=attrgetter("price"), reverse=reverse)


def save_merged_ob(symbol, orderbook, messages):
    toggle = True
    bids, asks = orderbook.bids, orderbook.asks
    # 交叉盘/锁定盘处理。正常的单一交易所订单簿中，最高买价 应该永远低于 最低卖价
    while bids and asks and bids[0].price >= asks[0].price:
        bids, asks = (bids[1:], asks[:]) if toggle else (bids[:], asks[1:])
        toggle = not toggle
    bids_hidden = len(orderbook.bids) - len(bids)
    if bids_hidden:
        logger.warning(f"{symbol.name}.{symbol.exchanges.name}: {bids_hidden} layers are hidden from bid-side merged orderbook.")
        messages['bids_hidden'] = bids_hidden
        orderbook.bids = bids
    asks_hidden = len(orderbook.asks) - len(asks)
    if asks_hidden:
        logger.warning(f"{symbol.name}.{symbol.exchanges.name}: {asks_hidden} layers are hidden from ask-side merged orderbook.")
        messages['asks_hidden'] = asks_hidden
        orderbook.asks = asks
    # if bids_hidden or asks_hidden:
    #     logger.warning(messages)
    # else:
    #     logger.debug(messages)
    set_merged_orderbook(symbol.name, orderbook)


def merge_usds_orderbooks(symbol: Symbol):
    orderbook = Orderbook()
    symbols_dict = settings.EXCHANGE_FUTURES_SYMBOLS[symbol.quote_asset.name]

    # TODO: what if symbols_dict is empty
    groups = []
    for exchange_name, symbols in symbols_dict.items():
        try:
            ob = get_orderbook(exchange_name, symbols[0])
        except OrderbookNotFound:
            continue
        groups.append({
            'symbol': symbols[0],
            'timestamp': ob.timestamp,
            'source': ob.source,
            'exchange': ob.exchange,
            'detail': ob.as_json()
        })
        orderbook.bids = merge_order_list(orderbook.bids, ob.bids, reverse=True)
        orderbook.asks = merge_order_list(orderbook.asks, ob.asks)
    messages = {
        'groups': groups,
        'bids': [bid.as_json() for bid in orderbook.bids],
        'asks': [ask.as_json() for ask in orderbook.asks],
        'asks_hidden': 0,
        'bids_hidden': 0,
    }
    return orderbook, messages


async def merge_orderbooks(symbol: Symbol):
    if symbol.name in ['BTC/USDS', 'ETH/USDS']:
        orderbook, messages = merge_usds_orderbooks(symbol)
    else:
        orderbook, messages = await merge_usdt_orderbooks(symbol)
    save_merged_ob(symbol, orderbook, messages)


SPOT_EXG: Dict[str, Tuple[List, int]] = {}
SPOT_EXG_UPDATE_INTERVAL = 60


async def merge_usdt_orderbooks(symbol: Symbol):
    global SPOT_EXG, SPOT_EXG_UPDATE_INTERVAL

    @sync_to_async
    def get_active_cex_exchanges(sym):
        return list(sym.exchanges.filter(market_type="Cex", status="Active")[:])

    if symbol.name not in SPOT_EXG or SPOT_EXG[symbol.name][1] + SPOT_EXG_UPDATE_INTERVAL < time.time():
        exchanges = await get_active_cex_exchanges(symbol)
        last_update = int(time.time())
        SPOT_EXG[symbol.name] = exchanges, last_update

    groups = []
    orderbook = Orderbook()

    try:
        exchange_names = list(settings.MERGE_SYMBOL_CONFIG[symbol.name].keys())
    except KeyError:
        logger.warning(f"Symbol {symbol.name} not found in MERGE_SYMBOL_CONFIG. Skipping merge.")
        return orderbook, {}  # Return empty orderbook and messages

    @sync_to_async
    def get_filtered_exchanges(sym, names):
        return list(sym.exchanges.filter(market_type="Cex", status="Active", name__in=names))

    filtered_exchanges = await get_filtered_exchanges(symbol, exchange_names)
    for exchange in filtered_exchanges:
        try:
            ob = get_orderbook(exchange.name, symbol.name)
        except OrderbookNotFound:
            logger.warning(f"Orderbook not found for {exchange.name} {symbol.name}. Skipping.")
            continue

        if symbol.category == "Spot":
            groups.append({
                'symbol': symbol.name,
                'timestamp': ob.timestamp,
                'source': ob.source,
                'exchange': ob.exchange,
                'detail': ob.as_json()
            })
            orderbook.bids = merge_order_list(orderbook.bids, ob.bids, reverse=True)
            orderbook.asks = merge_order_list(orderbook.asks, ob.asks)
    messages = {
        'groups': groups,
        'bids': [bid.as_json() for bid in orderbook.bids],
        'asks': [ask.as_json() for ask in orderbook.asks],
        'asks_hidden': 0,
        'bids_hidden': 0,
    }
    return orderbook, messages
