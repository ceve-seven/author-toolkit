from __future__ import annotations

from typing import Any, Dict, Optional

from src.core.quality.fixers.base_fixer import BaseFixer


class EmotionShowingFixer(BaseFixer):
    """情感展示修正器——将抽象情感描述转化为具体行为展示"""

    EMOTION_LABELS = ["感到", "觉得", "心中充满", "内心", "感受到", "体会到"]

    EMOTION_ACTIONS: Dict[str, list] = {
        "愤怒": ["攥紧拳头，指节发白", "呼吸变得急促而沉重", "额角青筋隐隐跳动",
                 "声音低沉得像是从胸腔深处挤出", "眼神冰冷如刀"],
        "悲伤": ["眼眶不受控制地发红", "肩膀微微颤抖着", "声音哽咽得几乎说不出话",
                 "久久地站在那里，一言不发", "泪水在眼眶里打转"],
        "喜悦": ["嘴角不自觉地上扬", "眼睛里闪烁着光芒", "步伐变得轻快起来",
                 "笑声清脆得像风铃", "整个人都舒展了开来"],
        "恐惧": ["脸色唰地变得苍白", "手心里全是冷汗", "不由自主地后退了半步",
                 "心跳快得像要跳出胸腔", "声音带着细微的颤抖"],
        "惊讶": ["猛地瞪大了眼睛", "张了张嘴，却发不出声音", "愣在原地好一会儿",
                 "难以置信地摇了摇头", "眉头紧锁，陷入沉思"],
        "焦虑": ["不停地搓着手指", "在房间里来回踱步", "频繁地看着时间",
                 "咬着下唇，眉头紧锁", "坐立不安地变换着姿势"],
    }

    def fix(self, content: str, params: Optional[Dict[str, Any]] = None) -> str:
        """修正情感表达方式

        策略：
        - 将「感到+情感」替换为具体行为描述
        - 将「觉得+看法」替换为更具体的思考过程
        """
        variant = params.get("variant", 0) if params else 0
        fixed = content

        replacements = [
            ("感到愤怒", self._pick("愤怒", variant)),
            ("感到悲伤", self._pick("悲伤", variant)),
            ("感到喜悦", self._pick("喜悦", variant)),
            ("感到害怕", self._pick("恐惧", variant)),
            ("感到恐惧", self._pick("恐惧", variant)),
            ("感到惊讶", self._pick("惊讶", variant)),
            ("感到焦虑", self._pick("焦虑", variant)),
            ("心中充满愤怒", self._pick("愤怒", variant) + "。"),
            ("心中充满悲伤", self._pick("悲伤", variant) + "。"),
            ("心中充满喜悦", self._pick("喜悦", variant) + "。"),
            ("内心充满恐惧", self._pick("恐惧", variant) + "。"),
            ("内心充满焦虑", self._pick("焦虑", variant) + "。"),
        ]

        for old, new in replacements:
            fixed = fixed.replace(old, new)

        for label in self.EMOTION_LABELS:
            count = fixed.count(label)
            if count > 1:
                fixed = fixed.replace(label, "", count - 1)

        return fixed

    def _pick(self, emotion: str, variant: int) -> str:
        """根据变体索引选择对应的行为描述"""
        actions = self.EMOTION_ACTIONS.get(emotion, ["感到" + emotion])
        idx = variant % len(actions)
        return actions[idx]

    def validate(self, content: str) -> bool:
        """检查是否需要修正"""
        count = sum(content.count(w) for w in self.EMOTION_LABELS)
        return count > 3