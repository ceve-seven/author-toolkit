from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class QualityRule:
    """质量规则定义"""

    rule_id: str
    """规则唯一标识"""
    display_name: str
    """规则显示名称"""
    applies_to: List[str]
    """适用的模块列表"""
    level: str
    """审查级别: blocker / critical / warning / info"""
    priority: int
    """优先级（数值越小优先级越高）"""
    check_algorithm: str
    """检测算法的伪代码描述"""
    auto_fix: bool
    """是否支持自动修复"""
    fix_strategy: str = ""
    """自动修复策略描述"""
    description: str = ""
    """规则描述"""


class RuleRegistry:
    """质量规则注册表——管理所有质量规则的加载、查询和匹配"""

    def __init__(self):
        self._rules: Dict[str, QualityRule] = {}
        self._module_index: Dict[str, List[str]] = {}

    def register(self, rule: QualityRule):
        """注册一条规则"""
        self._rules[rule.rule_id] = rule
        for module in rule.applies_to:
            if module not in self._module_index:
                self._module_index[module] = []
            self._module_index[module].append(rule.rule_id)

    def register_from_file(self, filepath: str):
        """从 YAML 配置文件加载规则"""
        try:
            import yaml
            with open(filepath, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
        except (FileNotFoundError, ImportError):
            return

        if not config or "quality_rules" not in config:
            return

        for rule_id, rule_config in config["quality_rules"].items():
            rule = QualityRule(
                rule_id=rule_id,
                display_name=rule_config.get("display_name", rule_id),
                applies_to=rule_config.get("applies_to", []),
                level=rule_config.get("level", "info"),
                priority=rule_config.get("priority", 9),
                check_algorithm=rule_config.get("check_algorithm", ""),
                auto_fix=rule_config.get("auto_fix", False),
                fix_strategy=rule_config.get("fix_strategy", ""),
                description=rule_config.get("description", ""),
            )
            self.register(rule)

    def register_default_rules(self):
        """注册默认内置规则"""
        defaults = [
            QualityRule(
                rule_id="setting_consistency",
                display_name="设定一致性",
                applies_to=["manuscript", "fix_manuscript"],
                level="blocker",
                priority=1,
                check_algorithm=(
                    "1. 提取正文所有世界观实体引用\n"
                    "2. 对照 world_building 数据逐一验证\n"
                    "3. 冲突时标记位置 + 违反规则编号 + 冲突类型\n"
                    "4. 统计冲突总数，>0 时标记为 BLOCKER"
                ),
                auto_fix=False,
                description="确保正文中的设定描述与世界构建数据一致",
            ),
            QualityRule(
                rule_id="logic_chain_integrity",
                display_name="逻辑链完整性",
                applies_to=["outline", "manuscript"],
                level="blocker",
                priority=1,
                check_algorithm=(
                    "1. 提取因果链中所有 from_event → to_event 映射\n"
                    "2. 检查每个 to_event 是否至少有一个 from_event 前置\n"
                    "3. 检查是否有孤立事件（无因/无果）\n"
                    "4. 孤立事件 > 0 时标记为 BLOCKER"
                ),
                auto_fix=False,
                description="确保大纲因果链完整，无孤立事件",
            ),
            QualityRule(
                rule_id="literary_quality",
                display_name="文学质感",
                applies_to=["manuscript"],
                level="critical",
                priority=2,
                check_algorithm=(
                    "1. 计算句式波动系数（std/mean），阈值 0.3\n"
                    "2. 计算过渡词密度（次/千字），阈值 15\n"
                    "3. 检测情感标签出现次数，阈值 3\n"
                    "4. 检测信息密集型对话占比，阈值 70%\n"
                    "5. 检测常见描写模板命中数，阈值 2\n"
                    "6. 每项未达标 +1 issue，≥3 项时标记为 CRITICAL"
                ),
                auto_fix=True,
                fix_strategy="调用 AITracePurifier L1 自动修复器",
                description="检测 AI 写作的常见文学质量问题",
            ),
            QualityRule(
                rule_id="ai_trace_detection",
                display_name="AI 痕迹检测",
                applies_to=["manuscript", "fix_manuscript"],
                level="critical",
                priority=2,
                check_algorithm=(
                    "1. 调用 AITraceDetector.detect() 执行 6 大特征检测\n"
                    "2. 按 fix_level 分组（L1 自动/L2 半自动/L3 仅报告）\n"
                    "3. 若存在 L1 以外的问题 → CRITICAL\n"
                    "4. 所有问题均为 L1 → WARNING\n"
                    "5. 无问题 → INFO"
                ),
                auto_fix=True,
                fix_strategy="L1 自动执行修复器链，L2 生成 3 种方案供用户选择",
                description="检测 6 大 AI 痕迹特征并分级处理",
            ),
            QualityRule(
                rule_id="foreshadow_integrity",
                display_name="伏笔完整性",
                applies_to=["detail_outline", "manuscript"],
                level="critical",
                priority=2,
                check_algorithm=(
                    "1. 提取细纲/正文中所有 foreshadow_refs\n"
                    "2. 对照 foreshadows 表验证所有 ref 已注册\n"
                    "3. 检查主伏笔（importance > 0.7）是否已埋设\n"
                    "4. 未注册 ref > 0 时标记为 CRITICAL"
                ),
                auto_fix=False,
                description="确保正文中的伏笔引用有效且主伏笔齐全",
            ),
            QualityRule(
                rule_id="chapter_consistency",
                display_name="跨章节一致性",
                applies_to=["manuscript", "fix_manuscript"],
                level="critical",
                priority=2,
                check_algorithm=(
                    "1. 提取所有章节的角色出场记录\n"
                    "2. 检查角色状态是否与前一章一致\n"
                    "3. 检查时间线是否连续\n"
                    "4. 状态不一致 > 0 时标记为 CRITICAL"
                ),
                auto_fix=False,
                description="确保各章节间角色/时间/物品状态一致",
            ),
            QualityRule(
                rule_id="outline_quality",
                display_name="大纲质量审查",
                applies_to=["outline"],
                level="blocker",
                priority=1,
                check_algorithm=(
                    "1. 检查三幕结构完整性（3 幕齐全）\n"
                    "2. 检查章节数分配比例（20-30%/40-50%/20-30%）\n"
                    "3. 检查因果链非空\n"
                    "4. 比例偏差 > 10% 时标记为 BLOCKER"
                ),
                auto_fix=False,
                description="审查三幕结构、章节分配和因果链完整性",
            ),
            QualityRule(
                rule_id="world_building_five_layers",
                display_name="世界观五层审查",
                applies_to=["world_building"],
                level="blocker",
                priority=1,
                check_algorithm=(
                    "1. 主题适配审查\n"
                    "2. 规则自洽性审查\n"
                    "3. 结构完整性审查\n"
                    "4. 极端场景测试\n"
                    "5. 叙事压力审查"
                ),
                auto_fix=True,
                fix_strategy="主题适配→弱关联规则改造方案；规则自洽→裂缝填补方案",
                description="主题适配/规则自洽/结构完整/极端测试/叙事压力五层审查",
            ),
            QualityRule(
                rule_id="word_count_check",
                display_name="字数校验",
                applies_to=["manuscript"],
                level="warning",
                priority=3,
                check_algorithm=(
                    "1. 统计每章字数\n"
                    "2. 对照细纲预算检查是否在 80%-120% 范围内\n"
                    "3. 超出范围时标记为 WARNING"
                ),
                auto_fix=False,
                description="校验正文字数是否在细纲预算范围内",
            ),
        ]
        for rule in defaults:
            self.register(rule)

    def get_rule(self, rule_id: str) -> Optional[QualityRule]:
        """根据规则 ID 获取规则"""
        return self._rules.get(rule_id)

    def get_rules(self, module_name: str) -> List[QualityRule]:
        """获取指定模块适用的所有规则"""
        rule_ids = self._module_index.get(module_name, [])
        return [self._rules[rid] for rid in rule_ids if rid in self._rules]

    def get_rules_for_context(self, context: Any) -> List[QualityRule]:
        """根据上下文获取适用的规则"""
        step_name = ""
        if hasattr(context, "step_name"):
            step_name = context.step_name
        elif isinstance(context, dict):
            step_name = context.get("step_name", "")

        module_map = {
            "灵感启动": "theme",
            "小说主题": "theme",
            "拟定大纲": "outline",
            "世界观设定": "world_building",
            "人物设定": "character",
            "人物关系": "relation",
            "角色弧线": "character_arc",
            "势力设定": "faction",
            "势力关系": "faction_relation",
            "物品库": "item",
            "伏笔追踪": "foreshadow",
            "小说档案": "archive",
            "小说简介": "synopsis",
            "分卷配置": "volume",
            "章节细纲": "detail_outline",
            "正文初稿": "manuscript",
            "正文审核": "review",
            "正文修正": "fix_manuscript",
            "导出发布": "export",
        }

        mapped = module_map.get(step_name, step_name)
        return self.get_rules(mapped)

    def get_all_rules(self) -> List[QualityRule]:
        """获取所有已注册的规则"""
        return list(self._rules.values())

    def get_fixers(self) -> Dict[str, Dict[str, Any]]:
        """获取所有支持自动修复的规则信息"""
        fixer_map: Dict[str, Dict[str, Any]] = {}
        for rule in self._rules.values():
            if rule.auto_fix:
                fixer_map[rule.rule_id] = {
                    "display_name": rule.display_name,
                    "fix_strategy": rule.fix_strategy,
                    "level": rule.level,
                    "priority": rule.priority,
                }
        return fixer_map

    def count_rules(self) -> Dict[str, int]:
        """统计各级别的规则数量"""
        counts: Dict[str, int] = {"blocker": 0, "critical": 0, "warning": 0, "info": 0}
        for rule in self._rules.values():
            level = rule.level.lower()
            if level in counts:
                counts[level] += 1
        return counts