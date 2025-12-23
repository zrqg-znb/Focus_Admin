# -*- coding: utf-8 -*-
import logging
import time
from datetime import datetime

logger = logging.getLogger(__name__)

def test_task(name="World"):
    """
    测试定时任务
    :param name: 名字
    """
    logger.info(f"[{datetime.now()}] Hello, {name}! This is a test task.")
    print(f"[{datetime.now()}] Hello, {name}! This is a test task running.")
    return f"Success: Hello {name}"

def long_running_task(seconds=5):
    """
    模拟耗时任务
    :param seconds: 耗时秒数
    """
    logger.info(f"Task started, will sleep for {seconds} seconds...")
    time.sleep(seconds)
    logger.info("Task finished.")
    return "Done"
