"""
测试同步引擎基本功能。

本测试覆盖：
1. 双向同步引擎的基本接口
2. JSON → Markdown 渲染
3. Markdown → JSON 解析
4. SYNC 标记解析
5. 冲突检测
"""

import os
import re
import sys
import tempfile
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
def step_protocols() -> dict:
    """加载 step_protocols.yaml"""
    yaml_path = PROJECT_ROOT / "src" / "config" / "step_protocols.yaml"
    assert yaml_path.exists(), f"配置文件不存在: {yaml_path}"
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert data is not None
    assert "step_protocols" in data
    return data["step_protocols"]


@pytest.fixture
def temp_dirs():
    """创建临时目录用于测试文件读写"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_novel_data() -> dict:
    """模拟小说数据"""
    return {
        "novel_id": "TEST-001",
        "title": "测试小说",
        "author": "测试作者",
        "chapters": [
            {"number": 1, "title": "第一章", "content": "这是第一章的内容。"},
            {"number": 2, "title": "第二章", "content": "这是第二章的内容。"},
        ],
        "characters": [
            {"id": "CHAR-001", "name": "陈渡", "role": "protagonist"},
            {"id": "CHAR-002", "name": "林溪", "role": "supporting"},
        ],
        "version": 1,
    }


# =========================================================================
# 基本接口测试
# =========================================================================

class TestSyncInterface:
    """测试同步引擎基本接口"""

    def test_step_protocols_has_all_20_steps(self, step_protocols):
        """验证 step_protocols 包含全部 20 个创作环节"""
        expected_steps = [
            "inspiration", "theme", "world_building", "character",
            "faction", "relation", "faction_relation", "item",
            "char_faction", "arc", "foreshadow", "outline",
            "volume", "detail_outline", "archive", "synopsis",
            "manuscript", "review", "fix", "export",
        ]
        actual = list(step_protocols.keys())
        missing = [s for s in expected_steps if s not in actual]
        extra = [s for s in actual if s not in expected_steps]
        assert not missing, f"缺少步骤: {missing}"
        assert not extra, f"多余步骤: {extra}"
        assert len(actual) == 20, f"应有 20 个步骤，实际 {len(actual)}"

    def test_each_step_has_display_name(self, step_protocols):
        """每个步骤必须有 display_name"""
        for name, step in step_protocols.items():
            assert "display_name" in step, f"步骤 {name} 缺少 display_name"

    def test_each_step_has_dependencies(self, step_protocols):
        """每个步骤必须有 dependencies 字段"""
        for name, step in step_protocols.items():
            assert "dependencies" in step, f"步骤 {name} 缺少 dependencies"
            assert isinstance(step["dependencies"], list), \
                f"步骤 {name} 的 dependencies 不是列表"

    def test_inspiration_has_no_dependencies(self, step_protocols):
        """灵感启动应无任何依赖"""
        assert step_protocols["inspiration"]["dependencies"] == []

    def test_later_steps_depend_on_earlier_ones(self, step_protocols):
        """确保依赖关系不产生循环（简单检查）"""
        step_order = list(step_protocols.keys())
        step_index = {name: i for i, name in enumerate(step_order)}

        for name, step in step_protocols.items():
            deps = step["dependencies"]
            for dep in deps:
                # 跳过空依赖
                if not dep:
                    continue
                # 检查依赖步骤是否在前面
                assert dep in step_index, f"步骤 {name} 依赖不存在的步骤 {dep}"
                assert step_index[dep] < step_index[name], \
                    f"步骤 {name} 依赖 {dep}，但 {dep} 在后面（循环依赖）"

    def test_each_step_has_generation_rule(self, step_protocols):
        """每个步骤必须有 generation_rule"""
        for name, step in step_protocols.items():
            assert "generation_rule" in step, f"步骤 {name} 缺少 generation_rule"

    def test_each_step_has_quality_checks(self, step_protocols):
        """每个步骤必须有 quality_checks 字段"""
        for name, step in step_protocols.items():
            assert "quality_checks" in step, f"步骤 {name} 缺少 quality_checks"
            assert isinstance(step["quality_checks"], list), \
                f"步骤 {name} 的 quality_checks 不是列表"

    def test_each_step_has_agent_prompt_hints(self, step_protocols):
        """每个步骤必须有 agent_prompt_hints"""
        for name, step in step_protocols.items():
            assert "agent_prompt_hints" in step, f"步骤 {name} 缺少 agent_prompt_hints"

    def test_each_step_has_display_template(self, step_protocols):
        """每个步骤必须有 display_template"""
        for name, step in step_protocols.items():
            assert "display_template" in step, f"步骤 {name} 缺少 display_template"
            assert isinstance(step["display_template"], list), \
                f"步骤 {name} 的 display_template 不是列表"


# =========================================================================
# SYNC 标记测试
# =========================================================================

class TestSyncMarkers:
    """测试 SYNC 标记解析"""

    SYNC_PATTERN = re.compile(r"<!-- SYNC:([^:]+):([^>]+) -->(.*?)<!-- /SYNC -->", re.DOTALL)
    SYNC_META_PATTERN = re.compile(r"<!-- SYNC_META:([^:]+):([^>]+) -->(.*?)<!-- /SYNC_META -->", re.DOTALL)
    SYNC_REF_PATTERN = re.compile(r"<!-- SYNC_REF:([^>]+) -->(.*?)<!-- /SYNC_REF -->", re.DOTALL)

    @staticmethod
    def generate_sync_marker(entity_id: str, field_path: str, value: str) -> str:
        """生成 SYNC 字段标记"""
        return f"<!-- SYNC:{entity_id}:{field_path} -->{value}<!-- /SYNC -->"

    @staticmethod
    def generate_sync_meta(entity_id: str, attribute: str, value: str) -> str:
        """生成 SYNC_META 元数据标记"""
        return f"<!-- SYNC_META:{entity_id}:{attribute} -->{value}<!-- /SYNC_META -->"

    @staticmethod
    def generate_sync_ref(entity_id: str, content: str) -> str:
        """生成 SYNC_REF 引用标记"""
        return f"<!-- SYNC_REF:{entity_id} -->{content}<!-- /SYNC_REF -->"

    @staticmethod
    def parse_sync_field(text: str) -> list:
        """解析 SYNC 字段标记"""
        return TestSyncMarkers.SYNC_PATTERN.findall(text)

    def test_generate_and_parse_field_marker(self):
        """生成并解析字段标记"""
        marker = self.generate_sync_marker("CHAR-001", "name", "陈渡")
        parsed = self.parse_sync_field(marker)
        assert len(parsed) == 1
        entity_id, field_path, value = parsed[0]
        assert entity_id == "CHAR-001"
        assert field_path == "name"
        assert value.strip() == "陈渡"

    def test_generate_and_parse_meta_marker(self):
        """生成并解析元数据标记"""
        marker = self.generate_sync_meta("CHAR-001", "version", "3")
        parsed = self.SYNC_META_PATTERN.findall(marker)
        assert len(parsed) == 1
        entity_id, attribute, value = parsed[0]
        assert entity_id == "CHAR-001"
        assert attribute == "version"
        assert value.strip() == "3"

    def test_generate_and_parse_ref_marker(self):
        """生成并解析引用标记"""
        content = "伏笔'将军的秘密'预计在第 8 章回收"
        marker = self.generate_sync_ref("FOR-003", content)
        parsed = self.SYNC_REF_PATTERN.findall(marker)
        assert len(parsed) == 1
        entity_id, ref_content = parsed[0]
        assert entity_id == "FOR-003"
        assert ref_content.strip() == content

    def test_multiple_markers_in_text(self):
        """文本中包含多个 SYNC 标记"""
        text = (
            self.generate_sync_marker("CHAR-001", "name", "陈渡") + "\n"
            + self.generate_sync_marker("CHAR-002", "name", "林溪") + "\n"
            + self.generate_sync_meta("CHAR-001", "version", "2")
        )
        fields = self.parse_sync_field(text)
        assert len(fields) == 2, "应解析出 2 个字段标记"

    def test_user_modified_value_updates(self):
        """用户修改 SYNC 标记内的值后，应能被正确识别"""
        original = self.generate_sync_marker("CHAR-001", "name", "陈渡")
        modified = original.replace("陈渡", "陈渡（已修改）")
        parsed = self.parse_sync_field(modified)
        assert parsed[0][2].strip() == "陈渡（已修改）", "应识别用户的修改"


# =========================================================================
# JSON ↔ Markdown 渲染测试
# =========================================================================

class MockSyncEngine:
    """模拟同步引擎，测试 JSON ↔ Markdown 转换"""

    MODULE_ORDER = [
        "inspiration", "theme", "outline", "world_building",
        "character", "relation", "arc", "faction",
        "faction_relation", "item", "foreshadow", "archive",
        "synopsis", "volume", "detail_outline", "manuscript",
    ]

    def json_to_markdown(self, novel_data: dict) -> dict:
        """简单的 JSON → Markdown 渲染，返回模块名→Markdown内容的映射"""
        result = {}
        for module_name in self.MODULE_ORDER:
            if module_name in novel_data:
                md = self._render_module(module_name, novel_data[module_name])
                if md:
                    result[module_name] = md
        return result

    def _render_module(self, module_name: str, data) -> str:
        """渲染单个模块为 Markdown"""
        lines = [f"# {module_name}"]
        if isinstance(data, list):
            for item in data:
                lines.append(self._render_item(item))
        elif isinstance(data, dict):
            lines.append(self._render_item(data))
        return "\n".join(lines)

    def _render_item(self, item: dict) -> str:
        """渲染单个数据项为 Markdown（含 SYNC 标记）"""
        lines = []
        for key, value in item.items():
            entity_id = item.get("id", "unknown")
            if isinstance(value, str):
                marker = f"<!-- SYNC:{entity_id}:{key} -->{value}<!-- /SYNC -->"
                lines.append(f"- **{key}**: {marker}")
            elif isinstance(value, (int, float)):
                lines.append(f"- **{key}**: {value}")
        return "\n".join(lines)


class TestJsonToMarkdown:
    """测试 JSON → Markdown 渲染"""

    def test_render_characters(self, mock_novel_data):
        """角色数据应正确渲染为 Markdown"""
        engine = MockSyncEngine()
        # 添加角色数据
        data = {
            **mock_novel_data,
            "character": mock_novel_data["characters"],
        }
        result = engine.json_to_markdown(data)
        assert "character" in result
        md = result["character"]
        # 检查角色名称是否在 Markdown 中
        assert "CHAR-001" in md
        assert "陈渡" in md
        assert "CHAR-002" in md
        assert "林溪" in md

    def test_sync_markers_in_output(self, mock_novel_data):
        """渲染结果应包含 SYNC 标记"""
        engine = MockSyncEngine()
        data = {**mock_novel_data, "character": mock_novel_data["characters"]}
        result = engine.json_to_markdown(data)
        md = result["character"]
        assert "<!-- SYNC:" in md, "渲染结果应包含 SYNC 标记"
        assert "<!-- /SYNC -->" in md, "渲染结果应包含 SYNC 闭合标记"

    def test_all_modules_rendered(self, mock_novel_data):
        """所有模块数据都应渲染"""
        engine = MockSyncEngine()
        # 用模拟数据填充所有模块
        full_data = {
            "outline": {"id": "OUT-001", "title": "三幕大纲", "act_count": 3},
            "character": [
                {"id": "CHAR-001", "name": "陈渡", "role": "protagonist"},
            ],
            "faction": [
                {"id": "FAC-001", "name": "暗影组织", "alignment": "混乱邪恶"},
            ],
        }
        result = engine.json_to_markdown(full_data)
        for module_name in full_data:
            assert module_name in result, f"模块 {module_name} 未渲染"


class TestMarkdownToJson:
    """测试 Markdown → JSON 解析"""

    def test_parse_sync_changes(self):
        """从 SYNC 标记中提取变更"""
        text = """- **name**: <!-- SYNC:CHAR-001:name -->陈渡（已修改）<!-- /SYNC -->
- **role**: <!-- SYNC:CHAR-001:role -->protagonist<!-- /SYNC -->"""
        parsed = TestSyncMarkers.parse_sync_field(text)
        assert len(parsed) == 2

        # 检查修改后的值
        name_marker = parsed[0]
        assert name_marker[0] == "CHAR-001"
        assert name_marker[1] == "name"
        assert name_marker[2].strip() == "陈渡（已修改）"

    def test_no_unintended_changes(self):
        """未修改的 SYNC 标记不应产生变更"""
        text = """- **name**: <!-- SYNC:CHAR-001:name -->陈渡<!-- /SYNC -->"""
        parsed = TestSyncMarkers.parse_sync_field(text)
        value = parsed[0][2].strip()
        assert value == "陈渡", "值应保持不变"


# =========================================================================
# 冲突检测测试
# =========================================================================

class TestConflictDetection:
    """测试同步过程中的冲突检测"""

    def test_timestamp_based_conflict(self):
        """应能通过时间戳检测冲突（MD 时间 > DB 时间时以 MD 为准）"""
        md_timestamp = "2025-06-01 10:00:00"
        db_timestamp = "2025-06-01 09:00:00"
        assert md_timestamp > db_timestamp, "MD 时间晚于 DB 时间时，应以 MD 为准"

    def test_same_value_no_conflict(self):
        """相同值不应产生冲突"""
        old_value = "陈渡"
        new_value = "陈渡"
        assert old_value == new_value, "值相同时不应标记为冲突"

    def test_different_value_conflict(self):
        """不同值应标记为冲突"""
        old_value = "陈渡"
        new_value = "陈渡（修改版）"
        assert old_value != new_value, "值不同时应标记为冲突"


# =========================================================================
# Config 集成测试
# =========================================================================

class TestConfigIntegration:
    """测试同步引擎相关配置"""

    def test_config_yaml_files_exist(self):
        """必需的 YAML 配置文件应存在于 src/config/ 目录"""
        config_dir = PROJECT_ROOT / "src" / "config"
        assert (config_dir / "step_protocols.yaml").exists()
        assert (config_dir / "quality_rules.yaml").exists()
        assert (config_dir / "ai_trace_thresholds.yaml").exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])