# AI 小说创作系统 — Agent 协作契约

## 总体架构

- **Hermes Agent**（当前会话）：负责运行创作管线、调度任务、处理用户指令
- **OpenCode**（opencode CLI）：负责代码维护、Bug 修复、重构、测试编写

## 协作流程

1. Hermes 运行管线 → 发现错误 → 记录到日志
2. 用户/监控发现错误 → 在项目目录启动 OpenCode → 修复代码
3. OpenCode 修复后提交 git → Hermes 感知到代码更新 → 重新运行验证

## 关键路径

- 项目位置: `/home/cwh13/ai-novel-system`
- GitHub: `https://github.com/ceve-seven/author-toolkit`
- 测试: `uv run pytest tests/ -v`（124 个测试）
- 启动: `cd /home/cwh13/ai-novel-system && uv run python main.py`

## OpenCode 职责

- 修复 TD-001~TD-005 等代码问题
- 实现 --batch 非交互模式
- 优化 LLM Client 接口
- 补充单元测试

## Hermes 职责

- 自主运行 20 步创作管线
- 定时 cron 创作任务
- 质量审核和结果反馈
- 将错误日志提供给 OpenCode 修复
