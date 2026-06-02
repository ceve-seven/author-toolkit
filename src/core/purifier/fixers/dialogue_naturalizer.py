from __future__ import annotations

import random
import re
from typing import Any, Dict, Optional


class DialogueNaturalizer:
    """对话自然化修复器

    将信息密集的、功能性的对话转化为自然交流。
    增加潜台词、停顿、动作描写和非语言信息。
    L2 半自动修复级别。
    """

    PAUSES = ["", "顿了顿，", "稍作停顿，", "沉吟片刻，", "沉默了一会儿，"]

    ACTIONS = [
        " forward",  # placeholder, will be replaced
    ]

    ACTION_MOVEMENTS = [
        "微微侧过头", "垂下眼帘", "抬起头来", "望向远方",
        "靠在椅背上", "向前倾了倾身", "双手交握", "手指轻轻敲着桌面",
        "端起杯子喝了一口", "整理了一下衣襟", "微微一笑", "皱了下眉头",
    ]

    def fix(self, text: str, params: Optional[Dict[str, Any]] = None) -> str:
        """修复对话的自然度

        策略：
        - 将信息密集的对话拆分，加入停顿
        - 在对话前后插入动作描写
        - 为长段对话添加潜台词标记
        """
        variant = params.get("variant", 0) if params else 0
        fixed = text

        dialogue_pattern = re.compile(r'([""])([^""]{20,})\1')

        def _naturalize(match: re.Match) -> str:
            content = match.group(2)
            quote = match.group(1)

            if len(content) < 20:
                return match.group(0)

            if len(content) > 60:
                mid = len(content) // 2
                pause = self.PAUSES[variant % len(self.PAUSES)]
                if pause:
                    parts = [
                        content[:mid],
                        pause,
                        content[mid:],
                    ]
                else:
                    parts = [content[:mid], "，", content[mid:]]
                content = "".join(parts)

            if variant % 2 == 0 and random.random() > 0.5:
                action = random.choice(self.ACTION_MOVEMENTS)
                return f"{quote}{content}{quote}，{action}"

            return f"{quote}{content}{quote}"

        fixed = dialogue_pattern.sub(_naturalize, fixed)

        return fixed

    def validate(self, text: str) -> bool:
        """检查是否需要修复"""
        dialogue_lines = re.findall(r'[""]([^""]{10,})[""]', text)
        if not dialogue_lines:
            return False

        info_markers = ["因为", "所以", "因此", "根据", "按照", "首先", "其次",
                         "你的任务是", "你需要", "你必须", "听好", "记住"]
        info_dense = sum(1 for line in dialogue_lines
                        if any(m in line for m in info_markers))
        ratio = info_dense / len(dialogue_lines) if dialogue_lines else 0
        return ratio > 0.7