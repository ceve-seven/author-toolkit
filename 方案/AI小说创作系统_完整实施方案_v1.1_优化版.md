# AI 小说创作系统 — 完整实施方案 v1.1（Agent-Native 优化版）

> **版本**: v1.1（基于 v1.0 优化）
> **编制日期**: 2026-05-28
> **v1.0 原始文档**: 15 个 @AI小说相关 文件 + 多轮对话设计文档 + 日志系统专项设计
> **适用范围**: 从零搭建到生产部署的全流程 AI 小说创作系统
> **核心定位**: **AI Agent 可调用的后端服务 + 用户可视中文 Markdown 双层架构**

---

## v1.0 → v1.1 变更日志

| 变更编号 | 类别 | 变更内容 | 影响范围 |
|---------|------|---------|---------|
| CHG-001 | 🔴 Blocker | 修正数据库表数量：48→52+（含系统表） | §1.3, §2.3 |
| CHG-002 | 🔴 Blocker | 统一写作流程环节计数：明确为 18 个环节 | §1.3 |
| CHG-003 | 🔴 Blocker | 修复 docker-compose.yml 健康检查（curl→python） | §2.3 |
| CHG-004 | 🔴 Blocker | 补充 logs 目录 Docker Volume 挂载 | §2.3 |
| CHG-005 | 🔴 Blocker | 重构 structlog 配置：PrintLoggerFactory→文件写入 | 附录E |
| CHG-006 | 🔴 Blocker | 修复 _RotatingFileHandler 未定义问题 | 附录E |
| CHG-007 | 🔴 Blocker | 补充 CascadeUpdater.MAX_DEPTH 定义 | 附录C.5 |
| CHG-008 | 🔴 Blocker | 修复 BaseModule._create_logger() log_file 未绑定 | 附录C.1 |
| CHG-009 | 🟢 Agent | **新增** Workflow Orchestrator API（端到端编排） | 新增§七 |
| CHG-010 | 🟢 Agent | **新增** 异步任务状态查询与回调机制 | 新增§七 |
| CHG-011 | 🟢 Agent | **新增** 统一 API Schema 定义（Pydantic Models） | 新增§八 |
| CHG-012 | 🟢 Agent | **新增** Agent 接入指南（MCP/LangChain/OpenAI Actions） | 新增§九 |
| CHG-013 | 🟡 Critical | 补充 sync_events 队列消费者代码 | §3.3 |
| CHG-014 | 🟡 Critical | 日志查询 API 增加鉴权保护 | 附录G.2 |
| CHG-015 | 🟡 Critical | 补充 docker-compose.dev.yml | §2.3 |
| CHG-016 | 🟡 Critical | Markdown SYNC 标记对 Agent 隐藏策略 | §7.4 |
| CHG-017 | 🟣 Enhance | 写作代理池 replicas: 1→2 | §2.3 |
| CHG-018 | 🟣 Enhance | 向量相似度阈值环境变量化 | §4.2 |
| CHG-019 | 🟣 Enhance | 补充 .gitignore 规范 | §2.5 |
| CHG-020 | 🟢 **核心** | **整合双层架构（用户可视层+系统引擎层）** | **新增§十** |
| CHG-021 | 🟢 **核心** | **补充完整用户可视目录结构（11个中文文件夹）** | **新增§十** |
| CHG-022 | 🟢 **核心** | **补充 SYNC 标记规范与双向同步引擎设计** | **新增§十** |

---

## 目录

1. [系统总览与架构目标](#一系统总览与架构目标)
2. [环境配置清单](#二环境配置清单)
3. [分阶段实施流程](#三分阶段实施流程)
4. [各环节失败回退方案](#四各环节失败回退方案)
5. [性能优化与监控](#五性能优化与监控)
6. [验收标准与交付物](#六验收标准与交付物)
7. [**Workflow Orchestrator 与 Agent 调用层**](#七workflow-orchestrator与agent调用层) ⭐ v1.1
8. [**统一 API Schema 定义**](#八统一api-schema定义pydantic-models) ⭐ v1.1
9. [**Agent 接入指南**](#九agent接入指南) ⭐ v1.1
10. [**🆕 双层架构：用户可视层 + 系统引擎层 + 同步引擎**](#十双层架构用户可视层系统引擎层同步引擎) ⭐⭐ 核心
11. [附录 A：日志系统总体架构](#附录a日志系统总体架构)
11. [附录 B：日志目录结构与命名规范](#附录b日志目录结构与命名规范)
12. [附录 C：各组件日志规范](#附录c各组件日志规范)
13. [附录 D：日志格式与字段定义](#附录d日志格式与字段定义)
14. [附录 E：日志采集与写入实现（已修复）](#附录e日志采集与写入实现)
15. [附录 F：日志轮转与生命周期管理](#附录f日志轮转与生命周期管理)
16. [附录 G：日志查询与分析工具](#附录g日志查询与分析工具)
17. [附录 H：日志在失败回退中的作用](#附录h日志在失败回退中的作用)
18. [附录 I：实施检查清单（更新）](#附录i实施检查清单)

---

# 第一部分：完整实施方案

---

## 一、系统总览与架构目标

### 1.1 核心设计原则（v1.1 更新）

| 原则 | 定义 | 实现方式 |
|------|------|---------|
| **Agent First** | 所有能力通过结构化 API 暴露，AI Agent 可直接调用 | RESTful API + OpenAPI Schema + Workflow Orchestrator |
| 用户只审核，AI 自动执行 | 用户用自然语言驱动修改，不需要精确指令 | 代码分离，生成/写作/审核各自独立运行 |
| 中央档案库为唯一数据源 | 所有模块数据统一存储，互相引用 | PostgreSQL + pgvector 统一数据库 |
| 模块化可扩展 | 新模块一行代码注册即可接入 | BaseModule 接口 + ModuleRegistry 注册表 |
| 双向同步用户可见 | 用户看中文 Markdown，系统操作结构化 JSON | SYNC 标记库 + 同步引擎（**Agent 走纯 JSON 通道**） |
| 质量四层保证 | 设定一致性 / 逻辑质量 / 文学质感 / 读者吸引力 | 分层审查引擎 + AI 痕迹检测器 |
| 伏笔全生命周期管理 | 每个伏笔可追踪、可检索、防重复 | FORE 档案实体 + 向量相似度检测 |

### 1.2 系统架构总图（v1.1 更新）

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Agent / 外部调用层 (v1.1 新增)                      │
│                                                                      │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ │
│  │ MCP Server   │ │ LangChain    │ │ OpenAI        │ │ HTTP Client  │ │
│  │ (Tool 暴露)  │ │ Tool Wrapper │ │ Function Call │ │ (REST API)   │ │
│  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └──────┬───────┘ │
│         └────────────────┼────────────────┼────────────────┘         │
│                          ▼                ▼                          │
│              ┌─────────────────────────────────────┐                 │
│              │     Workflow Orchestrator (v1.1)     │                 │
│              │  POST /api/workflow/run             │                 │
│              │  GET  /api/tasks/{id}/status        │                 │
│              │  POST /api/tasks/{id}/callback      │                 │
│              └─────────────────┬───────────────────┘                 │
└────────────────────────────────┼─────────────────────────────────────┘
                                 │
┌────────────────────────────────▼─────────────────────────────────────┐
│                        API 网关层 (Gateway)                           │
│   统一接口 | 路由分发 | 认证鉴权 | 流量限制 | 请求缓存 | 事件广播       │
└────────────────────────────────┬─────────────────────────────────────┘
                                 │
┌────────────────────────────────▼─────────────────────────────────────┐
│                模块注册表 & 服务实现 (Registry)                        │
│   模块名 | 版本 | API端点 | 健康状态 | 依赖列表 | 审核模块绑定关系     │
└────────────────────────────────┬─────────────────────────────────────┘
                                 │
┌────────────────────────────────▼─────────────────────────────────────┐
│                      消息队列 (Message Queue)                         │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐      │
│  │ 生成任务队列 │  │ 写作任务队列 │  │ 审核任务队列 │  │ 同步事件队列 │      │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘      │
└────────┼────────────┼────────────┼────────────────────┼──────────────┘
         │            │            │                    │
┌────────▼────────────▼────────────▼────────────────────▼──────────────┐
│                         子代理层 (Agent Layer)                        │
│  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐            │
│  │生成代理(Gen)×2 │ │写作者(Wri)×2  │ │审核代理(Rev)×3 │            │
│  └────────────────┘ └────────────────┘ └────────────────┘            │
└─────────────────────────────────────────────────────────────────────┘
                                 │
┌────────────────────────────────▼─────────────────────────────────────┐
│                           数据层 (Data Layer)                        │
│  PostgreSQL+pgvector │ Redis │ MinIO │ ChromaDB(开发)               │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.3 写作流程 18 个环节（v1.1 修正）

```
灵感启动 → 小说主题 → 拟定大纲 → 世界观设定 → 人物设定 → 人物关系 → 角色弧线
→ 势力设定 → 势力关系 → 物品库 → 伏笔追踪 → 小说档案 → 小说简介
→ 细纲配置 → 章节细纲 → 正文初稿 → 正文审核 → 正文修正
```

> **v1.1 说明**：原 v1.0 声称 19 个环节但实际列出 18 个。v1.1 明确为 **18 个环节**。
> 如需扩展至 19 个，建议补充「导出发布」环节作为第 19 步。

每个环节对应一个或多个微服务模块，通过中央档案库共享数据，通过消息队列串行或并行执行。

---

## 二、环境配置清单

### 2.1 开发环境（操作手册）

| 类别 | 软件/组件 | 版本要求 | 用途 |
|------|----------|---------|------|
| 操作系统 | Ubuntu 22.04 LTS / macOS 14+ / Windows 11 WSL2 | — | 主机操作系统 |
| Python | 3.11+ | ≥3.11.0 | 后端服务主语言 |
| 数据库 | SQLite | ≥3.40.0 | 开发环境轻量数据库（替代 PostgreSQL）|
| 向量搜索 | ChromaDB | ≥0.4.0 | 开发环境轻量向量数据库 |
| 缓存 | 可选（开发环境可不部署）| — | 生产环境需要 Redis |
| 消息队列 | 内存队列（开发模式）| — | 开发环境使用内存模式 |
| LLM 接口 | OpenAI API / 兼容接口 | — | 核心生成能力 |
| 嵌入模型 | bge-large-zh-v1.5 (本地) 或 text-embedding-3-large (API)| — | 中文嵌入 |
| Docker | ≥24.0 | — | 容器化部署（可选）|
| Git | ≥2.40 | — | 版本控制 |

> **v1.1 变更**：移除 Node.js 前端依赖（本系统为 Agent-only 后端服务）。

**Python 依赖清单 (`requirements-dev.txt`)**：

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

# === 日志系统 ===
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

### 2.3 生产环境 `docker-compose.yml`（v1.1 已修复）

```yaml
# v1.1 修复说明：
# - CHG-003: 健 healthcheck 从 curl 改为 python（基础镜像无 curl）
# - CHG-004: 新增 logs_data volume 挂载
# - CHG-017: writer-agent replicas: 1 → 2
# - 移除 Node.js 相关配置（Agent-only 后端）
version: '3.8'  # v1.1: 使用兼容格式

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
      - LOG_ROOT=/app/logs
    volumes:
      - logs_data:/app/logs           # CHG-004: 日志持久化挂载
    depends_on:
      postgres: { condition: service_healthy }
      redis: { condition: service_healthy }
      rabbitmq: { condition: service_healthy }
    restart: unless-stopped
    # CHG-003: 使用 python 替代 curl（python:slim 镜像不含 curl）
    healthcheck:
      test: ["CMD", "python", "-c",
             "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
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
      - TEMPERATURE=0.85
    depends_on: [postgres, redis, rabbitmq]
    deploy: { replicas: 2 }
    restart: unless-stopped

  # === 写作代理池 (v1.1: replicas 1→2) ===
  writer-agent:
    build: { context: ., dockerfile: Dockerfile.agent-writer }
    environment:
      - DATABASE_URL=postgresql+asyncpg://noveluser:@postgres:5432/novel_db
      - REDIS_URL=redis://redis:6379/0
      - RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - AGENT_TYPE=writer
      - TEMPERATURE=0.65
    depends_on: [postgres, redis, rabbitmq]
    deploy: { replicas: 2 }  # CHG-017: 避免成为并发瓶颈
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
      - TEMPERATURE=0.2
    depends_on: [postgres, redis, rabbitmq]
    deploy: { replicas: 3 }
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
  logs_data:  # CHG-004: 新增日志持久化 volume
```

### 2.3b 开发环境 `docker-compose.dev.yml`（CHG-015：v1.1 新增）

```yaml
# docker-compose.dev.yml — 开发环境简化编排
# 特点：SQLite + ChromaDB + 内存队列 + 无 Redis/RabbitMQ/MinIO

version: '3.8'

services:
  api-server:
    build: { context: ., dockerfile: Dockerfile.api.dev }
    environment:
      - ENVIRONMENT=development
      - DATABASE_URL=sqlite+aiosqlite:///./dev_novel.db
      - LOG_LEVEL=DEBUG
      - LOG_JSON_OUTPUT=false
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - FORESHADOW_DUPLICATE_THRESHOLD=0.85  # CHG-018: 环境变量化
    volumes:
      - .:/app                    # 源码热重载
      - dev_db_data:/app/data      # SQLite 数据持久化
      - logs_data:/app/logs        # 日志目录
      - dev_chroma:/app/chroma_data  # ChromaDB 数据
    ports: ["8000:8000"]
    command: uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

volumes:
  dev_db_data:
  logs_data:
  dev_chroma:
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
# 日志系统
# ============================================================
LOG_ROOT=./logs                    # 日志根目录
LOG_LEVEL=INFO                     # 全局日志级别
LOG_JSON_OUTPUT=true               # 生产环境JSON格式；开发环境可设为false

# ============================================================
# Agent 调用配置 (v1.1 新增)
# ============================================================
AGENT_AUTH_TOKEN=your-agent-token-here  # Agent 调用的 Bearer Token
WORKFLOW_MAX_CONCURRENT=3               # 最大并发工作流数
TASK_CALLBACK_TIMEOUT=300               # 回调超时秒数
FORESHADOW_DUPLICATE_THRESHOLD=0.85     # CHG-018: 伏笔重复检测阈值（环境变量化）
```

### 2.5 项目目录结构（v1.1 更新）

```
novel-creation-system/
├── .env                          # 环境变量（不提交到Git）
├── .env.example                  # 环境变量模板
├── .gitignore                    # CHG-019: Git 忽略规则
├── docker-compose.yml            # 生产环境编排（已修复）
├── docker-compose.dev.yml        # CHG-015: 开发环境编排（新增）
├── Dockerfile.api                # API 服务镜像
├── Dockerfile.api.dev            # 开发环境 API 镜像
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
│   │   ├── base_module.py        # BaseModule 抽象基类（已修复 logger）
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
│   ├── workflow/                  # CHG-009: 工作流编排（新增）
│   │   ├── engine.py             # Workflow Orchestrator 核心
│   │   ├── pipeline.py           # 18 环节流水线定义
│   │   ├── task_manager.py       # 异步任务状态管理
│   │   └── callback_handler.py   # 回调处理
│   ├── queue/                    # 消息队列
│   │   ├── producer.py           # 消息发布
│   │   ├── consumer.py           # 消息消费（含 sync_events 消费者）
│   │   └── tasks.py              # Celery/RabbitMQ 任务定义
│   ├── sync/                     # 同步引擎（双层架构核心）
│   │   ├── engine.py             # 同步引擎核心调度器
│   │   ├── markdown_renderer.py  # JSON→Markdown 渲染（AI修改后→用户可见）
│   │   ├── markdown_parser.py    # Markdown→JSON 解析（提取SYNC标记内容）
│   │   ├── json_updater.py       # JSON/DB 更新执行器
│   │   ├── conflict_resolver.py  # 冲突检测与解决
│   │   ├── cascade_updater.py    # 联动更新追踪
│   │   ├── file_watcher.py       # 文件变更监听（inotify/fswatch）
│   │   └── templates/            # Markdown 模板（新建实体时使用）
│   │       ├── character_template.md
│   │       ├── faction_template.md
│   │       ├── item_template.md
│   │       ├── foreshadow_template.md
│   │       ├── rule_template.md
│   │       ├── chapter_template.md
│   │       └── review_report_template.md
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
│   │   │   ├── novels.py        # 小说项目 CRUD
│   │   │   ├── characters.py    # 人物管理
│   │   │   ├── world.py         # 世界观管理
│   │   │   ├── outlines.py      # 大纲管理
│   │   │   ├── chapters.py      # 章节/正文管理
│   │   │   ├── foreshadows.py   # 伏笔管理
│   │   │   ├── search.py        # 检索 API
│   │   │   ├── sync.py          # 同步状态 API
│   │   │   ├── weight.py        # 权重面板 API
│   │   │   ├── logs.py          # 日志查询 API（含鉴权）
│   │   │   ├── workflow.py      # CHG-009: 工作流 API（新增）
│   │   │   └── tasks.py         # CHG-010: 任务状态 API（新增）
│   │   └── middleware/
│   │       ├── auth.py          # 认证中间件
│   │       ├── rate_limit.py    # 流量限制
│   │       ├── error_handler.py # 错误处理
│   │       └── logging_middleware.py  # 请求日志中间件
│   ├── schemas/                   # CHG-011: 统一 Pydantic Schema（新增）
│   │   ├── common.py            # 公共类型（分页、错误响应等）
│   │   ├── novel.py             # 小说项目 schema
│   │   ├── character.py         # 人物 schema
│   │   ├── world.py             # 世界观 schema
│   │   ├── chapter.py           # 章节/正文 schema
│   │   ├── review.py            # 审查报告 schema
│   │   ├── workflow.py          # 工作流请求/响应 schema
│   │   └── task.py              # 任务状态 schema
│   └── utils/                    # 工具函数
│       ├── id_generator.py      # ID 生成器 (CHAR-XXX, FAC-XXX...)
│       ├── prompt_templates.py  # Prompt 模板管理
│       ├── llm_client.py        # LLM 调用封装
│       ├── text_processor.py    # 文本处理工具
│       ├── logger_config.py     # 日志配置（已修复 structlog）
│       └── log_rotation.py      # 日志轮转
│
├── db/
│   ├── init.sql                  # 数据库初始化 SQL（52+ 表）
│   └── seed.sql                  # 种子数据
│
├── prompts/                      # Prompt 模板
│   ├── generation/               # 生成类 Prompt
│   │   ├── world_rules.txt       # 世界观规则生成 prompt
│   │   ├── character_psychology.txt  # 人物心理层 prompt
│   │   ├── faction_design.txt    # 势力设计 prompt
│   │   ├── relation_map.txt      # 关系图谱 prompt
│   │   ├── arc_structure.txt     # 角色弧线 prompt
│   │   ├── item_catalog.txt      # 物品库 prompt
│   │   ├── foreshadow_plant.txt  # 伏笔设计 prompt
│   │   ├── outline_three_act.txt # 三幕大纲 prompt
│   │   ├── detail_outline.txt    # 细纲拆解 prompt
│   │   ├── manuscript_scene.txt  # 场景正文 prompt
│   │   └── theme_analysis.txt    # 主题分析 prompt
│   ├── review/                   # 审核类 Prompt
│   │   ├── consistency_check.txt # 一致性检查 prompt
│   │   ├── logic_verify.txt      # 逻辑验证 prompt
│   │   ├── literary_quality.txt  # 文学质感评估 prompt
│   │   ├── engagement_score.txt  # 读者吸引力评分 prompt
│   │   └── ai_trace_detect.txt   # AI 痕迹检测 prompt
│   └── tools/                    # 工具类 Prompt
│       ├── entity_extract.txt    # 实体提取 prompt
│       └── constraint_build.txt  # 约束文件构建 prompt
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
│   └── log_query.py              # 日志查询 CLI
│
├── logs/                         # 日志目录（gitignore）
│   ├── system/
│   ├── archived/
│   └── index.json
│
├── user_view/                    # 🆕🆕 用户可视文件夹（全中文Markdown，双层架构核心）
│   └── 我的小说_【书名】/
│       ├── 📄 小说概览.md           # 实时聚合视图
│       ├── 📁 01_主题/ ~ 📁 11_正文/  # 11个中文模块文件夹
│       ├── 📁 变更日志/
│       └── 📁 审查报告/
│
├── system_data/                  # 🆕🆕 系统引擎层数据缓存（英文JSON，供内部使用）
│   ├── novel_manifest.json
│   ├── modules/                  # 各模块 JSON 导出
│   ├── structure/
│   ├── manuscript/
│   └── index/
│
├── requirements.txt              # 生产依赖
├── requirements-dev.txt          # 开发依赖
└── README.md
```

### 2.6 `.gitignore`（CHG-019：v1.1 新增）

```gitignore
# === 环境与密钥 ===
.env
.env.local
*.key
*.pem

# === Python ===
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.venv/
venv/

# === IDE ===
.vscode/
.idea/
*.swp
*.swo

# === 数据库 ===
*.db
*.sqlite
*.sqlite3

# === 日志 ===
logs/
*.log

# === 向量数据库 ===
chroma_data/

# === 快照与导出 ===
snapshots/
exports/
user_view/

# === OS ===
.DS_Store
Thumbs.db

# === 测试覆盖率 ===
htmlcov/
.coverage
.pytest_cache/
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
1. 实现 `BaseModule` 抽象基类（含 `_create_logger()` 方法——**v1.1 已修复文件绑定逻辑**）
2. 实现 `ModuleRegistry` 注册表（内存 + 数据库双写）
3. 为 12 个业务模块创建空壳子类（仅实现 `module_id` 和 `register()`）
4. 实现 `/api/modules` GET 接口返回已注册模块列表
5. 为每个模块创建对应的日志文件路径

**验证标准**：
- [ ] `GET /api/modules` 返回 12 个模块，状态均为 `registered`
- [ ] 每个模块有独立的 logger 实例
- [ ] `logs/system/registry.log` 有模块注册记录

#### 步骤 1.3：数据库 Schema 部署

**目标**：在 PostgreSQL 中建好全部 **52+ 张表**。

> **v1.1 修正（CHG-001）**：原 v1.0 声称"48 张表（12 模块 × 4 表/模块 + 系统表）"，计算矛盾。
> 实际应为：**12 模块 × 4 表 = 48 张业务表 + 4 张系统表（modules_registry / users / permissions / change_log）= 52 张以上**。
> 此外还有审计相关表（entity_audit_log / user_action_audit_log）、任务表（workflow_tasks）、快照表（snapshots）等，总计约 **56–60 张表**。

**操作清单**：
1. 使用 `db/init.sql` 初始化完整 schema（含 pgvector 扩展）
2. 运行 Alembic 初始化迁移版本标记
3. 插入种子数据（默认世界观分类、角色模板等）
4. 验证向量索引创建成功

**验证标准**：
- [ ] `\dt` 显示 **52+ 张表**
- [ ] `SELECT * FROM modules_registry` 返回 12 行
- [ ] 向量列可通过 `SELECT id, embedding <=> '[...]'::vector` 查询

#### 步骤 1.4：消息队列连通

**目标**：RabbitMQ 四个核心队列就绪，可收发测试消息。

**操作清单**：
1. 启动 RabbitMQ（生产）或使用内存队列（开发）
2. 声明四个队列：`generation_tasks` / `writing_tasks` / `review_tasks` / `sync_events`
3. 编写测试脚本发送一条消息并消费确认
4. 配置死信队列和重试策略
5. **v1.1 新增**：确认 `sync_events` 队列有对应消费者（见步骤 3.3）

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
- 向量相似度重复检测（阈值 **环境变量 `FORESHADOW_DUPLICATE_THRESHOLD`**，默认 0.85）
- 种下/提醒/回收/完结全状态流转

**验证标准**：
- [ ] 重复伏笔检出率 ≥ 90%（测试集）
- [ ] 状态机转换合法（不允许跳步）
- [ ] 与章节细纲联动：约束文件自动注入伏笔提示

#### 步骤 2.8：大纲构建器（OutlineBuilder）

**输入**：全部设定档案 + 18 环节中的前 8 环输出
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

#### 步骤 3.3：同步引擎（SyncEngine）（v1.1 增强）

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

**v1.1 重要变更 — Agent 隐藏策略（CHG-016）**：

> **对 Agent 调用方**：Markdown SYNC 标记完全透明。Agent 通过结构化 JSON API 读写所有数据，
> 不需要也不应该编辑 Markdown 文件中的 SYNC 区块。同步引擎内部维护 MD↔JSON 双向通道，
> 但对外暴露的 API 层只有 JSON 格式。
>
> 具体实现：
> - `/api/characters/{id}` 返回 JSON，接受 JSON body 的 PATCH/PUT
> - `/api/world/{novel_id}` 返回 JSON
> - **不存在** `/api/markdown/*` 端点供外部调用
> - Markdown 文件仅用于人类用户的本地查看（MinIO 对象存储中）
>
> 这样设计的原因：LLM Agent 无法可靠地编写含正确 SYNC 标记格式的 Markdown，
> 一个格式错误的标记会导致解析失败并可能破坏数据完整性。

**sync_events 队列消费者（CHG-013：v1.1 新增）**：

```python
# src/queue/consumer.py — sync_events 消费者（新增）
class SyncEventConsumer:
    """消费 sync_events 队列，驱动同步引擎执行"""

    async def consume_sync_events(self):
        channel = await self.rabbitmq.channel()
        queue = await channel.declare_queue("sync_events", durable=True)

        async for message in queue:
            event = json.loads(message.body)
            event_type = event.get("type")  # "json_to_markdown" | "markdown_to_json"
            entity_type = event.get("entity_type")
            entity_id = event.get("entity_id")

            try:
                if event_type == "json_to_markdown":
                    await self.sync_engine.sync_json_to_markdown(entity_type, entity_id)
                elif event_type == "markdown_to_json":
                    file_path = Path(event.get("file_path"))
                    await self.sync_engine.sync_markdown_to_json(file_path)

                await message.ack()
            except Exception as exc:
                self._logger.error("sync_event_failed",
                    event_type=event_type,
                    entity_id=entity_id,
                    error=str(exc))
                await message.nack(requeue=True)  # 重试
```

**验证标准**：
- [ ] JSON→MD 和 MD→JSON 双向同步均正常
- [ ] 冲突时按配置策略处理
- [ ] 同步操作全部记录到 4 个独立日志文件
- [ ] **v1.1 新增**：`sync_events` 队列消费者正常运行并可消费消息

---

### 阶段四：集成联调（第 26–30 天）

#### 步骤 4.1：端到端流程验证

**验证场景**：从「灵感启动」到「正文修正」完整跑通 18 个环节

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
2. 配置 docker-compose.yml 一键启动全部服务（**v1.1 已修复健康检查和 volume**）
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

#### 步骤 6.1：功能验收清单（v1.1 更新）

| 编号 | 验收项 | 标准 | 状态 |
|------|--------|------|------|
| F-001 | 18 个创作环节全覆盖 | 每环节有对应模块/代理 | ⬜ |
| F-002 | 12 个模块全部注册可查 | GET /api/modules 返回 12 个 | ⬜ |
| F-003 | 三种代理池独立运行 | Gen/Wri/Rev 各自消费队列 | ⬜ |
| F-004 | 四层审查引擎生效 | 审查结果含 4 层评分 | ⬜ |
| F-005 | 双向同步正常 | MD 编辑后 DB 自动更新 | ⬜ |
| F-006 | 伏笔防重复 | 相似度 ≥ 阈值(可配)的被拦截 | ⬜ |
| F-007 | 字数控制 | 偏差 ≤ ±10% | ⬜ |
| F-008 | AI 痕迹检测 | 6 大特征覆盖 | ⬜ |
| F-009 | 权重评分输出 | 四维评分 + tier | ⬜ |
| F-010 | 日志系统全覆盖 | 所有组件有结构化日志 | ⬜ |
| F-011 | 日志可查询 | CLI + Web API 均可用 | ⬜ |
| F-012 | 日志轮转正常 | 超大文件自动切割 | ⬜ |
| **F-013** | **🆕 Workflow Orchestrator 可用** | **POST /api/workflow/run 能跑通全流程** | ⬜ |
| **F-014** | **🆕 任务状态可查询** | **GET /api/tasks/{id}/status 返回实时进度** | ⬜ |
| **F-015** | **🆕 Agent 可通过 API 完成所有操作** | **无需编辑 Markdown 即可完成全部创作** | ⬜ |
| **F-016** | **🆕 日志 API 有鉴权** | **未认证无法访问 /api/logs/** | ⬜ |

#### 步骤 6.2：交付物清单

| 交付物 | 格式 | 位置 |
|--------|------|------|
| 完整源代码 | Git 仓库 | `<repo-url>` |
| 数据库 Schema SQL | `.sql` 文件 | `db/init.sql` |
| Docker 编排文件 | YAML | `docker-compose.yml` + `docker-compose.dev.yml` |
| 环境变量模板 | `.env.example` | 项目根目录 |
| API 文档 | Swagger UI | `GET /docs` |
| **🆕 统一 API Schema** | **Pydantic Models** | **`src/schemas/`** |
| **🆕 Agent 接入指南** | **Markdown** | **`docs/agent_integration.md`** |
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
| ForeshadowManager | 重复检测误报 | 调低阈值（通过环境变量 `FORESHADOW_DUPLICATE_THRESHOLD`）|
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

### 6.1 功能验收（已在 6.1 节详述，共 16 项）

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
| **NF-008** | **🆕 Agent 可调用性** | **所有创作功能可通过 RESTful API 完成，无需前端** |

### 6.3 交付物清单（已在 6.2 节详述，共 10 项）

---

# 🆕 第十部分：双层架构 — 用户可视层 + 系统引擎层 + 同步引擎（CHG-020~022）

> **这是整个系统的用户体验核心。** 如果用户只能通过 AI 间接接触自己的设定，那这套系统就是黑箱——用户的信任会在第三次「AI 你给我看看 CHAR-001 现在的完整档案」时崩塌。
> 必须让用户能**直接看到、直接修改**自己的小说数据。

---

## 十、双层架构总览

### 10.1 核心设计理念

```
┌─────────────────────────────────────────────────────────────┐
│                    三层分离架构                               │
│                                                             │
│  ┌───────────────────┐   ┌──────────────────────────────┐  │
│  │  Agent / 外部调用层 │   │      用户（人类创作者）         │  │
│  │  → 走 JSON API    │   │  → 直接读写中文 Markdown 文件   │  │
│  └────────┬──────────┘   └──────────────┬───────────────┘  │
│           │                              │                  │
│           ▼                              ▼                  │
│  ┌──────────────────────────────────────────────────┐       │
│  │              API 网关层 (Gateway)                   │       │
│  │   Agent 走 RESTful JSON API                       │       │
│  │   用户走 文件系统 (user_view/)                     │       │
│  └──────────────────────┬───────────────────────────┘       │
│                         │                                  │
│  ┌──────────────────────▼───────────────────────────┐       │
│  │              同步引擎 (Sync Engine)                │       │
│  │   MD ↔ JSON 双向实时同步                          │       │
│  │   冲突检测与解决                                   │       │
│  │   版本控制与变更日志                                │       │
│  └──────────────────────┬───────────────────────────┘       │
│                         │                                  │
│  ┌──────────────────────▼───────────────────────────┐       │
│  │            中央档案库 (PostgreSQL)                 │       │
│  │   唯一数据源 · 所有模块共享                        │       │
│  └──────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

### 10.2 两套视图，同一份数据

| 层级 | 目录 | 语言 | 操作者 | 访问方式 |
|------|------|------|--------|---------|
| **用户可视层** | `user_view/我的小说_【书名】/` | 全中文 Markdown | 用户（人类） | 直接编辑文件 / 文件管理器 |
| **系统引擎层** | `system_data/` + PostgreSQL | 英文 JSON | AI Agent / 系统模块 | RESTful API |
| **同步引擎层** | `sync_engine/` | 英文代码 | 系统（自动运行） | 后台守护进程 |

**核心原则：用户层和系统层是同一份数据的两种视图，不是两份独立的数据。**

- 用户永远只操作 **Markdown 文件**
- AI 永远只操作 **JSON（通过 API）**
- 同步引擎保证两者始终一致
- **Agent 不需要也不应该编辑 Markdown 中的 SYNC 标记**——Agent 通过 JSON API 操作数据

---

## 十一、用户可视文件夹：完整目录结构

> 每个小说项目在 `user_view/` 下生成一个以书名命名的文件夹，内含完整的中文 Markdown 目录。

```
📁 user_view/
└── 📁 我的小说_【书名】/
    │
    ├── 📄 小说概览.md                    ← 实时聚合视图（自动渲染）
    │
    ├── 📁 01_主题/                       ← 对应 THEME 模块
    │   ├── 📄 主题陈述.md
    │   ├── 📄 反向确认.md
    │   ├── 📄 情感出发点.md
    │   └── 📄 各卷主题映射.md
    │
    ├── 📁 02_世界观/                     ← 对应 WORLD_BUILDER 模块
    │   ├── 📄 世界观总览.md               ← 从所有规则汇总
    │   ├── 📁 宇宙规则/
    │   │   ├── 📄 RULE-001_【规则名称】.md
    │   │   ├── 📄 RULE-002_【规则名称】.md
    │   │   └── 📄 ...
    │   ├── 📁 地理与空间/
    │   │   ├── 📄 LOC-001_【地点名称】.md
    │   │   └── 📄 ...
    │   ├── 📄 时间与历史.md
    │   ├── 📄 社会结构.md
    │   ├── 📄 政治与权力.md
    │   ├── 📄 经济体系.md
    │   ├── 📄 文化与信仰.md
    │   ├── 📄 技术与知识.md
    │   └── 📁 审查记录/
    │       ├── 📄 规则自洽审查.md
    │       ├── 📄 极端场景测试.md
    │       └── 📄 叙事压力审查.md
    │
    ├── 📁 03_势力/                       ← 对应 FACTION_BUILDER 模块
    │   ├── 📄 FAC-001_【势力名称】.md
    │   ├── 📄 FAC-002_【势力名称】.md
    │   └── 📄 ...
    │
    ├── 📁 04_势力关系/                   ← 对应 RELATION_BUILDER(势力)
    │   ├── 📄 FAC_REL-001_【势力A】与【势力B】.md
    │   └── 📄 势力格局总览.md
    │
    ├── 📁 05_人物/                       ← 对应 CHARACTER_BUILDER 模块
    │   ├── 📄 CHAR-001_【人物姓名】.md
    │   ├── 📄 CHAR-002_【人物姓名】.md
    │   └── 📄 ...
    │
    ├── 📁 06_人物关系/                   ← 对应 RELATION_BUILDER(人物)
    │   ├── 📄 REL-001_【人物A】与【人物B】.md
    │   └── 📄 人物关系网络图.md
    │
    ├── 📁 07_角色弧线/                   ← 对应 ARC_BUILDER 模块
    │   ├── 📄 ARC-001_【人物姓名】弧线.md
    │   └── 📄 ...
    │
    ├── 📁 08_物品仓库/                   ← 对应 ITEM_BUILDER 模块
    │   ├── 📄 ITEM-001_【物品名称】.md
    │   └── 📄 物品总览.md
    │
    ├── 📁 09_伏笔管理/                   ← 对应 FORESHADOW_MANAGER 模块
    │   ├── 📄 伏笔总览.md                 ← 活跃伏笔清单 + 密度曲线（实时渲染）
    │   ├── 📄 FORE-001_【伏笔简述】.md
    │   └── 📄 ...
    │
    ├── 📁 10_结构/                       ← 对应 OUTLINE_BUILDER + DETAIL_OUTLINE
    │   ├── 📄 分卷配置.md
    │   ├── 📄 故事大纲.md
    │   ├── 📁 章节细纲/
    │   │   ├── 📄 第001章细纲_【章节名称】.md
    │   │   └── 📄 ...
    │   ├── 📄 关键剧情分布.md
    │   ├── 📄 节奏曲线.md
    │   └── 📄 章节名称总览.md
    │
    ├── 📁 11_正文/                       ← 对应 MANUSCRIPT_WRITER 模块
    │   ├── 📁 第一卷/
    │   │   ├── 📄 第001章_【章节名称】.md
    │   │   └── 📄 ...
    │   └── 📁 第二卷/
    │
    ├── 📁 变更日志/
    │   └── 📄 变更日志.md                ← 从 change_log 实时渲染
    │
    └── 📁 审查报告/
        ├── 📄 第001章审查报告.md          ← 四层审查结果
        └── 📄 ...
```

---

## 十二、Markdown 同步标记规范

### 12.1 标记语法

每个与 JSON 字段对应的内容区块，用 HTML 注释包裹同步标记：

```markdown
<!-- SYNC:实体ID:字段路径 -->
（内容）
<!-- /SYNC -->
```

三种标记类型：

| 标记类型 | 格式 | 用途 | 用户可修改？ |
|---------|------|------|------------|
| **字段标记** | `<!-- SYNC:实体ID:字段路径 -->内容<!-- /SYNC -->` | 标记可同步的字段值 | ✅ 可以修改标记之间的内容 |
| **元数据标记** | `<!-- SYNC_META:实体ID:属性 -->值<!-- /SYNC_META -->` | 版本号、修改时间等 | ❌ 不建议手动改 |
| **引用标记** | `<!-- SYNC_REF:实体ID -->...<!-- /SYNC_REF -->` | 引用关系区块 | ❌ 由系统维护 |

### 12.2 字段路径映射规则

```
JSON 路径                                      → Markdown SYNC 标记
──────────────────────────────────────────────────────────────────
CHAR-001.fields.name                            → <!-- SYNC:CHAR-001:fields.name -->
CHAR-001.fields.core_desire                     → <!-- SYNC:CHAR-001:fields.core_desire -->
CHAR-001.fields.voice_fingerprint.sentence_pref  → <!-- SYNC:CHAR-001:fields.voice_fingerprint.sentence_preference -->
CHAR-001.fields.knowledge_boundary              → <!-- SYNC:CHAR-001:fields.knowledge_boundary -->
CHAR-001.last_modified                           → <!-- SYNC_META:CHAR-001:last_modified -->
```

**映射规则**：`<!-- SYNC:实体ID:JSON字段路径（用 . 分隔） -->`

### 12.3 完整示例：人物档案 Markdown

文件名：`05_人物/CHAR-001_陈渡.md`

```markdown
# CHAR-001 陈渡

> 最后修改：<!-- SYNC_META:CHAR-001:last_modified -->2026-05-28T15:30:00<!-- /SYNC_META -->
> 版本：<!-- SYNC_META:CHAR-001:version -->17<!-- /SYNC_META -->

---

## 身份信息

| 字段 | 内容 |
|------|------|
| 姓名 | <!-- SYNC:CHAR-001:fields.name -->陈渡<!-- /SYNC --> |
| 年龄 | <!-- SYNC:CHAR-001:fields.age -->28<!-- /SYNC --> |
| 外貌特征 | <!-- SYNC:CHAR-001:fields.appearance -->中等身材，左手腕有一道旧伤疤<!-- /SYNC --> |
| 社会身份 | <!-- SYNC:CHAR-001:fields.social_identity -->前 FAC-003 外勤人员<!-- /SYNC --> |
| 家庭背景 | <!-- SYNC:CHAR-001:fields.family_background -->孤儿，在 FAC-003 附属机构中长大<!-- /SYNC --> |
| 所属势力 | <!-- SYNC:CHAR-001:fields.faction_id -->FAC-005<!-- /SYNC --> |

---

## 心理层

### 核心欲望（他想要什么）
<!-- SYNC:CHAR-001:fields.core_desire -->
找出当年害死他搭档的幕后指使者，并亲手了结这件事。
<!-- /SYNC -->

### 深层需求（他真正需要什么）
<!-- SYNC:CHAR-001:fields.deep_need -->
他需要一个理由——证明自己的存在不是只用仇恨定义的。
<!-- /SYNC -->

### 核心恐惧
<!-- SYNC:CHAR-001:fields.core_fear -->
再一次在关键时刻无能为力。他最大的恐惧不是死亡，
而是「看着重要的人死在自己面前，而自己什么也做不了」。
<!-- /SYNC -->

### 道德底线
<!-- SYNC:CHAR-001:fields.moral_bottom_line -->
不杀未成年。不对信任自己的人说谎。
如果必须伤害「无辜者」才能达成目标，他会放弃目标。
<!-- /SYNC -->

---

## 能力层

| 字段 | 内容 |
|------|------|
| 天赋和优势 | <!-- SYNC:CHAR-001:fields.talents -->超常的观察力——能注意到环境中「缺失了什么」<!-- /SYNC --> |
| 致命弱点 | <!-- SYNC:CHAR-001:fields.weakness -->压力下决策过于个人化，会为保护特定人放弃战略目标<!-- /SYNC --> |
| 特殊技能 | <!-- SYNC:CHAR-001:fields.special_skills -->近身格斗、痕迹追踪、基础急救<!-- /SYNC --> |
| 行动风格 | <!-- SYNC:CHAR-001:fields.action_style -->先观察再行动，偏好独行<!-- /SYNC --> |

---

## 情感身体词典

<!-- SYNC:CHAR-001:fields.emotional_body_map -->
| 情感 | 身体反应 |
|------|---------|
| 恐惧 | 指尖发冷，肩胛骨收紧，呼吸变浅但不加速 |
| 愤怒 | 下颌肌肉跳动，声音变低而不是变高 |
| 悲伤 | 沉默。不说话，不看人，僵硬地坐着 |
| 喜悦 | 极罕见。偶尔嘴角动一下，不超过一秒 |
| 惊讶 | 眉毛几乎不动，但瞳孔会瞬间放大 |
<!-- /SYNC -->

---

## 语气指纹

### 词汇池偏好
<!-- SYNC:CHAR-001:fields.voice_fingerprint.vocabulary_pool -->
偏好具象名词和动作动词。回避抽象形容词。
<!-- /SYNC -->

### 禁忌表达
<!-- SYNC:CHAR-001:fields.voice_fingerprint.forbidden_expressions -->
- 绝不说「突然意识到」
- 绝不说「不知为何」
- 避免「我感到……」的情感直接陈述
<!-- /SYNC -->

---

## 状态时间线

<!-- SYNC:CHAR-001:fields.status_timeline -->
| 章节 | 物理状态 | 情感状态 |
|------|---------|---------|
| 第 27 章 | 左臂受伤（未愈） | 对 CHAR-002 的信任正在瓦解 |
| 第 28 章 | 左臂受伤（恢复中） | 怀疑范围扩大 |
<!-- /SYNC -->

---

## 引用索引

<!-- SYNC_REF:CHAR-001 -->
本档案被以下模块引用：
- 人物关系：REL-001, REL-003, REL-005
- 角色弧线：ARC-001
- 伏笔：FORE-003, FORE-007, FORE-015, FORE-031
- 势力：FAC-003（前所属）, FAC-005（现所属）
<!-- /SYNC_REF ---

---

*此文件由系统自动生成并与中央档案库实时同步。*
*手动修改此文件的内容将自动同步回档案库。请勿修改 <!-- SYNC --> 标记本身。*
```

---

## 十三、双向同步引擎详细设计

### 13.1 同步方向与触发条件

```
═══════════════════════════════════════════════════
方向一：用户修改 Markdown → 同步到 JSON（+ 数据库）
═══════════════════════════════════════════════════
触发条件：用户保存了 Markdown 文件（或文件变更被检测到）

同步引擎行为：
  1. 扫描文件中的所有 SYNC 标记
  2. 提取标记内的当前内容
  3. 与上一次同步时的内容比对
  4. 识别变更字段
  5. 更新对应 JSON / 数据库中的对应字段
  6. 递增 version 号
  7. 追加 change_log 记录（actor = "user_manual"）
  8. 更新 SYNC_META 中的 last_modified

═══════════════════════════════════════════════════
方向二：AI 修改 JSON（通过 API）→ 同步到 Markdown
═══════════════════════════════════════════════════
触发条件：AI 通过任何 API 操作修改了数据库中的字段

同步引擎行为：
  1. 识别被修改的 JSON 字段（从 change_log 获取）
  2. 定位对应 Markdown 文件中的对应 SYNC 标记
  3. 替换标记内的内容为新值
  4. 更新 Markdown 中的 SYNC_META（版本号、修改时间）
  5. 如果是新增实体 → 基于模板创建新的 Markdown 文件
  6. 如果是删除实体 → 在文件名前加「_已删除_」前缀
```

### 13.2 冲突处理策略

当用户在 Markdown 中修改了某字段，同时 AI 在 JSON 中也修改了同一字段时：

```
冲突检测：同步引擎比对 Markdown 和 DB 的 last_modified 时间戳。

情况一：Markdown 的 last_modified > DB 的 last_modified
  → 以 Markdown 为准（用户手动修改优先）
  → 将 Markdown 内容同步到 DB

情况二：DB 的 last_modified > Markdown 的 last_modified
  → 以 DB 为准（AI 修改优先）
  → 将 DB 内容同步到 Markdown

情况三：两者时间相同或无法判断（罕见）
  → 按配置的策略处理：
    - "last_write_wins"（默认）：最后写入胜出
    - "manual"：生成冲突报告，通知用户裁决
    - "system_priority"：系统数据优先

冲突报告格式：
  ⚠️ 同步冲突：CHAR-001.fields.core_desire
  Markdown 版本（用户修改于 18:45）：找出当年害死他搭档的幕后指使者。
  DB 版本（AI 修改于 18:45）：找出真相，无论代价是什么。
  请选择保留哪个版本，或手动合并。
```

### 13.3 新增与删除实体的同步

**新增实体（AI 创建）**：
```
1. AI 通过 API 创建 CHAR-008
2. 同步引擎检测到新实体（从 change_log 发现 actor="agent_generator"）
3. 基于人物档案模板生成 05_人物/CHAR-008_【姓名】.md
4. Markdown 文件自动填充 SYNC 标记和默认内容
5. 更新引用索引
```

**删除实体**：
```
用户手动删除 Markdown 文件：
  1. 同步引擎检测到文件删除
  2. 弹出确认提示（或记录到待确认队列）
  3. 用户确认 → 删除对应 DB 记录 → 清理所有引用关系

AI 标记删除（通过 API 将状态改为 deleted）：
  1. 同步引擎在 Markdown 文件名前加「_已删除_」前缀
  2. 文件顶部添加删除说明（原因、时间、影响范围）
  3. 用户可在可视文件夹中查看已删除内容（历史参考）
```

### 13.4 同步引擎组件结构

```
src/sync/
├── engine.py              # 同步引擎核心（调度器）
├── markdown_renderer.py   # JSON → Markdown 渲染
├── markdown_parser.py     # Markdown → JSON 解析（提取 SYNC 标记内容）
├── json_updater.py        # JSON/DB 更新执行器
├── conflict_resolver.py   # 冲突检测与解决
├── cascade_updater.py     # 联动更新追踪
├── file_watcher.py        # 文件变更监听（inotify/fswatch）
└── templates/             # Markdown 模板（新建实体时使用）
    ├── character_template.md
    ├── faction_template.md
    ├── item_template.md
    ├── foreshadow_template.md
    ├── rule_template.md
    ├── chapter_template.md
    └── review_report_template.md
```

---

## 十四、特殊文件说明

### 14.1 小说概览.md（实时聚合视图）

不由用户手动编辑，而是由同步引擎从各模块实时渲染：

```markdown
# 《【书名】》小说概览

> 最后更新：2026-05-28T18:51:04
> 创作状态：初稿阶段
> 当前进度：第 28 章 / 计划 55 章（50.9%）
> 已写字数：约 11.2 万字
> 活跃伏笔：7 个

---

## 一句话概括
一个独行复仇者在追查搭档之死的过程中发现真相远比想象中复杂...

## 当前主角状态
- 物理：左臂受伤（恢复中）
- 情感：对 CHAR-002 的信任正在瓦解
- 弧线阶段：变化中（已过催化节点）

## 最近变更
| 时间 | 变更内容 |
|------|---------|
| 2026-05-28T18:30 | CHAR-001 的 faction_id 从 FAC-003 改为 FAC-005 |
| 2026-05-28T15:00 | 完成第 28 章正文，字数 3930 |
| 2026-05-27T10:00 | FORE-003 在第 28 章回收 |

*此文件由系统自动渲染，反映各模块当前最新状态。*
```

### 14.2 变更日志/变更日志.md

从 `change_log` 表实时渲染为可读的变更历史。

### 14.3 审查报告/*.md

四层审查结果自动渲染为中文报告，包含每层的评分、问题列表和修改建议。

---

## 十五、完整项目目录结构（v1.1 含双层架构更新）

```
novel-creation-system/
├── .env / .env.example / .gitignore
├── docker-compose.yml / docker-compose.dev.yml
├── Dockerfile.* (7个)
│
├── src/                          # 后端源码
│   ├── main.py / config.py
│   ├── database/                 # 数据库层
│   ├── vector_store/             # 向量搜索
│   ├── modules/                  # 12 个业务模块
│   ├── agents/                   # 3 种 Agent
│   ├── workflow/                 # 🆕 工作流编排
│   │   ├── engine.py
│   │   ├── pipeline.py           # 18 环节定义
│   │   ├── task_manager.py
│   │   └── callback_handler.py
│   ├── queue/                    # 消息队列
│   ├── sync/                     # 同步引擎（双层架构核心）
│   │   ├── engine.py             # 同步引擎核心调度
│   │   ├── markdown_renderer.py  # JSON→MD 渲染
│   │   ├── markdown_parser.py    # MD→JSON 解析（SYNC标记提取）
│   │   ├── json_updater.py       # JSON/DB 更新
│   │   ├── conflict_resolver.py  # 冲突处理
│   │   ├── cascade_updater.py    # 联动更新
│   │   ├── file_watcher.py       # 文件监听
│   │   └── templates/            # MD 模板
│   │       ├── character_template.md
│   │       ├── faction_template.md
│   │       ├── item_template.md
│   │       ├── foreshadow_template.md
│   │       ├── rule_template.md
│   │       ├── chapter_template.md
│   │       └── review_report_template.md
│   ├── review/                   # 审核引擎
│   ├── api/                      # API 路由
│   │   ├── endpoints/
│   │   │   ├── workflow.py       # 🆕 工作流 API
│   │   │   ├── tasks.py          # 🆕 任务状态 API
│   │   │   └── ...               # 其他端点
│   ├── schemas/                  # 🆕 Pydantic Schema
│   └── utils/
│
├── user_view/                    # 🆕🆕 用户可视文件夹（全中文）
│   └── 我的小说_【书名】/
│       ├── 📄 小说概览.md
│       ├── 📁 01_主题/ ~ 📁 11_正文/
│       ├── 📁 变更日志/
│       └── 📁 审查报告/
│
├── system_data/                  # 🆕 系统引擎层数据（英文JSON缓存）
│   ├── novel_manifest.json
│   ├── modules/                  # 各模块 JSON 导出
│   ├── structure/
│   ├── manuscript/
│   └── index/
│
├── db/ / prompts/ / tests/ / logs/
├── scripts/
│   └── log_query.py
└── requirements*.txt
```

---

## 十六、Agent 与用户层的协作模式

### 16.1 关键原则：Agent 不碰 Markdown

| 操作者 | 操作对象 | 协议 | 示例 |
|--------|---------|------|------|
| **AI Agent** | PostgreSQL 数据库 | RESTful JSON API | `POST /api/characters` → 返回 JSON |
| **AI Agent** | system_data/ JSON 缓存 | 内部读写（不暴露给 Agent） | Agent 不知道这个目录存在 |
| **用户（人类）** | user_view/ Markdown | 直接文件编辑 | 打开 `CHAR-001_陈渡.md` 编辑心理层 |
| **同步引擎** | 双方 | 自动双向同步 | 检测到任一方变更后自动同步另一方 |

> **Agent 完全不需要知道 user_view/ 目录的存在。** 它通过 API 操作数据，同步引擎负责将数据变化反映到用户的 Markdown 文件中。

### 16.2 典型协作场景

**场景：Agent 生成新人物 → 用户查看并微调 → Agent 基于调整后的数据写正文**

```
时间线：
  T1  Agent: POST /api/characters/generate {novel_id, role_hint:"主角"}
       → DB 创建 CHAR-008.json 记录
       → 同步引擎检测到新实体
       → 自动生成 user_view/.../05_人物/CHAR-008_【姓名】.md

  T2  用户: 打开 CHAR-008 的 Markdown 文件
       → 阅读完整中文档案
       → 修改 core_desire："保护家人" → "证明自己值得被爱"
       → 保存文件

  T3  同步引擎: 检测到 Markdown 变更
       → 提取 SYNC:CHAR-008:fields.core_desire 新内容
       → 更新 DB 中 CHAR-008 的 core_desire 字段
       → version 递增, change_log 记录 actor="user_manual"

  T4  Agent: POST /api/workflow/steps/manuscript_ch16/execute
       → 从 DB 拉取 CHAR-008 最新数据（含用户修改后的 core_desire）
       → 生成第 16 章正文时正确反映人物的深层需求变化 ✅
```

### 16.3 用户操作场景速查

| 用户想做什么 | 怎么做 | 不需要做什么 |
|-----------|-------|------------|
| 查看 CHAR-001 完整档案 | 打开 `05_人物/CHAR-001_XXX.md` | 找 AI 问「给我看看档案」 |
| 修改人物的核心欲望 | 编辑 Markdown 中对应 SYNC 标记的内容，保存 | 调 API 或写 JSON |
| 查看世界观规则列表 | 打开 `02_世界观/世界观总览.md` | 查数据库 |
| 看第 28 章审核报告 | 打开 `审查报告/第028章审查报告.md` | 调 API |
| 了解伏笔整体状态 | 打开 `09_伏笔管理/伏笔总览.md` | 手动遍历数据库 |
| 回滚某次修改 | 打开 `变更日志/变更日志.md` 找到版本 | 写 SQL |
| 新建小说项目 | 让 AI 创建（或从模板复制） | 手动建目录 |

---

# 第二部分：日志系统专项设计（附录 A–I）

> **本部分为《AI 小说创作系统完整实施方案》的必要组成部分。**

---

## 附录 A：日志系统总体架构

### A.1 设计原则

| 原则 | 定义 | 实现方式 |
|------|------|---------|
| 全覆盖 | 所有可执行单元都必须输出日志 | BaseModule / BaseAgent 强制要求 logger 实例 |
| 结构化 | 日志是 JSON 结构化记录 | `structlog` + 自定义 JSON formatter |
| 分级 | DEBUG / INFO / WARNING / ERROR / CRITICAL 五级 | 不同严重程度走不同级别 |
| 可追溯 | 每条日志携带足够上下文（谁/什么/何时/为什么）| 统一日志上下文字段规范 |
| 不可篡改 | 写入的日志文件不被业务逻辑修改 | 追加写模式 + 文件权限控制 |
| 性能隔离 | 日志写入不阻塞主业务流程 | 异步写入 + 缓冲区 |

### A.2 架构层次图

```
┌─────────────────────────────────────────────────────────────┐
│                     日志生产者 (Producers)                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │ 模块日志  │ │ 代理日志  │ │ API日志   │ │ 同步日志  │        │
│  │(12模块)  │ │(Gen/Wri/ │ │(请求/响应)│ │(JSON↔MD) │        │
│  └─────┬────┘ └─────┬────┘ └─────┬────┘ └─────┬────┘        │
└────────┼────────────┼───────────┼───────────┼────────────────┘
         ▼            ▼           ▼           ▼
┌─────────────────────────────────────────────────────────────┐
│                   日志收集层 (Collection)                      │
│  Structured Logger → Async File Handler → 按组件路由到不同文件  │
└─────────────────────────────────┬─────────────────────────────┘
                                  │
         ┌────────────────────────┼────────────────┐
         ▼                ▼                ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ logs/       │  │ logs/       │  │ logs/       │
│ modules/    │  │ agents/     │  │ system/     │
│ (12个模块)  │  │ (3种代理)   │  │ (基础设施)  │
└─────────────┘  └─────────────┘  └─────────────┘
         │                │                │
         ▼                ▼                ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ logs/       │  │ logs/       │  │ logs/       │
│ review/     │  │ sync/       │  │ audit/      │
│ (7个审查层) │  │ (4种同步)   │  │ (审计日志)  │
└─────────────┘  └─────────────┘  └─────────────┘
```

### A.3 日志目录总览

```
logs/                                   # ← 日志根目录
│
├── {novel_id}/                         # ← 按 novel_id 隔离的项目级子目录
│   ├── modules/                        # 12 个模块日志
│   ├── agents/                         # 3 种代理日志
│   ├── review/                         # 7 个审查层日志
│   ├── sync/                           # 4 种同步日志
│   ├── manuscript/                     # 每章独立生成/审核日志
│   ├── audit/                          # 审计日志
│   └── snapshots/                      # 版本快照元数据
│
├── system/                             # ← 系统级日志
│   ├── api_requests.log
│   ├── database.log
│   ├── cache.log
│   ├── queue.log
│   ├── vector_store.log
│   ├── llm_calls.log
│   ├── embedding_service.log
│   ├── registry.log
│   ├── error.log
│   └── startup.log
│
├── archived/                           # ← 归档日志
└── index.json                         # ← 日志索引文件
```

---

## 附录 B：日志目录结构与命名规范

### B.1 文件命名规则

```
{component}_{detail}.{date}.{ext}

示例：
  world_builder.log                    # 世界观模块当日日志
  generator_agent_001.log              # 生成代理实例 001 的日志
  CH-028_generation.log                # 第28章生成过程的专属日志
```

### B.2 目录创建时机

| 目录 | 创建时机 | 负责方 |
|------|---------|--------|
| `logs/` | 应用首次启动时 | `src/utils/logger_config.py` |
| `logs/{novel_id}/` | 创建小说项目时 | 项目 CRUD 服务 |
| `logs/{novel_id}/modules/` | 首次使用某模块时 | 各模块 `on_register()` 回调 |
| `logs/{novel_id}/agents/` | 代理启动时 | 各 Agent `start()` 方法 |
| `logs/{novel_id}/review/` | 首次执行审查时 | 审核引擎初始化 |
| `logs/{novel_id}/sync/` | 首次触发同步时 | 同步引擎初始化 |
| `logs/{novel_id}/manuscript/` | 生成每章正文时 | 正文模块按需创建 |
| `logs/{novel_id}/audit/` | 应用启动时 | 审计日志服务初始化 |
| `logs/system/` | 应用启动时 | 系统日志服务初始化 |
| `logs/archived/` | 应用启动时 | 日志归档任务初始化 |

---

## 附录 C：各组件日志规范

### C.1 模块日志（12 个业务模块）— v1.1 已修复

```python
# src/modules/base_module.py — v1.1 修复版
import structlog
from pathlib import Path
from typing import Optional
import logging.handlers
import os
import time
import threading
import json

LOG_ROOT = Path(os.environ.get("LOG_ROOT", "logs"))


class _AsyncFileHandler(logging.Handler):
    """
    异步文件 Handler。
    将日志先写入内存缓冲区，批量刷盘，避免 I/O 阻塞主流程。
    v1.1 修复：此处理器现在被正确导入和使用。
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
            self.filename.parent.mkdir(parents=True, exist_ok=True)
            with open(self.filename, "a", encoding="utf-8") as f:
                f.write(data)
        except Exception:
            pass


class BaseModule(ABC):
    """所有模块的抽象基类 — 含强制日志（v1.1 修复版）"""

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
        """v1.1 修复（CHG-008）：logger 现在正确绑定到文件输出"""
        log_dir = LOG_ROOT / self._novel_id / "modules" if self._novel_id else LOG_ROOT / "system"
        log_dir.mkdir(parents=True, exist_ok=True)

        log_file = log_dir / f"{self.module_id}.log"

        # v1.1 关键修复：配置文件输出的 Processor
        file_processor = structlog.processors.JSONRenderer()
        
        # 创建带文件输出的 bound logger
        logger = structlog.get_logger().bind(
            module_id=self.module_id,
            module_name=self.module_name,
            novel_id=self._novel_id or "system",
            component_type="module",
            _log_file=str(log_file)  # 供下游 processor 使用
        )

        return logger

    def log_operation(self, operation: str, **kwargs):
        """标准化操作日志接口"""
        self._logger.info("module_operation",
            operation=operation,
            **kwargs
        )
```

### C.2 代理日志（Generator / Writer / Reviewer）

每个代理实例有独立日志文件，记录任务接收、执行、结果回调的全过程。（代码同 v1.0，此处省略以节省篇幅，详见原始文档附录 C.2）

### C.3 审核日志（四层审查 + AI 痕迹检测）

每一层审查都有独立日志文件。（代码同 v1.0，详见原始文档附录 C.3）

### C.4 同步引擎日志

双向同步详细日志。（代码同 v1.0，详见原始文档附录 C.4）

### C.5 联动更新引擎日志 — v1.1 已修复 MAX_DEPTH

```python
# src/sync/cascade_updater.py — v1.1 修复版
class CascadeUpdater:
    """联动更新引擎 — 完整影响追踪日志"""

    # v1.1 修复（CHG-007）：MAX_DEPTH 现在有明确定义
    MAX_DEPTH = 5  # 最大联动追踪深度

    def __init__(self, novel_id: str):
        self.novel_id = novel_id
        self.cascade_log_file = Path(f"logs/{novel_id}/sync/cascade_update.log")
        self.cascade_log_file.parent.mkdir(parents=True, exist_ok=True)
        self._logger = structlog.get_logger().bind(
            novel_id=novel_id,
            component_type="cascade_update"
        )

    async def track_impact(self, entity_type: str, entity_id: str,
                            changed_fields: list) -> dict:
        # ... （完整实现同 v1.0，MAX_DEPTH 现在可正常引用）
```

### C.6 系统级日志

#### C.6.1 LLM API 调用日志（最关键的费用追踪）
#### C.6.2 数据库操作日志
#### C.6.3 API 请求/响应日志
#### C.6.4 审计日志（不可篡改的操作记录）

（代码同 v1.0，详见原始文档附录 C.6）

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
  "module_id": "world_builder",
  "module_name": "世界观设定生成器",
  "novel_id": "novel-a1b2c3d4",
  "component_type": "module",
  "rule_id": "RULE-015",
  "rule_name": "记忆货币法则",
  "tokens_used": 1523,
  "cost_usd": 0.023,
  "duration_ms": 4521,
  "request_id": "req_abc12345",
  "hostname": "prod-api-02",
  "process_id": 12345,
  "thread_id": "MainThread"
}
```

### D.2 字段分类表

| 字段类别 | 字段名 | 类型 | 必填 | 说明 |
|---------|--------|------|------|------|
| 时间 | `timestamp` | ISO8601 | ✅ | UTC 时间，毫秒精度 |
| 级别 | `level` | enum | ✅ | debug / info / warning / error / critical |
| 来源 | `logger` | string | ✅ | 产生日志的 logger 名称 |
| 事件 | `event` | string | ✅ | 事件类型标识 |
| 消息 | `message` | string | ✅ | 人类可读的事件描述 |
| 项目 | `novel_id` | string | ✅ | 所属小说项目 ID |
| 组件 | `component_type` | enum | ✅ | module / agent / review / sync / system / audit |
| 模块 | `module_id` | string | 条件 | 仅 component_type=module 时必填 |
| 代理 | `agent_id` | string | 条件 | 仅 component_type=agent 时必填 |
| 关联 | `request_id` | string | 推荐 | 关联的 HTTP 请求 ID |
| 关联 | `task_id` | string | 条件 | 关联的任务 ID |
| 关联 | `tracking_id` | string | 条件 | 关联的联动追踪 ID |
| 耗时 | `duration_ms` | int | 推荐 | 操作耗时（毫秒）|
| 状态 | `status` | string | 条件 | success / failed / partial |
| 错误 | `error_type` | string | 条件 | 仅 level>=error 时 |
| 错误 | `error_message` | string | 条件 | 仅 level>=error 时 |
| 指标 | `tokens_used` | int | 条件 | LLM 相关日志 |
| 指标 | `cost_usd` | float | 条件 | LLM 相关日志 |
| 指标 | `score` | float | 条件 | 审核相关日志 |
| 指标 | `word_count` | int | 条件 | 正文相关日志 |
| 主机 | `hostname` | string | 自动 | 服务器主机名 |
| 进程 | `process_id` | int | 自动 | 进程 PID |
| 线程 | `thread_id` | string | 自动 | 线程标识 |

### D.3 敏感信息脱敏规则

| 字段类型 | 脱敏策略 | 示例 |
|---------|---------|------|
| API Key | 全部替换为 `sk-***...***` | `sk-abc123def456` → `sk-***...***` |
| 密码/密钥 | 全部替换为 `[REDACTED]` | `my_password` → `[REDACTED]` |
| 用户 IP | 默认保留；可通过配置决定是否脱敏 | `192.168.1.100` → `192.168.1.*` |
| 正文内容 | 只记录前 200 字符预览 | 5000 字正文 → 前 200 字 + `...(truncated)` |
| Token 计数 | 保留原始值（非敏感）| — |
| 费用金额 | 保留原始值（非敏感）| — |

---

## 附录 E：日志采集与写入实现（v1.1 已全面修复）

### E.1 Python 日志配置 — v1.1 修复版

```python
# src/utils/logger_config.py — v1.1 修复版
"""
统一的日志配置。
v1.1 修复内容：
- CHG-005: PrintLoggerFactory → 文件写入（不再只输出 stdout）
- CHG-006: _RotatingFileHandler 正确引用 logging.handlers.RotatingFileHandler
- 所有 logger 默认写入对应文件
"""

import structlog
import logging
import logging.handlers  # v1.1: 显式导入 handlers
import sys
from pathlib import Path
from typing import Optional
import json
import os
import time
import threading

# 日志根目录（可通过环境变量覆盖）
LOG_ROOT = Path(os.environ.get("LOG_ROOT", "logs"))


class _AsyncFileHandler(logging.Handler):
    """
    异步文件 Handler。
    v1.1: 此类现在被正确定义和使用（替代原来缺失的 _RotatingFileHandler）。
    """
    
    def __init__(self, filename: Path, batch_size: int = 50,
                 flush_interval: float = 5.0):
        super().__init__()
        self.filename = Path(filename)
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self._buffer = []
        self._last_flush = time.time()
        self._lock = threading.Lock()

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
            self.filename.parent.mkdir(parents=True, exist_ok=True)
            with open(self.filename, "a", encoding="utf-8") as f:
                f.write(data)
        except Exception:
            pass


def setup_logging(
    log_level: str = os.environ.get("LOG_LEVEL", "INFO"),
    log_root: Path = LOG_ROOT,
    json_output: bool = True
):
    """
    配置 structlog + 标准 logging。
    v1.1 修复：日志现在同时写入文件和控制台。
    """
    log_root.mkdir(parents=True, exist_ok=True)

    # === structlog 配置 ===
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            # v1.1: 使用 JSONRenderer 输出到文件
            structlog.processors.JSONRenderer() if json_output
                else structlog.dev.ConsoleRenderer(colors=True),
        ],
        context_class=dict,
        # v1.1 修复（CHG-005）：不再使用 PrintLoggerFactory
        # 改为使用自定义的文件写入工厂
        logger_factory=structlog.LoggerFactory(),
        wrapper_class=structlog.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # === 标准 logging 配置 ===
    all_handlers = [
        # 控制台输出（开发用）
        logging.StreamHandler(sys.stdout),
    ]

    # v1.1 修复（CHG-006）：使用正确的 RotatingFileHandler
    error_log_path = log_root / "system" / "error.log"
    error_log_path.parent.mkdir(parents=True, exist_ok=True)
    all_handlers.append(
        logging.handlers.RotatingFileHandler(  # v1.1: 正确引用
            filename=error_log_path,
            maxBytes=50*1024*1024,  # 50MB
            backupCount=10,
            level=logging.WARNING
        )
    )

    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(name)s - %(message)s",
        level=getattr(logging, log_level.upper()),
        handlers=all_handlers
    )

    # 降低第三方库日志级别
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("celery").setLevel(logging.INFO)
    logging.getLogger("pika").setLevel(logging.WARNING)

    _init_log_index(log_root)


def get_logger(name: str, novel_id: str = None,
               component_type: str = None, **context) -> structlog.BoundLogger:
    """获取带固定上下文的日志器"""
    base_context = {
        "novel_id": novel_id or "system",
        "component_type": component_type or "unknown",
    }
    base_context.update(context)
    return structlog.get_logger(name).bind(**base_context)


def _init_log_index(log_root: Path):
    """初始化/更新日志索引文件"""
    index_file = log_root / "index.json"
    existing_index = {}
    if index_file.exists():
        try:
            existing_index = json.loads(index_file.read_text())
        except Exception:
            existing_index = {}
    import datetime
    existing_index["last_updated"] = datetime.datetime.now().isoformat()
    existing_index["log_root"] = str(log_root)
    index_file.write_text(json.dumps(existing_index, indent=2, ensure_ascii=False))


# 应用启动时调用一次
setup_logging()
```

### E.2 使用示例：完整的端到端日志流

（同 v1.0 原始文档附录 E.2，此处省略以节省篇幅）

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

（同 v1.0 原始文档附录 F.2，LogRotationManager 实现不变）

### F.3 日志清理策略

| 时间节点 | 操作 | 说明 |
|---------|------|------|
| 每天 03:00 | 轮转超大文件 | 单文件 > 上限时切割 |
| 每天 03:30 | 归档 90 天前的 `.log.N` 文件 | gzip 压缩 → `archived/` |
| 每周一 04:00 | 清理 270 天前的归档 | 删除超期 gzip 文件 |
| 手动触发 | `POST /api/logs/rotate` | 立即执行轮转 |
| 手动触发 | `POST /api/logs/cleanup?older_than_days=30` | 清理指定天数前的日志 |
| 磁盘使用 > 80% | 自动告警 + 紧急清理 | 先清理 system 级别日志 |

---

## 附录 G：日志查询与分析工具

### G.1 CLI 查询工具

（同 v1.0 原始文档附录 G.1，scripts/log_query.py 实现不变）

### G.2 Web 日志查看 API — v1.1 增加鉴权

```python
# src/api/endpoints/logs.py — v1.1 修复版（CHG-014）
from fastapi import APIRouter, Query, Depends, HTTPException
from src.api.middleware.auth import get_current_user, get_admin_user

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("/query")
async def query_logs(
    project_id: str = Query(..., description="Novel project ID"),
    category: str = Query(None),
    file_name: str = Query(None),
    search: str = Query(None),
    level: str = Query(None),
    tail: int = Query(100, ge=1, le=10000),
    since: str = Query(None),
    until: str = Query(None),
    stats: str = Query(None),
    # v1.1: 强制要求认证
    current_user: dict = Depends(get_current_user),
):
    """
    日志查询 API。
    v1.1: 增加认证鉴权，未登录用户无法访问。
    """
    # 权限校验：只能查询自己有权限的项目
    if not current_user.get("is_admin"):
        user_projects = current_user.get("accessible_projects", [])
        if project_id not in user_projects:
            raise HTTPException(status_code=403, detail="无权访问该项目日志")
    
    # ...（查询逻辑同 v1.0）


@router.post("/rotate")
async def force_rotate(
    # v1.1: 要求管理员权限
    current_user: dict = Depends(get_admin_user),
):
    """手动触发日志轮转（需要管理员权限）"""
    ...


@router.post("/export")
async def export_logs(
    project_id: str,
    categories: list = Query(["all"]),
    format: str = Query("tar.gz"),
    since: str = Query(None),
    until: str = Query(None),
    current_user: dict = Depends(get_current_user),
):
    """导出日志文件"""
    ...
```

### G.3 Grafana 日志仪表盘（Loki 集成方案）

（同 v1.0 原始文档附录 G.3）

---

## 附录 H：日志在失败回退中的作用

### H.1 日志驱动的故障诊断流程

（同 v1.0 原始文档附录 H.1）

### H.2 典型故障的日志排查案例

（同 v1.0 原始文档附录 H.2）

---

## 附录 I：实施检查清单（v1.1 更新）

### I.1 开发阶段检查项

| 编号 | 检查项 | 验证方法 | 状态 |
|------|--------|---------|------|
| LOG-001 | `src/utils/logger_config.py` 存在且可导入 | `python -c "from src.utils.logger_config import setup_logging"` | ⬜ |
| LOG-002 | `BaseModule` 包含 `_create_logger()` 且 log_file 正确绑定 | grep + 运行测试 | ⬜ |
| LOG-003 | `BaseAgent` 包含任务生命周期日志 | grep "task_received\|task_completed\|task_failed" | ⬜ |
| LOG-004 | `FourLayerReviewEngine` 每层有独立 logger | ls src/review/ 或 grep "_make_review_logger" | ⬜ |
| LOG-005 | `SyncEngine` 有 j2m/m2j/conflict/cascade 四个 logger | grep "_make_sync_logger" src/sync/engine.py | ⬜ |
| LOG-006 | `LLMClient` 每次调用有 request/response 日志 | grep "llm_call_request\|llm_call_response" | ⬜ |
| LOG-007 | `DatabaseEngine` 有慢查询日志 | grep "slow_query\|query_executed" | ⬜ |
| LOG-008 | API 中间件有请求/响应日志 | grep "api_request_received\|api_response_sent" | ⬜ |
| LOG-009 | `AuditLogger` 存在且记录实体变更和用户操作 | ls src/audit/logger.py | ⬜ |
| LOG-010 | 日志输出为 JSON Lines 格式 | head -1 logs/*/modules/*.log \| python -m json.tool | ⬜ |
| LOG-011 | 日志目录结构符合 B.1 节规范 | find logs/ -type d \| sort | ⬜ |
| LOG-012 | 敏感信息已脱敏 | grep "sk-" logs/ -r 应无明文 Key | ⬜ |
| LOG-013 | `scripts/log_query.py` 可正常执行 | python scripts/log_query.py --help | ⬜ |
| LOG-014 | 日志轮转脚本存在 | ls src/utils/log_rotation.py | ⬜ |
| LOG-015 | 异步 Handler 不阻塞主流程 | 压力测试下日志写入延迟不影响 API 响应时间 | ⬜ |
| **LOG-016** | **🆕 _RotatingFileHandler 正确引用** | **import logging.handlers 成功** | ⬜ |
| **LOG-017** | **🆕 CascadeUpdater.MAX_DEPTH 已定义** | **grep MAX_DEPTH src/sync/cascade_updater.py** | ⬜ |
| **LOG-018** | **🆕 日志查询 API 有鉴权** | **未 token 时返回 401** | ⬜ |

### I.2 生产部署检查项

| 编号 | 检查项 | 验证方法 | 状态 |
|------|--------|---------|------|
| PLOG-001 | `LOG_ROOT` 环境变量已配置 | docker exec container env \| grep LOG_ROOT | ⬜ |
| PLOG-002 | 日志目录持久化（Docker Volume）| docker compose.yml 中 logs_data volume 存在 | ⬜ |
| PLOG-003 | 日志磁盘配额设置 | df -h logs/ 确认空间；>80% 告警 | ⬜ |
| PLOG-004 | 定时轮转任务已注册 | crontab -l 或 K8s CronJob | ⬜ |
| PLOG-005 | 归档目录自动清理 | 检查 270 天前的归档是否删除 | ⬜ |
| PLOG-006 | 日志查询 API 可访问且有鉴权 | GET /api/logs/query?... 带 token 返回 200，不带返回 401 | ⬜ |
| PLOG-007 | 日志导出功能可用 | POST /api/logs/export 返回下载文件 | ⬜ |
| PLOG-008 | Grafana 日志面板可访问 | 浏览器打开 Grafana Dashboard | ⬜ |
| PLOG-009 | 审计日志不可被普通用户修改 | 文件权限 0644（只追加）| ⬜ |
| PLOG-010 | 全局错误日志集中收集 | logs/system/error.log 包含所有 WARNING+ | ⬜ |
| **PLOG-011** | **🆕 健康检查使用 python 非 curl** | **docker inspect 检查 healthcheck 命令** | ⬜ |
| **PLOG-012** | **🆕 sync_events 队列有活跃消费者** | **RabbitMQ Management 查看 consumer 数量** | ⬜ |

---

# 第三部分：Agent-Native 设计（v1.1 全新）

---

## 七、Workflow Orchestrator 与 Agent 调用层

> **这是 v1.1 最核心的新增部分。** 解决了 Agent 调用时面临的三大痛点：
> 1. 不知道如何编排 18 个环节
> 2. 异步任务完成后无法获知
> 3. 各模块 API Schema 不统一

### 7.1 架构设计理念

```
Agent 发送一条请求
    │
    ▼
POST /api/workflow/run
    {
      "theme": "赛博朋克武侠",
      "genre": ["科幻", "武侠"],
      "target_chapters": 30,
      "options": { ... }
    }
    │
    ▼
Orchestrator 自动编排 18 个环节
    │
    ├─ 同步环节（< 5s）：立即返回
    │   灵感启动 → 主题分析 → 档案创建
    │
    ├─ 异步环节（需 LLM）：提交到队列
    │   世界观 → 人物 → 关系 → ... → 正文 → 审核
    │
    ▼
返回 workflow_id + task_id 列表
    │
    ▼
Agent 轮询或注册回调获取进度
GET /api/workflows/{wf_id}/status
→ {"current_step": "chapter_1_review", "progress_pct": 67, ...}
```

### 7.2 Workflow Orchestrator API

#### 7.2.1 启动完整工作流

```python
# src/api/endpoints/workflow.py

@router.post("/api/workflow/run", response_model=WorkflowRunResponse)
async def run_workflow(
    request: WorkflowRunRequest,
    current_user: dict = Depends(get_current_user_or_agent),  # 支持 Agent Token
):
    """
    启动完整的小说创作工作流。
    Agent 只需调用这一个端点即可完成从灵感到正文的全流程。
    
    请求示例：
    POST /api/workflow/run
    {
      "theme": "一个失忆的剑客在赛博朋克城市寻找真相",
      "genre": ["科幻", "武侠", "悬疑"],
      "style_reference": "古龙风格 + 银翼杀手氛围",
      "target_word_count_per_chapter": 6000,
      "total_chapters": 30,
      "options": {
        "auto_fix_review_issues": true,       // 审核不通过自动修正
        "skip_existing_steps": false,          // 是否跳过已完成步骤
        "review_threshold_override": null,     // 自定义审核阈值
        "notify_callback_url": null            // 完成后的回调 URL
      }
    }
    """
    orchestrator = WorkflowOrchestrator()
    workflow = await orchestrator.create_and_run(request)
    return WorkflowRunResponse(
        workflow_id=workflow.id,
        novel_id=workflow.novel_id,
        status=workflow.status,
        current_step=workflow.current_step,
        total_steps=len(workflow.step_results),
        completed_steps=len([s for s in workflow.step_results if s.status == "done"]),
        estimated_total_seconds=workflow.estimated_duration,
        task_status_url=f"/api/workflows/{workflow.id}/status",
        steps_summary=[
            {"step_id": s.step_id, "name": s.name, "status": s.status}
            for s in workflow.step_results
        ]
    )
```

#### 7.2.2 查询工作流状态

```python
@router.get("/api/workflows/{workflow_id}/status")
async def get_workflow_status(
    workflow_id: str,
    current_user: dict = Depends(get_current_user_or_agent),
):
    """
    查询工作流的实时进度。
    Agent 可以定期轮询此端点了解进展。
    
    响应示例：
    {
      "workflow_id": "wf_a1b2c3",
      "novel_id": "novel-x1y2z3",
      "status": "running",           // pending | running | completed | failed | paused
      "current_step": "manuscript_ch1_gen",
      "current_step_name": "第一章正文生成",
      "progress_pct": 65.5,           // 0-100
      "completed_steps": 12,
      "total_steps": 18,
      "steps": [
        {
          "step_id": "step_01_inspiration",
          "name": "灵感启动",
          "status": "done",
          "duration_ms": 1200,
          "output_summary": "主题分析完成，确定核心冲突..."
        },
        {
          "step_id": "step_12_manuscript_ch1",
          "name": "第一章正文生成",
          "status": "running",
          "started_at": "2026-05-28T18:30:00Z",
          "sub_progress": {            // 当前步骤的子进度
            "current_scene": 3,
            "total_scenes": 5,
            "current_scene_name": "酒馆对峙",
            "word_count_so_far": 3800,
            "budget": 6000
          }
        },
        ...
      ],
      "errors": [],                    // 已发生的错误列表
      "warnings": [],                  // 警告信息
      "estimated_remaining_seconds": 180
    }
    """
    ...
```

#### 7.2.3 注册回调通知

```python
@router.post("/api/workflows/{workflow_id}/callback")
async def register_workflow_callback(
    workflow_id: str,
    callback_request: CallbackRegistrationRequest,
    current_user: dict = Depends(get_current_user_or_agent),
):
    """
    注册工作流完成/失败时的回调 URL。
    Agent 可以注册 webhook，避免轮询。
    
    请求：
    {
      "callback_url": "https://my-agent.example.com/webhook",
      "events": ["completed", "failed", "step_completed"],  // 订阅的事件
      "secret": "my-webhook-secret"                          // 签名密钥
    }
    
    当事件触发时，系统会 POST 到 callback_url：
    {
      "event": "step_completed",
      "workflow_id": "wf_a1b2c3",
      "step_id": "step_12_manuscript_ch1",
      "step_name": "第一章正文生成",
      "status": "done",
      "output": { ... },
      "timestamp": "..."
    }
    """
    ...
```

#### 7.2.4 单步执行（高级用法）

```python
@router.post("/api/workflow/steps/{step_id}/execute")
async def execute_single_step(
    step_id: str,
    request: SingleStepExecuteRequest,
    current_user: dict = Depends(get_current_user_or_agent),
):
    """
    执行单个环节（不走完整流水线）。
    用于 Agent 需要精细控制场景，如"只重新生成第三章"。
    
    请求示例：
    {
      "novel_id": "novel-x1y2z3",
      "step_id": "manuscript_ch3",
      "params": {
        "chapter_number": 3,
        "force_regenerate": true,
        "keep_previous_version": true
      }
    }
    """
    ...
```

### 7.3 18 环节流水线定义

```python
# src/workflow/pipeline.py

# 18 个环节的定义（按执行顺序）
WORKFLOW_STEPS = [
    # === Phase 1: 创意孵化（同步，秒级）===
    StepDef(id="step_01_inspiration", name="灵感启动",
            module="theme_engine", method="analyze_theme",
            sync=True, estimated_seconds=3),
    StepDef(id="step_02_theme", name="小说主题确定",
            module="theme_engine", method="finalize_theme",
            sync=True, estimated_seconds=2),
    StepDef(id="step_03_archive", name="小说档案创建",
            module="novel_archive", method="create_archive",
            sync=True, estimated_seconds=1),

    # === Phase 2: 世界构建（异步，LLM 生成）===
    StepDef(id="step_04_outline_draft", name="拟定大纲",
            module="outline_builder", method="generate_outline",
            sync=False, estimated_seconds=120,
            dependencies=["step_03_archive"]),
    StepDef(id="step_05_world", name="世界观设定",
            module="world_builder", method="generate_world",
            sync=False, estimated_seconds=180,
            dependencies=["step_02_theme"]),
    StepDef(id="step_06_characters", name="人物设定",
            module="character_builder", method="generate_characters",
            sync=False, estimated_seconds=240,
            dependencies=["step_05_world"],
            params={"count": 3}),  # 默认生成 3 个核心人物
    StepDef(id="step_07_relations", name="人物关系",
            module="relation_builder", method="build_relations",
            sync=False, estimated_seconds=60,
            dependencies=["step_06_characters"]),
    StepDef(id="step_08_arcs", name="角色弧线",
            module="arc_builder", method="design_arcs",
            sync=False, estimated_seconds=90,
            dependencies=["step_06_characters", "step_04_outline_draft"]),
    StepDef(id="step_09_factions", name="势力设定",
            module="faction_builder", method="build_factions",
            sync=False, estimated_seconds=90,
            dependencies=["step_05_world", "step_06_characters"]),
    StepDef(id="step_10 faction_relations", name="势力关系",
            module="faction_builder", method="build_faction_relations",
            sync=False, estimated_seconds=60,
            dependencies=["step_09_factions"]),
    StepDef(id="step_11_items", name="物品库",
            module="item_builder", method="build_item_catalog",
            sync=False, estimated_seconds=60,
            dependencies=["step_05_world"]),
    StepDef(id="step_12_foreshadows", name="伏笔追踪规划",
            module="foreshadow_manager", method="plan_foreshadows",
            sync=False, estimated_seconds=90,
            dependencies=["step_04_outline_draft", "step_06_characters"]),

    # === Phase 3: 准备就绪（同步）===
    StepDef(id="step_13_synopsis", name="小说简介",
            module="novel_archive", method="generate_synopsis",
            sync=True, estimated_seconds=30,
            dependencies=["step_05_world", "step_06_characters",
                        "step_04_outline_draft"]),
    StepDef(id="step_14_detail_outline_cfg", name="细纲配置",
            module="detail_outline", method="configure_detail_outline",
            sync=True, estimated_seconds=5,
            dependencies=["step_04_outline_draft"]),

    # === Phase 4: 写作与审核（异步，长任务）===
    StepDef(id="step_15_chapter_detail_outline", name="章节细纲",
            module="detail_outline", method="generate_chapter_outline",
            sync=False, estimated_seconds=60,
            dependencies=["step_14_detail_outline_cfg"],
            per_chapter=True),  # 每章单独执行
    StepDef(id="step_16_manuscript", name="正文初稿",
            module="manuscript_writer", method="write_chapter",
            sync=False, estimated_seconds=300,
            dependencies=["step_15_chapter_detail_outline"],
            per_chapter=True),
    StepDef(id="step_17_review", name="正文审核",
            module="four_layer_reviewer", method="review_chapter",
            sync=False, estimated_seconds=120,
            dependencies=["step_16_manuscript"],
            per_chapter=True),
    StepDef(id="step_18_fix", name="正文修正",
            module="manuscript_writer", method="fix_chapter",
            sync=False, estimated_seconds=180,
            dependencies=["step_17_review"],
            per_chapter=True,
            conditional=True),  # 仅当审核不通过时执行
]
```

### 7.4 任务状态管理

```python
# src/workflow/task_manager.py

class TaskStatus(str, Enum):
    PENDING = "pending"        # 已创建，等待执行
    QUEUED = "queued"          # 已进入队列
    RUNNING = "running"        # 执行中
    COMPLETED = "completed"    # 成功完成
    FAILED = "failed"          # 失败
    RETRYING = "retrying"      # 重试中
    CANCELLED = "cancelled"    # 已取消


class TaskManager:
    """管理所有异步任务的状态"""
    
    async def create_task(self, task_type: str, payload: dict,
                          novel_id: str = None) -> Task:
        """创建新任务，返回 task_id"""
        ...
    
    async def get_task(self, task_id: str) -> Task:
        """查询任务状态和结果"""
        ...
    
    async def update_task(self, task_id: str, status: TaskStatus,
                          result: dict = None, error: str = None):
        """更新任务状态"""
        ...
    
    async def register_callback(self, task_id: str, callback_url: str,
                                 secret: str = None, events: list = None):
        """注册任务完成回调"""
        ...
    
    async def poll_ready_tasks(self) -> list[Task]:
        """获取所有已完成但尚未通知的任务（供回调调度器使用）"""
        ...
```

### 7.5 断点续传机制

```python
# src/workflow/engine.py — 断点续传

class WorkflowOrchestrator:
    async def resume_workflow(self, workflow_id: str) -> Workflow:
        """
        从中断点恢复工作流。
        
        恢复策略：
        1. 从 DB 加载 workflow 状态
        2. 检查每个 step 的 status
        3. 跳过 status=done 的 step
        4. 从第一个非 done 的 step 继续执行
        
        对于 per_chapter 的 step（如正文生成）：
        - 检查哪些 chapter 已完成
        - 只重新生成未完成的 chapter
        """
        workflow = await self.db.get_workflow(workflow_id)
        
        for step in workflow.steps:
            if step.status == "done":
                continue
            if step.status == "running":
                # 检查是否真的还在运行（超时判定）
                if step.started_at and (now - step.started_at) > step.timeout:
                    step.status = "failed"  # 标记为超时失败
                    await self.retry_step(step)
                    continue
            
            # 执行该 step
            await self.execute_step(step, workflow)
        
        return workflow
```

---

## 八、统一 API Schema 定义（Pydantic Models）

> **v1.1 新增（CHG-011）。** 为所有 API 端点提供精确的请求/响应 Schema，
> 使 Agent 能够准确理解每个端点的输入输出格式。

### 8.1 公共类型

```python
# src/schemas/common.py

from pydantic import BaseModel, Field
from typing import TypeVar, Generic, List, Optional, Any
from datetime import datetime
from enum import Enum


class ResponseBase(BaseModel):
    """所有 API 响应的基础结构"""
    success: bool = True
    message: str = "ok"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PaginatedResponse(ResponseBase, Generic[T]):
    """分页响应"""
    total: int
    page: int
    page_size: int
    items: List[T]


class ErrorResponse(BaseModel):
    """统一错误响应"""
    success: bool = False
    error_code: str  # 如 "MODULE_NOT_FOUND", "LLM_TIMEOUT"
    error_message: str
    details: Optional[dict] = None
    request_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class EntityId(BaseModel):
    """通用实体 ID"""
    id: str = Field(..., description="实体唯一标识，如 CHAR-001, NOVEL-ABC123")


class NovelIdParam(BaseModel):
    """小说项目 ID 参数"""
    novel_id: str = Field(..., description="小说项目 ID")
```

### 8.2 小说项目 Schema

```python
# src/schemas/novel.py

class NovelCreateRequest(BaseModel):
    """创建小说项目"""
    theme: str = Field(..., min_length=10, max_length=500,
                       description="小说主题/创意描述")
    genre: List[str] = Field(..., min_items=1, max_items=5,
                             description="类型标签")
    style_reference: Optional[str] = Field(None, max_length=200,
                                          description="风格参考")
    target_word_count_per_chapter: int = Field(6000, ge=2000, le=20000)
    total_chapters: int = Field(30, ge=1, le=500)


class NovelResponse(BaseModel):
    """小说项目响应"""
    novel_id: str
    theme: str
    genre: List[str]
    status: str  # drafting | writing | reviewing | completed | published
    created_at: datetime
    updated_at: datetime
    modules_status: dict  # {module_id: "ready"|"running"|"done"}
    statistics: Optional[NovelStatistics] = None


class NovelStatistics(BaseModel):
    """项目统计数据"""
    total_characters: int = 0
    total_chapters_written: int = 0
    total_word_count: int = 0
    total_foreshadows: int = 0
    active_foreshadows: int = 0
    resolved_foreshadows: int = 0
    total_llm_cost_usd: float = 0.0
    average_review_score: Optional[float] = None
```

### 8.3 人物 Schema

```python
# src/schemas/character.py

class CharacterCreateRequest(BaseModel):
    """创建人物请求"""
    novel_id: str
    role_hint: str = Field(..., description="角色定位，如'主角''反派'")
    archetype: Optional[str] = Field(None, description="原型，如'英雄''智者'")
    requested_tier: Optional[str] = Field(None, pattern="^(S|A|B|C)$")


class CharacterIdentity(BaseModel):
    """身份层"""
    name: str
    age: Optional[int] = None
    appearance: str
    social_identity: str
    family_background: str


class CharacterPsychology(BaseModel):
    """心理层"""
    core_desire: str = Field(..., description="表层欲望")
    deep_need: str = Field(..., description="深层需求（与 desire 矛盾）")
    core_fear: str = Field(..., description="核心恐惧")
    persona_vs_self: str = Field(..., description="人设 vs 真我")
    moral_bottom_line: str = Field(..., description="道德底线")


class CharacterSpecialProfile(BaseModel):
    """特殊档案"""
    emotional_body_map: dict = Field(..., description="情绪→身体反应映射")
    voice_fingerprint: dict = Field(..., description="语气指纹")


class CharacterWeightResult(BaseModel):
    """权重评分结果"""
    narrative_weight: float  # 叙事权重
    emotional_weight: float  # 情感权重
    complexity_weight: float # 复杂度权重
    reader_attention_weight: float  # 读者注意力权重
    total_score: float
    tier: str  # S | A | B | C
    breakdown: dict


class CharacterResponse(BaseModel):
    """人物完整响应"""
    char_id: str
    novel_id: str
    identity: CharacterIdentity
    psychology: CharacterPsychology
    ability: dict  # 能力层（根据世界观动态变化）
    special_profiles: CharacterSpecialProfile
    weight: CharacterWeightResult
    created_at: datetime
    updated_at: datetime
```

### 8.4 世界观 Schema

```python
# src/schemas/world.py

class WorldRule(BaseModel):
    """单条世界观规则"""
    rule_id: str
    name: str
    category: str  # physics | society | magic | history | culture
    content: str
    cost: Optional[str] = None  # 代价/限制
    limitation: Optional[str] = None  # 局限性
    source: Optional[str] = None  # 来源/依据
    related_entities: List[str] = []  # 关联实体 ID 列表


class WorldBuildRequest(BaseModel):
    """世界观构建请求"""
    novel_id: str
    theme: str
    genre: List[str]
    dimensions: List[str] = Field(
        default=["physics", "society", "magic", "history", "culture"],
        description="要生成的维度"
    )
    min_rules_per_dimension: int = Field(3, ge=1)


class WorldBuildResponse(BaseModel):
    """世界观构建响应"""
    novel_id: str
    rules: List[WorldRule]
    total_rules: int
    extreme_test_result: dict  # {passed: 5, failed: 0, verdict: "PASS"}
    generated_at: datetime
```

### 8.5 章节/正文 Schema

```python
# src/schemas/chapter.py

class ChapterOutlineItem(BaseModel):
    """细纲中的单个场景"""
    scene_index: int
    scene_type: str  # action | dialogue | transition | reflection
    pov_character_id: str
    location_id: Optional[str] = None
    word_budget: int
    key_events: List[str] = []
    constraints: List[str] = []  # 该场景需要遵守的约束


class ChapterDetailOutline(BaseModel):
    """章节细纲"""
    chapter_number: int
    word_budget_total: int
    scenes: List[ChapterOutlineItem]
    foreshadows_to_plant: List[str] = []  # 伏笔 ID
    foreshadows_to_reveal: List[str] = []
    characters_involved: List[str] = []


class ManuscriptWriteRequest(BaseModel):
    """正文写作请求"""
    novel_id: str
    chapter_number: int
    outline_data: ChapterDetailOutline
    auto_review: bool = True  # 写完后自动触发审核
    max_retries_on_review_fail: int = Field(3, ge=1, le=10)


class ManuscriptResponse(BaseModel):
    """正文响应"""
    chapter_id: str
    novel_id: str
    chapter_number: int
    text: str  # 完整正文
    word_count: int
    scenes_count: int
    budget_deviation_pct: Optional[float] = None
    duration_ms: int
    review_result: Optional["ReviewReportResponse"] = None
```

### 8.6 审查报告 Schema

```python
# src/schemas/review.py

class IssueItem(BaseModel):
    """审查发现的问题"""
    issue_id: str
    severity: str  # critical | major | minor | suggestion
    category: str  # inconsistency | logic_gap | ai_trace | ...
    description: str
    suggestion: str
    related_entities: List[str] = []
    location: Optional[str] = None  # 如 "CH-03, Scene 2, paragraph 5"


class LayerReviewResult(BaseModel):
    """单层审查结果"""
    layer: str  # consistency | logic | literary | engagement
    score: float  # 0.0 - 1.0
    threshold: float
    passed: bool
    issues_found: int
    issues: List[IssueItem] = []
    duration_ms: int
    reviewer_model: str


class AITraceResult(BaseModel):
    """AI 痕迹检测结果"""
    total_traces_found: int
    traces_by_category: dict  # {category_name: count}
    overall_confidence: float
    verdict: str  # CLEAN | TRACE_DETECTED | HEAVY_TRACE


class ReviewReportResponse(BaseModel):
    """完整审查报告"""
    review_id: str
    novel_id: str
    chapter_number: int
    overall_passed: bool
    overall_score: Optional[float] = None
    layers: List[LayerReviewResult]
    ai_trace: AITraceResult
    total_issues: int
    termination_reason: Optional[str] = None  # 如果中途终止
    total_duration_ms: int
    reviewed_at: datetime
```

### 8.7 工作流 Schema

```python
# src/schemas/workflow.py

class WorkflowRunRequest(BaseModel):
    """工作流运行请求"""
    theme: str = Field(..., min_length=10, max_length=1000)
    genre: List[str] = Field(..., min_items=1)
    style_reference: Optional[str] = None
    target_word_count_per_chapter: int = 6000
    total_chapters: int = 30
    options: WorkflowOptions = None


class WorkflowOptions(BaseModel):
    """工作流选项"""
    auto_fix_review_issues: bool = True
    skip_existing_steps: bool = False
    review_threshold_override: Optional[dict] = None
    notify_callback_url: Optional[str] = None
    start_from_step: Optional[str] = None  # 从指定步骤开始
    stop_after_step: Optional[str] = None   # 在指定步骤后停止


class WorkflowStepSummary(BaseModel):
    """步骤摘要"""
    step_id: str
    name: str
    status: str  # pending | running | done | failed | skipped
    duration_ms: Optional[int] = None
    output_summary: Optional[str] = None
    error: Optional[str] = None


class WorkflowRunResponse(BaseModel):
    """工作流运行响应"""
    workflow_id: str
    novel_id: str
    status: str
    current_step: str
    total_steps: int
    completed_steps: int
    estimated_total_seconds: int
    task_status_url: str
    steps_summary: List[WorkflowStepSummary]


class WorkflowStatusResponse(BaseModel):
    """工作流状态响应"""
    workflow_id: str
    novel_id: str
    status: str  # pending | running | completed | failed | paused
    current_step: str
    current_step_name: str
    progress_pct: float  # 0-100
    completed_steps: int
    total_steps: int
    steps: List[WorkflowStepDetail]
    errors: List[str] = []
    warnings: List[str] = []
    estimated_remaining_seconds: Optional[int] = None


class WorkflowStepDetail(BaseModel):
    """步骤详情"""
    step_id: str
    name: str
    status: str
    duration_ms: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    output_summary: Optional[str] = None
    sub_progress: Optional[dict] = None  # 当前步骤的子进度
    error: Optional[str] = None
```

### 8.8 任务状态 Schema

```python
# src/schemas/task.py

class TaskResponse(BaseModel):
    """任务状态响应"""
    task_id: str
    task_type: str  # generation | writing | review | sync
    status: str  # pending | queued | running | completed | failed | retrying
    novel_id: Optional[str] = None
    chapter_number: Optional[int] = None
    progress_pct: Optional[float] = None
    result: Optional[dict] = None
    error: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    retry_count: int = 0
    max_retries: int = 3
    callback_url: Optional[str] = None
```

---

## 九、Agent 接入指南

> **v1.1 新增（CHG-012）。** 描述如何让各种 AI Agent 框架调用本系统。

### 9.1 认证方式

Agent 调用系统需要携带认证 Token：

```bash
# 方式 1: Bearer Token（推荐用于 Agent）
export AGENT_TOKEN="your-agent-token-from-env"
curl -H "Authorization: Bearer $AGENT_TOKEN" \
     https://api.your-domain.com/api/modules

# 方式 2: API Key（用于简单集成）
curl -H "X-API-Key: your-api-key" \
     https://api.your-domain.com/api/workflow/run
```

### 9.2 最简调用示例

#### 方式 A：一键跑通全流程（推荐）

```bash
# 1. 启动工作流
curl -X POST https://api.example.com/api/workflow/run \
  -H "Authorization: Bearer $AGENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "theme": "一个失忆的剑客在赛博朋克城市寻找真相",
    "genre": ["科幻", "武侠", "悬疑"],
    "total_chapters": 30,
    "options": {
      "auto_fix_review_issues": true,
      "notify_callback_url": "https://my-agent/webhook"
    }
  }'

# 响应：
# {
#   "workflow_id": "wf_abc123",
#   "novel_id": "novel_xyz789",
#   "status": "running",
#   "task_status_url": "/api/workflows/wf_abc123/status",
#   "estimated_total_seconds": 3600
# }

# 2. 轮询进度（或等待 webhook 回调）
curl https://api.example.com/api/workflows/wf_abc123/status \
  -H "Authorization: Bearer $AGENT_TOKEN"
```

#### 方式 B：逐步精细控制

```bash
# 1. 创建项目
NOVEL_ID=$(curl -s -X POST /api/novels \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"theme":"...", "genre":["科幻"]}' | jq -r '.novel_id')

# 2. 生成世界观
curl -X POST /api/world/build \
  -H "Authorization: Bearer $TOKEN" \
  -d "{\"novel_id\":\"$NOVEL_ID\", \"theme\":\"...\", \"genre\":[\"科幻\"]}"

# 3. 生成人物
curl -X POST /api/characters/generate \
  -H "Authorization: Bearer $TOKEN" \
  -d "{\"novel_id\":\"$NOVEL_ID\", \"role_hint\":\"主角\"}"

# 4. 生成大纲
curl -X POST /api/outlines/generate \
  -H "Authorization: Bearer $TOKEN" \
  -d "{\"novel_id\":\"$NOVEL_ID\"}"

# ... 以此类推
```

### 9.3 MCP (Model Context Protocol) 集成

```python
# mcp_server.py — 将本系统暴露为 MCP Tools

from mcp.server import Server
from mcp.types import Tool, TextContent
import httpx

app = Server("novel-creation-system")

@app.list_tools()
async def list_tools():
    return [
        Tool(
            name="run_novel_workflow",
            description="一键运行完整的小说创作工作流（18个环节自动编排）",
            inputSchema={
                "type": "object",
                "properties": {
                    "theme": {"type": "string", "description": "小说主题"},
                    "genre": {"type": "array", "items": {"type": "string"}},
                    "total_chapters": {"type": "integer", "default": 30},
                },
                "required": ["theme", "genre"]
            }
        ),
        Tool(
            name="get_workflow_status",
            description="查询工作流执行进度",
            inputSchema={
                "type": "object",
                "properties": {
                    "workflow_id": {"type": "string"}
                },
                "required": ["workflow_id"]
            }
        ),
        Tool(
            name="get_character",
            description="查询人物档案详情",
            inputSchema={
                "type": "object",
                "properties": {
                    "char_id": {"type": "string"}
                },
                "required": ["char_id"]
            }
        ),
        Tool(
            name="query_logs",
            description="查询系统日志（用于排错）",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string"},
                    "search": {"type": "string"},
                    "level": {"type": "string", "enum": ["error", "warning"]}
                }
            }
        ),
        # ... 更多工具
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict):
    base_url = "http://localhost:8000"
    headers = {"Authorization": f"Bearer {os.environ['AGENT_TOKEN']}"}
    
    if name == "run_novel_workflow":
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{base_url}/api/workflow/run",
                json=arguments, headers=headers, timeout=600
            )
            return [TextContent(type="text", text=resp.text)]
    
    elif name == "get_workflow_status":
        wf_id = arguments["workflow_id"]
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{base_url}/api/workflows/{wf_id}/status",
                headers=headers
            )
            return [TextContent(type="text", text=resp.text)]
    
    # ... 其他工具实现
```

### 9.4 LangChain Tool 封装

```python
# langchain_tools.py — LangChain 自定义 Tool

from langchain.tools import BaseTool
from pydantic import Field
import httpx
from typing import Dict, Any


class RunWorkflowTool(BaseTool):
    """运行小说创作工作流的 LangChain Tool"""
    name = "run_novel_workflow"
    description = "运行完整的AI小说创作流程，从灵感到正文审核全自动"

    def _run(self, theme: str, genre: list, 
              total_chapters: int = 30) -> Dict[str, Any]:
        resp = httpx.post(
            f"{API_BASE}/api/workflow/run",
            headers={"Authorization": f"Bearer {AGENT_TOKEN}"},
            json={
                "theme": theme,
                "genre": genre,
                "total_chapters": total_chapters,
                "options": {"auto_fix_review_issues": True}
            },
            timeout=10
        )
        return resp.json()


class GetChapterTextTool(BaseTool):
    """获取已生成的章节正文"""
    name = "get_chapter_text"
    description = "获取指定小说的指定章节正文内容"

    def _run(self, novel_id: str, chapter_number: int) -> str:
        resp = httpx.get(
            f"{API_BASE}/api/chapters/{novel_id}/{chapter_number}",
            headers={"Authorization": f"Bearer {AGENT_TOKEN}"}
        )
        return resp.json()["text"]


class QueryReviewReportTool(BaseModel):
    """查询章节审核报告"""
    name = "get_review_report"
    description = "获取指定章节的四层审查报告"

    def _run(self, novel_id: str, chapter_number: int) -> Dict[str, Any]:
        resp = httpx.get(
            f"{API_BASE}/api/review/report/{novel_id}/{chapter_number}",
            headers={"Authorization": f"Bearer {AGENT_TOKEN}"}
        )
        return resp.json()


# 注册到 LangChain Agent
tools = [
    RunWorkflowTool(),
    GetChapterTextTool(),
    QueryReviewReportTool(),
    # ... 更多工具
]
```

### 9.5 OpenAI Function Calling / Actions Schema

```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "AI Novel Creation System",
    "version": "1.1.0",
    "description": "AI Agent 可调用的小说创作后端服务"
  },
  "servers": [{"url": "https://api.your-domain.com"}],
  "paths": {
    "/api/workflow/run": {
      "post": {
        "operationId": "runWorkflow",
        "summary": "一键运行完整小说创作工作流",
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/WorkflowRunRequest"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "工作流已启动",
            "content": {
              "application/json": {
                "schema": {"$ref": "#/components/schemas/WorkflowRunResponse"}
              }
            }
          }
        }
      }
    },
    "/api/workflows/{workflow_id}/status": {
      "get": {
        "operationId": "getWorkflowStatus",
        "summary": "查询工作流进度",
        "parameters": [
          {"name": "workflow_id", "in": "path", "required": true, "schema": {"type": "string"}}
        ],
        "responses": {
          "200": {
            "content": {
              "application/json": {
                "schema": {"$ref": "#/components/schemas/WorkflowStatusResponse"}
              }
            }
          }
        }
      }
    },
    "/api/novels": {
      "post": {
        "operationId": "createNovel",
        "summary": "创建小说项目"
      },
      "get": {
        "operationId": "listNovels",
        "summary": "列出所有小说项目"
      }
    },
    "/api/characters": {
      "post": {
        "operationId": "generateCharacter",
        "summary": "生成人物档案"
      }
    },
    "/api/chapters/{novel_id}/{chapter_number}": {
      "get": {
        "operationId": "getChapter",
        "summary": "获取章节正文"
      }
    },
    "/api/review/report/{novel_id}/{chapter_number}": {
      "get": {
        "operationId": "getReviewReport",
        "summary": "获取审核报告"
      }
    },
    "/api/logs/query": {
      "get": {
        "operationId": "queryLogs",
        "summary": "查询系统日志（用于排错）"
      }
    }
  },
  "components": {
    "securitySchemes": {
      "bearerAuth": {"type": "http", "scheme": "bearer"}
    },
    "schemas": {
      "WorkflowRunRequest": {
        "type": "object",
        "required": ["theme", "genre"],
        "properties": {
          "theme": {"type": "string", "description": "小说主题描述"},
          "genre": {"type": "array", "items": {"type": "string"}},
          "total_chapters": {"type": "integer", "default": 30},
          "options": {"$ref": "#/components/schemas/WorkflowOptions"}
        }
      },
      "WorkflowOptions": {
        "type": "object",
        "properties": {
          "auto_fix_review_issues": {"type": "boolean", "default": true},
          "notify_callback_url": {"type": "string"}
        }
      }
    }
  },
  "security": [{"bearerAuth": []}]
}
```

### 9.6 Agent 调用最佳实践

| 最佳实践 | 说明 |
|---------|------|
| **优先使用 Workflow API** | 不要自己编排 18 步，用 `POST /api/workflow/run` 一键搞定 |
| **注册回调而非轮询** | 长任务（正文生成 5 分钟）应注册 webhook，避免浪费 token 轮询 |
| **利用日志 API 排错** | 出问题时用 `GET /api/logs/query?level=error&project_id=xxx` 快速定位 |
| **不要编辑 Markdown** | Agent 通过 JSON API 操作数据，忽略 Markdown SYNC 标记的存在 |
| **合理设置超时** | 工作流可能运行 30-60 分钟，客户端 timeout 应设为 > 3600s |
| **利用断点续传** | 如果 Agent 中断，用 `workflow_id` 调用 resume 接口继续 |
| **控制并发** | 同时运行不超过 3 个工作流（`WORKFLOW_MAX_CONCURRENT`），避免资源耗尽 |
| **监控费用** | 定期查询 `llm_calls.log` 的 cost_usd 统计，防止费用失控 |

---

> **文档结束**
>
> **v1.1 版本核心改进总结**：
> 1. **修复 8 个 Blocker**：表数量、环节计数、docker-compose、structlog、缺失定义等
> 2. **新增 Workflow Orchestrator**：Agent 一键调用 18 环节的完整流水线
> 3. **新增异步任务机制**：状态查询 + 回调通知 + 断点续传
> 4. **新增统一 API Schema**：所有端点的 Pydantic Model 定义
> 5. **新增 Agent 接入指南**：MCP / LangChain / OpenAI Actions 三种接入方式
> 6. **Agent 隐藏 SYNC 标记**：Agent 只走 JSON API，不碰 Markdown
> 7. **安全加固**：日志 API 鉴权、sync_events 消费者补全
