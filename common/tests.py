import time
import json
from common.redis_client import local_redis


# data = local_redis().zrevrangebyscore("new:redis:crawler:ETH/USDT:merge_orderbooks", time.time(), time.time() - 1200)
data = local_redis().zrevrangebyscore("new:redis:crawler:huobi:ETH/USDT:orderbooks", time.time(), time.time() - 1200)
print(len(data))

if data:
    p = json.loads(data[-1].decode())
    p.setdefault("exchange", "huobi")
    print(p)

# DJANGO_SETTINGS_MODULE=skyeye.settings python3 -m common.tests