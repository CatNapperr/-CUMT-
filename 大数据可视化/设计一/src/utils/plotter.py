# -*- coding: utf-8 -*-
"""
==============================================
图表绘制工具模块
==============================================

职责：
    - 封装 Matplotlib 的绘图逻辑
    - 将图表渲染到指定的 Tkinter/CustomTkinter 容器中
    - 处理中文字体显示、深色模式适配等细节
"""

import logging
import pandas as pd
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates

# 强制使用 TkAgg 后端
matplotlib.use("TkAgg")

logger = logging.getLogger("AQI_System.Utils.Plotter")

def _setup_matplotlib_style():
    """
    配置 Matplotlib 全局样式。
    包括适配深色主题和中文字体显示。
    """
    # 尝试设置支持中文的字体（根据系统差异可能需要调整）
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
    plt.rcParams['axes.unicode_minus'] = False  # 正常显示负号

    # 深色模式风格适配
    plt.style.use('dark_background')
    
    # 微调颜色使其更柔和，匹配 CustomTkinter 深色主题
    plt.rcParams['figure.facecolor'] = '#2b2b2b'  # 图表整体背景
    plt.rcParams['axes.facecolor'] = '#2b2b2b'    # 坐标系背景
    plt.rcParams['axes.edgecolor'] = '#555555'
    plt.rcParams['text.color'] = '#dddddd'
    plt.rcParams['axes.labelcolor'] = '#dddddd'
    plt.rcParams['xtick.color'] = '#aaaaaa'
    plt.rcParams['ytick.color'] = '#aaaaaa'
    plt.rcParams['grid.color'] = '#444444'
    plt.rcParams['grid.alpha'] = 0.5


def draw_trend_plot(df: pd.DataFrame, container, future_df: pd.DataFrame = None) -> None:
    """
    在指定的容器中绘制多维可视化大屏图表 (Dashboard)。
    左侧：PM2.5 & PM10 趋势折线图 (如有预测数据则叠加虚线)
    右侧上：各污染物平均浓度占比环形图
    右侧下：污染物浓度分布箱线图

    Args:
        df: 包含历史数据的 DataFrame
        container: Tkinter/CustomTkinter 容器
        future_df: 预测数据的 DataFrame (可选)
    """
    if df is None or df.empty:
        logger.warning("传入的数据为空，无法绘制图表")
        return

    df = df.copy()
    df['record_date'] = pd.to_datetime(df['record_date'])
    df = df.sort_values('record_date')
    city_name = df['city'].iloc[0] if 'city' in df.columns else "未知城市"

    for widget in container.winfo_children():
        widget.destroy()

    _setup_matplotlib_style()

    # 创建 1 行 2 列的网格布局，右侧列再细分为上下两行
    fig = plt.figure(figsize=(12, 6), dpi=100)
    gs = fig.add_gridspec(2, 2, width_ratios=[2, 1])
    
    ax_trend = fig.add_subplot(gs[:, 0])      # 左侧占据两行：趋势图
    ax_pie = fig.add_subplot(gs[0, 1])        # 右上：饼图/环形图
    ax_box = fig.add_subplot(gs[1, 1])        # 右下：箱线图

    fig.subplots_adjust(left=0.05, right=0.95, top=0.9, bottom=0.1, wspace=0.2, hspace=0.3)

    # ---------------------------------------------------------
    # 1. 绘制左侧：趋势折线图
    # ---------------------------------------------------------
    x_data = df['record_date']
    
    # 历史数据
    ax_trend.plot(x_data, df['pm25'], color="#00a8ff", linewidth=2, label="PM2.5", alpha=0.8)
    ax_trend.plot(x_data, df['pm10'], color="#fbc531", linewidth=2, label="PM10", alpha=0.8)
    
    # 如果有预测数据，画出预测折线（虚线）
    if future_df is not None and not future_df.empty:
        future_df = future_df.copy()
        future_df['record_date'] = pd.to_datetime(future_df['record_date'])
        future_df = future_df.sort_values('record_date')
        
        # 为了连贯，将历史最后一天加入预测线开头
        last_hist = df.iloc[-1:]
        pred_line_pm25 = pd.concat([last_hist[['record_date', 'pm25']], future_df[['record_date', 'pm25']]])
        pred_line_pm10 = pd.concat([last_hist[['record_date', 'pm10']], future_df[['record_date', 'pm10']]])
        
        ax_trend.plot(pred_line_pm25['record_date'], pred_line_pm25['pm25'], 
                      color="#00a8ff", linewidth=2, linestyle='--', label="PM2.5(预测)")
        ax_trend.plot(pred_line_pm10['record_date'], pred_line_pm10['pm10'], 
                      color="#fbc531", linewidth=2, linestyle='--', label="PM10(预测)")
        
        # 标记预测起始线
        ax_trend.axvline(x=last_hist['record_date'].iloc[0], color='red', linestyle=':', alpha=0.5)
        ax_trend.text(last_hist['record_date'].iloc[0], ax_trend.get_ylim()[1]*0.9, ' 预测开始', color='red')

    ax_trend.set_title(f"[{city_name}] 颗粒物浓度趋势", fontsize=12)
    ax_trend.grid(True, linestyle='--', alpha=0.3)
    ax_trend.legend(loc="upper right")
    ax_trend.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax_trend.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.setp(ax_trend.get_xticklabels(), rotation=20, ha='right', fontsize=9)

    # ---------------------------------------------------------
    # 2. 绘制右上：平均浓度占比环形图
    # ---------------------------------------------------------
    pollutants = ['PM2.5', 'PM10', 'SO2', 'NO2']
    means = [df['pm25'].mean(), df['pm10'].mean(), df['so2'].mean(), df['no2'].mean()]
    colors = ['#00a8ff', '#fbc531', '#e84118', '#4cd137']
    
    wedges, texts, autotexts = ax_pie.pie(
        means, labels=pollutants, colors=colors, autopct='%1.1f%%',
        startangle=90, pctdistance=0.85, textprops={'fontsize': 9}
    )
    # 画中心白圆变成环形图
    centre_circle = plt.Circle((0,0), 0.70, fc='#2b2b2b')
    ax_pie.add_artist(centre_circle)
    ax_pie.set_title("期间平均浓度占比", fontsize=11, pad=10)

    # ---------------------------------------------------------
    # 3. 绘制右下：浓度分布箱线图 (评估波动性)
    # ---------------------------------------------------------
    data_to_plot = [df['pm25'], df['pm10'], df['so2'], df['no2']]
    
    box = ax_box.boxplot(data_to_plot, patch_artist=True, labels=pollutants)
    for patch, color in zip(box['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)
    for median in box['medians']:
        median.set_color('white')
        median.set_linewidth(2)
        
    ax_box.set_title("污染物浓度分布区间", fontsize=11)
    ax_box.grid(True, axis='y', linestyle='--', alpha=0.3)
    ax_box.tick_params(axis='x', labelsize=9)

    # =========================================================
    # 渲染到 Tkinter
    canvas = FigureCanvasTkAgg(fig, master=container)
    canvas.draw()
    canvas_widget = canvas.get_tk_widget()
    canvas_widget.pack(fill="both", expand=True)

    plt.close(fig)
    logger.debug("多维大屏图表渲染完毕")
