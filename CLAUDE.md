# AI 小说创作系统 — 项目上下文

## 快速启动
```bash
cd /home/cwh13/ai-novel-system
uv run python main.py      # 交互式 CLI
uv run pytest tests/ -v    # 124 tests
```

## 代码维护
代码维护通过 OpenCode 进行：
```bash
cd /home/cwh13/ai-novel-system
opencode                    # 启动 TUI，然后描述要修复的问题
```

修复后：
```bash
git add -A && git commit -m "fix: xxx"
git push origin main
```

## 技术栈
- Python 3.13.13, uv 构建
- SQLAlchemy 2.x + SQLite WAL
- ChromaDB PersistentClient
- structlog 日志
- 20 步创作管线（src/core/modules/）

## 关键文件
- main.py — 入口
- src/core/workflow/engine.py — 核心引擎（1042 行）
- src/config/step_protocols.yaml — 20 步管线契约
- src/ai/__pycache__/llm_client.cpython-313.pyc — ⚠️ 仅 .pyc
