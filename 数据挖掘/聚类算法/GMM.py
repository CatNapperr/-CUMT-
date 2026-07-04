from sklearn.datasets import load_iris
from sklearn.mixture import GaussianMixture
from sklearn.metrics import (
    adjusted_rand_score, 
    adjusted_mutual_info_score,
    homogeneity_score,
    completeness_score,
    v_measure_score,
    silhouette_score,
    precision_score,
    recall_score,
    f1_score
)
from scipy.optimize import linear_sum_assignment
import numpy as np

# ======================
# 1. 加载鸢尾花数据
# ======================
data = load_iris()
X = data.data
y_true = data.target

# ======================
# 2. 使用 GMM 聚类
# ======================
gmm = GaussianMixture(n_components=3, covariance_type='full', random_state=42)
gmm.fit(X)
clusters = gmm.predict(X)

print("GMM 聚类标签前 10 个：", clusters[:10])

# ======================
# 3. 外部指标（依赖真实标签）
# ======================
print("\n===== 外部指标 =====")
print("ARI（调整兰德指数）:", adjusted_rand_score(y_true, clusters))
print("AMI（调整互信息）:", adjusted_mutual_info_score(y_true, clusters))
print("Homogeneity（同质性）:", homogeneity_score(y_true, clusters))
print("Completeness（完整性）:", completeness_score(y_true, clusters))
print("V-measure:", v_measure_score(y_true, clusters))

# ======================
# 4. 内部指标（不依赖真实标签）
# ======================
sil = silhouette_score(X, clusters)
print("\n===== 内部指标 =====")
print("Silhouette Score（轮廓系数）:", sil)

# ======================
# 5. 精确率 / 召回率 / F1（需匈牙利算法对齐）
# ======================
# 构造代价矩阵
cost_matrix = np.zeros((3, 3), dtype=int)
for i in range(3):
    for j in range(3):
        cost_matrix[i, j] = np.sum((clusters == i) & (y_true == j))

# 匈牙利算法找到最佳映射
row_ind, col_ind = linear_sum_assignment(cost_matrix.max() - cost_matrix)

mapping = {cluster: label for cluster, label in zip(row_ind, col_ind)}
aligned = np.array([mapping[c] for c in clusters])

print("\n===== 精度指标（按真实标签对齐后） =====")
print("Precision:", precision_score(y_true, aligned, average='macro'))
print("Recall:", recall_score(y_true, aligned, average='macro'))
print("F1-score:", f1_score(y_true, aligned, average='macro'))
