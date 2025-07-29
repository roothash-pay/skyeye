"""
健康检查和监控API
"""
import redis
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.db import connection
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def _check_data_freshness():
    """
    检查关键数据的新鲜度
    验证任务是否真正更新了数据
    """
    freshness_status = {}
    
    try:
        from django.utils import timezone
        now = timezone.now()
        
        # 检查CMC市场数据新鲜度
        try:
            from apps.cmc_proxy.models import CmcMarketData
            latest_market_data = CmcMarketData.objects.order_by('-updated_at').first()
            if latest_market_data:
                age_seconds = (now - latest_market_data.updated_at).total_seconds()
                freshness_status['cmc_market_data'] = {
                    'last_update': latest_market_data.updated_at.isoformat(),
                    'age_seconds': int(age_seconds),
                    'status': 'fresh' if age_seconds < 600 else 'stale'  # 10分钟阈值
                }
            else:
                freshness_status['cmc_market_data'] = {'status': 'no_data'}
        except Exception as e:
            freshness_status['cmc_market_data'] = {'status': 'error', 'error': str(e)}
        
        # 检查价格 Oracle 数据新鲜度
        try:
            from apps.price_oracle.models import AssetPrice
            latest_price = AssetPrice.objects.order_by('-price_timestamp').first()
            if latest_price:
                age_seconds = (now - latest_price.price_timestamp).total_seconds()
                freshness_status['price_oracle'] = {
                    'last_update': latest_price.price_timestamp.isoformat(),
                    'age_seconds': int(age_seconds),
                    'status': 'fresh' if age_seconds < 300 else 'stale'  # 5分钟阈值
                }
            else:
                freshness_status['price_oracle'] = {'status': 'no_data'}
        except Exception as e:
            freshness_status['price_oracle'] = {'status': 'error', 'error': str(e)}
        
        # 检查K线数据新鲜度
        try:
            from apps.cmc_proxy.models import CmcKline
            latest_kline = CmcKline.objects.filter(timeframe='1h').order_by('-timestamp').first()
            if latest_kline:
                age_seconds = (now - latest_kline.timestamp).total_seconds()
                freshness_status['kline_data'] = {
                    'last_update': latest_kline.timestamp.isoformat(),
                    'age_seconds': int(age_seconds),
                    'status': 'fresh' if age_seconds < 7200 else 'stale'  # 2小时阈值
                }
            else:
                freshness_status['kline_data'] = {'status': 'no_data'}
        except Exception as e:
            freshness_status['kline_data'] = {'status': 'error', 'error': str(e)}
            
    except Exception as e:
        freshness_status['error'] = str(e)
    
    return freshness_status

def _get_task_execution_stats():
    """
    获取任务执行统计信息
    包括成功率、失败次数等
    """
    try:
        from celery import current_app
        
        # 获取Celery的inspect对象
        inspect = current_app.control.inspect()
        
        # 获取活跃任务
        active_tasks = inspect.active() or {}
        active_task_count = sum(len(tasks) for tasks in active_tasks.values())
        
        # 获取保留任务
        reserved_tasks = inspect.reserved() or {}
        reserved_task_count = sum(len(tasks) for tasks in reserved_tasks.values())
        
        # 获取worker统计
        stats = inspect.stats() or {}
        worker_count = len(stats)
        
        # 检查队列积压
        queue_lengths = _get_queue_lengths()
        
        return {
            'active_tasks': active_task_count,
            'reserved_tasks': reserved_task_count,
            'worker_count': worker_count,
            'queue_lengths': queue_lengths,
            'workers': list(stats.keys()) if stats else []
        }
        
    except Exception as e:
        return {'error': str(e)}

def _get_queue_lengths():
    """
    获取各个队列的积压情况
    """
    try:
        import redis
        redis_client = redis.from_url(settings.CELERY_BROKER_URL)
        
        # 定义需要检查的队列
        queues = ['celery', 'price', 'sync', 'klines', 'heavy']
        queue_lengths = {}
        
        for queue in queues:
            try:
                length = redis_client.llen(queue)
                queue_lengths[queue] = length
            except Exception as e:
                queue_lengths[queue] = f'error: {str(e)}'
        
        return queue_lengths
        
    except Exception as e:
        return {'error': str(e)}

@require_http_methods(["GET"])
def health_check(request):
    """
    完整健康检查 - 用于readiness probe
    检查数据库、Redis、Celery连接状态
    """
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'checks': {}
    }
    
    # 检查数据库连接
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        health_status['checks']['database'] = 'ok'
    except Exception as e:
        health_status['checks']['database'] = f'error: {str(e)}'
        health_status['status'] = 'unhealthy'
    
    # 检查Redis连接
    try:
        import redis
        redis_client = redis.from_url(settings.CELERY_BROKER_URL)
        redis_client.ping()
        health_status['checks']['redis'] = 'ok'
    except Exception as e:
        health_status['checks']['redis'] = f'error: {str(e)}'
        health_status['status'] = 'unhealthy'
    
    # 检查Celery Worker状态
    try:
        from celery import current_app
        inspect = current_app.control.inspect()
        active_workers = inspect.active()
        
        if active_workers:
            health_status['checks']['celery_workers'] = f'ok: {len(active_workers)} workers'
        else:
            health_status['checks']['celery_workers'] = 'warning: no active workers'
            # Worker不活跃不算完全不健康，可能是暂时没任务
            
    except Exception as e:
        health_status['checks']['celery_workers'] = f'error: {str(e)}'
        health_status['status'] = 'unhealthy'
    
    # 返回适当的HTTP状态码
    status_code = 200 if health_status['status'] == 'healthy' else 503
    return JsonResponse(health_status, status=status_code)

@require_http_methods(["GET"])  
def ping(request):
    """
    简单存活检查 - 用于liveness probe
    只检查服务是否能响应
    """
    return JsonResponse({
        'status': 'alive',
        'timestamp': datetime.now().isoformat(),
        'service': 'skyeye-api'
    })

def _check_cmc_keys_health():
    """检查CMC API Keys的配置状态"""
    cmc_keys_status = {}
    
    try:
        # 检查K线任务专用Key
        klines_key = getattr(settings, 'COINMARKETCAP_API_KEY', None)
        cmc_keys_status['klines_key'] = {
            'configured': bool(klines_key),
            'purpose': '系统维护任务专用 (K线、全量同步)',
            'length': len(klines_key) if klines_key else 0
        }
        
        # 检查外部请求专用Key  
        external_key = getattr(settings, 'COINMARKETCAP_API_KEY_EXTERNAL', None)
        cmc_keys_status['external_key'] = {
            'configured': bool(external_key),
            'purpose': '外部用户请求专用',
            'length': len(external_key) if external_key else 0
        }
        
        # 检查是否两个Key都配置了
        both_configured = bool(klines_key and external_key)
        cmc_keys_status['separation_enabled'] = both_configured
        
        if both_configured:
            cmc_keys_status['status'] = 'separated'
            cmc_keys_status['message'] = '双Key分离已启用，API调用能力翻倍'
        elif klines_key:
            cmc_keys_status['status'] = 'single_key'
            cmc_keys_status['message'] = '仅配置了K线Key，建议配置外部Key实现分离'
        else:
            cmc_keys_status['status'] = 'no_keys'
            cmc_keys_status['message'] = '未配置任何CMC API Key'
            
    except Exception as e:
        cmc_keys_status = {
            'status': 'error',
            'error': str(e)
        }
    
    return cmc_keys_status

@require_http_methods(["GET"])
def beat_health(request):
    """
    Beat调度器健康检查
    专门用于监控Beat调度器状态和任务执行结果
    """
    try:
        # 检查最近是否有任务被调度
        from django_celery_beat.models import PeriodicTask
        from django.utils import timezone
        
        # 获取最近5分钟内应该执行的任务
        recent_time = timezone.now() - timedelta(minutes=5)
        active_tasks = PeriodicTask.objects.filter(
            enabled=True,
            last_run_at__gte=recent_time
        ).count()
        
        # 检查关键任务状态
        critical_tasks = [
            # 高频价格任务（最关键）
            'collect_prices_frequently',
            'persist_prices_frequently',
            'process_pending_cmc_batch_requests',
            
            # 数据同步任务
            'sync_cmc_data_to_db',
            
            # K线任务（容易出问题）
            'hourly_cmc_klines_update',
            'daily_cmc_klines_initialization',
            
            # 每日任务（重要的数据更新）
            'daily_full_data_sync'
        ]
        
        # 不同任务的健康检查阈值（秒）
        task_thresholds = {
            # 高频任务
            'collect_prices_frequently': 300,          # 30秒执行，5分钟内必须有
            'persist_prices_frequently': 300,          # 15秒执行，5分钟内必须有
            'process_pending_cmc_batch_requests': 300, # 2秒执行，5分钟内必须有
            'sync_cmc_data_to_db': 900,               # 5分钟执行，15分钟内必须有
            
            # 小时任务
            'hourly_cmc_klines_update': 7200,         # 每小时执行，2小时内必须有
            'daily_cmc_klines_initialization': 86400 * 2,  # 每天执行，2天内必须有
            
            # 每日任务
            'daily_full_data_sync': 86400 * 2,        # 每天执行，2天内必须有
        }
        
        critical_status = {}
        for task_name in critical_tasks:
            try:
                task = PeriodicTask.objects.get(name=task_name, enabled=True)
                threshold = task_thresholds.get(task_name, 300)  # 默认5分钟
                
                if task.last_run_at:
                    time_since_run = (timezone.now() - task.last_run_at).total_seconds()
                    status = 'ok' if time_since_run < threshold else 'warning'
                    
                    critical_status[task_name] = {
                        'last_run': task.last_run_at.isoformat(),
                        'seconds_ago': int(time_since_run),
                        'status': status,
                        'threshold_seconds': threshold
                    }
                else:
                    critical_status[task_name] = {
                        'last_run': None,
                        'status': 'never_run',
                        'threshold_seconds': threshold
                    }
            except PeriodicTask.DoesNotExist:
                critical_status[task_name] = {'status': 'not_found'}
        
        # 判断整体健康状态
        overall_status = 'healthy'
        warning_count = sum(1 for task in critical_status.values() 
                          if task.get('status') in ['warning', 'never_run', 'not_found'])
        
        if warning_count > 0:
            overall_status = 'warning' if warning_count <= 1 else 'unhealthy'
        
        # 添加数据更新验证
        data_freshness = _check_data_freshness()
        
        # 添加任务执行统计
        task_execution_stats = _get_task_execution_stats()
        
        # 添加CMC Keys状态检查
        cmc_keys_status = _check_cmc_keys_health()
        
        response_data = {
            'status': overall_status,
            'timestamp': datetime.now().isoformat(),
            'recent_active_tasks': active_tasks,
            'critical_tasks': critical_status,
            'data_freshness': data_freshness,
            'execution_stats': task_execution_stats,
            'cmc_keys': cmc_keys_status
        }
        
        # 根据数据新鲜度调整整体状态
        if overall_status == 'healthy':
            stale_data_count = sum(1 for status in data_freshness.values() 
                                 if isinstance(status, dict) and status.get('status') == 'stale')
            if stale_data_count > 0:
                overall_status = 'warning'
        
        response_data['status'] = overall_status
        status_code = 200 if overall_status == 'healthy' else 503
        return JsonResponse(response_data, status=status_code)
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'timestamp': datetime.now().isoformat(),
            'error': str(e)
        }, status=503)