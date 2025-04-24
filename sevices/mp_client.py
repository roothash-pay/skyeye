# encoding=utf-8

import grpc
from django.conf import settings

from sevices.savourrpc import market_pb2_grpc, market_pb2


class MpClient:
    def __init__(self):
        options = [
            ('grpc.max_receive_message_length', settings.GRPC_MAX_MESSAGE_LENGTH),
        ]
        channel = grpc.insecure_channel("localhost:50250", options=options)
        self.stub = market_pb2_grpc.PriceServiceStub(channel)

    def get_symbol_price(self, consumer_token: str = None):
        return self.stub.getSymbolPrices(
            market_pb2.SymbolPriceRequest(
                consumer_token=consumer_token
            )
        )

    def get_stable_coin_price(self, consumer_token: str = None, coin_id: str = '0'):
        return self.stub.getStableCoinPrice(
            market_pb2.StableCoinPriceRequest(
                consumer_token=consumer_token,
                coin_id=coin_id
            )
        )