# encoding=utf-8


from django.core.management.base import BaseCommand

from sevices.mp_client import MpClient


class Command(BaseCommand):
    def handle(self, *args, **options):
        mp_client = MpClient()
        ret_info = mp_client.get_symbol_price()
        print("get_symbol_price ret_info====", ret_info)
        ret_info = mp_client.get_stable_coin_price()
        print("\nget_stable_coin_price ret_info====", ret_info)
