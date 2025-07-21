#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from django.views.decorators.cache import cache_page
from apps.price_oracle.services import price_service
from common.helpers import ok_json, error_json


@cache_page(2)
def get_price(request):
    base_asset = request.GET.get('symbol')
    if not base_asset:
        return error_json("参数symbol是必须的", code=400, status=400)
    try:
        price_obj = price_service.get_asset_price(base_asset)
        if not price_obj:
            return error_json(f"未找到 {base_asset.upper()} 的价格数据", code=404, status=404)
        data = {
            'base_asset': price_obj.base_asset,
            'exchange': price_obj.exchange,
            'price': float(price_obj.price),
            'price_change_24h': float(price_obj.price_change_24h) if price_obj.price_change_24h else None,
            'volume_24h': float(price_obj.volume_24h) if price_obj.volume_24h else None,
            'timestamp': price_obj.price_timestamp.isoformat(),
            # 添加CMC资产信息
            'cmc_info': {
                'name': price_obj.cmc_asset.name if price_obj.cmc_asset else None,
                'cmc_id': price_obj.cmc_asset.cmc_id if price_obj.cmc_asset else None,
                'slug': price_obj.cmc_asset.slug if price_obj.cmc_asset else None,
                'tags': price_obj.cmc_asset.tags if price_obj.cmc_asset else None,
            } if price_obj.cmc_asset else None
        }
        return ok_json(data)
    except Exception as e:
        return error_json(f"服务器内部错误，{e}", code=500, status=500)