# -*- coding: utf-8 -*-
"""
==============================================
主窗口视图模块 (View 层)
==============================================

职责：
    - 定义主程序的 GUI 布局（基于 CustomTkinter）
    - 提供界面组件（Widget）的初始化与静态展示
    - 预留交互回调接口，供 Controller 层绑定
    - 不包含任何数据库或业务逻辑处理

布局结构：
    - 左侧 Sidebar：城市选择、日期范围、更新按钮
    - 右侧 Main Frame：顶部指标展示、下方图表容器
"""

import customtkinter as ctk
import logging
from datetime import datetime, timedelta
import tkinter as tk
from tkcalendar import Calendar

logger = logging.getLogger("AQI_System.View.MainWindow")

class MainWindow(ctk.CTk):
    """
    系统主窗口类。
    继承自 customtkinter.CTk，负责整体界面布局与静态展示。
    """

    def __init__(self):
        super().__init__()

        # ============================================
        # 1. 窗口基础配置
        # ============================================
        self.title("城市空气质量(AQI)实时监测与预测分析系统")
        self.geometry("1100x650")
        self.minsize(900, 500)
        
        # 强制深色模式，符合数据大屏风格
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # 配置网格布局 (1行2列)
        # 第0列为 Sidebar，固定宽度，不随窗口拉伸扩展 (weight=0)
        # 第1列为 Main Frame，占据剩余空间 (weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)

        # ============================================
        # 2. 初始化各区域布局
        # ============================================
        self._init_sidebar()
        self._init_main_frame()
        
        logger.info("MainWindow 界面静态布局初始化完成")

    def _init_sidebar(self):
        """
        初始化左侧侧边栏 (Sidebar)。
        包含标题、城市选择、日期范围、更新按钮等控件。
        """
        self.sidebar_frame = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_propagate(False) # 固定宽度，不随子组件大小改变
        
        # Sidebar 内部采用相对布局或通过 pack/grid 细分布局
        
        # ---- 标题区 ----
        self.title_label = ctk.CTkLabel(
            self.sidebar_frame, 
            text="AQI 监测分析", 
            font=ctk.CTkFont(size=22, weight="bold")
        )
        self.title_label.pack(pady=(30, 20), padx=20)
        
        # 分隔线 (简单用一个很细的 Frame 代替)
        self.separator1 = ctk.CTkFrame(self.sidebar_frame, height=2, fg_color="gray30")
        self.separator1.pack(fill="x", padx=20, pady=10)

        # ---- 城市选择区 ----
        self.city_label = ctk.CTkLabel(self.sidebar_frame, text="选择城市：", font=ctk.CTkFont(size=14))
        self.city_label.pack(anchor="w", padx=20, pady=(10, 5))
        
        # 默认填入几个示例城市，后续 Controller 会动态更新这个列表
        self.city_combobox = ctk.CTkComboBox(
            self.sidebar_frame, 
            values=["北京", "上海", "广州", "深圳", "成都"]
        )
        self.city_combobox.pack(fill="x", padx=20, pady=5)
        self.city_combobox.set("北京") # 默认选中第一个

        # ---- 日期范围选择区 ----
        self.date_label = ctk.CTkLabel(self.sidebar_frame, text="分析日期范围：", font=ctk.CTkFont(size=14))
        self.date_label.pack(anchor="w", padx=20, pady=(20, 5))
        
        # 使用 Frame 包装 Entry 和日历按钮
        start_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        start_frame.pack(fill="x", padx=20, pady=5)
        self.start_date_entry = ctk.CTkEntry(start_frame, placeholder_text="开始日期 (YYYY-MM-DD)")
        self.start_date_entry.pack(side="left", fill="x", expand=True)
        btn_start_cal = ctk.CTkButton(start_frame, text="📅", width=30, command=lambda: self._open_calendar(self.start_date_entry))
        btn_start_cal.pack(side="right", padx=(5, 0))
        
        end_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        end_frame.pack(fill="x", padx=20, pady=5)
        self.end_date_entry = ctk.CTkEntry(end_frame, placeholder_text="结束日期 (YYYY-MM-DD)")
        self.end_date_entry.pack(side="left", fill="x", expand=True)
        btn_end_cal = ctk.CTkButton(end_frame, text="📅", width=30, command=lambda: self._open_calendar(self.end_date_entry))
        btn_end_cal.pack(side="right", padx=(5, 0))

        # ---- 快捷日期按钮区 ----
        self.quick_date_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.quick_date_frame.pack(fill="x", padx=20, pady=5)
        self.quick_date_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.btn_week = ctk.CTkButton(self.quick_date_frame, text="近一周", height=24, command=lambda: self._set_quick_date(7))
        self.btn_week.grid(row=0, column=0, padx=2)
        self.btn_month = ctk.CTkButton(self.quick_date_frame, text="近一月", height=24, command=lambda: self._set_quick_date(30))
        self.btn_month.grid(row=0, column=1, padx=2)
        self.btn_year = ctk.CTkButton(self.quick_date_frame, text="近一年", height=24, command=lambda: self._set_quick_date(365))
        self.btn_year.grid(row=0, column=2, padx=2)

        # ---- 按钮操作区 ----
        self.update_button = ctk.CTkButton(
            self.sidebar_frame, 
            text="更新分析视图",
            command=self._on_update_clicked,
            font=ctk.CTkFont(weight="bold")
        )
        self.update_button.pack(side="bottom", fill="x", padx=20, pady=(10, 30))

        self.import_button = ctk.CTkButton(
            self.sidebar_frame, 
            text="📁 导入 CSV / Excel",
            command=self._on_import_clicked,
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "#DCE4EE")
        )
        self.import_button.pack(side="bottom", fill="x", padx=20, pady=(10, 0))


    def _init_main_frame(self):
        """
        初始化右侧主展示区 (Main Frame)。
        包含顶部核心指标展示区和下方的图表容器。
        """
        self.main_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        
        # Main Frame 内部划分为上下三行
        # Row 0: 顶部指标卡片 (高度自适应)
        # Row 1: 图表容器 (占据剩余空间)
        # Row 2: AI分析报告
        self.main_frame.grid_rowconfigure(0, weight=0)
        self.main_frame.grid_rowconfigure(1, weight=3) # 图表权重给大一点
        self.main_frame.grid_rowconfigure(2, weight=1) # 文本框权重
        self.main_frame.grid_columnconfigure(0, weight=1)

        # ============================================
        # 顶部：核心指标展示区 (Cards)
        # ============================================
        self.cards_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.cards_frame.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        
        # 3个卡片等宽分布
        self.cards_frame.grid_columnconfigure(0, weight=1)
        self.cards_frame.grid_columnconfigure(1, weight=1)
        self.cards_frame.grid_columnconfigure(2, weight=1)

        # 卡片 1：最新 PM2.5
        self.pm25_card = self._create_indicator_card(self.cards_frame, "最新 PM2.5", "-- μg/m³", 0)
        
        # 卡片 2：最新 AQI
        self.aqi_card = self._create_indicator_card(self.cards_frame, "最新 AQI 指数", "--", 1)
        
        # 卡片 3：空气质量等级
        self.level_card = self._create_indicator_card(self.cards_frame, "空气质量等级", "--", 2)

        # ============================================
        # 下方：图表容器区 (Plot Container)
        # ============================================
        # 这个 Frame 会作为 Matplotlib FigureCanvasTkAgg 的父容器
        self.plot_container = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.plot_container.grid(row=1, column=0, sticky="nsew")
        
        # 添加一个占位提示文本
        self.plot_placeholder_label = ctk.CTkLabel(
            self.plot_container,
            text="[ 图表展示区域 - 等待数据加载 ]",
            text_color="gray50",
            font=ctk.CTkFont(size=18, slant="italic")
        )
        self.plot_placeholder_label.place(relx=0.5, rely=0.5, anchor="center")

        # ============================================
        # 底部：AI 智能分析报告区域 (Text Box)
        # ============================================
        self.ai_report_container = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.ai_report_container.grid(row=2, column=0, sticky="nsew", pady=(10, 0))
        
        self.ai_report_label = ctk.CTkLabel(
            self.ai_report_container, 
            text="AI 智能分析报告 (DeepSeek 驱动):", 
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.ai_report_label.pack(anchor="w", padx=10, pady=(10, 5))

        self.ai_report_textbox = ctk.CTkTextbox(
            self.ai_report_container, 
            wrap="word", 
            state="disabled",
            font=ctk.CTkFont(size=12)
        )
        self.ai_report_textbox.pack(fill="both", expand=True, padx=10, pady=(0, 10))


    def _create_indicator_card(self, parent, title, initial_value, col_index):
        """
        辅助方法：创建一个指标卡片。
        
        Args:
            parent: 父容器
            title: 指标标题
            initial_value: 初始显示数值
            col_index: 在父容器中的列索引
            
        Returns:
            CTkLabel: 用于更新数值的 Label 引用
        """
        card = ctk.CTkFrame(parent, corner_radius=8)
        card.grid(row=0, column=col_index, sticky="ew", padx=10)
        
        title_label = ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=14), text_color="gray70")
        title_label.pack(pady=(15, 5))
        
        value_label = ctk.CTkLabel(card, text=initial_value, font=ctk.CTkFont(size=28, weight="bold"))
        value_label.pack(pady=(0, 15))
        
        return value_label


    # ============================================
    # 交互回调占位符 (待 Controller 绑定)
    # ============================================
    
    def _set_quick_date(self, days):
        """快捷设置日期范围"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        self.start_date_entry.delete(0, "end")
        self.start_date_entry.insert(0, start_date.strftime("%Y-%m-%d"))
        
        self.end_date_entry.delete(0, "end")
        self.end_date_entry.insert(0, end_date.strftime("%Y-%m-%d"))

    def _open_calendar(self, target_entry):
        """打开日历选择器弹窗"""
        top = ctk.CTkToplevel(self)
        top.title("选择日期")
        top.geometry("300x250")
        top.attributes("-topmost", True)
        top.grab_set() # 模态对话框
        
        cal = Calendar(top, selectmode='day', date_pattern='y-mm-dd',
                       background='black', foreground='white', bordercolor='gray',
                       headersbackground='black', headersforeground='white',
                       selectbackground='#00a8ff', selectforeground='white')
        cal.pack(fill="both", expand=True, padx=10, pady=10)
        
        def set_date():
            target_entry.delete(0, "end")
            target_entry.insert(0, cal.get_date())
            top.destroy()
            
        btn = ctk.CTkButton(top, text="确定", command=set_date)
        btn.pack(pady=(0, 10))

    def _on_update_clicked(self):
        """
        点击“更新分析视图”按钮时的内部回调。
        视图层不处理具体逻辑，而是将事件抛出。
        """
        logger.debug("View: 点击了更新视图按钮")
        # 这里预留给 Controller 设置回调函数的入口
        pass

    def _on_import_clicked(self):
        """
        点击“导入数据”按钮时的内部回调。
        """
        logger.debug("View: 点击了导入数据按钮")
        pass

    def get_selected_city(self):
        """获取当前选择的城市。"""
        return self.city_combobox.get()

    def get_date_range(self):
        """获取当前填写的日期范围。"""
        return self.start_date_entry.get(), self.end_date_entry.get()
        
    def update_indicators(self, pm25_val, aqi_val, level_str):
        """
        更新顶部核心指标。
        供 Controller 调用。
        """
        self.pm25_card.configure(text=str(pm25_val))
        self.aqi_card.configure(text=str(aqi_val))
        self.level_card.configure(text=level_str)

    def update_ai_report(self, text: str):
        """
        更新 AI 智能分析报告的显示内容。
        供 Controller 调用。
        """
        self.ai_report_textbox.configure(state="normal")
        self.ai_report_textbox.delete("1.0", "end")
        self.ai_report_textbox.insert("1.0", text)
        self.ai_report_textbox.configure(state="disabled")

if __name__ == "__main__":
    # 简单的独立测试代码，确保布局能够正常显示
    app = MainWindow()
    app.mainloop()
