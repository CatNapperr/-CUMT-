
# 智慧城市交通可视化

一个面向课程设计的交通可视化与分析项目，包含实时流量监控、历史趋势展示、交通预警、绕行推荐以及基于小型问答接口的 AI 助手。后端基于 FastAPI，前端使用 ECharts 与原生 JS 实现大屏展示。

**主要目标**：提供可复现的开发环境、清晰的代码结构与快速上手说明，便于课程演示与二次开发。

**快速入口**
- **依赖**: 使用 [requirements.txt](requirements.txt) 管理 Python 包。
- **Docker（推荐）**: 使用 `docker compose` 启动完整环境（包含 MySQL）。
- **本地开发**: 支持不使用 Docker 的本地 MySQL + uvicorn 启动方式。

**快速启动（推荐：Docker）**

1. 在项目根目录执行：

```bash
docker compose up -d --build
```

2. 导入路段种子数据（建议使用容器复制，避免 Windows 编码问题）：

```bash
docker cp ./scripts/seed_roads.sql traffic-mysql:/tmp/seed_roads.sql
docker exec traffic-mysql sh -c "mysql --default-character-set=utf8mb4 -uroot -pYOUR_ROOT_PWD traffic_db < /tmp/seed_roads.sql"
```

3. （可选）生成历史样本数据以便快速查看趋势图：

```bash
docker exec traffic-backend python scripts/generate_history.py
```

4. 打开浏览器：

- 首页： http://localhost:8000/
- 详情页： http://localhost:8000/detail.html
- OpenAPI： http://localhost:8000/docs

**本地开发（不使用 Docker）**

1. 初始化数据库：

```bash
mysql -uroot -p < scripts/init_db.sql
mysql -uroot -p traffic_db < scripts/seed_roads.sql
```

2. 安装依赖：

```bash
pip install -r requirements.txt
```

3. 配置环境变量（示例）：

Windows PowerShell：

```powershell
$env:DATABASE_URL="mysql+pymysql://root:你的密码@127.0.0.1:3306/traffic_db?charset=utf8mb4"
```

4. 启动服务：

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

**项目结构（简要）**

- [main.py](main.py): 项目根启动入口（用于本地快速运行）。
- [backend/main.py](backend/main.py): 后端 FastAPI 应用入口。
- [frontend/index.html](frontend/index.html): 大屏主页面。
- [requirements.txt](requirements.txt): Python 依赖。
- [docker-compose.yml](docker-compose.yml): 推荐的容器编排。
- [scripts/generate_history.py](scripts/generate_history.py): 生成历史样本数据脚本。
- [scripts/seed_roads.sql](scripts/seed_roads.sql): 路段种子数据 SQL。

详细结构请参阅仓库目录。

**常用接口（示例）**

- `GET /api/health` — 健康检查
- `GET /api/roads` — 获取路段列表
- `GET /api/current` — 当前时刻路况汇总
- `GET /api/trend?hours=24&road_id=1` — 指定路段历史趋势
- `POST /api/assistant/chat` — AI 问答

（完整接口参见运行时的 [OpenAPI 文档](http://localhost:8000/docs)）

**开发建议**

- 后端代码主要位于 `backend/`，路由分散在 `backend/routers/` 中。
- 前端静态资源在 `frontend/`，地图数据在 `frontend/assets/xuzhou_full.json`。
- 若使用 Docker，请优先通过容器内命令导入 SQL，避免主机编码差异。

**常见问题**

- MySQL 端口冲突：默认将宿主端口映射为 `3307`，如需修改请编辑 [docker-compose.yml](docker-compose.yml)。
- 依赖安装慢或失败：可配置镜像源或使用国内 PyPI 镜像。

---


