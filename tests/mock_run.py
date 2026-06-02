"""
端到端 Mock 数据运行脚本
模拟 AI Agent 为 20 个创作环节生成内容，验证每个模块能否正确处理数据。
用法: python -m tests.mock_run
"""
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import Config
from sqlalchemy import text
from src.storage.database.engine import get_engine, get_session
from src.storage.vector_store.chroma_client import get_chroma_client
from src.utils.logger_config import setup_logging
from src.utils.id_generator import generate_id
from src.core.modules.registry import get_registry


logger = setup_logging()


def build_mock_context(novel_id, db_session, chroma_client, dependencies=None):
    return {
        "novel_id": novel_id,
        "db_session": db_session,
        "chroma_client": chroma_client,
        "dependencies": dependencies or {},
        "user_modifications": None,
    }


def get_module(name):
    cls = get_registry().get(name)
    if cls is None:
        raise ValueError(f"模块 '{name}' 未注册")
    return cls()


def log_step(step_num, module_name, result):
    status = "✅" if result.success else "❌"
    print(f"  {status} [{step_num:02d}] {module_name}: {result.summary}")
    if result.errors:
        for err in result.errors:
            print(f"       ⚠ 错误: {err}")
    return result.success


def main():
    print("=" * 60)
    print("  AI 小说创作系统 - Mock 数据端到端测试")
    print("=" * 60)
    print()

    # ========== 1. 初始化基础设施 ==========
    print("📦 [00] 初始化系统...")
    engine = get_engine()
    # 注意：不使用 init_db()（ORM 表列名与模块 SQL 不兼容），
    # 所有表直接用模块兼容的列名创建
    with engine.connect() as conn:
        conn.execute(text("PRAGMA foreign_keys=OFF"))
        conn.execute(text("DROP TABLE IF EXISTS world_rules"))
        conn.execute(text("DROP TABLE IF EXISTS world_building"))
        conn.execute(text("DROP TABLE IF EXISTS characters"))
        conn.execute(text("DROP TABLE IF EXISTS relations"))
        conn.execute(text("DROP TABLE IF EXISTS character_arcs"))
        conn.execute(text("DROP TABLE IF EXISTS faction_members"))
        conn.execute(text("DROP TABLE IF EXISTS factions"))
        conn.execute(text("DROP TABLE IF EXISTS faction_relations"))
        conn.execute(text("DROP TABLE IF EXISTS items"))
        conn.execute(text("DROP TABLE IF EXISTS foreshadow_density_snapshots"))
        conn.execute(text("DROP TABLE IF EXISTS foreshadows"))
        conn.execute(text("DROP TABLE IF EXISTS volume_chapters"))
        conn.execute(text("DROP TABLE IF EXISTS volumes"))
        conn.execute(text("DROP TABLE IF EXISTS detail_outlines"))
        conn.execute(text("DROP TABLE IF EXISTS manuscripts"))
        conn.execute(text("DROP TABLE IF EXISTS fix_logs"))
        conn.execute(text("DROP TABLE IF EXISTS change_log"))
        conn.execute(text("DROP TABLE IF EXISTS review_results"))
        conn.execute(text("DROP TABLE IF EXISTS step_data"))
        conn.execute(text("DROP TABLE IF EXISTS char_faction_links"))
        conn.execute(text("DROP TABLE IF EXISTS synopses"))
        conn.execute(text("DROP TABLE IF EXISTS archives"))
        conn.execute(text("DROP TABLE IF EXISTS outlines"))
        conn.execute(text("DROP TABLE IF EXISTS themes"))
        conn.execute(text("DROP TABLE IF EXISTS inspirations"))
        conn.execute(text("DROP TABLE IF EXISTS id_counters"))
        conn.execute(text("DROP TABLE IF EXISTS novels"))
        conn.commit()
    # 用模块兼容的列名创建所有表
    with engine.connect() as conn:
        conn.execute(text("PRAGMA foreign_keys=OFF"))
        # --- 基础设施表 ---
        conn.execute(text("""
            CREATE TABLE novels (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                author TEXT,
                current_step INTEGER DEFAULT 1,
                status TEXT DEFAULT '创作中',
                created_at TEXT,
                updated_at TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE id_counters (
                novel_id TEXT,
                prefix TEXT,
                current_value INTEGER DEFAULT 0,
                PRIMARY KEY (novel_id, prefix)
            )
        """))
        # --- 步骤 01-02: 灵感 & 主题 ---
        conn.execute(text("""
            CREATE TABLE inspirations (
                novel_id TEXT, direction_id TEXT,
                title TEXT, concept TEXT, innovation_score REAL,
                summary TEXT, emotional_potential REAL,
                created_at TEXT,
                PRIMARY KEY (novel_id, direction_id)
            )
        """))
        conn.execute(text("""
            CREATE TABLE themes (
                novel_id TEXT, id INTEGER PRIMARY KEY AUTOINCREMENT,
                surface_theme TEXT, deep_theme TEXT, emotional_hook TEXT,
                theme_statement TEXT, reverse_confirmation TEXT
            )
        """))
        # --- 步骤 03: 三幕大纲 ---
        conn.execute(text("""
            CREATE TABLE outlines (
                novel_id TEXT, id INTEGER PRIMARY KEY AUTOINCREMENT,
                acts TEXT, causal_chain TEXT, rhythm_map TEXT
            )
        """))
        # --- 步骤 04: 世界观 ---
        conn.execute(text("""
            CREATE TABLE world_building (
                novel_id TEXT, dimension_name TEXT, rules TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE world_rules (
                novel_id TEXT, rule_id TEXT, dimension TEXT,
                description TEXT, scope TEXT, constraints TEXT,
                PRIMARY KEY (novel_id, rule_id)
            )
        """))
        # --- 步骤 05: 角色 ---
        conn.execute(text("""
            CREATE TABLE characters (
                novel_id TEXT, char_id TEXT, name TEXT, role TEXT,
                layer1_json TEXT, layer2_json TEXT,
                layer3_json TEXT, layer4_json TEXT,
                weight_tier TEXT, weight_score REAL, weight_json TEXT,
                PRIMARY KEY (novel_id, char_id)
            )
        """))
        # --- 步骤 06: 关系 ---
        conn.execute(text("""
            CREATE TABLE relations (
                novel_id TEXT, relation_id TEXT,
                char_a_id TEXT, char_b_id TEXT,
                type TEXT, strength REAL, asymmetry REAL,
                history TEXT, trajectory TEXT,
                PRIMARY KEY (novel_id, relation_id)
            )
        """))
        # --- 步骤 07: 角色弧光 ---
        conn.execute(text("""
            CREATE TABLE character_arcs (
                novel_id TEXT, char_id TEXT, arc_type TEXT,
                start_state TEXT, catalyst_event TEXT,
                change_process TEXT, end_state TEXT, chapter_mapping TEXT
            )
        """))
        # --- 步骤 08: 势力 ---
        conn.execute(text("""
            CREATE TABLE factions (
                novel_id TEXT, faction_id TEXT, name TEXT, type TEXT,
                hierarchy TEXT, goals TEXT, resources TEXT,
                doctrines TEXT, reputation REAL,
                PRIMARY KEY (novel_id, faction_id)
            )
        """))
        conn.execute(text("""
            CREATE TABLE faction_members (
                novel_id TEXT, faction_id TEXT, char_id TEXT, role TEXT, rank TEXT,
                PRIMARY KEY (novel_id, faction_id, char_id)
            )
        """))
        # --- 步骤 09: 势力关系 ---
        conn.execute(text("""
            CREATE TABLE faction_relations (
                novel_id TEXT, relation_id TEXT,
                faction_a_id TEXT, faction_b_id TEXT,
                type TEXT, strength REAL,
                history TEXT, treaties TEXT, hidden_agenda TEXT,
                PRIMARY KEY (novel_id, relation_id)
            )
        """))
        # --- 步骤 10: 人物-势力关联 ---
        conn.execute(text("""
            CREATE TABLE char_faction_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                novel_id TEXT, char_id TEXT, faction_id TEXT,
                membership_type TEXT, join_chapter INTEGER,
                leave_chapter INTEGER, role_in_faction TEXT,
                loyalty REAL, notes TEXT
            )
        """))
        # --- 步骤 11: 物品 ---
        conn.execute(text("""
            CREATE TABLE items (
                novel_id TEXT, item_id TEXT, name TEXT, type TEXT,
                purpose TEXT, background_story TEXT,
                restrictions TEXT, current_owner TEXT,
                significance_to_plot TEXT, first_appearance_chapter INTEGER,
                PRIMARY KEY (novel_id, item_id)
            )
        """))
        # --- 步骤 12: 伏笔 ---
        conn.execute(text("""
            CREATE TABLE foreshadows (
                novel_id TEXT, foreshadow_id TEXT,
                type TEXT, status TEXT,
                plant_chapter INTEGER, plant_location TEXT, plant_form TEXT,
                reveal_chapter_planned INTEGER, reveal_chapter_actual INTEGER,
                reveal_form TEXT, payload TEXT, surface TEXT, depth TEXT,
                related_char TEXT, related_item TEXT, related_plot TEXT,
                parent_fore TEXT, child_fores TEXT, tags TEXT,
                importance REAL, chroma_id TEXT,
                created_at TEXT, last_modified TEXT,
                PRIMARY KEY (novel_id, foreshadow_id)
            )
        """))
        conn.execute(text("""
            CREATE TABLE foreshadow_density_snapshots (
                novel_id TEXT, chapter INTEGER, active_count INTEGER,
                density_per_kword REAL, new_count INTEGER, resolved_count INTEGER
            )
        """))
        # --- 步骤 13: 卷配置 ---
        conn.execute(text("""
            CREATE TABLE volumes (
                novel_id TEXT, volume_id TEXT, name TEXT, chapter_range TEXT,
                boundary_gravity TEXT, pacing TEXT, major_conflict TEXT,
                character_focus TEXT, themes TEXT, cliffhanger TEXT,
                volume_rhythm_curve TEXT, volume_rhythm_evaluation TEXT,
                PRIMARY KEY (novel_id, volume_id)
            )
        """))
        conn.execute(text("""
            CREATE TABLE volume_chapters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                novel_id TEXT, volume_id TEXT, chapter_number INTEGER,
                pov_character TEXT, summary TEXT, word_count_budget INTEGER
            )
        """))
        # --- 步骤 13: 详细大纲 ---
        conn.execute(text("""
            CREATE TABLE detail_outlines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                novel_id TEXT, chapter_number INTEGER,
                chapter_constraint_summary TEXT, scenes TEXT
            )
        """))
        # --- 步骤 15: 档案 ---
        conn.execute(text("""
            CREATE TABLE archives (
                novel_id TEXT, id INTEGER PRIMARY KEY AUTOINCREMENT,
                layer1_identity_card TEXT, layer2_core_summary TEXT,
                layer3_module_snapshots TEXT, updated_at TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE change_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                novel_id TEXT, timestamp TEXT, step TEXT, module TEXT,
                action TEXT, entity_id TEXT, entity_type TEXT,
                summary TEXT, changed_fields TEXT
            )
        """))
        # --- 步骤 14: 简介 ---
        conn.execute(text("""
            CREATE TABLE synopses (
                novel_id TEXT, id INTEGER PRIMARY KEY AUTOINCREMENT,
                one_liner TEXT, short_blurb TEXT, standard_blurb TEXT,
                long_blurb TEXT, core_conflict TEXT, world_highlight TEXT,
                selling_points TEXT, target_audience TEXT, tone_tags TEXT,
                comparison_titles TEXT, hook_question TEXT,
                word_count INTEGER, last_synced_at TEXT, stale_status TEXT
            )
        """))
        # --- 步骤 17-18: 正文 & 修复 ---
        conn.execute(text("""
            CREATE TABLE manuscripts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                novel_id TEXT, chapter_number INTEGER,
                title TEXT, compiled_constraint_file TEXT,
                scenes TEXT, word_count INTEGER,
                transition_fixes TEXT, status TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE fix_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                novel_id TEXT, chapter_number INTEGER, fix_type TEXT,
                issue_ref TEXT, original_summary TEXT,
                fixed_summary TEXT, timestamp TEXT
            )
        """))
        # --- 步骤 18: 审校 ---
        conn.execute(text("""
            CREATE TABLE review_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                novel_id TEXT, step_number INTEGER, module_name TEXT,
                level TEXT, score REAL, details TEXT,
                suggestions TEXT, created_at TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE step_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                novel_id TEXT, step_number INTEGER, module_name TEXT,
                status TEXT, data TEXT, created_at TEXT
            )
        """))
        conn.commit()
    chroma_client = get_chroma_client()
    registry = get_registry()
    registry.initialize()
    print(f"     数据库: {Config.SQLITE_PATH}")
    print(f"     ChromaDB: {Config.CHROMADB_PATH}")
    modules = registry.list_modules()
    print(f"     模块注册: {len(modules)} 个模块")

    # ========== 2. 创建测试小说 ==========
    with get_session() as session:
        with session.begin():
            novel_id = generate_id("NOV", "GLOBAL", session)
            session.execute(
                text("""
                    INSERT OR REPLACE INTO novels
                    (id, title, current_step, status, created_at, updated_at)
                    VALUES (:id, :title, :current_step, :status, :created_at, :updated_at)
                """),
                {
                    "id": novel_id,
                    "title": "星穹之下",
                    "current_step": 1,
                    "status": "创作中",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
            )
    print(f"     ✅ 测试小说创建成功: ID={novel_id}, 标题='星穹之下'")
    print()

    # ========== 3. 主流程 ==========
    # 收集所有步骤的结果，供后续步骤引用
    all_results = {}
    char_id_map = {}  # 角色名 → ID
    mock_chapters = []  # 用于步骤17/19共享

    print("🚀 [开始] 模拟 20 个创作环节运行")
    print("-" * 60)

    # ------ 步骤 01: ThemeEngine（灵感启动） ------
    with get_session() as session:
        with session.begin():
            module = get_module("theme_engine")
            ctx = build_mock_context(novel_id, session, chroma_client)
            content = {
                "directions": [
                    {
                        "title": "星际文明的重生之路",
                        "concept": "文明崩溃后，幸存者在星空中寻找新的生存之道",
                        "innovation_score": 0.85,
                        "summary": "融合硬科幻与东方哲学，探讨文明韧性的科幻史诗",
                        "emotional_potential": 0.75,
                    },
                    {
                        "title": "记忆与身份的量子谜题",
                        "concept": "当记忆可以被编辑和交易，人的身份认同将面临怎样的挑战",
                        "innovation_score": 0.78,
                        "summary": "赛博朋克背景下的身份认同悬疑故事",
                        "emotional_potential": 0.82,
                    },
                    {
                        "title": "古老预言与星际殖民的碰撞",
                        "concept": "一个被遗忘的预言在星际殖民时代被重新发现，揭示宇宙的真相",
                        "innovation_score": 0.72,
                        "summary": "融合神话元素与太空歌剧的冒险故事",
                        "emotional_potential": 0.68,
                    },
                ],
                "theme": {
                    "surface_theme": "在浩瀚星空中寻找希望之光",
                    "deep_theme": "文明的韧性不在于技术的高度，而在于人性的温度",
                    "emotional_hook": "当家园毁灭，你是选择沉沦还是成为他人的希望？",
                    "theme_statement": "本小说探讨在极端环境下，人性如何定义文明的边界",
                    "reverse_confirmation": "如果反过来，人性将摧毁文明而非拯救文明，故事同样成立",
                },
            }
            result = module.run(ctx, content)
            log_step(1, "theme_engine", result)
            all_results["theme_engine"] = result.data

    # ------ 步骤 02: ThemeEngine（小说主题深化） ------
    with get_session() as session:
        with session.begin():
            module = get_module("theme_engine")
            ctx = build_mock_context(novel_id, session, chroma_client, all_results)
            content = {
                "theme": {
                    "surface_theme": "在浩瀚星空中寻找希望之光",
                    "deep_theme": "文明的韧性不在于技术的高度，而在于人性的温度",
                    "emotional_hook": "当家园毁灭，你是选择沉沦还是成为他人的希望？",
                    "theme_statement": "本小说探讨在极端环境下，人性如何定义文明的边界",
                    "reverse_confirmation": "如果反过来，人性将摧毁文明而非拯救文明，故事同样成立",
                },
                "sub_themes": [
                    {"name": "家园与归属", "core_question": "什么才是真正的家园？是土地还是人心？"},
                    {"name": "牺牲与守护", "core_question": "为了守护所爱之人，你愿意牺牲到什么程度？"},
                ],
            }
            result = module.run(ctx, content)
            log_step(2, "theme_engine(主题深化)", result)
            all_results["dialog_theme"] = result.data

    # ------ 步骤 03: OutlineBuilder（拟定大纲） ------
    with get_session() as session:
        with session.begin():
            module = get_module("outline_builder")
            ctx = build_mock_context(novel_id, session, chroma_client, all_results)
            content = {
                "acts": [
                    {
                        "title": "启程",
                        "chapters": 8,
                        "key_events": [
                            "地球危机爆发",
                            "星舰启航",
                            "首次跃迁事故",
                            "发现未知信号",
                        ],
                        "description": "地球资源枯竭，主角带领幸存者踏上星际征途",
                    },
                    {
                        "title": "探索",
                        "chapters": 12,
                        "key_events": [
                            "抵达陌生星系",
                            "遭遇外星文明遗迹",
                            "内部叛变",
                            "发现预言石板",
                        ],
                        "description": "在陌生星系中探索，面临内忧外患",
                    },
                    {
                        "title": "抉择",
                        "chapters": 10,
                        "key_events": [
                            "预言真相大白",
                            "最终决战",
                            "文明新生的代价",
                            "希望的种子",
                        ],
                        "description": "真相浮出水面，主角必须做出最终抉择",
                    },
                ],
                "causal_chain": [
                    {"from_event": "地球危机爆发", "to_event": "星舰启航", "cause_type": "直接因果"},
                    {"from_event": "星舰启航", "to_event": "首次跃迁事故", "cause_type": "转折"},
                    {"from_event": "首次跃迁事故", "to_event": "发现未知信号", "cause_type": "铺垫"},
                    {"from_event": "抵达陌生星系", "to_event": "遭遇外星文明遗迹", "cause_type": "直接因果"},
                    {"from_event": "遭遇外星文明遗迹", "to_event": "发现预言石板", "cause_type": "伏笔"},
                    {"from_event": "发现预言石板", "to_event": "预言真相大白", "cause_type": "铺垫"},
                    {"from_event": "内部叛变", "to_event": "最终决战", "cause_type": "间接因果"},
                ],
                "rhythm_map": [
                    {"chapter_range": [1, 3], "pace": "缓", "purpose": "世界观铺垫"},
                    {"chapter_range": [4, 6], "pace": "急", "purpose": "冲突爆发"},
                    {"chapter_range": [7, 8], "pace": "缓", "purpose": "情感沉淀"},
                    {"chapter_range": [9, 12], "pace": "急", "purpose": "探索高潮"},
                    {"chapter_range": [13, 16], "pace": "缓", "purpose": "谜团揭示"},
                    {"chapter_range": [17, 20], "pace": "急", "purpose": "最终决战"},
                    {"chapter_range": [21, 22], "pace": "缓", "purpose": "尾声余韵"},
                ],
            }
            result = module.run(ctx, content)
            log_step(3, "outline_builder", result)
            all_results["outline_builder"] = result.data

    # ------ 步骤 04: WorldBuilder（世界观设定） ------
    with get_session() as session:
        with session.begin():
            module = get_module("world_builder")
            ctx = build_mock_context(novel_id, session, chroma_client, all_results)
            dimensions_data = {
                "物理规则": [
                    {"description": "超光速跃迁只能在特定空间节点进行", "scope": "星际旅行", "constraints": "节点位置每 72 小时变动一次"},
                    {"description": "重力场强度影响时间流速", "scope": "时空物理", "constraints": "强重力场区域时间流速减慢 50%"},
                ],
                "地理空间": [
                    {"description": "银河系分为三大星域：联邦核心区、边缘区域、未知领域", "scope": "星际地理", "constraints": "未知领域被强辐射带包围"},
                    {"description": "每个宜居行星都有独特的生态系统", "scope": "行星生态", "constraints": "跨行星生态移植成功率低于 10%"},
                ],
                "时间历史": [
                    {"description": "公元 3000 年，人类文明进入星际时代", "scope": "历史背景", "constraints": "旧地球纪元的科技文献大量遗失"},
                    {"description": "银河战争纪元前 500 年，存在一个高度发达的先驱文明", "scope": "远古历史", "constraints": "先驱文明的遗迹带有量子保护机制"},
                ],
                "社会结构": [
                    {"description": "星际联邦实行议会制，由主要殖民星球的代表组成", "scope": "政治体制", "constraints": "核心星球拥有否决权"},
                    {"description": "殖民星球分为三个等级，等级决定资源分配权", "scope": "社会等级", "constraints": "等级每十年评估一次"},
                ],
                "文化习俗": [
                    {"description": "星际航行者的传统：出发前举行星火仪式", "scope": "航行文化", "constraints": "仪式必须在恒星光芒照耀下进行"},
                    {"description": "各殖民星球保留独特节日，统一使用星际标准历法", "scope": "节日习俗", "constraints": "星球本地日与标准日有差异"},
                ],
                "科技水平": [
                    {"description": "反物质引擎是主流星际航行技术", "scope": "动力技术", "constraints": "反物质提取成本极高"},
                    {"description": "量子通讯实现跨星系实时信息传递", "scope": "通讯技术", "constraints": "量子纠缠对数量有限"},
                ],
                "魔法/超自然体系": [
                    {"description": "部分人类拥有「星感」能力，可感知空间波动", "scope": "超感知", "constraints": "星感能力会随年龄增长衰退"},
                    {"description": "先驱文明留下的「共鸣石」可与特定基因序列产生共鸣", "scope": "超自然物品", "constraints": "共鸣者必须通过精神试炼"},
                ],
                "经济体系": [
                    {"description": "星际通用货币为「星币」，基于能源单位定价", "scope": "货币体系", "constraints": "星币汇率由星际能源委员会调控"},
                    {"description": "稀有矿产和古代遗物是主要的高价值贸易品", "scope": "贸易体系", "constraints": "古代遗物交易需联邦特别许可"},
                ],
            }
            content = {
                "dimensions": [
                    {"name": dim_name, "rules": rules}
                    for dim_name, rules in dimensions_data.items()
                ]
            }
            result = module.run(ctx, content)
            log_step(4, "world_builder", result)
            all_results["world_builder"] = result.data

    # ------ 步骤 05: CharacterBuilder（人物设定） ------
    with get_session() as session:
        with session.begin():
            module = get_module("character_builder")
            ctx = build_mock_context(novel_id, session, chroma_client, all_results)
            char_id_01 = generate_id("CHAR", novel_id, session)
            char_id_02 = generate_id("CHAR", novel_id, session)
            char_id_03 = generate_id("CHAR", novel_id, session)
            char_id_04 = generate_id("CHAR", novel_id, session)
            char_id_map["林星辰"] = char_id_01
            char_id_map["苏月"] = char_id_02
            char_id_map["罗教授"] = char_id_03
            char_id_map["维拉"] = char_id_04

            content = {
                "characters": [
                    {
                        "id": char_id_01,
                        "name": "林星辰",
                        "role": "主角",
                        "layer1_identity": {"age": 32, "occupation": "星舰舰长", "origin": "地球·东亚联合区", "status": "前地球防卫军上校"},
                        "layer2_psychology": {
                            "personality": "INFJ",
                            "motivation": "寻找人类新家园",
                            "fear": "无法保护所爱之人",
                            "desire": "建立一个不再重复地球错误的新文明",
                            "contradiction": "理性决策者与感性守护者的内心冲突",
                            "body_language_dictionary": {
                                "高兴": ["嘴角微微上扬", "眼神变得柔和"],
                                "愤怒": ["拳头紧握指节发白", "声音压低变得沙哑"],
                                "悲伤": ["凝视远方沉默不语", "手指轻轻颤抖"],
                                "恐惧": ["瞳孔微微收缩", "呼吸变得急促"],
                                "惊讶": ["眉毛猛然抬高", "身体微微后倾"],
                            },
                        },
                        "layer3_ability": {
                            "skills": ["星际航行", "战术指挥", "谈判", "应急医疗"],
                            "knowledge_boundaries": {
                                "knows": ["星际联邦法规", "古代文明传说"],
                                "not_knows": ["先驱文明语言的完整解读", "自身星感能力的真正渊源"],
                                "partial_knows": ["共鸣石的秘密"],
                            },
                        },
                        "layer4_special": {
                            "secrets": ["林星辰是最后的共鸣石守护者后裔"],
                            "cracks": ["过度自责倾向", "难以信任他人", "对地球毁灭有幸存者愧疚"],
                            "quirks": ["总是在重要决定前抚摸胸前的吊坠", "习惯用星图来平复情绪"],
                        },
                        "weight": {
                            "tier": "S",
                            "arc_contribution": 0.95,
                            "plot_driving": 0.90,
                            "theme_carrying": 0.85,
                            "network_centrality": 0.88,
                        },
                    },
                    {
                        "id": char_id_02,
                        "name": "苏月",
                        "role": "关键配角",
                        "layer1_identity": {"age": 28, "occupation": "星舰首席科学官", "origin": "火星·奥林匹斯城", "status": "天体物理学博士"},
                        "layer2_psychology": {
                            "personality": "INTP",
                            "motivation": "揭开宇宙的真相",
                            "fear": "科学无法解释一切",
                            "desire": "证明古代预言的科学依据",
                            "contradiction": "理性科学家与对未知的浪漫向往",
                            "body_language_dictionary": {
                                "高兴": ["眼睛发亮加快语速", "不自觉地比划手势"],
                                "愤怒": ["冷着脸不说话", "笔直地站着双臂交叉"],
                                "悲伤": ["低头玩手指", "声音变得很轻"],
                                "恐惧": ["咬住下唇", "眼神游离不定"],
                                "惊讶": ["手中的数据板差点滑落", "张着嘴说不出话"],
                            },
                        },
                        "layer3_ability": {
                            "skills": ["天体物理", "量子计算", "古代文字破译", "数据分析"],
                            "knowledge_boundaries": {
                                "knows": ["量子通讯原理", "星际航行动力学"],
                                "not_knows": ["先驱文明语言的全部语法", "共鸣石的量子态本质"],
                                "partial_knows": ["预言石板的初步解读"],
                            },
                        },
                        "layer4_special": {
                            "secrets": ["苏月的祖母是最后一位接触过先驱文明的地球人"],
                            "cracks": ["过度沉迷研究忽视人际关系", "有轻微的强迫倾向"],
                            "quirks": ["思考时会无意识地在桌上画公式", "紧张时会哼一首古老的曲子"],
                        },
                        "weight": {
                            "tier": "A",
                            "arc_contribution": 0.78,
                            "plot_driving": 0.72,
                            "theme_carrying": 0.65,
                            "network_centrality": 0.70,
                        },
                    },
                    {
                        "id": char_id_03,
                        "name": "罗教授",
                        "role": "配角",
                        "layer1_identity": {"age": 58, "occupation": "星际考古学家", "origin": "月球·第谷基地", "status": "星际联邦科学院院士"},
                        "layer2_psychology": {
                            "personality": "ESTJ",
                            "motivation": "保护古代文明遗产",
                            "fear": "古代智慧被滥用",
                            "desire": "建立星际文明档案馆",
                            "contradiction": "学者的理想主义与现实政治的妥协",
                            "body_language_dictionary": {
                                "高兴": ["爽朗大笑拍拍对方肩膀", "眼睛眯成一条缝"],
                                "愤怒": ["脸色涨红声音发抖", "用力拍桌子"],
                                "悲伤": ["深深叹气", "闭上眼睛久久不语"],
                                "恐惧": ["身体僵直", "额头上冒出冷汗"],
                                "惊讶": ["摘下眼镜擦了擦", "难以置信地摇头"],
                            },
                        },
                        "layer3_ability": {
                            "skills": ["考古学", "古代语言", "文明学", " diplomacy"],
                            "knowledge_boundaries": {
                                "knows": ["已知所有古代文明的兴衰史"],
                                "not_knows": ["先驱文明的真正目的", "共鸣石的制造方法"],
                                "partial_knows": ["古代预言的不同版本"],
                            },
                        },
                        "layer4_special": {
                            "secrets": ["罗教授曾私下保存了一块共鸣石碎片"],
                            "cracks": ["过于固执己见", "对新技术有排斥心理"],
                            "quirks": ["收集各个文明的文字样本", "喝茶时必须用地球带来的陶瓷杯"],
                        },
                        "weight": {
                            "tier": "A",
                            "arc_contribution": 0.65,
                            "plot_driving": 0.60,
                            "theme_carrying": 0.70,
                            "network_centrality": 0.55,
                        },
                    },
                    {
                        "id": char_id_04,
                        "name": "维拉",
                        "role": "反派",
                        "layer1_identity": {"age": 35, "occupation": "星际军阀", "origin": "半人马座·α基地", "status": "边缘星域的实际掌控者"},
                        "layer2_psychology": {
                            "personality": "ENTP",
                            "motivation": "用任何手段确保族群的生存",
                            "fear": "被联邦出卖和抛弃",
                            "desire": "建立独立于联邦的星际帝国",
                            "contradiction": "残酷手段背后的守护之心",
                            "body_language_dictionary": {
                                "高兴": ["嘴角勾起一抹冷笑", "眼神变得更加锐利"],
                                "愤怒": ["周围的温度仿佛降低", "一字一顿地说话"],
                                "悲伤": ["仰头喝干一杯酒", "转过身背对所有人"],
                                "恐惧": ["面色不变但握枪的手在抖", "呼吸变得极其平稳"],
                                "惊讶": ["挑了一下眉毛", "沉默了三秒钟"],
                            },
                        },
                        "layer3_ability": {
                            "skills": ["战略指挥", "格斗术", "政治权谋", "地下网络"],
                            "knowledge_boundaries": {
                                "knows": ["边缘星域所有秘密航线", "联邦的暗面"],
                                "not_knows": ["共鸣石的真正力量", "自己身世的真相"],
                                "partial_knows": ["先驱文明的军事科技"],
                            },
                        },
                        "layer4_special": {
                            "secrets": ["维拉体内有先驱文明的基因改造"],
                            "cracks": ["偏执多疑", "无法建立真正的信任关系"],
                            "quirks": ["在做出重大决定前会独自看星云图", "从不背对任何人"],
                        },
                        "weight": {
                            "tier": "A",
                            "arc_contribution": 0.72,
                            "plot_driving": 0.80,
                            "theme_carrying": 0.68,
                            "network_centrality": 0.75,
                        },
                    },
                ]
            }
            result = module.run(ctx, content)
            log_step(5, "character_builder", result)
            all_results["character_builder"] = result.data
            # 注入角色ID用于后续步骤
            all_results["character_builder"]["char_id_map"] = char_id_map

    # ------ 步骤 06: RelationBuilder（人物关系） ------
    with get_session() as session:
        with session.begin():
            module = get_module("relation_builder")
            ctx = build_mock_context(novel_id, session, chroma_client, all_results)
            content = {
                "relations": [
                    {
                        "char_a_id": char_id_01, "char_b_id": char_id_02,
                        "type": "alliance", "strength": 0.85, "asymmetry": 0.1,
                        "history": [{"event": "共同经历首次跃迁事故", "impact": "建立了生死信任"}],
                        "trajectory": ["专业合作", "私人信任", "精神共鸣"],
                    },
                    {
                        "char_a_id": char_id_01, "char_b_id": char_id_03,
                        "type": "mentorship", "strength": 0.75, "asymmetry": 0.2,
                        "history": [{"event": "罗教授曾是林星辰的导师", "impact": "师生情谊深厚"}],
                        "trajectory": ["师生", "平等合作", "理念分歧"],
                    },
                    {
                        "char_a_id": char_id_01, "char_b_id": char_id_04,
                        "type": "enmity", "strength": 0.88, "asymmetry": 0.4,
                        "history": [{"event": "维拉曾伏击林星辰的护航舰队", "impact": "结下深仇"}],
                        "trajectory": ["敌对", "被迫合作", "亦敌亦友"],
                    },
                    {
                        "char_a_id": char_id_02, "char_b_id": char_id_03,
                        "type": "mentorship", "strength": 0.70, "asymmetry": 0.15,
                        "history": [{"event": "科学研究合作", "impact": "学术上的互相欣赏"}],
                        "trajectory": ["学术合作", "共同研究"],
                    },
                ]
            }
            result = module.run(ctx, content)
            log_step(6, "relation_builder", result)
            all_results["relation_builder"] = result.data

    # ------ 步骤 07: ArcBuilder（角色弧线） ------
    with get_session() as session:
        with session.begin():
            module = get_module("arc_builder")
            ctx = build_mock_context(novel_id, session, chroma_client, all_results)
            content = {
                "arcs": [
                    {
                        "char_id": char_id_01,
                        "arc_type": "成长弧",
                        "start_state": {"status": "背负着地球毁灭的幸存者愧疚", "belief": "必须完美地保护每一个人"},
                        "catalyst_event": "跃迁事故中不得不做出放弃部分船员的艰难决定",
                        "change_process": [
                            {"phase": "拒绝", "chapter": 2, "behavior": "自责与回避"},
                            {"phase": "挣扎", "chapter": 5, "behavior": "在理性与感性间摇摆"},
                            {"phase": "接受", "chapter": 9, "behavior": "认识到牺牲有时不可避免"},
                            {"phase": "升华", "chapter": 14, "behavior": "将愧疚转化为更坚定的使命感"},
                        ],
                        "end_state": {"status": "成为一个懂得守护也懂得放手的真正领袖", "belief": "保护的意义在于让被保护者也有成长的机会"},
                        "chapter_mapping": [2, 5, 9, 14],
                    },
                    {
                        "char_id": char_id_04,
                        "arc_type": "转变弧",
                        "start_state": {"status": "以强硬手段统治的军阀", "belief": "只有力量才能确保生存"},
                        "catalyst_event": "发现自己的身世之谜与先驱文明有关",
                        "change_process": [
                            {"phase": "困惑", "chapter": 7, "behavior": "对过去的信念产生动摇"},
                            {"phase": "探索", "chapter": 11, "behavior": "暗中寻找真相"},
                            {"phase": "抉择", "chapter": 16, "behavior": "在极端手段与和解之间做选择"},
                        ],
                        "end_state": {"status": "重新定义自己的使命", "belief": "真正的力量来自于团结而非征服"},
                        "chapter_mapping": [7, 11, 16],
                    },
                    {
                        "char_id": char_id_02,
                        "arc_type": "觉醒弧",
                        "start_state": {"status": "纯粹的科学家", "belief": "科学可以解释一切"},
                        "catalyst_event": "接触到无法用科学解释的共鸣石现象",
                        "change_process": [
                            {"phase": "否定", "chapter": 4, "behavior": "试图用现有理论强行解释"},
                            {"phase": "怀疑", "chapter": 8, "behavior": "开始接受超自然现象的可能性"},
                            {"phase": "融合", "chapter": 13, "behavior": "建立科学与神秘学的新认知框架"},
                        ],
                        "end_state": {"status": "科学与信仰的统一者", "belief": "真理有多重表现形式"},
                        "chapter_mapping": [4, 8, 13],
                    },
                ]
            }
            result = module.run(ctx, content)
            log_step(7, "arc_builder", result)
            all_results["arc_builder"] = result.data

    # ------ 步骤 08: FactionBuilder（势力设定） ------
    with get_session() as session:
        with session.begin():
            module = get_module("faction_builder")
            ctx = build_mock_context(novel_id, session, chroma_client, all_results)
            content = {
                "factions": [
                    {
                        "name": "星际联邦",
                        "type": "政治",
                        "hierarchy": ["联邦议会", "执行委员会", "星域总督", "行星理事会"],
                        "goals": ["维持星际秩序", "促进跨星域合作", "保护人类文明延续"],
                        "resources": ["联合舰队", "星际通讯网络", "联邦金库"],
                        "doctrines": ["所有殖民星球平等", "资源共享原则", "和平发展优先"],
                        "reputation": 0.65,
                        "members": [
                            {"char_id": char_id_01, "role": "特遣舰队长官", "rank": "上校"},
                            {"char_id": char_id_03, "role": "科学院顾问", "rank": "院士"},
                        ],
                    },
                    {
                        "name": "边缘星域联盟",
                        "type": "军事",
                        "hierarchy": ["最高指挥官", "星域领主", "基地司令", "舰队队长"],
                        "goals": ["争取边缘星域自治权", "开发未知星域资源", "对抗联邦控制"],
                        "resources": ["私掠舰队", "黑市网络", "稀有矿产"],
                        "doctrines": ["实力即正义", "星域自治", "生存优先于秩序"],
                        "reputation": 0.35,
                        "members": [
                            {"char_id": char_id_04, "role": "最高指挥官", "rank": "将军"},
                        ],
                    },
                ]
            }
            result = module.run(ctx, content)
            log_step(8, "faction_builder", result)
            all_results["faction_builder"] = result.data

    # ------ 步骤 09: FactionRelationBuilder（势力关系） ------
    with get_session() as session:
        with session.begin():
            module = get_module("faction_relation")
            faction_results = all_results["faction_builder"]
            faction_id_01 = faction_results["factions"][0].get("id", "FAC-001")
            faction_id_02 = faction_results["factions"][1].get("id", "FAC-002")
            ctx = build_mock_context(novel_id, session, chroma_client, all_results)
            content = {
                "relations": [
                    {
                        "faction_a_id": faction_id_01,
                        "faction_b_id": faction_id_02,
                        "type": "hostile",
                        "strength": 0.80,
                        "history": [{"event": "联邦试图收回边缘星域控制权", "impact": "武装冲突不断"}],
                        "treaties": [{"name": "停火协议", "status": "已破裂"}],
                        "hidden_agenda": "双方高层都有通过战争转移内部矛盾的意图",
                    },
                ]
            }
            result = module.run(ctx, content)
            log_step(9, "faction_relation", result)
            all_results["faction_relation"] = result.data

    # ------ 步骤 10: CharFactionBridge（人物-势力关联） ------
    with get_session() as session:
        with session.begin():
            module = get_module("char_faction_bridge")
            faction_results = all_results["faction_builder"]
            faction_id_01 = faction_results["factions"][0].get("id", "FAC-001")
            faction_id_02 = faction_results["factions"][1].get("id", "FAC-002")
            ctx = build_mock_context(novel_id, session, chroma_client, all_results)
            content = {
                "links": [
                    {
                        "char_id": char_id_map.get("林星辰", "CHAR-001"),
                        "char_name": "林星辰",
                        "faction_id": faction_id_01,
                        "faction_name": "星际联邦探索舰队",
                        "membership_type": "正式成员",
                        "join_chapter": 1,
                        "role_in_faction": "星舰舰长",
                        "loyalty": 0.95,
                        "notes": "主角，联邦精英军官",
                    },
                    {
                        "char_id": char_id_map.get("苏月", "CHAR-002"),
                        "char_name": "苏月",
                        "faction_id": faction_id_01,
                        "faction_name": "星际联邦探索舰队",
                        "membership_type": "正式成员",
                        "join_chapter": 1,
                        "role_in_faction": "首席科学官",
                        "loyalty": 0.85,
                        "notes": "主角挚友，联邦科学家",
                    },
                    {
                        "char_id": char_id_map.get("雷昊", "CHAR-003"),
                        "char_name": "雷昊",
                        "faction_id": faction_id_02,
                        "faction_name": "边缘星域自由军",
                        "membership_type": "正式成员",
                        "join_chapter": 1,
                        "role_in_faction": "自由军首领",
                        "loyalty": 0.90,
                        "notes": "与联邦敌对势力的领袖",
                    },
                    {
                        "char_id": char_id_map.get("维拉", "CHAR-004"),
                        "char_name": "维拉",
                        "faction_id": faction_id_01,
                        "faction_name": "星际联邦探索舰队",
                        "membership_type": "正式成员",
                        "join_chapter": 2,
                        "role_in_faction": "医疗官",
                        "loyalty": 0.75,
                        "notes": "外星混血，身世成谜",
                    },
                ]
            }
            result = module.run(ctx, content)
            log_step(10, "char_faction_bridge", result)
            all_results["char_faction_bridge"] = result.data

    # ------ 步骤 11: ItemBuilder（物品库） ------
    with get_session() as session:
        with session.begin():
            module = get_module("item_builder")
            ctx = build_mock_context(novel_id, session, chroma_client, all_results)
            content = {
                "items": [
                    {
                        "name": "共鸣石",
                        "type": "artifact",
                        "purpose": "储存先驱文明的智慧与能量",
                        "background_story": "由先驱文明创造，用于传承核心知识的量子态存储器",
                        "restrictions": ["只有特定基因序列的人能激活", "每次激活消耗内部能量"],
                        "current_owner": "林星辰",
                        "significance_to_plot": "是整个故事的核心线索，连接过去与未来",
                        "first_appearance_chapter": 3,
                    },
                    {
                        "name": "星轨吊坠",
                        "type": "key_item",
                        "purpose": "星舰舰长的身份象征，内含紧急跃迁坐标",
                        "background_story": "林星辰已故父亲留给她的唯一遗物",
                        "restrictions": ["只有舰长本人可以使用", "跃迁坐标每代舰长只更新一次"],
                        "current_owner": "林星辰",
                        "significance_to_plot": "在关键时刻成为拯救星舰的关键道具",
                        "first_appearance_chapter": 1,
                    },
                    {
                        "name": "预言石板",
                        "type": "key_item",
                        "purpose": "记录先驱文明留给后世的预言",
                        "background_story": "在陌生星系的遗迹中被发现，刻有古老的预言文字",
                        "restrictions": ["需要专门的解读工具", "部分内容被加密"],
                        "current_owner": "苏月",
                        "significance_to_plot": "揭示了故事的最终走向和选择",
                        "first_appearance_chapter": 5,
                    },
                    {
                        "name": "量子破译器",
                        "type": "technology",
                        "purpose": "破译古代文明加密信息的量子设备",
                        "background_story": "苏月自主研发的尖端科技设备",
                        "restrictions": ["运算时长过长会过热保护", "需要星舰能源核心支持"],
                        "current_owner": "苏月",
                        "significance_to_plot": "用以破译预言石板的真正内容",
                        "first_appearance_chapter": 6,
                    },
                ]
            }
            result = module.run(ctx, content)
            log_step(11, "item_builder", result)
            all_results["item_builder"] = result.data

    # ------ 步骤 12: ForeshadowManager（伏笔追踪） ------
    with get_session() as session:
        with session.begin():
            module = get_module("foreshadow_manager")
            ctx = build_mock_context(novel_id, session, chroma_client, all_results)
            content = {
                "foreshadows": [
                    {
                        "type": "物品伏笔", "status": "已埋设",
                        "plant_chapter": 1, "plant_location": "主角介绍", "plant_form": "林星辰抚摸吊坠的习惯动作",
                        "reveal_chapter_planned": 18, "reveal_form": "吊坠内的紧急跃迁坐标成为扭转战局关键",
                        "payload": "星轨吊坠是上一代舰长留下的底牌", "surface": "一个普通纪念品",
                        "depth": "深层", "importance": 0.85,
                        "related_char": [char_id_01], "tags": ["关键道具", "情感纽带"],
                    },
                    {
                        "type": "设定伏笔", "status": "已埋设",
                        "plant_chapter": 3, "plant_location": "第一次星际跃迁", "plant_form": "跃迁时主角感到异常的空间波动",
                        "reveal_chapter_planned": 12, "reveal_form": "揭示主角的星感能力",
                        "payload": "林星辰拥有罕见的星感能力", "surface": "跃迁时的正常不适感",
                        "depth": "中层", "importance": 0.75,
                        "related_char": [char_id_01], "tags": ["能力觉醒", "血脉秘密"],
                    },
                    {
                        "type": "人物伏笔", "status": "已埋设",
                        "plant_chapter": 4, "plant_location": "维拉的第一次登场", "plant_form": "维拉的瞳孔颜色和某种古老描述一致",
                        "reveal_chapter_planned": 16, "reveal_form": "发现维拉拥有先驱文明基因改造",
                        "payload": "维拉与先驱文明有基因层面的关联", "surface": "一种罕见的虹膜异色征",
                        "depth": "深层", "importance": 0.80,
                        "related_char": [char_id_04], "tags": ["身世之谜", "血脉秘密"],
                    },
                    {
                        "type": "情感伏笔", "status": "待埋设",
                        "plant_chapter": 6, "plant_location": "苏月与研究中的对话", "plant_form": "提到祖母的遗言",
                        "reveal_chapter_planned": 14, "reveal_form": "祖母的身世和最后的留言",
                        "payload": "苏月的祖母曾是先驱文明的联络人", "surface": "对逝去亲人的怀念",
                        "depth": "中层", "importance": 0.65,
                        "related_char": [char_id_02], "tags": ["家族秘密", "情感线索"],
                    },
                    {
                        "type": "规则伏笔", "status": "待埋设",
                        "plant_chapter": 8, "plant_location": "探索古代遗迹", "plant_form": "遗迹中的能量防护场",
                        "reveal_chapter_planned": 19, "reveal_form": "利用防护场原理对抗最终Boss",
                        "payload": "先驱文明的能量防护场存在频率共振弱点", "surface": "无法逾越的能量屏障",
                        "depth": "深层", "importance": 0.70,
                        "tags": ["世界观关键", "战斗转折"],
                    },
                    {
                        "type": "关系伏笔", "status": "待埋设",
                        "plant_chapter": 10, "plant_location": "主角与反派的第二次交锋", "plant_form": "维拉对林星辰的战斗方式异常熟悉",
                        "reveal_chapter_planned": 17, "reveal_form": "维拉曾接受过林星辰父亲的训练",
                        "payload": "维拉是林星辰父亲的学生，了解林家战斗风格", "surface": "巧合的战术熟悉",
                        "depth": "深层", "importance": 0.72,
                        "related_char": [char_id_01, char_id_04], "tags": ["人物关系", "过去纠葛"],
                    },
                ],
                "density_curve": [
                    {"chapter": 1, "active_count": 1, "density": 1.5, "new_count": 1, "resolved_count": 0},
                    {"chapter": 3, "active_count": 2, "density": 2.0, "new_count": 1, "resolved_count": 0},
                    {"chapter": 6, "active_count": 3, "density": 2.5, "new_count": 1, "resolved_count": 0},
                    {"chapter": 8, "active_count": 4, "density": 3.0, "new_count": 1, "resolved_count": 0},
                    {"chapter": 10, "active_count": 5, "density": 3.5, "new_count": 1, "resolved_count": 0},
                    {"chapter": 12, "active_count": 4, "density": 3.0, "new_count": 0, "resolved_count": 1},
                    {"chapter": 15, "active_count": 3, "density": 2.5, "new_count": 0, "resolved_count": 1},
                    {"chapter": 18, "active_count": 2, "density": 2.0, "new_count": 0, "resolved_count": 1},
                    {"chapter": 20, "active_count": 0, "density": 0.0, "new_count": 0, "resolved_count": 2},
                ],
            }
            result = module.run(ctx, content)
            log_step(12, "foreshadow_manager", result)
            all_results["foreshadow_manager"] = result.data

    # ------ 步骤 13: ArchiveBuilder（小说档案） ------
    with get_session() as session:
        with session.begin():
            module = get_module("archive_builder")
            ctx = build_mock_context(novel_id, session, chroma_client, all_results)
            content = {
                "archive": {
                    "layer1_identity_card": {
                        "title": "星穹之下",
                        "genre": "科幻 / 太空歌剧 / 人文",
                        "target_audience": "科幻爱好者、人文关怀型读者",
                        "tone": "宏大壮丽中带着细腻的情感温度",
                    },
                    "layer2_core_summary": {
                        "premise": "在文明濒临崩溃之际，一群星际拓荒者踏上了寻找新家园的征途，却在途中发现了足以颠覆人类认知的宇宙真相",
                        "core_conflict": "生存需求与道德底线之间的冲突",
                        "emotional_core": "在绝望中寻找希望的故事",
                    },
                    "layer3_module_snapshots": {
                        "character_list": [char_id_01, char_id_02, char_id_03, char_id_04],
                        "faction_list": ["星际联邦", "边缘星域联盟"],
                        "recent_changes": [
                            {"timestamp": datetime.now(timezone.utc).isoformat(), "step": "01", "module": "theme_engine", "action": "generate", "entity_id": "NOV-001", "entity_type": "novel", "summary": "主题生成", "changed_fields": ["theme"]},
                            {"timestamp": datetime.now(timezone.utc).isoformat(), "step": "03", "module": "outline_builder", "action": "generate", "entity_id": novel_id, "entity_type": "outline", "summary": "大纲生成", "changed_fields": ["acts", "causal_chain"]},
                            {"timestamp": datetime.now(timezone.utc).isoformat(), "step": "04", "module": "world_builder", "action": "generate", "entity_id": novel_id, "entity_type": "world", "summary": "世界观生成", "changed_fields": ["dimensions"]},
                            {"timestamp": datetime.now(timezone.utc).isoformat(), "step": "05", "module": "character_builder", "action": "generate", "entity_id": char_id_01, "entity_type": "character", "summary": "主角生成", "changed_fields": ["layer1", "layer2", "layer3", "layer4"]},
                            {"timestamp": datetime.now(timezone.utc).isoformat(), "step": "08", "module": "faction_builder", "action": "generate", "entity_id": "FAC-001", "entity_type": "faction", "summary": "势力生成", "changed_fields": ["name", "type", "hierarchy"]},
                            {"timestamp": datetime.now(timezone.utc).isoformat(), "step": "11", "module": "foreshadow_manager", "action": "generate", "entity_id": novel_id, "entity_type": "foreshadow", "summary": "伏笔生成", "changed_fields": ["foreshadows", "density_curve"]},
                        ],
                    },
                }
            }
            result = module.run(ctx, content)
            log_step(13, "archive_builder", result)
            all_results["archive_builder"] = result.data

    # ------ 步骤 14: SynopsisBuilder（小说简介） ------
    with get_session() as session:
        with session.begin():
            module = get_module("synopsis_builder")
            ctx = build_mock_context(novel_id, session, chroma_client, all_results)
            content = {
                "synopsis": {
                    "one_liner": {"text": "当星际拓荒者发现了足以颠覆人类认知的宇宙真相，文明的意义被重新定义。"},
                    "short_blurb": {"text": "公元3000年，地球资源枯竭，人类文明站在崩溃的边缘。前地球防卫军上校林星辰带领一批幸存者，乘坐星舰「希望号」踏上寻找新家园的征途。在穿越未知星域的过程中，他们发现了一个古老文明的遗迹——一个掌握着宇宙终极秘密的先驱文明。然而，这个发现不仅引来了野心勃勃的星际军阀的觊觎，更揭开了一段跨越千年的文明轮回之谜。在生存与道德、希望与牺牲之间，每个人都要做出自己的选择。"},
                    "standard_blurb": {"text": "公元3000年，地球资源枯竭，人类文明站在崩溃的边缘。前地球防卫军上校林星辰带领一批幸存者，乘坐星舰「希望号」踏上寻找新家园的征途。\n\n在穿越未知星域的过程中，他们发现了一个古老文明的遗迹——一个掌握着宇宙终极秘密的先驱文明。遗迹中的共鸣石、预言石板等遗物暗示着一个惊人的真相：宇宙中的文明并非偶然诞生，而是遵循着某种神秘的轮回规律。\n\n林星辰的团队中，科学官苏月试图用理性解读这些超自然现象，老教授罗则坚信古代智慧的价值。与此同时，边缘星域的军阀维拉也对先驱文明的遗产虎视眈眈。\n\n随着探索的深入，林星辰逐渐发现自己的身世与先驱文明有着千丝万缕的联系。她必须在保护队友、揭开真相和应对外敌之间找到平衡。最终，她将面临一个终极抉择：是按照预言揭示的命运走下去，还是开创人类自己的道路？\n\n这是一个关于文明韧性、人性温度和希望力量的故事。在浩瀚的星穹之下，每个人都在寻找属于自己的答案。"},
                    "long_blurb": {"text": "公元3000年，人类文明在经历了两千年的科技飞跃后，终于迎来了最严峻的考验——地球的资源即将枯竭。曾经繁华的星际联邦如今人心惶惶，各个殖民星球各自为政。\n\n在这个动荡的时代，前地球防卫军上校林星辰接到了一个艰巨的任务：带领一批精选的幸存者，乘坐最先进的星舰「希望号」，穿越未知的星域，寻找适合人类定居的新家园。\n\n与她同行的有天才科学官苏月——一个执着于揭开宇宙真理的年轻博士；老教授罗——一个坚守古代文明遗产的星际考古学家；以及五百名怀揣着不同希望的殖民者。\n\n然而，他们的征途从一开始就充满了变数。一次意外的跃迁事故将他们带到了一个从未被标记的星域，那里隐藏着一个古老文明的遗迹——先驱文明。这个在人类诞生之前就已经存在的文明，似乎预见到了人类的到来，留下了一系列令人费解的遗物：共鸣石、预言石板、以及一个关于文明轮回的惊人真相。\n\n更让林星辰始料未及的是，边缘星域的军阀维拉·暗星也在追踪先驱文明的线索。这个以铁腕手段统治着边缘星域的女将军，似乎与先驱文明有着不为人知的联系。\n\n随着「希望号」深入未知星域，团队内部的矛盾也逐渐浮现：有人主张利用先驱文明的科技快速建立新家园，有人认为应该谨慎行事避免重蹈先驱文明的覆辙。而在这一片混乱之中，隐藏在团队内部的叛徒也开始蠢蠢欲动。\n\n林星辰必须在对队友的责任、对真相的渴望和对未来的希望之间做出艰难的平衡。而随着她逐渐发现自己的身世之谜——她是最后的共鸣石守护者后裔——她的每一个选择都将影响整个人类文明的命运。\n\n《星穹之下》是一部融合硬科幻与人文关怀的宏大叙事，探讨了文明的意义、人性的韧性，以及在浩瀚宇宙中寻找希望的力量。"},
                    "core_conflict": "在生存压力与道德底线之间，人类文明该选择怎样的未来",
                    "world_highlight": "构建了包含三大星域、八大维度规则的硬科幻世界观，融合了先驱文明的神秘元素",
                    "selling_points": [
                        {"point": "星际冒险与哲学思辨的完美融合", "dimension": "plot"},
                        {"point": "四个层次深度的角色塑造，每个人物都有独立的成长弧线", "dimension": "character"},
                        {"point": "构建了自洽且富有想象力的硬科幻世界体系", "dimension": "world"},
                        {"point": "伏笔系统贯穿全书，前后呼应的叙事结构", "dimension": "plot"},
                    ],
                    "target_audience": "25-45岁科幻爱好者、人文社科读者、硬科幻与软科幻的双重受众",
                    "tone_tags": ["宏大", "温暖", "悬疑", "哲思", "希望"],
                    "comparison_titles": ["《三体》的中文科幻深度", "《星际穿越》的情感内核", "《沙丘》的世界观构建"],
                    "hook_question": "如果宇宙中存在着比你更古老的文明，他们留下的预言，你敢揭开吗？",
                }
            }
            result = module.run(ctx, content)
            log_step(14, "synopsis_builder", result)
            all_results["synopsis_builder"] = result.data

    # ------ 步骤 15: VolumeConfig（分卷配置） ------
    with get_session() as session:
        with session.begin():
            module = get_module("volume_config")
            ctx = build_mock_context(novel_id, session, chroma_client, all_results)
            content = {
                "volumes": [
                    {
                        "name": "启程卷",
                        "chapter_range": [1, 8],
                        "boundary_gravity": [{"chapter": 3, "event": "跃迁事故", "gravity": 0.7}],
                        "pacing": "medium",
                        "major_conflict": "地球危机与星际航行的生存挑战",
                        "character_focus": [char_id_01, char_id_02],
                        "themes": ["告别", "希望", "未知"],
                        "cliffhanger": "「希望号」被一股未知力量牵引，偏离了预定航线",
                        "chapters": [
                            {"chapter_number": 1, "pov_character": char_id_01, "summary": "地球危机的序幕", "word_count_budget": 5000},
                            {"chapter_number": 2, "pov_character": char_id_01, "summary": "启航前的准备与告别", "word_count_budget": 4000},
                            {"chapter_number": 3, "pov_character": char_id_02, "summary": "首次跃迁与意外事故", "word_count_budget": 4500},
                            {"chapter_number": 4, "pov_character": char_id_01, "summary": "事故后的危机管理", "word_count_budget": 4000},
                            {"chapter_number": 5, "pov_character": char_id_02, "summary": "发现未知信号", "word_count_budget": 4500},
                            {"chapter_number": 6, "pov_character": char_id_03, "summary": "解读信号来源", "word_count_budget": 4000},
                            {"chapter_number": 7, "pov_character": char_id_01, "summary": "接近未知星域", "word_count_budget": 3500},
                            {"chapter_number": 8, "pov_character": char_id_02, "summary": "发现先驱文明遗迹", "word_count_budget": 5000},
                        ],
                    },
                    {
                        "name": "探索卷",
                        "chapter_range": [9, 18],
                        "boundary_gravity": [{"chapter": 12, "event": "预言石板解读", "gravity": 0.8}],
                        "pacing": "fast",
                        "major_conflict": "探索先驱文明秘密与维拉势力的对抗",
                        "character_focus": [char_id_01, char_id_02, char_id_04],
                        "themes": ["探索", "冲突", "真相"],
                        "cliffhanger": "维拉出现在遗迹深处，而她的真实身份让人震惊",
                        "chapters": [
                            {"chapter_number": 9, "pov_character": char_id_03, "summary": "遗迹初步探索", "word_count_budget": 4500},
                            {"chapter_number": 10, "pov_character": char_id_01, "summary": "与维拉的首次正面冲突", "word_count_budget": 5000},
                            {"chapter_number": 11, "pov_character": char_id_04, "summary": "维拉的视角与动机", "word_count_budget": 4500},
                            {"chapter_number": 12, "pov_character": char_id_02, "summary": "预言石板破译", "word_count_budget": 5000},
                            {"chapter_number": 13, "pov_character": char_id_01, "summary": "内部叛变的暴露", "word_count_budget": 4000},
                            {"chapter_number": 14, "pov_character": char_id_02, "summary": "祖母秘密的揭示", "word_count_budget": 4500},
                            {"chapter_number": 15, "pov_character": char_id_04, "summary": "维拉与林星辰的被迫合作", "word_count_budget": 5000},
                            {"chapter_number": 16, "pov_character": char_id_01, "summary": "真相大白与身世揭秘", "word_count_budget": 5500},
                            {"chapter_number": 17, "pov_character": char_id_04, "summary": "维拉的选择与转变", "word_count_budget": 4500},
                            {"chapter_number": 18, "pov_character": char_id_01, "summary": "决定命运的最后准备", "word_count_budget": 4000},
                        ],
                    },
                    {
                        "name": "抉择卷",
                        "chapter_range": [19, 22],
                        "boundary_gravity": [{"chapter": 20, "event": "最终决战", "gravity": 0.95}],
                        "pacing": "fast",
                        "major_conflict": "如何利用先驱文明遗产决定人类命运",
                        "character_focus": [char_id_01, char_id_04],
                        "themes": ["牺牲", "重生", "希望"],
                        "cliffhanger": "林星辰做出了最终选择，星穹之下人类文明迎来了新的篇章",
                        "chapters": [
                            {"chapter_number": 19, "pov_character": char_id_01, "summary": "利用防护场反攻", "word_count_budget": 5000},
                            {"chapter_number": 20, "pov_character": char_id_04, "summary": "最终决战", "word_count_budget": 6000},
                            {"chapter_number": 21, "pov_character": char_id_02, "summary": "战后重建与新秩序", "word_count_budget": 4000},
                            {"chapter_number": 22, "pov_character": char_id_01, "summary": "尾声：希望的种子", "word_count_budget": 3500},
                        ],
                    },
                ],
            }
            result = module.run(ctx, content)
            log_step(15, "volume_config", result)
            all_results["volume_config"] = result.data

    # ------ 步骤 16: DetailOutlineBuilder（章节细纲） ------
    with get_session() as session:
        with session.begin():
            module = get_module("detail_outline")
            ctx = build_mock_context(novel_id, session, chroma_client, all_results)
            chapters_data = []
            for _, vol in enumerate(content["volumes"]):
                for ch in vol.get("chapters", []):
                    ch_num = ch["chapter_number"]  # type: ignore
                    chapters_data.append({
                        "chapter": ch_num,
                        "chapter_constraint_summary": {
                            "volume": vol["name"],
                            "pacing": vol["pacing"],
                            "major_conflict": vol["major_conflict"],
                            "active_foreshadows": [
                                f for f in all_results.get("foreshadow_manager", {}).get("foreshadows", [])
                                if f.get("plant_chapter", 0) <= ch_num <= f.get("reveal_chapter_planned", 999)
                            ],
                        },
                        "scenes": [
                            {
                                "id": f"ch{ch_num}s{si+1}",
                                "pov_char_id": ch["pov_character"],  # type: ignore
                                "emotional_arc": {"start_emotion": "平静", "end_emotion": "紧张"},
                                "word_count_budget": 2_500,
                                "setting": f"第{ch_num}章场景{si+1}",
                            }
                            for si in range(2)
                        ],
                    })

            mock_content = {"chapters": chapters_data}
            result = module.run(ctx, mock_content)
            log_step(16, "detail_outline", result)
            all_results["detail_outline"] = result.data

    # ------ 步骤 17: ManuscriptWriter（正文初稿） ------
    with get_session() as session:
        with session.begin():
            module = get_module("manuscript_writer")
            ctx = build_mock_context(novel_id, session, chroma_client, all_results)
            mock_chapters.clear()
            for ch_num in range(1, 23):
                scenes = []
                for si in range(2):
                    scenes.append({
                        "pov_char_id": char_id_01 if ch_num % 2 == 1 else char_id_02,
                        "content": f"第{ch_num}章第{si+1}场景的正文内容。这是一段模拟的小说正文，用于测试稿件生成模块的数据处理能力。在浩瀚的星穹之下，人类文明正面临着前所未有的挑战和机遇。{'林星辰站在舰桥的舷窗前，凝视着远方的星空。' if si == 0 else '苏月埋头于数据分析终端，眉头紧锁。'}",
                        "scene_id": f"ch{ch_num:02d}_sc{si+1:02d}",
                        "word_count": 120,
                        "setting": f"第{ch_num}章场景{si+1}",
                    })
                mock_chapters.append({
                    "chapter_number": ch_num,
                    "title": f"第{ch_num}章",
                    "scenes": scenes,
                    "word_count": sum(int(s.get("word_count", 0) or 0) for s in scenes),
                })
            content = {
                "chapters": mock_chapters,
                "transition_fixes": [],
            }
            result = module.run(ctx, content)
            log_step(17, "manuscript_writer", result)
            all_results["manuscript_writer"] = result.data

    # ------ 步骤 18: ReviewExecutor（正文审核） ------
    with get_session() as session:
        with session.begin():
            from src.core.quality.review_executor import ReviewExecutor
            module = ReviewExecutor()
            # 拼接所有章节正文供审查
            newline = "\n"
            full_text = "\n\n".join(
                f"第{ch['chapter_number']}章 {newline.join(s.get('content', '') for s in ch['scenes'])}"
                for ch in mock_chapters
            )
            ctx = build_mock_context(novel_id, session, chroma_client, all_results)
            # 注入审核器所需依赖
            ctx["dependencies"]["world_building"] = all_results.get("world_builder", {}).get("dimensions", [])
            ctx["dependencies"]["characters"] = all_results.get("character_builder", {}).get("characters", [])
            content = {
                "text": full_text,
                "chapters_to_review": list(range(1, 23)),
            }
            result = module.run(ctx, content)
            log_step(18, "review_executor", result)
            all_results["review_executor"] = result.data

    # ------ 步骤 19: ManuscriptFixer（正文修正） ------
    with get_session() as session:
        with session.begin():
            module = get_module("manuscript_fixer")
            # 注入审核结果作为依赖
            all_results["manuscript_fixer"] = all_results.get("manuscript_writer", {}).copy()
            all_results["manuscript_fixer"]["_dependencies"] = {
                "manuscript_writer": all_results.get("manuscript_writer", {}),
                "review_executor": all_results.get("review_executor", {}),
            }
            ctx = build_mock_context(novel_id, session, chroma_client, all_results)
            mock_fixes = []
            review_data = all_results.get("review_executor", {}).get("review_result", {})
            if not review_data.get("passed", True):
                details = review_data.get("details", [])
                for detail in details[:3]:
                    mock_fixes.append({
                        "chapter_number": 1,
                        "fix_type": "writing_quality",
                        "issue_ref": detail[:100],
                        "original_text": "需要修正的原文内容",
                        "fixed_text": "修正后的内容",
                    })
            content = {
                "chapters": list(mock_chapters),
                "fixes": mock_fixes if mock_fixes else [
                    {"chapter_number": 1, "fix_type": "minor", "issue_ref": "格式调整", "original_text": "原内容", "fixed_text": "修正内容"},
                ],
            }
            result = module.run(ctx, content)
            log_step(19, "manuscript_fixer", result)
            all_results["manuscript_fixer"] = result.data

    # ------ 步骤 20: ExportTool（导出发布） ------
    with get_session() as session:
        with session.begin():
            module = get_module("export_tool")
            ctx = build_mock_context(novel_id, session, chroma_client, all_results)
            # 更新稿件状态，让导出模块能找到数据
            for ch_num in range(1, 23):
                session.execute(
                    text("UPDATE manuscripts SET status = 'fixed' WHERE chapter_number = :cn AND novel_id = :nid"),
                    {"cn": ch_num, "nid": novel_id},
                )
            content = {
                "export": {
                    "formats": ["markdown", "txt"],
                    "include_review_report": True,
                    "include_foreshadow_map": True,
                }
            }
            result = module.run(ctx, content)
            log_step(20, "export_tool", result)
            all_results["export_tool"] = result.data

    # ========== 4. 汇总报告 ==========
    print()
    print("=" * 60)
    print("  📊 Mock 端到端测试结果汇总")
    print("=" * 60)
    success_count = sum(1 for _, data in all_results.items() if isinstance(data, dict) and len(data) > 0)
    print(f"  ✅ 成功执行步骤: {success_count}/20")
    print(f"  📁 测试小说 ID: {novel_id}")
    print(f"  📁 Rollback SQLite: {Config.SQLITE_PATH}")

    for step_name, data in all_results.items():
        if isinstance(data, dict) and data:
            word_count = data.get("word_count", 0)
            if word_count:
                print(f"     {step_name}: {word_count} 字")

    # 检查导出文件
    export_data = all_results.get("export_tool", {})
    exported_files = export_data.get("exported_files", [])
    if exported_files:
        print(f"\n  📄 导出文件:")
        for ef in exported_files:
            path = ef.get("path", "")
            if os.path.exists(path):
                file_size = os.path.getsize(path)
                print(f"     ✅ {ef.get('format', '')}: {path} ({file_size} 字节)")
            else:
                print(f"     ❌ {ef.get('format', '')}: {path} (文件不存在)")

    print()
    print("=" * 60)
    print("  🎉 Mock 端到端测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
