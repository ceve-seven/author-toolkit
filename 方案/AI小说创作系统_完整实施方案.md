# AI 协同小说创作系统 — 完整实施方案

> **版本**: v1.0  
> **编制日期**: 2026-05-28  
> **基于文档**: 15 个 @AI小说相关 文件 + 多轮对话设计文档  
> **适用范围**: 从灵感到定稿的全流程 AI 小说创作系统  

---

## 目录

1. [系统总览与架构目标](#一系统总览与架构目标)
2. [环境配置清单](#二环境配置清单)
3. [分阶段实施流程](#三分阶段实施流程)
4. [各环节失败回退方案](#四各环节失败回退方案)
5. [性能优化与监控](#五性能优化与监控)
6. [验收标准与交付物](#六验收标准与交付物)

---

## 一、系统总览与架构目标

### 1.1 核心设计原则

| 原则 | 定义 | 实现方式 |
|------|------|---------|
| 用户只审核，AI 全执行 | 用户用自然语言驱动修改，不需要精确指令 | 三代理分离：生成/写作/审核各自独立运行 |
| 中央档案库唯一数据源 | 所有模块数据统一存储，双向引用 | PostgreSQL + pgvector 统一数据库 |
| 模块化可扩展 | 新模块一行代码注册即可接入 | BaseModule 接口 + ModuleRegistry 注册表 |
| 双向同步用户可见 | 用户看中文 Markdown，系统操作结构化 JSON | SYNC 标记区块 + 同步引擎 |
| 质量三层保证 | 设定一致性 / 叙事质量 / 文学质感 | 四层审查引擎 + AI 痕迹检测器 |
| 伏笔全生命周期管理 | 每个伏笔可追踪、可检索、防重复 | FORE 档案实体 + 向量相似度检测 |

### 1.2 系统架构总图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          用户界面层 (UI Layer)                            │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────────────┐  │
│  │  小说档案面板     │  │  Markdown 编辑器  │  │  权重面板/伏笔面板等   │  │
│  └────────┬─────────┘  └────────┬─────────┘  └───────────┬───────────┘  │
└───────────┼─────────────────────┼─────────────────────────┼──────────────┘
            │                     │                         │
┌───────────▼─────────────────────▼─────────────────────────▼──────────────┐
│                         API 网关 (Gateway)                                │
│  统一入口 | 路由分发 | 认证授权 | 速率限制 | 请求聚合 | 事件广播           │
└───────────┬─────────────────────┬─────────────────────────┬──────────────┘
            │                     │                         │
┌───────────▼─────────────────────▼─────────────────────────▼──────────────┐
│                      模块注册表 & 服务发现 (Registry)                      │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ 模块名 | 版本 | API端点 | 健康状态 | 依赖列表 | 审核模块绑定关系  │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└───────────┬─────────────────────┬─────────────────────────┬──────────────┘
            │                     │                         │
┌───────────▼─────────────────────▼─────────────────────────▼──────────────┐
│                        消息队列 (Message Queue)                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────────┐  │
│  │ 生成任务队列 │  │ 写作任务队列 │  │ 审核任务队列 │  │  同步事件队列   │  │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └───────┬────────┘  │
└─────────┼─────────────────┼─────────────────┼─────────────────┼──────────┘
          │                 │                 │                 │
┌─────────▼─────────────────▼─────────────────▼─────────────────▼──────────┐
│                           子代理层 (Agent Layer)                          │
│                                                                          │
│  ┌──────────────────────┐  ┌──────────────────────┐  ┌───────────────┐  │
│  │   生成代理 (Generator) │  │   写作代理 (Writer)    │  │ 审核代理(Rev) │  │
│  │  ┌──────────────────┐│  │  ┌──────────────────┐│  │               │  │
│  │  │ 设定生成器        ││  │  │ 正文生成器        ││  │ 四层审查引擎   │  │
│  │  │ 细纲生成器        ││  │  │ 场景展开器        ││  │ 一致性检查器   │  │
│  │  │ 伏笔设计器        ││  │  │ 对话写作器        ││  │ 字数校验器     │  │
│  │  │ 大纲生成器        ││  │  │ 描写增强器        ││  │ AI痕迹检测器   │  │
│  │  └──────────────────┘│  │  └──────────────────┘│  └───────────────┘  │
│  └──────────────────────┘  └──────────────────────┘                     │
└──────────────────────────────────────────────────────────────────────────┘
          │                 │                 │                 │
┌─────────▼─────────────────▼─────────────────▼─────────────────▼──────────┐
│                          数据层 (Data Layer)                              │
│                                                                          │
│  ┌──────────────────────────┐  ┌──────────────────────────────────────┐ │
│  │  关系型数据库              │  │  向量数据库                           │ │
│  │  (PostgreSQL + pgvector)  │  │  (pgvector 内嵌于 PostgreSQL)       │ │
│  │                           │  │                                      │ │
│  │  • 12模块结构化数据        │  │  • 角色档案向量 (语义查询)            │ │
│  │  • 实体关系 & 引用图       │  │  • 章节正文向量 (内容相似度)          │ │
│  │  • 变更日志 & 版本快照     │  │  • 伏笔描述向量 (主题检索)            │ │
│  │  • 用户权限 & 配置         │  │  • 世界观规则向量 (规则匹配)          │ │
│  └──────────────────────────┘  └──────────────────────────────────────┘ │
│                                                                          │
│  ┌──────────────────────────┐  ┌──────────────────────────────────────┐ │
│  │  Redis 缓存层             │  │  MinIO / 本地FS 文件存储             │ │
│  │  • 约束文件缓存           │  │  • Markdown 用户可视文件             │ │
│  │  • 章节生成中间状态       │  │  • 版本快照归档                      │ │
│  │  • 实时权重面板数据        │  │  • 导出 PDF/EPUB                    │ │
│  └──────────────────────────┘  └──────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
```

### 1.3 创作流程 19 个环节

```
灵感创作 → 小说主题 → 故事大纲 → 世界观设定 → 人物设定 → 人物关系 → 角色弧线
→ 势力设定 → 势力关系 → 物品仓库 → 伏笔追踪 → 小说档案 → 小说简介
→ 分卷配置 → 章节细纲 → 关键剧情 → 章节正文
```

每个环节对应一个或多个微服务模块，通过中央档案库共享数据，通过消息队列串联执行。

---

## 二、环境配置清单

### 2.1 开发环境（最低要求）

| 类别 | 软件/组件 | 版本要求 | 用途 |
|------|----------|---------|------|
| 操作系统 | Ubuntu 22.04 LTS / macOS 14+ / Windows 11 WSL2 | — | 主机操作系统 |
| Python | 3.11+ | ≥3.11.0 | 后端服务主语言 |
| Node.js | 20+ | ≥20.0.0 | 前端 UI 服务 |
| 数据库 | SQLite | ≥3.40.0 | 开发环境轻量数据库（替代 PostgreSQL） |
| 向量搜索 | ChromaDB | ≥0.4.0 | 开发环境轻量向量数据库 |
| 缓存 | 可选（开发环境可不部署） | — | 生产才需要 Redis |
| 消息队列 | 内存队列（开发模式） | — | 开发环境使用内存模拟 |
| LLM 接口 | OpenAI API / 兼容接口 | — | 核心生成能力 |
| 嵌入模型 | bge-large-zh-v1.5 (本地) 或 text-embedding-3-large (API) | — | 中文向量化 |
| Docker | ≥24.0 | — | 容器化部署（可选） |
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

# === 消息队列 (开发用内存模拟) ===
celery[redis]>=5.3.0         # 生产用；开发可用内存模式

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

# === 测试 ===
pytest>=7.4.0
pytest-asyncio>=0.23.0
httpx                     # TestClient
```

### 2.2 生产环境（推荐配置）

| 类别 | 软件/组件 | 版本要求 | 部署方式 | 用途 |
|------|----------|---------|---------|------|
| 操作系统 | Ubuntu 22.04 LTS / Debian 12 | — | 物理机/云主机 | 主机 OS |
| 容器编排 | Docker Compose / Kubernetes | ≥24.0 / ≥1.28 | 容器化 | 全部服务容器化 |
| 反向代理 | Nginx / Traefik | ≥1.24 / ≥3.0 | Docker | API 网关 |
| 数据库 | PostgreSQL | ≥16 | Docker | 主数据库 |
| 向量扩展 | pgvector | ≥0.7.0 | PostgreSQL 扩展 | 向量搜索内嵌 |
| 缓存 | Redis | ≥7.2 | Docker | 会话/缓存/锁 |
| 消息队列 | RabbitMQ | ≥3.12 | Docker | 任务队列 |
| 对象存储 | MinIO | ≥2024.1 | Docker | 文件存储 |
| 监控 | Prometheus + Grafana | latest | Docker | 性能监控 |
| 日志 | ELK Stack / Loki | latest | Docker | 日志聚合 |
| LLM 接口 | OpenAI API / Azure OpenAI / 本地 Ollama | — | 外部服务 | 核心生成能力 |
| 嵌入模型服务 | TEI (Text Embeddings Inference) / 本地推理 | — | Docker/GPU | 高吞吐向量化 |

**生产环境 `docker-compose.yml` 核心服务定义**:

```yaml
version: '3.9'

services:
  # === API 网关 ===
  gateway:
    image: nginx:1.24-alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
    depends_on:
      - api-server
      - registry
    restart: unless-stopped

  # === API 主服务 ===
  api-server:
    build:
      context: .
      dockerfile: Dockerfile.api
    environment:
      - DATABASE_URL=postgresql+asyncpg://noveluser:${DB_PASSWORD}@postgres:5432/novel_db
      - REDIS_URL=redis://redis:6379/0
      - RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - EMBEDDING_MODEL=${EMBEDDING_MODEL:-bge-large-zh-v1.5}
      - EMBEDDING_ENDPOINT=${EMBEDDING_ENDPOINT}  # 本地TEI服务地址
      - ENVIRONMENT=production
      - LOG_LEVEL=INFO
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # === PostgreSQL + pgvector ===
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: noveluser
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: novel_db
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./db/init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U noveluser -d novel_db"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  # === Redis ===
  redis:
    image: redis:7.2-alpine
    command: redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3
    restart: unless-stopped

  # === RabbitMQ ===
  rabbitmq:
    image: rabbitmq:3.12-management-alpine
    environment:
      RABBITMQ_DEFAULT_USER: guest
      RABBITMQ_DEFAULT_PASSWORD: guest
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq
    ports:
      - "5672:5672"    # AMQP
      - "15672:15672"  # 管理界面
    healthcheck:
      test: ["CMD", "rabbitmq-diagnostics", "-q", "ping"]
      interval: 15s
      timeout: 10s
      retries: 5
    restart: unless-stopped

  # === MinIO (对象存储) ===
  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ACCESS_KEY}
      MINIO_ROOT_PASSWORD: ${MINIO_SECRET_KEY}
    volumes:
      - minio_data:/data
    ports:
      - "9000:9000"   # API
      - "9001:9001"   # Console
    restart: unless-stopped

  # === 嵌入模型服务 (本地推理) ===
  embedding-service:
    build:
      context: .
      dockerfile: Dockerfile.embedding
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    environment:
      - MODEL_ID=BAAI/bge-large-zh-v1.5
      - PORT=8080
    ports:
      - "8080:8080"
    restart: unless-stopped

  # === 模块注册表服务 ===
  registry:
    build:
      context: .
      dockerfile: Dockerfile.registry
    environment:
      - DATABASE_URL=postgresql+asyncpg://noveluser:${DB_PASSWORD}@postgres:5432/novel_db
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped

  # === 生成代理池 (可水平扩展) ===
  generator-agent:
    build:
      context: .
      dockerfile: Dockerfile.agent-generator
    environment:
      - DATABASE_URL=postgresql+asyncpg://noveluser:${DB_PASSWORD}@postgres:5432/novel_db
      - REDIS_URL=redis://redis:6379/0
      - RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - AGENT_TYPE=generator
      - TEMPERATURE=0.85  # 高温度=高创意
    depends_on:
      - postgres
      - redis
      - rabbitmq
    deploy:
      replicas: 2  # 生成代理池大小
    restart: unless-stopped

  # === 写作代理池 ===
  writer-agent:
    build:
      context: .
      dockerfile: Dockerfile.agent-writer
    environment:
      - DATABASE_URL=postgresql+asyncpg://noveluser:${DB_PASSWORD}@postgres:5432/novel_db
      - REDIS_URL=redis://redis:6379/0
      - RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - AGENT_TYPE=writer
      - TEMPERATURE=0.65  # 中温度=稳定输出
    depends_on:
      - postgres
      - redis
      - rabbitmq
    deploy:
      replicas: 1
    restart: unless-stopped

  # === 审核代理池 (可水平扩展) ===
  reviewer-agent:
    build:
      context: .
      dockerfile: Dockerfile.agent-reviewer
    environment:
      - DATABASE_URL=postgresql+asyncpg://noveluser:${DB_PASSWORD}@postgres:5432/novel_db
      - REDIS_URL=redis://redis:6379/0
      - RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - AGENT_TYPE=reviewer
      - TEMPERATURE=0.2   # 低温度=精确判断
    depends_on:
      - postgres
      - redis
      - rabbitmq
    deploy:
      replicas: 3  # 审核代理池大小（审核可高度并行）
    restart: unless-stopped

  # === 同步引擎 ===
  sync-engine:
    build:
      context: .
      dockerfile: Dockerfile.sync
    environment:
      - DATABASE_URL=postgresql+asyncpg://noveluser:${DB_PASSWORD}@postgres:5432/novel_db
      - MINIO_ENDPOINT=minio:9000
      - MINIO_ACCESS_KEY=${MINIO_ACCESS_KEY}
      - MINIO_SECRET_KEY=${MINIO_SECRET_KEY}
      - MARKDOWN_ROOT=/app/user_view
    volumes:
      - markdown_files:/app/user_view
    depends_on:
      - postgres
      - minio
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  rabbitmq_data:
  minio_data:
  markdown_files:
```

### 2.3 环境变量配置 (`.env` 模板)

```bash
# ═══════════════════════════════════════════
# 数据库
# ═══════════════════════════════════════════
DB_PASSWORD=your_strong_password_here_change_me
DATABASE_URL=postgresql+asyncpg://noveluser:${DB_PASSWORD}@localhost:5432/novel_db

# ═══════════════════════════════════════════
# LLM 配置
# ═══════════════════════════════════════════
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1  # 或兼容接口地址
OPENAI_MODEL=gpt-4o  # 生成用
OPENAI_REVIEW_MODEL=gpt-4o  # 审核用（可用更便宜的模型）
OPENAI_EMBEDDING_MODEL=text-embedding-3-large  # API嵌入模型

# ═══════════════════════════════════════════
# 本地嵌入模型（如果不用API）
# ═══════════════════════════════════════════
EMBEDDING_MODEL=bge-large-zh-v1.5
EMBEDDING_ENDPOINT=http://localhost:8080/embed  # 本地TEI服务

# ═══════════════════════════════════════════
# 缓存
# ═══════════════════════════════════════════
REDIS_URL=redis://localhost:6379/0

# ═══════════════════════════════════════════
# 消息队列
# ═══════════════════════════════════════════
RABBITMQ_URL=amqp://guest:guest@localhost:5672/

# ═══════════════════════════════════════════
# 对象存储 (MinIO)
# ═══════════════════════════════════════════
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin_secret_change_me
MINIO_BUCKET=novel-files

# ═══════════════════════════════════════════
# 应用配置
# ═══════════════════════════════════════════
ENVIRONMENT=development  # development | production
LOG_LEVEL=DEBUG          # DEBUG | INFO | WARNING | ERROR
SECRET_KEY=your-secret-key-for-jwt-tokens-change_me
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# ═══════════════════════════════════════════
# 文件路径
# ═══════════════════════════════════════════
USER_VIEW_DIR=./user_view          # Markdown 用户可视目录
SYSTEM_DATA_DIR=./system_data      # JSON 系统数据目录
SNAPSHOT_DIR=./snapshots           # 版本快照目录
EXPORT_DIR=./exports               # 导出文件目录
```

### 2.4 项目目录结构

```
novel-creation-system/
├── .env                          # 环境变量（不提交到Git）
├── .env.example                  # 环境变量模板
├── docker-compose.yml            # 生产环境编排
├── docker-compose.dev.yml        # 开发环境编排（简化版）
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
│   │   │   ├── env.py
│   │   │   ├── versions/
│   │   │   └── 001_initial_schema.sql
│   │   └── crud.py               # CRUD 操作
│   ├── vector_store/
│   │   ├── embeddings.py         # 嵌入模型封装
│   │   ├── search.py             # 向量搜索服务
│   │   └── collections.py        # 向量集合管理
│   ├── modules/                  # 微服务模块实现
│   │   ├── base_module.py        # BaseModule 抽象基类
│   │   ├── registry.py           # 模块注册表
│   │   ├── world_builder/        # 世界观设定模块
│   │   │   ├── __init__.py
│   │   │   ├── generator.py      # 世界观生成器
│   │   │   └── reviewer.py       # 世界观审核器
│   │   ├── character_builder/    # 人物设定模块
│   │   │   ├── __init__.py
│   │   │   ├── generator.py
│   │   │   └── reviewer.py
│   │   ├── faction_builder/      # 势力设定模块
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
│   │   │   └── weight.py        # 权重面板API
│   │   └── middleware/
│   │       ├── auth.py          # 认证中间件
│   │       ├── rate_limit.py    # 限流
│   │       └── error_handler.py # 错误处理
│   └── utils/                    # 工具函数
│       ├── id_generator.py      # ID生成器 (CHAR-XXX, FAC-XXX...)
│       ├── prompt_templates.py  # Prompt模板管理
│       ├── llm_client.py        # LLM调用封装
│       └── text_processor.py    # 文本处理工具
│
├── frontend/                     # 前端UI
│   ├── package.json
│   ├── src/
│   │   ├── App.tsx
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── NovelEditor.tsx
│   │   │   ├── CharacterPanel.tsx
│   │   │   ├── WorldViewPanel.tsx
│   │   │   ├── OutlineView.tsx
│   │   │   ├── ChapterEditor.tsx
│   │   │   ├── ForeshadowBoard.tsx
│   │   │   └── WeightDashboard.tsx
│   │   ├── components/
│   │   ├── hooks/
│   │   └── api/
│   └── vite.config.ts
│
├── db/
│   ├── init.sql                  # 数据库初始化SQL（完整schema）
│   ├── seed.sql                  # 种子数据
│   └── migrations/               # Alembic迁移
│
├── prompts/                      # Prompt模板
│   ├── generation/               # 生成类Prompt
│   │   ├── inspiration.txt
│   │   ├── theme.txt
│   │   ├── world_building.txt
│   │   ├── character.txt
│   │   ├── faction.txt
│   │   ├── outline.txt
│   │   ├── detail_outline.txt
│   │   └── chapter_writing.txt
│   ├── review/                   # 审核类Prompt
│   │   ├── consistency.txt
│   │   ├── logic.txt
│   │   ├── literary_quality.txt
│   │   ├── reader_appeal.txt
│   │   └── ai_trace_detection.txt
│   └── tools/                    # 工具类Prompt
│       ├── constraint_injection.txt
│       ├── human_perception.txt
│       └── emotion_body_map.txt
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
│   └── restore.sh                # 恢复
│
├── requirements.txt              # 生产依赖
├── requirements-dev.txt          # 开发依赖
└── README.md
```

---

## 三、分阶段实施流程

实施分为 **6 个大阶段、18 个子步骤**。每个步骤有明确的输入、输出、验证标准和回退方案。

---

### 阶段一：基础设施搭建（第 1–4 天）

#### 步骤 1.1：开发环境初始化

**目标**：在开发者机器上搭建可运行的最低限度环境。

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
| pip install 超时 | PyPI 网络问�