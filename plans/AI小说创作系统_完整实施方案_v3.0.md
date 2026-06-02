# AI 小说创作系统 — 完整实施方案 v3.0（Agent-Native 原生版）

> **版本**: v3.0（从 v2.0 服务化架构重建为 Agent-Native 原生架构）
> **编制日期**: 2026-05-29
> **v3.0 核心变更**: 去掉所有 HTTP API / Docker / PostgreSQL / Redis / RabbitMQ，改为 **Agent 直接运行 Python 代码、操作本地文件系统** 的原生模式
> **核心定位**: **AI Agent 在本地直接执行的 skill 式小说创作系统 + 用户可视中文 Markdown 双层架构**
> **执行方式**: AI Agent（如 Trae、Cursor、Claude Code）直接运行 `python agent_entry.py`，无需启动任何服务

---


## 目录

1. [系统总览与架构目标](#一系统总览与架构目标)
2. [环境与项目结构](#二环境与项目结构)
3. [agent_entry.py —— Agent 入口脚本](#三agent_entrypy--agent-入口脚本)
4. [19 环节创作流程](#四19-环节创作流程)
5. [质量保障体系](#五质量保障体系)
6. [AI 痕迹清除体系](#六ai-痕迹清除体系)
7. [步骤协议体系](#七步骤协议体系)
8. [双向同步引擎](#八双向同步引擎)
9. [双层架构（用户可视层 + 系统层）](#九双层架构用户可视层--系统层)
10. [分阶段实施指南](#十分阶段实施指南)
11. [验收标准](#十一验收标准)
12. [附录：完整项目文件清单](#附录完整项目文件清单)

---

## 一、系统总览与架构目标

### 1.1 v3.0 核心架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        AI Agent 执行层（v3.0 核心）                       │
│                                                                         │
│  Agent 执行: python agent_entry.py                                      │
│  → 读取 novel_id（或创建新项目）                                         │
│  → 按 19 环节顺序执行                                                    │
│  → 每环节: 调用 modules.* → quality.* → purifier.* → sync.*             │
│  → 每环节: 加载步骤协议，展示方案等待用户确认                           │
│  → 全部完成后输出完整小说 Markdown 文件                                  │
│                                                                         │
└───────────────────────────┬─────────────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────────────┐
│                    核心引擎层（Python 模块直接调用）                        │
│                                                                         │
│  ┌───────────────────────┐  ┌────────────────────────┐                  │
│  │  Workflow Orchestrator │  │  Quality Orchestrator   │                  │
│  │  → 环节顺序编排         │  │  → 规则注册表            │                  │
│  │  → 依赖数据加载         │  │  → 审查链执行            │                  │
│  │  → 步骤协议加载         │  │  → 结果分级 & 修正       │                  │
│  └─────────┬─────────────┘  └──────────┬─────────────┘                  │
│            │                           │                                 │
│            ▼                           ▼                                 │
│  ┌───────────────────────┐  ┌────────────────────────┐                  │
│  │  AI Trace Purifier    │  │  Sync Engine            │                  │
│  │  → 6 大特征检测        │  │  → sync_md_to_json()   │                  │
│  │  → 三级清除            │  │  → sync_json_to_md()   │                  │
│  │  → 清除报告            │  │  → conflict_resolve()  │                  │
│  └───────────────────────┘  └────────────────────────┘                  │
│                                                                         │
│  ┌────────────────────────────────────────────────────────────┐         │
│  │  12 个业务模块（直接 Python 函数调用）                        │         │
│  │  modules.world_builder / character_builder / foreshadow... │         │
│  └────────────────────────────────────────────────────────────┘         │
└───────────────────────────┬─────────────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────────────┐
│                        数据层（全部本地文件）                              │
│                                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐            │
│  │  SQLite      │  │  ChromaDB    │  │  文件系统            │            │
│  │  data/novel. │  │  data/       │  │  user_view/ ← 用户看 │            │
│  │  db          │  │  chromadb/   │  │  system_data/ ← 系统 │            │
│  └──────────────┘  └──────────────┘  └────────────────────┘            │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 核心设计原则（v3.0）

| 原则 | 定义 | 实现方式 |
|------|------|---------|
| **用户驱动** | 每个环节 Agent 必须先展示方案，用户确认后才能执行。Agent 不能替用户做任何决定 | 三明治交互模式：展示方案 → 用户决策 → 执行 → 确认完成 |
| **Agent-Native** | Agent 直接运行 Python 代码，无需启动任何外部服务 | `agent_entry.py` 入口 + 直接模块调用 |
| **零基础设施** | 不需要 Docker、数据库服务、消息队列 | SQLite + ChromaDB（都是本地文件） |
| **质量总控** | 所有质量保障模块统一编排 | Quality Orchestrator（无消息队列） |
| **AI 痕迹清除** | 从检测到清除形成完整闭环 | AI Trace Purifier 模块直接调用 |
| **中央档案库为唯一数据源** | 所有模块数据统一 SQLite 存储 | SQLAlchemy + SQLite |
| **双向同步用户可见** | 用户看中文 Markdown，系统操作结构化 JSON | `sync_engine.py` 两个函数 |
| **伏笔全生命周期管理** | 每个伏笔可追踪、可检索、防重复 | ChromaDB 向量相似度检测 |
| **即拿即用** | 克隆 → `pip install -r requirements.txt` → `python agent_entry.py` | 无需任何配置 |

### 1.3 19 环节创作流程

```
环节 01: 灵感启动          环节 08: 势力设定          环节 15: 章节细纲
环节 02: 小说主题          环节 09: 势力关系          环节 16: 正文初稿
环节 03: 拟定大纲          环节 10: 物品库            环节 17: 正文审核
环节 04: 世界观设定        环节 11: 伏笔追踪          环节 18: 正文修正
环节 05: 人物设定          环节 12: 小说档案          环节 19: 导出发布
环节 06: 人物关系          环节 13: 小说简介
环节 07: 角色弧线          环节 14: 分卷配置
```

### 1.4 Agent 执行流程——三明治交互模式（v3.0 核心变更）

**规则：每个环节都必须经过"展示 → 决策 → 执行 → 确认"四步，Agent 不能跳过任何一步。**

```
Agent 执行: python agent_entry.py
│
├── Step 0: 初始化
│   ├── 连接 SQLite 数据库 (data/novel.db)
│   ├── 连接 ChromaDB 向量库 (data/chromadb/)
│   ├── 加载 QualityOrchestrator 规则
│   └── 加载 step_protocols.yaml 步骤协议
│
├── For step = 1 to 19:
│   │
│   ├── 第一阶段：展示（Agent 向用户报告当前状态）
│   │   ├── print(f"📝 即将开始: 环节 {step}/19 {名称}")
│   │   ├── print(f"   前置依赖: {依赖模块列表}")
│   │   ├── print(f"   已有数据: {已有内容摘要}")
│   │   └── print("我的执行计划是：")
│   │       ├── 1. 读取 {X} 和 {Y} 数据
│   │       ├── 2. 按照 {Z} 规则生成内容
│   │       └── 3. 执行质量审查并生成报告
│   │
│   ├── 第二阶段：用户决策（Agent 必须等待用户指令）
│   │   ├── print("可用命令:")
│   │   ├── print("  [执行]   按计划开始")
│   │   ├── print("  [修改]   调整计划后执行（请说明如何修改）")
│   │   ├── print("  [跳过]   跳过此环节")
│   │   └── user_input = input("请输入命令 > ")
│   │       ├── "执行" → 继续
│   │       ├── "修改 ..." → 解析修改指令，调整计划
│   │       └── "跳过" → 标记跳过，进入下一环节
│   │
│   ├── 第三阶段：执行（Agent 按照用户指令执行）
│   │   ├── 加载前置依赖数据
│   │   ├── 调用模块函数生成内容
│   │   ├── 执行质量审查
│   │   ├── 执行 AI 痕迹清除（仅正文相关环节）
│   │   └── 执行双向同步（更新 Markdown 文件）
│   │
│   └── 第四阶段：确认（Agent 展示结果，用户确认后继续）
│       ├── print(f"✅ 环节 {step}/19 {名称} 已完成")
│       ├── print(f"   生成内容摘要: {...}")
│       ├── print(f"   质量评分: {...}")
│       ├── print(f"   审查结果: {...}")
│       ├── print("可用命令:")
│       ├── print("  [确认]   满意，进入下一环节")
│       ├── print("  [修改]   不满意，修改后重新执行")
│       └── user_input = input("请输入命令 > ")
│           ├── "确认" → 保存当前状态，进入 step + 1
│           ├── "修改 ..." → 回到第三阶段，重新执行
│           └── "回到步骤 X" → 回退到指定步骤修改
│
└── Step 20: 完成
    ├── print("🎉 全部 19 个环节已完成！")
    ├── print(f"📁 小说文件: user_view/{书名}/")
    └── print(f"📊 审查报告: user_view/{书名}/审查报告/")
```

#### 聊天式交互示例

```
[Agent 启动]
系统: 欢迎使用 AI 小说创作系统 v3.0！
请描述您想创作的小说主题或灵感方向：

用户: 我想写一个关于记忆和身份的故事，背景设定在古代

[Agent 执行 环节 01: 灵感启动]
系统: 基于您的想法，我生成了三个灵感方向——
  1. 身份重组：一位将军在战场上受伤后，脑海中多了六个人的记忆
  2. 记忆烙印：一个可以通过触碰读取他人记忆的工匠
  3. 遗忘诅咒：整个村庄的人每天都会忘记前一天的事

[Agent 执行 质量审查]
系统: ✓ 灵感方向审查通过（创新性: 0.88, 情感潜力: 0.92）

[Agent 展示方案 → 等待用户决策]
系统: 请选择或提出修改意见（输入编号，或输入您的建议）:

用户: 选第 1 个，但把六个人改成三个人

[Agent 执行修改]
系统: 已更新灵感方向：身份重组（三身份版本）。
请确认是否满意？（输入"通过"继续，或继续修改）:

用户: 通过

[Agent 进入 环节 02 → 重新开始四阶段循环]
```

### 1.5 Agent 约束规则（v3.0 核心）

Agent 在任何时候都必须遵守以下规则。这些规则不可被 Agent 自身修改或绕过。

#### 规则一：三明治交互（不可违反）

```
每个环节 = { 展示 } → { 用户决策 } → { 执行 } → { 确认 }
         ↑                        ↑              ↑
    必须展示完整计划         必须等待用户指令      必须等待用户确认
```

Agent 不得：
- ❌ 在展示计划之前直接执行
- ❌ 跳过用户确认环节
- ❌ 自动执行并仅通知用户（"我已经完成了，结果如下"）
- ❌ 替用户做决定（"我建议跳过这个环节，所以就跳过了"）

#### 规则二：可用命令列表

Agent 在每个环节的"用户决策"和"确认"阶段必须展示可用命令：

| 命令 | 阶段 | 含义 |
|------|------|------|
| `执行` | 决策 | 按 Agent 展示的计划执行 |
| `修改 <内容>` | 决策/确认 | 按用户要求修改计划或结果 |
| `跳过` | 决策 | 跳过此环节（标记为已跳过） |
| `确认` | 确认 | 确认结果，进入下一环节 |
| `重做` | 确认 | 不满意，重新执行当前环节 |
| `回到 <步骤号>` | 确认 | 回退到指定环节重新执行 |
| `停止` | 任意 | 保存当前进度，退出系统 |
| `查看 <模块>` | 任意 | 查看某个模块的当前数据 |

#### 规则三：数据写入规则

```
所有写入操作必须经过以下路径：
  1. Agent 调用 modules.* 模块 → 生成结构化数据
  2. 写入 SQLite 数据库（data/novel.db）
  3. 调用 sync_engine.sync_json_to_md() → 渲染为用户 Markdown
  4. 不直接写入 user_view/ 目录（交给同步引擎处理）
```

Agent 不得：
- ❌ 跳过同步引擎直接修改 Markdown 文件
- ❌ 修改 SQLite 数据库后不同步
- ❌ 删除用户已确认的数据

#### 规则四：回退规则

```
用户在任何时候都可以要求回退到之前的环节：
  "回到第 3 步" → 回退到环节 03，保留环节 01-02 的数据
  "世界观重做" → 只重做世界观环节，其他不受影响
  "全部重来" → 删除当前项目的所有数据，从环节 01 开始
```

Agent 执行回退时：
1. 保留目标环节之前的所有数据
2. 删除目标环节及其之后的所有数据
3. 在 change_log 中记录回退操作
4. 通知用户哪些数据被保留、哪些被删除

#### 规则五：质量事故处理

```
质量审查发现 BLOCKER 级别问题时：
  1. Agent 必须立即向用户报告问题详情
  2. 展示问题来源（哪个模块、哪个数据、什么冲突）
  3. 提供修复建议
  4. 等待用户指令（修改/重做/忽略）
  5. Agent 不得自行决定是否忽略 BLOCKER
```

#### 规则六：系统边界

```
Agent 绝对不可：
  ❌ 修改 config.py（除用户明确要求外）
  ❌ 修改 agent_entry.py 的执行逻辑
  ❌ 修改 step_protocols.yaml 步骤协议
  ❌ 删除 data/novel.db 数据库文件
  ❌ 调用未在 modules/ 注册的外部 Python 模块操作小说数据
  ❌ 向小说数据中注入与创作无关的内容
```

---

### 1.6 三层架构（v3.0 核心设计）

系统分为三个逻辑层，每层有明确定义的责任边界：

```
┌─────────────────────────────────────────────────────────────────┐
│  **执行层（Orchestration Layer）**                                │
│                                                                 │
│  职责：用户交互、流程编排、Agent 调用                              │
│  组件：agent_entry.py / WorkflowOrchestrator / NLPFeedbackParser  │
│  原则：不直接操作数据库和文件系统                                   │
│                                                                 │
│  ┌─ 用户输入 → _present_plan() → _wait_for_decision() ──────┐   │
│  │  → _execute_step() → _wait_for_confirmation() → 下一环节    │   │
│  └──────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│  **引擎层（Engine Layer）**                                      │
│                                                                 │
│  职责：内容生成调度、存储验证、质量审查、痕迹清除、双向同步          │
│  组件：12 个 BaseModule 子类 / QualityOrchestrator               │
│        / AITracePurifier / SyncEngine                            │
│  原则：不与用户直接交互，不调用 LLM                                │
│                                                                 │
│  ┌─ Agent 生成 content → module.run(context, content) ──────┐   │
│  │  → validate() → 写 SQLite → quality.review() → sync()     │   │
│  └──────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│  **数据层（Data Layer）**                                        │
│                                                                 │
│  职责：持久化、向量检索、文件读写                                  │
│  组件：SQLite (data/novel.db) / ChromaDB (data/chromadb/)        │
│        / user_view/ (Markdown) / system_data/ (JSON)             │
│  原则：引擎层唯一的数据访问入口，执行层不直接访问                    │
│                                                                 │
│  ┌─ SQLAlchemy ORM → 56+ 张表 ── ChromaDB 向量嵌入 ──┐          │
│  │  user_view/ Markdown ←→ system_data/ JSON            │          │
│  └──────────────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

#### 典型调用时序（以环节 05：人物设定为例）

```
用户                   执行层                   引擎层                   数据层
 │                     │                       │                      │
 │  _present_plan()    │                       │                      │
 │ ←────────────────── │                       │                      │
 │                     │ 读 step_protocols.yaml │                      │
 │                     │ ──────────────────────→                      │
 │                     │ 返回 display_template  │                      │
 │                     │ ←──────────────────────                      │
 │ 展示执行计划         │                       │                      │
 │ ←────────────────── │                       │                      │
 │                     │                       │                      │
 │ 输入「执行」          │                       │                      │
 │ ──────────────────→ │                       │                      │
 │                     │                       │                      │
 │  _execute_step()    │                       │                      │
 │                     │  _build_context()      │                      │
 │                     │ ──────────────────────→                      │
 │                     │                       │  读 SQLite            │
 │                     │                       │ ── world_building ──→ │
 │                     │                       │ ←── 世界观数据 ────── │
 │                     │ 返回 context           │                      │
 │                     │ ←──────────────────────                      │
 │                     │                       │                      │
 │                     │  Agent 生成 content    │                      │
 │                     │  (LLM 推理)            │                      │
 │                     │                       │                      │
 │                     │  CharacterBuilder     │                      │
 │                     │  .run(context,content)│                      │
 │                     │ ──────────────────────→                      │
 │                     │                       │  validate()           │
 │                     │                       │  写 SQLite characters │
 │                     │                       │ ────────────────────→ │
 │                     │ 返回 ModuleResult      │                      │
 │                     │ ←──────────────────────                      │
 │                     │                       │                      │
 │                     │  QualityOrchestrator  │                      │
 │                     │  .review(context)     │                      │
 │                     │ ──────────────────────→                      │
 │                     │                       │  读 SQLite 验证一致性 │
 │                     │                       │ ────────────────────→ │
 │                     │ 返回 ReviewResult      │                      │
 │                     │ ←──────────────────────                      │
 │                     │                       │                      │
 │                     │  SyncEngine           │                      │
 │                     │  .sync_json_to_md()   │                      │
 │                     │ ──────────────────────→                      │
 │                     │                       │  写 user_view/       │
 │                     │                       │  05_人物/CHAR-XXX.md │
 │                     │                       │ ────────────────────→ │
 │                     │ 返回 SyncReport       │                      │
 │                     │ ←──────────────────────                      │
 │                     │                       │                      │
 │  _wait_for_confirmation()                    │                      │
 │ ←────────────────── │                       │                      │
 │                     │                       │                      │
 │ 输入「确认」          │                       │                      │
 │ ──────────────────→ │  进入环节 06           │                      │
```

---

### 1.7 日志追踪体系

系统使用 `structlog` 实现结构化日志，在关键节点自动记录上下文（小说 ID、步骤、模块）。

#### 1.7.1 日志配置

```python
# src/utils/logger_config.py
import structlog
import logging
import sys
from pathlib import Path
from config import Config

def setup_logging(log_level: str = None):
    """初始化结构化日志系统
    终端输出简洁版，日志文件输出完整版。
    """
    level = (log_level or Config.LOG_LEVEL).upper()
    log_level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
    }
    numeric_level = log_level_map.get(level, logging.INFO)

    # 确保 logs/ 目录存在
    log_path = Path(Config.LOG_PATH)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # 终端处理器：简洁版，仅显示关键字段
    console_processor = structlog.dev.ConsoleRenderer(
        colors=True,
        pad_level=True,
        force_try_number=False,
    )

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S.%f", utc=False),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.dev.ConsoleRenderer()  # 终端输出
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # 文件日志独立配置：完整 JSON，含所有上下文
    file_handler = logging.FileHandler(str(log_path), encoding="utf-8")
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
    ))

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    root_logger.addHandler(file_handler)

    # 创建 structlog 日志器
    logger = structlog.get_logger("workflow")
    logger.info("logging_initialized", log_level=level, log_path=str(log_path))
    return logger
```

#### 1.7.2 日志格式规范

```
终端输出（简洁版）:
  2026-05-29 10:23:45.123 [INFO] [workflow] [novel=NOV-001] [step=03/19] execute_start module=outline_builder

文件输出（完整版 → logs/novel_creation.log）:
  {"event": "execute_start", "timestamp": "2026-05-29 10:23:45.123456", "level": "INFO",
   "logger": "workflow", "novel_id": "NOV-001", "step_number": 3, "step_total": 19,
   "step_name": "拟定大纲", "module": "outline_builder", "dependencies": ["theme"],
   "thread": "MainThread", "process": 12345}
```

#### 1.7.3 关键节点日志注入

以下代码展示 `WorkflowOrchestrator` 中所有关键节点的日志注入点：

```python
# src/workflow/engine.py（关键节点日志注入）
import structlog

class WorkflowOrchestrator:
    def __init__(self, db_session, chroma_client, quality_orchestrator, sync_engine):
        self.logger = structlog.get_logger("workflow")
        # ... 其他初始化 ...

    def run(self, novel_id: str, start_step: int = 1):
        """执行创作流程——带完整日志"""
        self.logger.info("workflow_start", novel_id=novel_id, start_step=start_step)

        novel = self._load_novel(novel_id)
        plan_modifications = None
        step_index = start_step - 1

        while step_index < len(self.STEPS):
            step_number = step_index + 1
            step_name = self.STEPS[step_index][0]
            module_path = self.STEPS[step_index][1]

            # 阶段一入口
            self.logger.info("phase_enter",
                phase="present", novel_id=novel_id,
                step=f"{step_number:02d}/{len(self.STEPS)}",
                step_name=step_name)
            self._present_plan(novel_id, step_number, step_name)

            # 阶段二：用户决策
            self.logger.info("phase_enter",
                phase="decision", step_name=step_name)
            decision = self._wait_for_decision(step_name)
            self.logger.info("user_decision",
                action=decision["action"],
                modifications=decision.get("modifications"))

            if decision["action"] == "skip":
                self._mark_skipped(novel_id, step_number, step_name)
                self.logger.info("step_skipped", step=f"{step_number:02d}/{len(self.STEPS)}")
                step_index += 1
                continue
            elif decision["action"] == "modify":
                plan_modifications = decision.get("modifications", [])
            else:
                plan_modifications = None

            # 阶段三入口
            self.logger.info("phase_enter",
                phase="execute", step_name=step_name,
                has_modifications=plan_modifications is not None)

            # Agent 生成前
             context = self._build_context(novel_id, step_name)
             if plan_modifications:
                 context["user_modifications"] = plan_modifications
             self.logger.info("agent_generate_start",
                 step_name=step_name,
                 dep_count=len(context.get("dependencies", {})))

            content = self._agent_generate(step_name, context)

            # Agent 生成后
            content_length = len(str(content))
            content_summary = str(content)[:100] if content else ""
            self.logger.info("agent_generate_end",
                step_name=step_name,
                content_length=content_length,
                content_summary=content_summary)

            # 模块 run() 调用前
            self.logger.info("module_run_start",
                module_path=module_path,
                content_length=content_length)
            module = self._import_module(module_path)
            result = module.run(context, content)

            # 模块 run() 调用后
            self.logger.info("module_run_end",
                module=module.__class__.__name__,
                result_summary=str(result.summary)[:100] if result.summary else "",
                result_word_count=result.word_count if hasattr(result, "word_count") else 0,
                result_success=result.success)

            # 质量审查前后
            self.logger.info("quality_review_start", step_name=step_name)
            context = self._build_context(novel_id, step_name)
            review = self.quality.review(context)
            self.logger.info("quality_review_end",
                review_level=str(review.level) if hasattr(review, "level") else "unknown",
                review_score=review.score if hasattr(review, "score") else 0,
                issue_count=len(review.details) if hasattr(review, "details") else 0)

            if review.level == "blocker":
                self.logger.warning("quality_blocker",
                    detail=review.details[0] if review.details else "",
                    suggestion=review.suggestions[0] if review.suggestions else "")
                action = self._handle_review_result(review, context)
                if action == "regenerate":
                    continue
                if action == "wait_for_user":
                    print("⏸️ 需要您的决策...")
                    user_cmd = input("请输入命令（重做/忽略）> ")
                    self.logger.info("user_decision_on_review",
                        action=user_cmd, review_action="wait_for_user")
                    if user_cmd == "重做":
                        continue

            # AI 痕迹清除前后
            if step_name in ("正文初稿", "正文修正"):
                self.logger.info("ai_purify_start",
                    text_length=len(result.text) if hasattr(result, "text") else 0)
                purified = self._purify_ai_traces(result.text)
                purified_issues = len(purified) if isinstance(purified, list) else 0
                self.logger.info("ai_purify_end",
                    issues_detected=purified_issues,
                    issues_cleared=purified_issues)

            # 同步引擎调用前后
            self.logger.info("sync_start",
                direction="json_to_md", step_name=step_name)
            sync_report = self.sync.sync_json_to_md(novel_id)
            self.logger.info("sync_end",
                direction="json_to_md",
                files_updated=sync_report.files_updated if hasattr(sync_report, "files_updated") else 0)

            # 阶段四入口
            self.logger.info("phase_enter",
                phase="confirmation", step_name=step_name)
            confirmed = self._wait_for_confirmation(
                novel_id, step_number, step_name, result, review
            )

            # 用户决策结果
            self.logger.info("user_confirmation",
                action="confirmed" if confirmed is True else (
                    "rollback" if isinstance(confirmed, int) else "retry"),
                target_step=confirmed if isinstance(confirmed, int) else None)

            if confirmed is True:
                novel.current_step = step_number
                self._save_novel(novel)
                step_index += 1
            elif isinstance(confirmed, int):
                self._rollback(novel_id, confirmed)
                # 回退日志
                self.logger.warning("rollback_executed",
                    target_step=confirmed,
                    current_step=step_number,
                    deleted_range=f"{confirmed}-{step_number}")
                step_index = confirmed - 1

        self.logger.info("workflow_complete",
            novel_id=novel_id, total_steps=len(self.STEPS))

    def _rollback(self, novel_id: str, target_step: int):
        """回退操作——带日志，级联删除专有表"""
        self.logger.warning("rollback_start",
            target_step=target_step,
            delete_range=f">= {target_step}")
        print(f"  🗑️  回滚：删除环节 {target_step} 之后的数据...")
        self.db.query(StepData).filter(
            StepData.novel_id == novel_id,
            StepData.step_number >= target_step
        ).delete()

        # 级联删除各环节对应的专有表数据
        step_table_map = {
            4: ["world_building", "world_rules"],
            5: ["characters"],
            6: ["relations"],
            7: ["character_arcs"],
            8: ["factions"],
            9: ["faction_relations"],
            10: ["items"],
            11: ["foreshadows"],
            12: ["archives", "synopses"],
            14: ["volumes", "volume_chapters"],
            15: ["detail_outlines"],
            16: ["manuscripts"],
            17: ["review_results", "fix_logs"],
            18: ["review_results", "fix_logs"],
        }
        deleted_tables = []
        for step_num, tables in step_table_map.items():
            if step_num >= target_step:
                for table in tables:
                    self.db.execute(f"DELETE FROM {table} WHERE novel_id = ?", (novel_id,))
                    deleted_tables.append(table)
        self.db.commit()
        self.logger.warning("rollback_complete",
            target_step=target_step,
            deleted_tables=deleted_tables)
        print(f"  ✓ 已回滚到环节 {target_step}（级联删除 {len(deleted_tables)} 张专有表）")
```

#### 1.7.4 异常日志处理

```python
# src/workflow/engine.py（异常处理）
import traceback

class WorkflowOrchestrator:
    def _execute_step(self, novel_id, step_number, step_name, module_path,
                      modifications=None):
        """阶段三：执行——带异常日志"""
        self.logger.info("execute_start",
            module=module_path.split(".")[-1],
            modifications=modifications is not None)
        try:
            context = self._build_context(novel_id, step_name)
            if modifications:
                context["user_modifications"] = modifications

            content = self._agent_generate(step_name, context)
            module = self._import_module(module_path)
            result = module.run(context, content)

            self.logger.info("execute_end",
                module=module_path.split(".")[-1],
                success=result.success if hasattr(result, "success") else True)
            return result
        except Exception as e:
            self.logger.error("execute_exception",
                module=module_path,
                error=str(e),
                traceback=traceback.format_exc())
            raise
```

#### 1.7.5 Config 补充

```python
# config.py 新增字段
class Config:
    # ... 原有配置 ...

    # 日志配置
    LOG_LEVEL = "INFO"              # DEBUG / INFO / WARNING / ERROR
    LOG_PATH = "logs/novel_creation.log"  # 完整日志文件路径
    LOG_CONSOLE_LEVEL = "INFO"      # 终端日志级别（可独立于文件日志）
```

---

## 二、环境与项目结构

### 2.1 所需环境

| 组件 | 版本要求 | 说明 |
|------|---------|------|
| Python | ≥3.10 | 唯一依赖 |
| pip | ≥23.0 | Python 包管理器 |
| 操作系统 | Windows / macOS / Linux | 任意支持 Python 的系统 |

**AI Agent 本身就是 LLM**：Agent（如 Trae、Cursor、Claude Code）内置了完整的语言理解和生成能力。系统运行时，Agent 直接用自己的推理能力来创作小说内容，**不需要**额外配置 `OPENAI_API_KEY`。

**不需要**：Docker、PostgreSQL、Redis、RabbitMQ、Nginx、Kubernetes、外部 API Key

### 2.2 Python 依赖

```txt
# === 数据库 ===
sqlalchemy>=2.0.25          # SQLite ORM

# === 向量搜索 ===
chromadb>=0.4.24             # 本地向量数据库

# === 文本处理 ===
jieba>=0.42.1                # 中文分词（AI 痕迹检测用）
markdown>=3.5.1              # Markdown 渲染
pyyaml>=6.0.1                # YAML 配置
jinja2>=3.1.3                # 模板渲染

# === 工具 ===
structlog>=24.1.0            # 结构化日志
```

### 2.3 项目目录结构

```
novel-creation-system/
│
├── agent_entry.py              # ★ Agent 入口脚本（运行这个文件）
├── config.py                   # 全局配置（Agent 即 LLM，路径等）
├── requirements.txt            # Python 依赖
│
├── src/
│   ├── database/
│   │   ├── engine.py           # SQLite 引擎初始化
│   │   ├── models.py           # SQLAlchemy ORM 模型（56+ 张表）
│   │   └── crud.py             # 通用 CRUD 操作
│   │
│   ├── vector_store/
│   │   ├── chroma_client.py    # ChromaDB 客户端（本地持久化）
│   │   └── embeddings.py       # 嵌入计算
│   │
│   ├── modules/                # 12 个业务模块
│   │   ├── __init__.py
│   │   ├── base_module.py      # BaseModule 基类
│   │   ├── registry.py         # ModuleRegistry 注册表
│   │   ├── theme_engine.py     # 01-02: 灵感 + 主题
│   │   ├── outline_builder.py  # 03: 大纲
│   │   ├── world_builder.py    # 04: 世界观
│   │   ├── character_builder.py# 05: 人物
│   │   ├── relation_builder.py # 06: 人物关系
│   │   ├── arc_builder.py      # 07: 角色弧线
│   │   ├── faction_builder.py  # 08: 势力
│   │   ├── faction_relation.py # 09: 势力关系
│   │   ├── item_builder.py     # 10: 物品库
│   │   ├── foreshadow_manager.py # 11: 伏笔
│   │   ├── archive_builder.py  # 12: 小说档案
│   │   ├── synopsis_builder.py # 13: 小说简介
│   │   ├── volume_config.py    # 14: 分卷配置
│   │   ├── detail_outline.py   # 15: 章节细纲
│   │   ├── manuscript_writer.py # 16: 正文初稿
│   │   ├── export_tool.py      # 19: 导出发布
│   │   │
│   │   └── [注意] 环节17 正文审核 的特殊模块位于 src/quality/review_executor.py
│   │
│   ├── workflow/
│   │   ├── engine.py           # Workflow Orchestrator
│   │   ├── pipeline.py         # 环节编排
│   │   └── nlp_parser.py       # 自然语言反馈解析
│   │
│   ├── quality/
│   │   ├── orchestrator.py     # Quality Orchestrator 调度器
│   │   ├── rule_registry.py    # 质量规则注册表
│   │   ├── review_executor.py  # 审查执行器
│   │   ├── fixers/             # 自动修正器
│   │   │   ├── base_fixer.py
│   │   │   ├── sentence_rhythm_fixer.py
│   │   │   ├── transition_word_fixer.py
│   │   │   └── emotion_showing_fixer.py
│   │   └── report_aggregator.py
│   │
│   ├── ai_purifier/
│   │   ├── detector.py         # 6 大特征检测器
│   │   ├── purifier.py         # 清除执行器
│   │   ├── pipeline.py         # 清除流水线
│   │   └── fixers/
│   │       ├── sentence_rhythm_fixer.py
│   │       ├── transition_word_fixer.py
│   │       ├── emotion_showing_fixer.py
│   │       ├── dialogue_naturalizer.py
│   │       └── description_defaulter.py
│   │
│   ├── sync/
│   │   ├── engine.py           # 同步引擎核心
│   │   ├── json_to_md.py       # JSON → Markdown 渲染
│   │   ├── md_to_json.py       # Markdown → JSON 解析
│   │   └── conflict_resolver.py
│   │
│   └── utils/
│       ├── logger_config.py    # 日志配置
│       └── id_generator.py     # ID 生成器
│
├── config/
│   ├── step_protocols.yaml      # 步骤协议（展示模板/依赖关系）
│   ├── quality_rules.yaml       # 质量规则配置
│   └── ai_trace_thresholds.yaml# AI 痕迹检测阈值
│
├── data/                       # ★ 所有数据文件
│   ├── novel.db                # SQLite 数据库文件
│   └── chromadb/               # ChromaDB 持久化目录
│
├── user_view/                  # ★ 用户可视层 Markdown
│   └── 我的小说_【书名】/
│       ├── 📄 小说概览.md
│       ├── 📁 01_主题/
│       ├── 📁 02_世界观/
│       ├── 📁 03_势力/
│       ├── 📁 04_势力关系/
│       ├── 📁 05_人物/
│       ├── 📁 06_人物关系/
│       ├── 📁 07_角色弧线/
│       ├── 📁 08_物品仓库/
│       ├── 📁 09_伏笔管理/
│       ├── 📁 10_结构/
│       ├── 📁 11_正文/
│       ├── 📁 变更日志/
│       └── 📁 审查报告/
│
├── system_data/                # ★ 系统引擎层 JSON
│   ├── 我的小说_【书名】/
│   │   ├── novel_manifest.json
│   │   ├── modules/
│   │   │   ├── theme/theme.json
│   │   │   ├── world/rules/RULE-001.json
│   │   │   ├── world/rules/RULE-002.json
│   │   │   ├── world/locations/LOC-001.json
│   │   │   ├── factions/FAC-001.json
│   │   │   ├── factions/fac_rel/FAC_REL-001.json
│   │   │   ├── characters/CHAR-001.json
│   │   │   ├── characters/CHAR-002.json
│   │   │   ├── relations/REL-001.json
│   │   │   ├── arcs/ARC-001.json
│   │   │   ├── items/ITEM-001.json
│   │   │   ├── foreshadows/FORE-001.json
│   │   │   └── ...
│   │   ├── structure/
│   │   │   ├── outlines.json
│   │   │   ├── volumes.json
│   │   │   └── detail_outlines.json
│   │   └── manuscript/
│   │       ├── chapter_001.json
│   │       ├── chapter_002.json
│   │       └── ...
│   └── index/                  # 搜索索引
│
├── logs/                       # 日志文件
│   └── novel_creation.log
│
└── tests/                      # 测试
    ├── test_quality.py
    ├── test_purifier.py
    └── test_sync.py
```

### 2.4 配置文件

```python
# config.py
"""
全局配置 — Agent-Native 模式
Agent 本身是 LLM，不需要外部 API Key，不需要启动任何外部服务。
所有数据存储在本地文件系统。
"""

class Config:
    # 数据文件路径（全部本地）
    DATA_DIR = "data"
    SQLITE_PATH = f"{DATA_DIR}/novel.db"
    CHROMADB_PATH = f"{DATA_DIR}/chromadb"
    USER_VIEW_DIR = "user_view"
    SYSTEM_DATA_DIR = "system_data"
    LOG_PATH = "logs/novel_creation.log"

    # 日志配置
    LOG_LEVEL = "INFO"              # 文件日志级别：DEBUG / INFO / WARNING / ERROR
    LOG_CONSOLE_LEVEL = "INFO"      # 终端日志级别（可独立于文件日志）

    # 质量保障配置
    QUALITY_AUTO_FIX_ENABLED = True
    AI_PURIFIER_ENABLED = True
    AI_PURIFIER_AUTO_FIX_LEVELS = [1, 2]

    # 向量搜索配置（用于伏笔相似度检测）
    FORESHADOW_DUPLICATE_THRESHOLD = 0.85
```

---

## 三、agent_entry.py —— Agent 入口脚本

这是整个系统的单一入口点。AI Agent 只需运行 `python agent_entry.py`，系统会自动执行完整创作流程。

```python
#!/usr/bin/env python3
"""
agent_entry.py — AI 小说创作系统 v3.0 入口脚本
AI Agent 直接运行此文件，无需任何其他操作。

用法:
    python agent_entry.py                    # 创建新项目
    python agent_entry.py --novel NOV-001    # 继续已有项目
"""

import sys
import argparse
from pathlib import Path

# 确保 src 目录在 Python 路径中
sys.path.insert(0, str(Path(__file__).parent))

from src.database.engine import init_database
from src.vector_store.chroma_client import init_chromadb
from src.quality.orchestrator import QualityOrchestrator
from src.workflow.engine import WorkflowOrchestrator
from src.sync.engine import SyncEngine
from config import Config


def main():
    parser = argparse.ArgumentParser(description="AI 小说创作系统 v3.0")
    parser.add_argument("--novel", help="已有小说 ID，继续创作")
    parser.add_argument("--step", type=int, help="从指定环节开始")
    parser.add_argument("--resume", action="store_true", help="从上次中断处继续")
    args = parser.parse_args()

    # 1. 初始化本地数据层
    print("📦 初始化数据库...")
    db_session = init_database(Config.SQLITE_PATH)

    print("📦 初始化向量库...")
    chroma_client = init_chromadb(Config.CHROMADB_PATH)

    # 2. 初始化核心引擎
    quality = QualityOrchestrator(db_session)
    quality.load_rules()

    sync_engine = SyncEngine(db_session, Config.USER_VIEW_DIR, Config.SYSTEM_DATA_DIR)

    workflow = WorkflowOrchestrator(
        db_session=db_session,
        chroma_client=chroma_client,
        quality_orchestrator=quality,
        sync_engine=sync_engine,
    )

    # 3. 加载或创建小说项目
    if args.novel:
        novel = workflow.load_novel(args.novel)
        print(f"📖 继续创作: {novel.title} (ID: {novel.id})")
    else:
        print("🎨 欢迎使用 AI 小说创作系统 v3.0！")
        print("请输入小说的灵感或主题（自然语言描述即可）:")
        user_input = input("> ").strip()
        novel = workflow.create_novel(user_input)
        print(f"📖 新项目已创建: {novel.title} (ID: {novel.id})")

    # 4. 执行创作流程
    start_step = args.step or (novel.current_step if args.resume else 1)
    workflow.run(novel.id, start_step=start_step)

    # 5. 完成
    print(f"\n✅ 小说创作完成！")
    print(f"📁 文件位置: {Config.USER_VIEW_DIR}/{novel.title}/")
    print(f"📊 最终审查报告: {Config.USER_VIEW_DIR}/{novel.title}/审查报告/")


if __name__ == "__main__":
    main()
```

### 3.1 Workflow Orchestrator 核心逻辑

> **⚠️ 已废弃：此处为旧版 `run()` 实现（v2.0 迁移残留），无 structlog 日志注入。当前有效版本见 [§1.7.3 日志注入版 run()](#173-流程编排器日志注入版)。**
>
> 两版差异：
> - 旧版（§3.1）：`print()` 驱动，无日志追踪
> - 新版（§1.7.3）：`structlog` 全覆盖，每阶段入口/出口记录，供后续通过 `novel_id + step` 回溯
>
> 以下代码保留仅作参考，**实际以 §1.7.3 为准**。

```python
# src/workflow/engine.py
class WorkflowOrchestrator:
    """
    工作流编排器
    每个环节执行四阶段交互：展示 → 用户决策 → 执行 → 确认
    Agent 不得跳过任何阶段。

    架构说明：
    - Agent（LLM）自己生成内容，模块只做存储和验证
    - 所有模块通过统一的 run(context, content) 接口调用
    - 零外部 LLM 调用，Agent 本身就是 LLM
    """

    STEPS = [
        ("灵感启动",     "modules.theme_engine.ThemeEngine"),
        ("小说主题",     "modules.theme_engine.ThemeEngine"),
        ("拟定大纲",     "modules.outline_builder.OutlineBuilder"),
        ("世界观设定",   "modules.world_builder.WorldBuilder"),
        ("人物设定",     "modules.character_builder.CharacterBuilder"),
        ("人物关系",     "modules.relation_builder.RelationBuilder"),
        ("角色弧线",     "modules.arc_builder.ArcBuilder"),
        ("势力设定",     "modules.faction_builder.FactionBuilder"),
        ("势力关系",     "modules.faction_relation.FactionRelationBuilder"),
        ("物品库",       "modules.item_builder.ItemBuilder"),
        ("伏笔追踪",     "modules.foreshadow_manager.ForeshadowManager"),
        ("小说档案",     "modules.archive_builder.ArchiveBuilder"),
        ("小说简介",     "modules.synopsis_builder.SynopsisBuilder"),
        ("分卷配置",     "modules.volume_config.VolumeConfig"),
        ("章节细纲",     "modules.detail_outline.DetailOutlineBuilder"),
        ("正文初稿",     "modules.manuscript_writer.ManuscriptWriter"),
        ("正文审核",     "quality.review_executor.ReviewExecutor"),
        ("正文修正",     "modules.manuscript_writer.ManuscriptFixer"),
        ("导出发布",     "modules.export_tool.ExportTool"),
    ]

    def run(self, novel_id: str, start_step: int = 1):
        """执行创作流程：每个环节都遵循四阶段交互"""
        novel = self._load_novel(novel_id)
        plan_modifications = None  # Bug 1 fix: 初始化修改指令

        step_index = start_step - 1  # Bug 2 fix: while 循环替代 for
        while step_index < len(self.STEPS):
            step_number = step_index + 1
            step_name = self.STEPS[step_index][0]
            module_path = self.STEPS[step_index][1]

            # === 阶段一：展示（Agent 向用户报告计划） ===
            self._present_plan(novel_id, step_number, step_name)

            # === 阶段二：用户决策（Agent 必须等待指令） ===
            decision = self._wait_for_decision(step_name)
            if decision["action"] == "skip":
                self._mark_skipped(novel_id, step_number, step_name)
                step_index += 1
                continue
            elif decision["action"] == "modify":
                plan_modifications = decision.get("modifications", [])
            else:
                plan_modifications = None

            # === 阶段三：执行 ===
            result = self._execute_step(
                novel_id, step_number, step_name, module_path,
                modifications=plan_modifications
            )

            # 质量审查（执行中的自动步骤）
            context = self._build_context(novel_id, step_name)
            review = self.quality.review(context)
            if review.level == "blocker":
                self._handle_review_result(review, context)
                continue  # 回到当前环节开头

            # AI 痕迹清除（仅正文相关环节）
            if step_name in ("正文初稿", "正文修正"):
                result.text = self._purify_ai_traces(result.text)

            # 同步到用户可视层
            self.sync.sync_json_to_md(novel_id)

            # === 阶段四：确认（Agent 展示结果，用户确认） ===
            confirmed = self._wait_for_confirmation(
                novel_id, step_number, step_name, result, review
            )
            if confirmed is True:
                novel.current_step = step_number
                self._save_novel(novel)
                step_index += 1  # Bug 2 fix: 确认后才前进
            elif isinstance(confirmed, int):
                # Bug 3 fix: 回退到指定环节
                self._rollback(novel_id, confirmed)
                step_index = confirmed - 1
            # confirmed 为 False 时不操作，自然重试当前环节

        print(f"\n{'='*60}")
        print(f"🎉 全部 {len(self.STEPS)} 个环节已完成！")

    def _present_plan(self, novel_id: str, step_number: int, step_name: str):
        """阶段一：展示执行计划"""
        print(f"\n{'='*60}")
        print(f"📝 将开始环节 {step_number:02d}/19: {step_name}")
        print(f"{'='*60}")

        # 加载前置依赖信息
        deps = self._get_dependencies(step_name)
        print(f"\n📋 前置依赖:")
        for dep in deps:
            status = "✓ 已就绪" if self._has_data(novel_id, dep) else "○ 待生成"
            print(f"   {dep}: {status}")

        # 展示已有数据摘要
        existing = self._get_existing_summary(novel_id, step_name)
        if existing:
            print(f"\n📂 已有数据:")
            print(f"   {existing}")
        else:
            print(f"\n📂 未有前置数据，将从零生成")

        # 展示执行计划
        print(f"\n📋 执行计划:")
        print(f"   1. 读取 {', '.join(deps[:3])} 数据")
        print(f"   2. 使用 {self._get_generation_rule(step_name)} 规则生成")
        print(f"   3. 执行质量审查并生成报告")
        print(f"   4. 同步到 user_view/ 可视化目录\n")

    def _wait_for_decision(self, step_name: str) -> dict:
        """阶段二：等待用户决策"""
        print("可用命令:")
        print("  [执行]         按上述计划开始")
        print("  [修改 ...]     调整计划后执行（在 ... 中说明修改内容）")
        print("  [跳过]         跳过此环节")
        print("  [停止]         保存进度并退出")

        while True:
            cmd = input("\n请输入命令 > ").strip()
            if cmd == "执行":
                return {"action": "execute"}
            elif cmd == "跳过":
                print(f"  → 已标记跳过：{step_name}")
                return {"action": "skip"}
            elif cmd == "停止":
                self._save_and_exit()
            elif cmd.startswith("修改"):
                modifications = cmd[2:].strip()
                return {"action": "modify", "modifications": modifications}
            else:
                print("  无法识别，请使用: 执行 / 修改 <内容> / 跳过 / 停止")

    def _execute_step(self, novel_id, step_number, step_name, module_path,
                      modifications=None):
        """阶段三：执行"""
        print(f"\n  ⏳ 正在执行 {step_name}...")

        context = self._build_context(novel_id, step_name)
        if modifications:
            context["user_modifications"] = modifications

        # Agent（LLM）先自己生成内容，再调用模块存储和验证
        print(f"  🤖 Agent 正在生成 {step_name} 内容...")
        content = self._agent_generate(step_name, context)

        # 模块只做存储和验证，不做内容生成
        module = self._import_module(module_path)
        result = module.run(context, content)

        print(f"  ✅ {step_name} 执行完成")
        return result

    def _wait_for_confirmation(self, novel_id, step_number, step_name, result,
                               review):
        """阶段四：展示结果，等待用户确认
        返回值：
          True   → 确认通过，进入下一环节
          False  → 重做当前环节
          int    → 回退到指定环节编号
        """
        print(f"\n{'─'*50}")
        print(f"✅ 环节 {step_number:02d}/19 {step_name} 已完成")
        print(f"{'─'*50}")

        # 结果摘要
        print(f"\n📄 生成内容:")
        print(f"   {result.summary[:200]}..." if len(result.summary) > 200
              else f"   {result.summary}")

        # 质量评分
        print(f"\n📊 质量评分: {review.score:.2f}")
        if review.level == "blocker":
            print(f"   ⛔ BLOCKER: {review.details[0]}")
            print(f"   建议: {review.suggestions[0]}")
        elif review.level == "critical":
            print(f"   ⚠  {review.details[0]}" if review.details else "")
        elif review.level == "warning":
            print(f"   ⚡ {len(review.details)} 个建议")

        # 文件位置
        print(f"\n📁 文件位置: user_view/")

        # 用户确认
        print(f"\n可用命令:")
        print(f"  [确认]         满意，进入下一环节")
        print(f"  [修改 ...]     不满意，按反馈修改后重做")
        print(f"  [重做]         完全重做当前环节")
        print(f"  [回到 <N>]     回退到指定环节 N")
        print(f"  [停止]         保存进度并退出")

        while True:
            cmd = input("\n请输入命令 > ").strip()
            if cmd == "确认":
                print(f"  ✓ 用户已确认，进入下一环节")
                # 在 change_log 中记录确认
                self._log_confirmation(novel_id, step_number, step_name)
                return True
            elif cmd == "重做":
                print(f"  ↻ 重新执行 {step_name}")
                return False
            elif cmd.startswith("修改"):
                modifications = cmd[2:].strip()
                print(f"  ↻ 根据用户反馈修改: {modifications}")
                return False
            elif cmd.startswith("回到"):
                parts = cmd[2:].strip().split()
                target = int(parts[-1])
                print(f"  ↻ 回退到环节 {target:02d}")
                return target  # Bug 3 fix: 返回目标环节编号
            elif cmd == "停止":
                self._save_and_exit()
            else:
                print("  无法识别，请使用: 确认 / 修改 <内容> / 重做 / 回到 <N> / 停止")
```

### 3.2 辅助方法定义

以下方法在 `WorkflowOrchestrator` 中被引用，用于支持四阶段交互流程：

```python
# === 依赖读取 ===

def _get_dependencies(self, step_name: str) -> list[str]:
    """从 step_protocols.yaml 读取当前环节的依赖模块列表"""
    protocol = self.step_protocols.get(step_name, {})
    return protocol.get("dependencies", [])

def _get_generation_rule(self, step_name: str) -> str:
    """从 step_protocols.yaml 读取生成规则描述"""
    protocol = self.step_protocols.get(step_name, {})
    return protocol.get("generation_rule", "")

def _get_existing_summary(self, novel_id: str, step_name: str) -> str | None:
    """返回数据库中已有数据的摘要（用于阶段一展示）"""
    data = self.db.query(StepData).filter_by(
        novel_id=novel_id, step_name=step_name
    ).first()
    if data and data.summary:
        return data.summary
    return None

def _has_data(self, novel_id: str, dep_name: str) -> bool:
    """检查依赖模块是否已有数据"""
    return self.db.query(StepData).filter_by(
        novel_id=novel_id, step_name=dep_name
    ).first() is not None

# === 上下文构建 ===

def _build_context(self, novel_id: str, step_name: str) -> dict:
    """构建传给模块函数的完整 context 字典"""
    context = {
        "novel_id": novel_id,
        "db_session": self.db,
        "chroma_client": self.chroma,
        "dependencies": {},
    }
    # 加载所有依赖数据
    for dep in self._get_dependencies(step_name):
        dep_data = self.db.query(StepData).filter_by(
            novel_id=novel_id, step_name=dep
        ).first()
        if dep_data:
            context["dependencies"][dep] = dep_data.content
    return context

# === 模块动态导入 ===

def _import_module(self, module_path: str) -> BaseModule:
    """动态导入模块类并实例化"""
    import importlib
    parts = module_path.split(".")
    class_name = parts[-1]
    module_name = ".".join(parts[:-1])
    module = importlib.import_module(f"src.{module_name}")
    cls = getattr(module, class_name)
    return cls(self.db, self.chroma)

# === 进度保存 ===

def _save_and_exit(self):
    """保存当前进度并退出"""
    print("  💾 保存进度...")
    self.db.commit()
    print("  👋 已退出，下次运行 --resume 可继续")
    sys.exit(0)

def _load_novel(self, novel_id: str):
    """从数据库加载小说项目"""
    from src.database.models import Novel
    return self.db.query(Novel).filter_by(id=novel_id).first()

def _save_novel(self, novel):
    """保存小说进度"""
    self.db.commit()

# === 日志与确认 ===

def _log_confirmation(self, novel_id: str, step_number: int, step_name: str):
    """在 change_log 中记录用户确认"""
    from datetime import datetime
    entry = {
        "novel_id": novel_id, "step": step_number,
        "name": step_name, "action": "confirmed",
        "timestamp": datetime.now().isoformat(),
    }
    self.db.add(ChangeLog(**entry))
    self.db.commit()

def _mark_skipped(self, novel_id: str, step_number: int, step_name: str):
    """标记环节为已跳过"""
    print(f"  → 已跳过环节 {step_number}: {step_name}")
    self.db.add(StepData(
        novel_id=novel_id, step_number=step_number,
        step_name=step_name, status="skipped"
    ))
    self.db.commit()

# === 回滚 ===

def _rollback(self, novel_id: str, target_step: int):
    """删除目标环节及之后的所有数据"""
    print(f"  🗑️  回滚：删除环节 {target_step} 之后的数据...")
    self.db.query(StepData).filter(
        StepData.novel_id == novel_id,
        StepData.step_number >= target_step
    ).delete()
    self.db.commit()

    # 级联删除各环节对应的专有表数据
    step_table_map = {
        4: ["world_building", "world_rules"],
        5: ["characters"],
        6: ["relations"],
        7: ["character_arcs"],
        8: ["factions"],
        9: ["faction_relations"],
        10: ["items"],
        11: ["foreshadows"],
        12: ["archives", "synopses"],
        14: ["volumes", "volume_chapters"],
        15: ["detail_outlines"],
        16: ["manuscripts"],
        17: ["review_results", "fix_logs"],
        18: ["review_results", "fix_logs"],
    }
    deleted_tables = []
    for step_num, tables in step_table_map.items():
        if step_num >= target_step:
            for table in tables:
                self.db.execute(f"DELETE FROM {table} WHERE novel_id = ?", (novel_id,))
                deleted_tables.append(table)
    self.db.commit()
    print(f"  ✓ 已回滚到环节 {target_step}（级联删除 {len(deleted_tables)} 张专有表）")

def _set_context_modifications(self, mods: str):
    """暂存用户修改指令，供下次执行时使用"""
    self._pending_modifications = mods

def _agent_generate(self, step_name: str, context: dict) -> Any:
    """
    Agent（LLM）自己生成内容。
    此方法由 AI Agent（如 Trae、Cursor）的 LLM 能力实现，
    不是 Python 函数调用。这里仅为展示架构设计。
    """
    raise NotImplementedError(
        "此方法由 Agent 的 LLM 能力实现，无需 Python 实现。"
    )

def _purify_ai_traces(self, text: str) -> str:
    """执行 AI 痕迹清除流水线"""
    return self.purifier.purify(text)
```

---

## 四、19 环节创作流程

> 每个环节对应 `src/modules/` 下的一个 Python 模块。
> Agent（LLM）先自己生成内容，再调用 `module.run(context, content)` 将内容传入模块存储和验证。
> 模块不做内容生成，只做数据持久化和校验。

### 4.1 环节依赖关系

```
环节 01 (灵感)      → 依赖: 用户输入
环节 02 (主题)      → 依赖: 01
环节 03 (大纲)      → 依赖: 02
环节 04 (世界观)    → 依赖: 03
环节 05 (人物)      → 依赖: 04
环节 06 (人物关系)  → 依赖: 04, 05
环节 07 (角色弧线)  → 依赖: 05, 06
环节 08 (势力)      → 依赖: 04
环节 09 (势力关系)  → 依赖: 04, 08
环节 10 (物品库)    → 依赖: 04
环节 11 (伏笔)      → 依赖: 03, 05, 08
环节 12 (档案)      → 依赖: 01-11（聚合）
环节 13 (简介)      → 依赖: 12
环节 14 (分卷)      → 依赖: 03, 05, 08
环节 15 (细纲)      → 依赖: 14, 04, 05, 11
环节 16 (正文初稿)  → 依赖: 15, 04, 05, 08, 11
环节 17 (审核)      → 依赖: 16 → 调用 Quality Orchestrator
环节 18 (修正)      → 依赖: 16, 17
环节 19 (导出)      → 依赖: 01-18（聚合）
```

### 4.2 模块调用接口

每个业务模块实现统一接口。注意：**模块不做内容生成**，只负责存储和验证。
Agent（LLM）自己生成内容后，通过 `content` 参数传入模块。

```python
# src/modules/base_module.py
class BaseModule:
    """所有业务模块的基类"""

    module_name: str  # 模块名称
    depends_on: list[str]  # 依赖的模块名称列表

    def run(self, context: dict, content: Any) -> ModuleResult:
        """
        存储并验证 Agent 已生成的内容。
        
        Agent（LLM）先自己生成内容，再调用此方法传入。
        模块不做生成，只做：
          1. 将 content 写入 SQLite 数据库
          2. 验证数据完整性
          3. 返回存储结果
        
        context: {
            "novel_id": str,
            "db_session": Session,
            "chroma_client": ChromaClient,
            "dependencies": {模块名: 依赖数据},
            "user_modifications": str | None,  # 用户修改指令
        }
        content: Any  # Agent（LLM）自己生成的内容
        """
        raise NotImplementedError

    def validate(self, result: ModuleResult) -> list[str]:
        """
        验证模块输出质量。
        返回问题列表，空列表表示通过。
        """
        return []
```

### 4.3 各环节的模块调用

| 环节 | 模块 | 核心接口 | 前置数据 | 输出 |
|------|------|---------|---------|------|
| 01 | `theme_engine.ThemeEngine` | `run(context, content)` | 用户自然语言输入 | 3 个灵感方向（含创新性评分） |
| 02 | `theme_engine.ThemeEngine` | `run(context, content)` | 灵感输出 | 三层主题结构（表层/深层/情感切入点） |
| 03 | `outline_builder.OutlineBuilder` | `run(context, content)` | 主题 | 三幕大纲 + 因果链 + 节奏热力图 |
| 04 | `world_builder.WorldBuilder` | `run(context, content)` | 大纲 | 8 维度世界观规则集（不少于 15 条） |
| 05 | `character_builder.CharacterBuilder` | `run(context, content)` | 世界观 + 用户 hint | 四层人物档案（身份/心理/能力/特殊） |
| 06 | `relation_builder.RelationBuilder` | `run(context, content)` | 人物 | 关系网络（关系类型/强度/变化轨迹） |
| 07 | `arc_builder.ArcBuilder` | `run(context, content)` | 人物 + 关系 | 角色弧线（起点/转折/终点） |
| 08 | `faction_builder.FactionBuilder` | `run(context, content)` | 世界观 | 势力设定（等级/目标/资源/关系） |
| 09 | `faction_relation.FactionRelationBuilder` | `run(context, content)` | 势力 | 势力关系图谱（联盟/敌对/中立） |
| 10 | `item_builder.ItemBuilder` | `run(context, content)` | 世界观 | 物品库（名称/用途/背景/限制） |
| 11 | `foreshadow_manager.ForeshadowManager` | `run(context, content)` | 大纲+人物+势力 | FORE 档案实体列表（含向量嵌入） |
| 12 | `archive_builder.ArchiveBuilder` | `run(context, content)` | 全部前置 | 聚合档案（含实体参考图 + 变更日志） |
| 13 | `synopsis_builder.SynopsisBuilder` | `run(context, content)` | 档案 | 小说简介（核心冲突/世界观亮点/卖点） |
| 14 | `volume_config.VolumeConfig` | `run(context, content)` | 大纲+人物 | 分卷方案（每卷章节数/视角/节奏） |
| 15 | `detail_outline.DetailOutlineBuilder` | `run(context, content)` | 分卷+全部设定 | 场景级拆解（POV / 字数预算 / 约束） |
| 16 | `manuscript_writer.ManuscriptWriter` | `run(context, content)` | 细纲+全部设定 | 正文初稿（含约束注入） |
| 17 | `review_executor.ReviewExecutor` | `run(context, content)` | 正文初稿 | 四层审查报告 + AI 痕迹检测 |
| 18 | `manuscript_writer.ManuscriptFixer` | `run(context, content)` | 正文+审查报告 | 修正后正文 |
| 19 | `export_tool.ExportTool` | `run(context, content)` | 全部数据 | 完整小说文件（Markdown + TXT） |

### 4.4 引擎层模块详细设计（统一模板）

每个模块遵循以下模板：
1. **职责**：一句话
2. **输入结构**：context 字典必需字段 + content 参数结构
3. **输出结构**：ModuleResult(success, summary, data, word_count, errors)
4. **存储逻辑**：写入 SQLite 哪些表、什么格式
5. **验证规则**：validate() 至少 3 条，含阈值
6. **依赖数据**：具体读取哪个表的哪个字段
7. **Agent 约束**：该环节生成时必须遵循的结构化规则

---

#### 4.4.1 ThemeEngine（环节 01-02：灵感启动 + 小说主题）

```python
# src/modules/theme_engine.py
class ThemeEngine(BaseModule):
    """灵感 + 主题模块"""
    module_name = "theme_engine"
    depends_on = []

    def run(self, context: dict, content: dict) -> ModuleResult:
        ...

    def validate(self, result: ModuleResult) -> list[str]:
        ...
```

**职责**：基于用户输入的灵感描述，生成结构化灵感方向 / 三层主题结构

**输入结构**：
| 步骤 | context 字段 | content 字段 |
|------|-------------|-------------|
| 01 灵感 | novel_id, db_session | `directions: [{id, title, concept, innovation_score(0-1), summary, emotional_potential(0-1)}]` — 必须恰好3个 |
| 02 主题 | + dependencies.theme.inspiration_selected | `{surface_theme: str, deep_theme: str, emotional_hook: str, theme_statement: str, reverse_confirmation: str}` |

**输出结构**：`ModuleResult(success=True, summary=str, data={...}, word_count=0, errors=[])`

**存储逻辑**：
- 灵感：写入 `inspirations` 表（novel_id, direction_id, title, concept, innovation_score, summary, emotional_potential, created_at）
- 主题：写入 `themes` 表（novel_id, surface_theme, deep_theme, emotional_hook, theme_statement, reverse_confirmation）

**验证规则**：
1. 灵感方向必须正好 3 个
2. 每个方向的 innovation_score 必须在 0.0-1.0 之间
3. 主题三层的文本长度均 ≥ 10 字
4. surface_theme ≠ deep_theme（表层与深层不得相同）

**依赖数据**：环节 02 依赖环节 01 `inspirations` 表的 `direction_id`

**Agent 约束**：
- 灵感必须差异化：三个方向分别覆盖情节驱动、角色驱动、设定驱动三种类型
- 情感切入点必须具象化到具体场景，不写抽象概念
- 反向确认必须质疑主题的潜在漏洞
- 灵感生成时禁止从"类型"出发（如"写一个修仙小说"），必须从用户提供的情感问题出发，仅用类型作为承载容器
- 主题生成后自动执行偏执测试：在三个方向上朝极端推进一步（"在哪个方向上让读者更不安？"），输出三个极端版本供用户反观主题深度
- 读者心理三层自动分析：补偿心理（表层吸引力）/镜像心理（情感困境可共鸣）/答案心理（故事留在读者心里），缺任何一层则标记为"读者心理不完整"
- 主题层面AI痕迹自检：生成的主题必须通过以下四类症状检测——① 核心冲突配方化（是否遵循高度可预测的冲突模板？）；② 情感落点中产化（是否所有结局都落在"安全、健康、主流价值观认可"范围内？）；③ 世界观零件拼装感（是否只是把热门类型拼在一起，缺乏"必须为这个主角存在"的内在必然性？）；④ 表达无锐度（是否面面俱到完整，但没有一个让人感到"被冒犯/被击中/被看穿"的锐利瞬间）。任一症状阳性则标记为"主题存在AI痕迹"，要求重做
- 用户实操指令集：当用户发现主题层面问题时可使用的指令模板——
  - "这个主题太安全了——对核心情感做偏执测试，朝三个方向各极端化一步，让读者更不安"
  - "主题设定新鲜但情感空洞——为核心人物写情感简历，不写身份和能力，只写他醒来时的第一个念头、他对谁撒谎最频繁"
  - "主题的核心情感困境在当代读者生活中的对应场景是什么？不要用概括词，给我三个具体场景"
  - "假设作者用多年没走出来的情感困境选择了这个故事——基于这个假设修改主题"

---

#### 4.4.2 OutlineBuilder（环节 03：拟定大纲）

```python
# src/modules/outline_builder.py
class OutlineBuilder(BaseModule):
    module_name = "outline_builder"
    depends_on = ["theme_engine"]
```

**职责**：生成三幕结构大纲，含因果链标注和节奏热力图

**输入结构**：`context["dependencies"]["theme"] = {surface_theme, deep_theme, emotional_hook}`
`content = {acts: [{act, name, chapters, summary, key_events}×3], causal_chain: [{from_event, to_event, cause_type}], rhythm_map: [{chapter_range, tension(0-1), pace(slow/medium/fast)}]}`

**输出结构**：`ModuleResult(success=True, summary=str, data={acts, causal_chain, rhythm_map}, word_count=0, errors=[])`

**存储逻辑**：写入 `outlines` 表（JSON 字段：acts/causal_chain/rhythm_map），关联 novel_id

**验证规则**：
1. 必须恰好三幕（acts 长度 = 3）
2. 必须有因果链（causal_chain 非空）
3. 总章节数 10-200
4. 第二幕章节数 > 第一幕章节数
5. 每个 key_event 必须在因果链中出现至少一次
6. cause_type 必须是枚举值之一

**依赖数据**：`themes` 表的 surface_theme、deep_theme、emotional_hook、theme_statement

**Agent 约束**：
- 第一幕（setup）章节数占总章节 20-30%
- 第二幕（confrontation）占 40-50%
- 第三幕（resolution）占 20-30%
- 节奏曲线必须有至少 3 次 tension 峰值变化
- causal_chain 中必须有至少一条跨幕因果链

---

#### 4.4.3 WorldBuilder（环节 04：世界观设定）

```python
# src/modules/world_builder.py
class WorldBuilder(BaseModule):
    module_name = "world_builder"
    depends_on = ["theme_engine", "outline_builder"]
```

**职责**：基于大纲生成 8 维度的世界观规则集，每维度 ≥ 2 条

**输入结构**：`context["dependencies"]["outline"]` 中的大纲 acts/summary
`content = {dimensions: [{name, rules: [{id, description, scope, constraints, conflicts_with}]}]}`

8 维度：物理规则 / 地理空间 / 时间历史 / 社会结构 / 文化习俗 / 科技水平 / 魔法/超自然体系 / 经济体系

**输出结构**：`ModuleResult(success=True, summary=str, data={dimensions: [...]}, word_count=0, errors=[])`

**存储逻辑**：
- 写入 `world_building` 表（novel_id, dimension_name, rules JSON）
- 每条 rule 单独写入 `world_rules` 表（rule_id, dimension, description, scope, constraints）

**验证规则**：
1. 必须包含全部 8 个维度
2. 每维度至少 2 条规则
3. 总规则数 ≥ 16
4. 跨维度规则间不得有 _未声明_ 的冲突（所有冲突必须在 `conflicts_with` 中声明）

**依赖数据**：`outlines` 表的 acts JSON 中的 summary 和 setting_requirements（如有）

**Agent 约束**：
- 每条规则必须有明确的 scope（适用范围）
- 冲突规则必须双向声明（A 声明冲突 B，B 也必须声明冲突 A）
- 至少包含 2 条"硬规则"（不可违反）和 2 条"软规则"（可破例）

---

#### 4.4.4 CharacterBuilder（环节 05：人物设定）

```python
# src/modules/character_builder.py
class CharacterBuilder(BaseModule):
    module_name = "character_builder"
    depends_on = ["world_builder"]
```

**职责**：生成四层人物档案，含情感身体词典/语气指纹/感知过滤器/知识边界/权重评分/破绽档案

**输入结构**：`context["dependencies"]["world_building"]` 世界观规则
`content = {characters: [{id, name, role, layer1_identity: {name, age, gender, occupation, background, appearance, personality_traits}, layer2_psychology: {motivation, fear, desire, flaw, growth_direction, emotional_vocabulary: [动作反应词表], body_language_dictionary: {emotion: [身体反应链]}}, layer3_ability: {skills, knowledge_boundaries: {knows: [str], not_knows: [str], misunderstands: [{subject, misconception, truth}]}, tone_fingerprint: {speech_pattern, vocabulary_preferences, rhythm, taboo_expressions: [str], filler_words: [{word, frequency}]}, inner_voice_profile: {sentence_style, digression_tendency(self_interrupt/associative), typical_openings: [str]}}, layer4_special: {secrets: [{content, reveal_chapter}], quirks: [{detail, contradicts_trait}], habits: [str], triggers: [{situation, reaction}], perception_filter: {notices: [str], ignores: [str], misinterprets: [{situation, wrong_conclusion}]}, cracks: [{surface_detail, underlying_contradiction}]}, weight: {arc_contribution(0-10), plot_driving(0-10), theme_carrying(0-10), network_centrality(0-10), weighted_score, tier(protagonist/core_support/major_support/functional/background)}]}]`

**输出结构**：`ModuleResult(success=True, summary=str, data={characters: [...]}, word_count=0, errors=[])`

**存储逻辑**：
- 写入 `characters` 表（novel_id, char_id, name, role, layer1_json, layer2_json, layer3_json, layer4_json, weight_tier, weight_score, weight_json）
- 每个角色一条记录，各层分别存储在独立 JSON 字段
- 权重字段（weight_tier/weight_score/weight_json）单独列存

**验证规则**：
1. 至少包含 3 个角色（1 主角 + 2 配角）
2. 每个角色必须包含全部四层数据
3. layer3.knowledge_boundaries.not_knows 至少 2 项（该角色不知道的事）
4. layer2.body_language_dictionary 至少覆盖 5 种情感（高兴/愤怒/悲伤/恐惧/惊讶），每种情感至少 2 个身体反应
5. 主角必须有 layer4.secrets（秘密）
6. 主角必须有 layer4.cracks（破绽，至少 2 个与主要性格不自洽的细节）
7. 权重计算：weighted_score = arc_contribution×0.35 + plot_driving×0.30 + theme_carrying×0.20 + network_centrality×0.15

**依赖数据**：`world_building` 表的 world_rules（确保角色能力不违反世界观规则）

**Agent 约束**：
- 必须包含情感身体词典（角色高兴/愤怒/悲伤时的具体身体反应，而非抽象描述），禁止使用通用情感标签（"感到愤怒"→必须替换为角色特有的身体反应）
- 语气指纹必须与角色身份一致（农夫不用书生词汇）
- 感知过滤器决定该角色在叙述中会注意到什么、忽略什么
- 破绽（cracks）必须与角色主要性格不自洽（如极度严谨的人手机屏幕碎了三个月不修）
- inner_voice_profile（内心独白特征）决定该角色内心独白的"脏感"——必须包含跑题倾向、自我打断频率
- 群像文权重模型：检测是否为群像文（没有任何角色在四维度上同时大幅领先其他角色），如是则按群像文分配权重（25-40%每人，总权重可超过100%因重叠），非群像文则主角占45-60%
- 群像文类型识别：中心型群像（共享核心事件/地点/主题）vs 平行型群像（独立旅程交汇），不同类型有不同的弧线错峰策略
- 弧线错峰检测：核心配角（非群像文）或所有主角级角色（群像文）的弧线节点（催化/变化/终点）不得与主角（或彼此）在同一章节窗口内撞车。自动检测并标记冲突区间
- 独立叙事功能评分：每个核心配角必须计算 independence_score（0-10），分析"如果主角不存在，该角色是否还有自己的完整故事"。低于5/10的核心配角标记为"危险—戏份多的功能配角"，需要重新设计或增加独立维度
- 配角独立性检测：统计每个配角的场景中"与主角同框或直接受主角驱动"的比例。如果占比 100%（无独立场景），标记并建议安排至少 1 个"主角不在场"场景
- 配角功能重叠检测：检测是否有多个配角在叙事功能上重叠（如"两个盟友"），对功能重叠的配角要求各自至少有一个独立叙事维度
- TODO: 实时权重面板生成函数——在章节细纲生成时按当前章节输出 POV 分配建议和平衡检查

---

#### 4.4.5 RelationBuilder（环节 06：人物关系）

```python
# src/modules/relation_builder.py
class RelationBuilder(BaseModule):
    module_name = "relation_builder"
    depends_on = ["world_builder", "character_builder"]
```

**职责**：建立角色间关系网络，含类型枚举、强度评分和变化轨迹

**输入结构**：`context["dependencies"]["characters"]` 人物列表
`content = {relations: [{id, char_a_id, char_b_id, type(enum), strength(0-1), asymmetry(0-1), history: [{phase, description, change_event}], trajectory: [{chapter_range, strength, description}]}]}`

关系类型枚举：`family / romance / friendship / rivalry / mentorship / enmity / alliance / master_servant / neutral`

**输出结构**：`ModuleResult(success=True, summary=str, data={relations: [...]}, word_count=0, errors=[])`

**存储逻辑**：
- 写入 `relations` 表（novel_id, relation_id, char_a_id, char_b_id, type, strength, asymmetry, history JSON, trajectory JSON）
- 每条双向关系存一条记录（A-B 和 B-A 视为同一条）

**验证规则**：
1. 所有 relation 中的 char_a_id、char_b_id 必须在 characters 表中存在
2. 每个主角至少与 2 个其他角色有关系
3. strength 必须在 0-1 之间
4. 敌对关系必须双向 strength > 0.6

**依赖数据**：`characters` 表的 char_id、name、role

**Agent 约束**：
- asymmetry（非对称性）表示双方感受差异（0=完全对称，1=单方面）
- 单向暗恋：asymmetry > 0.8
- 轨迹中必须标注关系转折点（从敌到友等）
- **他人眼中的碎片化折射**：每条关系记录必须在 actual_layer 中包含"A 眼中的 B"和"B 眼中的 A"两个视角——同一个人在不同人眼中可能是完全不同的版本（如 B 眼中 A 温暖不可靠，C 眼中 A 冷酷）。正文生成时，通过某角色视角观察另一角色时，自动加载观察者的情感滤镜而非被观察者的完整档案

---

#### 4.4.6 ArcBuilder（环节 07：角色弧线）

```python
# src/modules/arc_builder.py
class ArcBuilder(BaseModule):
    module_name = "arc_builder"
    depends_on = ["character_builder", "relation_builder"]
```

**职责**：定义主要角色的成长弧线，含起点/催化/变化/终点 + 章节映射

**输入结构**：`context["dependencies"]["characters"]` + `dependencies["relations"]`
`content = {arcs: [{char_id, arc_type(positive/negative/flat), start_state, catalyst_event, change_process: [{phase, chapter_range, description}], end_state, chapter_mapping: [{chapter, arc_stage, state_snapshot}]}]}`

**输出结构**：`ModuleResult(success=True, summary=str, data={arcs: [...]}, word_count=0, errors=[])`

**存储逻辑**：
- 写入 `character_arcs` 表（novel_id, char_id, arc_type, start_state, catalyst_event, change_process JSON, end_state, chapter_mapping JSON）

**验证规则**：
1. 主角必须有一条完整弧线（4 阶段完整）
2. start_state ≠ end_state（角色必须有变化）
3. change_process 至少 2 个 phase
4. catalyst_event 必须在 outlines 表的 key_events 中出现

**依赖数据**：`characters` 表的 char_id、layer2_psychology；`outlines` 表的 acts.key_events

**Agent 约束**：
- positive arc：角色变得更好；negative arc：角色堕落；flat arc：角色改变世界
- 催化事件必须与角色核心恐惧/欲望相关
- 终点状态必须与起点形成对比

---

#### 4.4.7 FactionBuilder（环节 08：势力设定）

```python
# src/modules/faction_builder.py
class FactionBuilder(BaseModule):
    module_name = "faction_builder"
    depends_on = ["world_builder"]
```

**职责**：生成小说中的势力，含等级/目标/资源/成员

**输入结构**：`context["dependencies"]["world_building"]` 社会结构维度
`content = {factions: [{id, name, type(government/corporation/cult/military/guild/family), hierarchy: [{level, name, privileges, responsibilities}], goals: [{priority, description, deadline_chapter}], resources: [{type, amount, description}], members: [{char_id, role, rank}], doctrines: [str], reputation(0-1)}]}`

**输出结构**：`ModuleResult(success=True, summary=str, data={factions: [...]}, word_count=0, errors=[])`

**存储逻辑**：
- 写入 `factions` 表（novel_id, faction_id, name, type, hierarchy JSON, goals JSON, resources JSON, doctrines, reputation）
- 成员关联通过 `faction_members` 表（faction_id, char_id, role, rank）

**验证规则**：
1. 至少生成 2 个势力
2. 每个势力至少 2 个层级
3. 每个势力至少 1 个明确目标
4. 成员 char_id 必须在 characters 表中存在

**依赖数据**：`world_building` 表的社会结构维度规则

**Agent 约束**：
- 势力目标必须与大纲中的关键事件相关
- 同类型势力不得有完全相同的目标
- 势力声誉值 0-1 影响其他势力的初始态度

---

#### 4.4.8 FactionRelationBuilder（环节 09：势力关系）

```python
# src/modules/faction_relation.py
class FactionRelationBuilder(BaseModule):
    module_name = "faction_relation"
    depends_on = ["world_builder", "faction_builder"]
```

**职责**：定义势力间关系（联盟/敌对/中立）及关系演变

**输入结构**：`context["dependencies"]["factions"]` 势力列表
`content = {relations: [{id, faction_a_id, faction_b_id, type(alliance/hostile/neutral/subordinate/puppet), strength(0-1), history: [{phase, event, impact}], treaties: [{name, terms, status}], hidden_agenda: str}]}`

**输出结构**：`ModuleResult(success=True, summary=str, data={relations: [...]}, word_count=0, errors=[])`

**存储逻辑**：
- 写入 `faction_relations` 表（novel_id, relation_id, faction_a_id, faction_b_id, type, strength, history JSON, treaties JSON, hidden_agenda）

**验证规则**：
1. 所有 faction_id 必须在 factions 表中存在
2. strength 0-1 并与 type 语义一致（alliance 的 strength > 0.5）
3. 每个势力至少与 1 个其他势力有关系
4. hostile 类型必须双方 strength > 0.5

**依赖数据**：`factions` 表的 faction_id、type、goals、reputation

**Agent 约束**：
- 敌对关系必须有明确原因（资源冲突/历史仇恨/意识形态对立）
- 联盟关系可以有 hidden_agenda（隐藏目的）
- puppet（傀儡）关系必须标注实际控制方

---

#### 4.4.9 ItemBuilder（环节 10：物品库）

```python
# src/modules/item_builder.py
class ItemBuilder(BaseModule):
    module_name = "item_builder"
    depends_on = ["world_builder"]
```

**职责**：生成小说中的特殊物品清单

**输入结构**：`context["dependencies"]["world_building"]` 世界观规则
`content = {items: [{id, name, type(weapon/artifact/magic_item/technology/key_item/daily_item), purpose, background_story, restrictions: [{condition, consequence}], current_owner(char_id|faction_id), significance_to_plot, first_appearance_chapter}]}`

**输出结构**：`ModuleResult(success=True, summary=str, data={items: [...]}, word_count=0, errors=[])`

**存储逻辑**：
- 写入 `items` 表（novel_id, item_id, name, type, purpose, background_story, restrictions JSON, current_owner, significance_to_plot, first_appearance_chapter）

**验证规则**：
1. 至少生成 3 件物品
2. 每件物品必须有限制条件（restrictions 非空）
3. 每件物品必须关联到大纲中的一个关键事件
4. current_owner 必须引用 characters 或 factions 表中的 ID

**依赖数据**：`world_building` 表的规则集；`outlines` 表的 key_events

**Agent 约束**：
- 限制条件必须包含"使用代价"或"使用条件"
- 关键剧情物品必须有背景故事
- 物品能力不得违反世界观规则

---

#### 4.4.10 ForeshadowManager（环节 11：伏笔追踪）

```python
# src/modules/foreshadow_manager.py
class ForeshadowManager(BaseModule):
    module_name = "foreshadow_manager"
    depends_on = ["outline_builder", "character_builder", "faction_builder"]
```

**职责**：管理伏笔全生命周期（注册/埋设/回收/废弃），维护伏笔密度曲线，去重检测

**输入结构**：`context["dependencies"]["outline"]` + `dependencies["characters"]` + `dependencies["factions"]`
`content = {foreshadows: [{id, type(信息伏笔/人物伏笔/物品伏笔/能力伏笔/关系伏笔/规则伏笔/情感伏笔/结构伏笔), status(待埋设/已埋设/待回收/已回收/已废弃), plant_chapter, plant_location(场景/段落), plant_form(对话/环境/动作/内心独白/旁白), reveal_chapter_planned, reveal_chapter_actual, reveal_form(情节转折/对话揭示/闪回/物品使用/角色变化), payload(真正要传达的内容), surface(表层呈现), depth(浅层/中层/深层), related_char: [char_id], related_item: [item_id], related_plot: [event_id], parent_fore(嵌套上级伏笔), child_fores(嵌套下级伏笔), tags: [str], importance(0-1)}]}`

**输出结构**：`ModuleResult(success=True, summary=str, data={foreshadows: [...], density_curve: [{chapter, active_count, density, new_count, resolved_count}], active_list: [{chapter_range, foreshadow_id, urgency}], word_count=0, errors=[], chroma_ids=[...])`

**存储逻辑**：
- 写入 `foreshadows` 表（novel_id, foreshadow_id, type, status, plant_chapter, plant_location, plant_form, reveal_chapter_planned, reveal_chapter_actual, reveal_form, payload TEXT, surface TEXT, depth, related_char JSON, related_item JSON, related_plot JSON, parent_fore, child_fores JSON, tags JSON, importance, chroma_id, created_at, last_modified）
- 写入 `foreshadow_density_snapshots` 表（novel_id, chapter, active_count, density_per_kword, new_count, resolved_count）
- 同步写入 ChromaDB：每个伏笔作为一条向量记录（collection="foreshadows"），嵌入 payload + surface，存储完整 metadata

**验证规则**：
1. ChromaDB 中去重检测：新伏笔与已有伏笔的余弦相似度 < 0.85；若 surface 相似度 > 0.85，提示"疑似重复埋设"并展示已有伏笔详情供用户判断
2. target_chapter 必须在 outlines 表的章节范围内
3. importance(0-1)，其中 > 0.7 的主伏笔必须有 reveal_plan
4. 至少包含 3 种不同类型的伏笔
5. 伏笔密度计算：密度 = 当前活跃伏笔数 / 章节长度（千字）；密度 > 5.0/千字时标记为"过密"警告
6. 状态流转校验：已埋设→只能进入待回收/已废弃；已回收→不可重复回收；已废弃→保留档案但不再参与活跃度计算
7. 逾期预警：计划回收章节超过 5 章仍未回收时自动生成遗忘预警

**依赖数据**：`outlines` 表的 acts JSON（章节范围）；`characters` 表 char_id；`factions` 表 faction_id

**Agent 约束**：
- 主伏笔（importance > 0.7）必须提前至少 3 章埋设
- 伏笔的 hint_text（暗示文本）不得直接暴露真相
- reveal_plan 描述伏笔回收时的具体揭晓方式
- 已经存在的相似伏笔（cosine > 0.85）应合并而非重复创建
- 每章写作前自动输出活跃伏笔清单（按紧迫度分组：本回收窗口内/中期待回收/远期待回收）
- 伏笔密度控制规则：密度 0-1.5/千字→可埋新；1.5-3.0/千字→优先回收；3.0-5.0/千字→暂停埋新；5.0+/千字→警告
- 嵌套伏笔的 parent_fore 和 child_fores 必须在同一篇小说内，不支持跨小说引用
- **surface 与 payload 的分离原则**：surface 是读者第一眼看到的内容（工具性描述），payload 是回收时才理解的真正含义（情感性揭示）。两者必须在语义上有"表层 vs 真相"的错位空间，禁止 surface 直接等同 payload
- **depth 分类的跨距约束**：浅层伏笔必须在本卷内回收（1-10 章），中层需在读者快要忘记时回收（10-30 章），深层可全书跨度（30 章以上）。depth 与 reveal_chapter_planned 的差值必须匹配该层级的跨距规则
- **密度曲线可视化输出**：在伏笔档案中自动生成"伏笔密度-章节"ASCII 图表（每 5 章为一区间，标注活跃伏笔数、密度等级、新埋设数、已回收数），供用户在任何时候查看

---

#### 4.4.11 ArchiveBuilder（环节 12：小说档案）

```python
# src/modules/archive_builder.py
class ArchiveBuilder(BaseModule):
    module_name = "archive_builder"
    depends_on = [全部前置模块]
```

**职责**：聚合全部已有数据，生成小说结构的聚合档案（三层结构：身份卡+核心摘要+模块快照）

**输入结构**：`context["dependencies"]` 全部前置模块数据
`content = {archive: {layer1_identity_card: {title, subtitle, genre, target_audience, total_words_estimate(动态调整), current_progress(已完成/总计划), current_word_count, creation_status(设定阶段/大纲阶段/初稿阶段/修改阶段/已定稿), version}, layer2_core_summary: {one_sentence_summary(从主线冲突提取), one_paragraph_blurb(从三幕结构提取), theme_statement, current_core_conflict(从当前章节提取活跃冲突线), protagonist_current_state(从CHAR-001弧线拉取), key_character_count, faction_landscape_summary(从FAC_REL提取), active_foreshadow_count}, layer3_module_snapshots: {world_rules_summary, character_list: [{id, name, faction, arc_stage}], faction_list: [{id, name, game_status}], item_list: [{id, name, holder, function}], outline_structure: {volumes, chapters, completion_status}, foreshadow_stats: {by_status, count}, recent_changes: [{timestamp, step, description}]}}}`

**输出结构**：`ModuleResult(success=True, summary=str, data={archive: {...}}, word_count=0, errors=[])`

**存储逻辑**：
- 写入 `archives` 表（novel_id, layer1_identity_card JSON, layer2_core_summary JSON, layer3_module_snapshots JSON, updated_at）
- archive 不存储重复数据，只存储引用摘要和聚合统计
- 每次修改其他模块时自动触发 archive 对应字段刷新（由 WorkflowOrchestrator 在每环节确认后触发 sync）

**验证规则**：
1. 必须引用 characters 表中所有角色
2. 必须引用 factions 表中所有势力
3. structure_summary 的 total_chapters 必须与 outlines 一致
4. change_log 必须包含最近 5 次变更
5. 阶段性准入检查：在各阶段切换时（设定→大纲→大纲→初稿→初稿→修改）自动执行，任一前置模块不完整则阻止切换

**依赖数据**：`novels`、`themes`、`world_building`、`characters`、`factions`、`faction_relations`、`items`、`relations`、`character_arcs`、`foreshadows`、`outlines` 等全部前置表

**Agent 约束**：
- layer1 只存储元数据（不存储内容，从 novels 表实时拉取）
- layer2 所有字段不是用户手动填写的，而是 AI 从各模块当前状态实时提取
- layer3 只存储摘要（name + 一句话描述）+ 统计数字，不重复存储全量数据
- 阶段性准入检查输出格式（示例）：
  ```
  === 阶段准入检查：设定阶段 → 大纲阶段 ===
  ✅ 世界观规则：已完成（8条规则，五层审查通过）
  ✅ 人物设定：已完成（6个主要人物）
  ❌ 势力设定：未完成（需要至少3个势力）
  准入失败：请先完成全部前置模块。
  ```
- 变更日志格式：每行一条 JSON 记录写入 `change_log.jsonl`，格式为 `{"timestamp", "novel_id", "step", "module", "action"(create/update/delete/rollback), "entity_id", "entity_type", "summary", "changed_fields": [str]}`
- 版本快照机制：在每个创作阶段切换时自动创建全局快照（备份所有模块当前数据到 `system_data/snapshots/{timestamp}/`目录），用户可通过"回退到阶段 X 快照"恢复指定时间点的全局状态
- 检索接口定义：中央档案库支持两种检索方式——① 字段级精确查询 `search(entity_type="CHAR", field="faction_id", value="FAC-003")` 返回实体 ID 列表；② 语义检索 `semantic_search(collection="characters", query="以其人之道还治其人之身的角色", top_k=5)` 通过 ChromaDB 向量相似度返回匹配实体

---

#### 4.4.12 SynopsisBuilder（环节 13：小说简介）

```python
# src/modules/synopsis_builder.py
class SynopsisBuilder(BaseModule):
    module_name = "synopsis_builder"
    depends_on = ["archive_builder"]
```

**职责**：基于小说档案生成四套对外发布的简介版本，并维护简介实时更新

**输入结构**：`context["dependencies"]["archive"]`
`content = {synopsis: {one_liner: {text(30-50字), structure: [异常情境+情感赌注]}, short_blurb: {text(150-250字), structure: [世界异常点→主角困境→冲突升级→情感钩子]}, standard_blurb: {text(300-500字), structure: [世界观引入→主角深度→核心冲突展开→情感赌注→开放式钩子]}, long_blurb: {text(800-1500字), structure: [完整前提→人物弧线预告→主题暗示→不透底]}, core_conflict: str, world_highlight: str, selling_points: [{dimension(plot/character/world), text}], target_audience: str, tone_tags: [str], comparison_titles: [str], hook_question: str}}`

**输出结构**：`ModuleResult(success=True, summary=str, data={synopsis: {...}}, word_count=计算字数, errors=[])`

**存储逻辑**：
- 写入 `synopses` 表（novel_id, one_liner TEXT, short_blurb TEXT, standard_blurb TEXT, long_blurb TEXT, core_conflict, world_highlight, selling_points JSON, target_audience, tone_tags JSON, comparison_titles JSON, hook_question, word_count, last_synced_at, stale_status(up_to_date/needs_update/outdated)）
- 不存储独立副本，每个版本的生成逻辑指向对应的数据源映射

**验证规则**：
1. one_liner 长度 30-50 字
2. short_blurb 长度 150-250 字
3. standard_blurb 长度 300-500 字
4. long_blurb 长度 800-1500 字
5. selling_points 至少 3 个，分别对应情节/角色/世界观三维度
6. comparison_titles 必须与已有作品不同（不得与原作完全相同）
7. 简介过期检测：大纲主线结构性变化/主角核心欲望改变/世界观核心规则修改/写作进度超过简介覆盖范围时，自动标记 stale_status=needs_update

**依赖数据**：`archives` 表的 layer1/layer2/layer3；`world_building` 表最具叙事张力的规则；`characters` 表核心欲望+恐惧+弧线起点

**Agent 约束**：
- one_liner 结构 = `[异常情境] + [情感赌注]`，仅制造好奇不解释
- short_blurb 四段式（各1-2句）：世界异常点→主角困境→冲突升级→情感钩子
- standard_blurb 五段式：世界观引入→主角深度→核心冲突→情感赌注→钩子
- hook_question 必须引发好奇心（不展示答案）
- comparison_titles 使用"XX meets YY"格式

**简介生成数据源映射**（每个段落指向特定数据源，数据源变化时自动触发重新生成）：
- one_liner → 来源：theme_statement + CHAR-001 核心矛盾 + 世界观最吸引人的异常点
- short_blurb 第1段（世界异常点）→ 来源：世界观最具叙事张力的 1-2 条规则
- short_blurb 第2段（主角困境）→ 来源：CHAR-001 核心欲望 + 核心恐惧 + 弧线起点状态
- short_blurb 第3段（冲突升级）→ 来源：大纲催化事件 + 中点转折的核心冲突
- standard_blurb 第2段（主角深度）→ 来源：CHAR-001 情感身体词典 + 感知过滤器 + 破绽（用于生成有质感的描写而非标签式介绍）
- standard_blurb 第4段（情感赌注）→ 来源：characters 表 cost_list + 弧线终点状态（读者需要知道角色可能失去什么、可能变成什么）

**小说档案输出三格式**（ArchiveBuilder 阶段输出时提供三种粒度）：
- 完整版：三层全部输出（身份卡 + 核心内容摘要 + 各模块快照）
- 摘要版：仅输出身份卡 + 核心内容摘要（适合阶段性回顾和团队同步）
- 投稿版：仅输出适合发给出版方的信息（不包括伏笔和未揭示设定，避免泄底）
---

#### 4.4.13 VolumeConfig（环节 14：分卷配置）

```python
# src/modules/volume_config.py
class VolumeConfig(BaseModule):
    module_name = "volume_config"
    depends_on = ["outline_builder", "character_builder"]
```

**职责**：基于弧线节点扫描自动识别分卷边界，配置每卷的视角/节奏/卷名

**输入结构**：`context["dependencies"]["outline"]` + `dependencies["characters"]` + `dependencies["arcs"]`
`content = {volumes: [{id, name(卷名), chapter_range, boundary_gravity: [{source(arc/conflict/catharsis), chapter, weight}], chapters: [{chapter_number, pov_character, summary, word_count_budget}], pacing(slow/medium/fast), major_conflict, character_focus: [char_id], themes: [str], cliffhanger, volume_rhythm_curve: [{chapter, tension, emotion_type}], volume_rhythm_evaluation: str}]}`

**输出结构**：`ModuleResult(success=True, summary=str, data={volumes: [...], boundary_candidates: [{chapter, gravity_source, weight}], rhythm_reports: [{volume_id, evaluation}]}, word_count=0, errors=[])`

**存储逻辑**：
- 写入 `volumes` 表（novel_id, volume_id, name, chapter_range, boundary_gravity JSON, pacing, major_conflict, character_focus JSON, themes JSON, cliffhanger, volume_rhythm_curve JSON, volume_rhythm_evaluation）
- 写入 `volume_chapters` 表（volume_id, chapter_number, pov_character, summary, word_count_budget）

**验证规则**：
1. 各卷 chapter_number 合计必须等于 outlines 的总章节数
2. 每卷至少 3 章
3. 每章必须指定 pov_character（从 characters 表中选择）
4. 每卷必须有 cliffhanger（卷末悬念）
5. 分卷边界必须与弧线节点（催化/变化至少其一）或冲突线收束点重合，禁止以章节整数为分割依据
6. 卷内节奏评价：卷内连续低谷不超过 2 章、卷内高峰位置合理（不在卷首）、结尾有自然回落或钩子

**依赖数据**：`outlines` 表的 acts JSON；`characters` 表的 char_id、name；`character_arcs` 表的 node_catalyst、node_change、chapter_mapping（弧线节点扫描用）

**Agent 约束**：
- 每卷的 POV 角色不超过 3 个，避免视角混乱
- 分卷边界必须是自然的故事转折点（弧线节点或冲突收束点），不是整数章
- 各卷字数预算应与节奏匹配（紧张卷短、舒缓卷长）
- 卷名生成：从本卷核心冲突 + 主角弧线阶段 + 核心意象中提取关键词，生成至少 3 个候选卷名
- 分卷边界的自动识别流程（不可跳过）：弧线扫描→重力点计算（催化/变化最高）→冲突线收束验证→综合输出分卷方案

---

#### 4.4.14 DetailOutlineBuilder（环节 15：章节细纲）

```python
# src/modules/detail_outline.py
class DetailOutlineBuilder(BaseModule):
    module_name = "detail_outline"
    depends_on = ["volume_config", "world_builder", "character_builder", "foreshadow_manager"]
```

**职责**：拉取全部约束后生成场景级细纲，含人物状态/关系状态/知识边界/物品/伏笔/主题/节奏约束

**输入结构**：`context["dependencies"]` 含 volumes、world_building、characters、foreshadows、relations、arcs、items
`content = {chapters: [{chapter, chapter_constraint_summary: {character_states: [{char_id, arc_stage, physical_status, emotional_status, knowledge_boundary_chapter_snapshot}], relation_states: [{rel_id, current_stage, info_asymmetry}], item_states: [{item_id, status, holder}], foreshadow_actions: [{foreshadow_id, action(plant/reveal/touch)}], theme_progression: {theme_aspect, advance_through, forbidden_approach}, rhythm: {opening_intensity, emotional_curve: [scene_emotion], paragraph_pacing, ending(悬空/回落/爆发)}}, scenes: [{id, pov_char_id, location(世界观点名), time(时间段), conflict_type(inner/outer/social/philosophical), word_count_budget, foreshadow_refs: [foreshadow_id], purpose_in_chapter, summary, emotional_arc: {start_emotion, end_emotion, turning_point}}]}]}`

**输出结构**：`ModuleResult(success=True, summary=str, data={chapters: [...]}, word_count=sum(scenes.word_count_budget), errors=[])`

**存储逻辑**：
- 写入 `detail_outlines` 表（novel_id, chapter_number, chapter_constraint_summary JSON, scenes JSON）
- 每章一条记录，scenes 为场景数组 JSON，约束摘要为一个独立字段

**验证规则**：
1. 每章至少 2 个场景
2. 每个场景的 pov_char_id 必须在 characters 表中
3. 每个场景的 location 必须在 world_building 的维度中存在
4. foreshadow_refs 必须引用 foreshadows 表中已注册的伏笔
5. 每章字数预算总和 ≥ 2000
6. 场景 emotional_arc.start_emotion ≠ end_emotion（情感必须有变化）
7. character_states.knowledge_boundary_chapter_snapshot 与 characters 表的 knowledge_boundaries 一致

**依赖数据**：`volumes` 表、`volume_chapters` 表；`world_building` 表的地理空间维度；`characters` 表（含 status_timeline、knowledge_boundaries）；`relations` 表（change_curve）；`foreshadows` 表；`items` 表（status_timeline）

**Agent 约束**：
- 场景 emotional_arc 必须有变化（起始情感 ≠ 结束情感），且变化必须与 chapter_constraint_summary.rhythm.emotional_curve 一致
- 同一章节内的连续场景不得使用同一 POV
- 伏笔引用必须是该场景中实际出现（埋伏或回收）的伏笔
- 冲突类型分布：正文中 inner + social 至少占 40%
- 约束生成顺序不可逆：必须先拉取全部约束（人物/关系/物品/伏笔/主题/节奏），再在约束内设计场景
- knowledge_boundary_chapter_snapshot 必须精确到章节级——该角色在第 N 章知道什么、不知道什么、以为什么是真其实不是

---

#### 4.4.15 ManuscriptWriter（环节 16：正文初稿）

```python
# src/modules/manuscript_writer.py
class ManuscriptWriter(BaseModule):
    module_name = "manuscript_writer"
    depends_on = ["detail_outline", "world_builder", "character_builder", "faction_builder", "foreshadow_manager"]
```

**职责**：读入全部约束数据，逐场景生成正文，执行场景间过渡微调和字数统计

**输入结构**：`context["dependencies"]` 全部前序模块数据
`content = {chapters: [{chapter_number, title, compiled_constraint_file: {scene_bound: [{scene_id, scene_specific_constraints}], character_level_constraints: [{char_id, physical_effect_required, knowledge_boundary_enforce, tone_fingerprint_enforce, emotion_show_via_body_required}], item_usage_constraints: [{item_id, allowed_appearances, forbidden_use}], foreshadow_execution: [{foreshadow_id, action, natural_embedding_rule}], theme_execution: [{theme_aspect, advance_via_concrete_choice, forbidden_method}], rhythm_execution: {opening_force, emotional_path: [scene_emotion_target], paragraph_rhythm: [{scene_id, sentence_length_range}]}, word_count_budget: {total, per_scene: [{scene_id, min, max}]}}, scenes: [{scene_id, pov_char_id, text, word_count}]}]}`

**输出结构**：`ModuleResult(success=True, summary=str, data={chapters: [...], transition_fixes: [{from_scene, to_scene, fix_text, word_count}]}, word_count=sum(chapters.word_count), errors=[])`

**存储逻辑**：
- 写入 `manuscripts` 表（novel_id, chapter_number, title, compiled_constraint_file JSON, scenes JSON, word_count, transition_fixes JSON, status(draft/reviewed/fixed)）
- 每章一条记录，约束文件和场景正文同表存储，确保生成时始终可回溯约束

**验证规则**：
1. 每章字数 ≥ detail_outlines 中该章的 word_count_budget 的 80%
2. 每章字数 ≤ detail_outlines 中 word_count_budget 的 120%
3. 场景数必须与 detail_outlines 一致
4. 每个场景的 POV 必须与细纲一致
5. 正文中出现的 foreshadow_refs 必须全部注册过
6. character_level_constraints 中的情感展示必须通过身体反应呈现（禁止"感到""觉得"等标签）——每章检测，违者标记为 issue
7. 场景间过渡段落字数 50-150 字，不超过总字数 5%
8. 字数漂移补救机制：若某场景实际字数超过预算的 120%，自动触发"相邻场景预算调配"——缩减同章内其他场景的预算（缩减比例不超过 30%），确保全章总字数在 ±20% 范围内；若全章总字数仍超出 120%，标记为 WARNING 并建议用户决定是否拆分到下一章

**依赖数据**：`detail_outlines`（场景结构+约束摘要）；`characters`（情感身体词典/语气指纹/感知过滤器/知识边界）；`world_building`（环境描写）；`factions`（势力互动）；`foreshadows`（伏笔插入）；`items`（物品状态）

**Agent 约束**：
- 场景正文必须以符合该 POV 角色的感知过滤器来叙述（角色注意到什么、忽略什么，不是作者在描述客观场景）
- 正文中不得出现情感标签（"感到愤怒""心中充满恐惧"），必须使用情感身体词典中的具体身体反应
- 对话必须符合角色的语气指纹（词汇池/句式偏好/禁忌表达）和身份背景
- 伏笔暗示必须以自然方式嵌入（角色行为/环境细节/对话潜台词），不做标签式插入
- 逐场景生成流程不可跳过：拉取约束→输出场景约束摘要→用户确认→生成场景正文→字数统计→审核通过→下一场景
- 场景间过渡微调清单（拼合时自动执行）：时间连续性/视角切换锚点/情感曲线的连贯性

**事件描写技法三要则**（关键事件场景强制使用）：
- 要则一·注意力的非理性分配：在高冲突场景（打斗/对峙/灾难/情感爆发）中，角色的注意力不得按"叙事重要性"均匀分配。必须在高潮处插入至少 1 个"无关"的感官细节——角色注意到对方袖口少了一颗扣子、闻到走廊里的消毒水味、发现自己手指上沾了一小块墨水——这些细节不服务于情节推进，而是服务于真实感。禁止写"角色全神贯注"式的均匀注意力分配。
- 要则二·时间感的扭曲：每个重要事件场景必须确定"主观时间流速"——恐惧加速时间、痛苦拉长时间、沉浸让时间消失。追捕场景时间必须快（动作无缝衔接，无内心停顿）；坠落/创伤场景时间必须拉长（半秒内大脑跑出多年闪回）；喝茶聊天的时间感不得与生死搏斗相同。禁止所有场景使用统一的时间节奏。
- 要则三·事件的残影：关键事件结束后，角色的身体必须携带事件的残影进入后续场景——不是通过闪回叙事，而是通过身体记忆：手还在轻微发抖、嗓子因未说出的话而干哑、某个关键词触发下意识的停顿。相邻关键事件之间必须有"身体的连续性"，禁止叙事切换后角色身体完全重置。

---

#### 4.4.16 ReviewExecutor（环节 17：正文审核）

```python
# src/quality/review_executor.py
# [注意] 此模块不在 src/modules/ 下，位于 src/quality/ 目录
class ReviewExecutor(BaseModule):
    module_name = "review_executor"
    depends_on = ["manuscript_writer"]
```

**职责**：对正文执行四层审查（设定一致性/逻辑完整性/文学质感/AI 痕迹检测），输出审查报告

**输入结构**：`context["dependencies"]["manuscripts"]` 正文数据
`content = {review: {manuscript_chapter_numbers: [int], focus_areas: [str]}}`
或直接使用 context 中的依赖数据自动审查

**输出结构**：`ModuleResult(success=True, summary=str, data={review_result: {...}}, word_count=0, errors=[])`

`review_result` 包含：
- `layer1_setting_consistency`: {passed, issues: [{chapter, position, rule_violated, suggestion}]}
- `layer2_logic_completeness`: {passed, issues: [{type, description}]}
- `layer3_literary_quality`: {score(0-1), issues: [{type(节奏/对话/描写/情感), severity, suggestion}]}
- `layer4_ai_trace_detection`: {score(0-1), issues: [{trait_type, severity, fix_level, detail}]}
- `overall_score`: float, `summary`: str, `suggestions`: [str]

**存储逻辑**：
- 写入 `review_results` 表（novel_id, chapter_number, layer1_json, layer2_json, layer3_json, layer4_json, overall_score, summary, suggestions JSON, created_at）
- 每章一条审查记录

**验证规则**：
1. 必须执行全部四层审查
2. layer1 发现 blocker 必须阻断（不阻断视为审查失败）
3. layer4 AI 痕迹评分 < 0.6 时必须标记为 CRITICAL
4. overall_score 必须在 0-1 之间

**依赖数据**：`manuscripts` 表的正文 scenes；`world_building` 表规则集；`characters` 表情感词典

**Agent 约束**：
- 审查器不做内容修改，只输出审查报告
- 每个 issue 必须标注精确位置（章节+段落）
- blocker 级别问题必须提供修改建议

---

#### 4.4.17 ManuscriptFixer（环节 18：正文修正）

```python
# src/modules/manuscript_writer.py（与 ManuscriptWriter 同一文件）
class ManuscriptFixer(BaseModule):
    module_name = "manuscript_fixer"
    depends_on = ["manuscript_writer", "review_executor"]
```

**职责**：基于审查报告修正正文问题

**输入结构**：`context["dependencies"]["manuscripts"]` + `dependencies["review_results"]`
`content = {fixes: [{chapter_number, scene_id, issue_ref, original_text, fixed_text, fix_type(setting/logic/literary/ai_trace)}], chapters: [{chapter_number, title, scenes: [{scene_id, text, word_count}]}]}`

**输出结构**：`ModuleResult(success=True, summary=str, data={chapters: [...]}, word_count=sum, errors=[])`

**存储逻辑**：
- 更新 `manuscripts` 表对应章节的 scenes JSON 和 status="fixed"
- 写入 `fix_logs` 表（novel_id, chapter_number, fix_type, issue_ref, original_summary, fixed_summary, timestamp）

**验证规则**：
1. blocker 级别的 issue 必须全部修复
2. critical 级别至少修复 80%
3. 修正后字数变化不得超过原章节字数的 ±10%

**依赖数据**：`manuscripts` 表；`review_results` 表的各层 issues

**Agent 约束**：
- 必须逐条对应 issue 做修复，不得遗漏
- 修复后文本应与原正文风格一致，不得引入新问题
- 修正完成后自动触发 AI 痕迹清除流水线

---

#### 4.4.18 ExportTool（环节 19：导出发布）

```python
# src/modules/export_tool.py
class ExportTool(BaseModule):
    module_name = "export_tool"
    depends_on = [全部前置模块]
```

**职责**：聚合全部创作数据，导出为完整的 Markdown 和 TXT 文件

**输入结构**：`context["dependencies"]` 全部前置模块数据
`content = {export: {formats: ["markdown", "txt"], include_review_report: bool, include_foreshadow_map: bool}}`

**输出结构**：`ModuleResult(success=True, summary=str, data={exported_files: [{format, path, word_count}]}, word_count=total_word_count, errors=[])`

**存储逻辑**：
- 不写 SQLite（只读）
- 写文件系统：
  - `user_view/我的小说_【书名】/📖 完整小说.md`：全部正文按章拼接
  - `user_view/我的小说_【书名】/📖 完整小说.txt`：纯文本版本
  - `user_view/我的小说_【书名】/导出配置.json`：导出元数据

**验证规则**：
1. 必须包含全部已完成的章节（跳过状态的不包含）
2. Markdown 版本必须包含完整的目录树链接
3. TXT 版本必须纯文本无格式标记
4. 文件编码必须为 UTF-8

**依赖数据**：`novels` 表（标题/作者）；`manuscripts` 表（正文）；`themes`、`world_building`、`characters` 等（附录数据）

**Agent 约束**：
- Markdown 输出顺序：书名 → 作者 → 简介 → 目录 → 正文（按章）→ 附录（设定/人物/势力/伏笔图）
- 每章开头标注章号+标题+字数
- TXT 版本每章用 `======== 第X章 ========` 分隔

---

## 五、质量保障体系

> v3.0 保留了 v2.0 中 Quality Orchestrator 的核心逻辑，但去掉了消息队列依赖。
> Agent 在每个环节完成后直接调用 `QualityOrchestrator.review()`，同步获取审查结果。

### 5.1 Quality Orchestrator

```python
# src/quality/orchestrator.py
class QualityOrchestrator:
    """
    质量总控调度器
    Agent 在每个环节完成后直接调用此方法：
        quality.review(novel_id, step_name, result)
    """

    def __init__(self, db_session):
        self.db_session = db_session
        self.rule_registry = QualityRuleRegistry()
        self.review_executors: dict[str, ReviewExecutor] = {}
        self.fixers: dict[str, Fixer] = {}

    def load_rules(self):
        """加载所有质量规则"""
        # 注册默认规则
        self.rule_registry.register_from_file("config/quality_rules.yaml")

    def review(self, context: ReviewContext) -> ReviewResult:
        """
        执行完整审查链。
        参数 context 包含:
        - novel_id, step_name, content
        - dependencies (前置数据，供一致性检查用)
        """
        # 1. 获取该环节适用的审查规则
        rules = self.rule_registry.get_rules_for_context(context)

        # 2. 按优先级排序并执行
        results = []
        for rule in sorted(rules, key=lambda r: r.priority):
            executor = self.review_executors.get(rule.executor_id)
            if not executor:
                continue
            result = executor.execute(context.content, context.dependencies)
            results.append(result)

            # BLOCKER 级别立即返回
            if result.level == ReviewLevel.BLOCKER:
                return self._aggregate(results, blocked=True)

        # 3. 聚合结果
        return self._aggregate(results)

    def _aggregate(self, results: list, blocked=False) -> ReviewResult:
        """聚合多个审查结果"""
        levels = [r.level for r in results]
        if blocked or ReviewLevel.BLOCKER in levels:
            final_level = ReviewLevel.BLOCKER
        elif ReviewLevel.CRITICAL in levels:
            final_level = ReviewLevel.CRITICAL
        elif ReviewLevel.WARNING in levels:
            final_level = ReviewLevel.WARNING
        else:
            final_level = ReviewLevel.INFO

        return ReviewResult(
            level=final_level,
            score=sum(r.score for r in results) / len(results),
            details=[d for r in results for d in r.details],
            suggestions=[s for r in results for s in r.suggestions],
            auto_fixes=[f for r in results for f in r.auto_fixes],
        )
```

### 5.2 审查结果分级处理

```python
# 统一审查结果处理器（合并 _handle_blocker 和 _handle_review_result）
def _handle_review_result(self, result: ReviewResult, context: ReviewContext):
    """统一审查结果处理器
    返回值：
      "regenerate"   → 重做当前环节
      "continue"     → 继续后续流程
      "wait_for_user" → 等待用户决策后继续
    """
    if result.level == ReviewLevel.BLOCKER:
        print(f"\n  ⛔ BLOCKER: {result.details[0] if result.details else '严重问题'}")
        print(f"  建议: {result.suggestions[0] if result.suggestions else '无'}")
        print(f"\n可用命令:")
        print(f"  [重做]         重新执行当前环节")
        print(f"  [修改 ...]     提供修改方向后重做")
        print(f"  [忽略]         忽略此问题（不推荐）")
        while True:
            cmd = input("\n请输入命令 > ").strip()
            if cmd == "重做":
                context.constraints = result.suggestions
                return "regenerate"
            elif cmd.startswith("修改"):
                context.constraints = result.suggestions
                context.user_modifications = cmd[2:].strip()
                return "regenerate"
            elif cmd == "忽略":
                print(f"  ⚠ 用户选择忽略 BLOCKER，风险自担")
                return "continue"
            else:
                print("  无法识别，请使用: 重做 / 修改 <内容> / 忽略")

    elif result.level == ReviewLevel.CRITICAL:
        print(f"  ⚠  CRITICAL: 发现问题，尝试自动修正...")
        if result.auto_fixes:
            for fix in result.auto_fixes:
                fixer = self.quality.fixers.get(fix.fixer_id)
                if fixer:
                    context.content = fixer.fix(context.content, fix.params)
                    print(f"     ✓ {fix.description}")
            return self._handle_review_result(
                self.quality.review(context), context
            )
        else:
            print(f"  ⏸️  需要用户确认: {result.details[0]}")
            return "wait_for_user"

    elif result.level == ReviewLevel.WARNING:
        print(f"  ⚡ WARNING: {len(result.details)} 个建议")
        for s in result.suggestions:
            print(f"    建议: {s}")
        return "continue"

    else:
        print(f"  ✓ 审查通过（评分: {result.score:.2f}）")
        return "continue"
```

### 5.3 预注册的质量规则清单

| 规则名称 | 所属模块 | 触发场景 | 审查级别 | 优先级 |
|---------|---------|---------|---------|--------|
| 设定一致性 | 世界观模块 | 正文生成后、设定变更后 | BLOCKER | 1 |
| 逻辑链完整性 | 大纲模块 | 大纲生成后、正文生成后 | BLOCKER | 1 |
| 文学质感 | 正文模块 | 正文生成后 | CRITICAL | 2 |
| AI 痕迹检测 | AI Purifier | 正文生成后、修正后 | CRITICAL | 2 |
| 读者吸引力 | 正文模块 | 正文审核阶段 | WARNING | 3 |
| 世界观五层审查 | 世界观模块 | 世界观生成后、实体新增后 | BLOCKER | 1 |
| 大纲质量审查 | 大纲模块 | 大纲生成后 | BLOCKER | 1 |
| 伏笔完整性 | 伏笔模块 | 章节生成后 | CRITICAL | 2 |
| 字数校验 | 正文模块 | 正文生成后 | WARNING | 3 |
| 跨章节一致性 | 同步引擎 | 每章正文生成后 | CRITICAL | 2 |

### 5.4 质量规则配置（增强版）

**第二层约束：quality_rules.yaml**
| 属性 | 说明 | 读取者 | 读取时机 |
|------|------|--------|---------|
| `check_algorithm` | 检测算法的伪代码描述 | QualityOrchestrator.review() | 阶段三末尾 |
| `auto_fix` | 是否支持自动修复（true/false） | QualityOrchestrator | 自动修正阶段 |

```yaml
# config/quality_rules.yaml（增强版）
# 作用：定义质量审查的规则、检测算法和自动修复策略
# 读取者：QualityOrchestrator.review()
# 读取时机：阶段三执行末尾

quality_rules:
  setting_consistency:
    display_name: "设定一致性"
    applies_to: [manuscript, fix_manuscript]
    level: blocker
    priority: 1
    check_algorithm: |
      1. 提取正文所有世界观实体引用（地点/规则/势力/物品）
      2. 对照 world_building 数据逐一验证
      3. 提取所有角色能力/行为，对照 characters 表验证
      4. 冲突时标记位置 + 违反规则编号 + 冲突类型
      5. 统计冲突总数，>0 时标记为 BLOCKER
    auto_fix: false
    description: "确保正文中的设定描述与世界构建数据一致"

  logic_chain_integrity:
    display_name: "逻辑链完整性"
    applies_to: [outline, manuscript]
    level: blocker
    priority: 1
    check_algorithm: |
      1. 提取因果链中所有 from_event → to_event 映射
      2. 检查每个 to_event 是否至少有一个 from_event 前置
      3. 检查是否有孤立事件（无因/无果）
      4. 检查跨幕因果链比率（至少 1 条跨幕）
      5. 孤立事件 > 0 时标记为 BLOCKER
    auto_fix: false
    description: "确保大纲因果链完整，无孤立事件"

  foreshadow_integrity:
    display_name: "伏笔完整性"
    applies_to: [detail_outline, manuscript]
    level: critical
    priority: 2
    check_algorithm: |
      1. 提取细纲/正文中所有 foreshadow_refs
      2. 对照 foreshadows 表验证所有 ref 已注册
      3. 检查主伏笔（importance > 0.7）是否已埋设
      4. 检查已回收伏笔是否在 target_chapter 范围内
      5. 未注册 ref > 0 时标记为 CRITICAL
    auto_fix: false
    description: "确保正文中的伏笔引用有效且主伏笔齐全"

  literary_quality:
    display_name: "文学质感"
    applies_to: [manuscript]
    level: critical
    priority: 2
    check_algorithm: |
      1. 计算句式波动系数（std/mean），阈值 0.3
      2. 计算过渡词密度（次/千字），阈值 15
      3. 检测情感标签出现次数（"感到""觉得"等），阈值 3
      4. 检测信息密集型对话占比，阈值 70%
      5. 检测常见描写模板命中数，阈值 2
      6. 每项未达标 +1 issue，≥3 项时标记为 CRITICAL
    auto_fix: true
    fix_strategy: "调用 AITracePurifier L1 自动修复器处理句式/过渡词/描写模板问题"
    description: "检测 AI 写作的常见文学质量问题"

  ai_trace_detection:
    display_name: "AI 痕迹检测"
    applies_to: [manuscript, fix_manuscript]
    level: critical
    priority: 2
    check_algorithm: |
      1. 调用 AITraceDetector.detect() 执行 6 大特征检测
      2. 按 fix_level 分组（L1 自动/L2 半自动/L3 仅报告）
      3. 若存在 L1 以外的问题 → CRITICAL
      4. 所有问题均为 L1 → WARNING
      5. 无问题 → INFO
    auto_fix: true
    fix_strategy: "L1 自动执行修复器链，L2 生成 3 种方案供用户选择"
    description: "检测 6 大 AI 痕迹特征并分级处理"

  chapter_consistency:
    display_name: "跨章节一致性"
    applies_to: [manuscript, fix_manuscript]
    level: critical
    priority: 2
    check_algorithm: |
      1. 提取所有章节的角色出场记录
      2. 检查角色状态是否与前一章一致（受伤/死亡等）
      3. 检查时间线是否连续（无跳跃/回溯）
      4. 检查物品所有权是否连续
      5. 状态不一致 > 0 时标记为 CRITICAL
    auto_fix: false
    description: "确保各章节间角色/时间/物品状态一致"

  world_building_five_layers:
    display_name: "世界观五层审查"
    applies_to: [world_building]
    level: blocker
    priority: 1
    check_algorithm: |
      1. [主题适配审查] 逐条规则追问：是否拷问/放大/具体化主角的核心情感冲突？
         强关联：规则直接作用于主角情感困境
         中关联：规则间接影响主角外部环境
         弱关联：标记为"设定赘肉"，提供改造方案使其与主题关联
      2. [规则自洽性审查] 三步流程：
         Step 1 规则原子化：每条规则拆解为不可再分的逻辑命题
         Step 2 规则交叉推演：所有原子规则两两配对，检测隐性冲突
         Step 3 裂缝决策清单：每条裂缝标注"涉及规则/冲突描述/叙事潜力/AI建议(填补/保留/开发)"
      3. [结构完整性审查] 逐维度深度评级：
         不及格：仅基础描述，故事中用到时需临时编
         及格：有尺度感和分层
         良好：自动产生冲突的结构性力量
      4. [极端场景测试] 自动生成5-8个极端测试用例：
         资源枯竭测试/规则对冲测试/规则滥用测试
         致命级→必须修补/潜在级→可选修补/理论级→可忽略/叙事潜力点→写入设定
      5. [叙事压力审查] 规则分类：
         压力产生规则：天然让某些人受益/受损，自动产生结构性矛盾
         纹理规则：不产生人际张力
         标记"叙事潜力未被激活"的规则并提供激活建议
    auto_fix: true
    fix_strategy: "主题适配→弱关联规则改造方案；规则自洽→裂缝填补方案；结构完整→深度加深方案；极端测试→致命级修补+叙事潜力点利用"
    description: "主题适配/规则自洽/结构完整/极端测试/叙事压力五层完整审查"

  world_building_review_report:
    display_name: "世界观审查报告用户交互框架"
    applies_to: [world_building]
    level: info
    priority: 9
    check_algorithm: |
      五层审查完成后，自动输出结构化审查报告供用户逐层确认：
      【报告结构】
      一、主题适配摘要（半页）
      - 哪些规则和主题强关联（不需关注）
      - 哪些规则弱关联——AI建议删除/保留/改造？已自动执行的改造方案
      二、规则裂缝清单（1-2页）
      - 每条裂缝的位置、性质、AI建议（填补/保留/开发）
      - 用户逐条确认：哪些填补、哪些保留为叙事潜力、哪些神秘化
      三、结构完整性评级（半页）
      - 每个维度的深度评级（不及格/及格/良好）
      - 不及格维度——AI已自动生成加深方案
      四、极端测试结果（1页）
      - 致命级→必须修补/潜在级→可选修补/理论级→可忽略/叙事潜力点→写入势力设定
      五、叙事压力激活（半页）
      - 压力产生规则中哪些叙事潜力未激活→建议在大纲中插入对应冲突节点
      【用户交互方式】
      - 每条决策项展示时同步展示"可用命令"：接受/驳回/修改为...
      - 用户确认全部决策项后，审查结果一次性写入
    auto_fix: false
    description: "世界观五层审查的结构化输出框架与用户逐层确认交互流程"

  cross_module_linkage:
    display_name: "跨模块联动更新"
    applies_to: [world_building, characters, factions, items, foreshadows, outline]
    level: critical
    priority: 2
    check_algorithm: |
      触发条件：修改任一实体核心字段/新增实体/删除实体/移动大纲关键事件
      1. [正向追踪] 该实体引用了什么？→ 引用目标变化时检查本实体是否受影响
      2. [反向追踪] 谁引用了该实体？→ 列出所有引用者逐项检查
      3. [涟漪扩散] 受影响者的受影响者→ 递归追踪至不再产生新影响
      输出《联动更新报告》：触发操作/直接影响/需要确认的连锁影响/建议方案
    auto_fix: false
    description: "修改一处设定后自动追踪正向/反向/涟漪影响范围并生成报告"

  cross_module_validation_checklist:
    display_name: "跨模块交叉验证清单"
    applies_to: [world_building, characters, factions, items, foreshadows, outline, detail_outline]
    level: critical
    priority: 2
    check_algorithm: |
      在每次跨模块联动更新完成后，自动执行以下结构性交叉验证：
      1. [人物-势力] 所有 faction_members 中的 char_id 必须对应存在的 CHAR，且该 CHAR 的 faction_id 与成员表一致
      2. [人物-弧线] 所有 ARC 的 char_id 必须对应存在的 CHAR
      3. [人物-关系] 所有 REL 的 char_a/char_b 必须对应存在的 CHAR
      4. [势力-关系] 所有 FAC_REL 的 fac_a/fac_b 必须对应存在的 FAC
      5. [物品-持有者] ITEM holder_timeline 中的 char_id 必须对应存在的 CHAR
      6. [物品-规则] ITEM related_rules 必须对应存在的 RULE
      7. [伏笔-人物/物品/事件] FORE related_char/related_item/related_plot 必须对应存在的实体
      8. [章节细纲-大纲] detail_outlines 中的 chapter_number 必须在 outlines 的章节范围内
      9. [章节细纲-伏笔] 每章 foreshadow_refs 中所有 FORE 的 status 必须为"已埋设"或"待埋设"
      10. [正文-细纲] manuscripts 中的 scenes 数组长度必须与对应 detail_outlines 一致
      任意一项检测失败则标记为 CRITICAL，并生成具体的不一致报告
    auto_fix: false
    description: "十项结构性交叉验证，确保实体间引用关系的完整性和一致性"

  outline_quality:
    display_name: "大纲质量审查"
    applies_to: [outline]
    level: blocker
    priority: 1
    check_algorithm: |
      1. 检查三幕结构完整性（3 幕齐全）
      2. 检查章节数分配比例（20-30%/40-50%/20-30%）
      3. 检查因果链非空
      4. 检查节奏热力图至少 3 个 tension 峰值
      5. 比例偏差 > 10% 时标记为 BLOCKER
    auto_fix: false
    description: "审查三幕结构、章节分配和因果链完整性"

  outline_rhythm_quality:
    display_name: "大纲节奏质量"
    applies_to: [outline]
    level: critical
    priority: 1
    check_algorithm: |
      1. [冲突强度量化] 为每章标注冲突强度值（1-10），检测异常模式：
         A. 连续低谷：连续3章以上冲突强度<3 → 标记，建议插入次级冲突
         B. 连续高峰：连续5章以上冲突强度>8 → 标记，建议插入冷却点
         C. 峰值递减：全篇最高值出现在中段而非结尾 → 标记，建议调整
         D. 起点过高：第1章冲突强度>6 → 标记，建议前移情感建立
      2. [情绪类型交替] 为每章标注主导情绪类型，检测连续4章以上同类型 → 标记失衡区间
      3. [事件间距检测] 统计同类关键事件（战斗/情感爆发/重大揭示/角色死亡）的出现间隔，检测间距异常（过近/过远）
      4. 生成《节奏修正报告》含检测到的问题类型、位置、AI已执行的修正
    auto_fix: true
    fix_strategy: "根据检测到的异常模式生成修正方案（插入次级冲突/冷却点/调整峰值位置），用户审核后执行"
    description: "冲突强度量化、情绪类型交替、事件间距三维节奏检测"

  outline_logic_quality:
    display_name: "大纲逻辑质量"
    applies_to: [outline]
    level: blocker
    priority: 1
    check_algorithm: |
      1. [因果链断裂检测] 对每章每个核心事件追溯起因：
         角色主动推动 → 检查动机链是否完整
         外部事件触发 → 检查前文是否有铺垫
      2. [动机不一致检测] 逐章比对角色行为与设定动机，标记行为偏离
      3. [信息对等性检查] 逐章检查角色知识边界：
         角色是否做出基于"他不知道的信息"的决策？
         角色是否未利用"他应该知道的信息"？
      4. 生成《逻辑修正报告》含断裂位置/不一致位置/对等性破坏位置及修正方案
    auto_fix: true
    fix_strategy: "因果链断裂→在前文插入铺垫；动机不一致→修改行为或补动机转变铺垫；信息对等性破坏→修改决策或调整知识边界标注"
    description: "因果链完整性、动机一致性、信息对等性三重逻辑审查"

  outline_structure_quality:
    display_name: "大纲结构质量"
    applies_to: [outline]
    level: critical
    priority: 2
    check_algorithm: |
      1. [幕比例检测] 一幕占20-25%/二幕50-60%/三幕15-25%，严重偏离标记
      2. [关键节点位置] 催化事件10-15%/中点转折45-55%/最终高潮85-95%，位置偏移标记
      3. [多线平衡检测] 统计每条情节线在各章节的推进情况：
         支线连续>8章无推进 → 标记遗忘
         支线总占比<5%却在结局承担关键功能 → 标记铺垫不足
         主线连续>5章被支线挤压 → 标记方向感缺失
      4. 生成《结构修正报告》含压缩/扩充/移动方案
    auto_fix: true
    fix_strategy: "幕比例→压缩扩充；关键节点→移动位置；多线平衡→插入/合并支线推进"
    description: "幕比例、关键节点位置、多线平衡三维结构审查"

  outline_comprehensive_checklist:
    display_name: "大纲综合审核检查清单"
    applies_to: [outline]
    level: info
    priority: 9
    check_algorithm: |
      在节奏/逻辑/结构审查通过后，最终输出用户直觉检查清单供用户快速验证：
      【节奏检查】
      1. 随便挑三个位置（前中后各一），连读3章——有没有在任一处觉得"没什么让人兴奋的东西"？
      2. 有没有哪个位置的冲突强度让你觉得"已经到这个程度了，后面还能怎么升级？"
      3. 中间有哪段让你想快速跳过吗？
      【逻辑检查】
      4. 随便挑三个情节节点，问"这件事为什么会发生？"——能否立刻回答因果链？
      5. 有没有哪个角色的行为像"这不像是他会做的事"？
      6. 有没有哪个节点的剧情推进让你觉得"主角的运气太好了？"
      【结构检查】
      7. 开场读完后是否产生"我想继续看他的故事"的感觉？
      8. 结尾是否让你觉得"这就结束了？我还有问题没被回答"？
      9. 有没有哪条支线你完全忘了存在，到后面它突然跳出来了？
    auto_fix: false
    description: "用户直觉驱动的五维大纲终审检查清单"

  outline_user_instruction_templates:
    display_name: "大纲用户指令模板"
    applies_to: [outline]
    level: info
    priority: 10
    check_algorithm: |
      当用户发现大纲问题但说不清具体修改方式时，可使用以下指令模板驱动AI自动诊断和修正：
      【节奏类】
      - "这段大纲读起来太平了——自查这几章的冲突强度和情绪类型，标记问题并修正。"
      - "高潮结束之后拖得太久了——高潮位置往后移，让高潮更接近结局。"
      【逻辑类】
      - "主角在这章做的选择我不太信——回溯动机链，看哪个环节铺垫不够。"
      - "这个转折太突然了——在前文找两个位置插入暗示，让读者在回收时觉得'原来之前是这个意思'。"
      【结构类】
      - "开场太慢了——压缩第一幕，把催化事件提前至少3章，同时确保情感建立不损。"
      - "支线X到后面消失了——检查推进频率，如果中断太久，重新安排后续出场。"
    auto_fix: false
    description: "用户驱动AI大纲诊断的指令模板集合"
```

## 六、AI 痕迹清除体系

> v3.0 保留了 v2.0 中 AI Trace Purifier 的完整检测和清除逻辑。
> Agent 直接调用 `purifier.pipeline.purify(text)`，同步获取清除结果。

### 6.1 6 大 AI 痕迹特征检测

```python
# src/ai_purifier/detector.py
class AITraceDetector:
    """
    AI 痕迹检测器
    检测 6 大 AI 痕迹特征，返回问题列表
    """

    def detect(self, text: str) -> list[TraitIssue]:
        issues = []

        # 特征1: 句式匀质化
        # AI 倾向写出长度均匀的句子，缺乏节奏变化
        sentence_lengths = [len(s) for s in text.replace("！","。").replace("？","。").split("。")]
        sentence_lengths = [l for l in sentence_lengths if l > 0]
        if sentence_lengths:
            mean = statistics.mean(sentence_lengths)
            std = statistics.stdev(sentence_lengths) if len(sentence_lengths) > 1 else 0
            fluctuation = std / mean if mean > 0 else 1
            if fluctuation < 0.3:
                issues.append(TraitIssue(
                    trait_type="sentence_rhythm_uniform",
                    severity="critical", fix_level=1,
                    detail=f"句式波动系数 {fluctuation:.2f}（阈值 0.3）"
                ))

        # 特征2: 过渡词依赖
        transition_words = ["然而", "因此", "与此同时", "另外", "但是", "所以", "此外", "不过", "然而", "于是"]
        word_count = max(len(text), 1)
        transition_count = sum(text.count(w) for w in transition_words)
        density = transition_count / (word_count / 1000)
        if density > 15:
            issues.append(TraitIssue(
                trait_type="transition_word_overuse",
                severity="warning", fix_level=1,
                detail=f"过渡词密度 {density:.1f} 次/千字（阈值 15）"
            ))

        # 特征3: 情感说明
        emotion_labels = ["感到", "觉得", "心中充满", "内心", "感受到", "体会到"]
        emotion_count = sum(text.count(w) for w in emotion_labels)
        if emotion_count > 3:
            issues.append(TraitIssue(
                trait_type="emotion_telling",
                severity="warning", fix_level=2,
                detail=f"情感标签出现 {emotion_count} 次"
            ))

        # 特征4: 对话功能化
        # 检测对话是否仅用于传递信息（无潜台词、无停顿）
        dialogue_lines = re.findall(r'"[^"]{10,}"', text)
        info_dense = sum(1 for l in dialogue_lines if self._is_info_dense(l))
        if dialogue_lines and info_dense / len(dialogue_lines) > 0.7:
            issues.append(TraitIssue(
                trait_type="dialogue_functional",
                severity="warning", fix_level=2,
                detail=f"信息密集型对话占比 {info_dense}/{len(dialogue_lines)}"
            ))

        # 特征5: 描写模板化
        templates = ["阳光透过", "微风拂过", "空气中弥漫", "映入眼帘",
                     "他/她深吸一口气", "时间仿佛", "无声的"]
        template_hits = sum(1 for t in templates
                          if re.search(t.replace("/", ""), text))
        if template_hits >= 2:
            issues.append(TraitIssue(
                trait_type="description_templated",
                severity="warning", fix_level=1,
                detail=f"匹配 {template_hits} 个常见描写模板"
            ))

        # 特征6: 安全化倾向
        # 检查是否有"过度安全"的表达
        safety_markers = ["我们应该", "最好还是", "不太合适", "考虑到"]
        safety_count = sum(text.count(m) for m in safety_markers)
        if safety_count > 0:
            issues.append(TraitIssue(
                trait_type="safety_bias",
                severity="info", fix_level=3,
                detail=f"检测到 {safety_count} 处安全化表达"
            ))

        return issues
```

### 6.2 三级清除策略

| 级别 | 清除方式 | 适用场景 | 示例问题 |
|------|---------|---------|---------|
| **L1 自动** | 无需用户介入，自动执行 | 句式/过渡词/描写模板 | 句式匀质化、过渡词过度使用、描写模板化 |
| **L2 半自动** | AI 提供 3 种方案供用户选择 | 情感表达/对话优化 | 情感说明式表达、对话功能化 |
| **L3 仅报告** | 标记位置供用户决策 | 安全化倾向 | 安全化倾向（需要用户判断） |

```python
# src/ai_purifier/pipeline.py
class PurificationPipeline:
    def purify(self, text: str) -> PurificationResult:
        """执行完整的 AI 痕迹清除流水线"""
        issues = self.detector.detect(text)
        if not issues:
            return PurificationResult(passed=True, text=text)

        # 按清除级别分组
        l1 = [i for i in issues if i.fix_level == 1]  # 自动
        l2 = [i for i in issues if i.fix_level == 2]  # 半自动
        l3 = [i for i in issues if i.fix_level == 3]  # 仅报告

        # 执行 L1 自动修复
        text = self._auto_fix(text, l1)

        # 生成 L2 半自动修复建议
        suggestions = self._generate_suggestions(text, l2) if l2 else []

        # 生成 L3 报告
        report = self._build_report(l1, l2, l3)

        return PurificationResult(
            passed=len(issues) == len(l1),  # 所有问题都是 L1 级别才算自动通过
            text=text,
            suggestions=suggestions,
            report=report,
        )
```

### 6.3 自动修复器示例

```python
# src/ai_purifier/fixers/sentence_rhythm_fixer.py
class SentenceRhythmFixer:
    """
    句式节奏修复器
    破坏 AI 匀质句式，注入长短交替的节奏
    """

    def fix(self, text: str, params: dict = None) -> str:
        sentences = text.split("。")
        fixed = []

        for i, sent in enumerate(sentences):
            if not sent.strip():
                fixed.append(sent)
                continue

            # 节奏破坏策略
            strategy = i % 3
            if strategy == 0 and len(sent) > 30:
                # 长句拆短：将长句按"，"拆为短句，部分用"。"替换"，
                parts = sent.split("，")
                mid = len(parts) // 2
                short = "。".join(parts[:mid]) + "，" + "，".join(parts[mid:])
                fixed.append(short)
            elif strategy == 1 and len(sent) < 10:
                # 短句接续：将短句与下一句合并
                if i + 1 < len(sentences):
                    next_sent = sentences[i + 1]
                    merged = sent + "，" + next_sent
                    fixed.append(merged)
                    sentences[i + 1] = ""  # 跳过下一句
                else:
                    fixed.append(sent)
            else:
                fixed.append(sent)

        return "。".join(fixed)
```

---

## 七、步骤协议体系

> v3.0 不再有"审核断点"的概念。所有环节默认需要用户交互，无需配置 `requires_review` 或 `auto_approve_threshold`。
> `step_protocols.yaml` 仅用于定义每个环节的展示模板、依赖关系和生成规则，供 Agent 在"阶段一：展示"时使用。

### 7.1 步骤协议配置（增强版）

**第一层约束：step_protocols.yaml**
| 属性 | 说明 | 读取者 | 读取时机 |
|------|------|--------|---------|
| `input_schema` | Agent 生成时必须遵循的结构定义（字段类型、范围、枚举值） | Agent（LLM）生成前校验 | 阶段三执行前 |
| `quality_checks` | 生成后立即执行的轻量检查（不同于深度审查） | ModuleRegistry.validate() | 模块 run() 后立即 |
| `agent_prompt_hints` | Agent 生成时的提示方向列表 | Agent（LLM） | 阶段三生成时 |
| `display_template` | 阶段一展示给用户的执行计划步骤列表 | WorkflowOrchestrator._present_plan() | 阶段一展示 |

```yaml
# config/step_protocols.yaml（增强版）
# 作用：定义每个环节 Agent 向用户展示的信息模板、生成约束和质量检查
# 注意：所有环节都需要用户交互，此文件不控制审核流程

step_protocols:
  inspiration:
    display_name: "灵感启动"
    dependencies: []
    generation_rule: "基于用户输入，生成 3 个创新的灵感方向"
    input_schema:
      directions:
        type: list
        min_items: 3
        max_items: 3
        item_schema:
          id: str
          title: {type: str, min_length: 2}
          concept: {type: str, min_length: 20}
          innovation_score: {type: float, min: 0, max: 1}
          summary: {type: str, min_length: 50}
          emotional_potential: {type: float, min: 0, max: 1}
    quality_checks:
      - check: innovation_score_range
        rule: "每个方向的 innovation_score 必须在 0-1 之间"
        level: error
      - check: direction_count
        rule: "必须恰好生成 3 个方向"
        level: error
      - check: direction_diversity
        rule: "三个方向不可雷同（cosine < 0.6）"
        level: warning
    agent_prompt_hints:
      - "三个方向分别侧重情节驱动、角色驱动、设定驱动"
      - "每个方向附带一个具体场景梗概"
      - "创新性评分基于题材差异化程度"
    display_template:
      - "📋 执行计划："
      - "  1. 分析用户输入的主题关键词"
      - "  2. 生成 3 个差异化灵感方向"
      - "  3. 每个方向附带创新性评分和梗概"
      - "  4. 质量审查并展示"

  outline:
    display_name: "拟定大纲"
    dependencies: [theme]
    generation_rule: "生成三幕结构大纲，含因果链标注和节奏热力图"
    input_schema:
      acts:
        type: list
        min_items: 3
        max_items: 3
        item_schema:
          act: int
          name: str
          chapters: {type: int, min: 3, max: 60}
          summary: str
          key_events: {type: list, min_items: 1}
      causal_chain:
        type: list
        min_items: 1
        item_schema:
          from_event: str
          to_event: str
          cause_type: {enum: ["直接因果","间接因果","伏笔关联"]}
      rhythm_map:
        type: list
        min_items: 3
        item_schema:
          chapter_range: str
          tension: {type: float, min: 0, max: 1}
          pace: {enum: ["slow", "medium", "fast"]}
    quality_checks:
      - check: act_count
        rule: "必须恰好三幕"
        level: error
      - check: causal_chain_not_empty
        rule: "必须有因果链"
        level: error
      - check: total_chapters_range
        rule: "总章节数 10-200"
        level: error
      - check: act2_greater_act1
        rule: "第二幕章节数必须大于第一幕"
        level: error
      - check: key_events_in_causal_chain
        rule: "每个 key_event 必须在因果链中出现"
        level: warning
    agent_prompt_hints:
      - "第一幕(setup)20-30%, 第二幕(confrontation)40-50%, 第三幕(resolution)20-30%"
      - "因果链需有一条跨幕因果链"
      - "节奏曲线至少 3 次 tension 峰值变化"
    display_template:
      - "📋 执行计划："
      - "  1. 读取小说主题数据"
      - "  2. 构建三幕结构：设置/对抗/解决"
      - "  3. 标注各幕间的因果链关系"
      - "  4. 生成节奏热力图"
      - "  5. 质量审查（逻辑链完整性、章节数校验）"

  # 其余环节以此类推，因篇幅限制仅展示关键字段
  character:
    display_name: "人物设定"
    dependencies: [world_building]
    generation_rule: "生成核心角色和配角，含四层档案"
    input_schema:
      characters:
        type: list
        min_items: 3
        item_schema:
          id: str
          name: {type: str, min_length: 1}
          role: {enum: ["protagonist", "antagonist", "supporting", "minor"]}
          layer1_identity: {type: object, required: [name, age, occupation, background]}
          layer2_psychology: {type: object, required: [motivation, fear, desire, flaw]}
          layer3_ability: {type: object, required: [skills, knowledge_boundaries]}
          layer4_special: {type: object, required: [secrets, perception_filter]}
    quality_checks:
      - check: min_character_count
        rule: "至少 3 个角色（1 主角 + 2 配角）"
        level: error
      - check: four_layers_complete
        rule: "每角色必须包含全部四层"
        level: error
      - check: protagonist_secret
        rule: "主角必须有秘密"
        level: warning
    agent_prompt_hints:
      - "每角色必须包含情感身体词典（非抽象描述）"
      - "语气指纹必须与角色身份一致"
      - "感知过滤器决定角色叙述视角"
    display_template:
      - "📋 执行计划："
      - "  1. 读取世界观规则集"
      - "  2. 生成主角 + 至少 2 名配角"
      - "  3. 每角色构建四层档案：身份/心理/能力/特殊"
      - "  4. 标注情感身体词典和语气指纹"
      - "  5. 质量审查（完整性、世界观一致性）"

  world_building:
    display_name: "世界观设定"
    dependencies: [theme, outline]
    generation_rule: "生成 8 维度世界观规则集"
    input_schema:
      dimensions:
        type: list
        min_items: 8
        max_items: 8
        item_schema:
          name: {enum: ["物理规则", "地理空间", "时间历史", "社会结构", "文化习俗", "科技水平", "魔法/超自然体系", "经济体系"]}
          rules:
            type: list
            min_items: 2
            item_schema:
              id: str
              description: {type: str, min_length: 10}
              scope: str
              constraints: str
              conflicts_with: {type: list}

  foreshadow:
    display_name: "伏笔追踪"
    dependencies: [outline, character, faction]
    generation_rule: "生成伏笔并注册到 ChromaDB"
    input_schema:
      foreshadows:
        type: list
        min_items: 1
        item_schema:
          id: str
          type: {enum: ["信息伏笔", "人物伏笔", "物品伏笔", "能力伏笔", "关系伏笔", "规则伏笔", "情感伏笔", "结构伏笔"]}
          target_chapter: {type: int, min: 1}
          description: {type: str, min_length: 20}
          hint_text: {type: str, min_length: 10}
          importance: {type: float, min: 0, max: 1}
    quality_checks:
      - check: chroma_deduplicate
        rule: "与已有伏笔余弦相似度 < 0.85"
        level: error
      - check: target_chapter_valid
        rule: "target_chapter 在大纲章节范围内"
        level: error
      - check: major_foreshadow_plan
        rule: "重要性 > 0.7 的伏笔必须有 reveal_plan"
        level: error

  manuscript:
    display_name: "正文初稿"
    dependencies: [detail_outline, world_building, character, foreshadow]
    generation_rule: "生成正文初稿 → 质量审查 → AI 痕迹清除 → 同步"
    quality_checks:
      - check: word_count_min
        rule: "每章字数 ≥ 细纲预算的 80%"
        level: error
      - check: word_count_max
        rule: "每章字数 ≤ 细纲预算的 120%"
        level: error
      - check: scene_count_match
        rule: "场景数必须与细纲一致"
        level: error
      - check: pov_match
        rule: "场景 POV 必须与细纲一致"
        level: error
```

### 7.2 NLP 反馈解析器

Agent 在收到用户的 `修改 <内容>` 指令时，首先尝通过模板匹配解析自然语言反馈。
未匹配的反馈通过 `pass_to_agent` 操作传递给 Agent 自己处理。

```python
# src/workflow/nlp_parser.py
class NLPFeedbackParser:
    """
    自然语言反馈解析器
    将用户的模糊反馈解析为可执行的修改操作
    Agent 在"修改"命令和"确认"阶段的修改指令中使用
    
    注意：解析器不做 LLM 调用。模板匹配失败时，
    将原始反馈通过 EditOp(action="pass_to_agent") 传递给 Agent 处理。
    """

    def parse(self, feedback: str, context: dict) -> list[EditOp]:
        templates = [
            (r"太(.+)了", lambda m: EditOp(
                action="adjust", field=m.group(1), direction="decrease")),
            (r"不够(.+)", lambda m: EditOp(
                action="adjust", field=m.group(1), direction="increase")),
            (r"把(.+)改成(.+)", lambda m: EditOp(
                action="replace", field=m.group(1), value=m.group(2))),
            (r"保留(.+)，修改(.+)", lambda m: EditOp(
                action="partial", keep=m.group(1), modify=m.group(2))),
            (r"重新(.+)", lambda m: EditOp(
                action="regenerate", field=m.group(1))),
            (r"再想想|重做|不满意", lambda _: EditOp(
                action="regenerate_all")),
        ]

        for pattern, handler in templates:
            match = re.search(pattern, feedback)
            if match:
                return [handler(match)]

        return self._llm_parse(feedback, context)

    def _llm_parse(self, feedback: str, context: dict) -> list[EditOp]:
        """模板未匹配时，将原始反馈传递给 Agent 处理"""
        return [
            EditOp(
                action="pass_to_agent",
                original_feedback=feedback,
                context_summary=context.get("step_name", ""),
            )
        ]

```

### 7.3 Agent 约束配置（第三层）

**第三层约束：agent_constraints.yaml**
| 属性 | 说明 | 读取者 | 读取时机 |
|------|------|--------|---------|
| `constraint_type` | 约束类型（behavior/data/boundary） | Agent（LLM） | 全程生效 |
| `severity` | 违反后果（blocker/error/warning） | WorkflowOrchestrator | 决策时校验 |

```yaml
# config/agent_constraints.yaml
# 作用：定义 Agent 在任何时候都必须遵守的行为约束
# 读取者：agent_entry.py（启动时打印摘要） + Agent（LLM 全程遵守）
# 注意：这些规则不可被 Agent 自身修改或绕过

agent_constraints:

  - id: sandwich_interaction
    constraint_type: behavior
    severity: blocker
    display_name: "三明治交互约束"
    applies_to: all_steps
    description: |
      每个环节 = { 展示 } → { 用户决策 } → { 执行 } → { 确认 }
    violations:
      - "在展示计划之前直接执行"
      - "跳过用户确认环节"
      - "自动执行并仅通知用户（'我已经完成了，结果如下'）"
      - "替用户做决定（'我建议跳过这个环节，所以就跳过了'）"

  - id: data_write_path
    constraint_type: data
    severity: blocker
    display_name: "数据写入路径约束"
    description: |
      所有写入必须经过：Agent 生成 → module.run() → 写 SQLite → sync_engine.sync_json_to_md()
    violations:
      - "跳过同步引擎直接修改 Markdown 文件"
      - "修改 SQLite 后不同步到 user_view/"
      - "删除用户已确认的数据"

  - id: rollback_scope
    constraint_type: behavior
    severity: error
    display_name: "回退范围约束"
    applies_to: all_steps
    description: |
      回退时保留目标环节之前的所有数据，删除目标环节及之后的数据
    rules:
      - "保留目标环节之前的所有数据"
      - "删除目标环节及其之后的所有数据"
      - "在 change_log 中记录回退操作"
      - "通知用户哪些数据被保留、哪些被删除"

  - id: blocker_reporting
    constraint_type: behavior
    severity: blocker
    display_name: "质量事故处理约束"
    applies_to: all_steps
    description: |
      质量审查发现 BLOCKER 级别问题时，必须向用户报告并等待决策
    rules:
      - "立即向用户报告问题详情"
      - "展示问题来源（哪个模块、哪个数据、什么冲突）"
      - "提供修复建议"
      - "等待用户指令（修改/重做/忽略）"
      - "Agent 不得自行决定是否忽略 BLOCKER"

  - id: system_boundary
    constraint_type: boundary
    severity: blocker
    display_name: "系统边界约束"
    applies_to: all_steps
    violations:
      - "修改 config.py（除用户明确要求外）"
      - "修改 agent_entry.py 的执行逻辑"
      - "修改 step_protocols.yaml / quality_rules.yaml / agent_constraints.yaml"
      - "删除 data/novel.db 数据库文件"
      - "调用未在 modules/ 注册的外部 Python 模块操作小说数据"
      - "向小说数据中注入与创作无关的内容"

  - id: command_availability
    constraint_type: behavior
    severity: error
    display_name: "可用命令展示约束"
    applies_to: decision_and_confirmation
    description: |
      每个环节的"用户决策"和"确认"阶段必须展示所有可用命令
    required_commands:
      decision_phase: ["执行", "修改 <内容>", "跳过", "停止"]
      confirmation_phase: ["确认", "修改 <内容>", "重做", "回到 <N>", "停止"]

  - id: agent_generation_boundary
    constraint_type: boundary
    severity: error
    display_name: "Agent 生成边界约束"
    applies_to: all_steps
    description: |
      Agent 生成内容时必须遵循以下原则
    rules:
      - "Agent 生成内容，模块只做存储验证——模块不做 LLM 调用"
      - "约束外置——所有规则/阈值/模板在 yaml，不硬编码"
      - "零外部依赖——不需 API Key 或外部服务"
```

#### 7.3.1 agent_entry.py 启动时打印约束摘要

```python
# agent_entry.py 启动时
def print_agent_constraints():
    """打印 Agent 约束规则摘要"""
    from config import Config
    import yaml

    with open("config/agent_constraints.yaml", encoding="utf-8") as f:
        constraints = yaml.safe_load(f)

    print("\n" + "=" * 60)
    print("  Agent 约束规则（全程生效）")
    print("=" * 60)
    for c in constraints["agent_constraints"]:
        severity_icon = {"blocker": "⛔", "error": "⚠", "warning": "⚡"}
        icon = severity_icon.get(c["severity"], "•")
        print(f"  {icon} [{c['severity'].upper()}] {c['display_name']}")
    print("=" * 60 + "\n")
```

---

## 八、双向同步引擎

> v3.0 保留了双向同步的核心逻辑，但实现为 `sync_engine.py` 的两个函数。
> Agent 直接在 WorkflowOrchestrator 中调用 `sync.sync_json_to_md()` 和 `sync.sync_md_to_json()`。

### 8.1 同步引擎接口

```python
# src/sync/engine.py
class SyncEngine:
    """
    双向同步引擎
    Agent 直接调用两个函数:
    - sync_json_to_md(novel_id): 将系统 JSON 数据渲染为用户可读的 Markdown
    - sync_md_to_json(novel_id): 将用户修改的 Markdown 解析回系统 JSON
    """

    def __init__(self, db_session, user_view_dir: str, system_data_dir: str):
        self.db = db_session
        self.user_view_dir = Path(user_view_dir)
        self.system_data_dir = Path(system_data_dir)

    def sync_json_to_md(self, novel_id: str) -> SyncReport:
        """
        方向: 系统 JSON → 用户 Markdown
        场景: Agent 修改数据后，更新用户可视层
        """
        novel = self._load_novel(novel_id)
        novel_dir = self.user_view_dir / f"我的小说_{novel.title}"
        novel_dir.mkdir(parents=True, exist_ok=True)

        # 渲染各个模块的 Markdown
        for module_name in self.MODULE_ORDER:
            data = self._load_module_data(novel_id, module_name)
            if not data:
                continue
            md_content = self._render_markdown(module_name, data, novel)
            md_path = novel_dir / f"{module_name}.md"
            md_path.write_text(md_content, encoding="utf-8")

        # 渲染审查报告
        self._render_review_report(novel_id, novel_dir)

        # 渲染小说概览（聚合视图）
        self._render_overview(novel_id, novel_dir)

        return SyncReport(
            direction="json_to_md",
            files_updated=len(list(novel_dir.glob("*.md"))),
            timestamp=datetime.now(),
        )

    def sync_md_to_json(self, novel_id: str) -> SyncReport:
        """
        方向: 用户 Markdown → 系统 JSON
        场景: 用户手动编辑了 Markdown 文件后，同步回系统
        """
        novel = self._load_novel(novel_id)
        novel_dir = self.user_view_dir / f"我的小说_{novel.title}"

        if not novel_dir.exists():
            return SyncReport(direction="md_to_json", files_updated=0, errors=["目录不存在"])

        changes = []
        for md_file in novel_dir.glob("*.md"):
            content = md_file.read_text(encoding="utf-8")
            # 解析 SYNC 标记
            parsed = self._parse_sync_markers(content)
            if parsed:
                changes.extend(parsed)

        # 应用变更到数据库
        applied = self._apply_changes(novel_id, changes)

        return SyncReport(
            direction="md_to_json",
            files_updated=len(applied),
            changes=applied,
            timestamp=datetime.now(),
        )

    def _render_markdown(self, module_name: str, data: dict, novel) -> str:
        """将系统 JSON 数据渲染为带 SYNC 标记的 Markdown"""
        # 使用 Jinja2 模板渲染
        template = self._load_template(module_name)
        return template.render(
            data=data,
            novel_title=novel.title,
            sync_markers=self._generate_sync_markers(module_name, data),
        )
```

### 8.2 Markdown SYNC 标记规范

```markdown
Markdown 中的 SYNC 标记用于标识可以被系统自动同步的字段。

三种标记类型:

1. 字段标记: <!-- SYNC:实体ID:字段路径 -->内容<!-- /SYNC -->
   用户可修改标记内的内容，系统会同步回 JSON。
   <!-- SYNC:CHAR-001:fields.name -->陈渡<!-- /SYNC -->

2. 元数据标记: <!-- SYNC_META:实体ID:属性 -->值<!-- /SYNC_META -->
   由系统维护，用户不建议修改。
   <!-- SYNC_META:CHAR-001:version -->3<!-- /SYNC_META -->

3. 引用标记: <!-- SYNC_REF:实体ID -->关联内容<!-- /SYNC_REF -->
   表示该段落引用了某个实体。
   <!-- SYNC_REF:FOR-003 -->伏笔"将军的秘密"预计在第 8 章回收<!-- /SYNC_REF -->
```

### 8.3 冲突处理

| 冲突场景 | 处理策略 |
|---------|---------|
| 用户修改了 Markdown，但系统也修改了同一字段（MD 时间 > DB 时间） | 以 Markdown 为准（用户手动修改优先） |
| 系统和用户同时修改（DB 时间 > MD 时间） | 以 DB 为准（Agent 修改优先） |
| 时间戳相同或无法判断 | 按配置策略: `last_write_wins` |
| 用户删除了 SYNC 标记 | 标记为"用户主动删除"，不再同步该字段 |

---

## 九、双层架构（用户可视层 + 系统层）

> 从 v1.0 开始保留的核心设计，v3.0 保持不变。

### 9.0 同步标记格式（SYNC Markup）

用户 Markdown 文件中每个与 JSON 字段对应的内容区块，使用 HTML 注释包裹同步标记：

```markdown
<!-- SYNC:实体类型:实体ID:字段路径 -->
（内容）
<!-- /SYNC -->
```

同步引擎通过解析这些标记，实现 Markdown ↔ JSON 的精确双向映射。

**完整示例——人物档案 Markdown：**

```markdown
# CHAR-001 陈渡

> 最后修改：<!-- SYNC_META:CHAR-001:last_modified -->2026-05-28T15:30:00<!-- /SYNC_META -->

## 身份信息

| 字段 | 内容 |
|------|------|
| 姓名 | <!-- SYNC:CHAR-001:fields.name -->陈渡<!-- /SYNC --> |
| 年龄 | <!-- SYNC:CHAR-001:fields.age -->28<!-- /SYNC --> |
| 所属势力 | <!-- SYNC:CHAR-001:fields.faction_id -->FAC-005<!-- /SYNC --> |
```

**同步方向规则：**
- **JSON → MD**（写入）：Module 写完 SQLite 后，SyncEngine 读取 JSON 字段，填充到对应 `<!-- SYNC:... -->` 标记区间，生成完整 Markdown。
- **MD → JSON**（读取）：用户直接编辑 Markdown 文件后，SyncEngine 扫描 `<!-- SYNC:... -->` 标记，提取内容更新 JSON。
- **冲突处理**：当两边同时修改时，conflict_resolver 按"时间戳最新者优先"规则，记录冲突日志并通知用户。

### 9.1 用户可视层

每个小说项目在 `user_view/` 下生成以书名命名的文件夹，包含完整的中文 Markdown 文件：

```
user_view/
└── 我的小说_【书名】/
    ├── 📄 小说概览.md                    ← 实时聚合视图
    ├── 📁 01_主题/
    │   ├── 📄 主题陈述.md
    │   ├── 📄 反向确认.md
    │   └── 📄 情感出发点.md
    ├── 📁 02_世界观/
    │   ├── 📄 世界观总览.md
    │   ├── 📁 宇宙规则/
    │   ├── 📁 地理与空间/
    │   ├── 📄 时间与历史.md
    │   ├── 📁 审查记录/
    │   │   ├── 📄 规则自洽审查.md
    │   │   └── 📄 极端场景测试.md
    │   └── 📄 社会结构.md
    ├── 📁 03_势力/
    ├── 📁 04_势力关系/
    ├── 📁 05_人物/
    ├── 📁 06_人物关系/
    ├── 📁 07_角色弧线/
    ├── 📁 08_物品仓库/
    ├── 📁 09_伏笔管理/
    ├── 📁 10_结构/                     ← 大纲 + 细纲 + 节奏曲线
    ├── 📁 11_正文/                     ← 每章一个 Markdown 文件
    ├── 📁 变更日志/
    │   └── 📄 changelog_2026-05-29.md
    └── 📁 审查报告/
        ├── 📄 四层审查报告.md
        ├── 📄 AI 痕迹清除报告.md
        └── 📄 质量评分趋势.md
```

### 9.2 系统引擎层

`system_data/` 目录存储系统的结构化 JSON 数据，供模块间引用和程序处理：

```
system_data/
└── 我的小说_【书名】/
    ├── novel_manifest.json              ← 项目元数据
    ├── modules/
    │   ├── theme.json
    │   ├── world.json
    │   ├── characters.json
    │   ├── relations.json
    │   ├── foreshadows.json
    │   └── ...
    ├── structure/
    │   ├── outline.json
    │   └── detail_outlines.json
    └── manuscript/
        ├── chapter_001.json
        ├── chapter_002.json
        └── ...
```

### 9.3 用户操作方式

```
用户有两种方式与系统交互：

方式一：终端聊天（推荐）
  Agent 运行 python agent_entry.py
  → 在终端与 Agent 自然语言对话
  → 通过步骤交互确认或修改内容
  → 无需接触文件系统

方式二：直接修改 Markdown
  Agent 完成某个环节后，用户直接在 user_view/ 下编辑 Markdown 文件
  编辑后运行: python agent_entry.py --sync-only
  → 同步引擎读取 SYNC 标记，将用户修改同步回数据库
  → 后续环节自动基于用户的修改继续
```

---

## 十、分阶段实施指南

实施分为 **4 个阶段**。每个阶段有明确的输入、输出和验证标准。

### 阶段一：核心骨架（第 1-3 天）

| 步骤 | 内容 | 验证方式 |
|------|------|---------|
| 1.1 | 创建项目目录结构和 `requirements.txt` | `pip install -r requirements.txt` 成功 |
| 1.2 | 实现数据库层：`engine.py` + `models.py` | SQLite 数据库文件 `data/novel.db` 创建成功 |
| 1.3 | 实现 ChromaDB 客户端：`chroma_client.py` | `data/chromadb/` 目录创建成功 |
| 1.4 | 实现核心引擎：`WorkflowOrchestrator` | 空跑 19 环节循环（不调用 LLM）通过 |

**验证命令**：
```bash
# 初始化数据库
python -c "from src.database.engine import init_database; init_database('data/novel.db')"

# 验证 ChromaDB
python -c "from src.vector_store.chroma_client import init_chromadb; init_chromadb('data/chromadb')"

# 空跑工作流
python -c "
from src.workflow.engine import WorkflowOrchestrator
wo = WorkflowOrchestrator(...)
wo.run('test-novel', dry_run=True)  # dry_run 模式不调用 LLM
"
```

### 阶段二：业务模块（第 4-10 天）

| 步骤 | 内容 | 前置依赖 | 优先级 |
|------|------|---------|--------|
| 2.1 | `theme_engine.py` — 灵感 + 主题 | 阶段一完成 | P0 |
| 2.2 | `world_builder.py` — 世界观 | 2.1 | P0 |
| 2.3 | `character_builder.py` — 人物 | 2.2 | P0 |
| 2.4 | `outline_builder.py` — 大纲 | 2.1 | P1 |
| 2.5 | `relation_builder.py` — 人物关系 | 2.3 | P1 |
| 2.6 | `faction_builder.py` — 势力 | 2.2 | P1 |
| 2.7 | `foreshadow_manager.py` — 伏笔 | 2.2 + 2.3 + 2.4 | P1 |
| 2.8 | `detail_outline.py` — 细纲 | 2.4 + 2.3 | P1 |
| 2.9 | `manuscript_writer.py` — 正文 | 2.8 + 全部设定 | P1 |
| 2.10 | 其他模块（弧线/物品/档案/简介/分卷/导出） | 前序模块 | P2 |

**验证方式**：
```bash
# Agent 先自己生成灵感内容，再调用模块存储
python -c "
from src.modules.theme_engine import ThemeEngine
engine = ThemeEngine(db_session, chroma_client)
# content 是 Agent 自己生成的灵感内容
result = engine.run(context, content)
print(result)
"
```

### 阶段三：质量体系（第 11-14 天）

| 步骤 | 内容 | 验证方式 |
|------|------|---------|
| 3.1 | Quality Orchestrator + 规则注册表 | 质量规则全注册成功 |
| 3.2 | L1 一致性检查器 + L2 逻辑验证器 | BLOCKER 级别正确阻断 |
| 3.3 | AI Trace Purifier 6 大检测器 | 测试文本检出率 ≥ 85% |
| 3.4 | 自动修复器（句式/过渡词/描写） | 修复后二次检测通过率 ≥ 90% |
| 3.5 | 步骤协议 + NLP 反馈解析 | 用户输入正确解析 |

**验证命令**：
```bash
# 测试质量审查
python -c "
from src.quality.orchestrator import QualityOrchestrator
q = QualityOrchestrator(...)
result = q.review(context)
assert result.level != 'blocker'
"

# 测试 AI 痕迹清除
python -c "
from src.ai_purifier.pipeline import PurificationPipeline
p = PurificationPipeline(...)
result = p.purify(sample_text)
print(f'清除问题: {len(result.issues)}')
"
```

### 阶段四：同步与集成（第 15-17 天）

| 步骤 | 内容 | 验证方式 |
|------|------|---------|
| 4.1 | Sync Engine（json_to_md） | JSON 数据渲染为正确的 Markdown |
| 4.2 | Sync Engine（md_to_json） | 修改 Markdown 后同步回 JSON |
| 4.3 | 端到端流程 | `python agent_entry.py` 跑通 19 环节 |

**端到端验证**：
```bash
# 最小可用流程
python agent_entry.py

# 预期输出（在终端看到）:
# 📦 初始化数据库... ✓
# 📦 初始化向量库... ✓
# 🎨 输入灵感: 一个关于记忆的故事
# 📝 环节 01: 灵感启动
#   ✓ 生成 3 个灵感方向
#   ⏸️ 请选择: 1
# ...
# 📝 环节 16: 正文初稿
#   ✓ 第 1 章 (2456 字)
#   ⚠ CRITICAL: AI 痕迹清除（消除 3 个问题）
# ...
# ✅ 小说创作完成！
# 📁 文件位置: user_view/我的小说_【书名】/
```

---

## 十一、验收标准

### 11.1 功能验收

| 编号 | 验收项 | 标准 | 验证方式 |
|------|--------|------|---------|
| F-001 | 零服务启动 | `pip install -r requirements.txt` + `python agent_entry.py` 即可运行 | 无需 Docker/数据库服务/消息队列 |
| F-002 | 19 环节全流程 | 从灵感到导出的完整创作流程串行跑通 | `python agent_entry.py` 不报错 |
| F-003 | 质量审查 | Quality Orchestrator 在每个环节后自动执行审查 | 日志中出现 quality_review 记录 |
| F-004 | AI 痕迹清除 | 正文生成后自动执行清除流水线 | 清除报告在审查报告中生成 |
| F-005 | 步骤交互 | 每环节四阶段交互（展示→决策→执行→确认）正常 | 手动测试逐一确认 |
| F-006 | NLP 反馈解析 | "太短了"、"不够生动"等反馈正确解析 | 模板匹配测试 |
| F-007 | 双向同步 | `sync_json_to_md()` 和 `sync_md_to_json()` 正常工作 | 修改 Markdown 后重新同步验证 |
| F-008 | 伏笔检索 | ChromaDB 向量检索返回正确结果 | 测试相似度查询准确率 |
| F-009 | 数据持久化 | 关闭程序后重新打开数据完整 | 重启后继续创作 |
| F-010 | 导出发布 | 导出为完整的 Markdown/TXT 文件 | 检查导出文件完整性 |

### 11.2 非功能验收

| 编号 | 验收项 | 标准 |
|------|--------|------|
| NF-001 | 可重现性 | 任意步骤可回退重做 |
| NF-002 | 数据安全 | 所有数据仅存储在本地文件系统，不写入日志 |
| NF-003 | 可用性 | 用户只需终端操作，无需编辑代码 |
| NF-004 | 低门槛 | 仅需 Python 3.10+ 和 pip install |

---

## 十二、端到端交互流程验证

三个验证场景覆盖系统全部核心路径，验证无死循环、数据一致。

### 12.1 场景 A：正常流程

**目标**：用户一路「执行」→「确认」走完 19 环节

**前置条件**：
- 空数据库（`data/novel.db` 不存在）
- 执行 `python agent_entry.py`
- 输入灵感描述（如"一个关于记忆和身份的故事，背景在古代"）

**用户操作序列**：

| 阶段 | 用户输入 | 预期系统行为 |
|------|---------|------------|
| 环节 01 决策 | `执行` | Agent 生成 3 个灵感方向，写入 `inspirations` 表 |
| 环节 01 确认 | `确认` | 记录 change_log，进入环节 02 |
| 环节 02 决策 | `执行` | 生成三层主题结构，写入 `themes` 表 |
| 环节 02 确认 | `确认` | 进入环节 03 |
| ...持续至... | ... | ... |
| 环节 16 确认 | `确认` | 正文写入 `manuscripts` 表，状态=draft |
| 环节 17 确认 | `确认` | 审查报告写入 `review_results` 表 |
| 环节 18 确认 | `确认` | manuscripts 状态更新为 fixed |
| 环节 19 确认 | `确认` | 导出文件到 user_view/，流程结束 |

**验证清单**：

| 验证项 | 验证方法 | 预期结果 |
|--------|---------|---------|
| SQLite 数据完整 | 执行 `SELECT count(*) FROM inspirations` 等 | 19 环节均有对应数据 |
| 日志完整 | 检查 `logs/novel_creation.log` | 每个环节的 phase_enter/exit 均记录 |
| user_view Markdown | 检查 `user_view/` 目录 | 19 个模块均有对应 .md 文件 |
| ChromaDB 伏笔 | 查询 chromadb foreshadows collection | 伏笔向量记录完整 |
| 变更日志 | 查询 `change_log` 表 | 19 条 confirmed 记录 |
| 最终导出 | 打开 `📖 完整小说.md` | 包含全部已确认章节正文 |

**Python 验证脚本**：

```python
# tests/test_scenario_a_normal.py
"""场景 A：正常流程验证"""
import sqlite3
from pathlib import Path

def test_scenario_a():
    # 1. SQLite 数据完整性
    conn = sqlite3.connect("data/novel.db")
    cursor = conn.cursor()

    # 验证关键表有数据
    tables_to_check = [
        "inspirations", "themes", "outlines", "world_building",
        "characters", "relations", "character_arcs", "factions",
        "faction_relations", "items", "foreshadows", "archives",
        "synopses", "volumes", "detail_outlines", "manuscripts",
        "review_results"
    ]
    for table in tables_to_check:
        count = cursor.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        assert count > 0, f"{table} 表无数据"

    # 验证 manuscripts 状态链
    statuses = cursor.execute(
        "SELECT DISTINCT status FROM manuscripts"
    ).fetchall()
    status_list = [s[0] for s in statuses]
    assert "draft" in status_list
    assert "fixed" in status_list or "reviewed" in status_list

    # 2. 日志完整性
    log_path = Path("logs/novel_creation.log")
    assert log_path.exists()
    log_content = log_path.read_text(encoding="utf-8")
    assert "workflow_start" in log_content
    assert "workflow_complete" in log_content
    assert "user_confirmation" in log_content

    # 3. user_view 文件验证
    user_view = Path("user_view")
    md_files = list(user_view.rglob("*.md"))
    assert len(md_files) >= 5  # 至少 5 个 Markdown 文件

    # 4. ChromaDB 伏笔验证
    # （略，需 chroma_client 连接验证）

    conn.close()
    print("✅ 场景 A 验证通过")
```

### 12.2 场景 B：修改循环

**目标**：环节 05 确认阶段触发修改，验证数据更新、Markdown 同步、日志记录修改链

**用户操作序列**：

| 阶段 | 用户输入 | 预期系统行为 |
|------|---------|------------|
| 环节 01-04 | `执行` → `确认` | 正常完成 |
| 环节 05 决策 | `执行` | Agent 生成人物设定，写入 `characters` 表 |
| 环节 05 确认 | `修改 主角年龄 28→35` | NLP 解析为 replace 操作 |
| | | Agent 重新生成角色数据 |
| | | CharacterBuilder.run() 更新 `characters` 表 |
| | | SyncEngine 更新 user_view/ 对应 Markdown |
| | | change_log 记录修改链 |
| 环节 05 确认 | `确认` | 进入环节 06 |

**验证清单**：

| 验证项 | 验证方法 | 预期结果 |
|--------|---------|---------|
| 年龄字段更新 | 查询 `characters` 表 JSON 字段 | 主角 age=35 |
| Markdown 同步 | 检查 `user_view/05_人物/CHAR-*.md` | 年龄已更新为 35 |
| 修改链日志 | 查询 `change_log` 表 | 2 条记录：generated + modified |
| 版本号递增 | 查询 characters 表的 version 字段 | version 从 1 → 2 |

**Python 验证脚本**：

```python
# tests/test_scenario_b_modification.py
"""场景 B：修改循环验证"""
import json
import sqlite3

def test_scenario_b():
    conn = sqlite3.connect("data/novel.db")
    cursor = conn.cursor()

    # 1. 验证角色年龄已更新
    row = cursor.execute(
        "SELECT layer1_json FROM characters WHERE role='protagonist'"
    ).fetchone()
    assert row is not None, "主角不存在"
    layer1 = json.loads(row[0])
    assert layer1["age"] == 35, f"年龄未更新: {layer1['age']}"

    # 2. 验证 change_log 记录修改链
    logs = cursor.execute(
        "SELECT action FROM change_log WHERE step_name='人物设定' ORDER BY timestamp"
    ).fetchall()
    actions = [log[0] for log in logs]
    assert "generated" in actions, "缺少生成记录"
    assert "modified" in actions or "confirmed" in actions, "缺少修改记录"

    # 3. 验证有版本号或更新时间戳
    # （需 models.py 支持 version 字段）

    # 4. 验证 user_view Markdown 一致性
    # （在同步引擎完整实现后手动验证）

    conn.close()
    print("✅ 场景 B 验证通过")
```

### 12.3 场景 C：回退操作

**目标**：环节 08 确认阶段触发回退到 04，验证数据删除范围和保留数据的正确性

**用户操作序列**：

| 阶段 | 用户输入 | 预期系统行为 |
|------|---------|------------|
| 环节 01-03 | `执行` → `确认` | 正常完成 |
| 环节 04 | `执行` → `确认` | 世界观念完成 |
| 环节 05 | `执行` → `确认` | 人物设定完成 |
| 环节 06 | `执行` → `确认` | 人物关系完成 |
| 环节 07 | `执行` → `确认` | 角色弧线完成 |
| 环节 08 决策 | `执行` | 势力设定生成完成 |
| 环节 08 确认 | `回到 4` | 删除环节 04-08 数据，保留 01-03 |

**验证清单**：

| 验证项 | 验证方法 | 预期结果 |
|--------|---------|---------|
| 环节 01-03 保留 | 查询 `inspirations`、`themes`、`outlines` | 数据完整 |
| 环节 04-08 删除 | 查询 `world_building`、`characters`、`relations`、`arcs`、`factions` | 数据已删除 |
| change_log 回退记录 | 查询 `change_log` 表 | 有 rollback 记录，含 target_step=4 |
| ChromaDB 一致性 | 查询 chromadb foreshadows collection | 伏笔数据与 SQLite 一致（伏笔是环节 11，不在此次回退范围） |
| user_view 同步 | 检查 user_view/ | 04-08 的目录/Markdown 已删除或标记为回退 |

**Python 验证脚本**：

```python
# tests/test_scenario_c_rollback.py
"""场景 C：回退操作验证"""
import sqlite3

def test_scenario_c():
    conn = sqlite3.connect("data/novel.db")
    cursor = conn.cursor()

    # 1. 环节 01-03 数据保留
    assert cursor.execute(
        "SELECT count(*) FROM inspirations"
    ).fetchone()[0] > 0, "灵感数据被删除"
    assert cursor.execute(
        "SELECT count(*) FROM themes"
    ).fetchone()[0] > 0, "主题数据被删除"
    assert cursor.execute(
        "SELECT count(*) FROM outlines"
    ).fetchone()[0] > 0, "大纲数据被删除"

    # 2. 环节 04-08 数据删除
    # 表映射：环节 04→world_building, 05→characters, 06→relations, 07→character_arcs, 08→factions
    deleted_tables = ["world_building", "characters", "relations",
                      "character_arcs", "factions"]
    for table in deleted_tables:
        count = cursor.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        assert count == 0, f"{table} 表有 {count} 条数据未被删除"

    # 3. change_log 有回退记录
    rollback_logs = cursor.execute(
        "SELECT * FROM change_log WHERE action='rollback'"
    ).fetchall()
    assert len(rollback_logs) > 0, "缺少回退日志"
    target_step = rollback_logs[0][3]  # 假设 target_step 在第 4 列
    assert target_step == 4, f"回退目标不是环节 04"

    # 4. 验证 step_data 表的状态
    step_04 = cursor.execute(
        "SELECT status FROM step_data WHERE step_number=4"
    ).fetchone()
    # 回退后环节 04 应标记为待重做
    assert step_04 is None or step_04[0] in (None, "pending"), \
        f"环节 04 状态异常: {step_04}"

    conn.close()
    print("✅ 场景 C 验证通过")
```

### 12.4 测试运行方式

所有端到端测试应使用独立的测试数据库（`tests/test_novel.db`）运行，避免影响真实数据：

```bash
# 运行全部场景
python -m pytest tests/test_scenario_a_normal.py tests/test_scenario_b_modification.py tests/test_scenario_c_rollback.py -v

# 运行单个场景
python -m pytest tests/test_scenario_a_normal.py -v

# 手动模拟场景 A（交互式）
python agent_entry.py --test-mode --test-db tests/test_novel.db
```

---

## 附录：完整项目文件清单

| 文件 | 位置 | 用途 |
|------|------|------|
| `agent_entry.py` | 项目根目录 | **Agent 入口**，运行此文件开始创作 |
| `config.py` | 项目根目录 | 全局配置（Agent 即 LLM，路径等） |
| `requirements.txt` | 项目根目录 | Python 依赖 |
| `src/quality/orchestrator.py` | 质量模块 | Quality Orchestrator 调度器 |
| `src/quality/rule_registry.py` | 质量模块 | 质量规则注册表 |
| `src/ai_purifier/detector.py` | 痕迹清除模块 | 6 大 AI 痕迹特征检测器 |
| `src/ai_purifier/pipeline.py` | 痕迹清除模块 | 清除流水线 |
| `src/workflow/engine.py` | 工作流引擎 | Workflow Orchestrator |
| `src/workflow/step_protocol.py` | 工作流引擎 | 步骤协议 + NLP 反馈解析 |
| `src/sync/engine.py` | 同步引擎 | 双向同步核心 |
| `src/database/engine.py` | 数据库层 | SQLite 初始化 |
| `src/database/models.py` | 数据库层 | 56+ 张 ORM 模型 |
| `src/vector_store/chroma_client.py` | 向量存储 | ChromaDB 本地持久化客户端 |
| `config/step_protocols.yaml` | 配置 | 步骤协议配置 |
| `config/quality_rules.yaml` | 配置 | 质量规则配置 |
| `config/ai_trace_thresholds.yaml` | 配置 | AI 痕迹检测阈值 |
```