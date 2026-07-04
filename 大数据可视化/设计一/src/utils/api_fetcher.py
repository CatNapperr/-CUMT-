# -*- coding: utf-8 -*-
"""
==============================================
实时数据抓取模块
==============================================

职责：
    - 定时从第三方气象 API 获取最新的空气质量数据
    - 验证数据并存入本地数据库
"""

import logging
import threading
import time
from datetime import datetime
import random

# 在实际项目中，你可以 import requests 并调用真实 API
# import requests

logger = logging.getLogger("AQI_System.Utils.ApiFetcher")

class RealTimeFetcher:
    def __init__(self, db_manager):
        self.db = db_manager
        self._running = False
        self._thread = None

    def start_auto_fetch(self, interval_seconds=3600):
        """开启后台定时抓取任务"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._fetch_loop,
            args=(interval_seconds,),
            daemon=True
        )
        self._thread.start()
        logger.info(f"已启动自动实时抓取服务，间隔 {interval_seconds} 秒")

    def stop_auto_fetch(self):
        """停止后台抓取任务"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=1)
        logger.info("实时抓取服务已停止")

    def _fetch_loop(self, interval):
        while self._running:
            self.fetch_latest_data()
            # 简单休眠。实际项目中推荐使用 schedule 或 APScheduler 库
            for _ in range(interval):
                if not self._running: break
                time.sleep(1)

    def fetch_latest_data(self):
        """
        立即抓取一次最新数据。
        这里我们不调用真实需付费的 API，而是模拟抓取今天最新的一条记录。
        """
        logger.info("正在请求第三方 API 获取最新实时数据...")
        
        # 假设我们获取所有目前数据库里有的城市的新数据
        cities = self.db.get_city_list()
        if not cities:
            cities = ["北京", "上海", "广州", "深圳"]

        today_str = datetime.now().strftime("%Y-%m-%d")
        
        records = []
        for city in cities:
            # ---------------------------------------------------------
            # 真实 API 调用模板：
            # url = f"https://api.example.com/aqi/now?city={city}&token=YOUR_TOKEN"
            # resp = requests.get(url).json()
            # pm25 = resp['data']['pm25']
            # ...
            # ---------------------------------------------------------
            
            # 模拟 API 返回的随机真实感数据
            pm25 = round(random.uniform(20, 150), 1)
            pm10 = round(pm25 * random.uniform(1.2, 2.0), 1)
            so2 = round(random.uniform(5, 30), 1)
            no2 = round(random.uniform(10, 60), 1)
            aqi = int(max(pm25, pm10/2))
            
            records.append((city, today_str, pm25, pm10, so2, no2, aqi))

        try:
            # 使用 INSERT OR REPLACE，避免重复抓取导致的主键冲突
            self.db.insert_many_records(records)
            logger.info(f"成功拉取并更新了 {len(cities)} 个城市的今日实时数据")
            return True
        except Exception as e:
            logger.error(f"保存实时数据失败: {e}")
            return False
