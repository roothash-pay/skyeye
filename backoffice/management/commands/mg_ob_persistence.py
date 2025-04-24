import logging
from decimal import Decimal

from django.core.management.base import BaseCommand

from backoffice.models import MgObPersistence
from backoffice.utils import get_usd_cny_rate, get_prices_from_orderbook
from exchange.models import ExchangeSymbolShip

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Updates the database with the latest order book data for all exchange symbols.'

    def handle(self, *args, **options):
        usd_cny_rate = get_usd_cny_rate()

        exchange_symbol_list = ExchangeSymbolShip.objects.all()
        updated_count = 0
        skipped_count = 0

        for exchange_symbol in exchange_symbol_list:
            price_data = get_prices_from_orderbook(symbol=exchange_symbol.symbol, exchange=exchange_symbol.exchange)

            if price_data is not None:
                avg_price, sell_price, buy_price = price_data
                try:
                    cny_price_calculated = avg_price * usd_cny_rate

                    MgObPersistence.objects.update_or_create(
                        symbol=exchange_symbol.symbol,
                        exchange=exchange_symbol.exchange,
                        base_asset=exchange_symbol.symbol.base_asset,
                        quote_asset=exchange_symbol.symbol.quote_asset,
                        defaults={
                            "sell_price": sell_price,
                            "buy_price": buy_price,
                            "usd_price": avg_price,
                            "cny_price": cny_price_calculated,
                            "avg_price": avg_price,
                            "margin": Decimal("0.23"),
                            "ratio": Decimal("0.23")
                        }
                    )
                    updated_count += 1
                except Exception as e:
                    logger.error(
                        f"Database error updating MgObPersistence for "
                        f"{exchange_symbol.exchange.name} {exchange_symbol.symbol.name}: {e}",
                        exc_info=True
                    )
                    skipped_count += 1
            else:
                skipped_count += 1

        self.stdout.write(f"Finished MgObPersistence update. Processed: {updated_count}, Skipped: {skipped_count}")
