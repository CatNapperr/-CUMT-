# 项目架构快速概览

## 系统架构

采用 **MVC (Model-View-Controller)** 分层架构。用户通过GUI与系统交互 → Controller响应事件 → Model处理数据 → View渲染结果。所有耗时的I/O操作都在后台线程异步执行，确保UI流畅。

---

## 主要服务模块

### 1. GUI视图服务 (View Layer)
- **文件**: `src/view/main_window.py`
- **职责**: 图形界面布局与用户交互
- **核心技术**:
  - `CustomTkinter` - 现代化跨平台GUI框架
  - 响应式网格布局 (grid_rowconfigure/columnconfigure)
  - 异步UI更新 (tkinter.after)

---

### 2. 数据库服务 (Model - Persistence)
- **文件**: `src/model/database.py`
- **职责**: 空气质量数据的增删改查
- **核心技术**:
  - `SQLite3` + `WAL模式` - 轻量级关系数据库，并发写入优化
  - 索引加速: `idx_city_date`, `idx_date_range`
  - 批量事务插入 - 性能提升10倍

---

### 3. 数据分析服务 (Model - Processing)
- **文件**: `src/model/predictor.py`
- **职责**: 时间序列预测与数据清洁
- **核心技术**:
  - `Pandas` - DataFrame数据处理、缺失值填充、时间序列重采样
  - `NumPy` - 指数平滑预测算法
  - 箱线图法异常值检测

---

### 4. 可视化服务 (Utils - Plotting)
- **文件**: `src/utils/plotter.py`
- **职责**: 多维数据图表绘制与交互
- **核心技术**:
  - `Matplotlib` + `FigureCanvasTkAgg` - 嵌入式图表渲染
  - `Seaborn` - 风格优化与统计绘图
  - 动态交互: 鼠标悬停提示、缩放平移、导出PNG

---

### 5. AI分析服务 (Utils - DeepSeek)
- **文件**: `src/utils/deepseek_service.py`
- **职责**: 利用大语言模型进行数据智能分析
- **核心技术**:
  - `OpenAI SDK` - DeepSeek API客户端 (兼容OpenAI接口)
  - 后台异步调用 - 防止阻塞UI

---

### 6. 数据采集服务 (Utils - API Fetcher)
- **文件**: `src/utils/api_fetcher.py`
- **职责**: 定时从外部API获取实时污染数据
- **核心技术**:
  - `requests` - HTTP请求库
  - `threading` + `Event` - 后台定时任务 (每1小时自动更新)
  - CSV/Excel导入 - `openpyxl`

---

### 7. 配置管理服务 (Utils - Config)
- **文件**: `src/utils/config.py`
- **职责**: YAML配置文件解析与全局配置管理
- **核心技术**:
  - `PyYAML` - YAML解析
  - 单例模式 - 全局唯一配置实例
  - PyInstaller路径适配 (sys._MEIPASS)

---

### 8. 应用控制器 (Controller)
- **文件**: `src/controller/app_controller.py`
- **职责**: 事件分发、服务编排、状态管理
- **核心技术**:
  - `threading` - 多线程异步任务管理
  - `logging` - 多级别日志记录 (DEBUG/INFO/ERROR/CRITICAL)
  - 依赖注入 - Model、View、Utility Services注入

---

## 核心技术栈总览

| 层级 | 技术 | 版本 | 用途 |
|------|------|------|------|
| **GUI** | CustomTkinter | ≥5.2.0 | 跨平台现代化界面 |
| **数据处理** | Pandas | ≥2.1.0 | 时间序列处理、聚合、缺失值处理 |
| **数学计算** | NumPy | ≥1.24.0 | 矩阵运算、预测算法 |
| **数据可视化** | Matplotlib | ≥3.7.0 | 多轴图表、趋势分析 |
| **统计美化** | Seaborn | ≥0.13.0 | 风格优化、调色板 |
| **数据库** | SQLite3 | 内置 | 轻量级结构化存储 |
| **AI服务** | OpenAI SDK | ≥1.0.0 | DeepSeek API集成 |
| **配置** | PyYAML | ≥6.0.0 | YAML文件解析 |
| **文件** | openpyxl | ≥3.1.0 | Excel读取 |
| **日历** | tkcalendar | ≥1.6.1 | 日期选择器 |
| **HTTP** | requests | ≥2.31.0 | API数据请求 |
| **日志** | logging | 内置 | 系统日志记录 |
| **打包** | PyInstaller | ≥6.0.0 | exe生成 |

---

## 数据流向

```
用户交互 (View)
  ↓
事件处理 (Controller)
  ↓
业务逻辑 (Model + Utils)
  ├─ 数据查询 (DatabaseManager)
  ├─ 数据清洁 (Predictor)
  ├─ 图表绘制 (Plotter)
  └─ AI分析 (DeepSeekService)
  ↓
UI更新 (View.after)
  ↓
用户看到分析结果
```

---

## 关键特性

✅ **异步处理** - 所有I/O操作后台化，UI永不卡顿  
✅ **多线程并发** - 数据查询、API调用、定时抓取并行执行  
✅ **模块解耦** - MVC分层，易于测试与维护  
✅ **性能优化** - 数据库索引、批量插入、缓存策略  
✅ **易于扩展** - 接口抽象，支持百万级→千万级→亿级数据演进  
✅ **PyInstaller支持** - 打包成独立exe文件，无需Python环境  

---

**更新时间**: 2026-04-07
