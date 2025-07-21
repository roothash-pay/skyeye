#!/usr/bin/env python
"""
手动执行 Celery 任务的示例脚本
展示如何在不启动 Celery worker 的情况下直接执行任务
"""
import os
import sys
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'skyeye.settings')
django.setup()

def execute_full_sync():
    """手动执行全量同步任务"""
    from apps.cmc_proxy.tasks import daily_full_data_sync
    
    print("🚀 开始执行 CMC 全量同步任务...")
    try:
        # 直接调用任务函数（同步执行）
        result = daily_full_data_sync()
        print(f"✅ 全量同步完成，处理了 {result} 个代币")
        return result
    except Exception as e:
        print(f"❌ 全量同步失败: {e}")
        return 0

def execute_batch_processing():
    """手动执行批量处理任务"""
    from apps.cmc_proxy.tasks import process_pending_cmc_batch_requests
    
    print("🔄 开始执行批量处理任务...")
    try:
        result = process_pending_cmc_batch_requests()
        print(f"✅ 批量处理完成，返回值: {result}")
        return result
    except Exception as e:
        print(f"❌ 批量处理失败: {e}")
        return None

def execute_klines_update():
    """手动执行K线更新任务"""
    from apps.cmc_proxy.tasks import update_cmc_klines
    
    print("📊 开始执行K线更新任务...")
    try:
        # 初始化模式：获取24小时历史数据
        result = update_cmc_klines(count=24, only_missing=True)
        print(f"✅ K线更新完成，存储了 {result} 条K线数据")
        return result
    except Exception as e:
        print(f"❌ K线更新失败: {e}")
        return 0

def execute_sync_to_db():
    """手动执行数据库同步任务"""
    from apps.cmc_proxy.tasks import sync_cmc_data_task
    
    print("💾 开始执行数据库同步任务...")
    try:
        result = sync_cmc_data_task()
        print(f"✅ 数据库同步完成，返回值: {result}")
        return result
    except Exception as e:
        print(f"❌ 数据库同步失败: {e}")
        return None

def show_menu():
    """显示菜单"""
    print("\n" + "="*50)
    print("🔧 SkyEye Celery 任务手动执行工具")
    print("="*50)
    print("1. 执行全量同步 (daily_full_data_sync)")
    print("2. 执行批量处理 (process_pending_cmc_batch_requests)")
    print("3. 执行K线更新 (update_cmc_klines)")
    print("4. 执行数据库同步 (sync_cmc_data_task)")
    print("5. 完整流程 (全量同步 + 数据库同步)")
    print("0. 退出")
    print("="*50)

def main():
    """主函数"""
    while True:
        show_menu()
        choice = input("\n请选择要执行的任务 (0-5): ").strip()
        
        if choice == '0':
            print("👋 退出程序")
            break
        elif choice == '1':
            execute_full_sync()
        elif choice == '2':
            execute_batch_processing()
        elif choice == '3':
            execute_klines_update()
        elif choice == '4':
            execute_sync_to_db()
        elif choice == '5':
            print("🔄 开始执行完整流程...")
            result1 = execute_full_sync()
            if result1 > 0:
                execute_sync_to_db()
                print("✅ 完整流程执行完成！")
            else:
                print("❌ 全量同步失败，跳过数据库同步")
        else:
            print("❌ 无效选择，请重新输入")
        
        input("\n按回车键继续...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 程序被用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 程序执行出错: {e}")
        sys.exit(1)