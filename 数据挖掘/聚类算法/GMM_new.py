import numpy as np
from sklearn import datasets
from sklearn.preprocessing import StandardScaler
from sklearn.mixture import GaussianMixture
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score, silhouette_score,adjusted_mutual_info_score, homogeneity_score, completeness_score, v_measure_score
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt

# 1. 加载 Iris 数据集
iris = datasets.load_iris()
X = iris.data
y_true = iris.target  # 真实标签，用于评估（但不参与聚类）

# 3. GMM 聚类
gmm = GaussianMixture(n_components=3, covariance_type='full', random_state=42)
gmm_labels = gmm.fit_predict(X)

# 4. 聚类评测

print("GMM 聚类评测结果：")
print("AMI（调整互信息）:", adjusted_mutual_info_score(y_true, gmm_labels))
print("Homogeneity（同质性）:", homogeneity_score(y_true, gmm_labels))
print("Completeness（完整性）:", completeness_score(y_true, gmm_labels))
print("V-measure:", v_measure_score(y_true, gmm_labels))
print(f"Adjusted Rand Index (ARI):", adjusted_rand_score(y_true, gmm_labels))
print(f"Normalized Mutual Information (NMI):", normalized_mutual_info_score(y_true, gmm_labels))
print(f"Silhouette Score（轮廓系数）:", silhouette_score(X, gmm_labels))


# 5. 使用 PCA 将数据降到 2D，用于可视化
pca = PCA(n_components=2)
X_pca = pca.fit_transform(X)

# 6. 可视化结果
plt.figure(figsize=(8, 6))
plt.scatter(X_pca[:, 0], X_pca[:, 1], c=gmm_labels, cmap="viridis", s=50)
plt.title("Gaussian Mixture Model (GMM) 聚类结果（PCA 可视化）")
plt.xlabel("PCA Component 1")
plt.ylabel("PCA Component 2")

# 绘制簇中心
centers = gmm.means_
centers_pca = pca.transform(centers)
plt.scatter(centers_pca[:, 0], centers_pca[:, 1], 
            c='red', s=200, marker='X', label='Cluster Centers')

plt.legend()
plt.show()
