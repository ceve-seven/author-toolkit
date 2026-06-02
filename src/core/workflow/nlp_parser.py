from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class EditOp:
    """编辑操作——用户自然语言反馈的解析结果"""

    action: str
    """操作类型: adjust / replace / partial / regenerate / regenerate_all / pass_to_agent"""

    field: str = ""
    """涉及字段或模块名称"""

    value: str = ""
    """替换值（replace 操作使用）"""

    direction: str = ""
    """调整方向: increase / decrease（adjust 操作使用）"""

    keep: str = ""
    """保留部分（partial 操作使用）"""

    modify: str = ""
    """修改部分（partial 操作使用）"""

    original_feedback: str = ""
    """原始反馈文本（pass_to_agent 操作使用）"""

    context_summary: str = ""
    """上下文摘要（pass_to_agent 操作使用）"""


class NLPFeedbackParser:
    """自然语言反馈解析器

    将用户的模糊反馈解析为可执行的修改操作。
    解析器不做 LLM 调用。模板匹配失败时，
    将原始反馈通过 EditOp(action="pass_to_agent") 传递给 Agent 处理。
    """

    def __init__(self):
        self._templates = [
            (r"太(.+)了", self._handle_too_much),
            (r"不够(.+)", self._handle_not_enough),
            (r"把(.+)改成(.+)", self._handle_replace),
            (r"保留(.+)，修改(.+)", self._handle_partial),
            (r"保留(.+),修改(.+)", self._handle_partial),
            (r"重新(.+)", self._handle_regenerate),
            (r"再想想|重做|不满意|全部重做", self._handle_regenerate_all),
        ]

    def parse(self, feedback: str, context: Optional[Dict[str, Any]] = None) -> List[EditOp]:
        """解析用户反馈为可执行的编辑操作列表

        Args:
            feedback: 用户的自然语言反馈
            context: 上下文信息，包含 step_name 等

        Returns:
            编辑操作列表
        """
        feedback = feedback.strip()
        context = context or {}

        for pattern, handler in self._templates:
            match = re.search(pattern, feedback)
            if match:
                op = handler(match)
                if op:
                    return [op]

        return self._llm_parse(feedback, context)

    def _handle_too_much(self, match: re.Match) -> EditOp:
        """处理「太...了」模式 → 减少"""
        field = match.group(1).strip()
        return EditOp(
            action="adjust",
            field=field,
            direction="decrease",
        )

    def _handle_not_enough(self, match: re.Match) -> EditOp:
        """处理「不够...」模式 → 增加"""
        field = match.group(1).strip()
        return EditOp(
            action="adjust",
            field=field,
            direction="increase",
        )

    def _handle_replace(self, match: re.Match) -> EditOp:
        """处理「把...改成...」模式 → 替换"""
        target = match.group(1).strip()
        replacement = match.group(2).strip()
        return EditOp(
            action="replace",
            field=target,
            value=replacement,
        )

    def _handle_partial(self, match: re.Match) -> EditOp:
        """处理「保留...，修改...」模式 → 部分修改"""
        keep_part = match.group(1).strip()
        modify_part = match.group(2).strip()
        return EditOp(
            action="partial",
            keep=keep_part,
            modify=modify_part,
        )

    def _handle_regenerate(self, match: re.Match) -> EditOp:
        """处理「重新...」模式 → 重新生成指定部分"""
        field = match.group(1).strip()
        return EditOp(
            action="regenerate",
            field=field,
        )

    def _handle_regenerate_all(self, match: re.Match) -> EditOp:
        """处理「再想想/重做/不满意」模式 → 全部重做"""
        return EditOp(
            action="regenerate_all",
        )

    def _llm_parse(self, feedback: str, context: Dict[str, Any]) -> List[EditOp]:
        """模板未匹配时，将原始反馈传递给 Agent 处理"""
        return [
            EditOp(
                action="pass_to_agent",
                original_feedback=feedback,
                context_summary=context.get("step_name", ""),
            )
        ]

    def describe_ops(self, ops: List[EditOp]) -> str:
        """将编辑操作列表转换为可读的描述文本"""
        if not ops:
            return "无操作"

        descriptions = {
            "adjust": lambda op: f"调整「{op.field}」: {'增加' if op.direction == 'increase' else '减少'}",
            "replace": lambda op: f"将「{op.field}」替换为「{op.value}」",
            "partial": lambda op: f"保留「{op.keep}」，修改「{op.modify}」",
            "regenerate": lambda op: f"重新生成「{op.field}」",
            "regenerate_all": lambda _: "全部重新生成",
            "pass_to_agent": lambda op: f"传递给 Agent 处理: {op.original_feedback[:50]}...",
        }

        parts = []
        for op in ops:
            desc_fn = descriptions.get(op.action, lambda _: f"未知操作: {op.action}")
            parts.append(desc_fn(op))

        return "；".join(parts)