import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECRET_KEY = 'xrszzb$tq7!!6n0h9%%g@0)*g%o*eg5g2+*u4vi1-t9nxwc*vs'
DEBUG = True
ALLOWED_HOSTS = ["*"]


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'common',
    'exchange',
    'sevices',
    'backoffice',
    'frontend',
    'dex'
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

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "skeye",
        "USER": "guoshijiang",
        "PASSWORD": "",
        "HOST": "127.0.0.1",
    },
}

TRADING_REDIS = {
    "host": "127.0.0.1",
    "port": 6379,
    "db": 2,
    "password": "",
    "socket_connect_timeout": 10,
}

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
    'handlers': {
        'console': {
            # 'level':'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
            # 'stream': sys.stdout,
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': True
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO'
    },
}

# Password validation
# https://docs.djangoproject.com/en/2.2/ref/settings/#auth-password-validators
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
# https://docs.djangoproject.com/en/2.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


STATIC_URL = '/static/'
QUOTE_ORDERBOOK_LIMIT = 15
QUOTE_ORDERBOOK_SMALL_LIMIT = 5
QUOTE_OB_USDTUSDS_LIMIT = 5

MERGE_SYMBOL_CONFIG = {

    "BTC/USDS": {'bitmex': 'BTC/USD', 'okex': 'BTC-USD-SWAP', 'huobipro': 'BTC-USD'},
    "ETH/USDS": {'okex': 'ETH-USD-SWAP', 'huobipro': 'ETH-USD'},
    "USDT/USDS": {},

    "BTC/USDT": {'binance': 'BTC/USDT', 'huobipro': 'BTC/USDT'},
    "EOS/USDT": {'binance': 'EOS/USDT', 'huobipro': 'EOS/USDT'},
    "ETH/USDT": {'binance': 'ETH/USDT', 'huobipro': 'ETH/USDT'},
    "LTC/USDT": {'binance': 'LTC/USDT', 'huobipro': 'LTC/USDT'},

    "EOS/BTC": {'binance': 'EOS/BTC', 'huobipro': 'EOS/BTC'},
    "ETH/BTC": {'binance': 'ETH/BTC', 'huobipro': 'ETH/BTC'},
    "LTC/BTC": {'binance': 'LTC/BTC', 'huobipro': 'LTC/BTC'},

    "CRV/USDT": {'binance': 'CRV/USDT', 'huobipro': 'CRV/USDT', 'okex': 'CRV/USDT'},
    "SUSHI/USDT": {'binance': 'SUSHI/USDT', 'huobipro': 'SUSHI/USDT', 'okex': 'SUSHI/USDT'},
    "UNI/USDT": {'binance': 'UNI/USDT', 'huobipro': 'UNI/USDT', 'okex': 'UNI/USDT'},
}

FETCHABLE_EXCHANGES = ["bitmex", "huobipro", "binance", "okex"]
CRAWLER_SLEEP_CONFIG = {}
C_PROXIES = ["127.0.0.1:41091"]
GRPC_MAX_MESSAGE_LENGTH = 2048

try:
    from .local_settings import *
except ImportError:
    pass
