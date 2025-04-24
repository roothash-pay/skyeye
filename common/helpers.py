#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import functools
import hashlib
import json
import logging
import os
import sys
import time
import uuid
from bisect import bisect
from datetime import datetime, timezone, timedelta
from decimal import Context as DecimalContext
from decimal import Decimal, InvalidOperation
from decimal import ROUND_FLOOR, ROUND_UP
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import urlencode

import json_log_formatter
import pytz
import requests
from django.conf import settings
from django.core.paginator import EmptyPage
from django.http import HttpRequest, JsonResponse
from django.utils.timezone import localtime, now

from common.paginator import MyPaginator


def call_people(alarmName, alarmContent):
    logger = logging.getLogger('call_people')
    try:
        logger.error('发起电话报警：' + alarmContent)
        data = {
            'app': 'a711c9b7-cb52-401a-a18c-ef9632ddec9f',
            'eventType': 'trigger',
            'eventId': uuid.uuid4().hex,
            'alarmName': alarmName,
            'alarmContent': alarmContent,
            'priority': 3
        }
        r = requests.post('http://api.aiops.com/alert/api/event', data=json.dumps(data))
        if not '"result":"success"' in r.text:
            raise RuntimeError(r.text)
    except Exception as ex:
        logger.error("Call people failed: {}".format(ex.args), exc_info=True)


def getLogger(name):
    logger = logging.getLogger(name)
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        logger.disabled = True
    return logger


def get_hostname() -> str:
    import socket
    return socket.gethostname()


def get_processid() -> int:
    import os
    return os.getpid()


def make_timestamp() -> float:
    return time.time() * 1000


def time_to_str(time_time: Optional[float] = None, tz: str = "Asia/Shanghai") -> str:
    time_time = time_time or time.time()
    dt = datetime.fromtimestamp(time_time).astimezone(pytz.timezone(tz))
    return str(dt)


def ok_json(data: Any, code: int = 200) -> JsonResponse:
    return JsonResponse({"ok": True, "code": code, "result": data})


def keep_two_place(value):
    if not value:
        return "0"
    dec_value = Decimal(value).quantize(Decimal("0.00"))
    return (
        dec_value.to_integral()
        if dec_value == dec_value.to_integral()
        else dec_value.normalize()
    )


def error_json(msg: str, code: int = -1, status: int = 200) -> JsonResponse:
    return JsonResponse({"ok": False, "code": code, "msg": msg, }, status=status)


def floor_decimal(amount: Decimal, digits: int = 18) -> Decimal:
    return amount.quantize(
        Decimal("1E-%d" % digits), context=DecimalContext(prec=60, rounding=ROUND_FLOOR)
    )


def up_decimal(amount: Decimal, digits: int = 18) -> Decimal:
    return amount.quantize(
        Decimal("1E-%d" % digits), context=DecimalContext(prec=60, rounding=ROUND_UP)
    )


def round_decimal(amount: Decimal, digits: int = 18) -> Decimal:
    return amount.quantize(Decimal("1E-%d" % digits), context=DecimalContext(prec=60))


limit_steps: List[int] = [5, 10, 20, 50, 100, 500, 1000, 5000]


def search_limit(limit: int) -> int:
    limit = max(0, min(limit, 5000))
    return limit_steps[bisect(limit_steps, limit)]


def dec(value: Any, default: Any = "0", digits: int = 18) -> Decimal:
    try:
        # if isinstance(value, float):
        #    value = str(value)
        if isinstance(value, Decimal):
            return floor_decimal(value, digits=digits)
        else:
            return floor_decimal(Decimal(value), digits=digits)
    except (InvalidOperation, TypeError):
        return Decimal(default)


parse_decimal = dec
d0: Decimal = dec("0")
d1 = dec("1")
d2 = dec("2")
d10 = dec("10")
d100 = dec("100")
d200 = dec("200")
d1000 = dec("1000")
d1_000 = dec("1000")
d1k = d1000
d10000 = dec("10000")
d10_000 = dec("10000")
d1m = dec("1_000_000")


def dec05up(a: Decimal) -> Decimal:
    half = dec("0.5", digits=1)
    floored = up_decimal(a + a, digits=0)
    return floored * half


def dec05floor(a: Decimal) -> Decimal:
    half = dec("0.5", digits=1)
    floored = floor_decimal(a + a, digits=0)
    return floored * half


dec05 = dec05floor


def mod_decimal(amount: Decimal, div: Decimal) -> Tuple[Decimal, Decimal]:
    divided = floor_decimal(amount / div, digits=0) * div
    remainder = amount - divided
    return divided, remainder


def _xx_decprice(value: Any) -> Decimal:
    return dec(value, digits=6)


decprice = dec


def decstr(value: Union[Decimal, float], round_number=None) -> str:
    if isinstance(value, float):
        value = Decimal(value)
    if round_number is not None:
        _s = "0."
        for i in range(round_number):
            _s += "0"
        value = value.quantize(Decimal(_s))

    s = "{:f}".format(value)
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    if s == "-0":
        s = "0"
    return s


def build_sign(params: Dict[str, Any], secretKey: str) -> str:
    data = sorted(params.items()) + [("secret_key", secretKey)]
    encoded = urlencode(data)
    return hashlib.md5(encoded.encode("utf8")).hexdigest().upper()


MIN = dec("0", digits=8)


def parse_int(v, default=0):
    try:
        v = int(v)
    except (ValueError, TypeError) as e:
        v = default
    return v


def get_page(request: HttpRequest) -> int:
    page = parse_int(request.GET.get("page", 1), 1)
    if page < 1:
        page = 1
    return page


PAGE_SIZE = 20


def paged_items(request: HttpRequest, qs, pagesize=PAGE_SIZE, page_cls=MyPaginator):
    paginator = page_cls(qs, pagesize, adjacent_pages=3)
    page = get_page(request)
    try:
        items = paginator.page(page)
    except EmptyPage:
        items = paginator.page(paginator.num_pages)

    args = {}
    for key, value in request.GET.items():
        if key != "page":
            args[key] = value.encode("utf-8")

    if len(args) == 0:
        items.prefix_uri = request.path + "?"
    else:
        items.prefix_uri = request.path + "?" + urlencode(args) + "&"
    return items


def sleep(sleep_time: float) -> None:
    time.sleep(sleep_time)


def utc_now() -> datetime:
    return now()


def bj_now() -> datetime:
    tz_utc_8 = pytz.timezone('Asia/Shanghai')
    return datetime.now(tz_utc_8)


def bj_now_str(format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    return bj_now().strftime(format_str)


def current_now() -> datetime:
    return localtime(utc_now())


def timestamp_to_utc(time_stamp):
    return datetime.utcfromtimestamp(time_stamp)


def retry(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        for i in range(3):
            r = func(*args, **kwargs)
            if r:
                return r
            else:
                time.sleep(1)

    return wrapper


def datetime2utctimestamp(datetime):
    timestamp = datetime.replace(tzinfo=timezone.utc).timestamp()
    return timestamp


def str2datetime(datestr: str) -> datetime:
    return datetime.strptime(datestr, '%Y-%m-%d %H:%M:%S')


def str_2_bj(s: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> datetime:
    tz = pytz.timezone('Asia/Shanghai')
    d = datetime.strptime(s, format_str)
    return tz.localize(d)


def md5_crypt(txt: str) -> str:
    """对字符串进行MD5"""

    m = hashlib.md5()
    m.update(txt.encode("utf8"))

    return m.hexdigest()


def utc_timestamp() -> int:
    return int(utc_now().strftime("%s"))


def datetime_offset(days: float = 0.0, hours: float = 0.0, minutes: float = 0.0, seconds: float = 0.0) -> datetime:
    return utc_now() - timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)


def check_monitor_token(func):
    def monitor_token_auth(request, *args, **kwargs):
        monitor_token = request.META.get("HTTP_API_TOKEN")
        if monitor_token in ["", "None", None, "unkown"]:
            return error_json("Monitor token is empty", 1000)
        if monitor_token != settings.MONITOR_TOKEN:
            return error_json("Monitor token is error", 1000)
        return func(request, *args, **kwargs)

    return monitor_token_auth


class CustomJsonFormatter(json_log_formatter.JSONFormatter):
    def json_record(self, message, extra, record):
        if "name" not in extra:
            extra["name"] = record.name.split(".")[-1]
        if "levelname" not in extra:
            extra["levelname"] = record.levelname.capitalize()
        if "filename" not in extra:
            extra["filename"] = record.filename
        if "funcName" not in extra:
            extra["funcName"] = record.funcName
        if "lineno" not in extra:
            extra["lineno"] = record.lineno
        extra.setdefault('pid', os.getpid())
        utc_time = utc_now()
        tz = pytz.timezone(settings.CELERY_TIMEZONE)
        extra["time"] = datetime.fromtimestamp(utc_time.timestamp(), tz).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        return super(CustomJsonFormatter, self).json_record(message, extra, record)
