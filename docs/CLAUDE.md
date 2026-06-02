# AI 小说创作系统 — 使用指南

这是一个 **20 步管线化 AI 小说创作系统**。所有步骤通过 `StepExecutor.execute()` 执行，**禁止创建任何临时 `.py` 脚本**。

## 快速启动

```python
from src.storage.database.engine import get_session
from src.core.workflow.step_executor import StepExecutor

with get_session() as session:
    executor = StepExecutor(novel_id, session, chroma_client)
    result = executor.execute(step_num, content)
```

## 核心规则

1. **零脚本** — 所有步骤使用 `StepExecutor.execute()`，禁止创建 `_*.py` 临时文件
2. **一次一步** — 每步执行后展示 output 结果，用户确认后才能进入下一步
3. **20 步管线** — 从灵感启动到导出发布，共 20 个自动化步骤
4. **质量门禁** — 步骤 13（分卷配置）/14（章节细纲）/17（正文初稿）/18（正文审核）/19（正文修正）自动执行质量审查
5. **输出路径** — `output/{小说标题}/`，自动同步 Markdown 文件
6. **数据库** — SQLite `data/novel.db`，ChromaDB `data/chromadb/`
7. **ID 生成** — `src.utils.id_generator.generate_id(prefix, novel_id, session)`

## 20 步管线

| 步号 | 环节 | 模块 | 需要审查 | 说明 |
|------|------|------|---------|------|
| 1-2 | 灵感/主题 | theme_engine | 否 | 灵感方向 + 主题定义 |
| 3 | 世界观 | world_builder | 否 | 修炼体系、世界规则 |
| 4 | 人物 | character_builder | 否 | 角色设定（layer1-4） |
| 5 | 势力 | faction_builder | 否 | 势力组织 |
| 6 | 物品 | item_builder | 否 | 关键物品 |
| 7 | 人物关系 | relation_builder | 否 | 角色关系图谱 |
| 8 | 势力关系 | faction_relation | 否 | 势力关系网 |
| 9 | 人物-势力关联 | char_faction_bridge | 否 | 角色归属 |
| 10 | 角色弧线 | arc_builder | 否 | 成长弧线 |
| 11 | 伏笔 | foreshadow_manager | 否 | 伏笔追踪 |
| 12 | 大纲 | outline_builder | 否 | 三幕结构 |
| 13 | 分卷 | volume_config | **是** | 分卷 + 叙事重力 |
| 14 | 细纲 | detail_outline | **是** | 章节细纲 |
| 15 | 档案 | archive_builder | 否 | 自动聚合 |
| 16 | 简介 | synopsis_builder | 否 | 小说简介 |
| 17 | 正文 | manuscript_writer | **是** | 正文初稿 |
| 18 | 审核 | review_executor | **是** | 自动审查 |
| 19 | 修正 | manuscript_fixer | **是** | 正文修正 |
| 20 | 导出 | export_tool | 否 | 发布导出 |

## 参考

- [project_rules.md](file:///d:/01-%E9%A1%B9%E7%9B%AE/AI%E5%B0%8F%E8%AF%B4%E5%88%9B%E4%BD%9C%E7%B3%BB%E7%BB%9F/.trae/rules/project_rules.md) — 完整项目规范
- [AGENT.md](file:///d:/01-%E9%A1%B9%E7%9B%AE/AI%E5%B0%8F%E8%AF%B4%E5%88%9B%E4%BD%9C%E7%B3%BB%E7%BB%9F/docs/AGENT.md) — Agent 操作指南
- [step_executor.py](file:///d:/01-%E9%A1%B9%E7%9B%AE/AI%E5%B0%8F%E8%AF%B4%E5%88%9B%E4%BD%9C%E7%B3%BB%E7%BB%9F/src/core/workflow/step_executor.py) — 执行器源码