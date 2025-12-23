#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
独立的调度器启动脚本
用于在生产环境中单独运行调度器进程
"""
import os
import sys
import django
import logging

# 设置 Django 配置
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'application.settings')

# 初始化 Django
django.setup()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('scheduler.log')
    ]
)

logger = logging.getLogger(__name__)


def main():
    """启动调度器"""
    try:
        from scheduler.service import scheduler_service
        
        logger.info("正在启动 APScheduler 调度器...")
        
        # 启动调度器
        if not scheduler_service.is_running():
            scheduler_service.start()
            logger.info("✅ APScheduler 调度器已成功启动")
        else:
            logger.warning("⚠️  调度器已经在运行中")
        
        # 保持进程运行
        logger.info("调度器正在运行，按 Ctrl+C 停止...")
        
        import time
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("收到停止信号，正在关闭调度器...")
            scheduler_service.shutdown()
            logger.info("✅ 调度器已安全关闭")
    
    except Exception as e:
        logger.error(f"❌ 调度器启动失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
