#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
from celery import shared_task
from django.core.management import call_command
from common.helpers import getLogger

logger = getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def collect_prices_task(self):
    """采集价格数据到Redis"""
    try:
        logger.info("开始采集价格数据...")
        call_command('collect_prices')
        logger.info("价格数据采集完成")
        return "SUCCESS"
    except Exception as e:
        logger.error(f"采集价格数据失败: {e}")
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=3)
def persist_prices_task(self):
    """持久化价格数据到数据库"""
    try:
        logger.info("开始持久化价格数据...")
        call_command('persist_prices')
        logger.info("价格数据持久化完成")
        return "SUCCESS"
    except Exception as e:
        logger.error(f"持久化价格数据失败: {e}")
        raise self.retry(exc=e, countdown=30)