# NutriAI

NutriAI 是一个面向饮食管理场景的 AI 辅助应用。项目由 Android 前端、Python/FastAPI 后端、数据库迁移脚本和设计文档组成，支持餐食记录、图片识别、营养目标计算、首页汇总和周统计分析等能力。

## 项目结构

- `frontend/`：Android 原生应用，使用 Kotlin、Jetpack Compose、Material 3、Room 和 Retrofit。
- `backend/`：Python/FastAPI 服务端，包含接口、模型、服务、Alembic 迁移和测试。
- `docs/`：需求文档、后端分阶段实现文档、部署指南和演示材料。
- `examples/`：示例数据和设计资源。

## 环境要求

- Android Studio 及 Android SDK
- Python 3.10+，用于后端开发和测试
- PostgreSQL，用于后端数据存储
- Gemini API Key，用于图片和文本识别相关能力

## 本地运行

### 前端

1. 进入 `frontend/`。
2. 使用 Android Studio 打开项目。
3. 按需配置 `frontend/.env`，写入 `GEMINI_API_KEY`。
4. 在模拟器或真机上运行应用。

### 后端

1. 进入 `backend/`。
2. 安装依赖：`pip install -r requirements.txt`
3. 配置数据库连接和其他环境变量。
4. 启动服务：`uvicorn app.main:app --reload`
5. 运行测试：`pytest`

## 常用命令

```bash
cd frontend
gradle build
gradle test
gradle lint
```

```bash
cd backend
alembic upgrade head
uvicorn app.main:app --reload
pytest
```

## 说明

- 仓库根目录的 `.gitignore` 已统一忽略 Android、Python、IDE 和本地环境文件。
- 详细的后端实现和部署步骤可继续参考 `docs/` 下的阶段文档与部署指南。