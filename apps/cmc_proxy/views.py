import asyncio
import math
from django.views import View

from apps.cmc_proxy.models import CmcAsset, CmcMarketData
from apps.cmc_proxy.services import get_klines_for_asset, get_latest_market_data
from apps.cmc_proxy.helpers import TimeRangeCalculator, MarketDataFormatter, ViewParameterValidator
from common.helpers import ok_json, error_json, getLogger, parse_int, PAGE_SIZE

logger = getLogger(__name__)


class CmcKlinesView(View):
    """
    获取CMC K线数据的API视图。
    支持按cmc_id查询单个资产的K线，或分页返回多个资产的K线数据摘要。
    """

    async def get(self, request):
        # 获取查询参数
        cmc_id = request.GET.get('cmc_id')
        timeframe = request.GET.get('timeframe', '1h')
        hours = parse_int(request.GET.get('hours', 24), 24)
        hours = max(1, min(hours, 744))  # 限制在1小时到1个月之间

        try:
            # 计算时间范围
            start_time, end_time, start_time_24h = TimeRangeCalculator.calculate_kline_time_range(hours)

            if cmc_id:
                return await self._get_single_asset_klines(request, cmc_id, timeframe, start_time, end_time,
                                                           start_time_24h)
            else:
                return await self._get_paged_assets_klines(request, timeframe, start_time, end_time, start_time_24h)

        except Exception as e:
            logger.error(f"Error fetching klines data: {e}", exc_info=True)
            return error_json(str(e), code=500, status=500)

    async def _get_single_asset_klines(self, request, cmc_id, timeframe, start_time, end_time, start_time_24h):
        success, cmc_id_int = ViewParameterValidator.validate_and_parse_cmc_id(cmc_id)
        if not success:
            return error_json(cmc_id_int, code=400, status=400)

        try:
            asset = await CmcAsset.objects.aget(cmc_id=cmc_id_int)
        except CmcAsset.DoesNotExist:
            return error_json(f"未找到cmc_id为{cmc_id}的资产", code=404, status=404)

        kline_data = await get_klines_for_asset(asset, timeframe, start_time, end_time, start_time_24h)
        if not kline_data['klines']:
            return error_json(f"未找到{asset.symbol}的K线数据", code=404, status=404)

        return ok_json({
            'asset': MarketDataFormatter.format_asset_info(asset),
            'timeframe': timeframe,
            'count': len(kline_data['klines']),
            'high_24h': kline_data['high_24h'],
            'low_24h': kline_data['low_24h'],
            'klines': kline_data['klines'],
        })

    async def _get_paged_assets_klines(self, request, timeframe, start_time, end_time, start_time_24h):
        # 解析分页参数
        page = max(1, parse_int(request.GET.get('page', 1), 1))
        page_size = max(1, parse_int(request.GET.get('page_size', PAGE_SIZE), PAGE_SIZE))

        # 获取有K线数据的资产列表
        assets_qs = CmcAsset.objects.filter(
            klines__timeframe=timeframe
        ).distinct().select_related('market_data').order_by('market_data__cmc_rank')

        total = await assets_qs.acount()
        offset = (page - 1) * page_size
        slice_qs = assets_qs[offset:offset + page_size]
        assets = [asset async for asset in slice_qs]

        results = []
        for asset in assets:
            kline_data = await get_klines_for_asset(asset, timeframe, start_time, end_time, start_time_24h)
            results.append({
                **MarketDataFormatter.format_asset_info(asset),
                **kline_data
            })

        pages = math.ceil(total / page_size) if page_size else 1

        return ok_json({
            'page': page,
            'pages': pages,
            'total': total,
            'timeframe': timeframe,
            'results': results,
        })


class CmcMarketDataView(View):
    """
    获取CMC最新行情数据的视图。
    支持单个查询、批量查询和分页列表。
    
    缓存策略：
    - CMC基础数据：10分钟缓存（市值、排名等，节省credit）
    - CCXT价格：实时获取（无缓存，保证时效性）
    """

    async def get(self, request):
        """
        根据查询参数分发到不同的处理方法。
        """
        cmc_id = request.GET.get('cmc_id')
        timeframe = request.GET.get('timeframe', '1h')
        hours = parse_int(request.GET.get('hours', 24), 24)
        hours = max(1, min(hours, 744))  # 限制在1小时到1个月之间

        # 计算时间范围
        start_time, end_time, start_time_24h = TimeRangeCalculator.calculate_kline_time_range(hours)
        kline_params = {'timeframe': timeframe, 'start_time': start_time, 'end_time': end_time,
                        'start_time_24h': start_time_24h}

        if cmc_id is not None:
            return await self._get_single_market_data(request, cmc_id, **kline_params)

        cmc_ids = request.GET.get('cmc_ids')
        if cmc_ids is not None:
            return await self._get_multiple_market_data(request, cmc_ids, **kline_params)

        return await self._get_paged_market_data(request, **kline_params)

    async def _get_single_market_data(self, request, cmc_id, **kline_params):
        """
        处理单个cmc_id的行情数据请求。
        """
        success, cmc_id_int = ViewParameterValidator.validate_and_parse_cmc_id(cmc_id)
        if not success:
            return error_json(cmc_id_int, code=400, status=400)

        market_data = await get_latest_market_data(cmc_id_int)
        if not market_data:
            return error_json(
                f"Market data not found for cmc_id {cmc_id_int}. This may be because the asset is not in our database or the data is temporarily unavailable.",
                code=404,
                status=404
            )

        try:
            asset = await CmcAsset.objects.aget(cmc_id=cmc_id_int)
            kline_data = await get_klines_for_asset(asset, **kline_params)
            market_data.update(kline_data)
        except CmcAsset.DoesNotExist:
            # 资产不存在，等待短暂时间后重试一次（处理异步创建延迟）
            logger.info(f"Asset cmc_id={cmc_id_int} not found, waiting for async creation...")
            await asyncio.sleep(0.5)  # 等待500ms

            try:
                asset = await CmcAsset.objects.aget(cmc_id=cmc_id_int)
                kline_data = await get_klines_for_asset(asset, **kline_params)
                market_data.update(kline_data)
                logger.info(f"Successfully retrieved asset and klines for cmc_id={cmc_id_int} after retry")
            except CmcAsset.DoesNotExist:
                # 最终仍未找到资产，返回空K线数据
                logger.warning(f"Asset cmc_id={cmc_id_int} still not found after retry")
                market_data.update({'klines': [], 'high_24h': None, 'low_24h': None})

        return ok_json(market_data)

    async def _get_multiple_market_data(self, request, cmc_ids, **kline_params):
        """
        处理批量cmc_ids的行情数据请求。
        """
        success, id_list = ViewParameterValidator.validate_and_parse_cmc_ids(cmc_ids)
        if not success:
            return error_json(id_list, code=400, status=400)

        qs = CmcMarketData.objects.select_related('asset').filter(asset__cmc_id__in=id_list).order_by('-market_cap')
        items = [item async for item in qs]
        results = []
        for item in items:
            kline_data = await get_klines_for_asset(item.asset, **kline_params)
            result_item = MarketDataFormatter.format_market_data_item(item)
            result_item.update(kline_data)
            results.append(result_item)
        return ok_json({'results': results})

    async def _get_paged_market_data(self, request, **kline_params):
        """
        处理分页的行情数据列表请求。
        """
        # 解析分页参数
        page = max(1, parse_int(request.GET.get('page', 1), 1))
        page_size = max(1, parse_int(request.GET.get('page_size', PAGE_SIZE), PAGE_SIZE))

        # 分页列表
        qs = CmcMarketData.objects.select_related('asset').all().order_by('-volume_24h')
        total = await qs.acount()
        offset = (page - 1) * page_size
        slice_qs = qs[offset:offset + page_size]
        items = [item async for item in slice_qs]
        pages = math.ceil(total / page_size) if page_size else 1
        results = []
        for item in items:
            kline_data = await get_klines_for_asset(item.asset, **kline_params)
            result_item = MarketDataFormatter.format_market_data_item(item)
            result_item.update(kline_data)
            results.append(result_item)
        return ok_json({
            'page': page,
            'pages': pages,
            'total': total,
            'results': results,
        })
