# -*- coding: utf-8 -*-
"""
==============================================
数据库管理模块 (Model 层)
==============================================

职责：
    - 封装 SQLite 数据库的连接与操作
    - 管理数据表的创建与索引
    - 提供数据的增删改查接口

设计模式：单例模式 (Singleton) —— 确保全局只有一个数据库连接实例
"""

import os
import sys
import sqlite3
import logging
from typing import List, Tuple, Optional, Any, Dict

import pandas as pd

logger = logging.getLogger("AQI_System.Model.Database")


class DatabaseManager:
    """
    SQLite 数据库管理器（单例模式）。

    负责管理与 SQLite 数据库的所有交互操作，包括：
    - 数据库连接管理
    - 数据表创建与索引构建
    - 数据的增删改查（CRUD）

    使用方式::

        db = DatabaseManager()  # 自动连接到默认数据库
        db.create_tables()      # 创建所有数据表
        db.insert_record(...)   # 插入单条记录
        db.close()              # 关闭连接

    Attributes:
        db_path (str): SQLite 数据库文件路径
        connection (sqlite3.Connection): 数据库连接对象
        cursor (sqlite3.Cursor): 数据库游标对象
    """

    # ---- 单例模式实现 ----
    _instance: Optional["DatabaseManager"] = None
    _initialized: bool = False

    def __new__(cls, db_path: Optional[str] = None) -> "DatabaseManager":
        """
        单例模式的 __new__ 方法。
        确保整个应用生命周期内只存在一个 DatabaseManager 实例。

        Args:
            db_path: SQLite 数据库文件路径（仅首次创建时有效）

        Returns:
            DatabaseManager: 唯一的数据库管理器实例
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, db_path: Optional[str] = None):
        """
        初始化数据库管理器。

        Args:
            db_path: SQLite 数据库文件路径。
                     默认为项目 data 目录下的 aqi.db
        """
        # 单例模式：避免重复初始化
        if DatabaseManager._initialized:
            return

        # 计算默认数据库路径：项目根目录/data/aqi.db
        if db_path is None:
            # 先检查是否为 PyInstaller 打包环境
            if getattr(sys, 'frozen', False):
                # PyInstaller 打包后的环境
                root_dir = sys._MEIPASS
            else:
                # 正常运行环境：向上3级目录
                root_dir = os.path.dirname(os.path.dirname(os.path.dirname(
                    os.path.abspath(__file__)
                )))
            db_path = os.path.join(root_dir, "data", "aqi.db")

        self.db_path: str = db_path
        self.connection: Optional[sqlite3.Connection] = None
        self.cursor: Optional[sqlite3.Cursor] = None

        # 确保数据库目录存在
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

        # 建立数据库连接
        self._connect()

        DatabaseManager._initialized = True
        logger.info("DatabaseManager 初始化完成 (单例) | 数据库: %s", self.db_path)

    # ============================================
    # 连接管理
    # ============================================

    def _connect(self) -> None:
        """
        建立与 SQLite 数据库的连接。

        配置说明：
            - check_same_thread=False：允许多线程访问
            - WAL 模式：提升并发读写性能
            - 外键约束：启用外键支持

        Raises:
            sqlite3.Error: 数据库连接失败时抛出
        """
        try:
            self.connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False  # 允许跨线程使用
            )
            # 返回字典形式的查询结果（可选）
            self.connection.row_factory = sqlite3.Row
            self.cursor = self.connection.cursor()

            # 启用 WAL 模式，提升并发性能
            self.cursor.execute("PRAGMA journal_mode=WAL;")
            # 启用外键约束
            self.cursor.execute("PRAGMA foreign_keys=ON;")

            logger.info("数据库连接成功: %s", self.db_path)
        except sqlite3.Error as e:
            logger.error("数据库连接失败: %s", str(e))
            raise

    def close(self) -> None:
        """
        安全关闭数据库连接。
        关闭前自动提交未提交的事务。
        """
        try:
            if self.connection:
                self.connection.commit()
                self.connection.close()
                self.connection = None
                self.cursor = None
                DatabaseManager._initialized = False
                DatabaseManager._instance = None
                logger.info("数据库连接已关闭")
        except sqlite3.Error as e:
            logger.error("关闭数据库连接时出错: %s", str(e))

    def _ensure_connection(self) -> None:
        """
        确保数据库连接处于活跃状态。
        如果连接已断开，则自动重新连接。
        """
        if self.connection is None:
            logger.warning("数据库连接已断开，正在重新连接...")
            self._connect()

    # ============================================
    # 数据表管理
    # ============================================

    def create_tables(self) -> None:
        """
        创建所有必要的数据表和索引。

        当前创建的表：
            - aqi_records：空气质量记录主表

        当前创建的索引：
            - idx_city_date：city + record_date 联合索引（加速按城市和日期查询）
        """
        self._ensure_connection()

        try:
            # ---- 创建 aqi_records 表 ----
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS aqi_records (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    city         TEXT    NOT NULL,           -- 城市名称
                    record_date  TEXT    NOT NULL,           -- 记录日期 (YYYY-MM-DD)
                    pm25         REAL    DEFAULT 0.0,        -- PM2.5 浓度 (μg/m³)
                    pm10         REAL    DEFAULT 0.0,        -- PM10 浓度 (μg/m³)
                    so2          REAL    DEFAULT 0.0,        -- SO2 浓度 (μg/m³)
                    no2          REAL    DEFAULT 0.0,        -- NO2 浓度 (μg/m³)
                    aqi_score    INTEGER DEFAULT 0,          -- AQI 综合指数
                    created_at   TEXT    DEFAULT (datetime('now', 'localtime')),
                    UNIQUE(city, record_date)                -- 保证同一城市每天只有一条记录
                );
            """)

            # ---- 创建联合索引：city + record_date ----
            # 用于优化按城市和日期范围查询的性能
            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_city_date
                ON aqi_records (city, record_date);
            """)

            self.connection.commit()
            logger.info("数据表和索引创建成功 ✓")

        except sqlite3.Error as e:
            logger.error("创建数据表失败: %s", str(e))
            self.connection.rollback()
            raise

    # ============================================
    # 数据插入操作
    # ============================================

    def insert_record(
        self,
        city: str,
        record_date: str,
        pm25: float,
        pm10: float,
        so2: float,
        no2: float,
        aqi_score: int
    ) -> int:
        """
        插入单条空气质量记录。

        Args:
            city: 城市名称
            record_date: 记录日期，格式 YYYY-MM-DD
            pm25: PM2.5 浓度 (μg/m³)
            pm10: PM10 浓度 (μg/m³)
            so2: SO2 浓度 (μg/m³)
            no2: NO2 浓度 (μg/m³)
            aqi_score: AQI 综合指数

        Returns:
            int: 插入记录的 ID

        Raises:
            sqlite3.Error: 插入失败时抛出
        """
        self._ensure_connection()

        try:
            self.cursor.execute("""
                INSERT OR REPLACE INTO aqi_records (city, record_date, pm25, pm10, so2, no2, aqi_score)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (city, record_date, pm25, pm10, so2, no2, aqi_score))

            self.connection.commit()
            record_id = self.cursor.lastrowid
            logger.debug("插入记录成功 | ID: %d | 城市: %s | 日期: %s", record_id, city, record_date)
            return record_id

        except sqlite3.Error as e:
            logger.error("插入记录失败: %s", str(e))
            self.connection.rollback()
            raise

    def insert_many_records(self, records: List[Tuple]) -> int:
        """
        批量插入空气质量记录。

        Args:
            records: 记录列表，每条记录为元组：
                     (city, record_date, pm25, pm10, so2, no2, aqi_score)

        Returns:
            int: 成功插入的记录数量

        Raises:
            sqlite3.Error: 批量插入失败时抛出
        """
        self._ensure_connection()

        try:
            self.cursor.executemany("""
                INSERT OR REPLACE INTO aqi_records (city, record_date, pm25, pm10, so2, no2, aqi_score)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, records)

            self.connection.commit()
            count = self.cursor.rowcount
            logger.info("批量插入成功 | 共插入 %d 条记录", count)
            return count

        except sqlite3.Error as e:
            logger.error("批量插入失败: %s", str(e))
            self.connection.rollback()
            raise

    def insert_dataframe(self, df: pd.DataFrame) -> int:
        """
        将 Pandas DataFrame 批量插入数据库。

        DataFrame 必须包含以下列：
            city, record_date, pm25, pm10, so2, no2, aqi_score

        Args:
            df: 包含空气质量数据的 DataFrame

        Returns:
            int: 成功插入的记录数量

        Raises:
            ValueError: DataFrame 缺少必要列时抛出
            sqlite3.Error: 数据库操作失败时抛出
        """
        required_columns = {"city", "record_date", "pm25", "pm10", "so2", "no2", "aqi_score"}
        missing_columns = required_columns - set(df.columns)

        if missing_columns:
            raise ValueError(f"DataFrame 缺少以下必要列: {missing_columns}")

        # 将 DataFrame 转换为元组列表
        records = list(df[["city", "record_date", "pm25", "pm10", "so2", "no2", "aqi_score"]].itertuples(
            index=False, name=None
        ))

        return self.insert_many_records(records)

    # ============================================
    # 数据查询操作
    # ============================================

    def query_all(self, limit: int = 1000) -> pd.DataFrame:
        """
        查询所有空气质量记录。

        Args:
            limit: 最大返回记录数，默认 1000

        Returns:
            pd.DataFrame: 查询结果
        """
        self._ensure_connection()

        try:
            df = pd.read_sql_query(
                "SELECT * FROM aqi_records ORDER BY record_date DESC LIMIT ?",
                self.connection,
                params=(limit,)
            )
            logger.debug("查询全部记录 | 返回 %d 条", len(df))
            return df
        except Exception as e:
            logger.error("查询全部记录失败: %s", str(e))
            return pd.DataFrame()

    def query_by_city(self, city: str) -> pd.DataFrame:
        """
        按城市名称查询空气质量记录。

        Args:
            city: 城市名称

        Returns:
            pd.DataFrame: 指定城市的所有记录
        """
        self._ensure_connection()

        try:
            df = pd.read_sql_query(
                "SELECT * FROM aqi_records WHERE city = ? ORDER BY record_date ASC",
                self.connection,
                params=(city,)
            )
            logger.debug("按城市查询 | 城市: %s | 返回 %d 条", city, len(df))
            return df
        except Exception as e:
            logger.error("按城市查询失败: %s", str(e))
            return pd.DataFrame()

    def query_by_date_range(
        self,
        start_date: str,
        end_date: str,
        city: Optional[str] = None
    ) -> pd.DataFrame:
        """
        按日期范围查询空气质量记录。

        Args:
            start_date: 开始日期，格式 YYYY-MM-DD
            end_date: 结束日期，格式 YYYY-MM-DD
            city: 可选的城市名称过滤

        Returns:
            pd.DataFrame: 查询结果
        """
        self._ensure_connection()

        try:
            if city:
                df = pd.read_sql_query(
                    """SELECT * FROM aqi_records
                       WHERE city = ? AND record_date BETWEEN ? AND ?
                       ORDER BY record_date ASC""",
                    self.connection,
                    params=(city, start_date, end_date)
                )
            else:
                df = pd.read_sql_query(
                    """SELECT * FROM aqi_records
                       WHERE record_date BETWEEN ? AND ?
                       ORDER BY city, record_date ASC""",
                    self.connection,
                    params=(start_date, end_date)
                )

            logger.debug(
                "按日期范围查询 | %s ~ %s | 城市: %s | 返回 %d 条",
                start_date, end_date, city or "全部", len(df)
            )
            return df
        except Exception as e:
            logger.error("按日期范围查询失败: %s", str(e))
            return pd.DataFrame()

    def get_city_list(self) -> List[str]:
        """
        获取数据库中所有不重复的城市名称列表。

        Returns:
            List[str]: 城市名称列表
        """
        self._ensure_connection()

        try:
            self.cursor.execute("SELECT DISTINCT city FROM aqi_records ORDER BY city")
            cities = [row[0] for row in self.cursor.fetchall()]
            logger.debug("获取城市列表 | 共 %d 个城市", len(cities))
            return cities
        except sqlite3.Error as e:
            logger.error("获取城市列表失败: %s", str(e))
            return []

    def get_record_count(self) -> int:
        """
        获取数据库中的总记录数。

        Returns:
            int: 记录总数
        """
        self._ensure_connection()

        try:
            self.cursor.execute("SELECT COUNT(*) FROM aqi_records")
            count = self.cursor.fetchone()[0]
            return count
        except sqlite3.Error as e:
            logger.error("获取记录总数失败: %s", str(e))
            return 0

    # ============================================
    # 数据删除操作
    # ============================================

    def clear_all_records(self) -> None:
        """
        清空 aqi_records 表中的所有数据。

        ⚠️ 此操作不可逆，请谨慎使用。
        """
        self._ensure_connection()

        try:
            self.cursor.execute("DELETE FROM aqi_records")
            self.connection.commit()
            logger.warning("已清空所有 AQI 记录")
        except sqlite3.Error as e:
            logger.error("清空记录失败: %s", str(e))
            self.connection.rollback()
            raise

    # ============================================
    # 上下文管理器支持
    # ============================================

    def __enter__(self) -> "DatabaseManager":
        """支持 with 语句进入。"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """支持 with 语句退出时自动关闭连接。"""
        self.close()

    def __repr__(self) -> str:
        status = "已连接" if self.connection else "已断开"
        return f"<DatabaseManager(db_path='{self.db_path}', status='{status}')>"
