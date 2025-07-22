#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from asgiref.sync import sync_to_async

from apps.price_oracle.coinup_adapter import CoinUpAdapter
from apps.price_oracle.services import price_service
from common.helpers import getLogger

logger = getLogger(__name__)


class Command(BaseCommand):
    help = 'Collect CP/USDT prices from CoinUp using title parsing (optimized)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--run-once',
            action='store_true',
            help='Run once and exit (default is continuous monitoring)',
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=5,  # 5秒间隔，支持实时价格监控
            help='Collection interval in seconds (default: 5)',
        )

    def handle(self, *args, **options):
        """处理命令执行"""
        run_once = options['run_once']
        interval = options['interval']

        self.stdout.write(
            self.style.SUCCESS(
                f'🚀 开始收集CoinUp CP/USDT价格\n'
                f'模式: {"单次执行" if run_once else f"实时监控(间隔{interval}秒)"}\n'
                f'方法: 开源API（毫秒级响应，极速高效） ⚡'
            )
        )

        if run_once:
            success = self.collect_price_once()
            if success:
                self.stdout.write(self.style.SUCCESS('✅ 价格收集成功'))
            else:
                self.stdout.write(self.style.ERROR('❌ 价格收集失败'))
        else:
            self.collect_price_continuously(interval)

    def collect_price_once(self) -> bool:
        """单次价格收集"""
        adapter = None
        try:
            self.stdout.write('⚡ 初始化CoinUp API适配器...')
            
            adapter = CoinUpAdapter()
            
            self.stdout.write('📊 开始收集价格数据（开源API）...')
            start_time = timezone.now()
            
            # 获取价格
            price_data = adapter.get_cp_usdt_price()
            
            elapsed = (timezone.now() - start_time).total_seconds()
            
            if price_data:
                # 转换为数据库格式
                db_price = {
                    'base_asset': price_data.base_asset,
                    'symbol': price_data.symbol,
                    'quote_asset': price_data.quote_asset,
                    'exchange': 'coinup',
                    'price': str(price_data.price),
                    'price_change_24h': str(price_data.price_change_24h) if price_data.price_change_24h else None,
                    'volume_24h': str(price_data.volume_24h) if price_data.volume_24h else None,
                    'exchange_priority': 99,  # CoinUp优先级较低
                    'quote_priority': 1,      # USDT优先级最高
                }
                
                # 保存到数据库
                saved_count = price_service.save_prices_to_db_upsert([db_price])
                
                if saved_count > 0:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✅ 成功保存CP价格: ${price_data.price}\n'
                            f'   交易对: {price_data.symbol}\n'
                            f'   用时: {elapsed:.1f}秒 ⚡\n'
                            f'   24h变化: {price_data.price_change_24h}%\n'
                            f'   24h成交量: {price_data.volume_24h}'
                        )
                    )
                    return True
                else:
                    self.stdout.write(self.style.WARNING('⚠️  价格保存失败'))
            else:
                self.stdout.write(self.style.WARNING(f'⚠️  未获取到价格数据（用时: {elapsed:.1f}秒）'))
                
        except Exception as e:
            logger.error(f'收集价格失败: {e}')
            self.stdout.write(self.style.ERROR(f'❌ 收集失败: {e}'))
        
        finally:
            if adapter:
                try:
                    asyncio.run(adapter.close())
                    self.stdout.write('🔒 已关闭HTTP会话')
                except Exception as e:
                    logger.warning(f'关闭适配器失败: {e}')
        
        return False

    def collect_price_continuously(self, interval: int):
        """连续价格收集"""
        self.stdout.write(f'🔄 开始实时价格监控 (间隔{interval}秒)...')
        self.stdout.write('💡 提示: 按 Ctrl+C 停止监控')
        
        success_count = 0
        failure_count = 0
        total_time = 0
        
        try:
            while True:
                start_time = timezone.now()
                self.stdout.write(f'\n⏰ [{start_time.strftime("%H:%M:%S")}] 开始收集...')
                
                # 每次都创建新的适配器，避免状态积累
                adapter = CoinUpAdapter()
                
                try:
                    # 获取价格
                    price_data = adapter.get_cp_usdt_price()
                    
                    collection_time = (timezone.now() - start_time).total_seconds()
                    total_time += collection_time
                    
                    if price_data:
                        # 保存到数据库
                        db_price = {
                            'base_asset': price_data.base_asset,
                            'symbol': price_data.symbol,
                            'quote_asset': price_data.quote_asset,
                            'exchange': 'coinup',
                            'price': str(price_data.price),
                            'price_change_24h': str(price_data.price_change_24h) if price_data.price_change_24h else None,
                            'volume_24h': str(price_data.volume_24h) if price_data.volume_24h else None,
                            'exchange_priority': 99,
                            'quote_priority': 1,
                        }
                        
                        saved_count = price_service.save_prices_to_db_upsert([db_price])
                        
                        if saved_count > 0:
                            success_count += 1
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'✅ 价格: ${price_data.price} '
                                    f'(用时: {collection_time:.1f}s) ⚡'
                                )
                            )
                        else:
                            failure_count += 1
                            self.stdout.write(self.style.WARNING('⚠️  保存失败'))
                    else:
                        failure_count += 1
                        self.stdout.write(
                            self.style.WARNING(f'⚠️  未获取到价格 (用时: {collection_time:.1f}s)')
                        )
                
                except Exception as e:
                    failure_count += 1
                    collection_time = (timezone.now() - start_time).total_seconds()
                    total_time += collection_time
                    logger.error(f'收集价格异常: {e}')
                    self.stdout.write(self.style.ERROR(f'❌ 异常: {str(e)[:100]}'))
                
                finally:
                    # 确保每次都关闭浏览器
                    try:
                        asyncio.run(adapter.close())
                    except:
                        pass
                
                # 输出统计信息
                if (success_count + failure_count) % 10 == 0:
                    total_attempts = success_count + failure_count
                    success_rate = (success_count / total_attempts * 100) if total_attempts > 0 else 0
                    avg_time = (total_time / total_attempts) if total_attempts > 0 else 0
                    self.stdout.write(
                        self.style.HTTP_INFO(
                            f'📈 统计: 成功{success_count}次, 失败{failure_count}次 '
                            f'(成功率: {success_rate:.1f}%, 平均用时: {avg_time:.1f}s)'
                        )
                    )
                
                # 计算等待时间
                elapsed = (timezone.now() - start_time).total_seconds()
                wait_time = max(0, interval - elapsed)
                
                if wait_time > 0:
                    self.stdout.write(f'⏳ 等待 {wait_time:.0f} 秒...')
                    import time
                    time.sleep(wait_time)
                    
        except KeyboardInterrupt:
            self.stdout.write('\n\n🛑 监控已停止')
            total_attempts = success_count + failure_count
            if total_attempts > 0:
                success_rate = success_count / total_attempts * 100
                avg_time = total_time / total_attempts
                self.stdout.write(
                    self.style.HTTP_INFO(
                        f'📊 最终统计: 成功{success_count}次, 失败{failure_count}次 '
                        f'(成功率: {success_rate:.1f}%, 平均用时: {avg_time:.1f}s)'
                    )
                )