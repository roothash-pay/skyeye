import logging

from django.conf import settings
from django.core.management.base import BaseCommand

from backoffice.models import OtcAssetPrice
from backoffice.utils import get_usd_cny_rate, get_prices_from_orderbook
from exchange.models import ExchangeSymbolShip

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Calculates and updates OTC asset prices based on exchange order book data and stored USD/CNY rate.'

    def handle(self, *args, **options):
        usd_cny_rate = get_usd_cny_rate()

        exchange_symbol_list = ExchangeSymbolShip.objects.all()
        processed_assets = set()
        updated_count = 0
        skipped_count = 0

        acceptable_quotes = settings.ACCEPTABLE_QUOTE_ASSETS_FOR_OTC

        for exchange_symbol in exchange_symbol_list:
            base_asset_obj = exchange_symbol.symbol.base_asset
            quote_asset_obj = exchange_symbol.symbol.quote_asset

            if base_asset_obj in processed_assets:
                continue

            if quote_asset_obj.name not in acceptable_quotes:
                logger.debug(
                    f"Skipping {exchange_symbol.symbol.name} for OTC price update: "
                    f"Quote asset '{quote_asset_obj.name}' is not in acceptable list {acceptable_quotes}."
                )
                skipped_count += 1
                continue

            price_data = get_prices_from_orderbook(symbol=exchange_symbol.symbol, exchange=None)

            if price_data is not None:
                avg_price, _, _ = price_data
                try:
                    cny_price_calculated = avg_price * usd_cny_rate

                    OtcAssetPrice.objects.update_or_create(
                        asset=base_asset_obj,
                        defaults={
                            "usd_price": avg_price,
                            "cny_price": cny_price_calculated
                        }
                    )
                    processed_assets.add(base_asset_obj)
                    updated_count += 1
                    logger.debug(
                        f"Updated OTC price for asset {base_asset_obj.name} using {exchange_symbol.symbol.name}"
                    )
                except Exception as e:
                    logger.error(
                        f"Database error updating OtcAssetPrice for "
                        f"asset {base_asset_obj.name}: {e}",
                        exc_info=True
                    )
                    skipped_count += 1
            else:
                skipped_count += 1

        self.stdout.write(
            f"Finished updating OTC asset prices. Updated: {updated_count}, Skipped Attempts: {skipped_count}"
        )
