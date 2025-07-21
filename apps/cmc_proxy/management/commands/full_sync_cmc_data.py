import asyncio
import time

from django.core.management.base import BaseCommand

from apps.cmc_proxy.tasks import _daily_full_data_sync_with_lock
from common.helpers import getLogger

logger = getLogger(__name__)


class Command(BaseCommand):
    help = 'Manually execute full sync of CoinMarketCap data from API to Redis (equivalent to daily 3 AM task)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-db-sync',
            action='store_true',
            help='Skip automatic database sync after full sync (only update Redis cache)'
        )

    def handle(self, *args, **options):
        skip_db_sync = options.get('skip_db_sync', False)
        
        self.stdout.write(self.style.SUCCESS("Starting manual CMC full data sync..."))
        start_time = time.time()
        
        try:
            # 执行全量同步
            tokens_processed = asyncio.run(self._run_full_sync())
            
            elapsed = time.time() - start_time
            
            if tokens_processed > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✅ Full sync completed successfully in {elapsed:.2f} seconds. '
                        f'Processed {tokens_processed} tokens from CoinMarketCap API.'
                    )
                )
                
                if not skip_db_sync:
                    self.stdout.write(self.style.SUCCESS("Starting automatic database sync..."))
                    self._run_db_sync()
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            "⚠️ Database sync skipped. Run 'python manage.py sync_cmc_data --run-once' "
                            "to sync data from Redis to database."
                        )
                    )
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f'❌ Full sync failed or no tokens were processed. '
                        f'Please check the logs for errors.'
                    )
                )
                return
                
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("⚠️ Full sync interrupted by user."))
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Full sync failed with error: {e}')
            )
            logger.error(f"Error during full sync: {e}", exc_info=True)

    async def _run_full_sync(self):
        """执行全量同步任务"""
        return await _daily_full_data_sync_with_lock()

    def _run_db_sync(self):
        """执行数据库同步"""
        from django.core.management import call_command
        
        try:
            call_command('sync_cmc_data', '--run-once', verbosity=1)
            self.stdout.write(self.style.SUCCESS("✅ Database sync completed successfully."))
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Database sync failed: {e}')
            )
            logger.error(f"Error during database sync: {e}", exc_info=True)