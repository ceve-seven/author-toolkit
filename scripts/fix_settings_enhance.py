# -*- coding: utf-8 -*-
"""
数据库设定层全面修复和增强脚本
- 删除旧的角色弧线空壳数据
- 补充张铁军和赵明轩的势力关联
- 增强人物设定（配角记忆点、反派去脸谱化）
- 增加主角代价设计
- 增加伏笔密度（FS-021 ~ FS-050）
- 增加角色冲突升级路径
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import sqlite3
from datetime import datetime, timezone
from config import Config

NOVEL_ID = "NOV-001"
NOW = datetime.now(timezone.utc).isoformat()

# ─────────────────────────────────────────────────────────────
# 辅助函数
# ─────────────────────────────────────────────────────────────
def step_header(msg):
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}")


def get_db():
    db_path = Config.SQLITE_PATH
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def load_json_field(cursor, table, id_col, id_val, field):
    """读取某个表的某个 JSON 字段"""
    cursor.execute(f"SELECT {field} FROM {table} WHERE {id_col} = ?", (id_val,))
    row = cursor.fetchone()
    if row and row[0]:
        val = row[0]
        if isinstance(val, str):
            return json.loads(val)
        return val
    return {}


def save_json_field(cursor, table, id_col, id_val, field, data):
    """保存 JSON 到某个表的某个字段"""
    cursor.execute(
        f"UPDATE {table} SET {field} = ? WHERE {id_col} = ?",
        (json.dumps(data, ensure_ascii=False), id_val),
    )


def merge_json_field(cursor, table, id_col, id_val, field, updates):
    """合并更新 JSON 字段"""
    data = load_json_field(cursor, table, id_col, id_val, field)
    data.update(updates)
    save_json_field(cursor, table, id_col, id_val, field, data)


# ─────────────────────────────────────────────────────────────
# 步骤1：删除旧的角色弧线空壳数据
# ─────────────────────────────────────────────────────────────
def step1_delete_empty_arcs(conn):
    step_header("步骤1: 删除旧的角色弧线空壳数据")
    c = conn.cursor()

    # 先查看现有弧线
    c.execute("SELECT * FROM character_arcs WHERE novel_id = ?", (NOVEL_ID,))
    cols = [desc[0] for desc in c.description]
    rows = c.fetchall()
    print(f"  当前弧线总数: {len(rows)}")
    for row in rows:
        d = dict(zip(cols, row))
        print(f"    {d.get('char_id')} / {d.get('arc_type')} | start={d.get('start_state','')[:30]}")

    # 删除成长弧和堕落弧的空壳
    c.execute(
        "DELETE FROM character_arcs WHERE novel_id = ? AND arc_type IN ('成长弧', '堕落弧')",
        (NOVEL_ID,),
    )
    deleted = c.rowcount
    print(f"  删除了 {deleted} 条空壳弧线（成长弧/堕落弧）")

    # 确认保留的弧线
    c.execute("SELECT * FROM character_arcs WHERE novel_id = ?", (NOVEL_ID,))
    remaining = c.fetchall()
    print(f"  保留弧线数: {len(remaining)}")
    for row in remaining:
        d = dict(zip(cols, row))
        print(f"    {d.get('char_id')} / {d.get('arc_type')}")

    conn.commit()
    return deleted


# ─────────────────────────────────────────────────────────────
# 步骤2：补充张铁军和赵明轩的势力关联
# ─────────────────────────────────────────────────────────────
def step2_add_faction_links(conn):
    step_header("步骤2: 补充张铁军和赵明轩的势力关联")
    c = conn.cursor()

    # 查询确认 faction 和 char 信息
    c.execute("SELECT faction_id, name FROM factions WHERE novel_id = ?", (NOVEL_ID,))
    factions = {row[0]: row[1] for row in c.fetchall()}
    print("  现有势力:")
    for fid, fname in factions.items():
        print(f"    {fid}: {fname}")

    c.execute("SELECT char_id, name FROM characters WHERE novel_id = ?", (NOVEL_ID,))
    chars = {row[0]: row[1] for row in c.fetchall()}
    print("  现有角色:")
    for cid, cname in chars.items():
        print(f"    {cid}: {cname}")

    # 查找王氏投资集团的 faction_id
    wang_faction = None
    for fid, fname in factions.items():
        if "王氏" in fname or "王志远" in fname:
            wang_faction = fid
            break
    print(f"\n  王氏投资集团 faction_id: {wang_faction}")

    # 查找林氏资本的 faction_id
    lin_faction = None
    for fid, fname in factions.items():
        if "林氏" in fname or "林默" in fname:
            lin_faction = fid
            break
    print(f"  林氏资本 faction_id: {lin_faction}")

    # 张铁军 -> 王氏投资集团（作为外围盟友）
    # 使用 char_faction_links 表
    if wang_faction:
        # 先检查是否已存在
        c.execute(
            "SELECT id FROM char_faction_links WHERE char_id = 'CHAR-010' AND faction_id = ?",
            (wang_faction,),
        )
        existing = c.fetchone()
        if existing:
            # 更新
            c.execute(
                """UPDATE char_faction_links SET
                   membership_type = '外围盟友',
                   join_chapter = 200,
                   role_in_faction = '外围盟友',
                   loyalty = 0.4,
                   notes = '张铁军作为王氏投资集团的外围盟友，提供地方资源'
                   WHERE char_id = 'CHAR-010' AND faction_id = ?""",
                (wang_faction,),
            )
            print(f"  更新 CHAR-010 <-> {wang_faction} 关联: 外围盟友")
        else:
            c.execute(
                """INSERT INTO char_faction_links
                   (novel_id, char_id, faction_id, membership_type, join_chapter, leave_chapter, role_in_faction, loyalty, notes)
                   VALUES (?, 'CHAR-010', ?, '外围盟友', 200, 0, '外围盟友', 0.4, '张铁军作为王氏投资集团的外围盟友')""",
                (NOVEL_ID, wang_faction),
            )
            print(f"  新增 CHAR-010 <-> {wang_faction} 关联: 外围盟友")

        # 同步更新 faction_members 表
        c.execute(
            "SELECT faction_id, char_id FROM faction_members WHERE faction_id = ? AND char_id = 'CHAR-010'",
            (wang_faction,),
        )
        if not c.fetchone():
            c.execute(
                "INSERT OR REPLACE INTO faction_members (novel_id, faction_id, char_id, role, rank) VALUES ('NOV-001', ?, 'CHAR-010', '外围盟友', 'B')",
                (wang_faction,),
            )
            print(f"  新增 faction_members: CHAR-010 -> {wang_faction}")

    # 赵明轩 -> 林氏资本（背叛前，核心成员）
    if lin_faction:
        c.execute(
            "SELECT id FROM char_faction_links WHERE char_id = 'CHAR-005' AND faction_id = ?",
            (lin_faction,),
        )
        existing = c.fetchone()
        if existing:
            c.execute(
                """UPDATE char_faction_links SET
                   membership_type = '正式成员',
                   join_chapter = 100,
                   role_in_faction = '核心成员',
                   loyalty = 0.6,
                   notes = '赵明轩在背叛前是林氏资本的核心成员，负责投资部'
                   WHERE char_id = 'CHAR-005' AND faction_id = ?""",
                (lin_faction,),
            )
            print(f"  更新 CHAR-005 <-> {lin_faction} 关联: 核心成员")
        else:
            c.execute(
                """INSERT INTO char_faction_links
                   (novel_id, char_id, faction_id, membership_type, join_chapter, leave_chapter, role_in_faction, loyalty, notes)
                   VALUES (?, 'CHAR-005', ?, '正式成员', 100, 800, '核心成员', 0.6, '赵明轩在背叛前是林氏资本核心成员')""",
                (NOVEL_ID, lin_faction),
            )
            print(f"  新增 CHAR-005 <-> {lin_faction} 关联: 核心成员")

        # 同步更新 faction_members 表
        c.execute(
            "SELECT faction_id, char_id FROM faction_members WHERE faction_id = ? AND char_id = 'CHAR-005'",
            (lin_faction,),
        )
        if not c.fetchone():
            c.execute(
                "INSERT OR REPLACE INTO faction_members (novel_id, faction_id, char_id, role, rank) VALUES ('NOV-001', ?, 'CHAR-005', '核心成员', 'A')",
                (lin_faction,),
            )
            print(f"  新增 faction_members: CHAR-005 -> {lin_faction}")

    conn.commit()
    print("  步骤2完成")


# ─────────────────────────────────────────────────────────────
# 步骤3：增强人物设定 -- 添加配角记忆点
# ─────────────────────────────────────────────────────────────
def step3_enhance_characters(conn):
    step_header("步骤3: 增强人物设定 -- 添加配角记忆点")
    c = conn.cursor()

    # 配角记忆点配置
    enhancements = {
        "CHAR-002": {
            "name": "陈锋",
            "memory_points": [
                "总是不自觉地摸腰间的军刀",
                "说话简短有力从不超过十个字",
                "保护林默时眼神会变得像狼一样",
            ],
            "catchphrase": "有我在。",
            "body_language_additions": {
                "紧张": ["右手摸军刀", "眼神扫视四周"],
                "愤怒": ["握紧拳头但不说话", "军刀出鞘半寸"],
                "忠诚": ["挡在林默身前", "沉默点头"],
            },
        },
        "CHAR-003": {
            "name": "苏晴",
            "memory_points": [
                "紧张时会翻笔记本",
                "做决策前会闭眼三秒",
                "用左手写字（独特习惯）",
            ],
            "catchphrase": "数据不会说谎。",
            "body_language_additions": {
                "紧张": ["翻笔记本", "咬笔帽"],
                "自信": ["合上笔记本微笑", "左手签字"],
                "愤怒": ["笔记本摔在桌上"],
            },
        },
        "CHAR-005": {
            "name": "赵明轩",
            "memory_points": [
                "笑的时候眼睛不笑（笑面虎特征）",
                "说话时喜欢用'我们'代替'我'",
                "背叛前会不自觉地摸右手无名指",
            ],
            "catchphrase": "为了团队好。",
            "body_language_additions": {
                "虚伪": ["标准微笑但眼神冰冷", "拍肩膀"],
                "动摇": ["摸无名指", "看手机"],
                "贪婪": ["嘴角微扬但眼神锐利"],
            },
        },
        "CHAR-006": {
            "name": "李雪",
            "memory_points": [
                "调查时习惯性地推眼镜",
                "紧张时会搓手指",
                "办公桌上总有一杯凉透的咖啡",
            ],
            "catchphrase": "消息已经确认了。",
            "body_language_additions": {
                "专注": ["推眼镜", "盯着屏幕不眨眼"],
                "担忧": ["搓手指", "看旧照片"],
                "坚定": ["放下咖啡站起来"],
            },
        },
        "CHAR-007": {
            "name": "钱浩天",
            "memory_points": [
                "从不喝咖啡只喝茶",
                "说话时喜欢用比喻",
                "输的时候反而会笑",
            ],
            "catchphrase": "市场永远是对的。",
            "body_language_additions": {
                "自信": ["慢悠悠喝茶", "用比喻说话"],
                "愤怒": ["摔茶杯", "罕见地沉默"],
                "算计": ["手指敲桌面", "眼神从对方移到窗外"],
            },
        },
        "CHAR-008": {
            "name": "沈婉清",
            "memory_points": [
                "思考时会玩头发",
                "说谎时语速会变慢",
                "对林默有真实的好感（内心冲突）",
            ],
            "catchphrase": "从科学角度来说……",
            "body_language_additions": {
                "伪装": ["标准微笑", "语速平稳"],
                "动摇": ["玩头发", "语速变慢"],
                "真实": ["卸下伪装后的脆弱", "看着林默时眼神柔软"],
            },
        },
        "CHAR-009": {
            "name": "詹姆斯·洛克",
            "memory_points": [
                "从不亲自露面只通过全息投影",
                "说话用第三人称称呼自己",
                "办公室里有一面墙的书但从未翻开过",
            ],
            "catchphrase": "有趣。",
            "body_language_additions": {
                "掌控": ["十指交叉", "语速极慢"],
                "兴趣": ["微微前倾", "说'有趣'"],
                "愤怒": ["罕见地站起来", "声音反而更低"],
            },
        },
        "CHAR-010": {
            "name": "张铁军",
            "memory_points": [
                "喜欢戴金链子",
                "说话声音特别大",
                "被怼的时候会脸红但嘴硬",
            ],
            "catchphrase": "你知道我是谁吗？",
            "body_language_additions": {
                "嚣张": ["拍桌子", "声音提高八度"],
                "心虚": ["摸金链子", "眼神闪躲"],
                "恐惧": ["脸发白", "声音突然变小"],
            },
        },
    }

    for char_id, enh in enhancements.items():
        # 读取现有 layer2_json
        layer2 = load_json_field(c, "characters", "char_id", char_id, "layer2_json")
        print(f"  {enh['name']}({char_id}) layer2_json 原始: {json.dumps(layer2, ensure_ascii=False)[:100]}")

        # 添加记忆点
        layer2["memory_points"] = enh["memory_points"]
        layer2["catchphrase"] = enh["catchphrase"]

        # 合并肢体语言词典
        if "body_language_dictionary" not in layer2:
            layer2["body_language_dictionary"] = {}
        layer2["body_language_dictionary"].update(enh["body_language_additions"])

        save_json_field(c, "characters", "char_id", char_id, "layer2_json", layer2)
        print(f"  {enh['name']}({char_id}) 已添加记忆点和口头禅")

    conn.commit()
    print("  步骤3完成: 8个角色的记忆点增强完毕")


# ─────────────────────────────────────────────────────────────
# 步骤4：增强反派"去脸谱化"
# ─────────────────────────────────────────────────────────────
def step4_de_face_villains(conn):
    step_header("步骤4: 增强反派去脸谱化 -- 深层动机与镜像对比")
    c = conn.cursor()

    villain_depth = {
        "CHAR-004": {
            "name": "王志远",
            "motivation_depth": (
                "王志远并非纯粹的坏人。他的疯狂源于对父亲的不认同——"
                "父亲用灰色手段积累财富却从不承认，王志远想用'正当方式'超越父亲，"
                "却发现自己也在走老路。他的嫉妒不是对林默的财富，"
                "而是对林默'不需要证明自己'的从容。"
            ),
            "mirror_to_protagonist": (
                "林默和王志远都是'想证明自己'的人，但林默选择低调（因为不需要证明），"
                "王志远选择高调（因为太需要证明）。两人是同一枚硬币的两面。"
            ),
        },
        "CHAR-007": {
            "name": "钱浩天",
            "motivation_depth": (
                "钱浩天出身贫寒，靠奖学金读完名校。他对市场的'操控'源于童年被命运操控的恐惧——"
                "他需要掌控一切来获得安全感。他不是纯粹的恶人，而是一个'被恐惧驱动的天才'。"
            ),
            "mirror_to_protagonist": (
                "林默用未来记忆掌控命运，钱浩天用金融工具掌控命运。"
                "两人都相信'信息就是权力'，但林默选择共赢，钱浩天选择零和。"
            ),
        },
        "CHAR-009": {
            "name": "詹姆斯·洛克",
            "motivation_depth": (
                "洛克曾是一个理想主义者，在华尔街试图改变金融体系但被现实碾碎。"
                "他创建黑石集团的初衷是'建立一个新的秩序'，但手段越来越极端。"
                "他自认为是'必要的恶'。"
            ),
            "mirror_to_protagonist": (
                "洛克和林默都是'穿越者'般的存在——洛克拥有超越常人的视野和格局。"
                "但洛克选择了控制，林默选择了自由。两人最终的对决是'控制vs自由'的哲学博弈。"
            ),
        },
    }

    for char_id, info in villain_depth.items():
        layer2 = load_json_field(c, "characters", "char_id", char_id, "layer2_json")
        layer2["motivation_depth"] = info["motivation_depth"]
        layer2["mirror_to_protagonist"] = info["mirror_to_protagonist"]
        save_json_field(c, "characters", "char_id", char_id, "layer2_json", layer2)
        print(f"  {info['name']}({char_id}) 已添加深层动机和镜像对比")

    conn.commit()
    print("  步骤4完成: 3个反派的去脸谱化增强完毕")


# ─────────────────────────────────────────────────────────────
# 步骤5：增加主角代价设计
# ─────────────────────────────────────────────────────────────
def step5_protagonist_cost(conn):
    step_header("步骤5: 增加主角代价设计（林默 layer4_json）")
    c = conn.cursor()

    cost_data = {
        "secrets": ["穿越者身份", "记忆正在逐渐模糊"],
        "cracks": [
            "过度依赖未来记忆导致对当下感知迟钝",
            "无法建立真正的亲密关系（因为知道所有人的结局）",
            "每使用一次关键记忆，就会遗忘一段2035年的个人记忆",
        ],
        "cost_of_power": {
            "memory_fade": "越远的未来记忆越模糊，2035年的个人生活记忆已经模糊了60%",
            "timeline_deviation": "每次重大干预都会导致时间线偏移，部分投资预测不再准确",
            "emotional_isolation": "知道所有人的未来结局，无法真正投入感情",
            "identity_crisis": "逐渐分不清自己是2035年的林默还是2010年的林默",
        },
    }

    layer4 = load_json_field(c, "characters", "char_id", "CHAR-001", "layer4_json")
    layer4.update(cost_data)
    save_json_field(c, "characters", "char_id", "CHAR-001", "layer4_json", layer4)

    print(f"  林默(CHAR-001) layer4_json 已更新:")
    print(f"    secrets: {cost_data['secrets']}")
    print(f"    cracks: {len(cost_data['cracks'])} 条")
    print(f"    cost_of_power: {len(cost_data['cost_of_power'])} 项")

    conn.commit()
    print("  步骤5完成")


# ─────────────────────────────────────────────────────────────
# 步骤6：增加伏笔密度（FS-021 ~ FS-050）
# ─────────────────────────────────────────────────────────────
def step6_add_foreshadows(conn):
    step_header("步骤6: 增加伏笔密度（FS-021 ~ FS-050，共30条）")
    c = conn.cursor()

    # 先确认现有伏笔数量
    c.execute("SELECT COUNT(*) FROM foreshadows WHERE novel_id = ?", (NOVEL_ID,))
    existing_count = c.fetchone()[0]
    print(f"  现有伏笔数量: {existing_count}")

    # 30条新伏笔定义
    new_foreshadows = [
        {
            "foreshadow_id": "FS-021",
            "type": "信息伏笔",
            "plant_chapter": 30,
            "plant_location": "林默独处时的内心独白",
            "plant_form": "林默发现自己记不清2035年某天的天气",
            "reveal_chapter_planned": 600,
            "reveal_form": "揭示记忆模糊是穿越的副作用",
            "payload": {"content": "林默的记忆模糊现象", "surface": "偶尔的记忆空白", "depth": "深层"},
            "related_char": ["林默"],
            "related_item": [],
            "related_plot": ["穿越"],
            "importance": 0.95,
        },
        {
            "foreshadow_id": "FS-022",
            "type": "人物伏笔",
            "plant_chapter": 55,
            "plant_location": "陈锋接到家里的电话",
            "plant_form": "陈锋提到妹妹的病情，暗示病因不寻常",
            "reveal_chapter_planned": 900,
            "reveal_form": "妹妹的病与国际组织的实验有关",
            "payload": {"content": "陈锋妹妹的病与某国际组织有关", "surface": "罕见的遗传病", "depth": "深层"},
            "related_char": ["陈锋"],
            "related_item": [],
            "related_plot": ["暗线"],
            "importance": 0.85,
        },
        {
            "foreshadow_id": "FS-023",
            "type": "关系伏笔",
            "plant_chapter": 65,
            "plant_location": "苏晴签字时的细节",
            "plant_form": "苏晴用左手签字，林默注意到这个习惯",
            "reveal_chapter_planned": 1100,
            "reveal_form": "左撇子暗示苏晴有隐藏身世",
            "payload": {"content": "苏晴左撇子习惯暗示她有隐藏身世", "surface": "独特的书写习惯", "depth": "中层"},
            "related_char": ["苏晴"],
            "related_item": [],
            "related_plot": ["身世线"],
            "importance": 0.7,
        },
        {
            "foreshadow_id": "FS-024",
            "type": "物品伏笔",
            "plant_chapter": 35,
            "plant_location": "林默翻看旧物时发现怀表",
            "plant_form": "怀表上刻有与笔记本密码相同的符号",
            "reveal_chapter_planned": 500,
            "reveal_form": "怀表密码打开加密笔记本",
            "payload": {"content": "加密笔记本的密码与老式怀表有关", "surface": "一枚旧怀表", "depth": "中层"},
            "related_char": ["林默"],
            "related_item": ["怀表", "加密笔记本"],
            "related_plot": ["线索"],
            "importance": 0.75,
        },
        {
            "foreshadow_id": "FS-025",
            "type": "情感伏笔",
            "plant_chapter": 120,
            "plant_location": "林默深夜独自站在窗前",
            "plant_form": "林默想起2035年的某个人，情绪波动",
            "reveal_chapter_planned": 1350,
            "reveal_form": "揭示林默在2035年有一段未了的感情",
            "payload": {"content": "林默对2035年的某个人的执念", "surface": "偶尔的出神", "depth": "深层"},
            "related_char": ["林默"],
            "related_item": [],
            "related_plot": ["情感线"],
            "importance": 0.85,
        },
        {
            "foreshadow_id": "FS-026",
            "type": "结构伏笔",
            "plant_chapter": 260,
            "plant_location": "星河科技成立时的文件签名",
            "plant_form": "创始人的签名模糊不清，似乎刻意隐藏",
            "reveal_chapter_planned": 700,
            "reveal_form": "星河科技创始人的真实身份揭晓",
            "payload": {"content": "星河科技创始人的真实身份", "surface": "一个神秘的签名", "depth": "中层"},
            "related_char": ["林默"],
            "related_item": [],
            "related_plot": ["商业线"],
            "importance": 0.8,
        },
        {
            "foreshadow_id": "FS-027",
            "type": "信息伏笔",
            "plant_chapter": 180,
            "plant_location": "林默与某官员的会面",
            "plant_form": "林默提前知道一个政策变化，但未说明消息来源",
            "reveal_chapter_planned": 350,
            "reveal_form": "揭示林默获取内幕消息的渠道",
            "payload": {"content": "2012年某个政策变化的内幕消息来源", "surface": "精准的政策预判", "depth": "浅层"},
            "related_char": ["林默"],
            "related_item": [],
            "related_plot": ["投资线"],
            "importance": 0.5,
        },
        {
            "foreshadow_id": "FS-028",
            "type": "人物伏笔",
            "plant_chapter": 210,
            "plant_location": "张铁军炫耀金链子的场景",
            "plant_form": "金链子在某次碰撞中发出不正常的声响",
            "reveal_chapter_planned": 400,
            "reveal_form": "金链子是假的，暗示张铁军外强中干",
            "payload": {"content": "张铁军的金链子是假的（暗示他外强中干）", "surface": "一条金链子", "depth": "浅层"},
            "related_char": ["张铁军"],
            "related_item": ["金链子"],
            "related_plot": ["喜剧线"],
            "importance": 0.4,
        },
        {
            "foreshadow_id": "FS-029",
            "type": "关系伏笔",
            "plant_chapter": 130,
            "plant_location": "陈锋和苏晴共同处理危机",
            "plant_form": "两人之间有微妙的默契和眼神交流",
            "reveal_chapter_planned": 600,
            "reveal_form": "揭示两人之间隐秘的情感",
            "payload": {"content": "陈锋和苏晴之间微妙的情感", "surface": "工作伙伴的默契", "depth": "浅层"},
            "related_char": ["陈锋", "苏晴"],
            "related_item": [],
            "related_plot": ["情感线"],
            "importance": 0.5,
        },
        {
            "foreshadow_id": "FS-030",
            "type": "物品伏笔",
            "plant_chapter": 555,
            "plant_location": "瑞士银行账户文件",
            "plant_form": "账户文件上出现第二个签名缩写'J.L.'",
            "reveal_chapter_planned": 1050,
            "reveal_form": "J.L.的身份揭晓，与洛克有关",
            "payload": {"content": "瑞士银行账户的第二个签名人是J.L.", "surface": "一个神秘的签名缩写", "depth": "深层"},
            "related_char": ["詹姆斯·洛克"],
            "related_item": ["瑞士银行账户"],
            "related_plot": ["暗线"],
            "importance": 0.9,
        },
        {
            "foreshadow_id": "FS-031",
            "type": "信息伏笔",
            "plant_chapter": 70,
            "plant_location": "林默复盘第一次投资",
            "plant_form": "林默回忆那次失败时表情异常复杂",
            "reveal_chapter_planned": 200,
            "reveal_form": "揭示第一次投资失败的真正原因",
            "payload": {"content": "林默第一次投资失败的原因", "surface": "一次普通的投资失误", "depth": "浅层"},
            "related_char": ["林默"],
            "related_item": [],
            "related_plot": ["成长线"],
            "importance": 0.5,
        },
        {
            "foreshadow_id": "FS-032",
            "type": "情感伏笔",
            "plant_chapter": 105,
            "plant_location": "赵明轩加入团队的欢迎会",
            "plant_form": "赵明轩的眼神在某个瞬间闪过异样的光芒",
            "reveal_chapter_planned": 760,
            "reveal_form": "揭示赵明轩从一开始就别有用心",
            "payload": {"content": "赵明轩加入团队时的眼神异常", "surface": "新人的紧张", "depth": "中层"},
            "related_char": ["赵明轩"],
            "related_item": [],
            "related_plot": ["背叛线"],
            "importance": 0.7,
        },
        {
            "foreshadow_id": "FS-033",
            "type": "结构伏笔",
            "plant_chapter": 320,
            "plant_location": "王氏投资集团的资金审计报告",
            "plant_form": "报告中有一笔来源不明的巨额资金",
            "reveal_chapter_planned": 580,
            "reveal_form": "资金来源与政府背景有关",
            "payload": {"content": "王氏投资集团的资金来源有政府背景", "surface": "正常的商业融资", "depth": "中层"},
            "related_char": ["王志远"],
            "related_item": [],
            "related_plot": ["阴谋线"],
            "importance": 0.75,
        },
        {
            "foreshadow_id": "FS-034",
            "type": "人物伏笔",
            "plant_chapter": 160,
            "plant_location": "李雪翻看旧手机",
            "plant_form": "李雪看到哥哥发来的最后一条信息，表情凝重",
            "reveal_chapter_planned": 850,
            "reveal_form": "哥哥失踪的真相与主线剧情相连",
            "payload": {"content": "李雪哥哥失踪前留下的最后一条信息", "surface": "一段普通的短信", "depth": "深层"},
            "related_char": ["李雪"],
            "related_item": [],
            "related_plot": ["暗线"],
            "importance": 0.8,
        },
        {
            "foreshadow_id": "FS-035",
            "type": "关系伏笔",
            "plant_chapter": 640,
            "plant_location": "钱浩天与林默首次会面",
            "plant_form": "钱浩天说'他让我想起了年轻时的自己'",
            "reveal_chapter_planned": 1060,
            "reveal_form": "揭示钱浩天和林默的相似与不同",
            "payload": {"content": "钱浩天对林默的第一印象——'他让我想起了年轻时的自己'", "surface": "长辈对后辈的评价", "depth": "中层"},
            "related_char": ["钱浩天", "林默"],
            "related_item": [],
            "related_plot": ["对决线"],
            "importance": 0.8,
        },
        {
            "foreshadow_id": "FS-036",
            "type": "物品伏笔",
            "plant_chapter": 680,
            "plant_location": "沈婉清的实验室",
            "plant_form": "实验桌上有一张旧照片，沈婉清迅速收起",
            "reveal_chapter_planned": 1240,
            "reveal_form": "照片上的人与主线剧情有关",
            "payload": {"content": "沈婉清实验室里的一张旧照片", "surface": "一张普通的全家福", "depth": "深层"},
            "related_char": ["沈婉清"],
            "related_item": ["旧照片"],
            "related_plot": ["身世线"],
            "importance": 0.85,
        },
        {
            "foreshadow_id": "FS-037",
            "type": "信息伏笔",
            "plant_chapter": 1210,
            "plant_location": "AI创新联盟的创始文件",
            "plant_form": "文件中的发起人签名并非林默",
            "reveal_chapter_planned": 1440,
            "reveal_form": "AI创新联盟的真正发起人身份揭晓",
            "payload": {"content": "AI创新联盟的真正发起人不是林默", "surface": "一份公开的联盟声明", "depth": "深层"},
            "related_char": ["林默"],
            "related_item": [],
            "related_plot": ["科技线"],
            "importance": 0.9,
        },
        {
            "foreshadow_id": "FS-038",
            "type": "情感伏笔",
            "plant_chapter": 280,
            "plant_location": "深夜的办公室",
            "plant_form": "林默独自流泪，但第二天若无其事",
            "reveal_chapter_planned": 1350,
            "reveal_form": "揭示林默内心深处的孤独与脆弱",
            "payload": {"content": "林默在某个深夜独自流泪", "surface": "工作压力", "depth": "深层"},
            "related_char": ["林默"],
            "related_item": [],
            "related_plot": ["情感线"],
            "importance": 0.8,
        },
        {
            "foreshadow_id": "FS-039",
            "type": "结构伏笔",
            "plant_chapter": 960,
            "plant_location": "黑石集团的命名仪式",
            "plant_form": "洛克解释'黑石'的含义时，林默的表情微变",
            "reveal_chapter_planned": 1380,
            "reveal_form": "黑石集团的名字与林默2035年记忆中的某个事件有关",
            "payload": {"content": "黑石集团的名字与林默2035年记忆中的某个事件有关", "surface": "一个商业品牌的命名", "depth": "深层"},
            "related_char": ["詹姆斯·洛克", "林默"],
            "related_item": [],
            "related_plot": ["终极对决"],
            "importance": 0.95,
        },
        {
            "foreshadow_id": "FS-040",
            "type": "人物伏笔",
            "plant_chapter": 980,
            "plant_location": "洛克的私人办公室",
            "plant_form": "洛克墙上挂着一幅中国水墨画",
            "reveal_chapter_planned": 1320,
            "reveal_form": "洛克年轻时曾在中国生活过",
            "payload": {"content": "詹姆斯·洛克年轻时曾在中国生活过", "surface": "一幅装饰画", "depth": "中层"},
            "related_char": ["詹姆斯·洛克"],
            "related_item": [],
            "related_plot": ["身世线"],
            "importance": 0.75,
        },
        {
            "foreshadow_id": "FS-041",
            "type": "信息伏笔",
            "plant_chapter": 2,
            "plant_location": "林默穿越后的第一反应",
            "plant_form": "林默对穿越原因的困惑一闪而过",
            "reveal_chapter_planned": 1490,
            "reveal_form": "穿越的确切原因在终章前揭示",
            "payload": {"content": "林默穿越的确切原因从未被揭示", "surface": "一次意外", "depth": "深层"},
            "related_char": ["林默"],
            "related_item": [],
            "related_plot": ["穿越"],
            "importance": 1.0,
        },
        {
            "foreshadow_id": "FS-042",
            "type": "关系伏笔",
            "plant_chapter": 350,
            "plant_location": "团队聚餐时的细节",
            "plant_form": "所有人都看苏晴和林默的互动，苏晴迅速移开视线",
            "reveal_chapter_planned": 1400,
            "reveal_form": "苏晴的感情终于说出口",
            "payload": {"content": "苏晴对林默的感情从未说出口但所有人都知道", "surface": "同事间的关心", "depth": "中层"},
            "related_char": ["苏晴", "林默"],
            "related_item": [],
            "related_plot": ["情感线"],
            "importance": 0.7,
        },
        {
            "foreshadow_id": "FS-043",
            "type": "物品伏笔",
            "plant_chapter": 45,
            "plant_location": "陈锋擦拭军刀的特写",
            "plant_form": "军刀刀柄上刻有小字，但未展示具体内容",
            "reveal_chapter_planned": 1200,
            "reveal_form": "刻字是林默祖父的名字，揭示两家人的渊源",
            "payload": {"content": "陈锋军刀上的刻字是林默祖父的名字", "surface": "一把旧军刀", "depth": "深层"},
            "related_char": ["陈锋", "林默"],
            "related_item": ["军刀"],
            "related_plot": ["身世线"],
            "importance": 0.85,
        },
        {
            "foreshadow_id": "FS-044",
            "type": "结构伏笔",
            "plant_chapter": 390,
            "plant_location": "2015年股灾前的市场分析",
            "plant_form": "林默注意到某些异常数据，但来不及深究",
            "reveal_chapter_planned": 500,
            "reveal_form": "股灾的真正原因不是市场泡沫",
            "payload": {"content": "2015年股灾的真正原因不是市场泡沫", "surface": "正常的市场波动", "depth": "中层"},
            "related_char": ["林默"],
            "related_item": [],
            "related_plot": ["金融线"],
            "importance": 0.7,
        },
        {
            "foreshadow_id": "FS-045",
            "type": "人物伏笔",
            "plant_chapter": 945,
            "plant_location": "王志远破产后的最后一刻",
            "plant_form": "王志远说了一句话，语气中带着不甘",
            "reveal_chapter_planned": 1100,
            "reveal_form": "王志远暗中布局卷土重来",
            "payload": {"content": "王志远破产后的最后一句话暗示他不会放弃", "surface": "失败者的抱怨", "depth": "浅层"},
            "related_char": ["王志远"],
            "related_item": [],
            "related_plot": ["复仇线"],
            "importance": 0.5,
        },
        {
            "foreshadow_id": "FS-046",
            "type": "情感伏笔",
            "plant_chapter": 700,
            "plant_location": "林默的书桌抽屉",
            "plant_form": "林默写了一封信，但没有寄出，放回抽屉",
            "reveal_chapter_planned": 1480,
            "reveal_form": "信的内容揭示林默对2035年某人的深情",
            "payload": {"content": "林默给2035年某人写了一封永远不会寄出的信", "surface": "一封普通的信", "depth": "深层"},
            "related_char": ["林默"],
            "related_item": [],
            "related_plot": ["情感线"],
            "importance": 0.9,
        },
        {
            "foreshadow_id": "FS-047",
            "type": "信息伏笔",
            "plant_chapter": 150,
            "plant_location": "林氏资本的财务系统",
            "plant_form": "林默操作一个隐藏账户，只有他知道密码",
            "reveal_chapter_planned": 1000,
            "reveal_form": "秘密账户在关键时刻发挥重要作用",
            "payload": {"content": "林氏资本有一个只有林默知道的秘密账户", "surface": "正常的财务管理", "depth": "中层"},
            "related_char": ["林默"],
            "related_item": [],
            "related_plot": ["商业线"],
            "importance": 0.7,
        },
        {
            "foreshadow_id": "FS-048",
            "type": "关系伏笔",
            "plant_chapter": 720,
            "plant_location": "沈婉清与林默的私下对话",
            "plant_form": "沈婉清说了一句话后立刻后悔，表情出现裂痕",
            "reveal_chapter_planned": 1250,
            "reveal_form": "沈婉清对林默的好感是真实的",
            "payload": {"content": "沈婉清对林默的好感是真实的（内心冲突）", "surface": "间谍的专业素养", "depth": "中层"},
            "related_char": ["沈婉清", "林默"],
            "related_item": [],
            "related_plot": ["情感线"],
            "importance": 0.8,
        },
        {
            "foreshadow_id": "FS-049",
            "type": "物品伏笔",
            "plant_chapter": 1160,
            "plant_location": "AI芯片原型展示",
            "plant_form": "芯片背面刻有中文字——'回家'",
            "reveal_chapter_planned": 1350,
            "reveal_form": "芯片上的字与林默的穿越有关",
            "payload": {"content": "AI芯片原型上刻有中文字——'回家'", "surface": "一个工程师的私人标记", "depth": "深层"},
            "related_char": ["林默"],
            "related_item": ["AI芯片"],
            "related_plot": ["科技线"],
            "importance": 0.85,
        },
        {
            "foreshadow_id": "FS-050",
            "type": "结构伏笔",
            "plant_chapter": 1450,
            "plant_location": "故事接近尾声",
            "plant_form": "林默面临一个选择，暗示结局不是简单的胜利",
            "reveal_chapter_planned": 1500,
            "reveal_form": "林默选择了放弃某些东西",
            "payload": {"content": "故事的真正结局不是林默赢了，而是他选择了放弃某些东西", "surface": "一个商业决策", "depth": "深层"},
            "related_char": ["林默"],
            "related_item": [],
            "related_plot": ["终章"],
            "importance": 1.0,
        },
    ]

    inserted = 0
    for fs in new_foreshadows:
        # 检查是否已存在
        c.execute(
            "SELECT foreshadow_id FROM foreshadows WHERE foreshadow_id = ?",
            (fs["foreshadow_id"],),
        )
        if c.fetchone():
            print(f"  {fs['foreshadow_id']} 已存在，跳过")
            continue

        c.execute(
            """INSERT INTO foreshadows
               (foreshadow_id, novel_id, type, status, plant_chapter, plant_location, plant_form,
                reveal_chapter_planned, reveal_chapter_actual, reveal_form,
                payload, surface, depth,
                related_char, related_item, related_plot,
                parent_fore, child_fores, tags,
                importance, chroma_id, created_at, last_modified)
               VALUES (?, ?, ?, '已埋设', ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                fs["foreshadow_id"],
                NOVEL_ID,
                fs["type"],
                fs["plant_chapter"],
                fs["plant_location"],
                fs["plant_form"],
                fs["reveal_chapter_planned"],
                fs["reveal_form"],
                json.dumps(fs["payload"], ensure_ascii=False),
                fs["payload"].get("surface", "") if isinstance(fs["payload"], dict) else "",
                fs["payload"].get("depth", "中层") if isinstance(fs["payload"], dict) else "中层",
                json.dumps(fs["related_char"], ensure_ascii=False),
                json.dumps(fs["related_item"], ensure_ascii=False),
                json.dumps(fs["related_plot"], ensure_ascii=False),
                "",
                json.dumps([], ensure_ascii=False),
                json.dumps([], ensure_ascii=False),
                fs["importance"],
                f"{NOVEL_ID}_{fs['foreshadow_id']}",
                NOW,
                NOW,
            ),
        )
        inserted += 1

    print(f"  新增伏笔: {inserted} 条")

    # 确认总数
    c.execute("SELECT COUNT(*) FROM foreshadows WHERE novel_id = ?", (NOVEL_ID,))
    total = c.fetchone()[0]
    print(f"  伏笔总数: {total} 条")

    conn.commit()
    print("  步骤6完成")


# ─────────────────────────────────────────────────────────────
# 步骤7：增加角色冲突升级路径
# ─────────────────────────────────────────────────────────────
def step7_conflict_upgrade_paths(conn):
    step_header("步骤7: 增加角色冲突升级路径（林默 layer4_json）")
    c = conn.cursor()

    conflict_paths = {
        "conflict_upgrade_paths": {
            "vs_王志远": {
                "level1_暗流": {"chapters": "200-300", "description": "表面合作，暗中试探"},
                "level2_爆发": {"chapters": "301-500", "description": "公开竞争，互相针对"},
                "level3_裂痕": {"chapters": "501-800", "description": "联合外部势力对抗"},
                "level4_分裂": {"chapters": "801-950", "description": "终极对决，一方覆灭"},
            },
            "vs_赵明轩": {
                "level1_暗流": {"chapters": "500-700", "description": "赵明轩内心动摇，行为异常"},
                "level2_爆发": {"chapters": "701-800", "description": "背叛行为被发现"},
                "level3_裂痕": {"chapters": "801-900", "description": "背叛后果扩大"},
                "level4_分裂": {"chapters": "901-1000", "description": "赵明轩被驱逐"},
            },
            "vs_钱浩天": {
                "level1_暗流": {"chapters": "600-800", "description": "互相观察，试探实力"},
                "level2_爆发": {"chapters": "801-1050", "description": "金融战争爆发"},
                "level3_裂痕": {"chapters": "1051-1080", "description": "一方占据上风"},
                "level4_分裂": {"chapters": "1081-1100", "description": "钱浩天败北"},
            },
            "vs_詹姆斯洛克": {
                "level1_暗流": {"chapters": "950-1200", "description": "幕后操控，逐渐浮出水面"},
                "level2_爆发": {"chapters": "1201-1350", "description": "正面博弈"},
                "level3_裂痕": {"chapters": "1351-1400", "description": "终极对决"},
                "level4_分裂": {"chapters": "1401-1450", "description": "洛克认输或覆灭"},
            },
        }
    }

    layer4 = load_json_field(c, "characters", "char_id", "CHAR-001", "layer4_json")
    layer4.update(conflict_paths)
    save_json_field(c, "characters", "char_id", "CHAR-001", "layer4_json", layer4)

    print(f"  林默(CHAR-001) 已添加4条冲突升级路径:")
    for key in conflict_paths["conflict_upgrade_paths"]:
        print(f"    - {key}")

    conn.commit()
    print("  步骤7完成")


# ─────────────────────────────────────────────────────────────
# 主函数
# ─────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  数据库设定层全面修复和增强脚本")
    print(f"  执行时间: {NOW}")
    print("=" * 60)

    conn = get_db()

    try:
        # 步骤1
        deleted_arcs = step1_delete_empty_arcs(conn)

        # 步骤2
        step2_add_faction_links(conn)

        # 步骤3
        step3_enhance_characters(conn)

        # 步骤4
        step4_de_face_villains(conn)

        # 步骤5
        step5_protagonist_cost(conn)

        # 步骤6
        step6_add_foreshadows(conn)

        # 步骤7
        step7_conflict_upgrade_paths(conn)

        # ─────────────────────────────────────────────────
        # 修复摘要
        # ─────────────────────────────────────────────────
        print("\n" + "=" * 60)
        print("  修复摘要")
        print("=" * 60)
        print(f"  [步骤1] 删除空壳弧线: {deleted_arcs} 条")
        print(f"  [步骤2] 补充势力关联: 张铁军->王氏投资集团, 赵明轩->林氏资本")
        print(f"  [步骤3] 增强配角记忆点: 8个角色（陈锋/苏晴/赵明轩/李雪/钱浩天/沈婉清/洛克/张铁军）")
        print(f"  [步骤4] 反派去脸谱化: 3个角色（王志远/钱浩天/洛克）")
        print(f"  [步骤5] 主角代价设计: 林默 secrets/cracks/cost_of_power")
        print(f"  [步骤6] 新增伏笔: 30条（FS-021 ~ FS-050）")

        # 验证伏笔总数
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM foreshadows WHERE novel_id = ?", (NOVEL_ID,))
        total_fs = c.fetchone()[0]
        print(f"  [验证] 伏笔总数: {total_fs} 条")

        print(f"  [步骤7] 冲突升级路径: 4条（vs王志远/vs赵明轩/vs钱浩天/vs洛克）")

        # 验证 layer4_json
        c.execute("SELECT layer4_json FROM characters WHERE char_id = 'CHAR-001'")
        row = c.fetchone()
        if row and row[0]:
            l4 = json.loads(row[0]) if isinstance(row[0], str) else row[0]
            print(f"  [验证] 林默 layer4_json 字段数: {len(l4)}")

        print("\n  全部修复完成!")

    except Exception as e:
        print(f"\n  错误: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
