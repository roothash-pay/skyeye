import os
import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Initialize environment variables
env = environ.Env(
    # Django Core Settings
    DEBUG=(bool, False),
    SECRET_KEY=(str, ''),
    ALLOWED_HOSTS=(list, []),
    
    # Database Settings
    POSTGRES_DB=(str, 'skyeye'),
    POSTGRES_USER=(str, 'skyeye_user'),
    POSTGRES_PASSWORD=(str, ''),
    POSTGRES_HOST_MASTER=(str, '127.0.0.1'),
    POSTGRES_PORT_MASTER=(str, '5430'),
    POSTGRES_HOST_SLAVE=(str, '127.0.0.1'),
    POSTGRES_PORT_SLAVE=(str, '5431'),
    
    # Redis Settings
    REDIS_URL=(str, 'redis://localhost:6379/0'),
    REDIS_CMC_URL=(str, 'redis://localhost:6379/1'),
    REDIS_TRADING_HOST=(str, '127.0.0.1'),
    REDIS_TRADING_PORT=(int, 6379),
    REDIS_TRADING_DB=(int, 2),
    REDIS_TRADING_PASSWORD=(str, ''),
    
    # Celery Settings
    CELERY_BROKER_URL=(str, 'redis://localhost:6379/0'),
    CELERY_RESULT_BACKEND=(str, 'redis://localhost:6379/0'),
    
    # External API Settings
    COINMARKETCAP_API_KEY=(str, ''),
    COINMARKETCAP_BASE_URL=(str, 'https://pro-api.coinmarketcap.com/v1'),
    FRANKFURTER_API_URL=(str, 'https://api.frankfurter.app/latest?from=USD&to=CNY'),
    
    # Application Settings
    DEFAULT_USD_CNY_RATE=(str, '7.29'),
    DJANGO_LOG_LEVEL=(str, 'INFO'),
    LANGUAGE_CODE=(str, 'en-us'),
    
    # Business Logic Settings
    GRPC_MAX_MESSAGE_LENGTH=(int, 2048),
    
    # Celery Task Settings
    CELERY_TASK_TIME_LIMIT=(int, 600),
)

# Read .env file if it exists
env_file = os.path.join(BASE_DIR, '.env')
if os.path.exists(env_file):
    environ.Env.read_env(env_file)

# Security settings
SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env('ALLOWED_HOSTS')

# Ensure SECRET_KEY is set in production
if not SECRET_KEY and not DEBUG:
    raise ValueError("SECRET_KEY must be set in production environment")

INSTALLED_APPS = [
    # Django modules
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Local apps
    'common',
    # 'services',
    # 'apps.backoffice',
    # 'apps.exchange',
    # 'apps.frontend',
    'apps.price_oracle',
    'apps.token_economics',
    'apps.token_unlocks',
    'apps.token_holdings',
    'apps.api_router',
    'apps.cmc_proxy',
    # Third-party modules
    'rest_framework',
    'django_celery_beat',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'skyeye.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'skyeye.wsgi.application'

# Database configuration using environment variables
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('POSTGRES_DB'),
        'USER': env('POSTGRES_USER'),
        'PASSWORD': env('POSTGRES_PASSWORD'),
        'HOST': env('POSTGRES_HOST_MASTER'),
        'PORT': env('POSTGRES_PORT_MASTER'),
    },
    'slave_replica': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('POSTGRES_DB'),
        'USER': env('POSTGRES_USER'),
        'PASSWORD': env('POSTGRES_PASSWORD'),
        'HOST': env('POSTGRES_HOST_SLAVE'),
        'PORT': env('POSTGRES_PORT_SLAVE'),
        'TEST': {
            'MIRROR': 'default',
        },
    }
}

# Database Routers for Read-Write Splitting
DATABASE_ROUTERS = ['skyeye.db_routers.ReadWriteRouter']

# Cache configuration using environment variables
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env('REDIS_URL'),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}

# Trading Redis configuration using environment variables
TRADING_REDIS = {
    "host": env('REDIS_TRADING_HOST'),
    "port": env('REDIS_TRADING_PORT'),
    "db": env('REDIS_TRADING_DB'),
    "password": env('REDIS_TRADING_PASSWORD'),
    "socket_connect_timeout": 10,
}

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(asctime)s %(name)s [%(module)s:%(levelname)s] %(message)s'
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'filters': {
        'ignore_broken_pipe': {
            '()': 'django.utils.log.CallbackFilter',
            'callback': lambda record: not (
                hasattr(record, 'getMessage') and 
                'Broken pipe' in record.getMessage()
            )
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
            'filters': ['ignore_broken_pipe'],
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': env('DJANGO_LOG_LEVEL'),
            'propagate': True
        },
        'django.server': {
            'handlers': ['console'],
            'level': 'WARNING',  # 减少服务器日志的详细程度
            'propagate': False,
            'filters': ['ignore_broken_pipe'],
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO'
    },
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = env('LANGUAGE_CODE')
TIME_ZONE = 'UTC'  # 固定为UTC，确保数据存储一致性（定时任务时区通过CELERY_TIMEZONE单独配置）
USE_I18N = True
USE_L10N = True
USE_TZ = True  # 开启后，django.utils.timezone.now()得到的是UTC时间，数据库存储也是UTC

STATIC_URL = '/static/'

# External API Configurations (using env defaults)
COINMARKETCAP_API_KEY = env('COINMARKETCAP_API_KEY')
COINMARKETCAP_BASE_URL = env('COINMARKETCAP_BASE_URL')
FRANKFURTER_API_URL = env('FRANKFURTER_API_URL')
DEFAULT_USD_CNY_RATE = env('DEFAULT_USD_CNY_RATE')

# Business Logic Settings
GRPC_MAX_MESSAGE_LENGTH = env('GRPC_MAX_MESSAGE_LENGTH')

# Business Constants
ACCEPTABLE_QUOTE_ASSETS_FOR_OTC = ['USDT', 'USDC']

# Celery Configuration (只保留Django需要的设置，其他在celery.py中配置)
CELERY_BROKER_URL = env('CELERY_BROKER_URL')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND')
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# CMC Redis URL (用于应用程序访问)
REDIS_CMC_URL = env('REDIS_CMC_URL')

# Django Settings
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Import local settings for development overrides (if they exist)
# Note: local_settings should now only contain development-specific overrides
# All sensitive configuration should be in environment variables
try:
    from .local_settings import *
except ImportError:
    pass