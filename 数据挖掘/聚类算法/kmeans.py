from sklearn.datasets import load_iris
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt
from sklearn.metrics import (
    adjusted_rand_score,
    adjusted_mutual_info_score,
    silhouette_score,
    homogeneity_score,
    completeness_score,
    v_measure_score,
    normalized_mutual_info_score
)
import numpy as np

# 1. 加载数据
data = load_iris()
X = data.data
y_true = data.target

# 2. 聚类模型
kmeans = KMeans(n_clusters=3, random_state=42)
kmeans.fit(X)
labels = kmeans.labels_

print("聚类标签前 10 个：", labels[:10])

# -------- 外部指标（需要真实标签） --------
print("\n===== 外部指标（与真实标签对比） =====")
print("ARI（调整兰德指数）：", adjusted_rand_score(y_true, labels))
print("AMI（调整互信息）：", adjusted_mutual_info_score(y_true, labels))
print("同质性 Homogeneity：", homogeneity_score(y_true, labels))
print("完整性 Completeness：", completeness_score(y_true, labels))
print(f"Normalized Mutual Information (NMI):", normalized_mutual_info_score(y_true, labels))
print("V-measure：", v_measure_score(y_true, labels))


# -------- 内部指标（不依赖真实标签） --------
print("\n===== 内部指标（仅使用 X） =====")
sil = silhouette_score(X, labels)
print("Silhouette Score（轮廓系数）：", sil)

# 5. 使用 PCA 将数据降到 2D，用于可视化
pca = PCA(n_components=2)
X_pca = pca.fit_transform(X)

# 6. 可视化结果
plt.figure(figsize=(8, 6))
plt.scatter(X_pca[:, 0], X_pca[:, 1], c=labels, cmap="viridis", s=50)
plt.title("K-means 聚类结果（PCA 可视化）")
plt.xlabel("PCA Component 1")
plt.ylabel("PCA Component 2")

# 绘制簇中心
centers = kmeans.cluster_centers_
centers_pca = pca.transform(centers)
plt.scatter(centers_pca[:, 0], centers_pca[:, 1], 
            c='red', s=200, marker='X', label='Cluster Centers')

plt.legend()
plt.show()
