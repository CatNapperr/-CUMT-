from sklearn.datasets import load_iris
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.mixture import GaussianMixture
from sklearn.metrics import (adjusted_mutual_info_score, homogeneity_score, completeness_score,
                             v_measure_score, adjusted_rand_score, normalized_mutual_info_score,
                             silhouette_score)
import numpy as np

# 加载鸢尾花数据
data = load_iris()
X = data.data
y_true = data.target  # 虽然是聚类，无监督，但用于评估效果

# -------------------------
# 数据标准化
# -------------------------
scaler = StandardScaler()
X_std = scaler.fit_transform(X)

# ---------------------------------------------------
# 聚类评测指标函数（与您之前使用的保持一致）
# ---------------------------------------------------
def evaluate_cluster(y_true, y_pred, X):
    print("AMI（调整互信息）:", adjusted_mutual_info_score(y_true, y_pred))
    print("Homogeneity（同质性）:", homogeneity_score(y_true, y_pred))
    print("Completeness（完整性）:", completeness_score(y_true, y_pred))
    print("V-measure:", v_measure_score(y_true, y_pred))
    print("Adjusted Rand Index (ARI):", adjusted_rand_score(y_true, y_pred))
    print("Normalized Mutual Information (NMI):", normalized_mutual_info_score(y_true, y_pred))
    print("Silhouette Coefficient（轮廓系数）:", silhouette_score(X, y_pred))
    print("-" * 60)

# -------------------------
# 1. K-Means 聚类
# -------------------------
kmeans = KMeans(n_clusters=3, random_state=42)
kmeans_labels = kmeans.fit_predict(X_std)

print("K-Means 聚类结果评测：")
evaluate_cluster(y_true, kmeans_labels, X_std)

# -------------------------
# 2. GMM 聚类
# -------------------------
gmm = GaussianMixture(n_components=3, random_state=42)
gmm_labels = gmm.fit_predict(X_std)

print("GMM 聚类结果评测：")
evaluate_cluster(y_true, gmm_labels, X_std)
