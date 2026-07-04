# -*- coding: utf-8 -*-
"""
==============================================
数据预测分析模块 (Model 层)
==============================================

职责：
    - 基于历史时间序列数据，预测未来几天的污染物浓度
    - 这里提供了一个轻量级的指数平滑 (Exponential Smoothing) 预测算法
"""

import logging
import pandas as pd
import numpy as np

logger = logging.getLogger("AQI_System.Model.Predictor")

def predict_future_aqi(df: pd.DataFrame, days_to_predict: int = 5) -> pd.DataFrame:
    """
    基于历史数据，预测未来几天的各项污染物浓度。
    采用简单的加权移动平均（近似指数平滑）算法。

    Args:
        df: 包含历史数据的 DataFrame（需按日期升序排列）
        days_to_predict: 需要预测的未来天数

    Returns:
        pd.DataFrame: 包含预测日期的虚拟 DataFrame
    """
    if df is None or len(df) < 3:
        logger.warning("历史数据太少，无法进行预测")
        return pd.DataFrame()

    df = df.copy()
    df['record_date'] = pd.to_datetime(df['record_date'])
    df = df.sort_values('record_date')

    # 获取最后一天日期
    last_date = df['record_date'].iloc[-1]
    city = df['city'].iloc[0]

    # 需要预测的字段
    target_cols = ['pm25', 'pm10', 'so2', 'no2']
    
    # 提取最近 N 天的数据用于平滑
    recent_data = df.tail(15) 
    
    predictions = []
    
    # 遍历未来的每一天
    for i in range(1, days_to_predict + 1):
        pred_date = last_date + pd.Timedelta(days=i)
        pred_row = {
            'city': city,
            'record_date': pred_date
        }
        
        # 简单模拟：基于历史均值 + 随时间衰减的近期波动 + 随机扰动
        for col in target_cols:
            hist_mean = df[col].mean()
            recent_mean = recent_data[col].mean()
            
            # 趋势：最近的数据权重较大，随着预测天数增加，逐渐向历史均值回归
            weight_recent = max(0.1, 0.8 - (i * 0.1))
            weight_hist = 1.0 - weight_recent
            
            base_pred = (recent_mean * weight_recent) + (hist_mean * weight_hist)
            
            # 加入一点随机波动 (基于历史标准差的10%)
            std_dev = df[col].std()
            noise = np.random.normal(0, std_dev * 0.1)
            
            final_pred = max(1.0, base_pred + noise) # 保证不为负数
            pred_row[col] = round(final_pred, 1)
            
        # 简单推算 AQI (这里不做复杂的分段插值，直接用最大项粗略估算)
        # 仅为演示预测效果
        pred_row['aqi_score'] = int(max(pred_row['pm25'], pred_row['pm10']/2.0))
        
        predictions.append(pred_row)

    pred_df = pd.DataFrame(predictions)
    logger.info(f"成功生成 {days_to_predict} 天的预测数据")
    return pred_df
