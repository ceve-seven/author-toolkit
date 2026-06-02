from __future__ import annotations

import importlib
import json
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import structlog

from src.config.settings import Config
from sqlalchemy import text
from src.core.quality.orchestrator import (
    QualityOrchestrator,
    ReviewContext,
    ReviewLevel,
    ReviewResult,
)
from src.core.sync.engine import SyncEngine, SyncReport
from src.utils import validate_table_name
from src.utils.prompt_loader import load_prompt


class NovelProxy:
    """数据库 Novel 模型的简易代理，供 WorkflowOrchestrator 内部使用。"""

    def __init__(self, novel_id: str, title: str, current_step: int = 1):
        self.id = novel_id
        self.title = title
        self.current_step = current_step


class WorkflowOrchestrator:
    """工作流编排器——四阶段交互：展示 → 用户决策 → 执行 → 确认"""

    STEPS: List[Tuple[str, str]] = [
        ("灵感启动",     "core.modules.theme_engine.ThemeEngine"),
        ("小说主题",     "core.modules.theme_engine.ThemeEngine"),
        ("世界观设定",   "core.modules.world_builder.WorldBuilder"),
        ("人物设定",     "core.modules.character_builder.CharacterBuilder"),
        ("势力设定",     "core.modules.faction_builder.FactionBuilder"),
        ("物品库",       "core.modules.item_builder.ItemBuilder"),
        ("人物关系",     "core.modules.relation_builder.RelationBuilder"),
        ("势力关系",     "core.modules.faction_relation.FactionRelationBuilder"),
        ("人物-势力关联", "core.modules.char_faction_bridge.CharFactionBridge"),
        ("角色弧线",     "core.modules.arc_builder.ArcBuilder"),
        ("伏笔追踪",     "core.modules.foreshadow_manager.ForeshadowManager"),
        ("拟定大纲",     "core.modules.outline_builder.OutlineBuilder"),
        ("分卷配置",     "core.modules.volume_config.VolumeConfig"),
        ("章节细纲",     "core.modules.detail_outline.DetailOutlineBuilder"),
        ("小说档案",     "core.modules.archive_builder.ArchiveBuilder"),
        ("小说简介",     "core.modules.synopsis_builder.SynopsisBuilder"),
        ("正文初稿",     "core.modules.manuscript_writer.ManuscriptWriter"),
        ("正文审核",     "core.quality.review_executor.ReviewExecutor"),
        ("正文修正",     "core.modules.manuscript_writer.ManuscriptFixer"),
        ("导出发布",     "core.modules.export_tool.ExportTool"),
    ]

    _STEP_TABLE_MAP: Dict[str, str] = {
        "灵感启动": "themes",
        "小说主题": "themes",
        "拟定大纲": "outlines",
        "世界观设定": "world_building",
        "人物设定": "characters",
        "人物关系": "relations",
        "人物-势力关联": "char_faction_links",
        "角色弧线": "character_arcs",
        "势力设定": "factions",
        "势力关系": "faction_relations",
        "物品库": "items",
        "伏笔追踪": "foreshadows",
        "小说档案": "archives",
        "小说简介": "synopses",
        "分卷配置": "volumes",
        "章节细纲": "detail_outlines",
        "正文初稿": "manuscripts",
        "正文审核": "review_results",
        "正文修正": "manuscripts",
        "导出发布": "novels",
    }

    def __init__(
        self,
        db_session: Any,
        chroma_client: Any,
        quality_orchestrator: QualityOrchestrator,
        sync_engine: SyncEngine,
    ):
        self.db = db_session
        self.chroma = chroma_client
        self.quality = quality_orchestrator
        self.sync = sync_engine
        self.logger = structlog.get_logger("workflow")

    def run(self, novel_id: str, start_step: int = 1):
        """执行创作流程——主循环，带 structlog 日志"""
        self.logger.info("workflow_start", novel_id=novel_id, start_step=start_step)

        novel = self._load_novel(novel_id)
        plan_modifications: Optional[List[str]] = None
        step_index = start_step - 1

        while step_index < len(self.STEPS):
            step_number = step_index + 1
            step_name = self.STEPS[step_index][0]
            module_path = self.STEPS[step_index][1]

            self.logger.info(
                "phase_enter",
                phase="present",
                novel_id=novel_id,
                step=f"{step_number:02d}/{len(self.STEPS)}",
                step_name=step_name,
            )
            self._present_plan(novel_id, step_number, step_name)

            self.logger.info(
                "phase_enter",
                phase="decision",
                step_name=step_name,
            )
            decision = self._wait_for_decision(step_name)
            self.logger.info(
                "user_decision",
                action=decision["action"],
                modifications=decision.get("modifications"),
            )

            if decision["action"] == "skip":
                self._mark_skipped(novel_id, step_number, step_name)
                self.logger.info(
                    "step_skipped",
                    step=f"{step_number:02d}/{len(self.STEPS)}",
                )
                step_index += 1
                continue
            elif decision["action"] == "stop":
                self.logger.info("workflow_stopped", novel_id=novel_id, step=step_number)
                print(f"\n⏸️  进度已保存到环节 {step_number}")
                self._save_novel(novel)
                break
            elif decision["action"] == "modify":
                plan_modifications = decision.get("modifications", [])
            else:
                plan_modifications = None

            self.logger.info(
                "phase_enter",
                phase="execute",
                step_name=step_name,
                has_modifications=plan_modifications is not None,
            )

            result = self._execute_step(
                novel_id, step_number, step_name, module_path,
                modifications=plan_modifications,
            )

            context = self._build_context(novel_id, step_name)
            self.logger.info("quality_review_start", step_name=step_name)
            review = self.quality.review(context)
            self.logger.info(
                "quality_review_end",
                review_level=str(review.level) if hasattr(review, "level") else "unknown",
                review_score=review.score if hasattr(review, "score") else 0,
                issue_count=len(review.details) if hasattr(review, "details") else 0,
            )

            review_action = self._handle_review_result(review, context)
            if review_action == "regenerate":
                self.logger.info("review_action_regenerate", step_name=step_name)
                continue
            elif review_action == "wait_for_user":
                self.logger.info("review_action_wait_for_user", step_name=step_name)

            if step_name in ("正文初稿", "正文修正"):
                text_to_purify = ""
                if hasattr(result, "text"):
                    text_to_purify = result.text
                elif isinstance(result, dict) and "text" in result:
                    text_to_purify = result["text"]
                if text_to_purify:
                    self.logger.info(
                        "ai_purify_start",
                        text_length=len(text_to_purify),
                    )
                    purify_report = self._purify_ai_traces(novel_id, text_to_purify)
                    if purify_report:
                        purified_issues = len(purify_report.get("issues", []))
                        purified_text = purify_report.get("text", "")
                        self.logger.info(
                            "ai_purify_end",
                            issues_detected=purified_issues,
                            text_updated=bool(purified_text),
                        )
                        if purified_text:
                            self._update_purified_text(novel_id, text_to_purify, purified_text)

            self.logger.info(
                "sync_start",
                direction="json_to_md",
                step_name=step_name,
            )
            sync_report = self.sync.sync_json_to_md(novel_id)
            self.logger.info(
                "sync_end",
                direction="json_to_md",
                files_updated=sync_report.files_updated if hasattr(sync_report, "files_updated") else 0,
            )

            self.logger.info(
                "phase_enter",
                phase="confirmation",
                step_name=step_name,
            )
            confirmed = self._wait_for_confirmation(
                novel_id, step_number, step_name, result, review,
            )

            self.logger.info(
                "user_confirmation",
                action="confirmed" if confirmed is True else (
                    "rollback" if isinstance(confirmed, int) else "retry"),
                target_step=confirmed if isinstance(confirmed, int) else None,
            )

            if confirmed is True:
                novel.current_step = step_number
                self._save_novel(novel)
                self._mark_completed(novel_id, step_number, step_name)
                step_index += 1
            elif isinstance(confirmed, int):
                self._rollback(novel_id, confirmed)
                self.logger.warning(
                    "rollback_executed",
                    target_step=confirmed,
                    current_step=step_number,
                    deleted_range=f"{confirmed}-{step_number}",
                )
                step_index = confirmed - 1

        if step_index >= len(self.STEPS):
            self.logger.info(
                "workflow_complete",
                novel_id=novel_id,
                total_steps=len(self.STEPS),
            )

    def _present_plan(self, novel_id: str, step_number: int, step_name: str):
        """阶段一：展示执行计划"""
        print(f"\n{'='*60}")
        print(f"📝 将开始环节 {step_number:02d}/{len(self.STEPS)}: {step_name}")
        print(f"{'='*60}")

        deps = self._get_dependencies(step_name)
        print(f"\n📋 前置依赖:")
        for dep in deps:
            status = "✓ 已就绪" if self._has_data(novel_id, dep) else "○ 待生成"
            print(f"   {dep}: {status}")

        existing = self._get_existing_summary(novel_id, step_name)
        if existing:
            print(f"\n📂 已有数据:")
            print(f"   {existing}")
        else:
            print(f"\n📂 未有前置数据，将从零生成")

        print(f"\n📋 执行计划:")
        print(f"   1. 读取 {', '.join(deps[:3])} 数据")
        print(f"   2. 使用 {self._get_generation_rule(step_name)} 规则生成")
        print(f"   3. 执行质量审查并生成报告")
        print(f"   4. 同步到 user_view/ 可视化目录\n")

    def _wait_for_decision(self, step_name: str) -> Dict[str, Any]:
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
                return {"action": "skip"}
            elif cmd == "停止":
                return {"action": "stop"}
            elif cmd.startswith("修改"):
                modifications = cmd[2:].strip()
                if modifications:
                    return {"action": "modify", "modifications": [modifications]}
                else:
                    print("  请在「修改」后输入具体修改内容")
            else:
                print("  无法识别，请使用: 执行 / 修改 <内容> / 跳过 / 停止")

    def _execute_step(
        self,
        novel_id: str,
        step_number: int,
        step_name: str,
        module_path: str,
        modifications: Optional[List[str]] = None,
    ) -> Any:
        """阶段三：执行——带异常日志"""
        self.logger.info(
            "execute_start",
            module=module_path.split(".")[-1],
            modifications=modifications is not None,
        )
        try:
            context = self._build_context(novel_id, step_name)
            if modifications:
                context["user_modifications"] = modifications

            module_class = self._import_module(module_path)
            module = module_class()
            content = self._agent_generate(step_name, context)
            result = module.run(context, content)

            self.logger.info(
                "execute_end",
                module=module_path.split(".")[-1],
                success=result.success if hasattr(result, "success") else True,
            )
            return result
        except Exception as e:
            self.logger.error(
                "execute_exception",
                module=module_path,
                error=str(e),
                traceback=traceback.format_exc(),
            )
            raise

    def _agent_generate(self, step_name: str, context: Dict[str, Any]) -> Any:
        """Agent 内容生成——交互模式下提示用户输入 JSON 格式内容"""
        self.logger.info("agent_generate_start", step_name=step_name)

        expected_format = self._get_expected_format(step_name)
        print(f"\n{'='*60}")
        print(f"  ✍️  请输入【{step_name}】内容（JSON 格式）")
        print(f"{'='*60}")
        if expected_format:
            print(f"\n📋 数据格式参考:")
            for line in expected_format:
                print(f"   {line}")

        prompt_rules = self._load_step_prompt_rules(step_name)
        if prompt_rules:
            print(f"\n📐 逻辑约束规则（必须遵守）:")
            for line in prompt_rules:
                print(f"   {line}")

        print(f"\n💡 提示: 直接输入单行 JSON，或输入 `...` 开始多行输入")
        print(f"        输入空行结束多行输入")
        print(f"        输入 `/跳过` 跳过此环节")
        print(f"        输入 `/停止` 保存进度并退出")
        print()

        lines = []
        multi_line = False
        while True:
            line = input("  > ").strip()
            if line == "/跳过":
                self.logger.info("agent_generate_skipped", step_name=step_name)
                return {"generated_by": "agent", "step_name": step_name, "skip": True}
            if line == "/停止":
                raise KeyboardInterrupt()
            if line == "..." and not multi_line:
                multi_line = True
                continue
            if multi_line:
                if line == "":
                    break
                lines.append(line)
                continue
            if line:
                lines.append(line)
                break

        raw = "\n".join(lines)
        if len(raw.encode("utf-8")) > Config.MAX_USER_INPUT_LENGTH:
            print(f"  ⚠ 输入内容超过最大限制 ({Config.MAX_USER_INPUT_LENGTH // (1024*1024)}MB)，已截断")
            self.logger.warning(
                "agent_generate_truncated",
                step_name=step_name,
                original_bytes=len(raw.encode("utf-8")),
                max_bytes=Config.MAX_USER_INPUT_LENGTH,
            )
            raw = raw.encode("utf-8")[:Config.MAX_USER_INPUT_LENGTH].decode("utf-8", errors="ignore")
        try:
            import json
            content = json.loads(raw)
            self.logger.info("agent_generate_end", step_name=step_name, parsed=True)
            return content
        except json.JSONDecodeError as e:
            print(f"  ⚠ JSON 解析失败: {e}")
            print(f"  已作为纯文本内容返回")
            return {
                "generated_by": "agent",
                "step_name": step_name,
                "text": raw,
            }

    def _get_expected_format(self, step_name: str) -> List[str]:
        """返回环节期望的数据格式说明"""
        formats = {
            "灵感启动": [
                '{',
                '  "directions": [',
                '    { "title": "...", "concept": "...",',
                '      "innovation_score": 0.8, "summary": "...",',
                '      "emotional_potential": 0.7 }',
                '  ],',
                '  "theme": {',
                '    "surface_theme": "表层主题",',
                '    "deep_theme": "深层主题",',
                '    "emotional_hook": "情感钩子",',
                '    "theme_statement": "主题陈述",',
                '    "reverse_confirmation": "反向验证"',
                '  }',
                '}',
            ],
            "小说主题": [
                '{ "theme": {',
                '    "surface_theme": "...", "deep_theme": "...",',
                '    "emotional_hook": "...", "theme_statement": "...",',
                '    "reverse_confirmation": "..."',
                '  }',
                '}',
            ],
            "拟定大纲": [
                '{',
                '  "acts": [',
                '    { "title": "...", "description": "...",',
                '      "chapters": 200, "climax": "...",',
                '      "tone": "...", "key_events": ["..."] }',
                '  ],',
                '  "causal_chain": [',
                '    { "from_event": "A", "to_event": "B", "reason": "..." }',
                '  ],',
                '  "rhythm_map": [',
                '    { "chapter_range": "1-50", "pace": "舒缓/渐快/紧凑/紧张/高亢",',
                '      "tension": 0.5, "event_density": 0.5 }',
                '  ]',
                '}',
            ],
            "世界观设定": [
                '{ "dimensions": [',
                '    { "name": "维度名", "rules": [',
                '      { "description": "...", "scope": "...", "constraints": "..." }',
                '    ]}',
                '  ]',
                '}',
            ],
            "人物设定": [
                '{ "characters": [',
                '    {',
                '      "name": "...", "role": "主角/反派/关键配角/配角",',
                '      "layer1_identity": { "age": 18, "occupation": "...", "origin": "...", "status": "..." },',
                '      "layer2_psychology": { "personality": "MBTI", "motivation": "...",',
                '        "fear": "...", "desire": "...", "contradiction": "...",',
                '        "body_language_dictionary": { "高兴": ["..."], "愤怒": ["..."] } },',
                '      "layer3_ability": { "skills": ["..."], "knowledge_boundaries": {...} },',
                '      "layer4_special": { "secrets": ["..."], "cracks": ["..."], "quirks": ["..."] },',
                '      "weight": { "tier": "S/A/B", "arc_contribution": 0.9, ... }',
                '    }',
                '  ]',
                '}',
            ],
            "人物关系": [
                '{ "relations": [',
                '    { "char_a_name": "甲", "char_b_name": "乙",',
                '      "type": "师徒/宿敌/知己/同门/传承",',
                '      "strength": 0.8, "asymmetry": 0.2,',
                '      "history": "...", "trajectory": "..." }',
                '  ]',
                '}',
            ],
            "角色弧线": [
                '{ "arcs": [',
                '    { "char_name": "...", "arc_type": "成长型/转变型/觉醒型",',
                '      "start_state": "...", "catalyst_event": "...",',
                '      "change_process": "...", "end_state": "...",',
                '      "chapter_mapping": { "setup": "1-100", "rising": "101-400",',
                '        "climax": "401-550", "resolution": "551-600" } }',
                '  ]',
                '}',
            ],
            "势力设定": [
                '{ "factions": [',
                '    { "name": "...", "type": "正派/反派/中立",',
                '      "hierarchy": "...", "goals": "...", "resources": "...",',
                '      "doctrines": "...", "reputation": 0.8,',
                '      "members": [',
                '        { "char_name": "...", "role": "...", "rank": "..." }',
                '      ]',
                '    }',
                '  ]',
                '}',
            ],
        }
        return formats.get(step_name, [
            '{ "key": "value" }  # 自由格式 JSON',
            '不需要特定格式，Agent 会根据上下文自行推断',
        ])

    def _wait_for_confirmation(
        self,
        novel_id: str,
        step_number: int,
        step_name: str,
        result: Any,
        review: Any,
    ) -> Union[bool, int]:
        """阶段四：等待用户确认"""
        print(f"\n{'='*60}")
        print(f"✅ 环节 {step_number:02d}/{len(self.STEPS)} {step_name} 已完成")
        print(f"{'='*60}")

        result_summary = ""
        if hasattr(result, "summary"):
            result_summary = result.summary
        elif isinstance(result, dict):
            result_summary = result.get("summary", "")
        if result_summary:
            print(f"\n📊 执行摘要: {result_summary}")

        if review and hasattr(review, "score"):
            score_icon = "⭐" if review.score >= 0.8 else "⚡"
            print(f"\n{score_icon} 质量评分: {review.score:.2f}")
            if hasattr(review, "details") and review.details:
                print(f"   详情: {len(review.details)} 项检查")
                for d in review.details[:3]:
                    print(f"   - {d}")

        print(f"\n可用命令:")
        print(f"  [确认]         确认结果，进入下一环节")
        print(f"  [修改 ...]     提供修改方向后重新执行")
        print(f"  [重做]         重新执行当前环节")
        print(f"  [回到 <N>]     回退到指定环节 N（1-{step_number}）")
        print(f"  [停止]         保存进度并退出")

        while True:
            cmd = input("\n请输入命令 > ").strip()
            if cmd == "确认":
                return True
            elif cmd == "重做":
                return False
            elif cmd.startswith("回到"):
                try:
                    target = int(cmd[2:].strip())
                    if 1 <= target <= step_number:
                        return target
                    else:
                        print(f"  请输入 1 到 {step_number} 之间的数字")
                except (ValueError, IndexError):
                    print("  格式错误，请使用: 回到 <N>，例如「回到 3」")
            elif cmd.startswith("修改"):
                print("  🔄 已记录修改指令，将重新执行当前环节")
                return False
            elif cmd == "停止":
                return True
            else:
                print("  无法识别，请使用: 确认 / 修改 <内容> / 重做 / 回到 <N> / 停止")

    def _handle_review_result(
        self,
        result: ReviewResult,
        context: ReviewContext,
    ) -> str:
        """统一审查结果处理器

        返回值：
          "regenerate"    → 重做当前环节
          "continue"      → 继续后续流程
          "wait_for_user" → 等待用户决策后继续
        """
        if result.level == ReviewLevel.BLOCKER:
            detail = result.details[0] if result.details else "严重问题"
            suggestion = result.suggestions[0] if result.suggestions else "无"
            print(f"\n  ⛔ BLOCKER: {detail}")
            print(f"  建议: {suggestion}")
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
            print(f"\n  ⚠  CRITICAL: 发现问题，尝试自动修正...")
            if result.auto_fixes:
                for fix in result.auto_fixes:
                    fixer_id = fix.get("fixer_id") if isinstance(fix, dict) else fix.fixer_id
                    fixer = self.quality.fixers.get(fixer_id)
                    if fixer:
                        params = fix.get("params") if isinstance(fix, dict) else fix.params
                        description = fix.get("description") if isinstance(fix, dict) else fix.description
                        context.content = fixer.fix(context.content, params)
                        print(f"     ✓ {description}")
                return self._handle_review_result(
                    self.quality.review(context),
                    context,
                )
            else:
                print(f"  ⏸️  需要用户确认: {result.details[0] if result.details else '无详细信息'}")
                return "wait_for_user"

        elif result.level == ReviewLevel.WARNING:
            print(f"\n  ⚡ WARNING: {len(result.details)} 个建议")
            for s in result.suggestions:
                print(f"    建议: {s}")
            return "continue"

        else:
            print(f"\n  ✓ 审查通过（评分: {result.score:.2f}）")
            return "continue"

    def _rollback(self, novel_id: str, target_step: int):
        """回退操作——带级联删除"""
        self.logger.warning(
            "rollback_start",
            target_step=target_step,
            delete_range=f">= {target_step}",
        )
        print(f"  🗑️  回滚：删除环节 {target_step} 之后的数据...")

        step_table_map = {
            1: ["inspirations"],
            2: ["themes"],
            3: ["world_building", "world_rules"],
            4: ["characters"],
            5: ["factions"],
            6: ["items"],
            7: ["relations"],
            8: ["faction_relations"],
            9: ["char_faction_links"],
            10: ["character_arcs"],
            11: ["foreshadows"],
            12: ["outlines"],
            13: ["volumes", "volume_chapters"],
            14: ["detail_outlines"],
            15: ["archives"],
            16: ["synopses"],
            17: ["manuscripts"],
            18: ["review_results", "fix_logs"],
            19: ["review_results", "fix_logs"],
            20: [],
        }
        deleted_tables = []
        for step_num, tables in step_table_map.items():
            if step_num >= target_step:
                for table in tables:
                    try:
                        self.db.execute(
                            f"DELETE FROM {table} WHERE novel_id = ?",
                            (novel_id,),
                        )
                        deleted_tables.append(table)
                    except Exception as e:
                        self.logger.warning(
                            "rollback_table_skip",
                            table=table,
                            error=str(e),
                        )
        self.db.commit()
        self.logger.warning(
            "rollback_complete",
            target_step=target_step,
            deleted_tables=deleted_tables,
        )
        print(f"  ✓ 已回滚到环节 {target_step}（级联删除 {len(deleted_tables)} 张专有表）")

    def _build_context(self, novel_id: str, step_name: str) -> Dict[str, Any]:
        """从数据库构建上下文"""
        context: Dict[str, Any] = {
            "novel_id": novel_id,
            "step_name": step_name,
            "db_session": self.db,
            "dependencies": {},
            "content": "",
            "constraints": [],
            "user_modifications": None,
        }

        dep_keys = self._get_dependencies(step_name)
        for dep in dep_keys:
            dep_data = self._load_dependency_data(novel_id, dep)
            if dep_data:
                context["dependencies"][dep] = dep_data

        return context

    def _load_step_prompt_rules(self, step_name: str) -> List[str]:
        """加载当前步骤对应的 prompt 规则，提取关键约束行"""
        prompt_map = {
            "世界观设定": "world_building.md",
            "人物设定": "character.md",
            "势力设定": "faction.md",
            "人物-势力关联": "char_faction_bridge.md",
            "人物关系": "relation.md",
            "势力关系": "faction_relation.md",
            "物品库": "item.md",
            "伏笔追踪": "foreshadow.md",
            "分卷配置": "volume.md",
            "章节细纲": "detail_outline.md",
            "拟定大纲": "outline.md",
            "正文初稿": "manuscript_writer.md",
        }
        filename = prompt_map.get(step_name)
        if not filename:
            return []
        try:
            full_text = load_prompt(filename)
            if not full_text:
                return []
            lines = full_text.split("\n")
            rules = [l for l in lines if "必须" in l or "禁止" in l or "不得" in l or "规则" in l or "底线" in l]
            limited = []
            for r in rules:
                r = r.strip().strip("#").strip("-").strip()
                if r and len(r) > 5 and len(r) < 120:
                    limited.append(r)
                if len(limited) >= 12:
                    break
            if not limited:
                limited = [l.strip() for l in lines if l.strip() and len(l.strip()) > 10][:8]
            limited.insert(0, f"—— 来自 {filename} ——")
            return limited
        except Exception:
            return []

    def _load_novel(self, novel_id: str) -> NovelProxy:
        """从数据库加载小说项目"""
        try:
            novel_row = self.db.execute(
                text("SELECT id, title, current_step FROM novels WHERE id = :nid"),
                {"nid": novel_id},
            ).fetchone()
            if novel_row:
                return NovelProxy(
                    novel_id=novel_row[0],
                    title=novel_row[1],
                    current_step=novel_row[2] or 1,
                )
        except Exception as e:
            self.logger.warning("load_novel_fallback", error=str(e))

        return NovelProxy(novel_id=novel_id, title=f"小说_{novel_id}", current_step=1)

    def _save_novel(self, novel: NovelProxy):
        """保存小说进度到数据库"""
        try:
            self.db.execute(
                text("UPDATE novels SET current_step = :step WHERE id = :nid"),
                {"step": novel.current_step, "nid": novel.id},
            )
            self.db.commit()
        except Exception as e:
            self.logger.warning("save_novel_error", error=str(e))

    def _mark_skipped(self, novel_id: str, step_number: int, step_name: str):
        """标记环节已跳过"""
        try:
            self.db.execute(
                text("INSERT OR REPLACE INTO step_status (novel_id, step_number, step_name, status) VALUES (:nid, :step_no, :sname, 'skipped')"),
                {"nid": novel_id, "step_no": step_number, "sname": step_name},
            )
            self.db.commit()
            self.logger.info(
                "step_marked_skipped",
                step=f"{step_number:02d}",
                step_name=step_name,
            )
        except Exception as e:
            self.logger.warning("mark_skipped_error", error=str(e))

    def _mark_completed(self, novel_id: str, step_number: int, step_name: str):
        """标记环节已完成"""
        try:
            self.db.execute(
                text("INSERT OR REPLACE INTO step_status (novel_id, step_number, step_name, status) VALUES (:nid, :step_no, :sname, 'completed')"),
                {"nid": novel_id, "step_no": step_number, "sname": step_name},
            )
            self.db.commit()
            self.logger.info(
                "step_marked_completed",
                step=f"{step_number:02d}",
                step_name=step_name,
            )
        except Exception as e:
            self.logger.warning("mark_completed_error", error=str(e))

    def _get_dependencies(self, step_name: str) -> List[str]:
        """获取环节的依赖模块列表"""
        dep_map = {
            "灵感启动": [],
            "小说主题": ["灵感启动"],
            "世界观设定": ["小说主题"],
            "人物设定": ["世界观设定"],
            "势力设定": ["世界观设定"],
            "物品库": ["世界观设定"],
            "人物关系": ["人物设定"],
            "势力关系": ["势力设定"],
            "人物-势力关联": ["人物设定", "势力设定", "人物关系", "势力关系"],
            "角色弧线": ["人物设定", "人物关系", "人物-势力关联"],
            "伏笔追踪": ["人物设定", "势力设定", "物品库"],
            "拟定大纲": ["灵感启动", "小说主题", "世界观设定", "人物设定", "势力设定", "物品库", "人物关系", "势力关系", "人物-势力关联", "角色弧线", "伏笔追踪"],
            "分卷配置": ["拟定大纲"],
            "章节细纲": ["分卷配置", "世界观设定", "人物设定", "物品库", "伏笔追踪"],
            "小说档案": ["灵感启动", "小说主题", "世界观设定", "人物设定", "势力设定", "物品库", "人物关系", "势力关系", "人物-势力关联", "角色弧线", "伏笔追踪", "拟定大纲", "分卷配置", "章节细纲"],
            "小说简介": ["小说档案"],
            "正文初稿": ["章节细纲", "世界观设定", "人物设定", "物品库", "伏笔追踪"],
            "正文审核": ["正文初稿"],
            "正文修正": ["正文审核"],
            "导出发布": ["正文修正"],
        }
        return dep_map.get(step_name, [])

    def _has_data(self, novel_id: str, dep_name: str) -> bool:
        """检查依赖模块是否有数据"""
        table = self._STEP_TABLE_MAP.get(dep_name)
        if not table:
            return False
        try:
            row = self.db.execute(
                text(f"SELECT COUNT(1) FROM {validate_table_name(table)} WHERE novel_id = :nid"),
                {"nid": novel_id},
            ).fetchone()
            return row is not None and row[0] > 0
        except Exception:
            return False

    def _get_existing_summary(self, novel_id: str, step_name: str) -> str:
        """获取已有数据的摘要信息"""
        try:
            table = self._STEP_TABLE_MAP.get(step_name)
            if not table:
                return ""
            row = self.db.execute(
                text(f"SELECT COUNT(1) FROM {validate_table_name(table)} WHERE novel_id = :nid"),
                {"nid": novel_id},
            ).fetchone()
            count = row[0] if row else 0
            if count > 0:
                return f"已有 {count} 条记录"
            return ""
        except Exception:
            return ""

    def _get_generation_rule(self, step_name: str) -> str:
        """获取生成规则描述"""
        rules = {
            "灵感启动": "基于用户输入生成 3 个创新灵感方向",
            "小说主题": "从灵感方向中提炼核心主题",
            "世界观设定": "生成 8 维度世界观规则集",
            "人物设定": "生成四层人物档案",
            "势力设定": "生成势力组织设定",
            "物品库": "生成重要物品设定",
            "人物关系": "生成人物关系图谱",
            "势力关系": "生成势力关系网络",
            "人物-势力关联": "交叉验证角色与势力的一致性，生成关联映射",
            "角色弧线": "生成角色成长弧线",
            "伏笔追踪": "生成伏笔并注册到 ChromaDB",
            "拟定大纲": "基于所有设定生成三幕结构大纲含因果链",
            "分卷配置": "配置分卷和章节分配",
            "章节细纲": "生成每章详细大纲",
            "小说档案": "聚合所有设定和细纲生成小说档案",
            "小说简介": "生成小说简介和卖点",
            "正文初稿": "生成正文初稿",
            "正文审核": "执行四层质量审查",
            "正文修正": "根据审查意见修正正文",
            "导出发布": "导出完整小说文件",
        }
        return rules.get(step_name, "标准生成规则")

    def _load_dependency_data(self, novel_id: str, dep_name: str) -> Optional[List[Dict[str, Any]]]:
        """加载依赖模块的数据"""
        try:
            table = self._STEP_TABLE_MAP.get(dep_name)
            if not table:
                return None
            rows = self.db.execute(
                text(f"SELECT * FROM {validate_table_name(table)} WHERE novel_id = :nid"),
                {"nid": novel_id},
            ).fetchall()
            if rows:
                columns = [desc[0] for desc in self.db.description]
                return [dict(zip(columns, row)) for row in rows]
            return None
        except Exception as e:
            self.logger.warning("load_dependency_error", dep=dep_name, error=str(e))
            return None

    def _import_module(self, module_path: str) -> Any:
        """动态导入模块"""
        try:
            parts = module_path.split(".")
            class_name = parts[-1]
            module_name = ".".join(parts[:-1])
            module = importlib.import_module(f"src.{module_name}")
            return getattr(module, class_name)
        except (ImportError, AttributeError) as e:
            self.logger.error(
                "import_module_error",
                module_path=module_path,
                error=str(e),
            )
            raise

    def _purify_ai_traces(self, novel_id: str, text: str) -> Dict[str, Any]:
        """执行 AI 痕迹检测与清除，返回净化后的文本和问题列表"""
        try:
            from src.core.purifier.pipeline import PurificationPipeline
            pipeline = PurificationPipeline()
            result = pipeline.purify(text)
            return {
                "text": result.text if hasattr(result, "text") else text,
                "issues": list(result.issues) if hasattr(result, "issues") else [],
                "report": result.report if hasattr(result, "report") else "",
            }
        except Exception as e:
            self.logger.warning("ai_purify_error", error=str(e))
            return {"text": text, "issues": [], "report": ""}

    def _update_purified_text(self, novel_id: str, original_text: str, purified_text: str) -> bool:
        """将净化后的文本写回数据库 manuscripts 表"""
        if original_text == purified_text or not purified_text:
            return False
        try:
            manuscripts = self.db.execute(
                text("SELECT novel_id, chapter_number, scenes FROM manuscripts WHERE novel_id = :nid"),
                {"nid": novel_id},
            ).fetchall()
            for row in manuscripts:
                ch_num = row[1]
                scenes_json = row[2]
                if not scenes_json:
                    continue
                scenes = json.loads(scenes_json)
                changed = False
                for scene in scenes:
                    content = scene.get("content", "")
                    if content and content in original_text:
                        pos = original_text.find(content)
                        if pos >= 0:
                            purified_content = purified_text[pos:pos + len(content)]
                            if purified_content != content:
                                scene["content"] = purified_content
                                changed = True
                if changed:
                    self.db.execute(
                        text("UPDATE manuscripts SET scenes = :scenes WHERE novel_id = :nid AND chapter_number = :ch"),
                        {
                            "scenes": json.dumps(scenes, ensure_ascii=False),
                            "nid": novel_id,
                            "ch": ch_num,
                        },
                    )
            self.db.commit()
            self.logger.info("purified_text_written", novel_id=novel_id)
            return True
        except Exception as e:
            self.logger.warning("update_purified_text_error", error=str(e))
            self.db.rollback()
            return False

    def load_novel(self, novel_id: str) -> NovelProxy:
        """公开接口：加载小说"""
        return self._load_novel(novel_id)

    def create_novel(self, user_input: str) -> NovelProxy:
        """公开接口：创建新小说"""
        from src.utils.id_generator import generate_id
        novel_id = generate_id("NOV", "GLOBAL", self.db)
        title = user_input[:50] if len(user_input) > 50 else user_input
        try:
            self.db.execute(
                text("INSERT INTO novels (id, title, current_step, created_at) VALUES (:id, :title, 1, :now)"),
                {"id": novel_id, "title": title, "now": datetime.now().isoformat()},
            )
            self.db.commit()
        except Exception as e:
            self.logger.warning("create_novel_db_error", error=str(e))
        self.logger.info("novel_created", novel_id=novel_id, title=title)
        return NovelProxy(novel_id=novel_id, title=title)

    def save_progress(self):
        """保存进度（KeyboardInterrupt 时调用）"""
        try:
            self.db.commit()
            self.logger.info("progress_saved")
        except Exception as e:
            self.logger.warning("save_progress_error", error=str(e))
