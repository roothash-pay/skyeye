from celery.schedules import crontab


# 定时任务配置 (使用模块路径.函数名格式，便于追溯和调试)
# 注意：定时任务时区由Celery配置中的timezone参数控制
# 如需指定为中国时间，设置环境变量：CELERY_TIMEZONE=Asia/Shanghai
DEFAULT_BEAT_SCHEDULE = {
    'daily_full_data_sync': {
        'task': 'apps.cmc_proxy.tasks.daily_full_data_sync',
        'schedule': crontab(hour=3, minute=0),  # 每天凌晨3点执行
        'options': {'queue': 'heavy'},  # 重任务队列
    },
    'process_pending_cmc_batch_requests': {
        'task': 'apps.cmc_proxy.tasks.process_pending_cmc_batch_requests',
        'schedule': 2.0,  # 每2秒，贴合API限制
        'options': {'queue': 'sync'},   # 同步专用队列
    },
    'sync_cmc_data_to_db': {
        'task': 'apps.cmc_proxy.tasks.sync_cmc_data_task',
        'schedule': 300.0,  # 每5分钟同步到数据库
        'options': {'queue': 'sync'},   # 同步专用队列
    },
    'hourly_cmc_klines_update': {
        'task': 'apps.cmc_proxy.tasks.update_cmc_klines',
        'schedule': crontab(minute=15),  # 每小时过15分执行，更新最新1小时K线数据
        'options': {'queue': 'klines'},  # K线专用队列
        'kwargs': {'count': 1},  # 每次只更新1小时数据
    },
    'daily_cmc_klines_initialization': {
        'task': 'apps.cmc_proxy.tasks.initialize_missing_klines',
        'schedule': crontab(hour=2, minute=30),  # 每天凌晨2:30执行，初始化缺失的K线数据
        'options': {'queue': 'klines'},  # K线专用队列
        'kwargs': {'count': 24, 'only_missing': True},  # 只处理缺失数据的资产
    },
    'daily_token_holdings_update': {
        'task': 'apps.token_holdings.tasks.update_token_holdings_daily_task',
        'schedule': crontab(hour=4, minute=0),  # 每天凌晨4点执行
        'options': {'queue': 'heavy'},  # 重任务队列
        'kwargs': {'max_concurrent': 5},  # 限制并发数避免API限频
    },
    'daily_token_unlocks_update': {
        'task': 'apps.token_unlocks.tasks.update_token_unlocks_task',
        'schedule': crontab(hour=5, minute=0),  # 每天凌晨5点执行
        'options': {'queue': 'heavy'},  # 重任务队列
    },
    'daily_token_allocations_update': {
        'task': 'apps.token_economics.tasks.update_token_allocations_task',
        'schedule': crontab(hour=6, minute=0),  # 每天凌晨6点分执行
        'options': {'queue': 'heavy'},  # 重任务队列
    },
    'collect_prices_frequently': {
        'task': 'apps.price_oracle.tasks.collect_prices_task',
        'schedule': 30.0,  # 每30秒采集一次价格数据
        'options': {'queue': 'price'},  # 价格专用队列
    },
    'persist_prices_frequently': {
        'task': 'apps.price_oracle.tasks.persist_prices_task',
        'schedule': 15.0,  # 每15秒持久化一次
        'options': {'queue': 'price'},  # 价格专用队列
    },
}
