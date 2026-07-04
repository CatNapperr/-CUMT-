"""
聚类算法综合对比分析
使用鸢尾花数据集比较5种不同的聚类算法性能
包括：K-Means、Agglomerative、DBSCAN、GMM、Spectral Clustering
"""

import numpy as np
import matplotlib.pyplot as plt
from sklearn.datasets import load_iris
from sklearn.cluster import KMeans, AgglomerativeClustering, DBSCAN, SpectralClustering
from sklearn.mixture import GaussianMixture
from sklearn.decomposition import PCA
from sklearn.metrics import (
    adjusted_mutual_info_score,           # 调整互信息
    homogeneity_score,                    # 同质性评分
    completeness_score,                   # 完整性评分
    v_measure_score,                      # V-measure评分（同质性和完整性的调和平均）
    adjusted_rand_score,                  # 调整兰德指数
    normalized_mutual_info_score,         # 规范化互信息
    silhouette_score                      # 轮廓系数
)

# ============================================================
# 数据加载
# ============================================================
# 加载鸢尾花数据集（包含150个样本，4个特征）
data = load_iris()
X = data.data                             # 特征矩阵，形状为(150, 4)
y_true = data.target                      # 真实标签，形状为(150,)，包含3类（0,1,2）

# ============================================================
# 评测函数 - 使用多种指标评估聚类结果
# ============================================================
def evaluate(name, y_true, y_pred, X):
    """
    评估聚类算法的性能
    
    参数：
    -------
    name : str
        聚类算法的名称
    y_true : array-like
        真实的类标签
    y_pred : array-like
        算法预测的聚类标签
    X : array-like
        原始特征矩阵，用于计算轮廓系数
    """
    print(f"\n=== {name} 聚类评测结果 ===")
    
    # AMI（调整互信息）：衡量真实标签和预测标签的一致性
    # 取值范围[-1, 1]，值越大越好，0表示随机聚类
    print("AMI（调整互信息）:", adjusted_mutual_info_score(y_true, y_pred))
    
    # Homogeneity（同质性）：衡量同一聚类中的样本是否都来自同一真实类
    # 取值范围[0, 1]，值越大越好
    print("Homogeneity（同质性）:", homogeneity_score(y_true, y_pred))
    
    # Completeness（完整性）：衡量同一真实类的样本是否都被分配到同一聚类
    # 取值范围[0, 1]，值越大越好
    print("Completeness（完整性）:", completeness_score(y_true, y_pred))
    
    # V-measure：同质性和完整性的加权调和平均
    # 取值范围[0, 1]，综合评估聚类效果
    print("V-measure:", v_measure_score(y_true, y_pred))
    
    # Adjusted Rand Index（ARI）：衡量两个聚类结果的相似度
    # 取值范围[-1, 1]，值越大越好，0表示随机聚类
    print("Adjusted Rand Index (ARI):", adjusted_rand_score(y_true, y_pred))
    
    # Normalized Mutual Information（NMI）：规范化互信息
    # 取值范围[0, 1]，值越大越好
    print("Normalized Mutual Information (NMI):", normalized_mutual_info_score(y_true, y_pred))

    # Silhouette Score（轮廓系数）：衡量样本与其所属聚类的匹配程度
    # 取值范围[-1, 1]，值越接近1越好
    # 前提：至少有2个聚类且不存在噪声点（标签为-1）
    unique_labels = set(y_pred)
    if len(unique_labels) > 1 and -1 not in unique_labels:
        print("Silhouette Score:", silhouette_score(X, y_pred))
    else:
        print("Silhouette Score: 无法计算（簇数不足或存在噪声点）")


# ============================================================
# 可视化函数 - 使用PCA降维将聚类结果显示在2D平面上
# ============================================================
def visualize(name, X, labels):
    """
    使用PCA降维将高维聚类结果可视化为2D散点图
    
    参数：
    -------
    name : str
        聚类算法的名称
    X : array-like
        原始特征矩阵
    labels : array-like
        聚类标签
    """
    # 使用PCA降维到2个主成分，保留最多的数据信息
    pca = PCA(n_components=2)
    X_pca = pca.fit_transform(X)

    # 创建图表
    plt.figure(figsize=(6, 5))
    
    # 绘制散点图，使用聚类标签为点着色
    plt.scatter(X_pca[:, 0], X_pca[:, 1], c=labels, cmap="viridis", s=45)
    
    plt.title(f"{name} 聚类结果（PCA 2D）")
    plt.xlabel("PC1（第一主成分）")
    plt.ylabel("PC2（第二主成分）")
    plt.show()


# ============================================================
# 1. K-Means 聚类（基于划分的算法）
# ============================================================
# K-Means 原理：
# - 将数据划分为K个不相交的聚类
# - 每个聚类由一个质心代表
# - 通过最小化样本到质心的距离平方和进行优化

kmeans = KMeans(
    n_clusters=3,      # 设置聚类数为3（与鸢尾花的3个品种相匹配）
    random_state=42    # 设置随机种子，确保结果可复现
)

# 拟合数据并预测聚类标签
kmeans_labels = kmeans.fit_predict(X)

# 评估聚类效果
evaluate("K-Means", y_true, kmeans_labels, X)

# 可视化聚类结果
visualize("K-Means", X, kmeans_labels)


# ============================================================
# 2. 层次聚类 - Agglomerative（基于层次的算法）
# ============================================================
# Agglomerative 聚类 原理：
# - 自下而上的聚合方式
# - 开始时每个样本为一个聚类，逐步合并最近的聚类
# - 直到获得指定数量的聚类为止

hier = AgglomerativeClustering(
    n_clusters=3        # 设置最终的聚类数为3
)

# 拟合数据并预测聚类标签
hier_labels = hier.fit_predict(X)

# 评估聚类效果
evaluate("Agglomerative Clustering", y_true, hier_labels, X)

# 可视化聚类结果
visualize("Agglomerative Clustering", X, hier_labels)


# ============================================================
# 3. DBSCAN 聚类（基于密度的算法）
# ============================================================
# DBSCAN（Density-Based Spatial Clustering of Applications with Noise）原理：
# - 基于点的密度进行聚类
# - 核心点：eps邻域内样本数 >= min_samples
# - 边界点：在核心点的eps邻域内，但自己不是核心点
# - 噪声点：既不是核心点也不是边界点（标签为-1）
# 优点：可以发现任意形状的聚类，无需提前指定聚类数

dbscan = DBSCAN(
    eps=0.6,           # 邻域半径：两点间距离小于此值时认为相邻
    min_samples=4      # 核心点的最小邻域样本数
)

# 拟合数据并预测聚类标签
db_labels = dbscan.fit_predict(X)

# 评估聚类效果
evaluate("DBSCAN", y_true, db_labels, X)

# 可视化聚类结果
visualize("DBSCAN", X, db_labels)


# ============================================================
# 4. GMM 聚类（基于模型的算法）
# ============================================================
# GMM（Gaussian Mixture Model）原理：
# - 假设数据由K个高斯分布的混合生成
# - 通过EM算法估计每个高斯分布的参数（均值、协方差）
# - 每个样本被分配给概率最大的高斯分布
# 优点：提供了概率化的聚类结果，而不仅仅是硬分配

gmm = GaussianMixture(
    n_components=3,    # 设置高斯分布的数量为3
    random_state=42    # 设置随机种子，确保结果可复现
)

# 拟合数据并预测聚类标签
gmm_labels = gmm.fit_predict(X)

# 评估聚类效果
evaluate("GMM", y_true, gmm_labels, X)

# 可视化聚类结果
visualize("GMM", X, gmm_labels)


# ============================================================
# 5. 谱聚类（基于图/谱的算法）
# ============================================================
# Spectral Clustering 原理：
# - 将数据看作图的顶点，样本相似度作为边权重
# - 使用图的拉普拉斯矩阵的特征向量进行降维
# - 在降维空间中使用K-Means进行聚类
# 优点：可以处理非凸形状的聚类，基于相似度而不是距离

spectral = SpectralClustering(
    n_clusters=3,                        # 设置聚类数为3
    affinity='nearest_neighbors',        # 使用最近邻图构建相似度矩阵
    random_state=42                      # 设置随机种子，确保结果可复现
)

# 拟合数据并预测聚类标签
sp_labels = spectral.fit_predict(X)

# 评估聚类效果
evaluate("Spectral Clustering", y_true, sp_labels, X)

# 可视化聚类结果
visualize("Spectral Clustering", X, sp_labels)
