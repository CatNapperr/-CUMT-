# 🏙️ 城市空气质量(AQI)实时监测与预测分析系统

> City Air Quality Index Real-time Monitoring & Prediction Analysis System

一个基于Python的专业级空气质量分析平台，集数据管理、统计分析、可视化展现和AI智能分析于一体。采用MVC三层架构设计，提供高效的数据处理、美观的图表展示、精准的趋势预测和深层的AI洞察。

## ✨ 核心功能

### 1. 数据存储与清洁
- SQLite关系数据库存储AQI历史记录
- 支持CSV/Excel数据导入
- WAL并发模式支持多线程访问
- 自动缺失值处理、异常值检测
- 联合索引加速查询性能

### 2. 统计分析与预测
- 按城市、日期范围的灵活数据查询
- PM2.5、PM10、SO2、NO2多污染物指标统计
- 基于指数平滑算法的7天趋势预测
- 四分位数分析与异常值识别
- 多城市对比分析

### 3. 多维可视化展现
- **2×2响应式仪表板**：四合一信息展示
  - 左侧趋势折线图：历史数据与预测对比
  - 右上环形图：污染物成分占比
  - 右下箱线图：浓度分布与异常检测
  - 顶部指标卡：PM2.5、AQI、空气质量等级
- 深色主题与CustomTkinter完全协调
- 中文字体自适应显示
- 响应式缩放，完美适配各种窗口大小

### 4. AI智能分析报告
- 集成DeepSeek大语言模型
- 自动生成专业分析报告（三段结构）：
  - 空气质量趋势总结
  - 异常值检测与风险识别
  - 环保建议与改善措施
- 后台异步处理，不阻塞UI

## 🛠️ 技术栈

| 层级 | 技术 | 版本 | 用途 |
|-----|-----|-----|------|
| **GUI框架** | CustomTkinter | ≥5.2.0 | 现代化跨平台桌面界面 |
| **数据处理** | Pandas | ≥2.1.0 | 时间序列处理、数据清洁、聚合统计 |
| **科学计算** | NumPy | ≥1.24.0 | 矩阵运算、预测算法实现 |
| **可视化** | Matplotlib + Seaborn | ≥3.7.0 | 图表生成、样式优化 |
| **数据库** | SQLite3 | 内置 | 本地结构化数据持久化 |
| **AI服务** | OpenAI SDK (DeepSeek) | ≥1.0.0 | 大语言模型智能分析 |
| **配置管理** | PyYAML | ≥6.0 | YAML配置文件解析 |
| **多线程** | threading | 内置 | 后台异步任务管理 |

## 📁 项目结构

```
AQI_System/
│
├── main.py                           # 🚀 项目入口 - 应用启动点
├── config.yaml                       # ⚙️ 配置文件 - API密钥、默认参数
├── requirements.txt                  # 📦 依赖清单
├── README.md                         # 📖 项目说明
│
├── src/                              # 📁 源代码主目录
│   ├── __init__.py
│   │
│   ├── model/                        # 🗄️  数据模型层（Model）
│   │   ├── database.py              # SQLite数据库管理器 (单例模式)
│   │   ├── predictor.py             # 时序预测模块 (指数平滑算法)
│   │   └── __init__.py
│   │
│   ├── view/                         # 🖥️  用户界面层（View）
│   │   ├── main_window.py           # CustomTkinter主窗口
│   │   └── __init__.py
│   │
│   ├── controller/                   # 🎮 控制层（Controller）
│   │   ├── app_controller.py        # 事件处理、流程编排、线程管理
│   │   └── __init__.py
│   │
│   └── utils/                        # 🔧 工具模块
│       ├── plotter.py               # Matplotlib图表绘制 (GridSpec布局)
│       ├── deepseek_service.py      # DeepSeek AI分析服务
│       ├── api_fetcher.py           # 实时数据采集服务
│       ├── config.py                # YAML配置管理 (单例模式)
│       └── __init__.py
│
├── data/                             # 💾 数据目录
│   ├── aqi.db                        # SQLite数据库文件
│   ├── historical_aqi_2020_2026.csv # 历史数据示例
│   ├── generate_massive_csv.py      # 数据生成脚本
│   ├── mock_data_generator.py       # 模拟数据工具
│   └── README.md
│
├── docs/                             # 📝 文档目录
│   ├── ARCHITECTURE_OVERVIEW.md     # 架构快速概览
│   ├── ARCHITECTURE_DEEPDIVE.md     # 深度架构分析
│   ├── TECH_STACK_DETAILS.md        # 技术栈详解
│   ├── VISUALIZATION_CODE_ANALYSIS.md # 可视化代码分析 
│   ├── PACKAGING_GUIDE.md           # 打包编译指南
│   ├── build_guide.md               # 构建说明
│   └── README.md
│
├── assets/                           # 🎨 静态资源
│   └── README.md                    # 图标、主题、样式资源
│
├── tests/                            # 🧪 测试目录
│   └── __init__.py                  # 单元测试、集成测试
│
├── build/                            # 🔨 编译输出目录
│   └── AQI_System/                  # PyInstaller打包文件
│
├── build.sh                          # Linux编译脚本
└── build.ps1                         # Windows编译脚本
```

## 🏗️ 系统架构

本项目采用**严格的MVC三层架构**设计，确保高内聚低耦合：

### 架构分层说明
- **Model（模型层）**：封装数据库操作、数据处理、业务逻辑，对外提供干净的接口
- **View（视图层）**：负责GUI界面布局、用户交互展示，不包含任何业务逻辑
- **Controller（控制层）**：作为Model和View的桥梁，协调事件分发、异步任务、状态管理

### 数据流向
```
用户交互 → View事件捕获 → Controller事件分发 → Model处理数据 → View更新展示
```

### 核心特性
- **异步设计**：后台线程处理耗时操作，主线程通过`view.after()`回调更新UI，保证流畅体验
- **线程安全**：严格遵循Tkinter线程安全规范，所有UI修改在主线程执行
- **解耦高内聚**：各层相互独立，可独立测试、迭代升级，降低维护成本

## 🚀 快速开始

### 前置要求
- Python 3.9+
- pip 或 conda 包管理器

### 安装步骤

```bash
# 1. 克隆或解压项目
cd 设计一

# 2. 创建虚拟环境（推荐）
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置API（可选 - 若要使用AI分析）
# 编辑 config.yaml，填入 DeepSeek API Key
# deepseek:
#   api_key: "your_deepseek_api_key"

# 5. 启动应用
python main.py
```

## 💡 使用指南

### 基本操作流程
1. **选择城市**：从左侧Sidebar的ComboBox中选择城市
2. **设置日期**：手动输入或点击日历按钮选择日期范围
3. **快速日期**：使用"近一周"、"近一月"、"近一年"快捷按钮
4. **点击更新**：点击"更新分析视图"按钮触发分析
5. **查看结果**：
   - 顶部指标卡：PM2.5、AQI评分、空气质量等级
   - 左侧趋势图：历史数据与7天预测对比
   - 右侧统计图：污染物占比与分布特征
   - 下方AI报告：自动生成的专业分析结论

### 数据导入
- 点击"📁 导入 CSV / Excel"按钮
- 选择包含AQI数据的文件（支持标准AQI数据格式）
- 系统自动验证并导入数据

## 📊 可视化仪表板

| 区域 | 图表类型 | 信息展现 |
|-----|--------|--------|
| **左侧（占比2:1）** | 折线图 | PM2.5/PM10历史数据与预测（实线vs虚线） |
| **右上** | 环形图 | 四种污染物平均浓度占比 |
| **右下** | 箱线图 | 污染物浓度分布（中位数、四分位数、异常值） |
| **顶部** | 指标卡 | PM2.5浓度、AQI评分、空气质量等级 |

### 设计特点
- ✅ 深色主题与CustomTkinter完全协调（背景色#2b2b2b）
- ✅ 色彩编码一致：PM2.5(蓝)、PM10(橙)、SO2(红)、NO2(绿)
- ✅ 中文字体自适应：自动检测并使用系统可用字体
- ✅ 响应式缩放：图表随窗口大小自动调整

## 🔧 配置说明

编辑 `config.yaml` 自定义系统参数：

```yaml
app:
  default_city: "北京"
  default_days_range: 365

deepseek:
  api_key: "your_api_key_here"
  base_url: "https://api.deepseek.com"
  proxy: null  # 可选代理

database:
  path: "data/aqi.db"
```

## 📚 详细文档

更多信息请查阅 `/docs` 目录：
- [可视化代码分析](docs/VISUALIZATION_CODE_ANALYSIS.md) - 关键代码与实现细节
- [架构深度解析](docs/ARCHITECTURE_DEEPDIVE.md) - MVC、数据流、设计模式
- [技术栈详解](docs/TECH_STACK_DETAILS.md) - 各技术库的具体用法

## 🧪 开发与扩展

### 开发环境推荐
- IDE: VS Code / PyCharm
- Python 3.9+
- 虚拟环境: venv

### 常见扩展
1. **更换数据库**：编辑 `src/model/database.py` 的DatabaseManager类
2. **新增图表**：扩展 `src/utils/plotter.py` 的图表绘制逻辑
3. **优化预测**：改进 `src/model/predictor.py` 的算法
4. **接入真实API**：完善 `src/utils/api_fetcher.py` 的数据采集
