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
        "NAME": "skyeye",
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
    "BTC/USDS": {'bitmex': 'BTC/USD', 'okx': 'BTC-USD-SWAP', 'huobi': 'BTC-USD'},
    "ETH/USDS": {'okx': 'ETH-USD-SWAP', 'huobi': 'ETH-USD'},
    "USDT/USDS": {},

    "BTC/USDT": {'binance': 'BTC/USDT', 'huobi': 'BTC/USDT', 'okx': 'BTC/USDT', 'bybit': 'BTC/USDT', 'bitget': 'BTC/USDT', 'bitmex': 'BTC/USDT'},
    "EOS/USDT": {'binance': 'EOS/USDT', 'huobi': 'EOS/USDT', 'okx': 'EOS/USDT', 'bybit': 'EOS/USDT', 'bitget': 'EOS/USDT', 'bitmex': 'EOS/USDT'},
    "ETH/USDT": {'binance': 'ETH/USDT', 'huobi': 'ETH/USDT', 'okx': 'ETH/USDT', 'bybit': 'ETH/USDT', 'bitget': 'ETH/USDT', 'bitmex': 'ETH/USDT'},
    "LTC/USDT": {'binance': 'LTC/USDT', 'huobi': 'LTC/USDT', 'okx': 'LTC/USDT', 'bybit': 'LTC/USDT', 'bitget': 'LTC/USDT', 'bitmex': 'LTC/USDT'},

    "EOS/BTC": {'binance': 'EOS/BTC', 'huobi': 'EOS/BTC', 'okx': 'EOS/BTC', 'bybit': 'EOS/BTC', 'bitget': 'EOS/BTC', 'bitmex': 'EOS/BTC'},
    "ETH/BTC": {'binance': 'ETH/BTC', 'huobi': 'ETH/BTC', 'okx': 'ETH/BTC', 'bybit': 'ETH/BTC', 'bitget': 'ETH/BTC', 'bitmex': 'ETH/BTC'},
    "LTC/BTC": {'binance': 'LTC/BTC', 'huobi': 'LTC/BTC', 'okx': 'LTC/BTC', 'bybit': 'LTC/BTC', 'bitget': 'LTC/BTC', 'bitmex': 'LTC/BTC'},

    "CRV/USDT": {'binance': 'CRV/USDT', 'huobi': 'CRV/USDT', 'okx': 'CRV/USDT'},
    "SUSHI/USDT": {'binance': 'SUSHI/USDT', 'huobi': 'SUSHI/USDT', 'okx': 'SUSHI/USDT'},
    "UNI/USDT": {'binance': 'UNI/USDT', 'huobi': 'UNI/USDT', 'okx': 'UNI/USDT'},
    "SOL/USDT": {'binance': 'SOL/USDT', 'huobi': 'SOL/USDT', 'okx': 'SOL/USDT', 'bybit': 'SOL/USDT', 'bitget': 'SOL/USDT', 'bitmex': 'SOL/USDT'},
}

FETCHABLE_EXCHANGES = ["bitmex", "huobi", "binance", "okx", "bybit", "bitget"]
CRAWLER_SLEEP_CONFIG = {}
C_PROXIES = []
GRPC_MAX_MESSAGE_LENGTH = 2048

# External API Configurations
FRANKFURTER_API_URL = "https://api.frankfurter.app/latest?from=USD&to=CNY"
DEFAULT_USD_CNY_RATE = '7.29'  # Default fallback rate as string

# Quote assets considered stable enough to represent USD price in OTC calculations
ACCEPTABLE_QUOTE_ASSETS_FOR_OTC = ['USDT', 'USDC']

try:
    from .local_settings import *
except ImportError:
    pass

# Default primary key field type
# https://docs.djangoproject.com/en/stable/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
