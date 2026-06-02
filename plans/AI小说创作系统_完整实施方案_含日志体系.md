# AI 小说创作系统 — 完整实施方案（含日志体系）

> **版本**: v1.0  
> **编制日期**: 2026-05-28  
> **基于文档**: 15 个 @AI小说相关 文件 + 多轮对话设计文档 + 日志系统专项设计  
> **适用范围**: 从零搭建到生产部署的全流程 AI 小说创作系统  

---

## 目录

1. [系统总览与架构目标](#一系统总览与架构目标)
2. [环境配置清单](#二环境配置清单)
3. [分阶段实施流程](#三分阶段实施流程)
4. [各环节失败回退方案](#四各环节失败回退方案)
5. [性能优化与监控](#五性能优化与监控)
6. [验收标准与交付物](#六验收标准与交付物)
7. [**附录 A：日志系统总体架构**](#附录a日志系统总体架构)
8. [**附录 B：日志目录结构与命名规范**](#附录b日志目录结构与命名规范)
9. [**附录 C：各组件日志规范**](#附录c各组件日志规范)
10. [**附录 D：日志格式与字段定义**](#附录d日志格式与字段定义)
11. [**附录 E：日志采集与写入实现**](#附录e日志采集与写入实现)
12. [**附录 F：日志轮转与生命周期管理**](#附录f日志轮转与生命周期管理)
13. [**附录 G：日志查询与分析工具**](#附录g日志查询与分析工具)
14. [**附录 H：日志在失败回退中的作用**](#附录h日志在失败回退中的作用)
15. [**附录 I：实施检查清单**](#附录i实施检查清单)

---

# 第一部分：完整实施方案

---

## 一、系统总览与架构目标

### 1.1 核心设计原则

| 原则 | 定义 | 实现方式 |
|------|------|---------|
| 用户只审核，AI 自动执行 | 用户用自然语言驱动修改，不需要精确指令 | 代码分离，生成/写作/审核各自独立运行 |
| 中央档案库为唯一数据源 | 所有模块数据统一存储，互相引用 | PostgreSQL + pgvector 统一数据库 |
| 模块化可扩展 | 新模块一行代码注册即可接入 | BaseModule 接口 + ModuleRegistry 注册表 |
| 双向同步用户可见 | 用户看中文 Markdown，系统操作结构化 JSON | SYNC 标记库 + 同步引擎 |
| 质量四层保证 | 设定一致性 / 逻辑质量 / 文学质感 / 读者吸引力 | 分层审查引擎 + AI 痕迹检测器 |
| 伏笔全生命周期管理 | 每个伏笔可追踪、可检索、防重复 | FORE 档案实体 + 向量相似度检测 |

### 1.2 系统架构总图

```
┌─────────────────────────────────────────────────────────────────────┐
│                        用户界面层 (UI Layer)                          │
│  ┌──────────────────┐ ┌──────────────────┐ ┌───────────────────────┐ │
│  │  小说档案面板     │ │  Markdown 编辑器  │ │  主题面板/伏笔面板等   │ │
│  └────────┬─────────┘ └────────┬─────────┘ └──────────┬────────────┘ │
└───────────┼────────────────────┼──────────────────────┼──────────────┘
            │                    │                      │
┌───────────┼────────────────────┼──────────────────────┼──────────────┐
│           ▼                    ▼                      ▼              │
│                     API 网关层 (Gateway)                               │
│   统一接口 | 路由分发 | 认证鉴权 | 流量限制 | 请求缓存 | 事件广播         │
└───────────┬────────────────────┬──────────────────────┬──────────────┘
            │                    │                      │
┌───────────┼────────────────────┼──────────────────────┼──────────────┐
│           ▼                    ▼                      ▼              │
│                模块注册表 & 服务实现 (Registry)                             │
│   模块名 | 版本 | API端点 | 健康状态 | 依赖列表 | 审核模块绑定关系        │
└───────────┬────────────────────┬──────────────────────┬──────────────┘
            │                    │                      │
┌───────────┼────────────────────┼──────────────────────┼──────────────┐
│           ▼                    ▼                      ▼              │
│                      消息队列 (Message Queue)                              │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐       │
│  │ 生成任务队列 │  │ 写作任务队列 │  │ 审核任务队列 │  │ 同步事件队列 │       │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘       │
└────────┼────────────┼────────────┼────────────────────┼──────────────┘
         │            │            │                    │
┌────────▼────────────▼────────────▼────────────────────▼──────────────┐
│                         子代理层 (Agent Layer)                          │
│                                                                         │
│  ┌────────────────────────┐ ┌────────────────────┐ ┌────────────────┐  │
│  │   生成代理 (Generator)  │ │  写作代理 (Writer)   │ │ 审核代理(Rev)  │  │
│  │  ┌──────────────────┐  │ │  ┌──────────────┐  │ │                │  │
│  │  │ 设定生成器        │  │ │  │ 正文生成器    │  │ │ 四层审查引擎   │  │
│  │  │ 经纪生成器        │  │ │  │ 场景展开器    │  │ │ 一致性检查器   │  │
│  │  │ 伏笔设计器        │  │ │  │ 对话写作器    │  │ │ 逻辑链验证器   │  │
│  │  │ 大纲生成器        │  │ │  │ 文风增强器    │  │ │ AI痕迹检测器   │  │
│  │  └──────────────────┘  │ │  └──────────────┘  │ └────────────────┘  │
│  └────────────────────────┘ └────────────────────┘                     │
└─────────────────────────────────────────────────────────────────────┘
          │                │                │
┌─────────▼────────────────▼────────────────▼─────────────────────────┐
│                           数据层 (Data Layer)                          │
│                                                                         │
│  ┌─────────────────────────────┐  ┌──────────────────────────────┐    │
│  │  关系型数据库               │  │  向量数据库                    │    │
│  │  (PostgreSQL + pgvector)   │  │  (pgvector 嵌入 PostgreSQL)    │    │
│  │                            │  │                                │    │
│  │  • 12模块结构化数据         │  │  • 角色档案向量 (语义查询)      │    │
│  │  • 实体关系 & 引用图        │  │  • 章节正文向量 (内容相似度)    │    │
│  │  • 变更日志 & 版本快照      │  │  • 伏笔描述向量 (主题检索)      │    │
│  │  • 用户权限 & 配置          │  │  • 世界观规则向量 (规则匹配)    │    │
│  └─────────────────────────────┘  └──────────────────────────────┘    │
│                                                                         │
│  ┌─────────────────────────────┐  ┌──────────────────────────────┐    │
│  │  Redis 缓存层               │  │  MinIO / 本地FS 文件存储      │    │
│  │  • 约束文件缓存             │  │  • Markdown 用户可见文件       │    │
│  │  • 章节生成中间状态         │  │  • 版本快照存档               │    │
│  │  • 实时词频面板数据         │  │  • 导出 PDF/EPUB              │    │
│  └─────────────────────────────┘  └──────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.3 写作流程 19 个环节

```
灵感启动 → 小说主题 → 拟定大纲 → 世界观设定 → 人物设定 → 人物关系 → 角色弧线
→ 势力设定 → 势力关系 → 物品库 → 伏笔追踪 → 小说档案 → 小说简介
→ 细纲配置 → 章节细纲 → 正文初稿 → 正文审核 → 正文修正
```
每个环节对应一个或多个微服务模块，通过中央档案库共享数据，通过消息队列串行或并行执行。

---

## 二、环境配置清单

### 2.1 开发环境（操作手册）

| 类别 | 软件/组件 | 版本要求 | 用途 |
|------|----------|---------|------|
| 操作系统 | Ubuntu 22.04 LTS / macOS 14+ / Windows 11 WSL2 | — | 主机操作系统 |
| Python | 3.11+ | ≥3.11.0 | 后端服务主语言 |
| Node.js | 20+ | ≥20.0.0 | 前端 UI 服务 |
| 数据库 | SQLite | ≥3.40.0 | 开发环境轻量数据库（替代 PostgreSQL）|
| 向量搜索 | ChromaDB | ≥0.4.0 | 开发环境轻量向量数据库 |
| 缓存 | 可选（开发环境可不部署）| — | 生产环境需要 Redis |
| 消息队列 | 内存队列（开发模式）| — | 开发环境使用内存模式 |
| LLM 接口 | OpenAI API / 兼容接口 | — | 核心生成能力 |
| 嵌入模型 | bge-large-zh-v1.5 (本地) 或 text-embedding-3-large (API)| — | 中文嵌入 |
| Docker | ≥24.0 | — | 容器化部署（可选）|
| Git | ≥2.40 | — | 版本控制 |

**Python 依赖清单 (`requirements-dev.txt`)**:

```txt
# === Web 框架 ===
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
pydantic>=2.5.0
python-multipart>=0.0.6

# === 数据库 ===
sqlalchemy[asyncio]>=2.0.25
aiosqlite>=0.19.0          # SQLite 异步驱动
alembic>=1.13.0             # 数据库迁移工具

# === 向量搜索 (开发环境) ===
chromadb>=0.4.24
sentence-transformers>=2.3.0  # 本地嵌入模型

# === 缓存 (开发可选) ===
# redis>=5.0.0
# aioredis>=2.0.0

# === 消息队列 (开发用内存模式) ===
celery[redis]>=5.3.0         # 生产用，开发可用内存模式

# === LLM 调用 ===
openai>=1.12.0
httpx>=0.26.0                # 异步 HTTP 客户端
tenacity>=8.2.0              # 重试机制

# === 工具库 ===
python-dotenv>=1.0.0
loguru>=0.7.2                # 日志
pyyaml>=6.0.1
jinja2>=3.1.3                # Markdown 模板渲染
markdown>=3.5.1              # Markdown 解析
python-frontmatter>=1.0.0    # YAML frontmatter 解析

# === 日志系统 (新增) ===
structlog>=24.1.0            # 结构化日志

# === 测试 ===
pytest>=7.4.0
pytest-asyncio>=0.23.0
httpx                     # TestClient
```

### 2.2 生产环境（推荐配置）

| 类别 | 软件/组件 | 版本要求 | 部署方式 | 用途 |
|------|----------|---------|---------|------|
| 操作系统 | Ubuntu 22.04 LTS / Debian 12 | — | 物理源/云主机 | 主机 OS |
| 容器编排 | Docker Compose / Kubernetes | ≥24.0 / ≥1.28 | 容器化 | 应用服务容器 |
| 反向代理 | Nginx / Traefik | ≥1.24 / ≥3.0 | Docker | API 网关 |
| 数据库 | PostgreSQL | ≥16 | Docker | 主数据库 |
| 向量扩展 | pgvector | ≥0.7.0 | PostgreSQL 扩展 | 向量搜索嵌入 |
| 缓存 | Redis | ≥7.2 | Docker | 会话/缓存/队列 |
| 消息队列 | RabbitMQ | ≥3.12 | Docker | 任务队列 |
| 对象存储 | MinIO | ≥2024.1 | Docker | 文件存储 |
| 监控 | Prometheus + Grafana | latest | Docker | 性能监控 |
| 日志 | ELK Stack / Loki | latest | Docker | 日志收集 |
| LLM 接口 | OpenAI API / Azure OpenAI / 本地 Ollama | — | 外部服务 | 核心生成能力 |
| 嵌入模型服务 | TEI (Text Embeddings Inference) / 本地推理 | — | Docker/GPU | 高吞吐嵌入 |

### 2.3 生产环境 `docker-compose.yml` 核心服务定义

```yaml
version: '3.9'

services:
  # === API 网关 ===
  gateway:
    image: nginx:1.24-alpine
    ports: ["80:80", "443:443"]
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
    depends_on: [api-server, registry]
    restart: unless-stopped

  # === API 主服务 ===
  api-server:
    build: { context: ., dockerfile: Dockerfile.api }
    environment:
      - DATABASE_URL=postgresql+asyncpg://noveluser:@postgres:5432/novel_db
      - REDIS_URL=redis://redis:6379/0
      - RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - EMBEDDING_MODEL=${EMBEDDING_MODEL}
      - ENVIRONMENT=production
      - LOG_LEVEL=INFO
    depends_on:
      postgres: { condition: service_healthy }
      redis: { condition: service_healthy }
      rabbitmq: { condition: service_healthy }
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s; timeout: 10s; retries: 3

  # === PostgreSQL + pgvector ===
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: noveluser
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: novel_db
    volumes: [postgres_data:/var/lib/postgresql/data]
    ports: ["5432:5432"]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U noveluser -d novel_db"]
      interval: 10s; timeout: 5s; retries: 5
    restart: unless-stopped

  # === Redis ===
  redis:
    image: redis:7.2-alpine
    command: redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru
    volumes: [redis_data:/data]
    ports: ["6379:6379"]
    healthcheck: { test: ["CMD", "redis-cli", "ping"], interval: 10s, timeout: 10s, retries: 3 }
    restart: unless-stopped

  # === RabbitMQ ===
  rabbitmq:
    image: rabbitmq:3.12-management-alpine
    environment: { RABBITMQ_DEFAULT_USER: guest, RABBITMQ_DEFAULT_PASSWORD: guest }
    volumes: [rabbitmq_data:/var/lib/rabbitmq]
    ports: ["5672:5672", "15672:15672"]
    healthcheck: { test: ["CMD", "rabbitmq-diagnostic", "-q", "ping"], interval: 15s, timeout: 10s, retries: 5 }
    restart: unless-stopped

  # === MinIO (对象存储) ===
  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ACCESS_KEY}
      MINIO_ROOT_PASSWORD: ${MINIO_SECRET_KEY}
    volumes: [minio_data:/data]
    ports: ["9000:9000", "9001:9001"]
    restart: unless-stopped

  # === 嵌入模型服务 (本地推理) ===
  embedding-service:
    build: { context: ., dockerfile: Dockerfile.embedding }
    deploy:
      resources:
        reservations:
          devices: [{ driver: nvidia, count: 1, capabilities: [gpu] }]
    environment: [MODEL_ID=BAAI/bge-large-zh-v1.5, PORT=8080]
    ports: ["8080:8080"]
    restart: unless-stopped

  # === 模块注册表服务 ===
  registry:
    build: { context: ., dockerfile: Dockerfile.registry }
    environment:
      - DATABASE_URL=postgresql+asyncpg://noveluser:@postgres:5432/novel_db
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      postgres: { condition: service_healthy }
      redis: { condition: service_healthy }
    restart: unless-stopped

  # === 生成代理池 (可水平扩展) ===
  generator-agent:
    build: { context: ., dockerfile: Dockerfile.agent-generator }
    environment:
      - DATABASE_URL=postgresql+asyncpg://noveluser:@postgres:5432/novel_db
      - REDIS_URL=redis://redis:6379/0
      - RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - AGENT_TYPE=generator
      - TEMPERATURE=0.85  # 高温度=高创意
    depends_on: [postgres, redis, rabbitmq]
    deploy: { replicas: 2 }  # 生成代理池大小
    restart: unless-stopped

  # === 写作代理池 ===
  writer-agent:
    build: { context: ., dockerfile: Dockerfile.agent-writer }
    environment:
      - DATABASE_URL=postgresql+asyncpg://noveluser:@postgres:5432/novel_db
      - REDIS_URL=redis://redis:6379/0
      - RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - AGENT_TYPE=writer
      - TEMPERATURE=0.65  # 中温度=稳定输出
    depends_on: [postgres, redis, rabbitmq]
    deploy: { replicas: 1 }
    restart: unless-stopped

  # === 审核代理池 (可水平扩展) ===
  reviewer-agent:
    build: { context: ., dockerfile: Dockerfile.agent-reviewer }
    environment:
      - DATABASE_URL=postgresql+asyncpg://noveluser:@postgres:5432/novel_db
      - REDIS_URL=redis://redis:6379/0
      - RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - AGENT_TYPE=reviewer
      - TEMPERATURE=0.2   # 低温度=精确判断
    depends_on: [postgres, redis, rabbitmq]
    deploy: { replicas: 3 }  # 审核代理池大小，审核可高密度并行
    restart: unless-stopped

  # === 同步引擎 ===
  sync-engine:
    build: { context: ., dockerfile: Dockerfile.sync }
    environment:
      - DATABASE_URL=postgresql+asyncpg://noveluser:@postgres:5432/novel_db
      - MINIO_ENDPOINT=minio:9000
      - MINIO_ACCESS_KEY=${MINIO_ACCESS_KEY}
      - MINIO_SECRET_KEY=${MINIO_SECRET_KEY}
      - MARKDOWN_ROOT=/app/user_view
    volumes: [markdown_files:/app/user_view]
    depends_on: [postgres, minio]
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  rabbitmq_data:
  minio_data:
  markdown_files:
```

### 2.4 环境变量配置 (`.env` 模板)

```bash
# ============================================================
# 数据库
# ============================================================
DB_PASSWORD=your_strong_password_here_change_me
DATABASE_URL=postgresql+asyncpg://noveluser:@localhost:5432/novel_db

# ============================================================
# LLM 配置
# ============================================================
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1  # 或兼容接口地址
OPENAI_MODEL=gpt-4o  # 生成用
OPENAI_REVIEW_MODEL=gpt-4o  # 审核用（可用更便宜的模型）
OPENAI_EMBEDDING_MODEL=text-embedding-3-large  # API嵌入模型

# ============================================================
# 本地嵌入模型（如不用API）
# ============================================================
EMBEDDING_MODEL=bge-large-zh-v1.5
EMBEDDING_ENDPOINT=http://localhost:8080/embed  # 本地TEI服务地址

# ============================================================
# 缓存
# ============================================================
REDIS_URL=redis://localhost:6379/0

# ============================================================
# 消息队列
# ============================================================
RABBITMQ_URL=amqp://guest:guest@localhost:5672/

# ============================================================
# 对象存储 (MinIO)
# ============================================================
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin_secret_change_me
MINIO_BUCKET=novel-files

# ============================================================
# 应用配置
# ============================================================
ENVIRONMENT=development  # development | production
LOG_LEVEL=DEBUG          # DEBUG | INFO | WARNING | ERROR
SECRET_KEY=your-secret-key-for-jwt-tokens-change_me
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# ============================================================
# 文件路径
# ============================================================
USER_VIEW_DIR=./user_view          # Markdown 用户可见目录
SYSTEM_DATA_DIR=./system_data      # JSON 系统数据目录
SNAPSHOT_DIR=./snapshots           # 版本快照目录
EXPORT_DIR=./exports               # 导出文件目录

# ============================================================
# 日志系统（新增）
# ============================================================
LOG_ROOT=./logs                    # 日志根目录
LOG_LEVEL=INFO                     # 全局日志级别
LOG_JSON_OUTPUT=true               # 生产环境JSON格式；开发环境可设为false
```

### 2.5 项目目录结构

```
novel-creation-system/
├── .env                          # 环境变量（不提交到Git）
├── .env.example                  # 环境变量模板
├── docker-compose.yml            # 生产环境编排
├── docker-compose.dev.yml        # 开发环境编排（简化）
├── Dockerfile.api                # API服务镜像
├── Dockerfile.registry           # 注册表服务镜像
├── Dockerfile.agent-generator    # 生成代理镜像
├── Dockerfile.agent-writer       # 写作代理镜像
├── Dockerfile.agent-reviewer     # 审核代理镜像
├── Dockerfile.sync               # 同步引擎镜像
├── Dockerfile.embedding          # 嵌入模型服务镜像
│
├── src/                          # 后端源码
│   ├── main.py                   # FastAPI 入口
│   ├── config.py                 # 配置加载
│   ├── database/
│   │   ├── engine.py             # 数据库引擎
│   │   ├── models.py             # SQLAlchemy ORM 模型
│   │   ├── migrations/           # Alembic 迁移脚本
│   │   └── crud.py               # CRUD 操作
│   ├── vector_store/
│   │   ├── embeddings.py         # 嵌入模型封装
│   │   ├── search.py             # 向量搜索服务
│   │   └── collections.py        # 向量集合管理
│   ├── modules/                  # 微服务模块实现
│   │   ├── base_module.py        # BaseModule 抽象基类
│   │   ├── registry.py           # 模块注册表
│   │   ├── world_builder/        # 世界观设定模块
│   │   ├── character_builder/    # 人物设定模块
│   │   ├── faction_builder/      # 势力模块
│   │   ├── relation_builder/     # 关系模块
│   │   ├── arc_builder/          # 弧线模块
│   │   ├── item_builder/         # 物品模块
│   │   ├── foreshadow_manager/   # 伏笔追踪模块
│   │   ├── outline_builder/      # 大纲模块
│   │   ├── detail_outline/       # 细纲模块
│   │   ├── manuscript_writer/    # 正文写作模块
│   │   └── theme_engine/         # 主题/灵感模块
│   ├── agents/                   # 子代理实现
│   │   ├── base_agent.py         # 代理基类
│   │   ├── generator_agent.py    # 生成代理
│   │   ├── writer_agent.py       # 写作代理
│   │   ├── reviewer_agent.py     # 审核代理
│   │   └── orchestrator.py       # 编排调度器
│   ├── queue/                    # 消息队列
│   │   ├── producer.py           # 消息发布
│   │   ├── consumer.py           # 消息消费
│   │   └── tasks.py              # Celery/RabbitMQ 任务定义
│   ├── sync/                     # 同步引擎
│   │   ├── engine.py             # 同步引擎核心
│   │   ├── markdown_renderer.py  # JSON→Markdown 渲染
│   │   ├── json_parser.py        # Markdown→JSON 解析
│   │   └── conflict_resolver.py  # 冲突处理
│   ├── review/                   # 审核引擎
│   │   ├── consistency_checker.py    # 一致性检查
│   │   ├── logic_verifier.py         # 逻辑链验证
│   │   ├── literary_reviewer.py      # 文学质感审查
│   │   ├── reader_engagement.py      # 读者吸引力评估
│   │   ├── word_counter.py           # 字数统计
│   │   ├── ai_trace_detector.py      # AI痕迹检测
│   │   └── cross_chapter_checker.py  # 跨章节一致性
│   ├── api/                       # API 路由
│   │   ├── router.py            # 路由汇总
│   │   ├── endpoints/
│   │   │   ├── novels.py        # 小说项目CRUD
│   │   │   ├── characters.py    # 人物管理
│   │   │   ├── world.py         # 世界观管理
│   │   │   ├── outlines.py      # 大纲管理
│   │   │   ├── chapters.py      # 章节/正文管理
│   │   │   ├── foreshadows.py   # 伏笔管理
│   │   │   ├── search.py        # 检索API
│   │   │   ├── sync.py          # 同步状态API
│   │   │   ├── weight.py        # 权重面板API
│   │   │   └── logs.py          # 日志查询API（新增）
│   │   └── middleware/
│   │       ├── auth.py          # 认证中间件
│   │       ├── rate_limit.py    # 流量限制
│   │       ├── error_handler.py # 错误处理
│   │       └── logging_middleware.py  # 请求日志中间件（新增）
│   └── utils/                    # 工具函数
│       ├── id_generator.py      # ID生成器 (CHAR-XXX, FAC-XXX...)
│       ├── prompt_templates.py  # Prompt模板管理
│       ├── llm_client.py        # LLM调用封装
│       ├── text_processor.py    # 文本处理工具
│       ├── logger_config.py     # 日志配置（新增）
│       └── log_rotation.py      # 日志轮转（新增）
│
├── frontend/                     # 前端UI
│   ├── package.json
│   └── src/
│
├── db/
│   ├── init.sql                  # 数据库初始化SQL（完整schema）
│   └── seed.sql                  # 种子数据
│
├── prompts/                      # Prompt模板
│   ├── generation/               # 生成类Prompt
│   ├── review/                   # 审核类Prompt
│   └── tools/                    # 工具类Prompt
│
├── tests/                        # 测试
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── nginx/
│   └── nginx.conf
│
├── scripts/                      # 运维脚本
│   ├── setup_dev.sh              # 开发环境一键搭建
│   ├── init_db.sh                # 数据库初始化
│   ├── backup.sh                 # 备份
│   ├── restore.sh                # 恢复
│   └── log_query.py              # 日志查询CLI（新增）
│
├── logs/                         # 日志目录（gitignore）
│   ├── system/                   # 系统级日志
│   ├── archived/                 # 归档日志
│   └── index.json                # 日志索引
│
├── requirements.txt              # 生产依赖
├── requirements-dev.txt          # 开发依赖
└── README.md
```

---

## 三、分阶段实施流程

实施分为 **6 个大阶段、18 个子步骤**。每步骤有明确的输入、输出、验证标准和回退方案。

---

### 阶段一：基础设施搭建（第 1–4 天）

#### 步骤 1.1：开发环境初始化

**目标**：在开发机器上建立可运行的操作系统级环境。

**操作清单**：

```bash
# 1. 克隆项目代码
git clone <repo-url> && cd novel-creation-system

# 2. 创建虚拟环境
python3.11 -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# 3. 安装开发依赖
pip install -r requirements-dev.txt

# 4. 复制环境变量模板并填写
cp .env.example .env
# 编辑 .env，填入你的 OPENAI_API_KEY 等

# 5. 初始化数据库（SQLite 开发模式）
python -c "
from src.database.engine import init_db
init_db()  # 自动创建所有表
"

# 6. 启动开发服务器
uvicorn src.main:app --reload --port 8000
```

**验证标准**：
- [ ] `GET http://localhost:8000/health` 返回 `{"status": "ok"}`
- [ ] `GET http://localhost:8000/docs` 能打开 Swagger UI
- [ ] 数据库连接正常，所有表已创建
- [ ] 日志无 ERROR 级别输出

**失败回退方案**：

| 失败现象 | 可能原因 | 回退操作 |
|---------|---------|---------|
| pip install 超时 | PyPI 网络问题 | 换国内镜像源 `pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple` |
| 数据库初始化失败 | SQLAlchemy 版本兼容 | `pip install 'sqlalchemy[asyncio]==2.0.25'` 固定版本 |
| uvicorn 启动端口占用 | 进程残留 | `lsof -i :8000 \| kill -9 <PID>` 或换端口 `--port 8001` |
| 日志报错缺少 structlog | 依赖未安装 | `pip install structlog>=24.1.0` |

#### 步骤 1.2：项目骨架搭建

**目标**：完成所有模块的空壳注册，确保模块注册表可查询。

**操作清单**：
1. 实现 `BaseModule` 抽象基类（含 `_create_logger()` 方法）
2. 实现 `ModuleRegistry` 注册表（内存 + 数据库双写）
3. 为 12 个业务模块创建空壳子类（仅实现 `module_id` 和 `register()`)
4. 实现 `/api/modules` GET 接口返回已注册模块列表
5. 为每个模块创建对应的日志文件路径

**验证标准**：
- [ ] `GET /api/modules` 返回 12 个模块，状态均为 `registered`
- [ ] 每个模块有独立的 logger 实例
- [ ] `logs/system/registry.log` 有模块注册记录

#### 步骤 1.3：数据库 Schema 部署

**目标**：在 PostgreSQL 中建好全部 48 张表。

**操作清单**：
1. 使用 `db/init.sql` 初始化完整 schema（含 pgvector 扩展）
2. 运行 Alembic 初始化迁移版本标记
3. 插入种子数据（默认世界观分类、角色模板等）
4. 验证向量索引创建成功

**验证标准**：
- [ ] `\dt` 显示 48 张表（12 模块 × 4 表/模块 + 系统表）
- [ ] `SELECT * FROM modules_registry` 返回 12 行
- [ ] 向量列可通过 `SELECT id, embedding <=> '[...]'::vector` 查询

#### 步骤 1.4：消息队列连通

**目标**：RabbitMQ 四个核心队列就绪，可收发测试消息。

**操作清单**：
1. 启动 RabbitMQ（生产）或使用内存队列（开发）
2. 声明四个队列：`generation_tasks` / `writing_tasks` / `review_tasks` / `sync_events`
3. 编写测试脚本发送一条消息并消费确认
4. 配置死信队列和重试策略

**验证标准**：
- [ ] RabbitMQ Management UI `http://localhost:15672` 可访问
- [ ] 四个队列均存在且消息可正常收发
- [ ] 消息发送到消费延迟 < 100ms

---

### 阶段二：核心模块实现（第 5–15 天）

#### 步骤 2.1：世界观模块（WorldBuilder）

**输入**：小说主题 + 类型标签  
**输出**：8 维度世界观规则集（≥15 条规则）  
**关键点**：
- 五层审查体系内置（物理/社会/魔法/历史/文化）
- 极端测试：5 类压力场景自动验证规则鲁棒性
- 每条规则含 cost/limitation/source 三字段

**验证标准**：
- [ ] 生成规则数 ≥ 15
- [ ] 极端测试通过率 ≥ 80%（5 场景中 ≥ 4 个不矛盾）
- [ ] 规则向量化后可语义检索
- [ ] 所有操作记录到 `logs/{novel_id}/modules/world_builder.log`

#### 步骤 2.2：人物模块（CharacterBuilder）

**输入**：世界观规则 + 角色定位 hint  
**输出**：四层人物档案（身份/心理/能力/特殊）  
**关键点**：
- 心理层必须包含 core_desire ↔ deep_need 矛盾对
- 特殊档案：情感身体地图 + 语气指纹
- 自动计算四维权重评分

**验证标准**：
- [ ] 身份层 5 字段齐全
- [ ] 心理层含 core_desire/deep_need/core_fear 三元组
- [ ] 权重评分输出 tier（S/A/B/C）
- [ ] 情感身体地图情绪数量 ≥ 8

#### 步骤 2.3–2.6：势力 / 关系 / 弧线 / 物品

按相同模式实现，每个模块：
1. 定义数据模型（继承 BaseModule）
2. 编写 Generator（LLM 生成逻辑）
3. 编写 Reviewer（自审逻辑）
4. 注册到 ModuleRegistry
5. 接入日志系统

#### 步骤 2.7：伏笔管理器（ForeshadowManager）

**特殊要求**：
- FORE 档案实体五段式生命周期
- 向量相似度重复检测（阈值 0.85）
- 种下/提醒/回收/完结全状态流转

**验证标准**：
- [ ] 重复伏笔检出率 ≥ 90%（测试集）
- [ ] 状态机转换合法（不允许跳步）
- [ ] 与章节细纲联动：约束文件自动注入伏笔提示

#### 步骤 2.8：大纲构建器（OutlineBuilder）

**输入**：全部设定档案 + 19 环节中的前 8 环输出  
**输出**：三幕结构大纲（含因果链标注）  
**关键点**：
- 因果链验证：每相邻事件必须有 because/since 标注
- 节奏热力图：紧张/舒缓交替比例符合类型惯例
- 三幕结构比例校验（开端 25%/发展 50%/高潮 25% 允许 ±10%）

**验证标准**：
- [ ] 因果断裂点 = 0
- [ ] 节奏热力图无连续 3 段同色
- [ ] 三幕比例在允许范围内

#### 步骤 2.9：细纲模块（DetailOutline）

**输入**：大纲 + 当前章节号 + 已有前文  
**输出**：场景级拆解（POV 分配 / 字数预算 / 约束拉取）  
**关键点**：
- 约束拉取强度校验（避免单场景约束过多导致 LLM 过载）
- 逐场景字数预算 = 章节总预算 × 场景权重

**验证标准**：
- [ ] 场景预算总和 = 章节总预算（误差 ≤ 5%）
- [ ] 每场景 POV 角色明确指定
- [ ] 约束条数 ≤ 8 条/场景

---

### 阶段三：写作与审核流水线（第 16–25 天）

#### 步骤 3.1：正文生成器（ManuscriptWriter）

**核心流程**：约束注入 → 分层生成 → 四层审查 → 修正循环

**约束注入机制**：
1. 从中央档案库拉取当前场景涉及的全部实体最新状态
2. 将硬约束（不可违反的事实）和软约束（风格建议）分别打包
3. 通过 Prompt 模板注入到 system prompt 和 user message

**分层生成**：
- 场景级逐段生成（非整章一次输出）
- 每段生成后即时做一致性检查
- 字数实时统计（累计超预算则触发截断警告）

**验证标准**：
- [ ] 单章生成时间 ≤ 5 分钟（6000 字章节）
- [ ] 字数偏差 ≤ ±10%
- [ ] 每个场景独立日志记录到 `manuscript/CH-XXX_generation.log`

#### 步骤 3.2：四层审查引擎（FourLayerReviewEngine）

| 层级 | 检查项 | 通过阈值 | 必需 |
|------|--------|---------|------|
| L1 设定一致性 | 实体属性矛盾 / 时间线冲突 / 状态不一致 | 0.85 | ✅ |
| L2 逻辑链完整性 | 因果缺失 / 动机不合理 / 行为OOC | 0.80 | ✅ |
| L3 文学质感 | AI 痕迹六特征检测 / 说教感 / 模板化描写 | 0.75 | ✅ |
| L4 读者吸引力 | 节奏热力图 / 信息密度 / 期待感管理 | 0.70 | ❌（不影响通过但影响评级）|

**额外审核维度**：
- 字数校验（独立于四层）
- AI 痕迹检测（6 大特征：同质句式/过渡词依赖/情感解释/功能性对话/模板描写/安全偏见）
- 跨章节一致性（对比前后文）

**验证标准**：
- [ ] 四层审查各自有独立日志文件
- [ ] 每层审查记录 score/threshold/passed/issues_found
- [ ] 不通过时给出具体的 issue 列表和修改建议

#### 步骤 3.3：同步引擎（SyncEngine）

**双向同步**：
- JSON → Markdown：系统数据变更后渲染到用户可见文件
- Markdown → JSON：用户编辑后解析回结构化数据

**SYNC 标记规范**：
```markdown
<!-- SYNC_START entity:type:id -->
字段名: 值
<!-- SYNC_END -->
```

**冲突解决策略**（可配置）：
- `last_write_wins`：最后写入胜出（默认）
- `manual`：人工介入
- `system_priority`：系统数据优先

**验证标准**：
- [ ] JSON→MD 和 MD→JSON 双向同步均正常
- [ ] 冲突时按配置策略处理
- [ ] 同步操作全部记录到 4 个独立日志文件

---

### 阶段四：集成联调（第 26–30 天）

#### 步骤 4.1：端到端流程验证

**验证场景**：从「灵感启动」到「正文修正」完整跑通 19 个环节

**最小可用流程**：
```
用户输入主题 → AI 生成主题分析 → 生成大纲(3幕) → 世界观生成(8维度)
→ 创建3个核心人物 → 建立人物关系 → 生成细纲(第1章)
→ 正文生成(第1章) → 四层审查 → 自动修正 → 输出最终正文
```

**验证标准**：
- [ ] 全流程无人工干预自动完成
- [ ] 每环节输出作为下一环节输入无缝传递
- [ ] 中央档案库数据完整性验证通过
- [ ] 全程日志可追溯（从主题输入到正文输出的完整链路）

#### 步骤 4.2：并发压力测试

**测试场景**：
- 同时生成 3 个不同项目的第 1 章
- 同一项目的生成/审核/同步并行执行
- 消息队列堆积后的消费恢复能力

**验证标准**：
- [ ] 并发 3 项目无数据混淆
- [ ] 消息队列积压消费后无丢失
- [ ] 数据库连接池未耗尽
- [ ] 日志写入不阻塞主流程（异步 Handler 验证）

---

### 阶段五：生产部署（第 31–35 天）

#### 步骤 5.1：Docker 容器化

**操作清单**：
1. 编写所有 7 个 Dockerfile（api/registry/3种agent/sync/embedding）
2. 配置 docker-compose.yml 一键启动全部服务
3. 配置 Nginx 反向代理 + SSL
4. 设置健康检查端点

**验证标准**：
- [ ] `docker compose up -d` 后全部容器 healthy
- [ ] `https://<domain>/health` 返回 ok
- [ ] 日志目录挂载为 Docker Volume（持久化）

#### 步骤 5.2：监控告警接入

**监控项**：
- Prometheus 指标采集（API 延迟/错误率/队列深度）
- Grafana 仪表盘（系统资源/业务指标）
- Loki 日志收集（如部署）
- 告警规则（错误率 > 5% / 队列深度 > 1000 / 磁盘 > 80%）

**验证标准**：
- [ ] Grafana 仪表盘可访问且数据显示正确
- [ ] 告警通知渠道通畅（邮件/钉钉/企微）
- [ ] 日志查询 API 正常工作

---

### 阶段六：验收交付（第 36–38 天）

#### 步骤 6.1：功能验收清单

| 编号 | 验收项 | 标准 | 状态 |
|------|--------|------|------|
| F-001 | 19 个创作环节全覆盖 | 每环节有对应模块/代理 | ⬜ |
| F-002 | 12 个模块全部注册可查 | GET /api/modules 返回 12 个 | ⬜ |
| F-003 | 三种代理池独立运行 | Gen/Wri/Rev 各自消费队列 | ⬜ |
| F-004 | 四层审查引擎生效 | 审查结果含 4 层评分 | ⬜ |
| F-005 | 双向同步正常 | MD 编辑后 DB 自动更新 | ⬜ |
| F-006 | 伏笔防重复 | 相似度 ≥ 0.85 的被拦截 | ⬜ |
| F-007 | 字数控制 | 偏差 ≤ ±10% | ⬜ |
| F-008 | AI 痕迹检测 | 6 大特征覆盖 | ⬜ |
| F-009 | 权重评分输出 | 四维评分 + tier | ⬜ |
| F-010 | 日志系统全覆盖 | 所有组件有结构化日志 | ⬜ |
| F-011 | 日志可查询 | CLI + Web API 均可用 | ⬜ |
| F-012 | 日志轮转正常 | 超大文件自动切割 | ⬜ |

#### 步骤 6.2：交付物清单

| 交付物 | 格式 | 位置 |
|--------|------|------|
| 完整源代码 | Git 仓库 | `<repo-url>` |
| 数据库 Schema SQL | `.sql` 文件 | `db/init.sql` |
| Docker 编排文件 | YAML | `docker-compose.yml` |
| 环境变量模板 | `.env.example` | 项目根目录 |
| API 文档 | Swagger UI | `GET /docs` |
| 日志系统设计文档 | Markdown | 本文档附录 A–I |
| 部署运维手册 | Markdown | `docs/operations.md` |
| Prompt 模板全集 | `.txt` 文件 | `prompts/` 目录 |

---

## 四、各环节失败回退方案

### 4.1 通用回退原则

| 故障类型 | 检测方式 | 默认回退 | 人工介入条件 |
|---------|---------|---------|------------|
| LLM API 超时 | 调用 > 30s | 自动重试 3 次（指数退避）| 重试全部失败 |
| LLM 返回格式错误 | JSON 解析失败 | 重新 prompt（加格式约束）| 连续 2 次失败 |
| 数据库连接丢失 | 操作异常 | 自动重连（最多 5 次）| 30 秒内无法恢复 |
| 消息队列堆积 | 深度 > 1000 | 自动扩容消费者 | 堆积持续 > 10min |
| 审核一直不通过 | 同章节 > 3 次 | 降低非必需层阈值 | 必需层仍不通过 |
| 同步冲突 | 双向修改同一字段 | 按策略自动解决 | strategy=manual 时 |

### 4.2 各模块特定回退

| 模块 | 典型故障 | 回退方案 |
|------|---------|---------|
| WorldBuilder | 规则间矛盾 > 30% | 调低创意温度(0.85→0.7)，增加示例 few-shot |
| CharacterBuilder | 心理层三元组不完整 | 拆为两次 LLM 调用（先 desire+need，后 fear）|
| ForeshadowManager | 重复检测误报 | 调低相似度阈值(0.85→0.80) |
| OutlineBuilder | 因果链断裂点多 | 减少并行事件数，改为更线性结构 |
| ManuscriptWriter | 字数严重超标 | 触发截断逻辑，对超出部分摘要化 |
| FourLayerReviewEngine | LLM 审核自身不稳定 | 切换到规则引擎兜底（正则/模板匹配）|
| SyncEngine | 冲突频繁 | 暂时锁定实体（禁止用户编辑），批量处理后解锁 |

### 4.3 数据恢复策略

| 损失范围 | 恢复方式 | RTO（恢复时间目标）|
|---------|---------|------------------|
| 单章节正文 | 从 manuscript 日志重建或重新生成 | < 5 min |
| 单个人物档案 | 从 change_log 回滚到最近一致版本 | < 10 min |
| 整个项目元数据 | 从每日快照恢复 | < 30 min |
| 数据库完全损坏 | 从备份 + WAL 恢复 | < 2 hour（需运维介入）|

---

## 五、性能优化与监控

### 5.1 性能基线指标

| 指标 | 目标值 | 测量方法 |
|------|--------|---------|
| API 平均响应时间 (P50) | < 200ms | Prometheus histogram |
| API P99 响应时间 | < 2000ms | Prometheus histogram |
| 单章生成耗时 | < 300s (6000字) | manuscript 日志 duration_ms |
| 单章审核耗时 | < 120s | review 日志 duration_ms |
| 同步操作延迟 | < 500ms | sync 日志 duration_ms |
| LLM 调用成功率 | > 99% | llm_calls.log 统计 |
| 数据库查询 P99 | < 100ms | database.log 慢查询统计 |
| 日志写入延迟对 API 影响 | < 5ms | 压力测试对比 |

### 5.2 优化手段

| 瓶颈 | 优化方案 | 预期效果 |
|------|---------|---------|
| LLM 调用排队 | 并行代理池 + 优先级队列 | 吞吐量 3× |
| 数据库慢查询 | pgvector 索引优化 + 读写分离 | 查询 P99 ↓ 60% |
| 同步频繁触发 | 批量合并 + debounce 300ms | 同步次数 ↓ 70% |
| 审核串行瓶颈 | 非必需层并行 + 结果缓存 | 审核耗时 ↓ 50% |
| 日志 I/O 阻塞 | 异步 Handler + 内存缓冲 | 主流程零阻塞 |
| 向量嵌入计算 | 批量嵌入 + 缓存 | 嵌入调用 ↓ 80% |

### 5.3 监控仪表盘

**Grafana 核心面板**：

| 面板 | 查询 | 告警阈值 |
|------|------|---------|
| API 请求速率 | `rate(http_requests_total[5m])` | — |
| API 错误率 | `rate(http_errors[5m]) / rate(http_requests_total[5m])` | > 5% |
| 队列深度 | `rabbitmq_queue_messages` | > 1000 |
| LLM 费用/小时 | `sum(cost_usd)` from llm_calls.log | > $10/hour |
| 章节生成吞吐 | `count(chapter_completed)` | — |
| 审核通过率 | `passed/total` from review logs | < 80% |
| 日志量趋势 | `sum by (level) (log_entries[5m])` | — |
| 磁盘使用率 | `df_used_percent` | > 80% |

---

## 六、验收标准与交付物

### 6.1 功能验收（已在 6.1 节详述，共 12 项）

### 6.2 非功能验收

| 编号 | 验收项 | 标准 |
|------|--------|------|
| NF-001 | 可用性 | 系统 7×24 可用，计划内停机 < 4h/月 |
| NF-002 | 并发支持 | ≥ 3 个小说项目同时创作互不干扰 |
| NF-003 | 数据安全 | 敏感信息（API Key/密码）不出现在日志中 |
| NF-004 | 审计追踪 | 所有数据变更可在审计日志中追溯到操作者和时间 |
| NF-005 | 日志保留 | 操作日志 ≥ 90 天，审计日志永久保留 |
| NF-006 | 恢复能力 | 任意单章节可在 5 分钟内从日志/快照恢复 |
| NF-007 | 性能 | API P99 < 2s，单章生成 < 5min |

### 6.3 交付物清单（已在 6.2 节详述，共 8 项）

---

# 第二部分：日志系统专项设计（附录 A–I）

> **本部分为《AI 小说创作系统完整实施方案》的必要组成部分。**
> **目标：系统中所有项目、模块、代理、中间件均有结构化日志输出，
> 统一存储到专用日志文件夹，支持后续审计、排障、回溯。**

---

## 附录 A：日志系统总体架构

### A.1 设计原则

| 原则 | 定义 | 实现方式 |
|------|------|---------|
| 全覆盖 | 所有可执行单元（模块/代理/中间件/同步引擎）都必须输出日志 | BaseModule / BaseAgent 强制要求 logger 实例 |
| 结构化 | 日志不是自由文本，而是 JSON 结构化记录，便于机器解析和检索 | 使用 `structlog` 或自定义 JSON formatter |
| 分级 | 不同严重程度的信息走不同级别，便于过滤 | DEBUG / INFO / WARNING / ERROR / CRITICAL 五级 |
| 可追溯 | 每条日志必须携带足够的上下文（谁/什么/何时/为什么） | 统一日志上下文字段规范 |
| 不可篡改 | 写入的日志文件不应被正常业务逻辑修改 | 追加写模式 + 文件权限控制 |
| 性能隔离 | 日志写入不能阻塞主业务流程 | 异步写入 + 缓冲区 |

### A.2 架构层次图

```
┌─────────────────────────────────────────────────────────────┐
│                     日志生产者 (Producers)                      │
│                                                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │ 模块日志  │ │ 代理日志  │ │ API日志   │ │ 同步日志  │        │
│  │(12模块)  │ │(Gen/Wri/ │ │(请求/响应)│ │(JSON↔MD) │        │
│  │          │ │ Rev)     │ │          │ │          │        │
│  └─────┬────┘ └─────┬────┘ └─────┬────┘ └─────┬────┘        │
│        │            │           │           │                │
└────────┼────────────┼───────────┼───────────┼────────────────┘
         │            │           │           │
         ▼            ▼           ▼           ▼
┌─────────────────────────────────────────────────────────────┐
│                   日志收集层 (Collection)                      │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Structured Logger (Python logging)       │   │
│  │  • 自定义 Formatter → JSON 输出                       │   │
│  │  • Context 注入器 → 自动附加 request_id / novel_id    │   │
│  │  • Filter → 敏感信息脱敏                              │   │
│  └──────────────────────┬───────────────────────────────┘   │
│                         │                                    │
│  ┌──────────────────────▼───────────────────────────────┐   │
│  │              Async File Handler (异步写入)             │   │
│  │  • 内存缓冲区 (batch_size=50 或 flush_interval=5s)   │   │
│  │  • 写入时按级别路由到不同文件                          │   │
│  └──────────────────────┬───────────────────────────────┘   │
│                         │                                    │
└─────────────────────────┼────────────────────────────────────┘
                          │
         ┌────────────────┼────────────────┐
         ▼                ▼                ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ logs/       │  │ logs/       │  │ logs/       │
│ modules/    │  │ agents/     │  │ api/        │
│ (12个模块)  │  │ (3种代理)   │  │ (请求日志)  │
└─────────────┘  └─────────────┘  └─────────────┘
         │                │                │
         ▼                ▼                ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ logs/       │  │ logs/       │  │ logs/       │
│ sync/       │  │ system/     │  │ audit/      │
│ (同步引擎)  │  │ (基础设施)  │  │ (审计日志)  │
└─────────────┘  └─────────────┘  └─────────────┘
```

### A.3 日志目录总览

```
logs/                                   # ← 日志根目录（所有项目共享）
│
├── {novel_id}/                         # ← 按 novel_id 隔离的项目级子目录
│   ├── modules/
│   │   ├── world_builder.log          # 世界观模块日志
│   │   ├── character_builder.log      # 人物模块日志
│   │   ├── faction_builder.log        # 势力模块日志
│   │   ├── relation_builder.log       # 关系模块日志
│   │   ├── arc_builder.log            # 弧线模块日志
│   │   ├── item_builder.log           # 物品模块日志
│   │   ├── foreshadow_manager.log     # 伏笔模块日志
│   │   ├── outline_builder.log        # 大纲模块日志
│   │   ├── detail_outline.log         # 细纲模块日志
│   │   ├── manuscript_writer.log      # 正文模块日志
│   │   ├── theme_engine.log           # 主题/灵感模块日志
│   │   └── novel_archive.log          # 档案/简介模块日志
│   │
│   ├── agents/
│   │   ├── generator.log              # 生成代理池日志
│   │   ├── writer.log                 # 写作代理池日志
│   │   └── reviewer.log               # 审核代理池日志
│   │
│   ├── review/
│   │   ├── consistency.log            # 一致性审查日志
│   │   ├── logic.log                  # 逻辑链审查日志
│   │   ├── literary.log               # 文学质感审查日志
│   │   ├── reader_engagement.log      # 读者吸引力审查日志
│   │   ├── word_count.log             # 字数校验日志
│   │   ├── ai_trace.log               # AI痕迹检测日志
│   │   └── cross_chapter.log          # 跨章节一致性日志
│   │
│   ├── sync/
│   │   ├── json_to_markdown.log       # JSON→Markdown 同步日志
│   │   ├── markdown_to_json.log       # Markdown→JSON 同步日志
│   │   ├── conflict.log               # 冲突检测与处理日志
│   │   └── cascade_update.log         # 联动更新追踪日志
│   │
│   ├── manuscript/
│   │   ├── CH-001_generation.log      # 第1章生成过程全量日志
│   │   ├── CH-001_review.log          # 第1章审核过程全量日志
│   │   ├── CH-002_generation.log
│   │   ├── CH-002_review.log
│   │   └── ...                        # 每章独立文件
│   │
│   ├── audit/
│   │   ├── entity_changes.log         # 所有实体变更审计日志
│   │   ├── user_actions.log           # 用户操作审计日志
│   │   ├── access.log                 # 访问审计日志
│   │   └── permission_changes.log     # 权限变更审计日志
│   │
│   └── snapshots/
│       ├── snapshot_20260528_183000.jsonl  # 版本快照元数据
│       └── ...
│
├── system/                             # ← 系统级日志（不按项目隔离）
│   ├── api_requests.log               # 所有 HTTP API 请求/响应
│   ├── database.log                  # 数据库操作（慢查询/错误）
│   ├── cache.log                     # Redis 缓存命中/未命中
│   ├── queue.log                     # RabbitMQ 消息收发
│   ├── vector_store.log              # pgvector 向量操作
│   ├── llm_calls.log                 # LLM API 调用记录（含 token/费用）
│   ├── embedding_service.log         # 嵌入模型服务调用
│   ├── registry.log                  # 模块注册表事件
│   ├── error.log                     # 全局错误汇总（所有 CRITICAL + ERROR）
│   └── startup.log                   # 服务启动/关闭/配置加载
│
├── archived/                           # ← 归档日志（超过保留期的压缩包）
│   ├── 2026-04.tar.gz
│   ├── 2026-05-week1.tar.gz
│   └── ...
│
└── index.json                         # ← 日志索引文件（加速查找）
```

---

## 附录 B：日志目录结构与命名规范

### B.1 文件命名规则

```
{component}_{detail}.{date}.{ext}

其中：
  component: 组件名称（小写下划线）
  detail: 可选的细分标识（如章节号、代理实例ID）
  date: 可选（按日轮转时自动追加；不轮转则无此后缀）
  ext: .log（纯文本JSON行）或 .jsonl（明确标识JSON Lines格式）

示例：
  world_builder.log                    # 世界观模块当日日志（自动轮转后变为 world_builder.2026-05-28.log）
  generator_agent_001.log              # 生成代理实例 001 的日志
  CH-028_generation.log                # 第28章生成过程的专属日志
  entity_changes.audit.log            # 审计日志（特殊标记）
```

### B.2 目录创建时机

| 目录 | 创建时机 | 负责方 |
|------|---------|--------|
| `logs/` | 应用首次启动时 | `src/utils/logger_config.py` 初始化函数 |
| `logs/{novel_id}/` | 创建小说项目时 | 项目 CRUD 服务 |
| `logs/{novel_id}/modules/` | 首次使用某模块时 | 各模块 `on_register()` 回调 |
| `logs/{novel_id}/agents/` | 代理启动时 | 各 Agent `start()` 方法 |
| `logs/{novel_id}/review/` | 首次执行审查时 | 审核引擎初始化 |
| `logs/{novel_id}/sync/` | 首次触发同步时 | 同步引擎初始化 |
| `logs/{novel_id}/manuscript/` | 生成每章正文时 | 正文模块按需创建 |
| `logs/{novel_id}/audit/` | 应用启动时 | 审计日志服务初始化 |
| `logs/system/` | 应用启动时 | 系统日志服务初始化 |
| `logs/archived/` | 应用启动时 | 日志归档任务初始化 |
| `logs/index.json` | 应用启动时 + 每次写入后更新 | 索引维护器 |

---

## 附录 C：各组件日志规范

### C.1 模块日志（12 个业务模块）

每个模块必须通过 `BaseModule` 基类获取专用的 logger 实例：

```python
# src/modules/base_module.py — 新增日志相关代码
import structlog
from pathlib import Path
from typing import Optional
import json

LOG_ROOT = Path("logs")  # 可通过环境变量 LOG_ROOT 覆盖


class BaseModule(ABC):
    """所有模块的抽象基类 — 含强制日志"""

    def __init__(self, novel_id: str = None):
        self._novel_id = novel_id
        self._logger = self._create_logger()

        # 注册时自动记录
        self._logger.info("module_initialized",
            module_id=self.module_id,
            module_name=self.module_name,
            version=self.version,
            module_type=self.module_type.value,
            dependencies=self.dependencies
        )

    def _create_logger(self) -> structlog.BoundLogger:
        """为当前模块创建带固定上下文的绑定日志器。
        每条日志自动携带：module_id, module_name, novel_id, timestamp"""
        log_dir = LOG_ROOT / self._novel_id / "modules" if self._novel_id else LOG_ROOT / "system"
        log_dir.mkdir(parents=True, exist_ok=True)

        log_file = log_dir / f"{self.module_id}.log"

        return structlog.get_logger().bind(
            module_id=self.module_id,
            module_name=self.module_name,
            novel_id=self._novel_id or "system",
            component_type="module"
        )

    def log_operation(self, operation: str, **kwargs):
        """标准化操作日志接口。所有模块的业务操作都应通过此方法记录。

        参数:
            operation: 操作名称字符串（如 "character_created", "rule_modified"）
            **kwargs: 操作相关的任意结构化数据
        """
        self._logger.info("module_operation",
            operation=operation,
            **kwargs
        )
```

**世界观模块日志示例**：

```python
# src/modules/world_builder/generator.py — 日志使用示例

class WorldBuilderGenerator(BaseModule):
    module_id = "world_builder"
    module_name = "世界观设定生成器"
    version = "1.0.0"
    module_type = ModuleType.GENERATOR

    async def generate_rule(self, novel_id: str, rule_spec: dict) -> dict:
        rule_id = generate_id("RULE")

        self.log_operation(
            "rule_generation_started",
            rule_id=rule_id,
            rule_name=rule_spec.get("name", "未命名"),
            category=rule_spec.get("category"),
            input_summary={k: v for k, v in rule_spec.items()
                          if k not in ["full_description"]}  # 不记录全文避免日志过大
        )

        try:
            result = await self.llm.call(prompt=..., temperature=0.85)

            self.log_operation(
                "rule_generation_completed",
                rule_id=rule_id,
                rule_name=result["name"],
                tokens_used=result["usage"]["total_tokens"],
                cost_usd=result["usage"].get("cost_usd", 0),
                duration_ms=result["duration_ms"],
                has_cost=True,
                has_limitation=bool(result.get("limitation")),
                has_source=bool(result.get("source"))
            )

            return result

        except Exception as e:
            self._logger.error("rule_generation_failed",
                rule_id=rule_id,
                error_type=type(e).__name__,
                error_message=str(e),
                error_traceback=traceback.format_exc()[:2000]  # 截断超长 traceback
            )
            raise

    async def run_extreme_test(self, novel_id: str, rule_id: str) -> dict:
        self.log_operation(
            "extreme_testing_started",
            rule_id=rule_id,
            test_type="five_scenario_pressure"
        )

        results = []
        for scenario_num in range(1, 6):
            scenario_result = await self._test_single_scenario(rule_id, scenario_num)
            results.append(scenario_result)

            # 每个场景单独记录一条日志
            self.log_operation(
                "extreme_test_scenario_completed",
                rule_id=rule_id,
                scenario_number=scenario_num,
                scenario_type=scenario_result["type"],
                rule_holds=scenario_result["rule_holds"],
                issues_found=len(scenario_result.get("issues", []))
            )

        # 汇总结果
        passed_count = sum(1 for r in results if r["rule_holds"])
        total_issues = sum(len(r.get("issues", [])) for r in results)

        self.log_operation(
            "extreme_testing_completed",
            rule_id=rule_id,
            total_scenarios=5,
            scenarios_passed=passed_count,
            scenarios_failed=5 - passed_count,
            total_issues_found=total_issues,
            overall_verdict="PASS" if passed_count >= 4 else "NEEDS_REVIEW"
        )

        return {"scenarios": results, "summary": {...}}
```

**人物模块日志示例**：

```python
# src/modules/character_builder/generator.py

class CharacterBuilderGenerator(BaseModule):
    module_id = "character_builder"
    module_name = "人物设定生成器"

    async def generate_character(self, novel_id: str, spec: dict) -> dict:
        char_id = generate_id("CHAR")

        self.log_operation(
            "character_generation_started",
            char_id=char_id,
            spec_type=spec.get("type", "custom"),
            role_hint=spec.get("role_hint"),
            requested_tier=spec.get("weight_tier")
        )

        # === 身份层生成 ===
        identity = await self._generate_identity_layer(spec)
        self.log_operation(
            "character_layer_generated",
            char_id=char_id,
            layer="identity",
            fields_generated=["name", "age", "appearance", "social_identity", "family_background"]
        )

        # === 心理层生成 ===
        psychology = await self._generate_psychology_layer(spec, identity)
        self.log_operation(
            "character_layer_generated",
            char_id=char_id,
            layer="psychology",
            fields_generated=["core_desire", "deep_need", "core_fear", "persona_vs_self", "moral_bottom_line"],
            core_desire_preview=psychology["core_desire"][:50] + "..."  # 只记录前50字符预览
        )

        # === 特殊档案生成 ===
        emotional_body_map = await self._generate_emotional_body_map(psychology)
        self.log_operation(
            "character_special_profile_generated",
            char_id=char_id,
            profile="emotional_body_map",
            emotion_count=len(emotional_body_map),
            emotions=list(emotional_body_map.keys())
        )

        voice_fingerprint = await self._generate_voice_fingerprint(identity, psychology)
        self.log_operation(
            "character_special_profile_generated",
            char_id=char_id,
            profile="voice_fingerprint",
            vocabulary_pool_size=len(voice_fingerprint.get("vocabulary_pool", [])),
            forbidden_expressions_count=len(voice_fingerprint.get("forbidden_expressions", []))
        )

        # === 权重计算 ===
        weight_result = await self.weight_calculator.calculate(novel_id, char_id)
        self.log_operation(
            "character_weight_calculated",
            char_id=char_id,
            total_score=weight_result["total_score"],
            tier=weight_result["tier"],
            breakdown=weight_result["breakdown"]
        )

        # === 完成 ===
        self.log_operation(
            "character_generation_completed",
            char_id=char_id,
            char_name=identity["name"],
            weight_tier=weight_result["tier"],
            layers_completed=["identity", "psychology", "ability", "special_profiles"],
            total_tokens=self._session_tokens,
            estimated_cost_usd=self._session_cost
        )

        return {"id": char_id, **identity, **psychology, ...}
```

### C.2 代理日志（Generator / Writer / Reviewer）

每个代理实例有独立日志文件，记录任务接收、执行、结果回调的全过程：

```python
# src/agents/base_agent.py — 新增日志代码

class BaseAgent(ABC):
    """子代理基类 — 含完整任务生命周期日志"""

    def __init__(self, agent_id: str, config: Dict[str, Any], novel_id: str):
        self.agent_id = agent_id
        self.novel_id = novel_id
        self.config = config

        # 创建代理专属日志
        self._log_dir = Path(f"logs/{novel_id}/agents")
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._logger = self._create_agent_logger()

        # 任务计数器
        self._task_counter = 0
        self._success_counter = 0
        self._failure_counter = 0

    def _create_agent_logger(self):
        log_file = self._log_dir / f"{self.agent_type}_{self.agent_id.split('_')[-1]}.log"
        return structlog.get_logger().bind(
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            novel_id=self.novel_id,
            component_type="agent"
        )

    async def execute_task(self, task: Dict[str, Any]) -> TaskResult:
        """执行单个任务，全程记录日志。"""
        task_id = task["task_id"]
        task_type = task["task_type"]
        self._task_counter += 1

        start_time = time.time()

        # === 任务接收 ===
        self._logger.info("task_received",
            task_id=task_id,
            task_type=task_type,
            queue_wait_time_ms=int((time.time() - task.get("enqueue_time", start_time)) * 1000),
            payload_keys=list(task.get("payload", {}).keys()),
            priority=task.get("priority", "normal")
        )

        try:
            # === 任务开始执行 ===
            self._logger.info("task_execution_started",
                task_id=task_id,
                task_type=task_type,
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )

            # 调用实际执行逻辑
            result = await self._do_execute(task)

            duration_ms = int((time.time() - start_time) * 1000)
            self._success_counter += 1

            # === 任务成功完成 ===
            self._logger.info("task_completed_success",
                task_id=task_id,
                task_type=task_type,
                duration_ms=duration_ms,
                result_preview=str(result.result)[:200] if result.result else None,
                tokens_used=getattr(result, 'tokens_used', None),
                metrics=result.metrics
            )

            # 发送结果回调
            await self._send_callback(result)
            self._logger.debug("callback_sent", task_id=task_id)

            return result

        except LLMRateLimitError as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self._failure_counter += 1
            self._logger.warning("task_rate_limited",
                task_id=task_id,
                task_type=task_type,
                duration_ms=duration_ms,
                retry_after_seconds=e.retry_after,
                will_retry=True
            )
            # 重试逻辑...

        except LLMAPITimeoutError as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self._failure_counter += 1
            self._logger.error("task_llm_timeout",
                task_id=task_id,
                task_type=task_type,
                duration_ms=duration_ms,
                timeout_seconds=e.timeout,
                attempt=self._current_retry + 1,
                max_retries=3
            )
            raise

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self._failure_counter += 1
            self._logger.error("task_failed",
                task_id=task_id,
                task_type=task_type,
                duration_ms=duration_ms,
                error_type=type(e).__name__,
                error_message=str(e),
                error_traceback=traceback.format_exc()[-1500:]  # 最后1500字符
            )

            result = TaskResult(
                task_id=task_id,
                success=False,
                error=f"{type(e).__name__}: {str(e)}",
                duration_ms=duration_ms,
                agent_id=self.agent_id
            )
            await self._send_callback(result)
            return result

    async def stop(self):
        """停止代理时输出汇总统计"""
        self._logger.info("agent_stopping",
            agent_id=self.agent_id,
            uptime_seconds=int(time.time() - self._start_time),
            total_tasks_received=self._task_counter,
            total_succeeded=self._success_counter,
            total_failed=self._failure_counter,
            success_rate=round(self._success_counter / max(1, self._task_counter), 4)
        )
        self._is_running = False
```

**写作代理额外日志——正文生成的逐场景记录**：

```python
# src/agents/writer_agent.py

class WriterAgent(BaseAgent):
    agent_type = "writer"

    async def _do_execute(self, task: Dict) -> TaskResult:
        if task["task_type"] == "chapter_writing":
            return await self._write_chapter(task)

    async def _write_chapter(self, task: Dict) -> TaskResult:
        chapter_number = task["payload"]["chapter_number"]
        novel_id = task["payload"]["novel_id"]

        # 创建本章专属日志文件
        chapter_log_dir = Path(f"logs/{novel_id}/manuscript")
        chapter_log_dir.mkdir(parents=True, exist_ok=True)
        chapter_logger = structlog.get_logger().bind(
            chapter_number=chapter_number,
            novel_id=novel_id,
            component_type="manuscript"
        )

        constraint_file = task["payload"]["constraint_file"]
        outline = task["payload"].get("outline_data", {})
        scenes = outline.get("scenes", [])

        chapter_logger.info("chapter_writing_started",
            chapter_number=chapter_number,
            scene_count=len(scenes),
            word_budget=constraint_file.get("word_budget", {}).get("total", 0),
            characters_involved=[c["id"] for c in constraint_file.get("characters", [])],
            foreshadows_to_plant=[f["id"] for f in constraint_file.get("foreshadows", {}).get("to_plant", [])],
            foreshadows_to_reveal=[f["id"] for f in constraint_file.get("foreshadows", {}).get("to_reveal", [])]
        )

        full_text = ""
        scene_texts = []

        for idx, scene in enumerate(scenes):
            scene_start = time.time()
            chapter_logger.info("scene_generation_started",
                chapter_number=chapter_number,
                scene_index=idx,
                scene_type=scene.get("type", "unknown"),
                pov_character=scene.get("pov_char_id"),
                word_budget=scene.get("word_budget", 0),
                location=scene.get("location_id")
            )

            scene_text = await self._generate_scene(scene, constraint_file)
            scene_duration = int((time.time() - scene_start) * 1000)
            scene_word_count = len(scene_text)

            scene_texts.append(scene_text)

            chapter_logger.info("scene_generation_completed",
                chapter_number=chapter_number,
                scene_index=idx,
                word_count=scene_word_count,
                budget=scene.get("word_budget", 0),
                budget_deviation_pct=round(
                    (scene_word_count - scene.get("word_budget", 0))
                    / max(1, scene.get("word_budget", 0)) * 100, 1
                ) if scene.get("word_budget") else None,
                duration_ms=scene_duration,
                ai_trace_score=None  # 后续审核填充
            )

            full_text += scene_text + "\n\n"

        total_word_count = len(full_text)
        total_duration = int((time.time() - task.get("start_time", time.time())) * 1000)

        chapter_logger.info("chapter_writing_completed",
            chapter_number=chapter_number,
            total_scenes=len(scenes),
            total_word_count=total_word_count,
            total_budget=constraint_file.get("word_budget", {}).get("total", 0),
            budget_deviation_pct=round(
                (total_word_count - constraint_file.get("word_budget", {}).get("total", 0))
                / max(1, constraint_file.get("word_budget", {}).get("total", 0)) * 100, 1
            ) if constraint_file.get("word_budget", {}).get("total") else None,
            total_duration_ms=total_duration,
            avg_words_per_scene=round(total_word_count / max(1, len(scenes))),
            will_proceed_to_review=True
        )

        return TaskResult(
            task_id=task["task_id"],
            success=True,
            result={"text": full_text, "word_count": total_word_count},
            duration_ms=total_duration,
            agent_id=self.agent_id,
            metrics={
                "scenes": len(scenes),
                "words": total_word_count,
                "tokens_estimate": total_word_count * 1.5  # 粗估
            }
        )
```

### C.3 审核日志（四层审查 + AI 痕迹检测）

每一层审查都有独立日志文件，记录审查输入、评分细节、发现的问题：

```python
# src/review/four_layer_reviewer.py — 审核日志增强

class FourLayerReviewEngine:
    """四层审查引擎 — 每层独立日志"""

    def __init__(self, novel_id: str):
        self.novel_id = novel_id
        self.review_log_dir = Path(f"logs/{novel_id}/review")
        self.review_log_dir.mkdir(parents=True, exist_ok=True)

        # 每层一个 logger
        self._loggers = {
            "consistency": self._make_review_logger("consistency"),
            "logic": self._make_review_logger("logic"),
            "literary": self._make_review_logger("literary"),
            "reader_engagement": self._make_review_reader_engagement_logger(),
            "ai_trace": self._make_ai_trace_logger()
        }

    def _make_review_logger(self, layer_name: str):
        log_file = self.review_log_dir / f"{layer_name}.log"
        return structlog.get_logger().bind(
            layer=layer_name,
            novel_id=self.novel_id,
            component_type="review"
        )

    async def review_chapter(self, chapter_number: str, manuscript_text: str,
                              constraint_file: dict) -> dict:

        overall_start = time.time()
        report = {"layers": {}, "issues": [], "ai_trace": {}}

        for layer_id, layer_name, threshold, required in self.LAYERS:
            layer_start = time.time()
            logger = self._loggers.get(layer_id)

            logger.info("review_layer_started",
                chapter_number=chapter_number,
                layer=layer_id,
                required=required,
                manuscript_word_count=len(manuscript_text),
                constraint_entities=self._count_constraint_entities(constraint_file)
            )

            try:
                layer_result = await self._run_layer(layer_id, manuscript_text, constraint_file)
                layer_duration = int((time.time() - layer_start) * 1000)

                logger.info("review_layer_completed",
                    chapter_number=chapter_number,
                    layer=layer_id,
                    score=layer_result["score"],
                    threshold=threshold,
                    passed=layer_result["score"] >= threshold,
                    issues_found=len(layer_result.get("issues", [])),
                    issues_by_severity=self._count_issues_by_severity(layer_result),
                    duration_ms=layer_duration,
                    reviewer_model=self._get_reviewer_model(layer_id),
                    tokens_used=layer_result.get("tokens_used")
                )

                # 记录每个问题的摘要（不记录全文）
                for issue in layer_result.get("issues", []):
                    logger.info("issue_detected",
                        chapter_number=chapter_number,
                        layer=layer_id,
                        issue_severity=issue.get("severity"),
                        issue_category=issue.get("category"),
                        issue_preview=issue.get("description", "")[:100],
                        suggestion_preview=issue.get("suggestion", "")[:100],
                        related_entities=issue.get("related_entities", [])
                    )

                report["layers"][layer_id] = layer_result

                if layer_result["score"] < threshold and required:
                    logger.warning("required_layer_failed_terminating",
                        chapter_number=chapter_number,
                        layer=layer_id,
                        score=layer_result["score"],
                        threshold=threshold,
                        gap=round(threshold - layer_result["score"], 3)
                    )
                    report["termination_reason"] = f"Required layer '{layer_name}' failed"
                    break

            except Exception as e:
                logger.error("review_layer_error",
                    chapter_number=chapter_number,
                    layer=layer_id,
                    error_type=type(e).__name__,
                    error_message=str(e)
                )
                report["layers"][layer_id] = {"score": 0, "error": str(e)}
                if required:
                    break

        # AI 痕迹独立记录
        ai_trace_logger = self._loggers["ai_trace"]
        ai_result = await self.ai_trace_detector.detect(manuscript_text)

        ai_trace_logger.info("ai_trace_scan_completed",
            chapter_number=chapter_number,
            manuscript_word_count=len(manuscript_text),
            total_traces_found=len(ai_result.get("detected_traces", [])),
            traces_by_category={
                cat: len([t for t in ai_result.get("detected_traces", []) if t["category"] == cat])
                for cat in [
                    "homogeneous_sentence_structure",
                    "transition_word_dependency",
                    "emotion_explanation",
                    "functional_dialogue",
                    "template_description",
                    "safety_bias"
                ]
            },
            overall_confidence=ai_result.get("confidence", 0),
            verdict="CLEAN" if len(ai_result.get("detected_traces", [])) == 0 else "TRACE_DETECTED"
        )

        report["ai_trace"] = ai_result

        total_duration = int((time.time() - overall_start) * 1000)

        # 汇总日志
        summary_logger = structlog.get_logger().bind(
            novel_id=self.novel_id, chapter_number=chapter_number, component_type="review_summary"
        )
        summary_logger.info("chapter_review_completed",
            chapter_number=chapter_number,
            total_layers_executed=len(report["layers"]),
            overall_score=report.get("overall_score", 0),
            passed=report.get("passed", False),
            total_issues=len(report.get("issues", [])),
            termination_reason=report.get("termination_reason"),
            total_duration_ms=total_duration,
            ai_trace_verdict="CLEAN" if not ai_result.get("detected_traces") else "NEEDS_POLISH"
        )

        return report
```

### C.4 同步引擎日志

双向同步是数据一致性的关键环节，必须有最详细的日志：

```python
# src/sync/engine.py — 同步日志增强

class SyncEngine:
    """双向同步引擎 — 完整操作日志"""

    def __init__(self, db, markdown_root: str, strategy: str = "last_write_wins"):
        self.sync_log_dir = Path(f"logs/{db.current_novel_id}/sync") if db.current_novel_id else Path("logs/system/sync")
        self.sync_log_dir.mkdir(parents=True, exist_ok=True)

        self._j2m_logger = self._make_sync_logger("json_to_markdown")  # JSON→MD
        self._m2j_logger = self._make_sync_logger("markdown_to_json")  # MD→JSON
        self._conflict_logger = self._make_sync_logger("conflict")     # 冲突
        self._cascade_logger = self._make_sync_logger("cascade_update") # 联动

    async def sync_json_to_markdown(self, entity_type: str, entity_id: str):
        sync_id = f"sync_{uuid.uuid4().hex[:8]}"
        start = time.time()

        self._j2m_logger.info("sync_j2m_started",
            sync_id=sync_id,
            entity_type=entity_type,
            entity_id=entity_id,
            trigger=traceback.extract_stack()[-3].name  # 触发来源函数名
        )

        try:
            entity_data = await self.db.get_entity(entity_type, entity_id)
            md_path = self.markdown_root / entity_type / f"{entity_id}.md"

            changes_made = 0
            fields_updated = []

            for field_path, value in self._extract_sync_fields(entity_data):
                old_value = self._read_existing_sync_field(md_path, entity_id, field_path)
                if old_value != value:
                    changes_made += 1
                    fields_updated.append(field_path)

                    self._j2m_logger.debug("field_synced",
                        sync_id=sync_id,
                        entity_id=entity_id,
                        field_path=field_path,
                        old_value_preview=(old_value or "")[:80],
                        new_value_preview=value[:80],
                        changed=True
                    )

            md_path.write_text(new_content, encoding="utf-8")

            duration = int((time.time() - start) * 1000)
            self._j2m_logger.info("sync_j2m_completed",
                sync_id=sync_id,
                entity_type=entity_type,
                entity_id=entity_id,
                fields_total=len(list(self._extract_sync_fields(entity_data))),
                fields_changed=changes_made,
                fields_updated=fields_updated,
                duration_ms=duration,
                file_size_bytes=md_path.stat().st_size
            )

        except Exception as e:
            self._j2m_logger.error("sync_j2m_failed",
                sync_id=sync_id,
                entity_type=entity_type,
                entity_id=entity_id,
                error_type=type(e).__name__,
                error_message=str(e),
                duration_ms=int((time.time() - start) * 1000)
            )
            raise

    async def sync_markdown_to_json(self, file_path: Path):
        sync_id = f"sync_{uuid.uuid4().hex[:8]}"
        start = time.time()
        entity_type, entity_id = self._parse_filename(file_path)

        self._m2j_logger.info("sync_m2j_started",
            sync_id=sync_id,
            file_path=str(file_path),
            entity_type=entity_type,
            entity_id=entity_id,
            file_size_bytes=file_path.stat().st_size
        )

        content = file_path.read_text(encoding="utf-8")
        changes = self._extract_sync_changes(content, entity_id)

        if not changes:
            self._m2j_logger.info("sync_m2j_no_changes",
                sync_id=sync_id,
                entity_id=entity_id,
                reason="No SYNC markers modified"
            )
            return

        # 冲突检测
        db_entity = await self.db.get_entity(entity_type, entity_id)
        db_modified = db_entity.get("updated_at")
        md_modified = self._extract_last_modified(content)

        has_conflict = self._has_conflict(db_modified, md_modified)

        if has_conflict:
            self._conflict_logger.warning("sync_conflict_detected",
                sync_id=sync_id,
                entity_id=entity_id,
                db_modified=db_modified.isoformat() if db_modified else None,
                md_modified=md_modified.isoformat() if hasattr(md_modified, 'isoformat') else str(md_modified),
                time_diff_seconds=int(abs(db_modified - md_modified).total_seconds()) if db_modified and md_modified else None,
                changed_fields=list(changes.keys()),
                strategy=self.strategy
            )

            if self.strategy == "manual":
                conflict_report = await self._create_conflict_report(entity_id, changes, db_entity)
                self._conflict_logger.info("conflict_report_created",
                    sync_id=sync_id,
                    entity_id=entity_id,
                    report_id=conflict_report["id"],
                    conflict_fields=list(conflict_report["conflicts"].keys())
                )
                return

        # 应用变更
        await self.db.update_entity_fields(entity_type, entity_id, changes)

        # 变更日志
        await self.db.log_change(
            novel_id=db_entity["novel_id"],
            entity_type=entity_type,
            entity_id=entity_id,
            field_path=list(changes.keys()),
            old_values={k: self._get_field(db_entity, k) for k in changes},
            new_values=changes,
            triggered_by="user_manual_edit"
        )

        duration = int((time.time() - start) * 1000)
        self._m2j_logger.info("sync_m2j_completed",
            sync_id=sync_id,
            entity_id=entity_id,
            fields_changed=len(changes),
            field_names=list(changes.keys()),
            had_conflict=has_conflict,
            conflict_resolution=self.strategy if has_conflict else "none_needed",
            duration_ms=duration,
            cascade_triggered=True
        )

        # 触发联动更新
        if has_conflict is False:  # 无冲突才联动
            await self._trigger_cascade_update(entity_type, entity_id, list(changes.keys()))
```

### C.5 联动更新引擎日志

联动更新是影响范围最大的操作，日志必须能回答「改了 A，影响了哪些 B」：

```python
# src/sync/cascade_updater.py — 联动日志增强

class CascadeUpdater:
    """联动更新引擎 — 完整影响追踪日志"""

    def __init__(self, novel_id: str):
        self.novel_id = novel_id
        self.cascade_log_file = Path(f"logs/{novel_id}/sync/cascade_update.log")
        self._logger = structlog.get_logger().bind(
            novel_id=novel_id,
            component_type="cascade_update"
        )

    async def track_impact(self, entity_type: str, entity_id: str,
                            changed_fields: list) -> dict:

        tracking_id = f"cascade_{uuid.uuid4().hex[:8]}"
        start = time.time()

        self._logger.info("impact_tracking_started",
            tracking_id=tracking_id,
            trigger_entity=f"{entity_type}:{entity_id}",
            changed_fields=changed_fields,
            trigger_source=self._identify_trigger_source(),
            max_depth=self.MAX_DEPTH
        )

        visited = set()
        impacts = []
        queue = [(entity_type, entity_id, changed_fields, 0)]

        depth_stats = {i: 0 for i in range(self.MAX_DEPTH + 1)}

        while queue:
            current_type, current_id, fields, depth = queue.pop(0)

            if depth > self.MAX_DEPTH:
                continue

            visit_key = f"{current_type}:{current_id}"
            if visit_key in visited:
                continue
            visited.add(visit_key)
            depth_stats[depth] += 1

            # 正向追踪
            references_to = await self.db.get_references_to(current_type, current_id)
            for ref in references_to:
                relevant = self._is_field_relevant(fields, ref)
                if relevant:
                    impact = {
                        "direction": "forward",
                        "source": f"{entity_type}:{entity_id}",
                        "target": f"{ref['target_type']}:{ref['target_id']}",
                        "field_path": ref.get("field_path"),
                        "depth": depth
                    }
                    impacts.append(impact)

                    self._logger.debug("forward_impact_found",
                        tracking_id=tracking_id,
                        depth=depth,
                        source=current_id,
                        target=ref['target_id'],
                        target_type=ref['target_type'],
                        relevance_reason=relevant
                    )
                    queue.append((
                        ref["target_type"], ref["target_id"],
                        [ref.get("field_path", "*")], depth + 1
                    ))

            # 反向追踪
            referenced_by = await self.db.get_referenced_by(current_type, current_id)
            for ref in referenced_by:
                impact = {
                    "direction": "backward",
                    "source": f"{entity_type}:{entity_id}",
                    "target": f"{ref['source_type']}:{ref['source_id']}",
                    "depth": depth
                }
                impacts.append(impact)

                self._logger.debug("backward_impact_found",
                    tracking_id=tracking_id,
                    depth=depth,
                    source=current_id,
                    affected_referrer=ref['source_id'],
                    referrer_type=ref['source_type']
                )
                queue.append((
                    ref["source_type"], ref["source_id"], ["*"], depth + 1
                ))

        duration = int((time.time() - start) * 1000)

        unique_impacts = self._deduplicate(impacts)

        self._logger.info("impact_tracking_completed",
            tracking_id=tracking_id,
            trigger_entity=f"{entity_type}:{entity_id}",
            changed_fields=changed_fields,
            total_entities_visited=len(visited),
            total_impacts_found=len(unique_impacts),
            high_severity_count=len([i for i in unique_impacts if i.get("severity") == "high"]),
            medium_severity_count=len([i for i in unique_impacts if i.get("severity") == "medium"]),
            low_severity_count=len([i for i in unique_impacts if i.get("severity") == "low"]),
            depth_distribution=depth_stats,
            truncated=len(unique_impacts) > 50,
            duration_ms=duration
        )

        return {
            "tracking_id": tracking_id,
            "trigger": f"{entity_type}:{entity_id}",
            "changed_fields": changed_fields,
            "total_impacts": len(unique_impacts),
            "impacts": unique_impacts[:50]
        }
```

### C.6 系统级日志

#### C.6.1 LLM API 调用日志（最关键的费用追踪）

```python
# src/utils/llm_client.py — LLM 调用日志

class LLMClient:
    """LLM 调用客户端 — 每次调用详细记录"""

    def __init__(self, config: dict):
        self.config = config
        self._llm_log_file = Path("logs/system/llm_calls.log")
        self._llm_log_file.parent.mkdir(parents=True, exist_ok=True)
        self._llm_logger = structlog.get_logger().bind(component_type="llm_call")

    async def chat(self, messages: list, model: str = None,
                   temperature: float = 0.7, **kwargs) -> dict:

        call_id = f"llm_{uuid.uuid4().hex[:10]}"
        start = time.time()

        # 记录请求（不含完整 messages 避免日志过大）
        self._llm_logger.info("llm_call_request",
            call_id=call_id,
            model=model or self.default_model,
            temperature=temperature,
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
            message_count=len(messages),
            message_roles=[m["role"] for m in messages],
            estimated_input_tokens=sum(
                len(m.get("content", "")) // 4 for m in messages  # 粗估
            ),
            caller_module=self._identify_caller(),
            purpose=kwargs.get("purpose", "unknown")
        )

        try:
            resp = await self._actual_api_call(messages, model, temperature, **kwargs)
            duration = int((time.time() - start) * 1000)

            usage = resp.get("usage", {})
            self._llm_logger.info("llm_call_response",
                call_id=call_id,
                status="success",
                model=resp.get("model", model),
                duration_ms=duration,
                prompt_tokens=usage.get("prompt_tokens"),
                completion_tokens=usage.get("completion_tokens"),
                total_tokens=usage.get("total_tokens"),
                cost_usd=self._estimate_cost(resp.get("model", model), usage),
                finish_reason=resp.get("choices", [{}])[0].get("finish_reason"),
                response_preview=resp.get("choices", [{}])[0].get("message", {}).get("content", "")[:200]
            )

            # 更新全局统计
            self._usage_stats["total_tokens"] += usage.get("total_tokens", 0)
            self._usage_stats["total_cost_usd"] += self._estimate_cost(resp.get("model", model), usage)
            self._usage_stats["call_count"] += 1

            return resp

        except Exception as e:
            duration = int((time.time() - start) * 1000)
            self._llm_logger.error("llm_call_error",
                call_id=call_id,
                status="error",
                duration_ms=duration,
                error_type=type(e).__name__,
                error_message=str(e),
                http_status=getattr(e, 'http_status', None),
                should_retry=isinstance(e, (RateLimitError, TimeoutError, APIServerError))
            )
            raise
```

#### C.6.2 数据库操作日志

```python
# src/database/engine.py — DB 操作日志

class DatabaseEngine:
    """数据库引擎 — 慢查询 + 错误日志"""

    SLOW_QUERY_THRESHOLD_MS = 1000  # 超过1秒的查询记为慢查询

    def __init__(self, url: str):
        self._db_log_file = Path("logs/system/database.log")
        self._db_log_file.parent.mkdir(parents=True, exist_ok=True)
        self._db_logger = structlog.get_logger().bind(component_type="database")

    async def execute(self, query: str, params: dict = None):
        call_id = f"db_{uuid.uuid4().hex[:8]}"
        start = time.time()

        try:
            result = await self._connection.execute(query, params)
            duration = int((time.time() - start) * 1000)

            log_level = "warning" if duration > self.SLOW_QUERY_THRESHOLD_MS else "debug"
            getattr(self._db_logger, log_level)("query_executed",
                call_id=call_id,
                query_hash=hash(query) % 100000,  # 不记录完整SQL防敏感信息泄露
                query_prefix=query[:100],  # 只记录前100字符
                has_params=params is not None,
                rows_affected=getattr(result, 'rowcount', None),
                duration_ms=duration,
                slow=duration > self.SLOW_QUERY_THRESHOLD_MS
            )

            return result

        except Exception as e:
            duration = int((time.time() - start) * 1000)
            self._db_logger.error("query_failed",
                call_id=call_id,
                query_prefix=query[:100],
                duration_ms=duration,
                error_type=type(e).__name__,
                error_code=getattr(e, 'pgcode', None),  # PostgreSQL 错误码
                error_message=str(e)[:500]
            )
            raise
```

#### C.6.3 API 请求/响应日志

```python
# src/api/middleware/logging_middleware.py

async def logging_middleware(request: Request, call_next):
    """API 请求/响应日志中间件"""
    request_id = request.headers.get("X-Request-ID", f"req_{uuid.uuid4().hex[:8]}")
    start = time.time()

    # 请求日志
    logger = structlog.get_logger().bind(component_type="api_request")
    logger.info("api_request_received",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        query_params=dict(request.query_params),
        client_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:100],
        content_length=request.headers.get("content-length"),
        content_type=request.headers.get("content-type")
    )

    try:
        response = await call_next(request)
        duration = int((time.time() - start) * 1000)

        # 响应日志
        logger.info("api_response_sent",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration,
            response_size=response.headers.get("content-length"),
            slow=duration > 3000  # >3s 标记为慢请求
        )

        # 在响应头中注入 request_id（方便前端排查）
        response.headers["X-Request-ID"] = request_id

        return response

    except Exception as e:
        duration = int((time.time() - start) * 1000)
        logger.error("api_request_error",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            duration_ms=duration,
            error_type=type(e).__name__,
            error_message=str(e)[:300]
        )
        raise
```

#### C.6.4 审计日志（不可篡改的操作记录）

```python
# src/audit/logger.py

class AuditLogger:
    """
    审计日志器。
    记录所有涉及安全、权限、数据变更的关键操作。
    审计日志写入独立的 append-only 文件。
    """

    def __init__(self, novel_id: str):
        self.audit_dir = Path(f"logs/{novel_id}/audit")
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        self._entity_log = structlog.get_logger().bind(
            component_type="audit_entity",
            novel_id=novel_id
        )
        self._user_log = structlog.get_logger().bind(
            component_type="audit_user",
            novel_id=novel_id
        )

    def log_entity_change(self, entity_type: str, entity_id: str,
                           operation: str, changes: dict, actor: str):
        """记录实体变更"""
        self._entity_log.info("entity_audit_record",
            timestamp=datetime.utcnow().isoformat(),
            entity_type=entity_type,
            entity_id=entity_id,
            operation=operation,  # CREATE / UPDATE / DELETE
            actor=actor,         # user_manual / agent_generator / agent_writer / system
            changed_fields=list(changes.keys()),
            old_values={k: str(v)[:200] for k, v in changes.get("old", {}).items()},
            new_values={k: str(v)[:200] for k, v in changes.get("new", {}).items()},
            ip_address=self._get_client_ip(),
            user_agent=self._get_user_agent()
        )

    def log_user_action(self, user_id: str, action: str,
                        resource: str, resource_id: str, details: dict = None):
        """记录用户操作"""
        self._user_log.info("user_action_audit",
            timestamp=datetime.utcnow().isoformat(),
            user_id=user_id,
            action=action,        # login / logout / export / delete / rollback / ...
            resource=resource,     # novel / character / chapter / ...
            resource_id=resource_id,
            details=details or {},
            ip_address=self._get_client_ip(),
            session_id=self._get_session_id()
        )
```

---

## 附录 D：日志格式与字段定义

### D.1 统一日志结构（JSON Lines 格式）

每条日志是一行 JSON，包含以下标准字段：

```json
{
  "timestamp": "2026-05-28T18:30:45.123Z",
  "level": "info",
  "logger": "world_builder",
  "event": "rule_generation_completed",
  "message": "Rule RULE-015 generated successfully",

  "=== 固定上下文（由 Logger.bind 自动注入）===",
  "module_id": "world_builder",
  "module_name": "世界观设定生成器",
  "novel_id": "novel-a1b2c3d4",
  "component_type": "module",

  "=== 事件特定字段（由调用方传入）===",
  "rule_id": "RULE-015",
  "rule_name": "记忆货币法则",
  "tokens_used": 1523,
  "cost_usd": 0.023,
  "duration_ms": 4521,
  "has_cost": true,
  "has_limitation": true,

  "=== 自动附加字段（由 Processor 注入）===",
  "request_id": "req_abc12345",
  "hostname": "prod-api-02",
  "process_id": 12345,
  "thread_id": "MainThread"
}
```

### D.2 字段分类表

| 字段类别 | 字段名 | 类型 | 必填 | 说明 |
|---------|--------|------|------|------|
| **时间** | `timestamp` | ISO8601 | ✅ | UTC 时间，毫秒精度 |
| **级别** | `level` | enum | ✅ | debug / info / warning / error / critical |
| **来源** | `logger` | string | ✅ | 产生日志的 logger 名称 |
| **事件** | `event` | string | ✅ | 事件类型标识（如 `rule_generation_completed`）|
| **消息** | `message` | string | ✅ | 人类可读的事件描述 |
| **项目** | `novel_id` | string | ✅ | 所属小说项目 ID |
| **组件** | `component_type` | enum | ✅ | module / agent / review / sync / system / audit |
| **模块** | `module_id` | string | 条件 | 仅 component_type=module 时必填 |
| **代理** | `agent_id` | string | 条件 | 仅 component_type=agent 时必填 |
| **关联** | `request_id` | string | 推荐 | 关联的 HTTP 请求 ID |
| **关联** | `task_id` | string | 条件 | 关联的任务 ID |
| **关联** | `tracking_id` | string | 条件 | 关联的联动追踪 ID |
| **耗时** | `duration_ms` | int | 推荐 | 操作耗时（毫秒）|
| **状态** | `status` | string | 条件 | success / failed / partial |
| **错误** | `error_type` | string | 条件 | 仅 level>=error 时 |
| **错误** | `error_message` | string | 条件 | 仅 level>=error 时 |
| **指标** | `tokens_used` | int | 条件 | LLM 相关日志 |
| **指标** | `cost_usd` | float | 条件 | LLM 相关日志 |
| **指标** | `score` | float | 条件 | 审核相关日志 |
| **指标** | `word_count` | int | 条件 | 正文相关日志 |
| **主机** | `hostname` | string | 自动 | 服务器主机名 |
| **进程** | `process_id` | int | 自动 | 进程 PID |
| **线程** | `thread_id` | string | 自动 | 线程标识 |

### D.3 敏感信息脱敏规则

| 字段类型 | 脱敏策略 | 示例 |
|---------|---------|------|
| API Key | 全部替换为 `sk-***...***` | `sk-abc123def456` → `sk-***...***` |
| 密码/密钥 | 全部替换为 `[REDACTED]` | `my_password` → `[REDACTED]` |
| 用户 IP | 默认保留；可通过配置决定是否脱敏 | `192.168.1.100` → `192.168.1.*` |
| 正文内容 | 只记录前 200 字符预览 | 5000 字正文 → 前 200 字 + `...(truncated)` |
| 人物心理描述 | 只记录前 50 字符 | 同上 |
| Token 计数 | 保留原始值（非敏感）| — |
| 费用金额 | 保留原始值（非敏感）| — |

---

## 附录 E：日志采集与写入实现

### E.1 Python 日志配置

```python
# src/utils/logger_config.py
"""
统一的日志配置。
所有模块、代理、中间件均通过此配置获取 logger 实例。
"""

import structlog
import logging
import sys
from pathlib import Path
from typing import Optional
import json
import os
import time
import threading

# 日志根目录（可通过环境变量覆盖）
LOG_ROOT = Path(os.environ.get("LOG_ROOT", "logs"))


def setup_logging(
    log_level: str = os.environ.get("LOG_LEVEL", "INFO"),
    log_root: Path = LOG_ROOT,
    json_output: bool = True
):
    """
    配置 structlog + 标准 logging。

    Args:
        log_level: 全局最低日志级别
        log_root: 日志根目录
        json_output: 是否输出 JSON 格式（生产环境推荐 True，开发环境可 False）
    """

    log_root.mkdir(parents=True, exist_ok=True)

    # === structlog 配置 ===
    structlog.configure(
        processors=[
            # 1. 添加时间戳
            structlog.processors.TimeStamper(fmt="iso"),

            # 2. 添加日志级别
            structlog.processors.add_log_level,

            # 3. 合并上下文（来自 logger.bind() 的字段）

            # 4. 格式化输出
            structlog.processors.JSONRenderer() if json_output
                else structlog.dev.ConsoleRenderer(colors=True),
        ],

        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        wrapper_class=structlog.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # === 标准 logging 配置（用于第三方库）===
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(name)s - %(message)s",
        level=getattr(logging, log_level.upper()),
        handlers=[
            # 控制台输出（开发用）
            logging.StreamHandler(sys.stdout),

            # 全局错误日志（收集所有 WARNING 以上级别的日志）
            _RotatingFileHandler(
                filename=log_root / "system" / "error.log",
                maxBytes=50*1024*1024,  # 50MB
                backupCount=10,
                level=logging.WARNING
            )
        ]
    )

    # 降低第三方库日志级别（避免噪音）
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("celery").setLevel(logging.INFO)
    logging.getLogger("pika").setLevel(logging.WARNING)  # RabbitMQ

    # 初始化日志索引
    _init_log_index(log_root)


def get_logger(name: str, novel_id: str = None,
               component_type: str = None, **context) -> structlog.BoundLogger:
    """
    获取带固定上下文的日志器。

    Args:
        name: logger 名称（通常为模块/代理 ID）
        novel_id: 所属项目 ID
        component_type: 组件类型
        **context: 额外的固定上下文字段

    Returns:
        绑定了上下文的 structlog.BoundLogger
    """
    base_context = {
        "novel_id": novel_id or "system",
        "component_type": component_type or "unknown",
    }
    base_context.update(context)

    return structlog.get_logger(name).bind(**base_context)


class _AsyncFileHandler(logging.Handler):
    """
    异步文件 Handler。
    将日志先写入内存缓冲区，批量刷盘，避免 I/O 阻塞主流程。
    """

    def __init__(self, filename: Path, batch_size: int = 50,
                 flush_interval: float = 5.0):
        super().__init__()
        self.filename = filename
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self._buffer = []
        self._last_flush = time.time()
        self._lock = threading.Lock()

        # 启动后台刷新线程
        self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
        self._flush_thread.start()

    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record)
            with self._lock:
                self._buffer.append(msg + "\n")
                if len(self._buffer) >= self.batch_size:
                    self._immediate_flush()
        except Exception:
            self.handleError(record)

    def _flush_loop(self):
        while True:
            time.sleep(self.flush_interval)
            with self._lock:
                if self._buffer:
                    self._immediate_flush()

    def _immediate_flush(self):
        if not self._buffer:
            return
        data = "".join(self._buffer)
        self._buffer.clear()
        try:
            with open(self.filename, "a", encoding="utf-8") as f:
                f.write(data)
        except Exception:
            pass  # 写入失败不阻塞主流程


def _init_log_index(log_root: Path):
    """初始化/更新日志索引文件"""
    index_file = log_root / "index.json"

    existing_index = {}
    if index_file.exists():
        try:
            existing_index = json.loads(index_file.read_text())
        except Exception:
            existing_index = {}

    # 更新索引中的时间戳
    import datetime
    existing_index["last_updated"] = datetime.datetime.now().isoformat()
    existing_index["log_root"] = str(log_root)

    index_file.write_text(json.dumps(existing_index, indent=2, ensure_ascii=False))


# 应用启动时调用一次
setup_logging()
```

### E.2 使用示例：完整的端到端日志流

以下展示「用户修改人物势力 → 联动更新 → 同步 Markdown → 审核受影响章节」这一完整链路的日志输出：

```
═══════════════════════════════════════════════════════════════
logs/novel-a1b2c3d4/audit/entity_changes.log
═══════════════════════════════════════════════════════════════

{"timestamp":"2026-05-28T18:30:00.123Z","level":"info","event":"entity_audit_record",
 "entity_type":"character","entity_id":"CHAR-001","operation":"UPDATE",
 "actor":"user_manual","changed_fields":["faction_id"],
 "old_values":{"faction_id":"FAC-003"},"new_values":{"faction_id":"FAC-005"},
 "ip_address":"192.168.1.100"}

═══════════════════════════════════════════════════════════════
logs/novel-a1b2c3d4/sync/markdown_to_json.log
═══════════════════════════════════════════════════════════════

{"timestamp":"2026-05-28T18:30:00.150Z","level":"info","event":"sync_m2j_started",
 "file_path":"/app/user_view/characters/CHAR-001.md","entity_id":"CHAR-001",
 "file_size_bytes":4250}
{"timestamp":"2026-05-28T18:30:00.280Z","level":"info","event":"sync_m2j_completed",
 "entity_id":"CHAR-001","fields_changed":1,"field_names":["faction_id"],
 "had_conflict":false,"duration_ms":130,"cascade_triggered":true}

═══════════════════════════════════════════════════════════════
logs/novel-a1b2c3d4/sync/cascade_update.log
═══════════════════════════════════════════════════════════════

{"timestamp":"2026-05-28T18:30:00.300Z","level":"info","event":"impact_tracking_started",
 "tracking_id":"cascade_a1b2c3d4","trigger_entity":"character:CHAR-001",
 "changed_fields":["faction_id"],"trigger_source":"user_manual_edit","max_depth":5}
{"timestamp":"2026-05-28T18:30:01.500Z","level":"debug","event":"forward_impact_found",
 "tracking_id":"cascade_a1b2c3d4","depth":0,"source":"CHAR-001",
 "target":"ARC-001","target_type":"arc","relevance_reason":"catalyst_node_references_faction"}
{"timestamp":"2026-05-28T18:30:01.520Z","level":"debug","event":"backward_impact_found",
 "tracking_id":"cascade_a1b2c3d4","depth":0,"source":"CHAR-001",
 "affected_referrer":"REL-001","referrer_type":"relation"}
{"timestamp":"2026-05-28T18:30:03.200Z","level":"info","event":"impact_tracking_completed",
 "tracking_id":"cascade_a1b2c3d4","total_impacts":8,"high_severity":3,
 "medium_severity":3,"low_severity":2,"duration_ms":2900}

═══════════════════════════════════════════════════════════════
logs/novel-a1b2c3d4/sync/json_to_markdown.log
═══════════════════════════════════════════════════════════════

{"timestamp":"2026-05-28T18:30:03.500Z","level":"info","event":"sync_j2m_started",
 "sync_id":"sync_e5f6g7h8","entity_type":"character","entity_id":"ARC-001",
 "trigger":"cascade_update"}
{"timestamp":"2026-05-28T18:30:03.650Z","level":"info","event":"sync_j2m_completed",
 "entity_id":"ARC-001","fields_changed":1,"fields_updated":["catalyst_faction_context"],
 "duration_ms":150}

═══════════════════════════════════════════════════════════════
logs/novel-a1b2c3d4/modules/character_builder.log
═══════════════════════════════════════════════════════════════

{"timestamp":"2026-05-28T18:30:04.000Z","level":"info","event":"module_operation",
 "operation":"character_faction_changed","char_id":"CHAR-001",
 "old_faction":"FAC-003","new_faction":"FAC-005",
 "affected_arcs":["ARC-001"],"affected_relations":["REL-001","REL-003"]}

═══════════════════════════════════════════════════════════════
logs/system/llm_calls.log
═══════════════════════════════════════════════════════════════

{"timestamp":"2026-05-28T18:31:00.000Z","level":"info","event":"llm_call_request",
 "call_id":"llm_xyz789","model":"gpt-4o","temperature":0.65,
 "message_count":3,"caller_module":"writer_agent",
 "purpose":"chapter_28_scene_2_generation"}
{"timestamp":"2026-05-28T18:31:08.500Z","level":"info","event":"llm_call_response",
 "call_id":"llm_xyz789","status":"success","duration_ms":8500,
 "prompt_tokens":4200,"completion_tokens":1800,"total_tokens":6000,
 "cost_usd":0.09,"finish_reason":"stop"}

═══════════════════════════════════════════════════════════════
logs/novel-a1b2c3d4/manuscript/CH-028_generation.log
═══════════════════════════════════════════════════════════════

{"timestamp":"2026-05-28T18:30:50.000Z","level":"info","event":"chapter_writing_started",
 "chapter_number":28,"scene_count":3,"word_budget":6000,
 "characters_involved":["CHAR-001","CHAR-003","CHAR-006"],
 "foreshadows_to_plant":["FORE-031"],"foreshadows_to_reveal":["FORE-003"]}
{"timestamp":"2026-05-28T18:31:20.000Z","level":"info","event":"scene_generation_completed",
 "chapter_number":28,"scene_index":1,"word_count":1850,
 "budget":2000,"budget_deviation_pct":-7.5,"duration_ms":40000}
{"timestamp":"2026-05-28T18:32:15.000Z","level":"info","event":"chapter_writing_completed",
 "chapter_number":28,"total_scenes":3,"total_word_count":5850,
 "budget_deviation_pct":-2.5,"total_duration_ms":165000}

═══════════════════════════════════════════════════════════════
logs/novel-a1b2c3d4/review/consistency.log
═══════════════════════════════════════════════════════════════

{"timestamp":"2026-05-28T18:33:00.000Z","level":"info","event":"review_layer_started",
 "chapter_number":28,"layer":"consistency","required":true,
 "manuscript_word_count":5850,"constraint_entities":12}
{"timestamp":"2026-05-28T18:33:15.000Z","level":"info","event":"issue_detected",
 "chapter_number":28,"layer":"consistency","issue_severity":"warning",
 "issue_category":"character_status","issue_preview":"CHAR-001 used left arm...",
 "related_entities":["CHAR-001","CH-028-SCENE-03"]}
{"timestamp":"2026-05-28T18:33:30.000Z","level":"info","event":"review_layer_completed",
 "chapter_number":28,"layer":"consistency","score":0.92,"passed":true,
 "issues_found":1,"duration_ms":30000}
```

---

## 附录 F：日志轮转与生命周期管理

### F.1 轮转策略

| 日志类型 | 轮转方式 | 单文件上限 | 保留份数 | 总保留期 |
|---------|---------|-----------|---------|---------|
| 模块日志 | 按天轮转 | 50 MB | 30 天 | 90 天 |
| 代理日志 | 按天轮转 | 100 MB | 14 天 | 42 天 |
| 审核日志 | 按天轮转 | 50 MB | 30 天 | 90 天 |
| 同步日志 | 按天轮转 | 50 MB | 60 天 | 180 天 |
| 章节生成日志 | 不轮转（每章独立文件）| — | 永久 | 永久 |
| LLM 调用日志 | 按天轮转 | 200 MB | 90 天 | 270 天 |
| 数据库日志 | 按天轮转 | 50 MB | 30 天 | 90 天 |
| API 请求日志 | 按天轮转 | 100 MB | 14 天 | 42 天 |
| 审计日志 | 不轮转（append-only）| — | 永久 | 永久 |
| 错误日志 | 按大小轮转 | 10 MB | 20 份 | — |
| 系统启动日志 | 按天轮转 | 10 MB | 30 天 | 30 天 |

### F.2 轮转实现

```python
# src/utils/log_rotation.py

import os
import gzip
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

LOG_ROOT = Path(os.environ.get("LOG_ROOT", "logs"))
ARCHIVE_DIR = LOG_ROOT / "archived"


class LogRotationManager:
    """日志轮转管理器"""

    # 轮转规则配置
    ROTATION_RULES = {
        "modules": {"max_size_mb": 50, "keep_days": 30, "pattern": "*.log"},
        "agents": {"max_size_mb": 100, "keep_days": 14, "pattern": "*.log"},
        "review": {"max_size_mb": 50, "keep_days": 30, "pattern": "*.log"},
        "sync": {"max_size_mb": 50, "keep_days": 60, "pattern": "*.log"},
        "system": {"max_size_mb": 200, "keep_days": 90, "pattern": "llm_calls.log"},
        "system_db": {"max_size_mb": 50, "keep_days": 30, "pattern": "database.log"},
        "system_api": {"max_size_mb": 100, "keep_days": 14, "pattern": "api_requests.log"},
    }

    def __init__(self):
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        self._executor = ThreadPoolExecutor(max_workers=2)

    def rotate_all(self):
        """执行全部轮转（由定时任务调用，建议每天凌晨 3 点执行）"""
        for category, rule in self.ROTATION_RULES.items():
            self._executor.submit(self._rotate_category, category, rule)

        # 归档过期日志
        self._executor.submit(self._archive_expired)

    def _rotate_category(self, category: str, rule: dict):
        """对单个类别执行轮转"""
        # 遍历所有项目的该类别目录
        for log_dir in LOG_ROOT.rglob(f"*/{category}"):
            if not log_dir.is_dir():
                continue
            for log_file in log_dir.glob(rule["pattern"]):
                self._rotate_single_file(log_file, rule["max_size_mb"])

    def _rotate_single_file(self, file_path: Path, max_size_mb: int):
        """轮转单个文件：超出大小限制则切割"""
        if file_path.stat().st_size < max_size_mb * 1024 * 1024:
            return

        # 重命名为 .1，原来的 .1 变为 .2，以此类推
        for i in range(9, 0, -1):
            rotated = Path(str(file_path) + f".{i}")
            next_rotated = Path(str(file_path) + f".{i+1}")
            if rotated.exists():
                rotated.rename(next_rotated)

        # 当前文件变为 .1
        rotated_1 = Path(str(file_path) + ".1")
        file_path.rename(rotated_1)

        # 创建新的空文件（原路径继续写入）
        file_path.touch()

    def _archive_expired(self):
        """归档过期的旧日志文件"""
        cutoff = datetime.now() - timedelta(days=90)  # 最长保留 90 天的原始文件

        for log_file in LOG_ROOT.rglob("*.log.*"):  # 已轮转的文件
            if datetime.fromtimestamp(log_file.stat().st_mtime) < cutoff:
                # 压缩后移到归档目录
                archive_name = (
                    f"{datetime.now().strftime('%Y-%m')}_"
                    f"{log_file.relative_to(LOG_ROOT).as_posix().replace('/', '_')}"
                    f".gz"
                )
                archive_path = ARCHIVE_DIR / archive_name

                with open(log_file, 'rb') as f_in:
                    with gzip.open(archive_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)

                log_file.unlink()

    def get_disk_usage(self) -> dict:
        """获取日志磁盘占用统计"""
        total_size = 0
        by_category = {}

        for log_file in LOG_ROOT.rglob("*.log"):
            size = log_file.stat().st_size
            total_size += size

            # 按类别统计
            parts = log_file.relative_to(LOG_ROOT).parts
            category = parts[0] if len(parts) > 1 else "root"
            by_category[category] = by_category.get(category, 0) + size

        # 加上归档目录
        archive_size = sum(f.stat().st_size for f in ARCHIVE_DIR.rglob("*.gz"))

        return {
            "total_bytes": total_size,
            "total_mb": round(total_size / 1024 / 1024, 2),
            "archive_bytes": archive_size,
            "archive_mb": round(archive_size / 1024 / 1024, 2),
            "by_category": {k: round(v / 1024 / 1024, 2) for k, v in by_category.items()}
        }


# 定时任务注册（通过 APScheduler 或 cron）
# 每天凌晨 3:00 执行轮转
# scheduler.add_job(rotation_manager.rotate_all, 'cron', hour=3, minute=0)
```

### F.3 日志清理策略

| 时间节点 | 操作 | 说明 |
|---------|------|------|
| 每天 03:00 | 轮转超大文件 | 单文件 > 上限时切割 |
| 每天 03:30 | 归档 90 天前的 `.log.N` 文件 | gzip 压缩 → `archived/` |
| 每周一 04:00 | 清理 270 天前的归档 | 删除超期 gzip 文件 |
| 手动触发 | `POST /api/logs/rotate` | 立即执行轮转 |
| 手动触发 | `POST /api/logs/cleanup?older_than_days=30` | 清理指定天数前的日志 |
| 磁盘使用 > 80% | 自动告警 + 紧急清理 | 先清理 system 级别日志，再清理项目级日志 |

---

## 附录 G：日志查询与分析工具

### G.1 CLI 查询工具

```bash
#!/usr/bin/env python3
# scripts/log_query.py — 日志命令行查询工具

"""
用法：
  # 查看某个项目的所有模块日志的最新 20 条
  python scripts/log_query.py --project novel-a1b2c3d4 --module world_builder --tail 20

  # 查看第 28 章的生成全过程
  python scripts/log_query.py --project novel-a1b2c3d4 --file manuscript/CH-028_generation.log

  # 搜索所有包含 "failed" 的日志
  python scripts/log_query.py --search "failed" --level error

  # 查看 LLM 调用费用统计
  python scripts/log_query.py --file system/llm_calls.log --stats cost_usd

  # 查看某段时间范围的日志
  python scripts/log_query.py --from "2026-05-28T18:00:00" --to "2026-05-28T19:00:00"
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict

LOG_ROOT = Path("logs")


def query_logs(project: str = None, module: str = None, file: str = None,
               search: str = None, level: str = None, tail: int = None,
               from_time: str = None, to_time: str = None,
               stats: str = None):

    # 确定搜索范围
    if file:
        files = [LOG_ROOT / file]
    elif project:
        base = LOG_ROOT / project
        if module:
            files = list(base.glob(f"modules/{module}.log"))
            files.extend(list(base.glob(f"agents/*{module}*.log")))
        else:
            files = list(base.rglob("*.log"))
    else:
        files = list(LOG_ROOT.rglob("*.log"))

    results = []
    total_lines = 0
    matched_lines = 0

    for f in files:
        try:
            for line in open(f, 'r', encoding='utf-8', errors='replace'):
                total_lines += 1
                try:
                    record = json.loads(line.strip())
                except json.JSONDecodeError:
                    continue

                # 时间过滤
                if from_time and record.get("timestamp", "") < from_time:
                    continue
                if to_time and record.get("timestamp", "") > to_time:
                    continue

                # 级别过滤
                if level and record.get("level", "").lower() != level.lower():
                    continue

                # 关键词搜索
                if search:
                    line_text = json.dumps(record, ensure_ascii=False).lower()
                    if search.lower() not in line_text:
                        continue

                matched_lines += 1
                results.append(record)

        except FileNotFoundError:
            print(f"[WARN] File not found: {f}", file=sys.stderr)

    # 输出结果
    if stats:
        print_stats(results, stats)
    elif tail:
        for r in results[-tail:]:
            print(format_record(r))
    else:
        for r in results:
            print(format_record(r))

    print(f"\n--- 共扫描 {total_lines} 行，匹配 {matched_lines} 条 ---", file=sys.stderr)


def format_record(record: dict) -> str:
    """格式化单条日志为可读文本"""
    ts = record.get("timestamp", "")[:19]
    level = record.get("level", "---").upper()
    event = record.get("event", "")
    msg = record.get("message", "")

    # 提取关键上下文
    ctx_parts = []
    for key in ["module_id", "agent_id", "chapter_number", "task_id",
                "char_id", "rule_id", "fore_id", "tracking_id"]:
        if key in record:
            ctx_parts.append(f"{key}={record[key]}")

    ctx = " ".join(ctx_parts)

    # 提取关键指标
    metric_parts = []
    for key in ["duration_ms", "score", "word_count", "tokens_used", "cost_usd"]:
        if key in record:
            metric_parts.append(f"{key}={record[key]}")

    metrics = " ".join(metric_parts) if metric_parts else ""

    return f"[{ts}] [{level:^5}] {event:<40} {ctx} {metrics}  {msg}"


def print_stats(records: list, stat_field: str):
    """统计模式"""
    if stat_field == "cost_usd":
        total = sum(r.get(stat_field, 0) for r in records)
        by_model = defaultdict(float)
        for r in records:
            by_model[r.get("model", "unknown")] += r.get(stat_field, 0)

        print(f"=== LLM 费用统计 ===")
        print(f"总费用: ${total:.2f}")
        print(f"\n按模型:")
        for model, cost in sorted(by_model.items(), key=lambda x: -x[1]):
            print(f"  {model}: ${cost:.2f}")

    elif stat_field == "duration_ms":
        durations = [r.get(stat_field, 0) for r in records if r.get(stat_field)]
        if durations:
            print(f"=== 耗时统计 ===")
            print(f"调用次数: {len(durations)}")
            print(f"平均: {sum(durations)/len(durations):.0f}ms")
            print(f"P50: {sorted(durations)[len(durations)//2]:.0f}ms")
            print(f"P99: {sorted(durations)[int(len(durations)*0.99)]:.0f}ms")
            print(f"最大: {max(durations):.0f}ms")

    elif stat_field == "level":
        counter = Counter(r.get("level", "UNKNOWN") for r in records)
        print(f"=== 日志级别分布 ===")
        for level, count in counter.most_common():
            print(f"  {level}: {count}")

    else:
        values = [r.get(stat_field) for r in records if r.get(stat_field)]
        counter = Counter(values)
        print(f"=== '{stat_field}' 统计 ===")
        for val, count in counter.most_common(20):
            print(f"  {val}: {count}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Log Query Tool")
    parser.add_argument("--project", "-p", help="Project ID")
    parser.add_argument("--module", "-m", help="Module name")
    parser.add_argument("--file", "-f", help="Specific log file (relative to logs/)")
    parser.add_argument("--search", "-s", help="Search keyword")
    parser.add_argument("--level", "-l", help="Filter by log level")
    parser.add_argument("--tail", "-n", type=int, help="Show last N entries")
    parser.add_argument("--from", "-F", dest="from_time", help="Start time (ISO)")
    parser.add_argument("--to", "-T", dest="to_time", help="End time (ISO)")
    parser.add_argument("--stats", help="Field to compute statistics on")
    args = parser.parse_args()

    query_logs(
        project=args.project, module=args.module, file=args.file,
        search=args.search, level=args.level, tail=args.tail,
        from_time=args.from_time, to_time=args.to_time, stats=args.stats
    )
```

### G.2 Web 日志查看 API

```python
# src/api/endpoints/logs.py

@router.get("/api/logs/query")
async def query_logs(
    project_id: str = Query(..., description="Novel project ID"),
    category: str = Query(None, description="modules/agents/review/sync/manuscript/system/audit"),
    file_name: str = Query(None, description="Specific log file name"),
    search: str = Query(None, description="Search keyword"),
    level: str = Query(None, description="Filter by level: debug/info/warning/error/critical"),
    tail: int = Query(100, ge=1, le=10000, description="Max results to return"),
    since: str = Query(None, description="ISO timestamp, show logs after this time"),
    until: str = Query(None, description="ISO timestamp, show logs before this time"),
    stats: str = Query(None, description="Compute statistics on this field")
):
    """
    日志查询 API。

    示例：
      GET /api/logs/query?project_id=novel-a1b2c3d4&category=agents&search=failed&level=error&tail=50
      GET /api/logs/query?project_id=novel-a1b2c3d4&file=manuscript/CH-028_generation.log
      GET /api/logs/query?project_id=novel-a1b2c3d4&category=system&file=llm_calls.log&stats=cost_usd
    """
    ...


@router.get("/api/logs/stats")
async def log_statistics(project_id: str):
    """
    日志统计面板数据。
    返回各类日志的数量、大小、最新写入时间等。
    用于前端仪表盘展示。
    """
    ...


@router.post("/api/logs/rotate")
async def force_rotate(current_user: User = Depends(get_current_user)):
    """手动触发日志轮转（需要管理员权限）"""
    ...


@router.post("/api/logs/export")
async def export_logs(
    project_id: str,
    categories: List[str] = Query(["all"]),
    format: str = Query("tar.gz"),  # tar.gz | zip | json
    since: str = Query(None),
    until: str = Query(None)
):
    """
    导出日志文件。
    打包指定项目和类别的日志为下载文件。
    """
    ...
```

### G.3 Grafana 日志仪表盘（Loki 集成方案）

如果部署了 Loki + Prometheus 全栈监控，可以将日志接入 Grafana：

```yaml
# promtail-config.yaml — 日志采集器配置
scrape_configs:
  - job_name: novel-system-logs
    static_configs:
      - targets:
          - localhost
        labels:
          job: novel-system
          __path__: /app/logs/**/*.log

    pipeline_stages:
      - json:
          expressions:
            timestamp: timestamp
            level: level
            event: event
            module_id: module_id
            novel_id: novel_id

      - timestamps:
          source: timestamp
          format: ISO8601

      - labels:
          level:
          novel_id:
          component_type:
          module_id:
          agent_id:

      - output:
          source: output
```

Grafana 仪表盘面板建议：

| 面板名称 | 查询 | 展示形式 |
|---------|------|---------|
| 日志量趋势 | `sum by (level) (over_time(logster_log_entries[5m]))` | 折线图（按级别分色）|
| 错误率 | `rate(logster_log_entries{level="error"}[5m]) / rate(logster_log_entries[5m])` | Gauge（百分比）|
| LLM 费用趋势 | `sum over(time) (cost_usd)` 从 llm_calls.log 解析 | 折线图 + 累计值 |
| 模块活跃度 | `count by (module_id) (logster_log_entries)` | 饼图 |
| 代理吞吐 | `count by (agent_id) (logster_log_entries{event="task_completed"})` | 柱状图 |
| 审核通过率 | `count(event="review_layer_completed", passed=true) / count(event="review_layer_completed")` | Gauge |
| 同步冲突率 | `count(event="conflict_detected") / count(event="sync_*_started")` | Gauge |
| 章节生成耗时分布 | `duration_ms` 从 manuscript/*.log 解析 | 直方图 |

---

## 附录 H：日志在失败回退中的作用

### H.1 日志驱动的故障诊断流程

```
检测到异常（告警/用户报错/自动检测）
  │
  ▼
步骤1：定位异常时间点
  ├─ 查 system/error.log → 找到第一条 ERROR/CRITICAL 记录
  ├─ 提取 timestamp 和 request_id/task_id
  │
  ▼
步骤2：追踪完整调用链
  ├─ 用 request_id 在 api_requests.log 中找到入口请求
  ├─ 用 task_id 在 agents/*.log 中找到代理处理过程
  ├─ 用 tracking_id 在 sync/cascade_update.log 中找到联动影响
  │
  ▼
步骤3：分析根因
  ├─ 查 llm_calls.log → LLM 调用是否超时/报错/返回异常？
  ├─ 查 database.log → 是否有慢查询或锁等待？
  ├─ 查 review/*.log → 审核是否发现了问题但被忽略？
  ├─ 查 sync/conflict.log → 是否有未解决的冲突？
  │
  ▼
步骤4：确定回退方案
  ├─ 如果是瞬时故障 → 查重试次数和间隔是否合理
  ├─ 如果是数据损坏 → 查最近的快照点（snapshots/）
  ├─ 如果是 LLM 质量 → 查 Prompt + 温度 + 返回内容
  ├─ 如果是并发冲突 → 查冲突日志中的双方修改时间戳
  │
  ▼
步骤5：执行修复并验证
  ├─ 执行回退/修复操作
  ├─ 在日志中搜索确认修复后的操作成功
  └─ 必要时通知相关人员
```

### H.2 典型故障的日志排查案例

**案例 1：第 28 章生成后审核一直不通过**

```
排查步骤：
1. grep "CH-028" logs/novel-xxx/review/*.log
   → 发现 consistency 层每次都报 CHAR-001 左臂状态不一致

2. grep "CHAR-001" logs/novel-xxx/modules/character_builder.log
   → 发现 status_timeline 在第 27 章更新时 left_arm 设为 injured
   → 但在第 27.5 章（插入的过渡章）中被某次操作意外清空了

3. grep "27.5" logs/novel-xxx/sync/markdown_to_json.log
   → 发现用户在第 27.5 章编辑时手动删除了 SYNC 标记中的 physical 字段
   → 导致同步时将该字段覆盖为空

4. 结论：用户误删 SYNC 标记 → 同步将物理状态置空 → 审核检测到不一致
   修复：从 change_log 中找到受伤状态的旧值 → 手动恢复 → 重新审核通过
```

**案例 2：LLM 费用突然飙升**

```
排查步骤：
1. cat logs/system/llm_calls.log | python -c "
   costs=[sum(json.loads(l)['cost_usd'] for l in sys.stdin if 'cost_usd' in l)];
   print(sum(costs))"
   → 发现最近 24 小时费用是之前的 3 倍

2. grep "2026-05-28" logs/system/llm_calls.log | grep '"cost_usd"'
   → 发现大量来自 writer_agent 的调用，每次 completion_tokens 都接近 max_tokens

3. grep "writer" logs/novel-xxx/agents/writer.log | grep "task_completed"
   → 发现章节生成任务的 duration_ms 从平均 60s 增长到 180s
   → 且 tokens_used 远超预算

4. grep "CH-029" logs/novel-xxx/manuscript/CH-029_generation.log
   → 发现第 29 章的场景数从 3 个增加到 8 个（大纲被修改过）
   → 每个场景都在用满 max_tokens

5. 结论：大纲调整增加了场景数量，导致每章 token 消耗翻倍
   修复：调整细纲减少场景数；设置单章 token 上限告警
```

**案例 3：伏笔重复检测漏报**

```
排查步骤：
1. grep "FORE-045" logs/novel-xxx/modules/foreshadow_manager.log
   → 发现 FORE-045 创建时 duplicate_detector 返回空列表（无重复）

2. grep "duplicate" logs/novel-xxx/modules/foreshadow_manager.log
   → 发现近期的 duplicate check 相似度阈值从 0.85 改为了 0.95
   → 是一次热更新配置导致的

3. grep "config" logs/system/registry.log
   → 确认 foreshadow_manager 模块在 T=XX:XX:XX 接收到了配置更新
   → DUPLICATE_THRESHOLD 从 0.85 改为 0.95

4. 结论：配置热更新时阈值设置过高导致漏报
   修复：恢复阈值为 0.85；增加配置变更审计日志；阈值变更需二次确认
```

---

## 附录 I：实施检查清单

### I.1 开发阶段检查项

| 编号 | 检查项 | 验证方法 | 状态 |
|------|--------|---------|------|
| LOG-001 | `src/utils/logger_config.py` 存在且可导入 | `python -c "from src.utils.logger_config import setup_logging; setup_logging()"` | ⬜ |
| LOG-002 | `BaseModule` 包含 `_create_logger()` 方法 | `grep "_create_logger" src/modules/base_module.py` | ⬜ |
| LOG-003 | `BaseAgent` 包含任务生命周期日志 | `grep "task_received\|task_completed\|task_failed" src/agents/base_agent.py` | ⬜ |
| LOG-004 | `FourLayerReviewEngine` 每层有独立 logger | `ls src/review/*_logger*.py` 或 grep "_make_review_logger" | ⬜ |
| LOG-005 | `SyncEngine` 有 j2m/m2j/conflict/cascade 四个 logger | `grep "_make_sync_logger" src/sync/engine.py` | ⬜ |
| LOG-006 | `LLMClient` 每次调用有 request/response 日志 | `grep "llm_call_request\|llm_call_response" src/utils/llm_client.py` | ⬜ |
| LOG-007 | `DatabaseEngine` 有慢查询日志 | `grep "slow_query\|query_executed" src/database/engine.py` | ⬜ |
| LOG-008 | API 中间件有请求/响应日志 | `grep "api_request_received\|api_response_sent" src/api/middleware/` | ⬜ |
| LOG-009 | `AuditLogger` 存在且记录实体变更和用户操作 | `ls src/audit/logger.py` | ⬜ |
| LOG-010 | 日志输出为 JSON Lines 格式 | 运行任意模块操作后 `head -1 logs/*/modules/*.log | python -m json.tool` 能正确解析 | ⬜ |
| LOG-011 | 日志目录结构符合 B.1 节规范 | `find logs/ -type d | sort` 输出符合预期 | ⬜ |
| LOG-012 | 敏感信息（API Key/密码）已脱敏 | `grep "sk-" logs/ -r` 应无明文 Key | ⬜ |
| LOG-013 | `scripts/log_query.py` 可正常执行 | `python scripts/log_query.py --help` | ⬜ |
| LOG-014 | 日志轮转脚本存在 | `ls src/utils/log_rotation.py` | ⬜ |
| LOG-015 | 异步写入 Handler 不阻塞主流程 | 压力测试下日志写入延迟不影响 API 响应时间 | ⬜ |

### I.2 生产部署检查项

| 编号 | 检查项 | 验证方法 | 状态 |
|------|--------|---------|------|
| PLOG-001 | `LOG_ROOT` 环境变量已配置 | `docker exec container env | grep LOG_ROOT` | ⬜ |
| PLOG-002 | 日志目录持久化（Docker Volume）| `docker compose.yml` 中 logs/ 目录挂载为 volume | ⬜ |
| PLOG-003 | 日志磁盘配额设置 | `df -h logs/` 确认有足够空间；设置 >80% 告警 | ⬜ |
| PLOG-004 | 定时轮转任务已注册 | `crontab -l` 或 Kubernetes CronJob 存在 | ⬜ |
| PLOG-005 | 归档目录自动清理 | 检查 270 天前的归档是否被自动删除 | ⬜ |
| PLOG-006 | 日志查询 API 可访问 | `GET /api/logs/query?project_id=xxx&tail=5` 返回结果 | ⬜ |
| PLOG-007 | 日志导出功能可用 | `POST /api/logs/export` 返回下载文件 | ⬜ |
| PLOG-008 | Grafana 日志面板可访问（如部署了 Loki）| 浏览器打开 Grafana Dashboard | ⬜ |
| PLOG-009 | 审计日志不可被普通用户修改 | 文件权限设置为 `0644`（只追加）| ⬜ |
| PLOG-010 | 全局错误日志集中收集 | `logs/system/error.log` 包含所有 WARNING+ 级别日志 | ⬜ |

---

> **文档结束**
>
> 本文档整合了《AI 小说创作系统完整实施方案》主体（第一部分，共 6 章）
> 与《日志系统专项设计方案》全文（第二部分，附录 A–I 共 9 个附录）。
>
> **核心承诺**：
> - 所有 12 个业务模块、3 种代理池、4 类审核引擎、双向同步引擎、
>   联动更新引擎以及全部系统中间件（数据库/缓存/消息队列/LLM/向量存储/API网关）
>   **均有对应的日志输出**
> - 统一存储到 `logs/` 目录下的专门文件夹中
> - 支持后续审计、排障、性能分析和故障回溯
> - 日志系统本身不影响主业务性能（异步写入 + 缓冲区）
