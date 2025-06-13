# -*- coding: utf-8 -*-

import logging
from urllib.parse import unquote


class BaseException(Exception):
    message = "An unknown exception occurred."
    code = 400

    def __init__(self, message=None, **kwargs):
        self.kwargs = kwargs

        if 'code' not in self.kwargs and hasattr(self, 'code'):
            self.kwargs['code'] = self.code

        if message:
            self.message = unquote(message)

        try:
            self.message = self.message % kwargs
        except Exception as e:
            # kwargs doesn't match a variable in the message
            # log the issue and the kwargs
            logging.exception('Exception in string format operation, kwargs: %s', self.message)
            raise e

        super(BaseException, self).__init__()

    def __str__(self):
        return self.message


class NotFound(BaseException):
    message = "Resource could not be found."
    code = 404


class AccessForbidden(BaseException):
    message = "Access Forbidden"
    code = 403


class Unauthorized(BaseException):
    message = "Not Authorized"
    code = 401


class Conflict(BaseException):
    message = 'Conflict.'
    code = 409


class TableCreateError(BaseException):
    message = "Table Create Error"
    code = 1001


class AccountNotFound(NotFound):
    message = "Account with ID %(account_id)s not found"


class AccountNameNotFound(NotFound):
    message = "Account with Name %(account_name)s not found"


class AccountCreateError(TableCreateError):
    message = "Account with Name %(account_name)s create fail"


class AssetNotFound(NotFound):
    message = "Asset with ID %(asset_id)s not found"


class AssetSymbolNotFound(NotFound):
    message = "Asset with Symbol %(asset_symbol)s not found"


class TradingPairNotFound(NotFound):
    message = "TradingPair with ID %(trading_pair_id)s not found"


class TradingPairSymbolDisplayNotFound(NotFound):
    message = "TradingPair with symbol_display '%(symbol_display)s' not found"


class ExchangeNotFound(NotFound):
    message = "Exchange with ID %(exchange_id)s not found"


class OrderNotFound(NotFound):
    message = "Order with ID %(order_id)s not found"


class AccountNameAlreadyExists(Conflict):
    message = "Account with Name %(account_name)s already exists"


class AssetSymbolAlreadyExists(Conflict):
    message = "Asset with Symbol %(asset_symbol)s already exists"


class TradingPairSymbolDisplayAlreadyExists(Conflict):
    message = "TradingPair with symbol_display '%(symbol_display)s' already exists"


class ExchangeNameAlreadyExists(Conflict):
    message = "Exchange with Name %(exchange_name)s already exists"


class OrderAlreadyExists(Conflict):
    message = 'Order with request_id %(request_id)s already exists'


class ParamError(BaseException):
    message = "illegal param"
    code = 400


class MethodFailure(BaseException):
    message = "server constraint"
    code = 420


class CCXTException(BaseException):
    message = "ccxt exception"


def notify_sentry():
    # https://stackoverflow.com/questions/50702642/making-sentry-report-5xx-errors-in-multi-thread-environment
    from raven.contrib.django.raven_compat.models import client

    client.captureException()
