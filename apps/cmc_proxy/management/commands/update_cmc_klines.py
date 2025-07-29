import asyncio
import time

from django.core.management.base import BaseCommand

from apps.cmc_proxy.models import CmcAsset, CmcKline
from apps.cmc_proxy.services import get_cmc_service
from common.helpers import getLogger

logger = getLogger(__name__)


class Command(BaseCommand):
    help = 'Fetches and updates CMC klines data for assets.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=3600,  # 默认每小时更新一次
            help='The interval in seconds to run the update task in a loop (default: 3600 seconds).'
        )
        parser.add_argument(
            '--run-once',
            action='store_true',
            help='Run the klines update task once and exit.'
        )
        parser.add_argument(
            '--count',
            type=int,
            default=24,
            help='Number of hourly klines to fetch (default: 24 for 24 hours).'
        )
        parser.add_argument(
            '--cmc-ids',
            type=str,
            help='Comma-separated CMC IDs to update (if not provided, all assets will be processed).'
        )
        parser.add_argument(
            '--top-n',
            type=int,
            help='Only process top N assets by CMC rank (requires market data).'
        )
        parser.add_argument(
            '--initialize',
            action='store_true',
            help='Initialize mode: fetch 24 hours of historical data for assets without klines.'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Batch size for processing assets (default: 100, will be split into API batches of batch_size).'
        )
        parser.add_argument(
            '--delay',
            type=float,
            default=2.0,
            help='Delay between API calls in seconds (default: 2.0, respects CMC rate limit of 30 calls/minute).'
        )

    def handle(self, *args, **options):
        interval = options['interval']
        run_once = options['run_once']
        count = options['count']
        cmc_ids_str = options.get('cmc_ids')
        top_n = options.get('top_n')
        initialize = options['initialize']
        batch_size = options['batch_size']
        delay = options['delay']
        
        # 解析cmc_ids字符串为整数列表
        cmc_ids = None
        if cmc_ids_str:
            try:
                cmc_ids = [int(x.strip()) for x in cmc_ids_str.split(',') if x.strip()]
                logger.info(f"Parsed CMC IDs: {cmc_ids}")
            except ValueError as e:
                self.stdout.write(self.style.ERROR(f"Invalid CMC IDs format: {cmc_ids_str}. Error: {e}"))
                return

        if run_once:
            logger.info("Running CMC klines update task once.")
        else:
            logger.info(f"Starting CMC klines update task to run every {interval} seconds.")

        try:
            asyncio.run(self.run_update_loop(interval, run_once, count, cmc_ids, top_n, initialize, batch_size, delay))
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("Klines update process interrupted by user."))
        except Exception as e:
            logger.error(f"An unhandled exception occurred in the update loop: {e}", exc_info=True)

    async def run_update_loop(self, interval, run_once, count, cmc_ids, top_n, initialize, batch_size, delay):
        cmc_service = None
        try:
            cmc_service = await get_cmc_service()

            while True:
                start_time = time.time()

                logger.info(f"Starting CMC klines data {'initialization' if initialize else 'update'}...")
                result = await cmc_service.process_klines(
                    cmc_ids=cmc_ids,
                    top_n=top_n,
                    count=count,
                    only_missing=initialize,  # 初始化模式只处理缺少数据的资产
                    delay_between_calls=delay,
                    batch_size=batch_size
                )
                self._print_result(result, "initialization" if initialize else "update")

                elapsed = time.time() - start_time
                logger.info(f"CMC klines update finished in {elapsed:.2f} seconds.")

                if run_once:
                    break

                wait_time = max(0.1, interval - elapsed)
                logger.info(f"Waiting for {wait_time:.2f} seconds before next update.")
                await asyncio.sleep(wait_time)

        finally:
            if cmc_service:
                await cmc_service.close()
                logger.info("CMC service connection closed.")

    def _print_result(self, result, operation_type):
        """打印操作结果"""
        self.stdout.write(self.style.SUCCESS(
            f'CMC klines {operation_type} completed. '
            f'Successful: {result["success"]}, '
            f'Failed: {result["failed"]}, '
            f'Total klines stored: {result["total_klines"]}'
        ))
        if result.get('message'):
            self.stdout.write(self.style.SUCCESS(result['message']))
