import pandas as pd
import numpy as np
import time
import matplotlib.pyplot as plt
from math import pi
import seaborn as sns

from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import LabelEncoder
from sklearn.naive_bayes import MultinomialNB
from sklearn.tree import DecisionTreeClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import (accuracy_score, precision_score, recall_score, 
                             f1_score, roc_curve, auc, precision_recall_curve, average_precision_score)

# 设置matplotlib支持中文显示（如果系统不支持SimHei，可以尝试去除或更换字体）
plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号

# ============================
# 1. 数据加载与预处理
# ============================
def load_and_preprocess_data(path):
    print(f"正在读取数据集: {path} ...")
    try:
        # SMSSpamCollection 通常没有表头，第一列是标签，第二列是短信内容，用制表符分隔
        df = pd.read_csv(path, sep='\t', header=None, names=['label', 'message'])
    except FileNotFoundError:
        print(f"错误: 找不到文件 {path}。请确保文件路径正确。")
        exit()

    # 标签编码: ham -> 0, spam -> 1
    le = LabelEncoder()
    y = le.fit_transform(df['label'])
    
    # 文本特征提取 (TF-IDF)
    print("正在进行 TF-IDF 向量化 ...")
    tfidf = TfidfVectorizer(stop_words='english', max_features=3000) # 限制特征数以加快KNN速度
    X = tfidf.fit_transform(df['message']).toarray() # KNN通常需要稠密矩阵或特定稀疏处理，这里转array方便处理
    
    # 划分训练集和测试集
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)
    
    return X_train, X_test, y_train, y_test

# ============================
# 2. 模型定义与评测流程
# ============================
def evaluate_models(X_train, X_test, y_train, y_test):
    # 定义要评测的模型
    models = {
        'Naive Bayes': MultinomialNB(),
        'Decision Tree': DecisionTreeClassifier(random_state=42),
        'KNN': KNeighborsClassifier(n_neighbors=5) 
    }
    
    results = {}
    
    print("\n开始训练与评测模型...")
    print("-" * 80)
    print(f"{'Model':<15} {'Acc':<10} {'Prec':<10} {'Recall':<10} {'F1':<10} {'Train Time(s)':<15} {'Pred Time(s)':<15}")
    print("-" * 80)

    for name, model in models.items():
        # 1. 训练并计时
        start_train = time.time()
        model.fit(X_train, y_train)
        end_train = time.time()
        train_time = end_train - start_train
        
        # 2. 预测并计时
        start_pred = time.time()
        y_pred = model.predict(X_test)
        end_pred = time.time()
        pred_time = end_pred - start_pred
        
        # 获取概率用于绘制 ROC 和 PR 曲线
        if hasattr(model, "predict_proba"):
            y_prob = model.predict_proba(X_test)[:, 1]
        else:
            # 对于没有 predict_proba 的模型（很少见），使用 decision_function 或 0/1
            y_prob = y_pred

        # 3. 计算指标
        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred)
        rec = recall_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred)
        
        # 打印结果
        print(f"{name:<15} {acc:.4f}     {prec:.4f}     {rec:.4f}     {f1:.4f}     {train_time:.4f}          {pred_time:.4f}")
        
        # 存储结果用于可视化
        results[name] = {
            'metrics': [acc, prec, rec, f1], # 用于雷达图
            'y_prob': y_prob,                # 用于 ROC/PR
            'y_test': y_test,
            'train_time': train_time,
            'pred_time': pred_time
        }
        
    return results

# ============================
# 3. 可视化函数
# ============================

def plot_radar_chart(results):
    """绘制雷达图：多指标综合比较"""
    categories = ['Accuracy', 'Precision', 'Recall', 'F1-Score']
    N = len(categories)
    
    # 计算角度
    angles = [n / float(N) * 2 * pi for n in range(N)]
    angles += angles[:1] # 闭合回路
    
    plt.figure(figsize=(8, 8))
    ax = plt.subplot(111, polar=True)
    
    # 设置刻度
    plt.xticks(angles[:-1], categories, color='grey', size=12)
    ax.set_rlabel_position(0)
    plt.yticks([0.2, 0.4, 0.6, 0.8, 1.0], ["0.2", "0.4", "0.6", "0.8", "1.0"], color="grey", size=7)
    plt.ylim(0, 1)
    
    colors = ['b', 'r', 'g']
    
    for i, (name, data) in enumerate(results.items()):
        values = data['metrics']
        values += values[:1] # 闭合
        
        ax.plot(angles, values, linewidth=1, linestyle='solid', label=name, color=colors[i])
        ax.fill(angles, values, color=colors[i], alpha=0.1)
        
    plt.title('各模型性能指标雷达图', size=16, y=1.1)
    plt.legend(loc='upper right', bbox_to_anchor=(0.1, 0.1))

def plot_roc_auc(results):
    """绘制多模型 ROC-AUC 曲线"""
    plt.figure(figsize=(8, 6))
    
    for name, data in results.items():
        y_test = data['y_test']
        y_prob = data['y_prob']
        
        fpr, tpr, _ = roc_curve(y_test, y_prob)
        roc_auc = auc(fpr, tpr)
        
        plt.plot(fpr, tpr, lw=2, label=f'{name} (AUC = {roc_auc:.3f})')
    
    plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel('False Positive Rate (FPR)')
    plt.ylabel('True Positive Rate (TPR)')
    plt.title('多模型 ROC 曲线对比')
    plt.legend(loc="lower right")
    plt.grid(alpha=0.3)

def plot_pr_auc(results):
    """绘制多模型 PR-AUC 曲线 (Precision-Recall)"""
    plt.figure(figsize=(8, 6))
    
    for name, data in results.items():
        y_test = data['y_test']
        y_prob = data['y_prob']
        
        precision, recall, _ = precision_recall_curve(y_test, y_prob)
        avg_prec = average_precision_score(y_test, y_prob)
        
        plt.plot(recall, precision, lw=2, label=f'{name} (AP = {avg_prec:.3f})')
    
    plt.xlabel('Recall')
    plt.ylabel('Precision')
    plt.title('多模型 Precision-Recall 曲线对比')
    plt.legend(loc="lower left")
    plt.grid(alpha=0.3)

# ============================
# 主程序
# ============================
if __name__ == "__main__":
    # 数据集路径
    DATA_PATH = "./dataset/SMSSpamCollection"
    
    # 1. 准备数据
    X_train, X_test, y_train, y_test = load_and_preprocess_data(DATA_PATH)
    
    # 2. 评测模型
    results = evaluate_models(X_train, X_test, y_train, y_test)
    
    # 3. 可视化分析
    print("\n正在生成可视化图表...")
    
    plot_radar_chart(results)
    plot_roc_auc(results)
    plot_pr_auc(results)
    
    # 也可以绘制时间对比图（额外赠送）
    plt.figure(figsize=(8, 5))
    times_train = [results[m]['train_time'] for m in results]
    times_pred = [results[m]['pred_time'] for m in results]
    models_names = list(results.keys())
    
    x = np.arange(len(models_names))
    width = 0.35
    
    plt.bar(x - width/2, times_train, width, label='Training Time')
    plt.bar(x + width/2, times_pred, width, label='Prediction Time')
    plt.xticks(x, models_names)
    plt.ylabel('Time (seconds)')
    plt.title('模型时间开销对比')
    plt.legend()
    
    print("可视化完成，请查看弹出的窗口。")
    plt.show()