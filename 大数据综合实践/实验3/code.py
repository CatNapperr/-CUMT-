# =========================
# (1) 数据预处理
# =========================
import paddle  # 导入 PaddlePaddle 主包
import paddle.fluid as fluid  # 导入 Fluid 静态图接口

import numpy as np  # 导入 NumPy
import matplotlib.pyplot as plt  # 导入绘图库

from sklearn.model_selection import train_test_split  # 导入数据集划分
from sklearn.metrics import mean_squared_error, mean_absolute_error  # 导入误差指标


# 数据路径
file_path = "data/data361/AbaloneAgePrediction.txt"  # 设置数据文件路径

# 读取文件
raw_data = []  # 保存原始行数据的列表

with open(file_path, "r") as f:  # 打开数据文件
    for line in f:  # 逐行读取
        line = line.strip()  # 去除首尾空白

        # 跳过空行
        if not line:  # 判断是否为空行
            continue  # 空行跳过

        raw_data.append(line.split(","))  # 按逗号切分并保存

print("样本数量:", len(raw_data))  # 打印样本数
print("第一条数据:", raw_data[0])  # 打印第一条样本


sex_map = {  # 定义性别映射
    "M": 0,
    "F": 1,
    "I": 2
}

features = []  # 保存特征
labels = []  # 保存标签

for row in raw_data:  # 遍历每条样本

    # 第一列：性别
    sex = sex_map[row[0]]  # 性别编码

    # 中间列：数值特征
    numeric_features = list(map(float, row[1:-1]))  # 数值特征转浮点

    # 拼接特征
    x = [sex] + numeric_features  # 组合特征向量

    # 最后一列：标签
    y = float(row[-1])  # 标签转浮点

    features.append(x)  # 追加特征
    labels.append(y)  # 追加标签

# 转 numpy
X = np.array(features, dtype=np.float32)  # 特征转为 NumPy 数组
y = np.array(labels, dtype=np.float32)  # 标签转为 NumPy 数组

print("X shape:", X.shape)  # 打印特征维度
print("y shape:", y.shape)  # 打印标签维度

# 计算每列最小值和最大值
x_min = X.min(axis=0)  # 每列最小值
x_max = X.max(axis=0)  # 每列最大值

# 防止除0
eps = 1e-8  # 加上极小值避免除 0

# 归一化
X_norm = (X - x_min) / (x_max - x_min + eps)  # Min-Max 归一化

print(X_norm[:5])  # 打印归一化后的前 5 条

# 先拿10条作为测试集
X_temp, X_test, y_temp, y_test = train_test_split(  # 划分测试集
    X_norm,
    y,
    test_size=10,
    random_state=42
)

# 剩余数据再划分训练集和验证集
X_train, X_val, y_train, y_val = train_test_split(  # 划分训练/验证集
    X_temp,
    y_temp,
    test_size=0.2,
    random_state=42
)

print("训练集大小:", X_train.shape)  # 打印训练集大小
print("测试集大小:", X_test.shape)  # 打印测试集大小
print("验证集大小:", X_val.shape)  # 打印验证集大小

# 说明：旧版本 Dataset/DataLoader 手动实现示例（仅说明，不执行）
"""
由于paddle版本过老，因此这里手动实现Dataset和Datloader，
并同时给出新版本的paddle的Dataset和Dataloader的写法
"""

# 说明：新版本 Dataset/DataLoader 写法示例（仅说明，不执行）
"""
新版本
import paddle
from paddle.io import Dataset, DataLoader


# 自定义数据集
class AbaloneDataset(Dataset):

    def __init__(self, X, y):

        super(AbaloneDataset, self).__init__()

        self.X = X.astype('float32')
        self.y = y.astype('float32')

    # 返回数据集大小
    def __len__(self):

        return len(self.X)

    # 根据索引获取单条数据
    def __getitem__(self, idx):

        x = self.X[idx]
        label = self.y[idx]

        return x, label


# 构造训练集
train_dataset = AbaloneDataset(
    X_train,
    y_train
)

# 构造验证集
val_dataset = AbaloneDataset(
    X_val,
    y_val
)

# 构造测试集
test_dataset = AbaloneDataset(
    X_test,
    y_test
)


# DataLoader
train_loader = DataLoader(
    train_dataset,
    batch_size=32,
    shuffle=True
)

val_loader = DataLoader(
    val_dataset,
    batch_size=32,
    shuffle=False
)

test_loader = DataLoader(
    test_dataset,
    batch_size=10,
    shuffle=False
)
"""

# 旧版本：手动实现 reader
def train_reader():  # 定义训练集 reader

    for i in range(len(X_train)):  # 遍历训练集索引

        x = X_train[i]  # 取出特征
        y = y_train[i]  # 取出标签

        yield x, y  # 生成单条样本


def val_reader():  # 定义验证集 reader

    for i in range(len(X_val)):  # 遍历验证集索引

        x = X_val[i]  # 取出特征
        y = y_val[i]  # 取出标签

        yield x, y  # 生成单条样本


def test_reader():  # 定义测试集 reader

    for i in range(len(X_test)):  # 遍历测试集索引

        x = X_test[i]  # 取出特征
        y = y_test[i]  # 取出标签

        yield x, y  # 生成单条样本


train_loader = paddle.batch(  # 构建训练集 batch 迭代器
    train_reader,
    batch_size=32
)

val_loader = paddle.batch(  # 构建验证集 batch 迭代器
    val_reader,
    batch_size=32
)

test_loader = paddle.batch(  # 构建测试集 batch 迭代器
    test_reader,
    batch_size=10
)

# 说明：新版本 Layer 写法示例（仅说明，不执行）
"""
# 定义全连接网络
class Regressor(paddle.nn.Layer):
    def __init__(self):
        super(Regressor, self).__init__()
        # 定义一层全连接层，输出维度是1，激活函数为None，即不使用激活函数
        self.linear = paddle.nn.Linear(8, 1, None)
    
    # 网络的前向计算函数
    def forward(self, inputs):
        x = self.linear(inputs)
        return x
"""

# =========================
# (2) 网络配置
# =========================

# 说明：使用老版本的 paddle 手动编写模型
"""
用老版本的paddle手动编写模型
"""
x = fluid.layers.data(  # 定义输入特征占位
    name='x',
    shape=[8],
    dtype='float32'
)

y = fluid.layers.data(  # 定义标签占位
    name='y',
    shape=[1],
    dtype='float32'
)

predict = fluid.layers.fc(  # 定义全连接输出层
    input=x,
    size=1,
    act=None
)


import os  # 导入系统操作模块
import numpy as np  # 再次导入 NumPy（保持原始结构）
import matplotlib.pyplot as plt  # 再次导入绘图库（保持原始结构）

import paddle.fluid as fluid  # 再次导入 Fluid（保持原始结构）

EPOCH_NUM = 10  # 设置训练轮数

# 说明：损失函数定义
"""
Loss
"""
loss = fluid.layers.square_error_cost(  # 定义平方误差损失
    input=predict,
    label=y
)

avg_loss = fluid.layers.mean(loss)  # 计算平均损失

# 说明：优化器定义
"""
优化器
"""
optimizer = fluid.optimizer.SGD(  # 定义 SGD 优化器
    learning_rate=0.01
)

optimizer.minimize(avg_loss)  # 绑定优化目标

# 说明：创建测试 Program，避免验证更新参数
"""
创建测试Program
防止验证集更新参数
"""
test_program = fluid.default_main_program().clone(  # 克隆主程序用于测试
    for_test=True
)

# 说明：创建执行器
"""
执行器
"""
place = fluid.CPUPlace()  # 设置运行设备

exe = fluid.Executor(place)  # 创建执行器

# 初始化参数
exe.run(fluid.default_startup_program())  # 运行初始化程序

# 说明：创建模型保存目录
"""
创建模型保存目录
"""
save_dir = "./model"  # 模型保存路径

if not os.path.exists(save_dir):  # 判断目录是否存在
    os.makedirs(save_dir)  # 创建目录

# =========================
# (3) 网络训练
# =========================

# 说明：保存训练 loss 的容器
"""
保存训练loss
"""
iters = []  # 保存迭代次数
train_costs = []  # 保存训练损失

# 说明：记录最佳验证 loss
"""
记录最佳验证loss
"""
best_cost = float('inf')  # 初始化最佳损失

iter_num = 0  # 初始化迭代计数

# 说明：开始训练
"""
开始训练
"""
for epoch_id in range(EPOCH_NUM):  # 遍历 epoch

    # =========================
    # 训练
    # =========================
    for batch_id, data in enumerate(train_loader()):  # 遍历训练 batch

        x_data = np.array(  # 组装批量特征
            [item[0] for item in data]
        ).astype('float32')

        y_data = np.array(  # 组装批量标签
            [item[1] for item in data]
        ).astype('float32').reshape(-1, 1)

        # 训练
        avg_loss_value = exe.run(  # 执行训练图
            program=fluid.default_main_program(),
            feed={
                'x': x_data,
                'y': y_data
            },
            fetch_list=[avg_loss]
        )

        loss_value = avg_loss_value[0][0]  # 取出标量损失

        # 保存loss
        iters.append(iter_num)  # 记录迭代编号
        train_costs.append(loss_value)  # 记录训练损失

        iter_num += 1  # 迭代计数自增

        # 每50次打印一次
        if batch_id % 50 == 0:  # 控制打印频率

            print(  # 打印当前损失
                "epoch: {}, iter: {}, loss is: {}".format(
                    epoch_id,
                    batch_id,
                    loss_value
                )
            )

    # =========================
    # (4) 网络评估
    # =========================

    test_costs = []  # 保存验证损失

    for _, data in enumerate(val_loader()):  # 遍历验证 batch

        x_data = np.array(  # 组装验证特征
            [item[0] for item in data]
        ).astype('float32')

        y_data = np.array(  # 组装验证标签
            [item[1] for item in data]
        ).astype('float32').reshape(-1, 1)
        
        

        # 注意：
        # 使用 test_program
        # 不会更新参数
        test_cost = exe.run(  # 执行验证图
            program=test_program,
            feed={
                'x': x_data,
                'y': y_data
            },
            fetch_list=[avg_loss]
        )

        test_costs.append(test_cost[0][0])  # 保存验证 loss

    # 平均验证loss
    test_cost = float(  # 计算验证平均损失
        sum(test_costs) / len(test_costs)
    )

    print(  # 打印验证损失
        "Test Epoch:{}, Cost:{:.5f}".format(
            epoch_id,
            test_cost
        )
    )

    # =========================
    # 保存最佳模型
    # =========================

    if test_cost < best_cost:  # 判断是否更优

        best_cost = test_cost  # 更新最佳损失

        fluid.io.save_params(  # 保存参数
            executor=exe,
            dirname=save_dir,
            main_program=fluid.default_main_program()
        )

        print("最佳模型保存成功！")  # 打印保存提示

# =========================
# (4) 网络评估（训练过程可视化）
# =========================

# =========================
# 绘制训练loss曲线
# =========================

# 创建图片目录
if not os.path.exists("./img"):  # 判断图片目录是否存在
    os.makedirs("./img")  # 创建图片目录

plt.figure(figsize=(10, 5))  # 创建画布

plt.plot(iters, train_costs)  # 绘制训练损失曲线

plt.xlabel('iter')  # 设置 x 轴标签
plt.ylabel('training cost')  # 设置 y 轴标签
plt.title('Training Cost vs Iter')  # 设置图标题

plt.grid()  # 显示网格

# 保存图片
plt.savefig('./img/training_cost.png')  # 保存训练损失图

# 显示图片
plt.show()  # 显示图像

print("训练完成！")  # 打印训练完成
print("最佳验证集loss:", best_cost)  # 打印最佳验证损失


# =========================
# (5) 网络预测
# =========================

def draw_plt(ground_truths,infer_results):  # 定义绘图函数
    # =========================
    # 创建图片目录
    # =========================

    if not os.path.exists("./img"):  # 判断图片目录是否存在
        os.makedirs("./img")  # 创建图片目录

    # =========================
    # 绘制散点图
    # =========================

    plt.figure(figsize=(8, 6))  # 创建画布

    # 散点图
    plt.scatter(  # 绘制散点
        ground_truths,
        infer_results
    )

    # 理想预测线
    min_val = min(  # 计算最小值
        np.min(ground_truths),
        np.min(infer_results)
    )

    max_val = max(  # 计算最大值
        np.max(ground_truths),
        np.max(infer_results)
    )

    plt.plot(  # 绘制理想预测线
        [min_val, max_val],
        [min_val, max_val]
    )

    plt.xlabel("ground truth")  # 设置 x 轴标签
    plt.ylabel("infer result")  # 设置 y 轴标签

    plt.title("abalone")  # 设置图标题

    plt.grid()  # 显示网格

    # 保存图片
    plt.savefig("./img/result_scatter.png")  # 保存散点图

    # 显示图片
    plt.show()  # 显示图像

    print("\n散点图已保存到 ./img/result_scatter.png")  # 打印保存提示

# =========================
# 开始预测
# =========================

fluid.io.load_params(  # 加载最佳模型参数
            executor=exe,
            dirname="./model"
        )

infer_results = []  # 保存预测结果
ground_truths = []  # 保存真实标签

for batch_id, data in enumerate(test_loader()):  # 遍历测试 batch

    x_data = np.array(  # 组装测试特征
        [item[0] for item in data]
    ).astype('float32')

    y_data = np.array(  # 组装测试标签
        [item[1] for item in data]
    ).astype('float32').reshape(-1, 1)

    

    result = exe.run(  # 执行推理
        program=test_program,
        feed={
            'x': x_data,
            'y': y_data
        },
        fetch_list=[predict]
    )

    preds = result[0]  # 获取预测输出

    for i in range(len(preds)):  # 遍历预测结果

        pred = float(preds[i][0])  # 取出预测值
        label = float(y_data[i][0])  # 取出真实值

        infer_results.append(pred)  # 保存预测值
        ground_truths.append(label)  # 保存真实值

        print(  # 打印单条预测结果
            "No. {}: infer result is {:.2f}, ground truth is {:.2f}".format(
                i,
                pred,
                label
            )
        )

# =========================
# 计算平均误差
# =========================

infer_results = np.array(infer_results)  # 预测结果转数组
ground_truths = np.array(ground_truths)  # 真实值转数组

avg_error = np.mean(  # 计算平均绝对误差
    np.abs(infer_results - ground_truths)
)

print("\n平均误差为: [{}]".format(avg_error))  # 打印平均误差

draw_plt(ground_truths,infer_results)  # 绘制散点图