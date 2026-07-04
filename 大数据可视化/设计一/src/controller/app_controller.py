# -*- coding: utf-8 -*-
"""
==============================================
主应用控制器模块 (Controller 层)
==============================================

职责：
    - 作为 Model 和 View 之间的桥梁
    - 响应 View 层的用户操作
    - 异步调用 Model 层获取数据，避免 GUI 卡顿
    - 更新 View 层的展示状态
"""

import logging
import threading
import pandas as pd
from datetime import datetime, timedelta
from tkinter import filedialog, messagebox

import customtkinter as ctk

from src.model.database import DatabaseManager
from src.model.predictor import predict_future_aqi
from src.utils.api_fetcher import RealTimeFetcher
from src.view.main_window import MainWindow
from src.utils.plotter import draw_trend_plot
from src.utils.config import get_config
from src.utils.deepseek_service import DeepSeekService

logger = logging.getLogger("AQI_System.Controller.AppController")

class AppController:
    """应用程序主控制器。"""

    def __init__(self, model: DatabaseManager, view: MainWindow):
        self.model = model
        self.view = view
        self.api_fetcher = RealTimeFetcher(model)
        self.deepseek_service = DeepSeekService()

        self._bind_events()
        self._initialize_view()
        
        # 启动后台定时抓取（每 1 小时 = 3600 秒）
        self.api_fetcher.start_auto_fetch(interval_seconds=3600)
        
        logger.info("AppController 初始化完成")

    def _bind_events(self):
        self.view.update_button.configure(command=self.handle_update_request)
        self.view.import_button.configure(command=self.handle_import_request)

    def _initialize_view(self):
        """应用启动时的视图初始化"""
        cities = self.model.get_city_list()
        
        # 读取配置
        default_city = get_config("app", "default_city", "北京")
        default_days = get_config("app", "default_days_range", 365)

        if cities:
            self.view.city_combobox.configure(values=cities)
            if default_city in cities:
                self.view.city_combobox.set(default_city)
            else:
                self.view.city_combobox.set(cities[0])
        else:
            logger.warning("数据库中没有城市数据！")
            return

        end_date = datetime.now()
        start_date = end_date - timedelta(days=default_days)
        
        self.view.start_date_entry.delete(0, "end")
        self.view.start_date_entry.insert(0, start_date.strftime("%Y-%m-%d"))
        
        self.view.end_date_entry.delete(0, "end")
        self.view.end_date_entry.insert(0, end_date.strftime("%Y-%m-%d"))

        # 触发首次加载
        self.handle_update_request()

    def handle_update_request(self):
        """处理更新请求，启动异步线程"""
        city = self.view.get_selected_city()
        start_date, end_date = self.view.get_date_range()

        if not city or not start_date or not end_date:
            return

        # ---- UI 状态：加载中 ----
        self.view.update_button.configure(state="disabled", text="加载中...")
        for widget in self.view.plot_container.winfo_children():
            widget.destroy()
        
        loading_label = ctk.CTkLabel(
            self.view.plot_container, 
            text="⏳ 正在查询数据库并渲染图表，请稍候...", 
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#00a8ff"
        )
        loading_label.place(relx=0.5, rely=0.5, anchor="center")

        # ---- 启动后台线程执行查询 ----
        thread = threading.Thread(
            target=self._fetch_data_async,
            args=(city, start_date, end_date),
            daemon=True
        )
        thread.start()

    def _fetch_data_async(self, city, start_date, end_date):
        """后台线程：执行数据库查询，避免阻塞主循环"""
        logger.info("后台线程开始查询数据: %s, %s~%s", city, start_date, end_date)
        
        try:
            df = self.model.query_by_date_range(start_date, end_date, city)
            
            # 查询完成后，切回主线程更新 UI
            # Tkinter 所有的 UI 修改必须在主线程进行！
            self.view.after(0, self._on_fetch_complete, df, city)
        except Exception as e:
            logger.error("异步查询失败: %s", str(e))
            self.view.after(0, self._on_fetch_error, str(e))

    def _on_fetch_complete(self, df: pd.DataFrame, city: str):
        """主线程：处理查询结果并更新视图"""
        # 恢复按钮状态
        self.view.update_button.configure(state="normal", text="更新分析视图")

        if df.empty:
            self.view.update_indicators("--", "--", "暂无数据")
            for widget in self.view.plot_container.winfo_children():
                widget.destroy()
            ctk.CTkLabel(
                self.view.plot_container, text="[ 该时间段内无数据 ]", text_color="gray50"
            ).place(relx=0.5, rely=0.5, anchor="center")
            return

        # 计算指标
        latest_record = df.iloc[-1]
        latest_pm25 = latest_record['pm25']
        latest_aqi = latest_record['aqi_score']
        level_str = self._get_aqi_level_string(latest_aqi)

        self.view.update_indicators(
            pm25_val=f"{latest_pm25:.1f} μg/m³",
            aqi_val=str(latest_aqi),
            level_str=level_str
        )

        # 进行未来 7 天的数据预测
        future_df = predict_future_aqi(df, days_to_predict=7)

        # 绘制图表 (传入历史数据和预测数据)
        draw_trend_plot(df, self.view.plot_container, future_df=future_df)
        logger.info("视图与图表更新完成。")
        
        # 启动后台线程请求 DeepSeek API 进行数据分析
        self._start_ai_analysis(df)

    def _start_ai_analysis(self, df: pd.DataFrame):
        """格式化数据并启动后台线程请求 AI 分析"""
        self.view.update_ai_report("⏳ 正在结合选定数据请求 DeepSeek API 进行智能分析，请稍候...")
        
        # 提取核心数据进行汇总（限制数据长度以避免超出 Token 限制）
        # 这里提取日期、城市、AQI和几项核心污染物
        cols_to_extract = ['record_date', 'city', 'aqi_score', 'pm25', 'pm10', 'so2', 'no2']
        available_cols = [c for c in cols_to_extract if c in df.columns]
        
        # 为了避免一次发送上万条导致超过 token 限制，这里采取按周/月重采样或截断
        # 但如果是按天，可以取最近的几十天
        df_subset = df[available_cols].tail(60) # 取最近60条
        df_summary_str = df_subset.to_csv(index=False)
        
        thread = threading.Thread(
            target=self._ai_analysis_async,
            args=(df_summary_str,),
            daemon=True
        )
        thread.start()

    def _ai_analysis_async(self, df_summary_str: str):
        """后台线程调用 DeepSeek API"""
        try:
            report_text = self.deepseek_service.analyze_data(df_summary_str)
            self.view.after(0, self.view.update_ai_report, report_text)
        except Exception as e:
            logger.error("AI 分析请求失败: %s", str(e))
            self.view.after(0, self.view.update_ai_report, f"❌ AI 分析失败：{str(e)}")

    def _on_fetch_error(self, error_msg: str):
        """主线程：处理查询错误"""
        self.view.update_button.configure(state="normal", text="更新分析视图")
        self.view.update_indicators("Error", "Error", "Error")
        for widget in self.view.plot_container.winfo_children():
            widget.destroy()
        ctk.CTkLabel(
            self.view.plot_container, text=f"[ 发生错误: {error_msg} ]", text_color="red"
        ).place(relx=0.5, rely=0.5, anchor="center")

    # ============================================
    # 导入数据逻辑
    # ============================================
    def handle_import_request(self):
        """处理导入文件请求"""
        file_path = filedialog.askopenfilename(
            title="选择要导入的数据文件",
            filetypes=(
                ("CSV/Excel 文件", "*.csv;*.xls;*.xlsx"),
                ("CSV 文件", "*.csv"),
                ("Excel 文件", "*.xls;*.xlsx"),
                ("所有文件", "*.*")
            )
        )
        if not file_path:
            return

        logger.info(f"用户选择了导入文件: {file_path}")
        
        # UI 锁定
        self.view.import_button.configure(state="disabled", text="导入中...")
        for widget in self.view.plot_container.winfo_children():
            widget.destroy()
        ctk.CTkLabel(
            self.view.plot_container, 
            text="📥 正在解析并导入数据到数据库，请稍候...", 
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#2ecc71"
        ).place(relx=0.5, rely=0.5, anchor="center")

        # 启动后台线程执行导入
        thread = threading.Thread(
            target=self._import_data_async,
            args=(file_path,),
            daemon=True
        )
        thread.start()

    def _import_data_async(self, file_path: str):
        """后台线程：读取文件并导入数据库"""
        try:
            # 1. 根据扩展名读取文件
            if file_path.lower().endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)

            # 2. 列名容错映射 (支持常见中文表头)
            column_mapping = {
                '城市': 'city', 'City': 'city',
                '日期': 'record_date', 'Date': 'record_date', '时间': 'record_date',
                'PM2.5': 'pm25', 'pm2.5': 'pm25',
                'PM10': 'pm10', 'pm10': 'pm10',
                'SO2': 'so2', '二氧化硫': 'so2',
                'NO2': 'no2', '二氧化氮': 'no2',
                'AQI': 'aqi_score', 'aqi': 'aqi_score', 'AQI指数': 'aqi_score'
            }
            df = df.rename(columns=column_mapping)
            
            # 检查缺失字段并补齐默认值
            required_cols = {"city", "record_date", "pm25", "pm10", "so2", "no2", "aqi_score"}
            missing = required_cols - set(df.columns)
            if "city" in missing or "record_date" in missing:
                raise ValueError("数据缺少关键列 'city' (城市) 或 'record_date' (日期)")
            
            # 对于缺失的污染物列填0
            for col in missing:
                df[col] = 0

            # 3. 数据清洗 (日期格式化)
            df['record_date'] = pd.to_datetime(df['record_date']).dt.strftime('%Y-%m-%d')
            df.fillna(0, inplace=True) # 处理 NaN

            # 4. 插入数据库
            inserted_count = self.model.insert_dataframe(df)
            
            # 切回主线程更新 UI
            self.view.after(0, self._on_import_complete, True, f"成功导入 {inserted_count} 条数据！")
            
        except Exception as e:
            logger.error(f"导入失败: {str(e)}")
            self.view.after(0, self._on_import_complete, False, str(e))

    def _on_import_complete(self, success: bool, message: str):
        """主线程：导入完成后的 UI 恢复"""
        self.view.import_button.configure(state="normal", text="📁 导入 CSV / Excel")
        
        for widget in self.view.plot_container.winfo_children():
            widget.destroy()
            
        if success:
            messagebox.showinfo("导入成功", message)
            # 刷新城市下拉框列表
            cities = self.model.get_city_list()
            if cities:
                self.view.city_combobox.configure(values=cities)
            # 自动触发一次更新视图，以便显示新数据
            self.handle_update_request()
        else:
            messagebox.showerror("导入失败", f"数据导入出错：\n{message}")
            ctk.CTkLabel(
                self.view.plot_container, text="[ 导入失败，请检查文件格式 ]", text_color="red"
            ).place(relx=0.5, rely=0.5, anchor="center")


    def _get_aqi_level_string(self, aqi: int) -> str:
        if aqi <= 50: return "优 (绿)"
        elif aqi <= 100: return "良 (黄)"
        elif aqi <= 150: return "轻度污染 (橙)"
        elif aqi <= 200: return "中度污染 (红)"
        elif aqi <= 300: return "重度污染 (紫)"
        else: return "严重污染 (褐)"
