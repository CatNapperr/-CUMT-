# -*- coding: utf-8 -*-
"""
==============================================
城市空气质量(AQI)实时监测与预测分析系统
项目入口文件
==============================================

技术栈：CustomTkinter + Matplotlib + Seaborn + SQLite3 + Pandas
架构：MVC (Model-View-Controller)

启动方式：
    python main.py
"""

import sys
import os
import logging
from datetime import datetime

# 将项目根目录加入 Python 路径，确保模块导入正常
# 处理 PyInstaller 打包后的路径：在打包后，__file__ 会在 _internal 目录中
if getattr(sys, 'frozen', False):
    # PyInstaller 打包后的环境
    ROOT_DIR = sys._MEIPASS
else:
    # 正常运行环境
    ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, ROOT_DIR)

# ============================================
# 日志配置
# ============================================
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt=LOG_DATE_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),  # 控制台输出
    ]
)

logger = logging.getLogger("AQI_System")


def check_dependencies() -> bool:
    """
    检查核心依赖库是否已安装。
    如果缺少关键依赖，记录错误日志并返回 False。

    Returns:
        bool: 所有依赖满足返回 True，否则返回 False
    """
    required_packages = {
        "customtkinter": "CustomTkinter (GUI 框架)",
        "matplotlib": "Matplotlib (数据可视化)",
        "seaborn": "Seaborn (统计可视化)",
        "pandas": "Pandas (数据处理)",
        "numpy": "NumPy (数值计算)",
    }

    missing = []
    for package, description in required_packages.items():
        try:
            __import__(package)
        except ImportError:
            missing.append(f"  - {package}: {description}")

    if missing:
        logger.error("以下依赖库未安装，请先执行 pip install -r requirements.txt")
        for item in missing:
            logger.error(item)
        return False

    logger.info("所有核心依赖检查通过 ✓")
    return True


def main():
    """
    应用程序主入口函数。
    执行流程：
        1. 打印启动横幅
        2. 检查依赖与数据目录
        3. 实例化 Model 层 (DatabaseManager)
        4. 实例化 View 层 (MainWindow)
        5. 实例化 Controller 层，组装 MVC
        6. 启动 GUI 主循环
    """
    # ---- 启动横幅 ----
    banner = """
    ╔══════════════════════════════════════════════════════════╗
    ║     城市空气质量(AQI)实时监测与预测分析系统             ║
    ║     City Air Quality Index Monitoring & Prediction      ║
    ╠══════════════════════════════════════════════════════════╣
    ║     版本: v1.0.0                                        ║
    ║     架构: MVC (Model-View-Controller)                   ║
    ║     启动时间: {timestamp}                    ║
    ╚══════════════════════════════════════════════════════════╝
    """.format(timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print(banner)

    # ---- Step 1: 依赖检查 ----
    logger.info("正在检查系统依赖...")
    if not check_dependencies():
        logger.critical("依赖检查失败，系统无法启动。")
        sys.exit(1)

    # ---- Step 2: 确保数据目录存在 ----
    data_dir = os.path.join(ROOT_DIR, "data")
    os.makedirs(data_dir, exist_ok=True)
    logger.info("数据目录就绪: %s", data_dir)

    try:
        logger.info("正在初始化 MVC 组件...")
        
        # 延迟导入内部模块，确保依赖检查已通过
        from src.model.database import DatabaseManager
        from src.view.main_window import MainWindow
        from src.controller.app_controller import AppController

        # ---- Step 3: 初始化 Model (数据层) ----
        # 获取单例实例，内部会自动建立数据库连接并建表
        logger.info("-> 实例化 Model...")
        db_manager = DatabaseManager()
        db_manager.create_tables()

        # ---- Step 4: 初始化 View (表现层) ----
        logger.info("-> 实例化 View...")
        app_window = MainWindow()

        # ---- Step 5: 初始化 Controller (控制层) 并进行组装 ----
        # 将 model 和 view 注入控制器，建立绑定和初始化渲染
        logger.info("-> 实例化 Controller 并完成组装...")
        controller = AppController(model=db_manager, view=app_window)

        # ---- Step 6: 启动 GUI 主循环 ----
        logger.info("系统初始化完毕，正在显示主窗口...")
        app_window.mainloop()
        
    except Exception as e:
        logger.critical("应用程序运行异常: %s", str(e), exc_info=True)
    finally:
        # 停止后台抓取服务
        if 'controller' in locals():
            controller.api_fetcher.stop_auto_fetch()
            
        # 确保应用退出时安全关闭数据库连接
        if 'db_manager' in locals():
            db_manager.close()
        logger.info("应用程序已正常退出。")


# ============================================
# 程序入口
# ============================================
if __name__ == "__main__":
    main()
