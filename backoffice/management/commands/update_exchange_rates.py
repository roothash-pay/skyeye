import logging
from decimal import Decimal, InvalidOperation

import requests
from django.conf import settings
from django.core.management.base import BaseCommand

from backoffice.models import ExchangeRate

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Fetches the latest USD/CNY exchange rate from Frankfurter API and updates the database.'

    def handle(self, *args, **options):
        self.stdout.write("Attempting to update USD/CNY exchange rate...")

        api_url = settings.FRANKFURTER_API_URL

        try:
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()

            data = response.json()

            if 'rates' in data and 'CNY' in data['rates']:
                try:
                    fetched_rate = Decimal(str(data['rates']['CNY']))

                    rate_obj, created = ExchangeRate.objects.update_or_create(
                        base_currency='USD',
                        quote_currency='CNY',
                        defaults={'rate': fetched_rate}
                    )

                    action = "created" if created else "updated"
                    success_msg = f"Successfully {action} USD/CNY exchange rate to {fetched_rate}"
                    self.stdout.write(self.style.SUCCESS(success_msg))
                    logger.info(success_msg)

                except InvalidOperation:
                    error_msg = f"Error converting fetched rate '{data['rates']['CNY']}' to Decimal."
                    self.stderr.write(self.style.ERROR(error_msg))
                    logger.error(error_msg)
                except Exception as db_err:
                    error_msg = f"Database error updating exchange rate: {db_err}"
                    self.stderr.write(self.style.ERROR(error_msg))
                    logger.error(error_msg, exc_info=True)

            else:
                error_msg = f"Unexpected API response format. 'rates' or 'CNY' key missing. Response: {data}"
                self.stderr.write(self.style.ERROR(error_msg))
                logger.error(error_msg)

        except requests.exceptions.Timeout:
            error_msg = f"Request timed out connecting to {api_url}"
            self.stderr.write(self.style.ERROR(error_msg))
            logger.error(error_msg)
        except requests.exceptions.RequestException as e:
            error_msg = f"Error fetching exchange rate from {api_url}: {e}"
            self.stderr.write(self.style.ERROR(error_msg))
            logger.error(error_msg, exc_info=True)
        except Exception as e:
            error_msg = f"An unexpected error occurred during exchange rate update: {e}"
            self.stderr.write(self.style.ERROR(error_msg))
            logger.error(error_msg, exc_info=True)

        self.stdout.write("Exchange rate update process finished.")
