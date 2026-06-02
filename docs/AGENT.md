# AI 小说创作系统 — Agent 操作指南

## 核心原则

**AI Agent 不得创建任何临时 `.py` 脚本。** 所有步骤必须通过 `StepExecutor.execute()` 完成。

工作流程：
1. AI Agent 通过对话了解用户需求（自然语言）
2. AI Agent 根据用户需求生成每步所需的结构化 content 数据
3. AI Agent 调用 `StepExecutor.execute(step_num, content)` 执行单个步骤
4. AI Agent 将执行结果用自然语言反馈给用户，获取确认
5. **每次只执行一个步骤，得到用户确认后，才能进入下一步**

---

## ⚠️ 强制协议：零脚本执行

### 严禁事项（违规将导致系统不可用）

| 严禁行为 | 说明 |
|---------|------|
| ❌ **严禁创建任何 `.py` 脚本文件** | 不得使用 `Write` 工具创建 `_step*.py`、`_check*.py` 等临时脚本 |
| ❌ **严禁直接操作数据库** | 不得执行 `INSERT/UPDATE/DELETE` 等 SQL，必须通过模块执行 |
| ❌ **严禁手动写入 system_data JSON** | 不得使用 `json.dump()` 写 system_data 目录，由 StepExecutor 自动完成 |
| ❌ **严禁直接调用模块** | 不得调用 `VolumeConfig().run(ctx, content)`，必须通过 `StepExecutor.execute()` |
| ❌ **严禁批量执行** | 不得一次性运行多个步骤，必须一次一步 |
| ❌ **严禁跳过用户交互** | 每步都必须与用户自然语言交流，等用户说"继续"才能进入下一步 |
| ❌ **严禁跳过质量审查** | 步骤 13/14/17/18/19 强制质量审查，不可跳过 |
| ❌ **严禁不展示 output 结果** | 每步执行后必须展示 output 目录结构和关键文件内容 |

### 强制执行流程

每步必须按以下 5 阶段执行：

```
阶段 1️⃣ 【自然语言交互】← 与用户对话了解需求
    ↓
阶段 2️⃣ 【生成结构化 content】← AI Agent 根据规则生成 content 字典
    ↓
阶段 3️⃣ 【StepExecutor 执行】← executor.execute(step_num, content)
    ↓                     ├─ 依赖验证
    ↓                     ├─ 约束验证（整数章检测等）
    ↓                     ├─ 模块执行（写数据库）
    ↓                     ├─ 写 system_data JSON
    ↓                     ├─ 同步到 output/
    ↓                     └─ 质量审查（步骤 13/14/17/18/19）
    ↓
阶段 4️⃣ 【展示结果给用户】← 展示 summary + output 目录文件
    ↓
阶段 5️⃣ 【等待用户确认】← 用户确认后才能执行下一步
```

---

## 系统架构

```
src/
  core/workflow/step_executor.py  ← 🔴 唯一允许的模块调用入口
  core/modules/                   ← 20 个模块，统一接口 module.run(context, content)
    registry.py                   ← get_registry().get("模块名") 获取模块类
    theme_engine.py               → 步骤 01-02: 灵感 & 主题
    world_builder.py              → 步骤 03: 世界观
    character_builder.py          → 步骤 04: 人物
    faction_builder.py            → 步骤 05: 势力
    item_builder.py               → 步骤 06: 物品
    relation_builder.py           → 步骤 07: 人物关系
    faction_relation.py           → 步骤 08: 势力关系
    char_faction_bridge.py        → 步骤 09: 人物-势力关联
    arc_builder.py                → 步骤 10: 角色弧线
    foreshadow_manager.py         → 步骤 11: 伏笔
    outline_builder.py            → 步骤 12: 大纲
    volume_config.py              → 步骤 13: 分卷配置
    detail_outline.py             → 步骤 14: 章节细纲
    archive_builder.py            → 步骤 15: 小说档案
    synopsis_builder.py           → 步骤 16: 简介
    manuscript_writer.py          → 步骤 17: 正文初稿
    review_executor.py            → 步骤 18: 正文审核
    manuscript_fixer.py           → 步骤 19: 正文修正
    export_tool.py                → 步骤 20: 导出发布
  core/sync/engine.py             ← 同步引擎（生成 output/ 结构化 Markdown）
  core/quality/orchestrator.py    ← 质量审查编排
  core/purifier/                  ← AI 痕迹检测与清除
  storage/database/engine.py      ← SQLite 数据库（get_session / init_schema）
  storage/vector_store/           ← ChromaDB 向量库
```

---

## 第零步：获取会话

```python
from src.storage.database.engine import get_session
from src.core.workflow.step_executor import StepExecutor, get_step_info, get_expected_format

with get_session() as session:
    executor = StepExecutor(novel_id, session, chroma_client)
```

---

## 20 步执行管线

| 步号 | 环节名 | 模块名 | 需质检 | 依赖 | content 关键字段 |
|------|--------|--------|--------|------|----------------|
| 01 | 灵感启动 | theme_engine | 否 | — | directions[] + theme{surface_theme, deep_theme, emotional_hook} |
| 02 | 小说主题 | theme_engine | 否 | 1 | theme{} + sub_themes[] |
| 03 | 世界观设定 | world_builder | 否 | 2 | dimensions[]（name, rules[]） |
| 04 | 人物设定 | character_builder | 否 | 3 | characters[]（name, role, layer1-4, weight） |
| 05 | 势力设定 | faction_builder | 否 | 3 | factions[]（name, type, hierarchy, goals, members[]） |
| 06 | 物品库 | item_builder | 否 | 3 | items[]（name, type, purpose, current_owner） |
| 07 | 人物关系 | relation_builder | 否 | 4 | relations[]（char_a_id, char_b_id, type, strength） |
| 08 | 势力关系 | faction_relation | 否 | 5 | relations[]（faction_a_id, faction_b_id, type, strength） |
| 09 | 人物-势力关联 | char_faction_bridge | 否 | 4,5,7,8 | links[]（char_id, faction_id, membership_type） |
| 10 | 角色弧线 | arc_builder | 否 | 4,7,9 | arcs[]（char_id, arc_type, start_state, end_state） |
| 11 | 伏笔追踪 | foreshadow_manager | 否 | 4,5,6 | foreshadows[] + density_curve[] |
| 12 | 拟定大纲 | outline_builder | 否 | 1-11 | acts[] + causal_chain[] + rhythm_map[] |
| **13** | **分卷配置** | **volume_config** | **✅** | **12** | volumes[]（name, chapter_range, pacing, cliffhanger） |
| **14** | **章节细纲** | **detail_outline** | **✅** | **13** | chapters[]（chapter_number, pov_character, summary, scenes[]） |
| 15 | 小说档案 | archive_builder | 否 | 1-14 | {}（自动聚合） |
| 16 | 小说简介 | synopsis_builder | 否 | 15 | synopsis{one_liner, short_blurb, standard_blurb} |
| **17** | **正文初稿** | **manuscript_writer** | **✅** | **14** | chapters[]（title, scenes[], word_count） |
| **18** | **正文审核** | **review_executor** | **✅** | **17** | {}（自动执行） |
| **19** | **正文修正** | **manuscript_fixer** | **✅** | **18** | chapters[]（含修正标记） |
| 20 | 导出发布 | export_tool | 否 | 19 | {}（自动执行） |

---

## 执行示例

### 分卷配置（步骤 13）

```python
content = {
    "volumes": [
        {
            "name": "弃子觉醒",
            "chapter_range": [1, 40],
            "boundary_gravity": [
                {"type": "narrative_gravity",
                 "description": "林家内斗白热化，林尘被迫出走"}
            ],
            "pacing": "fast",
            "major_conflict": "林家内斗，执笔之力觉醒",
            "character_focus": ["CHAR-001"],
            "themes": ["命运觉醒"],
            "cliffhanger": "空白之书的花纹开始发光"
        }
    ]
}

with get_session() as session:
    executor = StepExecutor(novel_id, session, chroma_client)
    result = executor.execute(13, content)

    if result.success:
        print(result.summary)       # "已保存 N 卷配置"
        print(result.sync_status)   # "已同步 N 个文件到 output/"
```

### 正文初稿（步骤 17）

> **必须包含 `manuscript_writer.md` 全部规则**：通过 `prompt_loader.load_prompt("manuscript_writer.md")` 加载。

```python
content = {
    "chapters": [
        {
            "chapter_number": 1,
            "title": "弃子",
            "scenes": [
                {"pov_char_id": "CHAR-001", "content": "正文内容..."}
            ],
            "word_count": 3000
        }
    ]
}
executor.execute(17, content)
```

---

## 查看执行结果

### 检查执行结果

```python
result = executor.execute(step_num, content)

if result.success:
    print(f"✅ {result.summary}")
    for v in result.constraint_violations:
        print(f"  ⚠ {v.message}")
    if result.review_result:
        print(f"  📋 {result.review_result['summary']}")
    print(f"  📁 {result.sync_status}")
else:
    print(f"❌ 失败: {result.errors}")
```

### 检查 output 目录

```python
from pathlib import Path

output_dir = Path("output") / novel_title
for f in sorted(output_dir.rglob("*")):
    print(f"{'📁 ' if f.is_dir() else '📄 '}{f.relative_to(output_dir.parent)}")
```

### 查看步骤信息

```python
from src.core.workflow.step_executor import get_step_info, get_expected_format

info = get_step_info(13)
# {"step_num": 13, "step_name": "分卷配置", "module_name": "volume_config", ...}

fmt = get_expected_format(13)
# "volumes[]（name, chapter_range[2], boundary_gravity[], ..."
```

---

## 输出目录结构

```
output/{小说标题}/
├── 01 主题/01_主题.md
├── 02 世界观/02_世界观.md
├── 03 势力/03_势力.md
├── 04 势力关系/04_势力关系.md
├── 05 人物/05_人物.md
├── 06 人物关系/06_人物关系.md
├── 07 角色弧线/07_角色弧线.md
├── 08 物品仓库/08_物品仓库.md
├── 09 伏笔管理/09_伏笔管理.md
├── 10 大纲/10_大纲.md
├── 11 分卷/11_分卷.md
├── 12 细纲/12_细纲.md
├── 13 正文/13_正文.md
├── 审查报告/
│   ├── 质量审查报告.md
│   └── AI痕迹清除报告.md
└── 小说概览.md
```

---

## 重要事项

1. **一次一步** — 每步执行后展示结果，用户确认后才能进入下一步
2. **约束优先** — 如果执行器返回约束违规，必须修改 content 后重新执行，不能忽略
3. **分卷必须提供 boundary_gravity** — 每卷必须有叙事重力来源解释
4. **正文必须注入 manuscript_writer.md 规则** — 通过 `prompt_loader.load_prompt("manuscript_writer.md")` 加载
5. **角色 ID** — `character_builder` 返回数据中的 char_id 后续步骤可直接使用
6. **格式参考** — `get_expected_format(step_num)` 获取每一步的 content 详细字段说明