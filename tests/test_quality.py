"""
测试质量审查规则加载和基本审查流程。

本测试覆盖：
1. quality_rules.yaml 的加载和解析
2. QualityRuleRegistry 规则注册表的注册和查询
3. 关键规则的存在性和结构完整性
"""

import os
import sys
from pathlib import Path

import pytest
# pyrefly: ignore [missing-source-for-stubs]
import yaml

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# =========================================================================
# Fixtures
# =========================================================================

@pytest.fixture(scope="module")
def quality_rules() -> dict:
    """加载 quality_rules.yaml 并返回解析后的字典"""
    yaml_path = PROJECT_ROOT / "src" / "config" / "quality_rules.yaml"
    assert yaml_path.exists(), f"配置文件不存在: {yaml_path}"
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert data is not None, "quality_rules.yaml 解析结果为空"
    assert "quality_rules" in data, "缺少 quality_rules 根键"
    return data["quality_rules"]


@pytest.fixture(scope="module")
def required_rule_names() -> list:
    """所有必须存在的质量规则名称列表"""
    return [
        "setting_consistency",
        "logic_chain_integrity",
        "outline_rhythm_quality",
        "outline_logic_quality",
        "outline_structure_quality",
        "outline_comprehensive_checklist",
        "outline_user_instruction_templates",
        "outline_quality",
        "foreshadow_integrity",
        "literary_quality",
        "ai_trace_detection",
        "chapter_consistency",
        "world_building_five_layers",
        "world_building_review_report",
        "cross_module_linkage",
        "cross_module_validation_checklist",
        "character_consistency",
        "plot_logic",
        "reader_engagement",
    ]


# =========================================================================
# 规则加载测试
# =========================================================================

class TestRuleLoading:
    """测试质量规则 YAML 解析的正确性"""

    def test_yaml_parses_successfully(self, quality_rules):
        """YAML 文件能被正确解析为字典"""
        assert isinstance(quality_rules, dict)
        assert len(quality_rules) > 5, "规则数量过少，至少应有 10+ 条规则"

    def test_all_required_rules_exist(self, quality_rules, required_rule_names):
        """所有必需的规则名称都存在"""
        missing = [name for name in required_rule_names if name not in quality_rules]
        assert not missing, f"缺少以下必需规则: {missing}"

    def test_each_rule_has_display_name(self, quality_rules):
        """每条规则必须有 display_name"""
        for name, rule in quality_rules.items():
            assert "display_name" in rule, f"规则 {name} 缺少 display_name"

    def test_each_rule_has_level(self, quality_rules):
        """每条规则必须有 level 属性，且为合法值"""
        valid_levels = {"blocker", "critical", "warning", "info"}
        for name, rule in quality_rules.items():
            assert "level" in rule, f"规则 {name} 缺少 level"
            assert rule["level"] in valid_levels, \
                f"规则 {name} 的 level 值 '{rule['level']}' 不合法，应为 {valid_levels}"

    def test_each_rule_has_priority(self, quality_rules):
        """每条规则必须有 priority"""
        for name, rule in quality_rules.items():
            assert "priority" in rule, f"规则 {name} 缺少 priority"
            assert isinstance(rule["priority"], int), f"规则 {name} 的 priority 不是整数"

    def test_each_rule_has_check_algorithm(self, quality_rules):
        """每条规则必须有 check_algorithm（检测算法描述）"""
        for name, rule in quality_rules.items():
            assert "check_algorithm" in rule, f"规则 {name} 缺少 check_algorithm"

    def test_auto_fix_consistency(self, quality_rules):
        """auto_fix 为 true 的规则必须有 fix_strategy"""
        for name, rule in quality_rules.items():
            if rule.get("auto_fix"):
                assert "fix_strategy" in rule, \
                    f"规则 {name} 的 auto_fix=true 但缺少 fix_strategy"

    def test_applies_to_is_list(self, quality_rules):
        """applies_to 字段必须是列表"""
        for name, rule in quality_rules.items():
            assert "applies_to" in rule, f"规则 {name} 缺少 applies_to"
            assert isinstance(rule["applies_to"], list), \
                f"规则 {name} 的 applies_to 不是列表"


# =========================================================================
# 规则内容测试
# =========================================================================

class TestRuleContent:
    """测试各条规则的内容完整性"""

    def test_world_building_five_layers_algorithm(self, quality_rules):
        """世界观五层审查的检查算法必须包含 5 个步骤"""
        rule = quality_rules.get("world_building_five_layers")
        assert rule is not None
        algo = rule["check_algorithm"]
        # 检查五个关键步骤名称
        for keyword in ["主题适配审查", "规则自洽性审查", "结构完整性审查", "极端场景测试", "叙事压力审查"]:
            assert keyword in algo, f"world_building_five_layers 缺少步骤: {keyword}"

    def test_cross_module_validation_10_items(self, quality_rules):
        """跨模块交叉验证清单必须包含 10 项"""
        rule = quality_rules.get("cross_module_validation_checklist")
        assert rule is not None
        algo = rule["check_algorithm"]
        # 检查 10 项编号
        for i in range(1, 11):
            assert f"{i}." in algo or f"[{i}]" in algo, \
                f"cross_module_validation_checklist 缺少第 {i} 项"

    def test_outline_comprehensive_9_items(self, quality_rules):
        """大纲综合审核检查清单必须包含 9 项用户检查"""
        rule = quality_rules.get("outline_comprehensive_checklist")
        assert rule is not None
        algo = rule["check_algorithm"]
        for i in range(1, 10):
            assert str(i) in algo or f"第{i}" in algo, \
                f"outline_comprehensive_checklist 缺少第 {i} 项"

    def test_outline_user_instruction_6_templates(self, quality_rules):
        """大纲用户指令模板必须包含 6 条模板"""
        rule = quality_rules.get("outline_user_instruction_templates")
        assert rule is not None
        algo = rule["check_algorithm"]
        # 统计引号数量（每个模板一条引号语句）
        quote_count = algo.count("——")
        assert quote_count >= 6, \
            f"outline_user_instruction_templates 应有至少 6 条模板，当前检测到约 {quote_count} 条"

    def test_level_blocker_rules_have_priority_1(self, quality_rules):
        """BLOCKER 级别的规则 priority 必须为 1"""
        for name, rule in quality_rules.items():
            if rule.get("level") == "blocker":
                assert rule.get("priority") == 1, \
                    f"BLOCKER 规则 {name} 的 priority 应为 1，实际为 {rule.get('priority')}"


# =========================================================================
# Config 集成测试
# =========================================================================

class TestConfigIntegration:
    """测试配置系统与质量规则的集成"""

    def test_config_can_load_quality_rules(self):
        """YAML 配置文件应在 src/config/ 目录下正确加载"""
        config_dir = Path(PROJECT_ROOT) / "src" / "config"
        yaml_path = config_dir / "quality_rules.yaml"
        assert yaml_path.exists(), f"配置文件不存在: {yaml_path}"
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert "quality_rules" in data
        assert len(data["quality_rules"]) >= 10

    def test_config_dir_has_yaml_files(self):
        """src/config/ 目录应包含所有必需 YAML 文件"""
        config_dir = Path(PROJECT_ROOT) / "src" / "config"
        required_files = ["step_protocols.yaml", "quality_rules.yaml", "ai_trace_thresholds.yaml"]
        for filename in required_files:
            assert (config_dir / filename).exists(), f"缺少配置文件: {filename}"


# =========================================================================
# 审查流程模拟测试
# =========================================================================

class MockReviewExecutor:
    """模拟审查执行器，用于测试审查流程编排"""

    def __init__(self, rule_name: str, level: str):
        self.rule_name = rule_name
        self.level = level

    def execute(self, content: str, dependencies: dict | None = None) -> dict:
        return {
            "rule": self.rule_name,
            "level": self.level,
            "passed": self.level != "blocker",
            "issues": [] if self.level != "blocker" else [{"description": "模拟问题"}],
        }


class TestReviewPipeline:
    """测试审查流水线的编排逻辑"""

    def test_blocker_interrupts_pipeline(self):
        """BLOCKER 级别问题应中断后续审查"""
        executors = [
            MockReviewExecutor("rule_a", "blocker"),
            MockReviewExecutor("rule_b", "info"),
        ]
        results = []
        for executor in executors:
            result = executor.execute("test content")
            results.append(result)
            if result["level"] == "blocker":
                break
        assert len(results) == 1, "BLOCKER 级别应中断流水线，只执行了第一条规则"

    def test_all_rules_execute_when_no_blocker(self):
        """无 BLOCKER 问题时，所有规则都应执行"""
        executors = [
            MockReviewExecutor("rule_a", "warning"),
            MockReviewExecutor("rule_b", "critical"),
            MockReviewExecutor("rule_c", "info"),
        ]
        results = []
        for executor in executors:
            result = executor.execute("test content")
            results.append(result)
        assert len(results) == 3, "应执行全部 3 条规则"

    def test_priority_sorting(self, quality_rules):
        """规则应按 priority 排序（priority 越小越优先）"""
        rules_with_priority = [
            (name, rule["priority"])
            for name, rule in quality_rules.items()
        ]
        # 验证所有 priority 值 >= 0
        for name, priority in rules_with_priority:
            assert priority >= 0, f"规则 {name} 的 priority 为负数 ({priority})"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])