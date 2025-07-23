from datetime import datetime

from django.db import connection
from django.http import JsonResponse

from common.redis_client import global_redis


def health_check(request):
    """
    Health check endpoint for monitoring and load balancers
    Checks database and Redis connectivity
    """
    try:
        status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {}
        }
        
        # Check database connectivity
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            status["services"]["database"] = "healthy"
        except Exception as e:
            status["services"]["database"] = f"unhealthy: {str(e)}"
            status["status"] = "unhealthy"
        
        # Check Redis connectivity
        try:
            redis_client = global_redis()
            redis_client.get("__health_check__")
            status["services"]["redis"] = "healthy"
        except Exception as e:
            status["services"]["redis"] = f"unhealthy: {str(e)}"
            status["status"] = "unhealthy"
        
        # Return appropriate HTTP status code
        http_status = 200 if status["status"] == "healthy" else 503
        
        return JsonResponse(status, status=http_status)
        
    except Exception as e:
        return JsonResponse({
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }, status=503)


def ping(request):
    """
    Simple ping endpoint for basic connectivity checks
    """
    return JsonResponse({
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat()
    })