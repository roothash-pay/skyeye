import logging
from decimal import Decimal
from typing import Optional, Tuple

from django.conf import settings

from backoffice.models import ExchangeRate
from common.helpers import dec
from exchange.controllers import get_history_orderbook, get_history_merged_orderbook
from exchange.exceptions import OrderbookNotFound
from exchange.models import Symbol, Exchange

logger = logging.getLogger(__name__)

def get_usd_cny_rate() -> Decimal:
    """Fetches the USD/CNY exchange rate from the database, with fallback to settings.

    Returns:
        Decimal: The USD/CNY exchange rate
    """
    default_rate = Decimal(settings.DEFAULT_USD_CNY_RATE)
    try:
        # Try fetching from DB first
        rate_obj = ExchangeRate.objects.get(base_currency='USD', quote_currency='CNY')
        usd_cny_rate = rate_obj.rate
        logger.debug(f"Using USD/CNY rate from database: {usd_cny_rate}")
        return usd_cny_rate
    except ExchangeRate.DoesNotExist:
        logger.warning(f"USD/CNY exchange rate not found in database. Using default rate from settings: {default_rate}")
        return default_rate
    except Exception as e:
        logger.error(
            f"Error fetching USD/CNY rate from database: {e}. Falling back to default rate: {default_rate}",
            exc_info=True
        )
        return default_rate # Return default as fallback


def get_prices_from_orderbook(symbol: Symbol, exchange: Optional[Exchange] = None) -> Optional[Tuple[Decimal, Decimal, Decimal]]:
    """Gets avg, sell (best ask), and buy (best bid) prices from the latest order book,
       fetching either merged data (if exchange is None) or specific exchange data.
       Applies flooring logic (via dec()) before returning.

    Args:
        symbol: The Symbol object.
        exchange: Optional Exchange object. If provided, fetch data for this specific exchange.
                  If None, fetch merged order book data for the symbol.

    Returns:
        Optional[Tuple[Decimal, Decimal, Decimal]]: A tuple containing floored (avg_price, sell_price, buy_price),
                                                     or None if fetching/calculation fails.
    """
    source_description = f"merged {symbol.name}" if exchange is None else f"{exchange.name} {symbol.name}"
    try:
        if exchange is None:
            # Fetch merged order book data
            logger.debug(f"Fetching merged order book for {source_description}")
            order_book = get_history_merged_orderbook(symbol.name)
        else:
            # Fetch order book for the specific exchange
            logger.debug(f"Fetching order book for {source_description}")
            order_book = get_history_orderbook(exchange.name, symbol.name)

        if not order_book.bids or not order_book.asks:
            logger.warning(
                f"Skipping {source_description}: Empty bids or asks in order book."
            )
            return None

        # Best bid price (highest price someone is willing to buy at)
        # Note: Assuming bids[0] is highest bid, asks[0] is lowest ask
        buy_price = order_book.bids[0].price
        # Best ask price (lowest price someone is willing to sell at)
        sell_price = order_book.asks[0].price

        # Ensure prices are valid before calculating average
        if sell_price <= 0 or buy_price <= 0:
            logger.warning(
                f"Skipping {source_description}: Invalid sell price ({sell_price}) or buy price ({buy_price})."
            )
            return None
        
        # Check for crossed market (might indicate bad data)
        if sell_price <= buy_price:
            logger.warning(f"Skipping {source_description}: Crossed prices (sell <= buy). Sell: {sell_price}, Buy: {buy_price}")
            return None

        avg_price = (sell_price + buy_price) / Decimal('2')

        # Apply dec() (flooring) before returning
        floored_avg_price = dec(avg_price)
        floored_sell_price = dec(sell_price) # Best ask
        floored_buy_price = dec(buy_price)  # Best bid
        
        # Return avg, best ask (sell), best bid (buy)
        return floored_avg_price, floored_sell_price, floored_buy_price

    except OrderbookNotFound:
        logger.warning(
            f"Skipping {source_description}: Orderbook not found in Redis history."
        )
        return None
    except IndexError:
        # This usually means bids or asks list was empty even if not None initially
        logger.warning(
            f"Skipping {source_description}: Not enough depth in order book (IndexError)."
        )
        return None
    except Exception as e:
        logger.error(
            f"Error processing order book for {source_description}: {e}",
            exc_info=True
        )
        return None
