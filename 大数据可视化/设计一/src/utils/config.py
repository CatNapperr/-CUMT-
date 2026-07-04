# -*- coding: utf-8 -*-
"""
==============================================
配置管理模块
==============================================

职责：
    - 读取 config.yaml 文件
    - 提供全局配置对象的访问
"""

import os
import sys
import yaml
import logging

logger = logging.getLogger("AQI_System.Utils.Config")

class ConfigManager:
    """全局配置管理器 (单例)"""
    _instance = None
    _config = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        """加载 yaml 配置文件"""
        try:
            # 先检查是否为 PyInstaller 打包环境
            if getattr(sys, 'frozen', False):
                # PyInstaller 打包后的环境
                root_dir = sys._MEIPASS
            else:
                # 正常运行环境：定位到项目根目录下的 config.yaml
                root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
            config_path = os.path.join(root_dir, "config.yaml")

            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    self._config = yaml.safe_load(f) or {}
                logger.info("配置文件加载成功: %s", config_path)
            else:
                logger.warning("配置文件不存在，使用默认配置: %s", config_path)
                self._config = {}
        except Exception as e:
            logger.error("加载配置文件失败: %s", str(e))
            self._config = {}

    def get(self, section: str, key: str, default=None):
        """
        获取配置项
        
        Args:
            section: 顶级块名 (如 'database', 'app')
            key: 具体键名 (如 'path', 'default_city')
            default: 若不存在返回的默认值
        """
        return self._config.get(section, {}).get(key, default)

# 提供一个全局可用的简易获取函数
def get_config(section: str, key: str, default=None):
    return ConfigManager().get(section, key, default)
