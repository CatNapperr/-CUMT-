# 模块说明

(1) 数据预处理
- 关键代码：
```python
file_path = "data/data361/AbaloneAgePrediction.txt"

raw_data = []
with open(file_path, "r") as f:
	for line in f:
		line = line.strip()
		if not line:
			continue
		raw_data.append(line.split(","))
```
```python
sex_map = {"M": 0, "F": 1, "I": 2}
features, labels = [], []
for row in raw_data:
	sex = sex_map[row[0]]
	numeric_features = list(map(float, row[1:-1]))
	x = [sex] + numeric_features
	y = float(row[-1])
	features.append(x)
	labels.append(y)
```
```python
X = np.array(features, dtype=np.float32)
y = np.array(labels, dtype=np.float32)
x_min = X.min(axis=0)
x_max = X.max(axis=0)
X_norm = (X - x_min) / (x_max - x_min + 1e-8)
```
```python
X_temp, X_test, y_temp, y_test = train_test_split(X_norm, y, test_size=10, random_state=42)
X_train, X_val, y_train, y_val = train_test_split(X_temp, y_temp, test_size=0.2, random_state=42)
```
```python
def train_reader():
	for i in range(len(X_train)):
		yield X_train[i], y_train[i]

train_loader = paddle.batch(train_reader, batch_size=32)
```
- 分析说明：先读入文本并按行切分，得到原始字符串特征；性别做离散编码后与数值特征拼接，构成 8 维输入；标签取最后一列。随后对每一列做 min-max 归一化以消除量纲差异。最后按固定随机种子划分训练/验证/测试集，并用旧版 `reader` 生成批数据供训练阶段使用。

(2) 网络配置
- 关键代码：
```python
x = fluid.layers.data(name='x', shape=[8], dtype='float32')
y = fluid.layers.data(name='y', shape=[1], dtype='float32')
predict = fluid.layers.fc(input=x, size=1, act=None)
```
```python
loss = fluid.layers.square_error_cost(input=predict, label=y)
avg_loss = fluid.layers.mean(loss)
optimizer = fluid.optimizer.SGD(learning_rate=0.01)
optimizer.minimize(avg_loss)
```
```python
test_program = fluid.default_main_program().clone(for_test=True)
place = fluid.CPUPlace()
exe = fluid.Executor(place)
exe.run(fluid.default_startup_program())
```
- 分析说明：输入为 8 维特征，输出为 1 维连续值，使用单层全连接实现线性回归；损失函数为平方误差并取均值；优化器用 SGD，学习率 0.01。通过克隆主图得到 `test_program`，确保评估阶段不更新参数。执行器与启动程序只初始化一次，参数在训练过程中持续更新。

(3) 网络训练
- 关键代码：
```python
for epoch_id in range(EPOCH_NUM):
	for batch_id, data in enumerate(train_loader()):
		x_data = np.array([item[0] for item in data]).astype('float32')
		y_data = np.array([item[1] for item in data]).astype('float32').reshape(-1, 1)
		avg_loss_value = exe.run(
			program=fluid.default_main_program(),
			feed={'x': x_data, 'y': y_data},
			fetch_list=[avg_loss]
		)
```
- 分析说明：训练阶段按 epoch 迭代，每个 batch 组装为二维输入与列向量标签。`exe.run` 在主训练图上执行前向与反向传播并更新参数，同时取出平均损失用于监控。训练损失被记录到列表用于后续可视化。

(4) 网络评估
- 关键代码：
```python
test_costs = []
for _, data in enumerate(val_loader()):
	x_data = np.array([item[0] for item in data]).astype('float32')
	y_data = np.array([item[1] for item in data]).astype('float32').reshape(-1, 1)
	test_cost = exe.run(
		program=test_program,
		feed={'x': x_data, 'y': y_data},
		fetch_list=[avg_loss]
	)
	test_costs.append(test_cost[0][0])
test_cost = float(sum(test_costs) / len(test_costs))
```
```python
if test_cost < best_cost:
	best_cost = test_cost
	fluid.io.save_params(executor=exe, dirname=save_dir, main_program=fluid.default_main_program())
```
- 分析说明：评估阶段使用 `test_program`，仅做前向计算不会更新权重。把每个 batch 的损失累加求均值，得到该 epoch 的验证损失。若当前损失优于历史最佳，就保存当前参数作为“最佳模型”。

(5) 网络预测
- 关键代码：
```python
fluid.io.load_params(executor=exe, dirname="./model")
for batch_id, data in enumerate(test_loader()):
	x_data = np.array([item[0] for item in data]).astype('float32')
	y_data = np.array([item[1] for item in data]).astype('float32').reshape(-1, 1)
	result = exe.run(
		program=test_program,
		feed={'x': x_data, 'y': y_data},
		fetch_list=[predict]
	)
```
```python
infer_results = np.array(infer_results)
ground_truths = np.array(ground_truths)
avg_error = np.mean(np.abs(infer_results - ground_truths))
```
- 分析说明：先加载验证集上表现最好的参数，再在测试集上做推理。推理阶段只取 `predict` 输出，随后把预测值与真实值对齐计算平均绝对误差，最后绘制散点图用于直观观察预测效果。
