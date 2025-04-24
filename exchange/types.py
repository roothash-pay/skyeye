import time
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union

import ntplib
from dateutil.parser import parse
from django.conf import settings
from pytz import timezone

from common.helpers import dec, decstr, d2
from exchange.models import Asset


class Ticker:
    timestamp: float
    buy_price: Decimal
    sell_price: Decimal
    exchange: Optional[str] = None

    def as_json(self) -> Dict[str, Any]:
        asj = {
            'timestamp': self.timestamp,
            'buy_price': decstr(self.buy_price),
            'sell_price': decstr(self.sell_price),
        }
        if self.exchange:
            asj['exchange'] = self.exchange
        return asj


class KlineEntry:
    open: Union[Decimal, str]
    high: Union[Decimal, str]
    low: Union[Decimal, str]
    close: Union[Decimal, str]
    volume: Union[Decimal, str]
    timestamp: Union[int, str]

    @classmethod
    def from_list(cls, item: List[Any]) -> 'KlineEntry':
        entry = KlineEntry()
        entry.open = dec(str(item[1]))
        entry.high = dec(str(item[2]))
        entry.low = dec(str(item[3]))
        entry.close = dec(str(item[4]))
        entry.volume = dec(str(item[5]))
        entry.timestamp = int(item[0])
        return entry

    def to_json(self, to_string=True) -> Dict[str, Any]:
        ret = {'timestamp': self.timestamp}
        for attr in ['open', 'high', 'low', 'close', 'volume']:
            value = getattr(self, attr)
            if to_string:
                ret[attr] = decstr(value)
            else:
                ret[attr] = value
        return ret


class OrderEntry:
    price: Decimal
    amount: Decimal

    @classmethod
    def from_json(cls, data: List[Any]) -> 'OrderEntry':
        order = OrderEntry()
        order.price = dec(str(data[0]))
        order.amount = dec(str(data[1]))
        return order

    @property
    def price_str(self) -> str:
        return '{:f}'.format(self.price)

    def as_json(self) -> List[Any]:
        return [self.price_str, float(self.amount)]

    def __str__(self) -> str:
        return '[{}, {}]'.format(self.price_str, self.amount)


class Orderbook:
    timestamp: Union[int, float, None]
    bids: List[OrderEntry]
    asks: List[OrderEntry]
    exchange: Optional[str] = None
    source: Optional[str] = None

    # bitmex specific fields
    nonce: Optional[str] = None
    datetime: Optional[str] = None

    def __init__(self):
        self.bids = []
        self.asks = []
        self.timestamp = time.time() * 1000
        self.exchange = None

    def mid_price(self) -> Decimal:
        return self.asks[0].price / d2 + self.bids[0].price / d2

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> 'Orderbook':
        ob = Orderbook()
        ob.bids = [OrderEntry.from_json(d) for d in data['bids']]
        ob.asks = [OrderEntry.from_json(d) for d in data['asks']]
        ob.exchange = data.get('exchange', '')
        ob.nonce = data.get('nonce')
        ob.datetime = data.get('datetime')
        ob.source = data.get('source')

        ob.timestamp = data['timestamp']
        if not ob.timestamp:
            try:
                ntp_time = ntplib.NTPClient().request(settings.NTP_TIME_SERVER).tx_time
                ob.timestamp = int(ntp_time * 1000)  # ms
            except Exception:
                ob.timestamp = time.time() * 1000
        return ob

    @classmethod
    def from_hb_swap_json(cls, data: Dict[str, Any]) -> 'Orderbook':
        ob = Orderbook()
        ob.timestamp = data['ts']
        ob.bids = [OrderEntry.from_json(d) for d in data['bids']]
        ob.asks = [OrderEntry.from_json(d) for d in data['asks']]
        ob.exchange = data.get('exchange', '')
        ob.nonce = data.get('nonce')
        ob.datetime = data.get('datetime')
        ob.source = data.get('source')
        return ob

    def as_json(self) -> Dict[str, Any]:
        asj = {
            'timestamp': self.timestamp,
            'bids': [order.as_json() for order in self.bids],
            'asks': [order.as_json() for order in self.asks],
        }
        if self.exchange:
            asj['exchange'] = self.exchange  # type: ignore
        if self.nonce:
            asj['nonce'] = self.nonce  # type: ignore
        if self.datetime:
            asj['datetime'] = self.datetime  # type: ignore
        if self.source:
            asj['source'] = self.source  # type: ignore
        return asj

    def selfie_entries(self, side: str) -> List[OrderEntry]:
        if side == 'BUY':
            return self.bids
        else:
            return self.asks

    def trading_entries(self, side: str) -> List[OrderEntry]:
        if side == 'BUY':
            return self.asks
        else:
            return self.bids


class OrderBookL2(object):
    id: int
    symbol: str
    side: str
    size: Decimal
    price: Decimal

    @classmethod
    def from_json(cls, data: List[Any]) -> List['OrderBookL2']:
        result = []
        for item in data:
            orderbook = OrderBookL2()
            orderbook.id = item['id']
            orderbook.symbol = item['symbol']
            orderbook.side = item['side']
            orderbook.size = item['size']
            orderbook.price = item['price']
            result.append(orderbook)
        return result


class Instrument:
    min_order_amount: Decimal
    name: str
    base_asset: Asset
    close_at: datetime
    status: str
    expiration_timestamp: int
    strike: Decimal
    option_type: str

    @classmethod
    def from_json(cls, data: List[Any]) -> List['Instrument']:
        results = []
        for item in data:
            instrument = Instrument()
            instrument.status = 'ACTIVE' if item['is_active'] else 'DISABLE'
            instrument.min_order_amount = dec(item['min_trade_amount'])

            if 'option_type' not in item:
                continue
            name = item['instrument_name']
            # 我们这里的base和quote相反
            instrument.base_asset = Asset.objects.get(name=item['quote_currency'])
            instrument.close_at = datetime.fromtimestamp(item['expiration_timestamp'] / 1000).astimezone(
                timezone('UTC'))
            instrument.name = name
            instrument.expiration_timestamp = item['expiration_timestamp']
            instrument.strike = dec(item['strike'])
            instrument.option_type = item['option_type'].lower()
            results.append(instrument)
        return results

    @classmethod
    def from_okex_json(cls, data: List[Dict[str, Any]]) -> List['Instrument']:
        results = []
        for item in data:
            instrument = Instrument()
            instrument.status = 'ACTIVE' if item['state'] == '2' else 'DISABLE'
            instrument.min_order_amount = dec(item['contract_val'])
            instrument.base_asset = Asset.objects.get(name='USD')
            delivery_dt = parse(item['delivery'])
            instrument.close_at = parse(item['delivery'])
            instrument.name = item['instrument_id']
            instrument.expiration_timestamp = int(time.mktime(delivery_dt.timetuple()))
            instrument.strike = dec(item['strike'])
            if item['option_type'] == 'C':
                option_type = 'call'
            else:
                assert item['option_type'] == 'P', f'value of item["option_type"] ' \
                                                   f'must be "P", not {item["option_type"]}'
                option_type = 'put'
            instrument.option_type = option_type
            results.append(instrument)
        return results
