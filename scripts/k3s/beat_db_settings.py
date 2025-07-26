"""
优化Beat调度器数据库配置
添加到 settings.py 中
"""

# Beat专用数据库配置 - 避免主从分离问题
BEAT_DATABASE_CONFIG = {
    'beat_master': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'your_db_name',
        'USER': 'your_db_user', 
        'PASSWORD': 'your_db_password',
        'HOST': 'your_master_host',
        'PORT': '5432',
        'OPTIONS': {
            'MAX_CONNS': 5,  # 限制连接数
            'connect_timeout': 10,
            'options': '-c statement_timeout=30000'  # 30秒超时
        },
        'CONN_MAX_AGE': 0,  # 不使用持久连接
    }
}

# 修改数据库路由器
class BeatOptimizedRouter:
    """
    为Celery Beat优化的数据库路由器
    """
    def db_for_read(self, model, **hints):
        # Beat相关表强制使用master
        if model._meta.app_label == 'django_celery_beat':
            return 'beat_master'
        
        # 其他表使用原有逻辑
        if hints.get('instance') and hasattr(hints['instance'], '_state') and hints['instance']._state.db:
             return hints['instance']._state.db
        return 'slave_replica'
    
    def db_for_write(self, model, **hints):
        if model._meta.app_label == 'django_celery_beat':
            return 'beat_master'
        return 'default'
    
    def allow_relation(self, obj1, obj2, **hints):
        db_list = ('default', 'slave_replica', 'beat_master')
        if obj1._state.db in db_list and obj2._state.db in db_list:
            return True
        return None
    
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == 'django_celery_beat':
            return db == 'beat_master'
        return db == 'default'