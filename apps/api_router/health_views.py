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

@require_http_methods(["GET"])
def beat_health(request):
    """
    Beat调度器健康检查
    专门用于监控Beat调度器状态
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
            'collect_prices_frequently',
            'persist_prices_frequently',
            'process_pending_cmc_batch_requests'
        ]
        
        critical_status = {}
        for task_name in critical_tasks:
            try:
                task = PeriodicTask.objects.get(name=task_name, enabled=True)
                if task.last_run_at:
                    time_since_run = (timezone.now() - task.last_run_at).total_seconds()
                    critical_status[task_name] = {
                        'last_run': task.last_run_at.isoformat(),
                        'seconds_ago': int(time_since_run),
                        'status': 'ok' if time_since_run < 300 else 'warning'  # 5分钟阈值
                    }
                else:
                    critical_status[task_name] = {
                        'last_run': None,
                        'status': 'never_run'
                    }
            except PeriodicTask.DoesNotExist:
                critical_status[task_name] = {'status': 'not_found'}
        
        # 判断整体健康状态
        overall_status = 'healthy'
        warning_count = sum(1 for task in critical_status.values() 
                          if task.get('status') in ['warning', 'never_run', 'not_found'])
        
        if warning_count > 0:
            overall_status = 'warning' if warning_count <= 1 else 'unhealthy'
        
        response_data = {
            'status': overall_status,
            'timestamp': datetime.now().isoformat(),
            'recent_active_tasks': active_tasks,
            'critical_tasks': critical_status
        }
        
        status_code = 200 if overall_status == 'healthy' else 503
        return JsonResponse(response_data, status=status_code)
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'timestamp': datetime.now().isoformat(),
            'error': str(e)
        }, status=503)