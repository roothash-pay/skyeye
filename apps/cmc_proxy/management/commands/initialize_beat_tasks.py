import json
from celery.schedules import crontab
from django.core.management.base import BaseCommand
from django.utils import timezone
from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule
import pytz

from skyeye.beat_schedules import DEFAULT_BEAT_SCHEDULE


class Command(BaseCommand):
    help = '将默认定时任务同步到数据库'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='强制覆盖所有任务，包括已存在的任务',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('开始同步定时任务到数据库...'))
        force_update = options.get('force', False)
        
        if not DEFAULT_BEAT_SCHEDULE:
            self.stdout.write(self.style.WARNING('没有找到定时任务配置'))
            return

        created_count = 0
        updated_count = 0
        skipped_count = 0

        for task_name, task_config in DEFAULT_BEAT_SCHEDULE.items():
            try:
                # 提取任务配置
                task_str = task_config['task']
                schedule = task_config['schedule']
                options_config = task_config.get('options', {})
                task_args = task_config.get('args', [])
                task_kwargs = task_config.get('kwargs', {})
                queue = options_config.get('queue', 'celery')
                enabled = task_config.get('enabled', True)

                # 检查任务是否已存在
                existing_task = PeriodicTask.objects.filter(name=task_name).first()
                
                if existing_task and not force_update:
                    self.stdout.write(self.style.NOTICE(f'跳过已存在的任务: {task_name} (使用 --force 强制更新)'))
                    skipped_count += 1
                    continue

                # 创建或获取调度对象
                crontab_schedule = None
                interval_schedule = None
                
                if isinstance(schedule, crontab):
                    # Cron调度 - 强制使用Shanghai时区
                    shanghai_tz = pytz.timezone('Asia/Shanghai')
                    crontab_schedule, _ = CrontabSchedule.objects.get_or_create(
                        minute=self._convert_cron_field(schedule._orig_minute),
                        hour=self._convert_cron_field(schedule._orig_hour),
                        day_of_week=self._convert_cron_field(schedule._orig_day_of_week),
                        day_of_month=self._convert_cron_field(schedule._orig_day_of_month),
                        month_of_year=self._convert_cron_field(schedule._orig_month_of_year),
                        timezone=shanghai_tz
                    )
                elif isinstance(schedule, (int, float)):
                    # 间隔调度(秒)
                    interval_schedule, _ = IntervalSchedule.objects.get_or_create(
                        every=int(schedule),
                        period=IntervalSchedule.SECONDS
                    )
                else:
                    self.stderr.write(self.style.ERROR(f'不支持的调度类型: {task_name}'))
                    continue

                # 创建或更新任务
                defaults = {
                    'task': task_str,
                    'crontab': crontab_schedule,
                    'interval': interval_schedule,
                    'args': json.dumps(task_args),
                    'kwargs': json.dumps(task_kwargs),
                    'queue': queue,
                    'enabled': enabled,
                    'description': f'自动同步 - {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}'
                }

                periodic_task, created = PeriodicTask.objects.update_or_create(
                    name=task_name,
                    defaults=defaults
                )

                if created:
                    created_count += 1
                    self.stdout.write(self.style.SUCCESS(f'✓ 创建任务: {task_name}'))
                else:
                    updated_count += 1
                    self.stdout.write(self.style.NOTICE(f'✓ 更新任务: {task_name}'))

            except Exception as e:
                self.stderr.write(self.style.ERROR(f'处理任务 {task_name} 时出错: {e}'))

        # 显示结果
        self.stdout.write(self.style.SUCCESS(
            f'\n同步完成！创建: {created_count}, 更新: {updated_count}, 跳过: {skipped_count}'
        ))
        
        if skipped_count > 0 and not force_update:
            self.stdout.write(self.style.NOTICE('提示: 使用 --force 参数可强制更新所有任务'))

    def _convert_cron_field(self, field):
        """转换cron字段为字符串"""
        if isinstance(field, (set, frozenset)):
            return ",".join(map(str, sorted(list(field))))
        return str(field)