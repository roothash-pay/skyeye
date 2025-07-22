# -*- coding: utf-8 -*-

# 稳定币符号列表 - 用于识别交易对中的计价货币, 优先级从上到下递减
STABLECOIN_SYMBOLS = [
    # 主流稳定币 - 最稳定，流动性最好
    'USDT',  # Tether - 市值最大
    'USDC',  # USD Coin - 合规性好
    'USD',
    'DAI',  # MakerDAO - 去中心化

    # 次级稳定币 - 相对稳定，有一定市场份额
    'USDS',
    'TUSD',  # TrueUSD
    'USDP',  # Pax Dollar（原PAX）
    'FRAX',  # Frax - 部分算法
    'LUSD',  # Liquity USD
    'PYUSD',  # PayPal USD - 新兴但背景强

    # 特定生态稳定币 - 在特定场景有用
    'SUSD',  # Synthetix
    'MIM',  # Magic Internet Money
    'DOLA',  # Inverse Finance
    'ALUSD',  # Alchemix USD
    'CUSD',  # Celo Dollar
]

# 交易所优先级列表 - 用于在多个交易所提供同一交易对时选择最优价格, 优先级从上到下递减
EXCHANGE_PRIORITY = [
    'binance',
    'bybit',
    'coinbase',
    # 'upbit', # 多数交易对是以韩元为报价
    'okx',
    'bitget',
    'mexc',
    'gate',
    'kucoin',
    'cryptocom',
    'htx',
    'kraken',
    'lbank',
    'bitmart',
    'ascendex',
    'poloniex',
    'bingx',
    'latoken',
    'yobit',
    'coinex',
    'xt',
    'phemex',
    'probit',
    'bigone',
    'hitbtc',
    'coinup',  # CoinUp - CP/USDT专用
]
