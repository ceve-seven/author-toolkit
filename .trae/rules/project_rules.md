# 【强制规则】AI 小说创作系统 — 项目架构约束与开发规范

## 第一章：项目架构总览

```
AI小说创作系统/                  # 项目根目录
│
├── main.py                      # 系统入口点
├── config.py                    # 向后兼容桥（新代码用 src.config.settings.Config）
├── requirements.txt             # 依赖管理
├── pyproject.toml               # 项目元数据与构建配置
├── .gitignore                   # Git 忽略规则
│
├── src/                         # 【源码目录】— 所有新代码必须放在此目录下
│   ├── config/                  # 配置层
│   │   ├── __init__.py
│   │   ├── settings.py          # Config 全局配置类
│   │   ├── step_protocols.yaml  # 步骤协议配置
│   │   ├── quality_rules.yaml   # 质量审查规则
│   │   └── ai_trace_thresholds.yaml  # AI 痕迹检测阈值
│   │
│   ├── core/                    # 【核心业务层】— 流程编排与业务逻辑
│   │   ├── __init__.py
│   │   ├── workflow/            # 工作流引擎
│   │   ├── modules/             # 业务模块建造器（18个）
│   │   ├── quality/             # 质量审查系统
│   │   ├── purifier/            # AI 痕迹检测与清除
│   │   └── sync/                # JSON ↔ MD 同步引擎
│   │
│   ├── ai/                      # 【AI 能力层】— AI 交互
│   │   ├── __init__.py
│   │   └── prompts/             # Prompt 工程资产（13 条规则文件）
│   │
│   ├── storage/                 # 【存储层】— 数据持久化
│   │   ├── __init__.py
│   │   ├── database/            # SQLite 数据库
│   │   └── vector_store/        # ChromaDB 向量库
│   │
│   └── utils/                   # 【工具层】— 通用工具
│       ├── __init__.py
│       ├── prompt_loader.py
│       ├── reference_retriever.py
│       ├── id_generator.py
│       └── logger_config.py
│
├── tests/                       # 测试套件
│   ├── __init__.py
│   ├── mock_run.py
│   ├── test_purifier.py
│   ├── test_quality.py
│   ├── test_scenario_a_normal.py
│   ├── test_scenario_b_modification.py
│   ├── test_scenario_c_rollback.py
│   └── test_sync.py
│
├── scripts/                     # 工具脚本（所有脚本必须放在此目录）
│   ├── chroma_vectorize_reference.py
│   ├── run_fault_tolerance_test.py
│   ├── run_full_test.py
│   ├── sync_and_verify.py
│   ├── sync_full_output.py
│   ├── trae_generate_chapter.py
│   ├── init_novel.py
│   ├── check_db.py
│   ├── final_score.py
│   ├── final_verify.py
│   ├── fix_all_data.py
│   ├── fix_chapters_enhance.py
│   ├── fix_satisfaction_design.py
│   ├── fix_settings_enhance.py
│   ├── gen_chapters_51_500.py
│   ├── gen_chapters_501_1100.py
│   ├── gen_chapters_1101_1500.py
│   ├── verify_1500_chapters.py
│   ├── verify_data.py
│   ├── user_simulation.py
│   ├── manager_simulation.py
│   └── simulation_memory_prison.py
│
├── reference/                   # 参考小说库
│   ├── 十日终焉/
│   ├── 我不是戏神.md
│   ├── 游戏入侵.md
│   └── 轮回乐园.md
│
├── plans/                       # 方案文档
│
├── docs/                        # 项目文档
│   ├── AGENT.md                 # Agent 开发手册
│   ├── CLAUDE.md                # Claude 配置
│   ├── 实验.md
│   ├── 审核标准.md
│   └── 容错测试报告.md
│
├── output/                      # 生成的小说输出文件（使用数据库小说标题，禁止加前缀）
│   └── {小说标题}/
│
├── data/                        # 运行时数据（自动生成，不提交到 git）
│   └── chromadb/
│
├── logs/                        # 日志输出
│   └── novel_creation.log
│
└── system_data/                 # 系统引擎层 JSON 数据（自动生成）
    └── {novel_id}/
```
                                      
## 运行方式规范

### 使用虚拟环境的 Python 运行
本项目所有依赖安装在 `.venv` 虚拟环境中，**必须使用虚拟环境的 Python 解释器运行**：

```bash
.venv\Scripts\python.exe main.py        # 启动主程序
.venv\Scripts\python.exe scripts/xxx.py # 运行工具脚本
```

直接使用系统 `python` 命令会导致 `ModuleNotFoundError`，因为系统环境未安装项目依赖。

### 命令行引号转义
PowerShell 的普通双引号字符串转义规则复杂（嵌套引号、中文、JSON 时需要大量反斜杠/反引号）。**复杂参数场景推荐使用 PowerShell here-string（`@"..."@`）**，无需任何转义：

```powershell
# 普通命令（简单场景）
.venv\Scripts\python.exe scripts/xxx.py

# 复杂参数（嵌套引号/中文/JSON 等），使用 here-string
.venv\Scripts\python.exe -c @"
import json
data = {"name": "测试", "desc": "包含'引号'和"双引号""}
print(json.dumps(data, ensure_ascii=False))
"@
```

here-string 的优点：
- 内部的双引号、单引号、中文、JSON 全部按字面处理
- 无需反斜杠、反引号、转义符
- 支持多行文本，适合复杂脚本

### 依赖管理
- 使用 `uv` 管理依赖（见 `uv.lock`）
- 安装新依赖：`uv add <包名>`
- 同步现有依赖：`uv sync`

## 第二章：文件放置强约束

### 规则 1：新文件必须按层放置，禁止随意创建
**所有新增源文件必须放在 `src/` 下的对应层中，不允许在根目录创建新目录。**

```
src/config/       ← 配置逻辑（Settings, YAML 加载）
src/core/         ← 业务逻辑（工作流/模块/质量/净化/同步）
src/ai/           ← AI 交互（Prompts）
src/storage/      ← 数据存储（Database/VectorStore）
src/utils/        ← 通用工具
```

### 规则 2：根目录内容严格限定
**根目录已确定的内容必须严格遵守：**
- `main.py` — 系统入口（唯一入口点）
- `config.py` — Config 兼容桥（只导入 src.config.settings）
- `requirements.txt` — 依赖清单
- `pyproject.toml` — 项目元数据
- `.gitignore` — Git 忽略规则
- `uv.lock` — 依赖锁文件（自动生成）
- `src/` — 源码
- `tests/` — 测试
- `scripts/` — 工具脚本
- `reference/` — 参考小说
- `plans/` — 方案文档
- `docs/` — 开发文档
- `output/` — 小说生成输出
- `data/` — 运行时数据
- `logs/` — 日志
- `system_data/` — 系统数据

**禁止在根目录创建任何 `.py` 文件。示例违规：**
- ❌ `run_steps_*.py` → 必须放 `scripts/`
- ❌ `temp_*.py` → 禁止创建临时脚本
- ❌ `_*.py` → 禁止创建下划线前缀文件

### 规则 3：配置类使用规范
- **新代码**：`from src.config.settings import Config`
- **旧代码兼容**：`from config import Config`（通过 `config.py` 兼容桥仍可用，但新代码不要用）
- YAML 配置文件统一放在 `src/config/` 目录下

### 规则 4：导入路径规范
所有内部导入必须使用绝对导入（`from src.xxx import yyy`），禁止使用相对导入。

```
src/core/modules/xxx.py       → from src.core.modules.base_module import BaseModule
src/core/purifier/detector.py → from src.config.settings import Config
src/storage/database/engine.py → from src.storage.database.models import Base
```

### 规则 5：Prompt 文件管理
Prompt 规则文件统一放在 `src/ai/prompts/` 目录下。
- 新增 Prompt 规则：必须放在 `src/ai/prompts/` 下
- Prompt 引用：YAML 配置中使用 `src/ai/prompts/文件名.md`
- Prompt 加载：统一通过 `src/utils/prompt_loader.py` 加载

## 第三章：命名规范

### 规则 6：Python 文件命名规范
- **必须使用 snake_case**（如 `sync_full_output.py`、`chroma_vectorize_reference.py`）
- **禁止使用下划线前缀**（如 `_build.py`）标识临时文件
- **禁止使用 `temp_` 前缀**（如 `temp_debug.py`）
- 测试文件必须使用 `test_` 前缀，放在 `tests/` 目录

### 规则 7：输出目录命名规范
- `output/` 下的目录名必须直接使用数据库中的小说标题
- **禁止添加任何前缀**（如 `我的小说_{title}`, `novel_{title}` 等）
- `system_data/` 下的目录名必须使用 `novel_id`，禁止添加前缀

### 规则 8：脚本命名规范
`scripts/` 目录中的脚本应根据其用途使用前缀分类：
- `run_` — 执行流程步骤的脚本（如 `run_steps_1_13.py`）
- `sync_` — 同步数据脚本（如 `sync_and_verify.py`）
- `generate_` / `gen_` — 批量生成脚本
- `check_` / `verify_` — 数据验证脚本
- `fix_` — 数据修复脚本
- `init_` — 初始化脚本

## 第四章：业务规则

### 规则 9：严格执行 20 步流程，一次一步
**一次只执行一个步骤。** 在用户确认当前步骤的结果之前，不得进入下一个步骤。

### 规则 10：每步执行后，必须向用户展示 output 输出结果
**每执行完一步，必须向用户汇报 output 同步结果。**

### 规则 11：禁止跳过质量审查步骤
步骤 14（分卷配置）约束引擎强制检测。
步骤 17（正文审核）是必选步骤，不可跳过。

### 规则 12：禁止批量执行
禁止在一次 `with session.begin():` 块中执行多个步骤。
每个 `executor.execute()` 调用之间，必须展示结果、等待用户确认。

### 规则 13：用户反馈优先
如果用户对当前步骤的结果提出修改意见，必须先更新数据库中的数据，再进入下一步。

### 规则 14：工作目录约束
所有代码都在 `AI小说创作系统/` 项目根目录下。不要离开此目录创建文件或寻找资源。

## 第五章：Agent 行为约束

### 规则 15：所有 Agent 必须遵守本规范
无论是当前 Agent 还是其他 Agent，在本项目中创建或修改文件时必须严格遵守本规范的全部规则。

### 规则 16：禁止在根目录创建脚本
**任何 Agent 都不得在根目录创建 `.py` 文件。** 所有脚本必须放在 `scripts/` 目录。

### 规则 17：禁止创建临时文件
- 禁止创建 `temp_*`、`_*` 前缀的临时文件
- 如果需要调试输出，使用 `logs/` 目录
- 调试完成后必须清理调试文件
- 一次性验证脚本使用后必须删除，不得留在仓库中

### 规则 18：输出路径禁止硬编码前缀
- 所有输出目录路径必须使用数据库中的实际数据（小说标题、novel_id）
- **禁止在任何代码中硬编码 `我的小说_` 或类似前缀**
- 导出 `output/` 目录时统一通过 `SyncEngine` 进行

### 规则 19：禁止新建脚本，遇到问题直接汇报
- **任何 Agent 都不得在 `scripts/` 目录下创建新脚本文件**
- 运行系统时遇到错误，只需将错误信息完整汇报给用户
- 由用户决定如何处理，Agent 不得自行创建脚本解决问题
- 已有的 `trae_generate_chapter.py` 已集成全部创作功能（生成提示词、素材加载、正文注入、AI痕迹检测、output同步），覆盖了正文创作的全流程

### 规则 20：prompts 规则文件必须注入创作 prompt
- 生成正文的创作提示词中，**必须包含 `src/ai/prompts/manuscript_writer.md` 的全部规则内容**
- 包括：数据校验规则（章节0）、句式多样性规则（章节6）、情感层次规则（章节7）、AI痕迹检测与清除规则（章节8）
- 通过 `src/utils/prompt_loader.py.load_prompt("manuscript_writer.md")` 加载并注入

## 第六章：数据库设计规范与全局同步约束

### 规则 21：所有实体表必须使用复合主键 (novel_id, entity_id)
**多小说共存要求所有按小说隔离的数据表使用 `(novel_id, entity_id)` 作为复合主键。**
- 示例：`PRIMARY KEY (novel_id, char_id)` 而非 `char_id TEXT PRIMARY KEY`
- 受影响表：characters, factions, faction_members, faction_relations, items, foreshadows, volumes, relations, inspirations, world_rules
- 例外：全局表（novels, id_counters, change_log, fix_logs, review_results, step_data, step_status, purification_logs）可使用自增 ID

### 规则 22：所有 SQL 查询必须通过 novel_id 限定范围
**所有涉及实体表的 SELECT / INSERT / UPDATE / DELETE 中必须包含 `novel_id` 限定：**
- ✅ 正确：`WHERE novel_id = :novel_id AND char_id = :char_id`
- ❌ 错误：`WHERE char_id = :char_id`（跨小说数据泄露风险）
- INSERT 必须在列清单和 VALUES 中都包含 novel_id
- 模块方法中 novel_id 从 `context["novel_id"]` 获取

### 规则 23：修改 schema 必须全局同步（关键规则）
**任何对 `init_schema()` 中 CREATE TABLE 的修改，必须同步更新以下全部位置：**

| 同步目标 | 文件 | 检查项 |
|---------|------|--------|
| ORM 模型 | `src/storage/database/models.py` | 字段名、类型、主键必须与 CREATE TABLE 一致 |
| 模块 SQL | `src/core/modules/*.py` | 所有 INSERT/SELECT/UPDATE/DELETE 语句 |
| 工作流 SQL | `src/core/workflow/*.py` | 所有查询语句 |
| 同步引擎 | `src/core/sync/engine.py` | 所有数据查询 |
| 测试 mock | `tests/mock_run.py` | 所有 CREATE TABLE 语句 |
| 种子数据 | `tests/helpers.py` | 所有 INSERT 语句 |
| 脚本 | `scripts/*.py` | 所有直接操作数据库的 SQL |

**操作方法**：修改 schema 后，必须执行全文 grep 搜索受影响表名，逐文件检查所有引用。

### 规则 24：测试必须使用独立数据库
- 测试数据库路径：`data/test_novel.db`（与生产库 `data/novel.db` 完全隔离）
- `tests/helpers.py` 中的 `DB_PATH` 必须指向测试数据库
- 测试前必须调用 `reset_engine()` 确保引擎使用测试库路径
- 禁止测试直接调用 `init_schema()` 生产库

### 规则 25：多小说 ID 生成规则
- `generate_id("NOV", "GLOBAL", session)` — 小说 ID 使用全局计数器
- `generate_id("CHAR", novel_id, session)` — 实体 ID 使用小说级计数器，复合主键确保唯一
- 修改 ID 生成方式时必须同步更新：id_generator.py + 调用方模块 + 数据库约束

## 第七章：步骤执行规范 — 零脚本强制约束

### 规则 26：所有步骤必须通过 StepExecutor.execute() 执行（核心规则）
**禁止以任何形式创建临时 `.py` 脚本。** 所有 20 个步骤必须通过 `StepExecutor` 的单步执行器完成。

```python
# ✅ 正确做法（零脚本）
from src.storage.database.engine import get_session
from src.core.workflow.step_executor import StepExecutor

with get_session() as session:
    executor = StepExecutor(novel_id, session, chroma_client)
    result = executor.execute(step_num, content)
    # result.summary → 执行摘要
    # result.sync_status → 同步结果
    # result.errors → 错误列表（如有）

# ❌ 禁止行为
# Write → _step10_volumes.py;  .venv\Scripts\python.exe _step10_volumes.py
# session.execute("INSERT INTO volumes ...")  ← 直接操作数据库
# json.dump({"records": ...}, f)              ← 手动写 system_data JSON
# VolumeConfig().run(ctx, content)            ← 直接调用模块
```

### 规则 27：执行流程自动完成，禁止手动拆分
`StepExecutor.execute()` 内部自动完成以下流程，Agent **不得**手动拆分：

```
依赖验证 → 约束检查 → 模块执行 → 写 system_data JSON → 同步到 output/ → 进度更新
                                                                 └→ 质量审查（步骤13/14/17/18/19）
```

### 规则 28：各步骤模块名与 content 格式

| 步号 | 环节名 | 模块名 | 需质检 | content 格式 |
|------|--------|--------|--------|-------------|
| 1 | 灵感启动 | theme_engine | 否 | directions[] + theme{} |
| 2 | 小说主题 | theme_engine | 否 | theme{} + sub_themes[] |
| 3 | 世界观设定 | world_builder | 否 | dimensions[]（name, rules[]） |
| 4 | 人物设定 | character_builder | 否 | characters[]（name, role, layer1-4, weight） |
| 5 | 势力设定 | faction_builder | 否 | factions[]（name, type, hierarchy, goals, members[]） |
| 6 | 物品库 | item_builder | 否 | items[]（name, type, purpose, current_owner） |
| 7 | 人物关系 | relation_builder | 否 | relations[]（char_a_id, char_b_id, type, strength） |
| 8 | 势力关系 | faction_relation | 否 | relations[]（faction_a_id, faction_b_id, type, strength） |
| 9 | 人物-势力关联 | char_faction_bridge | 否 | links[]（char_id, faction_id, membership_type） |
| 10 | 角色弧线 | arc_builder | 否 | arcs[]（char_id, arc_type, start_state, end_state） |
| 11 | 伏笔追踪 | foreshadow_manager | 否 | foreshadows[] + density_curve[] |
| 12 | 拟定大纲 | outline_builder | 否 | acts[] + causal_chain[] + rhythm_map[] |
| 13 | 分卷配置 | volume_config | **是** | volumes[]（name, chapter_range, pacing, cliffhanger） |
| 14 | 章节细纲 | detail_outline | **是** | chapters[]（chapter_number, pov_character, summary, scenes[]） |
| 15 | 小说档案 | archive_builder | 否 | {}（自动聚合） |
| 16 | 小说简介 | synopsis_builder | 否 | synopsis{one_liner, short_blurb, standard_blurb} |
| 17 | 正文初稿 | manuscript_writer | **是** | chapters[]（title, scenes[], word_count） |
| 18 | 正文审核 | review_executor | **是** | {}（自动执行） |
| 19 | 正文修正 | manuscript_fixer | **是** | chapters[]（含修正标记） |
| 20 | 导出发布 | export_tool | 否 | {}（自动执行） |

**格式参考**：调用 `get_expected_format(step_num)` 获取详细字段说明。

### 规则 29：模块名到 system_data 目录的映射
执行器自动按以下映射将模块结果写入 system_data JSON，Agent **不得**手动写入：

```
theme_engine      → 01_主题
world_builder     → 02_世界观
faction_builder   → 03_势力
faction_relation  → 04_势力关系
character_builder → 05_人物
relation_builder  → 06_人物关系
arc_builder       → 07_角色弧线
item_builder      → 08_物品仓库
foreshadow_manager → 09_伏笔管理
outline_builder   → 10_大纲
volume_config     → 11_分卷
detail_outline    → 12_细纲
manuscript_writer → 13_正文
```

### 规则 30：修改已执行步骤的数据
用户要求修改上一步数据时，只需生成修改后的 `content`，重新调用 `executor.execute(step_num, content)`：
- 模块的 `INSERT OR REPLACE` 会自动覆盖旧数据
- SyncEngine 会自动同步到 output 目录
- **禁止**手动 UPDATE 数据库或直接编辑 output Markdown 文件

### 规则 31：获取步骤信息与当前进度

```python
from src.core.workflow.step_executor import get_step_info, get_expected_format

# 获取步骤定义
info = get_step_info(13)
# → {"step_num": 13, "step_name": "分卷配置", "module_name": "volume_config", ...}

# 获取期望的 content 格式
fmt = get_expected_format(13)

# 查看当前步骤进度
from src.storage.database.engine import get_session
from sqlalchemy import text
with get_session() as s:
    rows = s.execute(
        text("SELECT step_number, step_name, status FROM step_status WHERE novel_id=:nid ORDER BY step_number"),
        {"nid": novel_id}
    ).fetchall()
```

## 第八章：数据库查询规范 — Agent 禁止手写 SQL

### 规则 32：Agent 禁止直接手写 SQL 查询
**Agent 不得直接在代码或命令行中编写 `SELECT / INSERT / UPDATE / DELETE` 语句来查询或修改数据库。**

任何查询需求都必须通过以下方式之一完成：
- `StepExecutor.execute()` → 执行步骤（会自动读写数据库）
- `StepExecutor.get_step_info()` / `get_expected_format()` → 获取步骤元信息
- `SyncEngine.sync_json_to_md()` → 触发同步（自动读取数据库并写 output）
- `JsonToMdRenderer` → 渲染数据库内容为 Markdown

### 规则 33：查看数据只能通过 output 目录或系统 API
需要查看数据时，Agent 必须按以下优先级操作：

```
1️⃣ 查看 output/{title}/ 目录下的 Markdown 文件
   → 所有已同步的数据都可以在这里直接读取

2️⃣ 调用系统模块的查询方法
   → NovelManager.list_novels()      → 列出所有小说
   → NovelManager.get_novel(id)      → 获取单部小说信息
   → NovelManager.get_novel_stats()  → 获取统计数据

3️⃣ 查看 system_data/{novel_id}/modules/ 下的 JSON 文件
   → 模块执行后自动写入，格式与渲染器匹配

4️⃣ ❌ 禁止：直接写 SQL 查询数据库
```

### 规则 34：数据库表名与列名参考（仅供理解数据模型，禁止直接查询）

| 表名 | 关键列 | 说明 |
|------|--------|------|
| novels | id, title, current_step, status | 小说主表 |
| step_status | novel_id, step_number, step_name, status | 步骤进度 |
| inspirations | novel_id, direction_id, title, concept | 灵感方向 |
| themes | novel_id, surface_theme, deep_theme, emotional_hook | 主题 |
| world_building | novel_id, dimension_name, rules(JSON) | 世界观维度 |
| world_rules | novel_id, rule_id, dimension, description, scope, constraints | 世界观规则 |
| characters | novel_id, char_id, name, role, layer1_json~layer4_json | 人物四层档案 |
| relations | novel_id, relation_id, char_a_id, char_b_id, type, strength | 人物关系 |
| character_arcs | novel_id, char_id, arc_type, start_state, end_state | 角色弧线 |
| factions | novel_id, faction_id, name, type, goals, resources, doctrines | 势力 |
| faction_relations | novel_id, relation_id, faction_a_id, faction_b_id, type | 势力关系 |
| char_faction_links | novel_id, char_id, faction_id, membership_type, loyalty | 人物-势力关联 |
| items | novel_id, item_id, name, type, purpose, current_owner | 物品 |
| foreshadows | novel_id, foreshadow_id, type, target_chapter, description | 伏笔 |
| outlines | novel_id, acts(JSON), causal_chain(JSON) | 三幕大纲 |
| volumes | novel_id, volume_number, title, chapter_range, chapter_count | 分卷 |
| detail_outlines | novel_id, chapter_number, chapter_constraint_summary(JSON), scenes(JSON) | 章节细纲 |
| manuscripts | novel_id, chapter_number, title, scenes(JSON) | 正文 |
| review_results | novel_id, module, level, score | 审查结果 |
| synopses | novel_id, one_liner, short_blurb, standard_blurb | 小说简介 |
| archives | novel_id, content(JSON) | 小说档案 |
| change_log | novel_id, step, module, action, summary | 变更日志 |
| fix_logs | novel_id, chapter_number, issue, fix | 修正日志 |
| purification_logs | novel_id, text_length, issues_found, auto_fixed | AI 痕迹清除日志 |
