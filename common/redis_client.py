#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import time
from typing import Optional, Dict, Any, List, Tuple, Union

import redis.asyncio as aioredis
from django.conf import settings
from django.core.cache import cache as django_redis
from redis import ConnectionPool, StrictRedis
from redis.asyncio import Redis as AsyncRedis

from common.helpers import getLogger
from . import constants

logger = getLogger(__name__)


def set_exchange_balance(exchange_name, balance):
    balance_key_str = constants.BALANCE_KEY % {"exchange_name": exchange_name}
    global_redis().set(balance_key_str, json.dumps(balance))


# def get_exchange_balance(exchange_name):
#     key = constants.BALANCE_KEY % {"exchange_name": exchange_name}
#     exchange_balance = global_redis().get(key)
#     return json.loads(exchange_balance) if exchange_balance else {}


REDIS_POOL = ConnectionPool(**settings.TRADING_REDIS)


def local_redis():
    rsd_client = StrictRedis(connection_pool=REDIS_POOL, decode_responses=True)
    return rsd_client


LOCAL_EXPIRE = 60


class GlobalRedisWrapper:
    instance_global = django_redis
    instance_local = local_redis()

    instance_local_expire: Optional[float] = None

    @staticmethod
    def __instance():
        local_expire = GlobalRedisWrapper.instance_local_expire
        if local_expire is None:
            return GlobalRedisWrapper.instance_global

        ago = time.time() - local_expire
        if ago > 0:
            msg = f"Restore to global redis (local one expired {ago} seconds ago)."
            logger.warning(msg)
            GlobalRedisWrapper.instance_local_expire = None
            return GlobalRedisWrapper.instance_global

        # local is in use
        return GlobalRedisWrapper.instance_local

    @staticmethod
    def __fallback(e: Exception):
        # NOTE: do not fallback twice, set expire only if backup is not in use
        if GlobalRedisWrapper.instance_local_expire is None:
            msg = f"Fallback to local redis (expire in 60 seconds), because of {e}."
            logger.warning(msg)
            GlobalRedisWrapper.instance_local_expire = time.time() + LOCAL_EXPIRE

        # keeping local
        return GlobalRedisWrapper.instance_local

    @staticmethod
    def __fix_args(ins, kwargs):
        global_used = ins is GlobalRedisWrapper.instance_global

        # django cache use 'timeout'
        if global_used and "ex" in kwargs:
            kwargs["timeout"] = kwargs["ex"]
            del kwargs["ex"]

        # redis use 'ex'
        if not global_used and "timeout" in kwargs:
            kwargs["ex"] = kwargs["timeout"]
            del kwargs["timeout"]

    @staticmethod
    def set(*args, **kwargs):
        try:
            ins = GlobalRedisWrapper.__instance()
            GlobalRedisWrapper.__fix_args(ins, kwargs)
            return ins.set(*args, **kwargs)

        except Exception as e:
            logger.warning('redis instance failed', exc_info=True)
            ins = GlobalRedisWrapper.__fallback(e)
            GlobalRedisWrapper.__fix_args(ins, kwargs)
            return ins.set(*args, **kwargs)

    @staticmethod
    def delete(*args, **kwargs):
        try:
            ins = GlobalRedisWrapper.__instance()
            GlobalRedisWrapper.__fix_args(ins, kwargs)
            return ins.delete(*args, **kwargs)

        except Exception as e:
            logger.warning('redis instance failed', exc_info=True)
            ins = GlobalRedisWrapper.__fallback(e)
            GlobalRedisWrapper.__fix_args(ins, kwargs)
            return ins.delete(*args, **kwargs)

    @staticmethod
    def get(*args, **kwargs):
        try:
            ins = GlobalRedisWrapper.__instance()
            return ins.get(*args, **kwargs)

        except Exception as e:
            logger.warning('redis instance failed', exc_info=True)
            ins = GlobalRedisWrapper.__fallback(e)
            return ins.get(*args, **kwargs)

    @staticmethod
    def incr(*args, **kwargs):
        try:
            ins = GlobalRedisWrapper.__instance()
            return ins.incr(*args, **kwargs)
        except Exception as e:
            logger.warning('redis instance failed', exc_info=True)
            ins = GlobalRedisWrapper.__fallback(e)
            return ins.incr(*args, **kwargs)

    @staticmethod
    def decr(*args, **kwargs):
        try:
            ins = GlobalRedisWrapper.__instance()
            return ins.decr(*args, **kwargs)
        except Exception as e:
            logger.warning('redis instance failed', exc_info=True)
            ins = GlobalRedisWrapper.__fallback(e)
            return ins.decr(*args, **kwargs)


def global_redis():
    return GlobalRedisWrapper


def get_async_redis_client(redis_url: str):
    """创建异步Redis客户端，处理连接池的生命周期管理"""
    return aioredis.from_url(
        redis_url, 
        decode_responses=True,
        # 设置连接池参数，避免事件循环关闭问题
        max_connections=20,
        retry_on_timeout=True,
        socket_connect_timeout=5,
        socket_keepalive=True,
        socket_keepalive_options={},
        health_check_interval=30
    )
