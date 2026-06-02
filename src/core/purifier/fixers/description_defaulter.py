from __future__ import annotations

import random
from typing import Any, Dict, Optional


class DescriptionDefaulter:
    """描写模板修复器

    识别并替换常见的模板化描写。
    L1 自动修复级别。
    """

    TEMPLATES = {
        "阳光透过": "光从{where}洒落，{detail}",
        "微风拂过": "风{detail}",
        "空气中弥漫": "空气里{detail}",
        "映入眼帘": "{detail}",
        "深吸一口气": "{action}",
        "时间仿佛": "感觉{detail}",
        "无声的": "{detail}的",
        "轻轻地": "{action}",
        "缓缓地": "{action}",
        "默默地": "{action}",
        "静静地": "{action}",
        "渐渐地": "慢慢{action}",
    }

    REPLACEMENTS: Dict[str, list] = {
        "阳光透过": [
            "光从窗棂的缝隙间斜斜地洒落，在地板上拖出长长的光影",
            "阳光穿过稀疏的云层，在空气中形成一道道可见的光柱",
            "日光透过树冠的间隙，在路面投下斑驳的光点",
        ],
        "微风拂过": [
            "风贴着地面掠过，卷起几片枯叶打了个旋",
            "一阵风从敞开的窗户灌进来，吹得桌上的纸页哗哗作响",
            "风穿过巷子，带着远处饭菜的香气扑面而来",
        ],
        "空气中弥漫": [
            "空气里浮动着一种说不清道不明的气息，像是久未通风的旧房间",
            "空气里裹挟着潮湿的泥土味和青草的腥气",
            "空气仿佛凝固了一般，沉闷得让人喘不过气",
        ],
        "映入眼帘": [
            "出现在视线中的是",
            "他/她第一眼看到的是",
        ],
        "深吸一口气": [
            "长长地吸了一口气，仿佛要把周围的空气都抽空",
            "深深地呼吸，让冰冷的空气充满肺部",
        ],
        "时间仿佛": [
            "感觉周围的一切都慢了下来",
        ],
    }

    def fix(self, text: str, params: Optional[Dict[str, Any]] = None) -> str:
        """修复模板化描写

        策略：
        - 用更具体、独特的描写替换常见模板
        - 保留句式结构但注入具体细节
        """
        fixed = text
        for template, replacement_list in self.REPLACEMENTS.items():
            if template not in fixed:
                continue
            replacement = random.choice(replacement_list)
            fixed = fixed.replace(template, replacement, 1)

        return fixed

    def validate(self, text: str) -> bool:
        """检查是否需要修复"""
        hits = sum(1 for t in self.TEMPLATES if t in text)
        return hits >= 2