"""utils 模块单元测试"""
from src.utils import validate_table_name, VALID_TABLES


class TestValidateTableName:
    def test_valid_table_names(self):
        for name in ["novels", "characters", "themes", "manuscripts", "step_status"]:
            assert validate_table_name(name) == name

    def test_invalid_table_name_raises(self):
        try:
            validate_table_name("evil_table; DROP TABLE novels--")
            assert False, "should raise ValueError"
        except ValueError as e:
            assert "非法表名" in str(e)

    def test_invalid_table_name_hint(self):
        try:
            validate_table_name("novel")
            assert False, "should raise ValueError"
        except ValueError as e:
            assert "您是不是想查" in str(e)

    def test_all_valid_tables_pass(self):
        for name in VALID_TABLES:
            assert validate_table_name(name) == name


class TestIdGenerator:
    def setup_method(self):
        from src.utils.id_generator import _counter_cache
        _counter_cache.clear()

    def test_generate_id_cache_only(self):
        from src.utils.id_generator import generate_id
        id1 = generate_id("CHAR", "GLOBAL")
        id2 = generate_id("CHAR", "GLOBAL")
        assert id1 == "CHAR-001"
        assert id2 == "CHAR-002"

    def test_generate_id_different_prefixes(self):
        from src.utils.id_generator import generate_id
        char_id = generate_id("CHAR", "GLOBAL")
        nov_id = generate_id("NOV", "GLOBAL")
        assert char_id.startswith("CHAR-")
        assert nov_id.startswith("NOV-")

    def test_generate_id_different_novels(self):
        from src.utils.id_generator import generate_id
        id_a = generate_id("CHAR", "NOV-001")
        id_b = generate_id("CHAR", "NOV-002")
        assert id_a == "CHAR-001"
        assert id_b == "CHAR-001"

    def test_peek_next_id(self):
        from src.utils.id_generator import generate_id, peek_next_id
        generate_id("FORE", "GLOBAL")
        next_id = peek_next_id("FORE", "GLOBAL")
        assert next_id == "FORE-002"

    def test_reset_counter(self):
        from src.utils.id_generator import generate_id, reset_counter
        generate_id("ITEM", "GLOBAL")
        generate_id("ITEM", "GLOBAL")
        reset_counter("ITEM", "GLOBAL")
        id_after = generate_id("ITEM", "GLOBAL")
        assert id_after == "ITEM-001"
