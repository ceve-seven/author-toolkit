# AI 小说创作系统 — 完整实施方案 v2.0（全流程优化版）

> **版本**: v2.0（基于 v1.1 深度优化）
> **编制日期**: 2026-05-29
> **v2.0 优化依据**: 《AI小说创作系统_v1.1_系统性优化报告》（8 维度 18 项优化建议）
> **适用范围**: 从零搭建到生产部署的全流程 AI 小说创作系统
> **核心定位**: **外部 AI Agent 通过 HTTP API 驱动的全流程小说创作系统 + 用户可视中文 Markdown 双层架构**

---

## 目录

1. [系统总览与架构目标](#一系统总览与架构目标)
2. [环境配置清单](#二环境配置清单)
3. [质量保障体系（v2.0 新增核心）](#三质量保障体系v20-新增核心)
4. [用户审核工作流体系（v2.0 新增核心）](#四用户审核工作流体系v20-新增核心)
5. [外部 AI Agent 调用链（v2.0 新增核心）](#五外部-ai-agent-调用链v20-新增核心)
6. [分阶段实施流程](#六分阶段实施流程)
7. [双层架构与双向同步](#七双层架构与双向同步)
8. [性能优化与智能监控](#八性能优化与智能监控)
9. [安全加固](#九安全加固)
10. [验收标准与交付物](#十验收标准与交付物)
11. [附录：持续优化体系](#附录持续优化体系)

---

# 第一部分：完整实施方案

---

## 一、系统总览与架构目标

### 1.1 核心设计原则（v2.0 更新）

| 原则 | 定义 | 实现方式 |
|------|------|---------|
| **外部 Agent 驱动** | 所有能力通过外部 HTTP API 暴露，AI Agent 通过外部 API 调用驱动全流程 | RESTful API + 完整的 Agent 调用链定义 |
| **聊天式交互** | 用户通过自然语言对话驱动创作，AI Agent 在过程中可随时向用户发起交互 | NLP 反馈解析器 + 审核循环 API |
| **质量总控** | 所有质量保障模块由统一调度器编排，确保审查规则不遗漏不冲突 | Quality Orchestrator + 质量规则注册表 |
| **AI 痕迹清除** | 从检测到清除形成完整闭环，定量化 6 大 AI 痕迹特征 | AI Trace Purifier 独立服务 |
| **中央档案库为唯一数据源** | 所有模块数据统一存储，互相引用 | PostgreSQL + pgvector 统一数据库 |
| **模块化可扩展** | 新模块一行代码注册即可接入 | BaseModule 接口 + ModuleRegistry 注册表 |
| **双向同步用户可见** | 用户看中文 Markdown，系统操作结构化 JSON | SYNC 标记库 + 同步引擎 |
| **伏笔全生命周期管理** | 每个伏笔可追踪、可检索、防重复 | FORE 档案实体 + 向量相似度检测 |
| **智能自愈** | 系统可自动检测异常并执行预定义的自愈操作 | 自愈引擎 + 模式告警 |

### 1.2 v2.0 系统架构总图

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    外部 AI Agent 调用层（v2.0 核心）                        │
│                                                                          │
│  ┌──────────────────────┐  ┌──────────────────────┐                     │
│  │  Cursor / Claude Code │  │  自定义 AI Agent      │                     │
│  │  → 通过 HTTP API 调用  │  │  → 通过 HTTP API 调用  │                     │
│  └────────┬─────────────┘  └────────┬─────────────┘                     │
│           │                         │                                   │
│           └──────────┬──────────────┘                                   │
│                      ▼                                                   │
│         ┌──────────────────────────────────────┐                       │
│         │      Agent 调用链编排器 (v2.0)        │                       │
│         │  /api/agent/start  — 启动创作流程      │                       │
│         │  /api/agent/next   — 执行下一环节      │                       │
│         │  /api/agent/chat   — 自然语言交互      │                       │
│         │  /api/agent/status — 查询当前状态      │                       │
│         └──────────────┬───────────────────────┘                       │
└────────────────────────┼────────────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────────────┐
│                        API 网关层 (Gateway)                              │
│   统一接口 | 路由分发 | 认证鉴权 | 流量限制 | 数据脱敏 | 审计日志          │
└────────────────────────┬────────────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────────────┐
│                Workflow Orchestrator & Quality Orchestrator              │
│                                                                         │
│  ┌────────────────────────────────┐  ┌──────────────────────────────┐  │
│  │  Workflow Orchestrator         │  │  Quality Orchestrator (v2.0) │  │
│  │  - 19 环节流水线编排            │  │  - 质量规则注册表            │  │
│  │  - 任务状态管理                 │  │  - 审查链编排（串/并行）      │  │
│  │  - 用户审核断点控制             │  │  - 审查结果分级（BLOCKER/    │  │
│  │  - 外部 Agent 调用代理          │  │    CRITICAL/WARNING/INFO）   │  │
│  └────────────────────────────────┘  │  - 自动修正闭环              │  │
│                                      └──────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────────────┐
│                      消息队列 (Message Queue)                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐  │
│  │ 生成任务  │ │ 写作任务  │ │ 审核任务  │ │ 同步事件  │ │ 质量检查事件  │  │
│  │ (优先级)  │ │ (优先级)  │ │ (优先级)  │ │          │ │ (v2.0 新增)  │  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └──────┬───────┘  │
└───────┼───────────┼───────────┼───────────┼──────────────┼────────────┘
        │           │           │           │              │
┌───────▼───────────▼───────────▼───────────▼──────────────▼────────────┐
│                       子代理层 (Agent Layer)                           │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                   │
│  │生成代理(Gen)  │ │写作者(Wri)   │ │审核代理(Rev) │                   │
│  │ 动态扩缩容    │ │ 动态扩缩容    │ │ 动态扩缩容    │                   │
│  │ min:1 max:5  │ │ min:1 max:4  │ │ min:2 max:6  │                   │
│  └──────────────┘ └──────────────┘ └──────────────┘                   │
│  ┌──────────────────────────────────────────────────────────┐         │
│  │  AI Trace Purifier (v2.0 新增独立服务)                     │         │
│  │  6 大特征检测 → 三级清除 → 清除报告                       │         │
│  └──────────────────────────────────────────────────────────┘         │
│  ┌──────────────────────────────────────────────────────────┐         │
│  │  LLM Quota Manager (v2.0 新增)                           │         │
│  │  令牌桶配额控制 · 多模型拆分配额 · 优先级抢占              │         │
│  └──────────────────────────────────────────────────────────┘         │
└───────────────────────────────────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────────────┐
│                           数据层 (Data Layer)                           │
│  PostgreSQL+pgvector │ Redis │ MinIO │ ChromaDB(开发)                  │
│  索引优化  │ 连接池  │ 慢查询监控                                      │
└────────────────────────────────────────────────────────────────────────┘
```

### 1.3 写作流程 19 个环节（v2.0 扩展）

```
环节 01: 灵感启动
环节 02: 小说主题
环节 03: 拟定大纲
环节 04: 世界观设定
环节 05: 人物设定
环节 06: 人物关系
环节 07: 角色弧线
环节 08: 势力设定
环节 09: 势力关系
环节 10: 物品库
环节 11: 伏笔追踪
环节 12: 小说档案
环节 13: 小说简介
环节 14: 分卷配置
环节 15: 章节细纲
环节 16: 正文初稿
环节 17: 正文审核
环节 18: 正文修正
环节 19: 导出发布（v2.0 新增）
```

> **v2.0 说明**：v1.1 为 18 个环节。v2.0 补充「导出发布」作为第 19 步，形成完整闭环。

每个环节对应一个或多个微服务模块，通过中央档案库共享数据，通过消息队列串行或并行执行。每个环节均配置审核断点，AI Agent 按预定义调用链顺序执行。

### 1.4 外部 AI Agent 完整调用链

外部 AI Agent（如 Cursor、Claude Code、自定义 Agent）通过以下标准化 HTTP API 调用驱动完整创作流程：

```
┌─────────────────────────────────────────────────────────────────────┐
│  AI Agent 调用链（全 19 环节按序执行）                               │
│                                                                     │
│  Step 1: POST /api/agent/start {"novel_id": "xxx"}                  │
│          → 系统返回当前环节、所需参数、下一步提示                       │
│                                                                     │
│  Step 2: POST /api/agent/next {"novel_id": "xxx", "step": 1}       │
│          → 系统执行"灵感启动"模块，返回结果                            │
│          → 如需用户确认，返回 pending_review=true                     │
│                                                                     │
│  Step 3: POST /api/agent/review {"novel_id": "xxx", "step": 1,     │
│                                   "approved": true}                 │
│          → 用户审核通过，进入下一环节                                  │
│                                                                     │
│  Step 4-19: 重复 Step 2-3，逐环节推进                                 │
│                                                                     │
│  任意环节: POST /api/agent/chat {"novel_id": "xxx",                 │
│                                   "message": "修改主角动机为..."}     │
│          → 自然语言修改指令，系统自动解析并执行修改                     │
└─────────────────────────────────────────────────────────────────────┘
```

**调用链核心 API 端点**：

| 端点 | 用途 | 调用方 |
|------|------|--------|
| `POST /api/agent/start` | 启动创作流程（新建小说项目） | 外部 AI Agent |
| `POST /api/agent/next` | 执行下一环节 | 外部 AI Agent |
| `POST /api/agent/review` | 提交审核决策（通过/不通过+修改方向） | 外部 AI Agent |
| `POST /api/agent/chat` | 自然语言交互消息 | 外部 AI Agent |
| `GET /api/agent/status` | 查询当前创作进度和待办事项 | 外部 AI Agent |
| `GET /api/agent/history` | 查询完整创作历史 | 外部 AI Agent |
| `POST /api/agent/reset` | 重置当前环节（回退到指定环节） | 外部 AI Agent |

**调用链保证**：
- 每个环节执行前自动加载前置依赖数据（如大纲依赖世界观、正文依赖细纲）
- 每个环节执行后自动触发质量审查（Quality Orchestrator）
- 每个环节的修改自动同步到用户可视层（Markdown 文件）
- 外部 Agent 通过 Bearer Token 认证，所有调用记录审计日志

### 1.5 自然语言聊天式交互模型

系统支持 AI Agent 在创作过程中随时与用户进行自然语言对话：

```
用户: "我想写一个关于记忆和身份的科幻故事"

AI Agent: "基于您的想法，我生成了三个灵感方向：
   1. 记忆交易：一个可以买卖记忆的世界，主角发现自己买来的记忆不属于任何人
   2. 身份重组：一个人醒来后发现自己有七个人的记忆，但都不是他自己的
   3. 记忆殖民：外星文明通过植入集体记忆来同化人类
  请选择您感兴趣的方向，或提出修改意见。"

用户: "第二个方向不错，但把背景换成古代"

AI Agent: "好的，我重新生成了'身份重组'的古代版本——
  一位将军在战场上受伤醒来后，脑海中多了六个人的记忆：
  一个刺客、一个商人、一个宫女、一个和尚、一个工匠、一个乞丐。
  他无法分辨哪段记忆是自己的，但有一个刺客正在根据记忆中的线索追杀他。
  您觉得这个方向如何？"
```

**交互流程规范**：

```
┌─────────────────────────────────────────────────┐
│  AI Agent 向用户发起交互                        │
│  → 调用 POST /api/agent/chat 发送消息给用户      │
│  → 消息包含：文本内容 + 可选项（如多选按钮）     │
│                                                   │
│  用户回复                                       │
│  → 任意自然语言文本                              │
│  → 系统将用户消息转发回 AI Agent                 │
│                                                   │
│  AI Agent 处理用户回复                          │
│  → 解析用户意图                                 │
│  → 执行对应操作（重新生成、修改参数、继续）       │
│  → 向用户呈现结果                                │
│                                                   │
│  循环直至用户满意 → 进入下一环节                  │
└─────────────────────────────────────────────────┘
```

**聊天消息结构**：

```json
{
  "role": "agent",
  "content": "基于您的想法，我生成了三个灵感方向...",
  "options": [
    {"id": "opt_1", "label": "方向一：记忆交易"},
    {"id": "opt_2", "label": "方向二：身份重组"},
    {"id": "opt_3", "label": "方向三：记忆殖民"}
  ],
  "actions": [
    {"type": "regenerate", "label": "全部重来"},
    {"type": "customize", "label": "我自己描述"}
  ],
  "context": {
    "current_step": 1,
    "step_name": "灵感启动",
    "novel_id": "NOV-001"
  }
}
```

---

## 二、环境配置清单

### 2.1 开发环境

| 类别 | 软件/组件 | 版本要求 | 用途 |
|------|----------|---------|------|
| 操作系统 | Ubuntu 22.04 LTS / macOS 14+ / Windows 11 WSL2 | — | 主机操作系统 |
| Python | 3.11+ | ≥3.11.0 | 后端服务主语言 |
| 数据库 | SQLite | ≥3.40.0 | 开发环境轻量数据库（替代 PostgreSQL）|
| 向量搜索 | ChromaDB | ≥0.4.0 | 开发环境轻量向量数据库 |
| 缓存 | 可选（开发环境可不部署） | — | 生产环境需要 Redis |
| 消息队列 | 内存队列（开发模式） | — | 开发环境使用内存模式 |
| LLM 接口 | OpenAI API / 兼容接口 | — | 核心生成能力 |
| 嵌入模型 | bge-large-zh-v1.5 (本地) 或 text-embedding-3-large (API) | — | 中文嵌入 |
| Docker | ≥24.0 | — | 容器化部署（可选） |
| Git | ≥2.40 | — | 版本控制 |

**Python 依赖清单 (`requirements-dev.txt`)**：

```txt
# === Web 框架 ===
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
pydantic>=2.5.0
python-multipart>=0.0.6

# === 数据库 ===
sqlalchemy[asyncio]>=2.0.25
aiosqlite>=0.19.0
alembic>=1.13.0

# === 向量搜索 (开发环境) ===
chromadb>=0.4.24
sentence-transformers>=2.3.0

# === 消息队列 ===
celery[redis]>=5.3.0

# === LLM 调用 ===
openai>=1.12.0
httpx>=0.26.0
tenacity>=8.2.0

# === 工具库 ===
python-dotenv>=1.0.0
structlog>=24.1.0
pyyaml>=6.0.1
jinja2>=3.1.3
markdown>=3.5.1
python-frontmatter>=1.0.0

# === 测试 ===
pytest>=7.4.0
pytest-asyncio>=0.23.0
httpx
```

### 2.2 生产环境

| 类别 | 软件/组件 | 版本要求 | 部署方式 | 用途 |
|------|----------|---------|---------|------|
| 操作系统 | Ubuntu 22.04 LTS / Debian 12 | — | 物理机/云主机 | 主机 OS |
| 容器编排 | Docker Compose / Kubernetes | ≥24.0 / ≥1.28 | 容器化 | 应用服务容器 |
| 反向代理 | Nginx / Traefik | ≥1.24 / ≥3.0 | Docker | API 网关 |
| 数据库 | PostgreSQL | ≥16 | Docker | 主数据库 |
| 向量扩展 | pgvector | ≥0.7.0 | PostgreSQL 扩展 | 向量搜索嵌入 |
| 缓存 | Redis | ≥7.2 | Docker | 会话/缓存/队列 |
| 消息队列 | RabbitMQ | ≥3.12 | Docker | 任务队列 |
| 对象存储 | MinIO | ≥2024.1 | Docker | 文件存储 |
| 监控 | Prometheus + Grafana | latest | Docker | 性能监控 |
| 日志 | ELK Stack / Loki | latest | Docker | 日志收集 |
| LLM 接口 | OpenAI API / Claude API / 本地 Ollama | — | 外部服务 | 核心生成能力 |
| 嵌入模型服务 | TEI / 本地推理 | — | Docker/GPU | 高吞吐嵌入 |

### 2.3 生产环境 `docker-compose.yml`（v2.0 增强）

```yaml
version: '3.8'

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
      - DATABASE_POOL_SIZE=20
      - DATABASE_MAX_OVERFLOW=10
      - DATABASE_POOL_TIMEOUT=30
      - DATABASE_POOL_RECYCLE=1800
      - DATABASE_SLOW_QUERY_THRESHOLD=500
      - REDIS_URL=redis://redis:6379/0
      - RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - EMBEDDING_MODEL=${EMBEDDING_MODEL}
      - ENVIRONMENT=production
      - LOG_LEVEL=INFO
      - LOG_ROOT=/app/logs
    volumes:
      - logs_data:/app/logs
    depends_on:
      postgres: { condition: service_healthy }
      redis: { condition: service_healthy }
      rabbitmq: { condition: service_healthy }
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c",
             "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
      interval: 30s; timeout: 10s; retries: 3
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G

  # === PostgreSQL + pgvector ===
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: noveluser
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: novel_db
    volumes: [postgres_data:/var/lib/postgresql/data]
    ports: ["5432:5432"]
    command: [
      "postgres",
      "-c", "shared_buffers=256MB",
      "-c", "effective_cache_size=1GB",
      "-c", "work_mem=32MB",
      "-c", "maintenance_work_mem=128MB",
      "-c", "random_page_cost=1.1",
      "-c", "effective_io_concurrency=200",
      "-c", "log_min_duration_statement=500"
    ]
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

  # === MinIO ===
  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ACCESS_KEY}
      MINIO_ROOT_PASSWORD: ${MINIO_SECRET_KEY}
    volumes: [minio_data:/data]
    ports: ["9000:9000", "9001:9001"]
    restart: unless-stopped

  # === 嵌入模型服务 ===
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

  # === 生成代理池 ===
  generator-agent:
    build: { context: ., dockerfile: Dockerfile.agent-generator }
    environment:
      - DATABASE_URL=postgresql+asyncpg://noveluser:@postgres:5432/novel_db
      - REDIS_URL=redis://redis:6379/0
      - RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - AGENT_TYPE=generator
      - TEMPERATURE=0.85
      - LLM_QUOTA_MODEL=gpt-4o
      - LLM_QUOTA_PRIORITY=1
    depends_on: [postgres, redis, rabbitmq]
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '1'
          memory: 2G
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
      - TEMPERATURE=0.65
      - LLM_QUOTA_MODEL=gpt-4o
      - LLM_QUOTA_PRIORITY=1
    depends_on: [postgres, redis, rabbitmq]
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '1'
          memory: 2G
    restart: unless-stopped

  # === 审核代理池 ===
  reviewer-agent:
    build: { context: ., dockerfile: Dockerfile.agent-reviewer }
    environment:
      - DATABASE_URL=postgresql+asyncpg://noveluser:@postgres:5432/novel_db
      - REDIS_URL=redis://redis:6379/0
      - RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - AGENT_TYPE=reviewer
      - TEMPERATURE=0.2
      - LLM_QUOTA_MODEL=gpt-4o
      - LLM_QUOTA_PRIORITY=2
    depends_on: [postgres, redis, rabbitmq]
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '1'
          memory: 2G
    restart: unless-stopped

  # === AI Trace Purifier 服务 (v2.0 新增) ===
  ai-purifier:
    build: { context: ., dockerfile: Dockerfile.ai-purifier }
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - LOG_LEVEL=INFO
      - LOG_ROOT=/app/logs
    volumes: [logs_data:/app/logs]
    depends_on: [rabbitmq]
    deploy:
      replicas: 1
      resources:
        limits:
          cpus: '1'
          memory: 2G
    restart: unless-stopped

  # === Quality Orchestrator 服务 (v2.0 新增) ===
  quality-orchestrator:
    build: { context: ., dockerfile: Dockerfile.quality }
    environment:
      - DATABASE_URL=postgresql+asyncpg://noveluser:@postgres:5432/novel_db
      - RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
      - LOG_LEVEL=INFO
    volumes: [logs_data:/app/logs]
    depends_on: [postgres, rabbitmq]
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

  # === 自愈引擎 (v2.0 新增) ===
  self-healer:
    build: { context: ., dockerfile: Dockerfile.self-healer }
    environment:
      - PROMETHEUS_URL=http://prometheus:9090
      - RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
      - LOG_LEVEL=INFO
    depends_on: [rabbitmq]
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  rabbitmq_data:
  minio_data:
  markdown_files:
  logs_data:
```

### 2.4 环境变量配置 (`.env` 模板)

```bash
# ============================================================
# 数据库
# ============================================================
DB_PASSWORD=your_strong_password_here_change_me
DATABASE_URL=postgresql+asyncpg://noveluser:@localhost:5432/novel_db
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10
DATABASE_POOL_TIMEOUT=30
DATABASE_POOL_RECYCLE=1800
DATABASE_SLOW_QUERY_THRESHOLD=500

# ============================================================
# LLM 配置（外部 API 调用）
# ============================================================
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o
OPENAI_REVIEW_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-large

# 备用 LLM（自愈时自动切换）
OPENAI_BACKUP_API_KEY=
OPENAI_BACKUP_BASE_URL=

# 本地嵌入模型
EMBEDDING_MODEL=bge-large-zh-v1.5
EMBEDDING_ENDPOINT=http://localhost:8080/embed

# ============================================================
# 缓存 & 消息队列
# ============================================================
REDIS_URL=redis://localhost:6379/0
RABBITMQ_URL=amqp://guest:guest@localhost:5672/

# ============================================================
# 对象存储
# ============================================================
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin_secret_change_me
MINIO_BUCKET=novel-files

# ============================================================
# 应用配置
# ============================================================
ENVIRONMENT=development
LOG_LEVEL=DEBUG
SECRET_KEY=your-secret-key-for-jwt-tokens-change_me
CORS_ORIGINS=*  # v2.0: Agent-only 后端，允许所有 Agent 来源

# ============================================================
# 文件路径
# ============================================================
USER_VIEW_DIR=./user_view
SYSTEM_DATA_DIR=./system_data
SNAPSHOT_DIR=./snapshots
EXPORT_DIR=./exports

# ============================================================
# 日志系统
# ============================================================
LOG_ROOT=./logs
LOG_JSON_OUTPUT=true

# ============================================================
# Agent 调用配置 (v2.0)
# ============================================================
AGENT_AUTH_TOKEN=your-agent-token-here
WORKFLOW_MAX_CONCURRENT=3
TASK_CALLBACK_TIMEOUT=300
FORESHADOW_DUPLICATE_THRESHOLD=0.85

# ============================================================
# 质量保障配置 (v2.0 新增)
# ============================================================
QUALITY_AUTO_FIX_ENABLED=true
QUALITY_REVIEW_TIMEOUT=120
AI_PURIFIER_ENABLED=true
AI_PURIFIER_AUTO_FIX_LEVELS=1,2

# ============================================================
# LLM 配额管理 (v2.0 新增)
# ============================================================
LLM_QUOTA_GPT4O_CAPACITY=100
LLM_QUOTA_GPT4O_REFILL_RATE=10
LLM_QUOTA_GPT4O_MINI_CAPACITY=500
LLM_QUOTA_GPT4O_MINI_REFILL_RATE=50

# ============================================================
# 监控 & 自愈 (v2.0 新增)
# ============================================================
SELF_HEAL_ENABLED=true
SELF_HEAL_MAX_ATTEMPTS=3
ANOMALY_DETECTION_ENABLED=true
ANOMALY_WINDOW_MINUTES=15
```

### 2.5 项目目录结构（v2.0 更新）

```
novel-creation-system/
├── .env / .env.example / .gitignore
├── docker-compose.yml / docker-compose.dev.yml
├── Dockerfile.* (10个)
├── config/
│   ├── review_gates.yaml          # v2.0: 审核断点配置
│   ├── quality_rules.yaml         # v2.0: 质量规则配置
│   └── ai_trace_thresholds.yaml   # v2.0: AI 痕迹检测阈值
│
├── src/
│   ├── main.py / config.py
│   ├── database/
│   │   ├── engine.py / models.py / migrations/ / crud.py
│   │   └── indexes.sql            # v2.0: 索引策略 SQL
│   ├── vector_store/
│   │   ├── embeddings.py / search.py / collections.py
│   │   └── index_selector.py     # v2.0: 索引类型自动选择
│   ├── modules/                   # 12 个业务模块
│   │   ├── base_module.py / registry.py
│   │   ├── world_builder/ / character_builder/
│   │   ├── faction_builder/ / relation_builder/
│   │   ├── arc_builder/ / item_builder/
│   │   ├── foreshadow_manager/ / outline_builder/
│   │   ├── detail_outline/ / manuscript_writer/
│   │   └── theme_engine/
│   ├── agents/
│   │   ├── base_agent.py / generator_agent.py
│   │   ├── writer_agent.py / reviewer_agent.py
│   │   ├── orchestrator.py
│   │   ├── scaler.py              # v2.0: 动态扩缩容
│   │   └── quota_manager.py       # v2.0: LLM 配额管理
│   ├── workflow/
│   │   ├── engine.py / pipeline.py
│   │   ├── task_manager.py / callback_handler.py
│   │   ├── agent_chain.py         # v2.0: Agent 调用链编排
│   │   ├── nlp_feedback_parser.py # v2.0: 自然语言反馈解析
│   │   └── review_gate.py         # v2.0: 审核断点控制
│   ├── quality/                    # v2.0: 质量总控（新增一级目录）
│   │   ├── orchestrator.py        # Quality Orchestrator 核心
│   │   ├── rule_registry.py       # 质量规则注册表
│   │   ├── review_executor.py     # 审查执行器
│   │   ├── fixers/                # 自动修正器
│   │   │   ├── base_fixer.py
│   │   │   ├── sentence_rhythm_fixer.py
│   │   │   ├── transition_word_fixer.py
│   │   │   └── emotion_showing_fixer.py
│   │   └── report_aggregator.py   # 审查报告聚合
│   ├── ai_purifier/                # v2.0: AI 痕迹清除（新增一级目录）
│   │   ├── detector.py            # 6 大特征检测器
│   │   ├── purifier.py            # 清除执行器
│   │   ├── pipeline.py            # 清除流水线
│   │   ├── report.py              # 清除报告生成
│   │   └── fixers/
│   │       ├── sentence_rhythm_fixer.py
│   │       ├── transition_word_fixer.py
│   │       ├── emotion_showing_fixer.py
│   │       ├── dialogue_naturalizer.py
│   │       ├── description_defaulter.py
│   │       └── safety_bias_detector.py
│   ├── queue/
│   │   ├── producer.py / consumer.py / tasks.py
│   │   └── priority_queue.py      # v2.0: 优先级队列
│   ├── sync/
│   │   ├── engine.py / markdown_renderer.py
│   │   ├── markdown_parser.py / json_updater.py
│   │   ├── conflict_resolver.py / cascade_updater.py
│   │   ├── file_watcher.py
│   │   └── templates/
│   ├── api/
│   │   ├── router.py
│   │   ├── endpoints/
│   │   │   ├── novels.py / characters.py / world.py
│   │   │   ├── outlines.py / chapters.py / foreshadows.py
│   │   │   ├── search.py / sync.py / weight.py / logs.py
│   │   │   ├── workflow.py / tasks.py
│   │   │   ├── agent.py           # v2.0: Agent 调用链端点
│   │   │   ├── review.py          # v2.0: 审核循环端点
│   │   │   ├── chat.py            # v2.0: 聊天交互端点
│   │   │   ├── quality.py         # v2.0: 质量查询端点
│   │   │   └── monitoring.py      # v2.0: 监控查询端点
│   │   └── middleware/
│   │       ├── auth.py / rate_limit.py / error_handler.py
│   │       ├── logging_middleware.py
│   │       ├── audit_middleware.py        # v2.0: 审计日志
│   │       └── data_sanitizer_middleware.py # v2.0: 数据脱敏
│   ├── schemas/
│   │   ├── common.py / novel.py / character.py
│   │   ├── world.py / chapter.py / review.py
│   │   ├── workflow.py / task.py
│   │   ├── agent.py               # v2.0: Agent 调用 schema
│   │   ├── chat.py                # v2.0: 聊天 schema
│   │   └── quality.py             # v2.0: 质量 schema
│   ├── monitoring/                 # v2.0: 监控（新增一级目录）
│   │   ├── anomaly_detector.py    # 异常模式检测
│   │   ├── self_healer.py         # 自愈引擎
│   │   ├── metrics_collector.py   # 指标采集
│   │   └── alert_manager.py       # 告警管理
│   ├── utils/
│   │   ├── id_generator.py / prompt_templates.py
│   │   ├── llm_client.py / text_processor.py
│   │   ├── logger_config.py / log_rotation.py
│   │   ├── data_sanitizer.py      # v2.0: 数据脱敏工具
│   │   └── prompt_manager.py      # v2.0: Prompt 版本管理
│   └── review/                    # 审核引擎（由 Quality Orchestrator 调用）
│       ├── consistency_checker.py / logic_verifier.py
│       ├── literary_reviewer.py / reader_engagement.py
│       ├── word_counter.py / cross_chapter_checker.py
│       └── ai_trace_detector.py
│
├── db/
│   ├── init.sql                   # 数据库初始化（含索引）
│   ├── indexes.sql                # v2.0: 独立索引文件
│   └── seed.sql
│
├── prompts/
│   ├── generation/
│   └── review/
│
├── tests/
│   ├── unit/ / integration/ / e2e/
│
├── nginx/
│   └── nginx.conf
│
├── scripts/
│   ├── setup_dev.sh / init_db.sh / backup.sh / restore.sh
│   └── log_query.py / scale_agents.py    # v2.0: 扩缩容脚本
│
├── logs/
│   ├── system/ / archived/ / index.json
│
├── user_view/                     # 用户可视层
│   └── 我的小说_【书名】/
│       ├── 📄 小说概览.md
│       ├── 📁 01_主题/ ~ 📁 11_正文/
│       ├── 📁 变更日志/
│       └── 📁 审查报告/
│
├── system_data/                   # 系统引擎层
│   ├── novel_manifest.json
│   ├── modules/ / structure/ / manuscript/ / index/
│
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

---

## 三、质量保障体系（v2.0 新增核心）

> v1.1 方案的审核引擎包含 4 层审查，但缺乏统一调度、AI 痕迹仅检测不清除、质量规则分散在独立文档中。
> v2.0 新增 **Quality Orchestrator 质量总控** 和 **AI Trace Purifier 独立服务**，形成完整的质量保障闭环。

### 3.1 Quality Orchestrator 质量总控

Quality Orchestrator 是统一调度所有质量保障模块的核心服务，位于 Workflow Orchestrator 的下游。

#### 3.1.1 架构定位

```
     Workflow Orchestrator
              │
              ▼ 触发质量检查事件
     ┌────────────────┐
     │ quality_check  │ 队列
     └───────┬────────┘
             │
     ┌───────▼────────┐
     │  Quality        │
     │  Orchestrator   │──→ 质量规则注册表 → 加载适用的审查规则
     │  (总控调度器)    │──→ 审查链编排 → 确定执⾏顺序（串/并行）
     │                 │──→ 分配审查执⾏器 → 调用具体审查模块
     │                 │──→ 结果聚合 → 审查报告 + 分级
     └───────┬────────┘
             │
     ┌───────▼────────┐
     │  审查执⾏器列表   │
     │  ┌──────────────────┐
     │  │ L1 一致性检查器   │ ← 设定一致性审查模块
     │  │ L2 逻辑验证器     │ ← 逻辑链完整性审查模块
     │  │ L3 文学质感审查器  │ ← 含 6 大 AI 痕迹检测
     │  │ L4 读者吸引力评估  │ ← 读者吸引力评估模块
     │  │ 世界观审查器      │ ← 五层世界观审查模块
     │  │ 大纲质量审查器    │ ← 节奏/逻辑/结构审查模块
     │  │ 伏笔完整性检查器  │ ← 伏笔生命周期审查模块
     │  └──────────────────┘
     └───────┬────────┘
             │
     ┌───────▼────────┐
     │  结果分级 & 修正 │
     │  BLOCKER → 阻断流程，强制重新生成
     │  CRITICAL → 必须修改，自动触发修正或⽤户审核
     │  WARNING → 建议修改，记录审查报告
     │  INFO → 仅供观察，不影响流程
     └────────────────
```

#### 3.1.2 核心实现

```python
# src/quality/orchestrator.py
class QualityOrchestrator:
    async def execute_review_chain(
        self,
        novel_id: str,
        context: ReviewContext,
    ) -> ReviewResult:
        # 1. 从质量规则注册表加载适用的审查规则
        rules = await self.rule_registry.get_rules_for_context(context)

        # 2. 根据规则依赖关系编排审查链
        chain = await self.pipeline.compile(rules)

        # 3. 并行/串行执⾏审查
        results = []
        for step in chain:
            if step.parallel:
                batch = await asyncio.gather(*[
                    executor.execute(context) for executor in step.executors
                ])
                results.extend(batch)
            else:
                for executor in step.executors:
                    result = await executor.execute(context)
                    results.append(result)
                    if result.level == ReviewLevel.BLOCKER:
                        return self._build_result(results)

        # 4. 聚合结果并分级
        return self._aggregate(results)
```

#### 3.1.3 审查结果分级策略

| 级别 | 含义 | 处理动作 | 示例 |
|------|------|---------|------|
| **BLOCKER** | 严重问题，阻断流程 | 终止当前环节，触发重新生成 | 设定矛盾：主角在第 3 章已死亡但在第 4 章出现 |
| **CRITICAL** | 必须修改的问题 | 自动触发修正器修正，或等待用户审核 | AI 痕迹 3 个以上特征同时触发 |
| **WARNING** | 建议修改的问题 | 记录到审查报告，不阻断流程 | 某场景字数偏差 12%（阈值为 ±10%） |
| **INFO** | 仅供观察的信息 | 记录到审查报告 | 某段落情感密度略低于平均水平 |

### 3.2 质量规则注册表

所有质量保障模块在启动时自动注册自己的审查规则，实现热插拔。

```python
# src/quality/rule_registry.py
class QualityRuleRegistry:
    rules: dict[str, QualityRule] = {}

    def register_from_module(self, module_name: str, rules: list[QualityRule]):
        """模块在启动时自动注册自己的审查规则"""
        for rule in rules:
            self.rules[f"{module_name}.{rule.name}"] = rule
        self._logger.info("rules_registered",
            module=module_name, count=len(rules))

    def get_rules_for_context(self, context: ReviewContext) -> list[QualityRule]:
        """根据审查上下文获取适用的规则"""
        applicable = []
        for rule in self.rules.values():
            if rule.applies_to(context):
                applicable.append(rule)
        return applicable
```

**预注册的质量规则清单**：

| 规则名称 | 所属模块 | 触发场景 | 审查级别 | 执行优先级 |
|---------|---------|---------|---------|-----------|
| 设定一致性 | 世界观模块 | 正文生成后、设定变更后 | BLOCKER | 1（最高） |
| 逻辑链完整性 | 大纲模块 | 大纲生成后、正文生成后 | BLOCKER | 1 |
| 文学质感 | 正文模块 | 正文生成后 | CRITICAL | 2 |
| AI 痕迹检测 | AI Purifier | 正文生成后、正文修正后 | CRITICAL | 2 |
| 读者吸引力 | 正文模块 | 正文审核阶段 | WARNING | 3 |
| 世界观五层审查 | 世界观模块 | 世界观生成后、实体新增后 | BLOCKER | 1 |
| 大纲质量审查 | 大纲模块 | 大纲生成后 | BLOCKER | 1 |
| 伏笔完整性 | 伏笔模块 | 章节生成后、伏笔状态变更后 | CRITICAL | 2 |
| 字数校验 | 正文模块 | 正文生成后 | WARNING | 3 |
| 跨章节一致性 | 同步引擎 | 每章正文生成后 | CRITICAL | 2 |

### 3.3 审查结果自动修正闭环

对于 BLOCKER 和 CRITICAL 级别的问题，Quality Orchestrator 自动触发修正：

```
BLOCKER 触发
  → 记录错误详情
  → 通知 Workflow Orchestrator 回退到上一环节
  → 在重新生成时注入修正约束

CRITICAL 触发（可自动修正）
  → Quality Orchestrator 调用对应 Fixer
  → Fixer 执⾏自动修正
  → 修正后重新触发审查（仅针对原问题）
  → 如通过则继续，如仍不通过则升级为 BLOCKER

CRITICAL 触发（不可自动修正）
  → 标记为需要用户审核
  → 通知 AI Agent 向用户发起交互
  → 等待用户反馈后再继续
```

### 3.4 AI Trace Purifier 独立服务

> v1.1 方案中 AI 痕迹检测是审核引擎的一个子模块，仅负责检测。
> v2.0 将其拆分为 **独立服务**，实现从检测到清除的完整闭环。

#### 3.4.1 服务架构

```
┌─────────────────────────────────────────────────────────┐
│                  AI Trace Purifier                        │
│                                                         │
│  输入：待检查的文本（章节正文/对话/描写段落）              │
│                                                         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │ 6 大特征检测器 │───▶ 问题分类器   │───▶ 修复器选择   │  │
│  └─────────────┘    └─────────────┘    └──────┬──────┘  │
│                                                │         │
│  ┌─────────────────────────────────────────────▼──────┐  │
│  │  修复器流水线                                       │  │
│  │  ┌──────────────────┐  ┌──────────────────┐        │  │
│  │  │ L1 自动修复       │  │ L2 半自动修复     │        │  │
│  │  │ (无需用户介入)     │  │ (需要用户确认)    │        │  │
│  │  └──────────────────┘  └──────────────────┘        │  │
│  │  ┌──────────────────┐  ┌──────────────────┐        │  │
│  │  │ L3 仅报告        │  │ 清除报告生成      │        │  │
│  │  │ (用户决策)       │  │ (与审查报告集成)   │        │  │
│  │  └──────────────────┘  └──────────────────┘        │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

#### 3.4.2 6 大 AI 痕迹特征检测算法

| 特征 | 检测算法 | 阈值 | 清除策略 |
|------|---------|------|---------|
| **句式匀质化** | 计算每句字数标准差/均值，生成波动系数 | 波动系数 < 0.3 时触发 | 自动：节奏破坏式改写 |
| **过渡词依赖** | 统计"然而""因此""与此同时"等高频过渡词密度 | > 15 次/千字 | 自动：过渡替代为意象/动作 |
| **情感说明** | 检测"感到""觉得""心中充满"等情感标签表达 | 出现 > 3 次/章 | 半自动：呈现化改写（提供 3 种方案） |
| **对话功能化** | 分析对话信息交换效率（信息量/句数比） | 效率 > 0.7 | 半自动：插入无效片段 + 潜台词 |
| **描写模板化** | 匹配高频模板库（"阳光透过窗帘"等 200+ 模板） | 匹配 > 2 次/章 | 自动：陌生化替换 |
| **安全化倾向** | LLM 评估道德灰度/情感极端性/冲突不可调和度 | LLM 打分 < 3/5 | 仅报告：标记供用户决策 |

#### 3.4.3 实现代码

```python
# src/ai_purifier/detector.py
class AITraceDetector:
    async def detect(self, text: str) -> list[TraitIssue]:
        issues = []

        # 特征1：句式匀质化检测
        sentence_lengths = [len(s) for s in text.split("。")]
        mean = statistics.mean(sentence_lengths)
        std = statistics.stdev(sentence_lengths)
        fluctuation_coefficient = std / mean if mean > 0 else 1
        if fluctuation_coefficient < 0.3:
            issues.append(TraitIssue(
                trait_type="sentence_rhythm_uniform",
                severity="critical",
                fix_level=1,
                positions=self._find_uniform_segments(text),
                suggestion="执行节奏破坏式改写"
            ))

        # 特征2：过渡词依赖检测
        transition_words = ["然而", "因此", "与此同时", "另外",
                            "但是", "所以", "此外", "不过"]
        word_count = len(list(jieba.cut(text)))
        transition_count = sum(text.count(w) for w in transition_words)
        density = transition_count / (word_count / 1000)
        if density > 15:
            issues.append(TraitIssue(
                trait_type="transition_word_overuse",
                severity="warning",
                fix_level=1,
                positions=self._find_transition_overuse(text),
                suggestion="替换为意象/动作过渡"
            ))

        # 特征3-6：类似模式实现
        # 情感说明检测 → emotion_label_density
        # 对话功能化检测 → dialogue_info_ratio
        # 描写模板化检测 → template_matching
        # 安全化倾向检测 → llm_evaluation

        return issues
```

```python
# src/ai_purifier/pipeline.py
class PurificationPipeline:
    async def purify(self, text: str) -> PurificationResult:
        # 1. 检测
        issues = await self.detector.detect(text)
        if not issues:
            return PurificationResult(passed=True, text=text)

        # 2. 按清除级别分组
        auto_fix = [i for i in issues if i.fix_level == 1]
        semi_fix = [i for i in issues if i.fix_level == 2]
        report_only = [i for i in issues if i.fix_level == 3]

        # 3. 执行自动修复（L1）
        text = await self._auto_fix(text, auto_fix)

        # 4. 生成半自动修复建议（L2）
        suggestions = await self._generate_suggestions(text, semi_fix)

        # 5. 生成修复报告（L3）
        report = self._build_report(auto_fix, semi_fix, report_only)

        return PurificationResult(
            passed=len(issues) == 0,
            text=text,
            suggestions=suggestions,
            report=report,
        )
```

### 3.5 质量保障集成到工作流

每个环节完成后自动触发质量审查：

```
环节执⾏完成
  → Quality Orchestrator 收到 quality_events
  → 从规则注册表获取该环节适用的规则
  → 执⾏审查链
  → 如果有 BLOCKER 级别问题
    → 阻断流程，自动回退到上一环节
    → 在 re-prompt 中注入修正约束
  → 如果有 CRITICAL 级别问题
    → 如果可自动修正 → 触发 Fixer 修正 → 再审查
    → 如果不自动修正 → 标记为等待用户审核
  → 如果全部通过 → 进入下一环节
```

---

## 四、用户审核工作流体系（v2.0 新增核心）

> v1.1 方案的 18 个环节是"后端模块"，没有定义哪些环节需要用户审核介入。
> v2.0 新增 **19 环节审核断点矩阵** 和完整的 **审核循环 API**，
> 实现"AI 生成 → 用户审核 → AI 修改 → 再审"的完整人机协作循环。

### 4.1 19 环节审核断点矩阵

每个环节配置独立的审核要求，通过 `config/review_gates.yaml` 管理：

```yaml
# config/review_gates.yaml
review_gates:
  inspiration:
    requires_review: true
    max_iterations: 3
    auto_approve_threshold: 0.85
    review_items:
      - novelty: "创新性评估，避免与已知作品雷同"
      - market_fit: "市场匹配度，目标读者接受度"
      - emotional_potential: "情感潜力，读者共鸣空间"

  theme:
    requires_review: true
    max_iterations: 5
    auto_approve_threshold: 0.90
    review_items:
      - three_layer_completeness: "三层结构完整（表层/深层/情感切入点）"
      - differentiation: "差异化程度，与同类作品的区分度"
      - sustainability: "可持续性，能否支撑 10 万字以上篇幅"

  world_building:
    requires_review: true
    max_iterations: 5
    auto_approve_threshold: 0.85
    review_items:
      - five_layer_validation: "五层世界观验证（物理/社会/魔法/历史/文化）"
      - extreme_scenario_test: "极端场景测试（5 类压力场景 ≥ 4 个通过）"
      - rule_consistency: "规则一致性，跨维度无矛盾"

  character:
    requires_review: true
    max_iterations: 5
    auto_approve_threshold: 0.85
    review_items:
      - four_layer_profile: "四层人物档案完整（身份/心理/能力/特殊）"
      - core_conflict_pair: "核心矛盾对（core_desire ↔ deep_need）"
      - weight_scoring: "四维权重评分 + S/A/B/C 分级"

  outline:
    requires_review: true
    max_iterations: 5
    auto_approve_threshold: 0.85
    review_items:
      - causal_chain_integrity: "因果链完整，断裂点 = 0"
      - rhythm_curve: "节奏曲线合理，无连续 3 段同色"
      - three_act_ratio: "三幕比例（25% / 50% / 25% 允许 ±10%）"

  detail_outline:
    requires_review: true
    max_iterations: 3
    auto_approve_threshold: 0.85
    review_items:
      - scene_weight_valid: "场景预算总和 = 章节总预算（误差 ≤ 5%）"
      - pov_assignment: "POV 角色明确指定"
      - constraint_limit: "约束条数 ≤ 8 条/场景"

  manuscript:
    requires_review: true
    max_iterations: 10
    auto_approve_threshold: 0.80
    review_items:
      - four_layer_review: "四层审查全部通过"
      - ai_trace_purified: "AI 痕迹已清除（L1 自动、L2 已确认、L3 已报告）"
      - word_count: "字数偏差 ≤ ±10%"
      - cross_chapter_consistency: "跨章节一致性检查通过"

  relationship:
    requires_review: false
    auto_approve_threshold: 0.90

  faction:
    requires_review: false
    auto_approve_threshold: 0.85

  arc:
    requires_review: false
    auto_approve_threshold: 0.85

  item:
    requires_review: false

  foreshadow:
    requires_review: false
    auto_approve_threshold: 0.90

  novel_archive:
    requires_review: false

  chapter_config:
    requires_review: false

  export:
    requires_review: true
    max_iterations: 2
    review_items:
      - format_valid: "导出格式正确"
      - content_complete: "内容完整无遗漏"
```

### 4.2 审核循环 API

Workflow Orchestrator 中新增面向用户审核的 API 端点：

| 端点 | 用途 | 请求体 | 响应 |
|------|------|--------|------|
| `POST /api/review/submit` | 提交审核结果 | `{step, approved, feedback}` | `{next_step, status}` |
| `GET /api/review/pending` | 获取待审核事项 | — | `[{step, items, status}]` |
| `GET /api/review/{session_id}` | 获取审核会话详情 | — | `{step, content, issues, suggestions}` |
| `POST /api/review/{session_id}/feedback` | 提交修改方向 | `{feedback}` | `{updated_content, changes}` |
| `POST /api/review/{session_id}/approve` | 审核通过 | — | `{next_step}` |
| `GET /api/review/{session_id}/history` | 审核迭代历史 | — | `[{iteration, action, changes}]` |
| `POST /api/review/{session_id}/nlp-feedback` | 自然语言反馈 | `{message}` | `{parsed_ops, updated_content}` |

**审核循环流程**：

```
Step 1: AI 自动执行某个环节（如生成大纲）
Step 2: 该环节的审核断点检测到 requires_review=true
Step 3: Quality Orchestrator 自动执行质量审查
Step 4: 审查通过且 auto_approve_threshold 达标
  → 自动进入下一环节（无需用户介入）
Step 5: 审查不通过
  → Workflow Orchestrator 暂停流程
  → AI Agent 向用户发起审核请求
  → 用户通过 /api/review/submit 或 /api/review/{id}/nlp-feedback 响应
  → AI Agent 根据用户反馈修改
  → 循环直至用户满意 → 进入下一环节
```

### 4.3 自然语言反馈解析器

将用户的模糊自然语言反馈解析为可执行的修改操作：

```python
# src/workflow/nlp_feedback_parser.py
class NLPFeedbackParser:
    async def parse(self, feedback: str, context: ReviewContext) -> list[EditOperation]:
        """
        输入: "这个主角的动机太弱了"
        输出: [
            EditOperation(
                target_module="character_builder",
                target_field="core_desire",
                action="regenerate",
                params={"intensity": "increase", "specificity": "increase"}
            )
        ]
        """
        # 第一阶段：基于模板匹配
        template_matches = self._match_templates(feedback)
        if template_matches:
            return [self._template_to_op(match) for match in template_matches]

        # 第二阶段：LLM 解析（模板不匹配时）
        parsed = await self._llm_parse(feedback, context)
        return self._parse_result(parsed)
```

**常用反馈模板库（50+ 模板）**：

| 用户说 | 解析结果 |
|--------|---------|
| "太 X 了"（如太简单、太复杂） | → 降低/提升 X 维度 |
| "不够 Y"（如不够生动、不够深刻） | → 增强 Y 维度 |
| "改一下 X" | → 触发 X 字段的重新生成 |
| "我不喜欢这个 X" | → 标记 X 为否定，重新生成替代方案 |
| "类似于 Z 的感觉" | → 将 Z 特征注入当前内容 |
| "再想想" | → 完全重新生成 |
| "保留 A，修改 B" | → 保留 A 字段不变，重新生成 B 字段 |
| "把 X 改成 Y" | → 将 X 字段值直接替换为 Y |

### 4.4 聊天式交互流程

外部 AI Agent 与用户的完整聊天式交互示例：

```
[场景：正文审核环节，用户审阅第 3 章正文]

AI Agent → 系统:
  POST /api/agent/review {"novel_id": "xxx", "approved": false,
                           "feedback": "这段打斗描写不够紧张"}

系统 → AI Agent:
  {"parsed": {"target": "manuscript", "action": "enhance",
              "dimension": "tension", "priority": "high"}}

AI Agent → 用户:
  "我根据您的反馈增强了打斗场面的紧张感：
   - 缩短了句式节奏（从平均 25 字/句改为 12 字/句）
   - 增加了细节描写（汗水、呼吸、心跳）
   - 加入了不确定性（谁会在下一招倒下？）
   这是修改后的版本，您觉得如何？需要再调整吗？"

用户 → AI Agent:
  "好多了，但主角的台词还是太长了"

AI Agent → 系统:
  POST /api/workflow/next {"novel_id": "xxx",
    "modifications": [
      {"target": "manuscript.dialogue.CHAR-003",
       "action": "shorten", "max_chars_per_line": 30}
    ]}

AI Agent → 用户:
  "已修改主角台词，现在每句不超过 30 字。
   如需进一步调整，请随时告诉我。可以直接说'再短一些'或'这样很好'。"

用户 → AI Agent:
  "这样很好"

AI Agent → 系统:
  POST /api/review/{id}/approve

AI Agent → 用户:
  "第 3 章审核通过！即将进入第 4 章创作。"
```

---

## 五、外部 AI Agent 调用链（v2.0 新增核心）

> 系统所有功能通过 **外部 HTTP API** 暴露，外部 AI Agent（Cursor、Claude Code、自定义 Agent）
> 通过标准 RESTful API 调用驱动完整创作流程。
> AI Agent 不调用系统内置 API，所有调用指向外部 HTTP 端点。

### 5.1 Agent 调用的完整链路

```
┌─────────────────────────────────────────────────────────────────────┐
│  外部 AI Agent 调用链（HTTP API 驱动）                              │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  启动阶段                                                     │   │
│  │                                                              │   │
│  │  POST /api/agent/start → 创建小说项目，初始化中央档案库          │   │
│  │  POST /api/agent/chat  → 与用户对话，确认创作方向               │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                               │                                    │
│  ┌─────────────────────────────▼───────────────────────────────┐   │
│  │  创作阶段（环节 01-19 循环执⾏）                               │   │
│  │                                                              │   │
│  │  For step = 1 to 19:                                        │   │
│  │    POST /api/agent/next {"step": step}                      │   │
│  │      → 系统自动加载前置依赖数据                               │   │
│  │      → 系统自动触发质量审查                                   │   │
│  │                                                              │   │
│  │    If review_gates[step].requires_review:                    │   │
│  │      POST /api/agent/chat → 向用户展示结果                    │   │
│  │      用户反馈 → POST /api/review/{id}/nlp-feedback           │   │
│  │      循环修正 → 用户满意                                     │   │
│  │      POST /api/review/{id}/approve → 进入下一环节             │   │
│  │    Else:                                                     │   │
│  │      自动进入下一环节                                         │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                               │                                    │
│  ┌─────────────────────────────▼───────────────────────────────┐   │
│  │  发布阶段                                                     │   │
│  │                                                              │   │
│  │  POST /api/workflow/step/19 → 导出发布                       │   │
│  │  GET /api/novels/{id}/export → 下载完整小说文件               │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### 5.2 19 环节的 Agent 调用顺序

| 环节编号 | 环节名称 | 调用的 API 端点 | 依赖数据 | 审核要求 | 预计 LLM 调用次数 |
|---------|---------|----------------|---------|---------|-----------------|
| 01 | 灵感启动 | `POST /api/workflow/step/inspiration` | 用户输入 | 必须审核 | 2-3 |
| 02 | 小说主题 | `POST /api/workflow/step/theme` | 灵感输出 | 必须审核 | 3-5 |
| 03 | 拟定大纲 | `POST /api/workflow/step/outline` | 主题 | 必须审核 | 5-8 |
| 04 | 世界观设定 | `POST /api/workflow/step/world` | 大纲 | 必须审核 | 8-12 |
| 05 | 人物设定 | `POST /api/workflow/step/characters` | 世界观 | 必须审核 | 3-5/人物 |
| 06 | 人物关系 | `POST /api/workflow/step/relations` | 人物设定 | 可选审核 | 2-3/关系 |
| 07 | 角色弧线 | `POST /api/workflow/step/arcs` | 人物+关系 | 可选审核 | 2-4/弧线 |
| 08 | 势力设定 | `POST /api/workflow/step/factions` | 世界观 | 可选审核 | 3-5/势力 |
| 09 | 势力关系 | `POST /api/workflow/step/faction-relations` | 势力设定 | 可选审核 | 2-3/关系 |
| 10 | 物品库 | `POST /api/workflow/step/items` | 世界观 | 可选审核 | 1-2/物品 |
| 11 | 伏笔追踪 | `POST /api/workflow/step/foreshadows` | 大纲+人物+势力 | 可选审核 | 2-3/伏笔 |
| 12 | 小说档案 | `POST /api/workflow/step/archive` | 全部前置数据 | 可选审核 | 1 |
| 13 | 小说简介 | `POST /api/workflow/step/synopsis` | 档案 | 可选审核 | 1-2 |
| 14 | 分卷配置 | `POST /api/workflow/step/volume-config` | 大纲 | 可选审核 | 1 |
| 15 | 章节细纲 | `POST /api/workflow/step/detail-outline` | 分卷+全部设定 | 必须审核 | 2-3/章 |
| 16 | 正文初稿 | `POST /api/workflow/step/manuscript` | 细纲+全部设定 | 必须审核 | 5-10/章 |
| 17 | 正文审核 | `POST /api/workflow/step/review` | 正文初稿 | 系统自动 | 3-5 |
| 18 | 正文修正 | `POST /api/workflow/step/fix` | 审核报告 | 必须审核 | 2-5 |
| 19 | 导出发布 | `POST /api/workflow/step/export` | 全部正文 | 必须审核 | 0 |

### 5.3 外部 Agent API 调用规范

所有 API 调用遵循以下规范：

#### 5.3.1 认证

```http
Authorization: Bearer ${AGENT_AUTH_TOKEN}
X-Request-Id: <uuid>  # 唯一请求 ID，用于审计追踪
```

#### 5.3.2 通用请求格式

```json
{
  "novel_id": "NOV-001",
  "step": 5,
  "params": {
    "entity_type": "character",
    "count": 3,
    "hints": {
      "主角": "一个背负过去的独行侠",
      "配角1": "与主角价值观冲突的搭档",
      "配角2": "知道真相但不说的老者"
    }
  },
  "user_context": {
    "user_id": "USER-001",
    "session_id": "SES-001"
  }
}
```

#### 5.3.3 通用响应格式

```json
{
  "status": "success",
  "step": 5,
  "step_name": "人物设定",
  "result": {
    "entities": [
      {
        "id": "CHAR-001",
        "name": "陈渡",
        "tier": "S",
        "summary": "前特种部队成员，追查搭档之死"
      }
    ],
    "review_status": "pending",
    "quality_score": 0.82,
    "ai_trace_status": "purified"
  },
  "next_steps": [
    {"step": 6, "name": "人物关系", "status": "ready"},
    {"step": 7, "name": "角色弧线", "status": "pending", "depends_on": [6]}
  ],
  "user_messages": [
    {
      "type": "review_required",
      "content": "请审阅三个人物设定，确认是否满意"
    }
  ],
  "request_id": "REQ-001"
}
```

#### 5.3.4 异步任务查询

对于耗时较长的（如正文生成），系统返回任务 ID，Agent 轮询查询进度：

```json
// 响应
{
  "status": "async",
  "task_id": "TASK-042",
  "estimated_completion_seconds": 120,
  "check_url": "/api/tasks/TASK-042/status"
}

// 轮询 GET /api/tasks/TASK-042/status
{
  "task_id": "TASK-042",
  "status": "running",
  "progress": 45,
  "current_stage": "正在生成第 3 段...",
  "estimated_remaining_seconds": 65
}

// 完成后的最终响应
{
  "task_id": "TASK-042",
  "status": "completed",
  "result": {...},
  "quality_review": {...},
  "ai_trace_report": {...}
}
```

#### 5.3.5 错误处理规范

```json
{
  "status": "error",
  "error": {
    "code": "QUALITY_BLOCKER",
    "message": "设定矛盾：CHAR-001 在第 3 章已被标记为死亡",
    "details": {
      "conflict": {
        "entity_id": "CHAR-001",
        "field": "status",
        "chapter_3": "deceased",
        "chapter_4": "alive"
      },
      "suggestion": "请确认是否应为 CHAR-001 的双胞胎兄弟"
    },
    "request_id": "REQ-001"
  }
}
```

### 5.4 Agent 调用链 vs 内置微服务调用

| 对比项 | 外部 Agent 调用（v2.0 标准） | 内置微服务调用（不推荐） |
|--------|---------------------------|----------------------|
| 调用方式 | HTTP API (REST) | Python 函数调用 / RPC |
| 认证方式 | Bearer Token | 内部网络信任 |
| 错误处理 | HTTP 状态码 + 错误体 | 异常抛出 |
| 事务边界 | 每个接口独立事务 | 可跨服务传播事务 |
| 调用方可追踪性 | 全链路审计日志 | 有限追踪 |
| 调用链依赖 | JSON Schema 明确定义 | 代码耦合 |
| **Agent 支持** | **Cursor/Claude Code/任意 HTTP 客户端** | 仅系统内部代码 |

---

## 六、分阶段实施流程

实施分为 **6 个大阶段、19 个子步骤**。每步骤有明确的输入、输出、验证标准和回退方案。v2.0 版本新增了质量保障体系、AI 痕迹清除和审核工作流的实施步骤。

---

### 阶段一：基础设施搭建（第 1–5 天）

#### 步骤 1.1：开发环境初始化

**目标**：在开发机器上建立可运行的操作系统级环境。

**操作清单**：
```bash
# 1. 克隆项目代码
git clone <repo-url> && cd novel-creation-system

# 2. 创建虚拟环境
python3.11 -m venv venv
source venv/bin/activate

# 3. 安装开发依赖
pip install -r requirements-dev.txt

# 4. 复制环境变量模板并填写
cp .env.example .env

# 5. 初始化数据库
python -c "from src.database.engine import init_db; init_db()"

# 6. 启动开发服务器
uvicorn src.main:app --reload --port 8000
```

**验证标准**：
- `GET http://localhost:8000/health` 返回 `{"status": "ok"}`
- `GET http://localhost:8000/docs` 能打开 Swagger UI
- 日志无 ERROR 级别输出

**失败回退方案**：

| 失败现象 | 可能原因 | 回退操作 |
|---------|---------|---------|
| pip install 超时 | PyPI 网络问题 | 换国内镜像源 |
| 数据库初始化失败 | SQLAlchemy 版本兼容 | 固定版本安装 |
| uvicorn 启动端口占用 | 进程残留 | `lsof -i :8000 \| kill` 或换端口 |

#### 步骤 1.2：项目骨架搭建

**目标**：完成所有模块的空壳注册，确保模块注册表可查询。

**操作清单**：
1. 实现 `BaseModule` 抽象基类
2. 实现 `ModuleRegistry` 注册表
3. 为 12 个业务模块创建空壳子类
4. 实现 `/api/modules` GET 接口
5. 初始化质量规则注册表（QualityRuleRegistry）

**验证标准**：
- `GET /api/modules` 返回 12 个模块，状态均为 `registered`
- 质量规则注册表包含至少 10 条预注册规则

#### 步骤 1.3：数据库 Schema 部署

**目标**：在 PostgreSQL 中建好全部 **56–60 张表**，含索引策略。

**操作清单**：
1. 使用 `db/init.sql` 初始化完整 schema（含 pgvector 扩展）
2. 运行 `db/indexes.sql` 创建索引策略
3. 运行 Alembic 初始化迁移版本标记
4. 插入种子数据

**验证标准**：
- `\dt` 显示 **56+ 张表**
- 索引创建成功（通过 `\di` 确认主力查询索引已创建）
- 向量列可通过 `SELECT id, embedding <=> '[...]'::vector` 查询

#### 步骤 1.4：消息队列连通

**目标**：RabbitMQ 五个核心队列就绪（v2.0 新增 quality_check 队列）。

**操作清单**：
1. 启动 RabbitMQ（生产）或使用内存队列（开发）
2. 声明五个队列：`generation_tasks` / `writing_tasks` / `review_tasks` / `sync_events` / `quality_check`
3. 配置优先级队列支持（v2.0 新增）
4. 配置死信队列和重试策略

**验证标准**：
- RabbitMQ Management UI `http://localhost:15672` 可访问
- 五个队列均存在且消息可正常收发

---

### 阶段二：核心模块实现（第 6–20 天）

#### 步骤 2.1：世界观模块 + 质量规则注册

**输入**：小说主题 + 类型标签
**输出**：8 维度世界观规则集（≥15 条规则）
**关键点**：
- 世界观生成后自动注册审查规则到 QualityRuleRegistry
- 五层审查体系内置（物理/社会/魔法/历史/文化）
- 极端测试：5 类压力场景自动验证规则鲁棒性

**验证标准**：
- 生成规则数 ≥ 15
- 极端测试通过率 ≥ 80%
- 世界观审查规则已成功注册到 Quality Orchestrator

#### 步骤 2.2：人物模块 + 权重系统

**输入**：世界观规则 + 角色定位 hint
**输出**：四层人物档案（身份/心理/能力/特殊）
**关键点**：
- 心理层必须包含 core_desire ↔ deep_need 矛盾对
- 特殊档案：情感身体地图 + 语气指纹
- 自动计算四维权重评分

**验证标准**：
- 身份层 5 字段齐全
- 心理层含 core_desire/deep_need/core_fear 三元组
- 权重评分输出 tier（S/A/B/C）

#### 步骤 2.3–2.6：势力 / 关系 / 弧线 / 物品

按相同模式实现，每个模块：
1. 定义数据模型（继承 BaseModule）
2. 编写 Generator（通过外部 LLM API 调用生成）
3. 编写 Reviewer（自审逻辑，注册到 Quality Orchestrator）
4. 注册到 ModuleRegistry

#### 步骤 2.7：伏笔管理器

**关键点**：
- FORE 档案实体五段式生命周期
- 向量相似度重复检测（阈值环境变量化）
- 种下/提醒/回收/完结全状态流转

**验证标准**：
- 重复伏笔检出率 ≥ 90%
- 状态机转换合法（不允许跳步）

#### 步骤 2.8：大纲构建器

**输入**：全部设定档案
**输出**：三幕结构大纲（含因果链标注）
**关键点**：
- 因果链验证：每相邻事件必须有 because/since 标注
- 节奏热力图：紧张/舒缓交替比例符合类型惯例

**验证标准**：
- 因果断裂点 = 0
- 节奏热力图无连续 3 段同色

#### 步骤 2.9：细纲模块

**输入**：大纲 + 当前章节号 + 已有前文
**输出**：场景级拆解（POV 分配 / 字数预算 / 约束拉取）
**关键点**：
- 约束拉取强度校验（避免单场景约束过多导致 LLM 过载）
- 逐场景字数预算 = 章节总预算 × 场景权重

**验证标准**：
- 场景预算总和 = 章节总预算（误差 ≤ 5%）
- 约束条数 ≤ 8 条/场景

---

### 阶段三：质量体系与审核流水线（第 21–35 天）

#### 步骤 3.1：Quality Orchestrator 实现

**目标**：实现质量总控服务的完整功能。

**操作清单**：
1. 实现 `QualityOrchestrator` 核心类（审查链编排）
2. 实现 `QualityRuleRegistry` 规则注册表
3. 实现 BLOCKER/CRITICAL/WARNING/INFO 四级结果处理
4. 实现自动修正器接口（Fixer 基类）
5. 至少实现 3 个自动修正器（句式节奏/过渡词/描写模板）
6. 实现审查报告聚合器
7. 集成到 Workflow Orchestrator

**验证标准**：
- Quality Orchestrator 可作为独立 Docker 容器运行
- 质量规则注册表至少包含 10 条规则
- BLOCKER 级别问题能正确阻断工作流
- 自动修正成功率 ≥ 80%（测试集）

#### 步骤 3.2：AI Trace Purifier 实现

**目标**：实现 AI 痕迹从检测到清除的完整闭环。

**操作清单**：
1. 实现 6 大特征检测器（AITraceDetector）
2. 实现三级清除流水线（PurificationPipeline）
3. 实现 4 个自动修复器（句式节奏/过渡词/情感呈现化/描写陌生化）
4. 实现 1 个半自动修复器（对话自然化）
5. 实现安全化倾向检测器（仅报告）
6. 实现清除报告生成器

**验证标准**：
- 6 大特征全部可检测，检出率 ≥ 85%
- L1 自动修复成功率 ≥ 90%
- L2 半自动修复提供 ≥ 3 种方案供用户选择
- L3 仅报告正确标记问题位置

#### 步骤 3.3：四层审查引擎强化

**目标**：v1.1 的 4 层审查引擎升级，与 Quality Orchestrator 集成。

**操作清单**：
1. L1 一致性检查器注册为 BLOCKER 级别审查
2. L2 逻辑验证器注册为 BLOCKER 级别审查
3. L3 文学质感审查器集成 AI 痕迹检测
4. L4 读者吸引力评估器注册为 WARNING 级别审查

**验证标准**：
- 四层审查各自有独立日志文件
- 审查结果正确映射到对应的结果级别

#### 步骤 3.4：用户审核工作流实现

**目标**：审核断点矩阵 + 审核循环 API + NLP 反馈解析。

**操作清单**：
1. 实现 `review_gates.yaml` 配置解析器
2. 实现审核循环 API（7 个端点）
3. 实现自然语言反馈解析器（NLPFeedbackParser）
4. 实现 50+ 常用反馈模板库
5. 集成到 Workflow Orchestrator

**验证标准**：
- 审核断点配置可动态修改（不重启生效）
- 自然语言反馈解析准确率 ≥ 80%（测试集）
- 审核循环 API 全部通过集成测试

#### 步骤 3.5：同步引擎（保留 v1.1 实现）

**目标**：双向同步引擎正常运行。

**操作清单**：
1. JSON→Markdown 渲染
2. Markdown→JSON 解析
3. 冲突检测与解决
4. 文件变更监听
5. 联动更新追踪

**验证标准**：
- JSON→MD 和 MD→JSON 双向同步均正常
- 冲突时按配置策略处理
- 同步操作全部记录到独立日志文件

---

### 阶段四：集成联调（第 36–42 天）

#### 步骤 4.1：端到端流程验证

**验证场景**：从「灵感启动」到「导出发布」完整跑通 19 个环节。

**最小可用流程**：
```
用户输入主题 → AI 生成主题分析 → 生成大纲(3幕) → 世界观生成(8维度)
→ 创建3个核心人物 → 建立人物关系 → 生成细纲(第1章)
→ 正文生成(第1章) → 四层审查 → AI 痕迹清除 → 自动修正
→ 用户审核通过 → 进入下一章
```

**验证标准**：
- 全流程无人工干预自动完成（审核断点除外）
- 每环节输出作为下一环节输入无缝传递
- Quality Orchestrator 在每个环节后正确触发审查
- AI Trace Purifier 在正文生成后自动清除痕迹
- 用户审核断点正确暂停流程并等待反馈
- 同步引擎保持用户可视层与系统层一致

#### 步骤 4.2：外部 Agent 调用链验证

**验证场景**：外部 AI Agent 通过 HTTP API 驱动完整创作流程。

**验证标准**：
- `POST /api/agent/start` → 正确创建项目并初始化
- `POST /api/agent/next` → 正确执行每个环节
- `POST /api/agent/chat` → 正确转发消息
- `POST /api/agent/review` → 正确提交审核
- 所有端点的认证鉴权正常
- 所有调用均有审计日志

#### 步骤 4.3：并发压力测试

**测试场景**：
- 同时生成 3 个不同项目的第 1 章
- Quality Orchestrator 同时处理多个质量检查请求
- 消息队列堆积后的消费恢复能力

**验证标准**：
- 并发 3 项目无数据混淆
- 质量检查无遗漏
- 消息队列积压消费后无丢失
- 数据库连接池未耗尽

---

### 阶段五：生产部署（第 43–48 天）

#### 步骤 5.1：Docker 容器化

**操作清单**：
1. 编写所有 10 个 Dockerfile
2. 配置 docker-compose.yml 一键启动全部服务
3. 配置 Nginx 反向代理 + SSL
4. 配置数据脱敏和审计日志中间件

**验证标准**：
- `docker compose up -d` 后全部容器 healthy
- `https://<domain>/health` 返回 ok
- 审计日志中间件正常运行

#### 步骤 5.2：监控告警接入

**监控项**（v2.0 新增）：
- Prometheus 指标采集
- Grafana 仪表盘（含智能告警面板）
- 自愈引擎配置
- 使用数据仪表盘（业务分析面板）

**验证标准**：
- 智能告警在异常模式触发时正确通知
- 自愈引擎在配置场景下正确执行自愈操作
- 审计日志可追溯所有数据变更

---

### 阶段六：验收交付（第 49–52 天）

#### 步骤 6.1：功能验收清单（v2.0 更新）

| 编号 | 验收项 | 标准 | 状态 |
|------|--------|------|------|
| F-001 | 19 个创作环节全覆盖 | 每环节有对应模块/代理 | ⬜ |
| F-002 | 12 个模块全部注册可查 | GET /api/modules 返回 12 个 | ⬜ |
| F-003 | 三种代理池独立运行 | Gen/Wri/Rev 各自消费队列 | ⬜ |
| F-004 | Quality Orchestrator 正常 | 质量规则注册 + 审查链编排 + 结果分级 | ⬜ |
| F-005 | AI Trace Purifier 正常 | 6 大特征检测 + 三级清除 | ⬜ |
| F-006 | 四层审查引擎生效 | 审查结果含 4 层评分 + 分级 | ⬜ |
| F-007 | 审核断点矩阵生效 | 19 环节 review_gates.yaml 配置正确 | ⬜ |
| F-008 | 审核循环 API 可用 | 7 个端点全部响应正常 | ⬜ |
| F-009 | NLP 反馈解析准确 | 50+ 模板匹配 + LLM 兜底 | ⬜ |
| F-010 | 外部 Agent API 可调用 | Agent 认证 + 完整调用链 | ⬜ |
| F-011 | 聊天式交互正常 | Agent ↔ 用户消息传递 | ⬜ |
| F-012 | 双向同步正常 | MD 编辑后 DB 自动更新 | ⬜ |
| F-013 | 伏笔防重复 | 相似度 ≥ 阈值的被拦截 | ⬜ |
| F-014 | 字数控制 | 偏差 ≤ ±10% | ⬜ |
| F-015 | 权重评分输出 | 四维评分 + tier | ⬜ |
| F-016 | 数据库索引生效 | 慢查询日志中无全表扫描 | ⬜ |
| F-017 | 动态扩缩容 | 代理池自动扩缩 | ⬜ |
| F-018 | 数据脱敏 | 敏感信息不在日志中出现 | ⬜ |
| F-019 | 审计日志 | 所有写操作有完整审计记录 | ⬜ |
| F-020 | 自愈引擎 | 配置场景下正确自愈 | ⬜ |

#### 步骤 6.2：交付物清单

| 交付物 | 格式 | 位置 |
|--------|------|------|
| 完整源代码 | Git 仓库 | `<repo-url>` |
| 数据库 Schema SQL（含索引） | `.sql` 文件 | `db/init.sql` + `db/indexes.sql` |
| Docker 编排文件 | YAML | `docker-compose.yml` + `docker-compose.dev.yml` |
| 环境变量模板 | `.env.example` | 项目根目录 |
| 审核断点配置 | YAML | `config/review_gates.yaml` |
| 质量规则配置 | YAML | `config/quality_rules.yaml` |
| AI 痕迹阈值配置 | YAML | `config/ai_trace_thresholds.yaml` |
| API 文档 | Swagger UI | `GET /docs` |
| Agent 接入指南 | Markdown | `docs/agent_integration.md` |
| 日志系统设计文档 | Markdown | 本文档附录 |
| Prompt 模板全集 | `.txt` 文件 | `prompts/` 目录 |

---

## 七、双层架构与双向同步

> 本章保留 v1.1 的双层架构设计，新增 v2.0 的质量保障和 Agent 调用链集成说明。
> 架构设计、用户可见层、同步引擎的完整内容参见以下子章节。

### 7.1 核心设计理念

```
┌─────────────────────────────────────────────────────────────┐
│                    三层分离架构                              │
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

### 7.2 用户可视层

每个小说项目在 `user_view/` 下生成一个以书名命名的文件夹，内含完整的中文 Markdown 目录：

```
📁 user_view/
└── 📁 我的小说_【书名】/
    ├── 📄 小说概览.md                    ← 实时聚合视图
    ├── 📁 01_主题/                       ← 对应 THEME 模块
    │   ├── 📄 主题陈述.md
    │   ├── 📄 反向确认.md
    │   ├── 📄 情感出发点.md
    │   └── 📄 各卷主题映射.md
    ├── 📁 02_世界观/                     ← 含审查记录子文件夹
    │   ├── 📄 世界观总览.md
    │   ├── 📁 宇宙规则/ / 📁 地理与空间/
    │   ├── 📄 时间与历史.md / 社会结构.md / ...
    │   └── 📁 审查记录/
    │       ├── 📄 规则自洽审查.md
    │       ├── 📄 极端场景测试.md
    │       └── 📄 叙事压力审查.md
    ├── 📁 03_势力/ / 04_势力关系/
    ├── 📁 05_人物/ / 06_人物关系/ / 07_角色弧线/
    ├── 📁 08_物品仓库/
    ├── 📁 09_伏笔管理/
    ├── 📁 10_结构/                       ← 含大纲 + 细纲 + 节奏曲线
    ├── 📁 11_正文/
    ├── 📁 变更日志/
    └── 📁 审查报告/                     ← 四层审查结果 + AI 痕迹清除报告
```

### 7.3 Markdown 同步标记规范

```markdown
三种标记类型：

| 标记类型 | 格式 | 用途 | 用户可修改？ |
|---------|------|------|------------|
| 字段标记 | `<!-- SYNC:实体ID:字段路径 -->内容<!-- /SYNC -->` | 标记可同步的字段值 | ✅ 可以 |
| 元数据标记 | `<!-- SYNC_META:实体ID:属性 -->值<!-- /SYNC_META -->` | 版本号、修改时间等 | ❌ 不建议 |
| 引用标记 | `<!-- SYNC_REF:实体ID -->...<!-- /SYNC_REF -->` | 引用关系区块 | ❌ 系统维护 |

字段路径映射规则：
JSON 路径 → Markdown SYNC 标记
CHAR-001.fields.name → <!-- SYNC:CHAR-001:fields.name -->
CHAR-001.fields.core_desire → <!-- SYNC:CHAR-001:fields.core_desire -->
```

### 7.4 双向同步引擎

**同步方向**：

```
方向一：用户修改 Markdown → 同步到 JSON（+ 数据库）
  1. 扫描文件中的所有 SYNC 标记
  2. 提取标记内的当前内容
  3. 与上一次同步时的内容比对
  4. 更新对应 JSON / 数据库中的对应字段
  5. 递增 version 号
  6. 追加 change_log 记录（actor = "user_manual"）

方向二：Agent 修改 JSON（通过 API）→ 同步到 Markdown
  1. 识别被修改的 JSON 字段（从 change_log 获取）
  2. 定位对应 Markdown 文件中的对应 SYNC 标记
  3. 替换标记内的内容为新值
  4. 更新 Markdown 中的 SYNC_META
```

**冲突处理**：

| 情况 | 处理策略 |
|------|---------|
| Markdown 的 last_modified > DB 的 last_modified | 以 Markdown 为准（用户手动修改优先） |
| DB 的 last_modified > Markdown 的 last_modified | 以 DB 为准（Agent 修改优先） |
| 两者时间相同或无法判断 | 按配置策略："last_write_wins" / "manual" / "system_priority" |

**v2.0 集成说明**：
- Agent 通过 JSON API 操作数据，标注变更到 change_log
- Quality Orchestrator 的审查结果自动渲染到 `审查报告/` 目录
- AI Trace Purifier 的清除报告自动追加到审查报告中
- Agent 隐藏策略不变：**Agent 不需要编辑 Markdown 中的 SYNC 标记**

---

## 八、性能优化与智能监控

### 8.1 数据库索引策略（v2.0 新增）

#### 8.1.1 核心表索引

```sql
-- 实体查询索引
CREATE INDEX idx_characters_novel_id ON characters(novel_id, tier);
CREATE INDEX idx_factions_novel_id ON factions(novel_id, tier);
CREATE INDEX idx_relations_source_target ON entity_relations(source_id, target_id);

-- 伏笔检索索引
CREATE INDEX idx_foreshadows_status ON foreshadows(novel_id, status);
CREATE INDEX idx_foreshadows_due_chapter ON foreshadows(novel_id, due_chapter);

-- 章节/正文索引
CREATE INDEX idx_chapters_novel_volume ON chapters(novel_id, volume_id, chapter_number);
CREATE INDEX idx_manuscripts_chapter_id ON manuscripts(chapter_id, version);

-- 审计日志索引
CREATE INDEX idx_change_log_entity ON change_log(entity_type, entity_id, changed_at DESC);
CREATE INDEX idx_audit_log_user ON entity_audit_log(operator_id, operated_at DESC);
```

#### 8.1.2 向量索引策略

根据数据量动态选择索引类型：

| 数据量 | 推荐索引 | 构建时间 | 查询速度 | 召回率 |
|--------|---------|---------|---------|--------|
| < 10 万行 | 暴力搜索（无索引） | 0 | 快 | 100% |
| 10 万 - 100 万行 | IVFFlat (lists=100-500) | 数分钟 | 毫秒级 | 99% |
| 100 万 - 1000 万行 | IVFFlat (lists=500-1000) | 数十分钟 | 毫秒级 | 98% |
| > 1000 万行 | HNSW (m=16, ef=200) | 数小时 | 亚毫秒级 | 99.9% |

```python
# src/vector_store/index_selector.py
class IndexSelector:
    async def auto_select_index(self, collection_name: str):
        count = await self.get_row_count(collection_name)
        if count < 100_000:
            return IndexType.NONE
        elif count < 1_000_000:
            return IndexType.IVFFLAT
        else:
            return IndexType.HNSW
```

### 8.2 连接池与慢查询监控

**数据库连接池配置**（在 docker-compose.yml 中已配置）：

| 参数 | 值 | 说明 |
|------|-----|------|
| DATABASE_POOL_SIZE | 20 | 连接池大小 |
| DATABASE_MAX_OVERFLOW | 10 | 最大溢出连接数 |
| DATABASE_POOL_TIMEOUT | 30s | 等待连接超时 |
| DATABASE_POOL_RECYCLE | 1800s | 连接回收时间 |
| DATABASE_SLOW_QUERY_THRESHOLD | 500ms | 慢查询阈值 |

**PostgreSQL 性能参数**（已在 docker-compose.yml 中配置）：

| 参数 | 值 | 优化目标 |
|------|-----|---------|
| shared_buffers | 256MB | 缓存常用数据 |
| effective_cache_size | 1GB | 查询计划器缓存估算 |
| work_mem | 32MB | 排序和连接操作 |
| maintenance_work_mem | 128MB | VACUUM/索引维护 |
| random_page_cost | 1.1 | SSD 优化 |
| effective_io_concurrency | 200 | SSD 优化 |

### 8.3 智能告警（v2.0 新增）

#### 8.3.1 基于日志模式的异常检测

不依赖固定阈值，基于历史模式识别异常：

```python
# src/monitoring/anomaly_detector.py
class PatternAnomalyDetector:
    SLIDING_WINDOW_MINUTES = 15

    async def detect(self) -> list[AnomalyAlert]:
        patterns = [
            "llm_error_rate_spike",         # LLM 错误率突升
            "queue_depth_growth",            # 队列深度持续增长
            "review_loop_excessive",         # 同章节审核迭代异常增多
            "sync_conflict_frequency",       # 同步冲突频率异常
            "memory_leak_pattern",           # 内存持续增长不回落
        ]
        alerts = []
        for pattern in patterns:
            baseline = await self._calculate_baseline(pattern)
            current = await self._get_current_value(pattern)
            if current > baseline + 2 * baseline_stdev:
                alerts.append(AnomalyAlert(
                    pattern=pattern,
                    severity="yellow" if current < baseline + 3 * stdev else "red",
                    current_value=current,
                    baseline_value=baseline,
                ))
        return alerts
```

#### 8.3.2 告警规则

| 告警类型 | 检测方式 | 基线计算 | 黄色告警 | 红色告警 |
|---------|---------|---------|---------|---------|
| LLM 错误率突升 | 滑动窗口统计 | 15 分钟平均错误率 | > 基线 + 2σ | > 基线 + 3σ |
| 队列深度增长 | 时间序列分析 | 15 分钟平均深度 | 持续增长 > 5 分钟 | 深度 > 1000 |
| 审核迭代异常 | 计数统计 | 前 10 章平均迭代次数 | > 基线 + 2σ | > 基线 + 3σ |
| 同步冲突频率 | 计数统计 | 前 1 小时冲突频率 | > 基线 × 3 | > 基线 × 5 |
| 连接池耗尽 | 指标监控 | 活跃连接数/总连接数 | > 70% | > 90% |

### 8.4 自愈引擎（v2.0 新增）

告警触发后，自动执行诊断流程并尝试自愈：

```python
# src/monitoring/self_healer.py
class SelfHealer:
    healing_actions = {
        "queue_depth_growth": [
            Action("诊断", "check_consumer_health"),
            Action("扩容", "scale_consumer_pool", {"increment": 1}),
            Action("验证", "verify_queue_depth_decreasing"),
        ],
        "llm_error_rate_spike": [
            Action("诊断", "check_llm_api_status"),
            Action("降级", "switch_to_backup_model"),
            Action("重试", "retry_failed_tasks"),
        ],
        "database_connection_pool_exhausted": [
            Action("诊断", "check_slow_queries"),
            Action("扩容", "increase_pool_size", {"increment": 5}),
            Action("终止", "terminate_idle_connections"),
        ],
        "agent_pool_congestion": [
            Action("诊断", "check_agent_queue_depth"),
            Action("扩容", "scale_agent_pool", {"increment": 1}),
        ],
    }

    MAX_ATTEMPTS_PER_24H = 3

    async def heal(self, alert: AnomalyAlert) -> HealingResult:
        if await self._exceeded_max_attempts(alert.type):
            return HealingResult(status="skipped",
                message=f"24 小时内已尝试 {self.MAX_ATTEMPTS_PER_24H} 次，需人工介入")
        pipeline = self.healing_actions.get(alert.type, [])
        for action in pipeline:
            result = await action.execute()
            if not result.success:
                return HealingResult(status="partial",
                    message=f"自愈步骤 {action.name} 失败，需人工介入")
        return HealingResult(status="healed")
```

**安全边界**：
- 自愈操作需记录审计日志
- 同一问题 24 小时内自愈尝试上限为 3 次
- 所有自愈操作发送通知给运维人员

### 8.5 代理池动态扩缩容（v2.0 新增）

基于队列深度和任务等待时间动态调整代理数量：

| 代理类型 | 扩容条件 | 缩容条件 | 最小副本 | 最大副本 |
|---------|---------|---------|---------|---------|
| Generator | 队列深度 > 50 或等待 > 60s | 队列深度 < 10 持续 5 分钟 | 1 | 5 |
| Writer | 队列深度 > 30 或等待 > 120s | 队列深度 < 5 持续 10 分钟 | 1 | 4 |
| Reviewer | 队列深度 > 40 或等待 > 90s | 队列深度 < 8 持续 5 分钟 | 2 | 6 |

### 8.6 LLM API 配额管理器（v2.0 新增）

基于令牌桶算法，防止多个代理同时调用 LLM API 导致限流：

| 模型 | 容量 | 填充速率 | 用途 |
|------|------|---------|------|
| gpt-4o | 100 令牌 | 10/分钟 | 生成和写作 |
| gpt-4o-mini | 500 令牌 | 50/分钟 | 审核和检测 |
| text-embedding-3-large | 1000 令牌 | 200/分钟 | 嵌入计算 |

**优先级分配**：
- `priority=2`：用户等待中的任务（审核、交互式生成）
- `priority=1`：流水线自动任务（大纲、正文生成）
- `priority=0`：批量后台任务（嵌入计算、批量审查）

### 8.7 性能基线指标

| 指标 | 目标值 | 测量方法 |
|------|--------|---------|
| API 平均响应时间 (P50) | < 200ms | Prometheus histogram |
| API P99 响应时间 | < 2000ms | Prometheus histogram |
| 单章生成耗时 | < 300s (6000字) | manuscript 日志 duration_ms |
| 单章审核+清除耗时 | < 180s | review + purifier 日志 |
| 同步操作延迟 | < 500ms | sync 日志 duration_ms |
| LLM 调用成功率 | > 99% | llm_calls.log 统计 |
| 数据库查询 P99 | < 100ms | 慢查询日志统计 |
| 日志写入延迟对 API 影响 | < 5ms | 压力测试对比 |

### 8.8 Grafana 监控面板

**核心面板**（v2.0 新增业务面板）：

| 面板 | 查询 | 告警阈值 |
|------|------|---------|
| API 请求速率 | `rate(http_requests_total[5m])` | — |
| API 错误率 | `rate(http_errors[5m]) / rate(http_requests_total[5m])` | > 5% |
| 队列深度 | `rabbitmq_queue_messages`（按队列分） | > 1000 |
| LLM 费用/小时 | `sum(cost_usd)` from llm_calls.log | > $10/hour |
| 质量审查 BLOCKER 数 | `count(quality_blocker)` | > 0 |
| AI 痕迹清除率 | `purified_count / total_issues` | < 85% |
| 各环节审核迭代次数 | `count(review_iterations)` by step | — |
| LLM 配额使用率 | `token_bucket_usage` by model | > 90% |
| 自愈事件记录 | `count(self_heal_events)` | — |
| 代理池副本数 | `agent_replicas` by type | — |

---

## 九、安全加固（v2.0 新增）

### 9.1 数据脱敏处理器

在日志写入前自动脱敏敏感字段，防止 API Key、密码等泄露到日志中。

```python
# src/utils/data_sanitizer.py
class DataSanitizer:
    SENSITIVE_PATTERNS = {
        "api_key": r"(sk-|pk-)[a-zA-Z0-9]{20,}",
        "password": r'"(password|secret|token)"\s*:\s*"[^"]+"',
        "jwt_token": r"eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+",
    }

    @classmethod
    def sanitize(cls, data: dict) -> dict:
        sanitized = {}
        for key, value in data.items():
            if any(p in key.lower() for p in ["key", "secret", "password", "token"]):
                sanitized[key] = "***REDACTED***"
            elif isinstance(value, dict):
                sanitized[key] = cls.sanitize(value)
            elif isinstance(value, str):
                sanitized[key] = cls._sanitize_string(value)
            else:
                sanitized[key] = value
        return sanitized
```

### 9.2 API 审计日志中间件

记录所有写操作的完整审计链路：

```python
# src/api/middleware/audit_middleware.py
class AuditMiddleware:
    async def __call__(self, request: Request, call_next):
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            response = await call_next(request)
            await self._log_audit(request, response)
            return response
        return call_next(request)

    async def _log_audit(self, request, response):
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "operator": request.headers.get("X-User-Id", "unknown"),
            "method": request.method,
            "path": request.url.path,
            "params": dict(request.query_params),
            "status_code": response.status_code,
            "request_id": request.headers.get("X-Request-Id"),
        }
        await audit_logger.info("api_audit", **DataSanitizer.sanitize(audit_entry))
```

### 9.3 安全加固清单

| 安全项 | 实现方式 | 验收标准 |
|--------|---------|---------|
| 敏感信息脱敏 | DataSanitizer 中间件 | API Key/密码不出现在日志中 |
| API 操作审计 | AuditMiddleware | 所有写操作可追溯 |
| Agent 认证 | Bearer Token 验证 | 无有效 Token 返回 401 |
| 流量限制 | RateLimitMiddleware | 单 IP 100 次/分钟 |
| CORS 配置 | CORS_ORIGINS=*（Agent-only） | 仅 Agent 来源可访问 |
| 数据库最小权限 | PostgreSQL 角色权限 | 应用账号仅 CRUD 权限 |

---

## 十、验收标准与交付物

### 10.1 功能验收（共 20 项）

见 6.1 节《功能验收清单（v2.0 更新）》。

### 10.2 非功能验收

| 编号 | 验收项 | 标准 |
|------|--------|------|
| NF-001 | 可用性 | 系统 7×24 可用，计划内停机 < 4h/月 |
| NF-002 | 并发支持 | ≥ 3 个小说项目同时创作互不干扰 |
| NF-003 | 数据安全 | 敏感信息不出现在日志中 |
| NF-004 | 审计追踪 | 所有数据变更可在审计日志中追溯 |
| NF-005 | 日志保留 | 操作日志 ≥ 90 天，审计日志永久保留 |
| NF-006 | 恢复能力 | 任意单章节可在 5 分钟内恢复 |
| NF-007 | 性能 | API P99 < 2s，单章生成 < 5min |
| NF-008 | Agent 可调用性 | 所有创作功能可通过 RESTful API 完成 |
| NF-009 | 质量保障 | 每环节自动触发质量审查 |
| NF-010 | AI 痕迹清除 | 正文生成后自动执行清除流水线 |

### 10.3 交付物清单

| 交付物 | 格式 | 位置 |
|--------|------|------|
| 完整源代码 | Git 仓库 | `<repo-url>` |
| 数据库 Schema SQL（含索引） | `.sql` 文件 | `db/init.sql` + `db/indexes.sql` |
| Docker 编排文件 | YAML | `docker-compose.yml` + `docker-compose.dev.yml` |
| 环境变量模板 | `.env.example` | 项目根目录 |
| 审核断点配置 | YAML | `config/review_gates.yaml` |
| 质量规则配置 | YAML | `config/quality_rules.yaml` |
| AI 痕迹阈值配置 | YAML | `config/ai_trace_thresholds.yaml` |
| Agent 调用链文档 | Markdown | `docs/agent_call_chain.md` |
| API 文档 | Swagger UI | `GET /docs` |
| 实施检查清单 | Markdown | `docs/implementation_checklist.md` |

---

## 附录：持续优化体系

### A.1 Prompt 版本管理系统

支持 Prompt 模板的版本控制、A/B 测试和自动回退：

```python
# src/utils/prompt_manager.py
class PromptManager:
    async def get_prompt(self, name: str, version: str = "latest") -> PromptTemplate:
        """获取指定 prompt 模板"""

    async def set_active_version(self, name: str, version: str):
        """切换活跃版本"""

    async def ab_test(self, name: str, versions: list[str], ratio: list[float]):
        """对指定 prompt 执行 A/B 测试"""

    async def auto_rollback(self, name: str, threshold: float = 0.1):
        """如果新版本导致质量下降超过阈值，自动回退"""
```

### A.2 使用数据仪表盘

在 Grafana 中增加业务分析面板，支持数据驱动的持续优化：

| 指标 | 数据来源 | 分析价值 |
|------|---------|---------|
| 各环节平均审核迭代次数 | review_logs | 识别质量瓶颈环节 |
| 各 AI 痕迹类型检出率 | purifier_logs | 识别最顽固的 AI 痕迹 |
| 各模块修改频率 | change_log | 识别频繁变动的设定类型 |
| 用户反馈关键词聚类 | review_feedback | 发现用户最关注的质量维度 |
| 生成-审核通过率趋势 | review_logs | 评估整体质量趋势 |
| Prompt 版本切换影响 | ab_test_results | 量化 prompt 优化效果 |

### A.3 持续优化流程

```
每月一次优化周期：

1. 收集使用数据（30 天）
   → 从仪表盘获取各环节迭代次数、AI 痕迹检出率、用户反馈关键词

2. 识别优化机会
   → 找出审核迭代最多的环节 → 优化该环节的 Prompt
   → 找出检出率最高的 AI 痕迹 → 优化该痕迹的检测/清除算法
   → 找出用户反馈最频繁的关键词 → 优化对应模块

3. 实施优化
   → 创建新版 Prompt（通过 PromptManager 注册新版本）
   → 在新项目中启用 A/B 测试（新版本 50% 流量）
   → 收集 A/B 测试数据（7 天）

4. 验证与推广
   → 对比新版 vs 旧版的质量指标
   → 如新版显著提升 → 正式切换为默认版本
   → 如无提升或下降 → 自动回退到旧版本

5. 更新优化报告
   → 记录优化前后的对比数据
   → 更新《AI小说创作系统_v1.1_系统性优化报告》
```

### A.4 失败回退方案汇总

| 故障类型 | 检测方式 | 默认回退 | 人工介入条件 |
|---------|---------|---------|------------|
| LLM API 超时 | 调用 > 30s | 自动重试 3 次（指数退避） | 重试全部失败 |
| LLM 返回格式错误 | JSON 解析失败 | 重新 prompt（加格式约束） | 连续 2 次失败 |
| 数据库连接丢失 | 操作异常 | 自动重连（最多 5 次） | 30 秒内无法恢复 |
| 消息队列堆积 | 深度 > 1000 | 自动扩容消费者 | 堆积持续 > 10min |
| 审核一直不通过 | 同章节 > 3 次 | 降低非必需层阈值 | 必需层仍不通过 |
| 同步冲突 | 双向修改同一字段 | 按策略自动解决 | strategy=manual 时 |
| Quality BLOCKER | 审查结果返回 BLOCKER | 自动回退到上一环节 | 连续 2 次 BLOCKER |
| AI 痕迹清除失败 | 清除后二次检测未通过 | 重新执行清除流水线 | 连续 3 次失败 |
| 自愈尝试超出上限 | 24 小时内同问题 > 3 次 | 升级为人工工单 | 即时 |