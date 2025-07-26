#!/usr/bin/env python3
"""
Redis-based Celery Beat Scheduler
更可靠的替代方案，避免数据库相关问题
"""

import redis
import json
import time
from datetime import datetime, timedelta
from celery.schedules import crontab
from skyeye.beat_schedules import DEFAULT_BEAT_SCHEDULE

class RedisBeatScheduler:
    def __init__(self, redis_url='redis://localhost:6379/0'):
        self.redis_client = redis.from_url(redis_url)
        self.schedule = DEFAULT_BEAT_SCHEDULE
        self.last_run_key = "celery:beat:last_run"
        
    def should_run_task(self, task_name, task_config):
        """检查任务是否应该运行"""
        schedule = task_config['schedule']
        last_run_key = f"{self.last_run_key}:{task_name}"
        
        # 获取上次运行时间
        last_run = self.redis_client.get(last_run_key)
        now = datetime.now()
        
        if last_run is None:
            # 首次运行
            return True
            
        last_run_time = datetime.fromisoformat(last_run.decode())
        
        if isinstance(schedule, (int, float)):
            # 间隔调度
            return (now - last_run_time).total_seconds() >= schedule
        elif isinstance(schedule, crontab):
            # Cron调度 - 简化实现
            return (now - last_run_time).total_seconds() >= 60  # 最小1分钟间隔
            
        return False
    
    def mark_task_run(self, task_name):
        """标记任务已运行"""
        last_run_key = f"{self.last_run_key}:{task_name}"
        self.redis_client.set(last_run_key, datetime.now().isoformat())
    
    def send_task(self, task_name, task_config):
        """发送任务到Celery"""
        from celery import current_app
        
        task_str = task_config['task']
        args = task_config.get('args', [])
        kwargs = task_config.get('kwargs', {})
        queue = task_config.get('options', {}).get('queue', 'celery')
        
        current_app.send_task(
            task_str,
            args=args,
            kwargs=kwargs,
            queue=queue
        )
        
        print(f"[{datetime.now()}] Sent task: {task_name}")
    
    def run(self):
        """主循环"""
        print(f"[{datetime.now()}] Redis Beat Scheduler started")
        
        while True:
            try:
                for task_name, task_config in self.schedule.items():
                    if not task_config.get('enabled', True):
                        continue
                        
                    if self.should_run_task(task_name, task_config):
                        self.send_task(task_name, task_config)
                        self.mark_task_run(task_name)
                
                time.sleep(1)  # 1秒检查间隔
                
            except Exception as e:
                print(f"[{datetime.now()}] Scheduler error: {e}")
                time.sleep(5)  # 出错后等待5秒

if __name__ == "__main__":
    import os
    redis_url = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    scheduler = RedisBeatScheduler(redis_url)
    scheduler.run()