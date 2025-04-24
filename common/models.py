#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import pickle
import time
from typing import Optional

from django.db import models

from common.redis_client import local_redis

COMMON_STATUS = [(x, x) for x in ['ACTIVE', 'DOWN', 'DISABLE', 'CLOSED']]
TIMEFRAME = [(x, x) for x in ['1m', '5m', '15m', '30m', '1h']]

logger = logging.getLogger(__name__)


class CacheManager(models.Manager):
    def filter(self, *args, expire: Optional[int] = None, **kwargs):
        if not expire:
            return super().filter(*args, **kwargs)

        r = local_redis()
        sub_keys = ",".join(f"{k}={v}" for k, v in kwargs.items())
        try:
            pickle_data = r.get(sub_keys)
            assert pickle_data, f'{self} did not get pickle data by {sub_keys} '
            json_data = pickle.loads(pickle_data)
            res = json_data['data']
        except:  # TODO: explicitly give exception types
            res = super().filter(*args, **kwargs)
            json_data = {'timestamp': time.time(), 'data': res.all()[:]}
            pickle_data = pickle.dumps(json_data)

            if len(pickle_data) < 5E7:
                r.set(sub_keys, pickle_data, ex=expire)
            else:
                logger.warning(f'Cache too large for query {sub_keys}')
        finally:
            return res


class BaseModelManager(models.Manager):
    def all_to_dict(self):
        queryset = self.get_queryset()
        return [obj.to_dict() for obj in queryset.all()]


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    # objects = BaseModelManager()

    class Meta:
        abstract = True

    def __str__(self):
        try:
            return "%s(%s)" % (self.__class__.__name__, self.id)
        except AttributeError:
            return "%s" % (self.__class__.__name__)
