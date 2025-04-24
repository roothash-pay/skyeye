import logging
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand

from backoffice.models import MgObPersistence
from backoffice.utils import get_usd_cny_rate, get_prices_from_orderbook
from exchange.models import Symbol

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Updates the database with the latest MERGED order book data for configured symbols.'

    def handle(self, *args, **options):
        usd_cny_rate = get_usd_cny_rate()
        if usd_cny_rate is None:
            self.stderr.write(self.style.ERROR("Failed to get USD/CNY rate. Aborting."))
            return

        symbols_to_merge = list(settings.MERGE_SYMBOL_CONFIG.keys())
        symbol_objects = Symbol.objects.filter(name__in=symbols_to_merge, status='Active')

        updated_count = 0
        created_count = 0
        skipped_count = 0

        self.stdout.write(f"Found {len(symbol_objects)} active symbols configured for merging: {symbols_to_merge}")

        for symbol in symbol_objects:
            self.stdout.write(f"Processing symbol: {symbol.name}...")
            try:
                price_data = get_prices_from_orderbook(symbol=symbol, exchange=None)

                if price_data is None:
                    skipped_count += 1
                    continue

                avg_price, sell_price, buy_price = price_data

                cny_price_calculated = avg_price * usd_cny_rate

                obj, created = MgObPersistence.objects.update_or_create(
                    symbol=symbol,
                    exchange=None,
                    defaults={
                        "base_asset": symbol.base_asset,
                        "quote_asset": symbol.quote_asset,
                        "sell_price": sell_price,
                        "buy_price": buy_price,
                        "usd_price": avg_price,
                        "cny_price": cny_price_calculated,
                        "avg_price": avg_price,
                        "margin": Decimal("2.3"),
                        "ratio": Decimal("2.3")
                    }
                )

                if created:
                    created_count += 1
                    self.stdout.write(self.style.SUCCESS(f"Successfully created merged price record for {symbol.name}"))
                else:
                    updated_count += 1
                    self.stdout.write(f"Successfully updated merged price record for {symbol.name}")

            except Exception as e:
                logger.error(
                    f"Error processing merged data for {symbol.name}: {e}",
                    exc_info=True
                )
                skipped_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Finished Merged MgObPersistence update. "
            f"Created: {created_count}, Updated: {updated_count}, Skipped: {skipped_count}"
        ))
