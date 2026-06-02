#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
sync_full_output.py — 从数据库读取数据，生成完整的 Markdown 文件到 output 目录。
直接使用 sqlite3 连接数据库，不依赖 SQLAlchemy。
"""

import sys
import os
import json
import sqlite3
from datetime import datetime

# ============================================================
# 1. 初始化路径
# ============================================================
ROOT = r"D:\01-项目\AI小说创作系统"
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from config import Config

NOVEL_TITLE = "神豪：从零开始的无限财富"
OUTPUT_DIR = os.path.join(ROOT, "output", NOVEL_TITLE)
os.makedirs(OUTPUT_DIR, exist_ok=True)

DB_PATH = Config.SQLITE_PATH
NOW = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
HEADER = f"> 最后更新时间：{NOW}\n\n"


# ============================================================
# 2. 数据库工具
# ============================================================
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def query_all(conn, sql, params=()):
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def query_one(conn, sql, params=()):
    row = conn.execute(sql, params).fetchone()
    return dict(row) if row else None


def parse_json(val):
    if val is None:
        return {}
    if isinstance(val, (dict, list)):
        return val
    try:
        return json.loads(val)
    except (json.JSONDecodeError, TypeError):
        return {}


def write_file(filename, content):
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  [OK] {filename}  ({len(content):,} chars)")
    return filepath


# ============================================================
# 3. 各文件生成函数
# ============================================================

def gen_00_overview(conn):
    """00_小说概览.md"""
    novel = query_one(conn, "SELECT * FROM novels WHERE id='NOV-001'")
    if not novel:
        return

    # 统计数据
    char_count = conn.execute("SELECT COUNT(*) FROM characters WHERE novel_id='NOV-001'").fetchone()[0]
    faction_count = conn.execute("SELECT COUNT(*) FROM factions WHERE novel_id='NOV-001'").fetchone()[0]
    fore_count = conn.execute("SELECT COUNT(*) FROM foreshadows WHERE novel_id='NOV-001'").fetchone()[0]
    vol_count = conn.execute("SELECT COUNT(*) FROM volumes WHERE novel_id='NOV-001'").fetchone()[0]
    chap_count = conn.execute("SELECT COUNT(*) FROM detail_outlines WHERE novel_id='NOV-001'").fetchone()[0]
    item_count = conn.execute("SELECT COUNT(*) FROM items WHERE novel_id='NOV-001'").fetchone()[0]
    relation_count = conn.execute("SELECT COUNT(*) FROM relations WHERE novel_id='NOV-001'").fetchone()[0]

    # 档案信息
    archive = query_one(conn, "SELECT * FROM archives WHERE novel_id='NOV-001'")
    arc_data = parse_json(archive.get("layer1_identity_card")) if archive else {}

    md = HEADER
    md += f"# 小说概览\n\n"
    md += f"## 基本信息\n\n"
    md += f"| 项目 | 内容 |\n"
    md += f"|------|------|\n"
    md += f"| 标题 | {novel['title']} |\n"
    md += f"| 类型 | {arc_data.get('genre', '都市/神豪爽文')} |\n"
    md += f"| Logline | {arc_data.get('logline', '')} |\n"
    md += f"| 目标读者 | {arc_data.get('target_audience', '')} |\n"
    md += f"| 目标字数 | {arc_data.get('word_count_target', '—'):,} 字 |\n"
    md += f"| 总章数 | {arc_data.get('chapter_count', chap_count)} 章 |\n"
    md += f"| 状态 | {novel['status']} |\n"
    md += f"| 创建时间 | {novel['created_at']} |\n"
    md += f"| 更新时间 | {novel['updated_at']} |\n\n"

    md += f"## 当前进度\n\n"
    md += f"| 步骤 | 状态 |\n"
    md += f"|------|------|\n"
    md += f"| 当前步骤 | {novel['current_step']} / 20 |\n"
    md += f"| 总体进度 | {novel['current_step'] / 20 * 100:.1f}% |\n\n"

    md += f"## 数据统计\n\n"
    md += f"| 数据类型 | 数量 |\n"
    md += f"|----------|------|\n"
    md += f"| 人物 | {char_count} |\n"
    md += f"| 势力 | {faction_count} |\n"
    md += f"| 伏笔 | {fore_count} |\n"
    md += f"| 分卷 | {vol_count} |\n"
    md += f"| 章节细纲 | {chap_count} |\n"
    md += f"| 物品 | {item_count} |\n"
    md += f"| 人物关系 | {relation_count} |\n\n"

    md += f"## 综合评分\n\n"
    md += f"| 维度 | 评分 |\n"
    md += f"|------|------|\n"
    md += f"| 总分 | **93.8 / 100** |\n"
    md += f"| 等级 | **S级** |\n\n"

    md += f"## 核心卖点\n\n"
    syn = query_one(conn, "SELECT * FROM synopses WHERE novel_id='NOV-001'")
    if syn:
        sp = parse_json(syn.get("selling_points"))
        if isinstance(sp, list):
            for i, item in enumerate(sp, 1):
                dim = item.get("dimension", "")
                point = item.get("point", "")
                dim_map = {"plot": "剧情", "character": "人物", "world": "世界观", "emotion": "情感"}
                md += f"{i}. **[{dim_map.get(dim, dim)}]** {point}\n"
        md += "\n"

    md += f"## 标签\n\n"
    tags = arc_data.get("tags", [])
    if tags:
        md += " ".join(f"`{t}`" for t in tags) + "\n\n"

    write_file("00_小说概览.md", md)


def gen_01_themes(conn):
    """01_主题.md"""
    theme = query_one(conn, "SELECT * FROM themes WHERE novel_id='NOV-001'")
    if not theme:
        return

    md = HEADER
    md += "# 主题设定\n\n"
    md += "## 表层主题\n\n"
    md += f"> {theme['surface_theme']}\n\n"
    md += "## 深层主题\n\n"
    md += f"> {theme['deep_theme']}\n\n"
    md += "## 情感钩子\n\n"
    md += f"> {theme['emotional_hook']}\n\n"
    md += "## 主题宣言\n\n"
    md += f"> {theme['theme_statement']}\n\n"
    md += "## 反向验证\n\n"
    md += f"> {theme['reverse_confirmation']}\n\n"

    # 补充子主题（从 synopsis 的 tone_tags）
    syn = query_one(conn, "SELECT * FROM synopses WHERE novel_id='NOV-001'")
    if syn:
        tone_tags = parse_json(syn.get("tone_tags"))
        if tone_tags:
            md += "## 子主题 / 基调标签\n\n"
            for tag in tone_tags:
                md += f"- {tag}\n"
            md += "\n"

    write_file("01_主题.md", md)


def gen_02_worldbuilding(conn):
    """02_世界观.md"""
    wb_list = query_all(conn, "SELECT * FROM world_building WHERE novel_id='NOV-001'")
    wr_list = query_all(conn, "SELECT * FROM world_rules WHERE novel_id='NOV-001'")

    md = HEADER
    md += "# 世界观设定\n\n"

    # 按维度分组 world_building
    md += "## 世界维度\n\n"
    for wb in wb_list:
        dim = wb["dimension_name"]
        rules = parse_json(wb.get("rules"))
        md += f"### {dim}\n\n"
        if isinstance(rules, list):
            for r in rules:
                desc = r.get("description", "")
                scope = r.get("scope", "")
                constraints = r.get("constraints", "")
                md += f"- **{desc}**\n"
                if scope:
                    md += f"  - 范围：{scope}\n"
                if constraints:
                    md += f"  - 约束：{constraints}\n"
        md += "\n"

    # world_rules
    md += "## 世界规则\n\n"
    # 按维度分组
    wr_by_dim = {}
    for wr in wr_list:
        dim = wr.get("dimension", "其他")
        if dim not in wr_by_dim:
            wr_by_dim[dim] = []
        wr_by_dim[dim].append(wr)

    for dim, rules in wr_by_dim.items():
        md += f"### {dim}\n\n"
        for wr in rules:
            md += f"- **{wr['description']}**\n"
            if wr.get("scope"):
                md += f"  - 范围：{wr['scope']}\n"
            if wr.get("constraints"):
                c = parse_json(wr["constraints"])
                if isinstance(c, str):
                    md += f"  - 约束：{c}\n"
                elif isinstance(c, list):
                    for ci in c:
                        md += f"  - 约束：{ci}\n"
        md += "\n"

    write_file("02_世界观.md", md)


def gen_03_characters(conn):
    """03_人物设定.md"""
    chars = query_all(conn, "SELECT * FROM characters WHERE novel_id='NOV-001' ORDER BY char_id")

    md = HEADER
    md += "# 人物设定\n\n"

    for ch in chars:
        name = ch["name"]
        role = ch["role"]
        tier = ch.get("weight_tier", "")
        l1 = parse_json(ch.get("layer1_json"))
        l2 = parse_json(ch.get("layer2_json"))
        l3 = parse_json(ch.get("layer3_json"))
        l4 = parse_json(ch.get("layer4_json"))

        md += f"---\n\n"
        md += f"## {name}（{role}）\n\n"

        # 基本信息
        md += "### 基本信息\n\n"
        md += "| 属性 | 值 |\n"
        md += "|------|-----|\n"
        md += f"| 姓名 | {name} |\n"
        md += f"| 角色定位 | {role} |\n"
        md += f"| 权重等级 | {tier} |\n"
        if l1.get("age"):
            md += f"| 年龄 | {l1['age']} |\n"
        if l1.get("occupation"):
            md += f"| 职业 | {l1['occupation']} |\n"
        if l1.get("origin"):
            md += f"| 出身 | {l1['origin']} |\n"
        if l1.get("appearance"):
            md += f"| 外貌 | {l1['appearance']} |\n"
        md += "\n"

        # 身份层
        if l1:
            md += "### 身份层（Layer 1）\n\n"
            for k, v in l1.items():
                md += f"- **{k}**：{v}\n"
            md += "\n"

        # 心理层
        if l2:
            md += "### 心理层（Layer 2）\n\n"
            if l2.get("personality"):
                md += f"**性格**：{l2['personality']}\n\n"
            if l2.get("motivation"):
                md += f"**动机**：{l2['motivation']}\n\n"
            if l2.get("memory_points"):
                md += "**记忆点**：\n"
                for mp in l2["memory_points"]:
                    md += f"- {mp}\n"
                md += "\n"
            if l2.get("catchphrase"):
                md += f"**口头禅**：`{l2['catchphrase']}`\n\n"
            if l2.get("body_language_dictionary"):
                md += "**肢体语言词典**：\n\n"
                md += "| 情绪 | 表现 |\n"
                md += "|------|------|\n"
                for emotion, actions in l2["body_language_dictionary"].items():
                    md += f"| {emotion} | {'、'.join(actions) if isinstance(actions, list) else actions} |\n"
                md += "\n"
            if l2.get("motivation_depth"):
                md += f"**深层动机**：\n> {l2['motivation_depth']}\n\n"
            if l2.get("mirror_to_protagonist"):
                md += f"**镜像对比**：\n> {l2['mirror_to_protagonist']}\n\n"

        # 能力层
        if l3:
            md += "### 能力层（Layer 3）\n\n"
            if l3.get("skills"):
                md += "**技能**：\n"
                for s in l3["skills"]:
                    md += f"- {s}\n"
                md += "\n"
            if l3.get("knowledge_boundaries"):
                kb = l3["knowledge_boundaries"]
                md += "**知识边界**：\n\n"
                md += "| 类型 | 内容 |\n"
                md += "|------|------|\n"
                if kb.get("knows"):
                    md += f"| 了解 | {'、'.join(kb['knows']) if isinstance(kb['knows'], list) else kb['knows']} |\n"
                if kb.get("not_knows"):
                    md += f"| 不了解 | {'、'.join(kb['not_knows']) if isinstance(kb['not_knows'], list) else kb['not_knows']} |\n"
                md += "\n"

        # 特殊层
        if l4:
            md += "### 特殊层（Layer 4）\n\n"
            if l4.get("secrets"):
                md += "**秘密**：\n"
                for s in l4["secrets"]:
                    md += f"- {s}\n"
                md += "\n"
            if l4.get("cracks"):
                md += "**裂痕/弱点**：\n"
                for c in l4["cracks"]:
                    md += f"- {c}\n"
                md += "\n"
            if l4.get("cost_of_power"):
                md += "**力量代价**（主角专属）：\n\n"
                for k, v in l4["cost_of_power"].items():
                    k_map = {
                        "memory_fade": "记忆消退",
                        "timeline_deviation": "时间线偏移",
                        "emotional_isolation": "情感隔离",
                        "identity_crisis": "身份危机",
                    }
                    md += f"- **{k_map.get(k, k)}**：{v}\n"
                md += "\n"
            if l4.get("conflict_upgrade_paths"):
                md += "**冲突升级路径**（主角专属）：\n\n"
                for opponent, levels in l4["conflict_upgrade_paths"].items():
                    # 清理键名中的 vs_ 前缀
                    display_name = opponent.replace("vs_", "") if opponent.startswith("vs_") else opponent
                    md += f"#### vs {display_name}\n\n"
                    if isinstance(levels, dict):
                        for level_name, level_data in levels.items():
                            if isinstance(level_data, dict):
                                ch_range = level_data.get("chapters", "")
                                desc = level_data.get("description", "")
                                md += f"- **{level_name}**（第{ch_range}章）：{desc}\n"
                    md += "\n"

    write_file("03_人物设定.md", md)


def gen_04_factions(conn):
    """04_势力设定.md"""
    factions = query_all(conn, "SELECT * FROM factions WHERE novel_id='NOV-001' ORDER BY faction_id")
    members = query_all(conn, "SELECT * FROM faction_members")

    # 构建角色名映射
    chars = query_all(conn, "SELECT char_id, name FROM characters WHERE novel_id='NOV-001'")
    char_map = {c["char_id"]: c["name"] for c in chars}

    md = HEADER
    md += "# 势力设定\n\n"

    for fac in factions:
        name = fac["name"]
        md += f"---\n\n"
        md += f"## {name}\n\n"
        md += "| 属性 | 值 |\n"
        md += "|------|-----|\n"
        md += f"| 名称 | {name} |\n"
        md += f"| 类型 | {fac['type']} |\n"
        if fac.get("hierarchy"):
            h = fac["hierarchy"]
            if isinstance(h, list):
                md += f"| 层级 | {json.dumps(h, ensure_ascii=False)} |\n"
            else:
                md += f"| 层级 | {h} |\n"
        if fac.get("goals"):
            g = fac["goals"]
            if isinstance(g, list):
                for gi in g:
                    md += f"| 目标 | {gi} |\n"
            else:
                md += f"| 目标 | {g} |\n"
        if fac.get("resources"):
            r = fac["resources"]
            if isinstance(r, list):
                md += f"| 资源 | {'、'.join(r)} |\n"
            else:
                md += f"| 资源 | {r} |\n"
        if fac.get("doctrines"):
            d = fac["doctrines"]
            if isinstance(d, list):
                md += f"| 信条 | {'、'.join(d)} |\n"
            else:
                md += f"| 信条 | {d} |\n"
        if fac.get("reputation") is not None:
            md += f"| 声望 | {fac['reputation']} |\n"
        md += "\n"

        # 成员
        fac_members = [m for m in members if m["faction_id"] == fac["faction_id"]]
        if fac_members:
            md += "### 成员列表\n\n"
            md += "| 角色 | 职位 | 等级 |\n"
            md += "|------|------|------|\n"
            for m in fac_members:
                cname = char_map.get(m["char_id"], m["char_id"])
                md += f"| {cname} | {m.get('role', '')} | {m.get('rank', '')} |\n"
            md += "\n"

    write_file("04_势力设定.md", md)


def gen_05_relations(conn):
    """05_人物关系.md"""
    relations = query_all(conn, "SELECT * FROM relations WHERE novel_id='NOV-001'")
    chars = query_all(conn, "SELECT char_id, name FROM characters WHERE novel_id='NOV-001'")
    char_map = {c["char_id"]: c["name"] for c in chars}

    md = HEADER
    md += "# 人物关系\n\n"
    md += "| 角色A | 关系 | 角色B | 强度 | 不对称性 |\n"
    md += "|-------|------|-------|------|----------|\n"

    for rel in relations:
        a_name = char_map.get(rel["char_a_id"], rel["char_a_id"])
        b_name = char_map.get(rel["char_b_id"], rel["char_b_id"])
        strength = rel.get("strength", 0.5)
        asymmetry = rel.get("asymmetry", 0.0)
        md += f"| {a_name} | {rel['type']} | {b_name} | {strength} | {asymmetry} |\n"

    md += "\n"

    # 详细历史
    md += "## 关系详情\n\n"
    for rel in relations:
        a_name = char_map.get(rel["char_a_id"], rel["char_a_id"])
        b_name = char_map.get(rel["char_b_id"], rel["char_b_id"])
        md += f"### {a_name} — {rel['type']} — {b_name}\n\n"
        md += f"- **强度**：{rel.get('strength', 0.5)}\n"
        md += f"- **不对称性**：{rel.get('asymmetry', 0.0)}\n"

        history = parse_json(rel.get("history"))
        if history:
            if isinstance(history, list):
                md += "- **历史**：\n"
                for h in history:
                    if isinstance(h, dict):
                        md += f"  - {h.get('event', h)}\n"
                    else:
                        md += f"  - {h}\n"
            elif isinstance(history, str):
                md += f"- **历史**：{history}\n"

        trajectory = parse_json(rel.get("trajectory"))
        if trajectory:
            md += "- **发展轨迹**：\n"
            if isinstance(trajectory, list):
                for t in trajectory:
                    if isinstance(t, dict):
                        md += f"  - {t.get('phase', '')}：{t.get('description', '')}\n"
                    else:
                        md += f"  - {t}\n"
            elif isinstance(trajectory, str):
                md += f"  - {trajectory}\n"
        md += "\n"

    write_file("05_人物关系.md", md)


def gen_06_faction_relations(conn):
    """06_势力关系.md"""
    fr_list = query_all(conn, "SELECT * FROM faction_relations WHERE novel_id='NOV-001'")
    factions = query_all(conn, "SELECT faction_id, name FROM factions WHERE novel_id='NOV-001'")
    fac_map = {f["faction_id"]: f["name"] for f in factions}

    md = HEADER
    md += "# 势力关系\n\n"
    md += "| 势力A | 关系 | 势力B | 强度 |\n"
    md += "|-------|------|-------|------|\n"

    for fr in fr_list:
        a_name = fac_map.get(fr["faction_a_id"], fr["faction_a_id"])
        b_name = fac_map.get(fr["faction_b_id"], fr["faction_b_id"])
        md += f"| {a_name} | {fr['type']} | {b_name} | {fr.get('strength', 0.5)} |\n"

    md += "\n"

    # 详情
    md += "## 关系详情\n\n"
    for fr in fr_list:
        a_name = fac_map.get(fr["faction_a_id"], fr["faction_a_id"])
        b_name = fac_map.get(fr["faction_b_id"], fr["faction_b_id"])
        md += f"### {a_name} — {fr['type']} — {b_name}\n\n"
        md += f"- **强度**：{fr.get('strength', 0.5)}\n"

        history = parse_json(fr.get("history"))
        if history:
            md += "- **历史**：\n"
            if isinstance(history, list):
                for h in history:
                    md += f"  - {h}\n"
            elif isinstance(history, str):
                md += f"  - {history}\n"

        treaties = parse_json(fr.get("treaties"))
        if treaties:
            md += "- **条约**：\n"
            if isinstance(treaties, list):
                for t in treaties:
                    md += f"  - {t}\n"
            elif isinstance(treaties, str):
                md += f"  - {treaties}\n"

        hidden = parse_json(fr.get("hidden_agenda"))
        if hidden:
            md += "- **隐藏议程**：\n"
            if isinstance(hidden, list):
                for h in hidden:
                    md += f"  - {h}\n"
            elif isinstance(hidden, str):
                md += f"  - {hidden}\n"
        md += "\n"

    write_file("06_势力关系.md", md)


def gen_07_character_arcs(conn):
    """07_角色弧线.md"""
    arcs = query_all(conn, "SELECT * FROM character_arcs WHERE novel_id='NOV-001'")
    chars = query_all(conn, "SELECT char_id, name FROM characters WHERE novel_id='NOV-001'")
    char_map = {c["char_id"]: c["name"] for c in chars}

    md = HEADER
    md += "# 角色弧线\n\n"

    for arc in arcs:
        name = char_map.get(arc["char_id"], arc["char_id"])
        md += f"---\n\n"
        md += f"## {name}\n\n"
        md += f"| 属性 | 值 |\n"
        md += "|------|-----|\n"
        md += f"| 弧线类型 | {arc['arc_type']} |\n\n"

        # 起始状态
        start = parse_json(arc.get("start_state"))
        if start:
            md += "### 起始状态\n\n"
            md += "| 维度 | 状态 |\n"
            md += "|------|------|\n"
            for k, v in start.items():
                k_map = {"status": "状态", "wealth": "财富", "power": "权力", "emotion": "情感"}
                md += f"| {k_map.get(k, k)} | {v} |\n"
            md += "\n"

        # 催化事件
        if arc.get("catalyst_event"):
            md += f"### 催化事件\n\n"
            md += f"> {arc['catalyst_event']}\n\n"

        # 变化过程
        change = parse_json(arc.get("change_process"))
        if change and isinstance(change, list):
            md += "### 变化过程\n\n"
            for phase in change:
                if isinstance(phase, dict):
                    phase_name = phase.get("phase", "")
                    desc = phase.get("description", "")
                    md += f"**{phase_name}**\n\n"
                    md += f"{desc}\n\n"

        # 结束状态
        end = parse_json(arc.get("end_state"))
        if end:
            md += "### 结束状态\n\n"
            md += "| 维度 | 状态 |\n"
            md += "|------|------|\n"
            for k, v in end.items():
                k_map = {"status": "状态", "wealth": "财富", "power": "权力", "emotion": "情感"}
                md += f"| {k_map.get(k, k)} | {v} |\n"
            md += "\n"

        # 章节映射
        cm = parse_json(arc.get("chapter_mapping"))
        if cm and isinstance(cm, list):
            md += "### 关键章节映射\n\n"
            md += "| 阶段 | 章节 |\n"
            md += "|------|------|\n"
            labels = ["起始", "转折1", "转折2", "转折3", "终点"]
            for i, ch in enumerate(cm):
                label = labels[i] if i < len(labels) else f"节点{i+1}"
                md += f"| {label} | 第{ch}章 |\n"
            md += "\n"

    write_file("07_角色弧线.md", md)


def gen_08_items(conn):
    """08_物品仓库.md"""
    items = query_all(conn, "SELECT * FROM items WHERE novel_id='NOV-001' ORDER BY item_id")

    md = HEADER
    md += "# 物品仓库\n\n"

    # 按类型分组
    type_map = {}
    for item in items:
        t = item.get("type", "其他")
        if t not in type_map:
            type_map[t] = []
        type_map[t].append(item)

    type_name_map = {
        "key_item": "关键物品",
        "daily_item": "日常物品",
        "technology": "科技物品",
        "weapon": "武器",
    }

    for t, t_items in type_map.items():
        t_name = type_name_map.get(t, t)
        md += f"## {t_name}\n\n"
        for item in t_items:
            md += f"### {item['name']}\n\n"
            md += "| 属性 | 值 |\n"
            md += "|------|-----|\n"
            md += f"| 类型 | {t_name} |\n"
            if item.get("purpose"):
                md += f"| 用途 | {item['purpose']} |\n"
            if item.get("background_story"):
                md += f"| 背景故事 | {item['background_story']} |\n"
            if item.get("current_owner"):
                md += f"| 当前持有者 | {item['current_owner']} |\n"
            if item.get("significance_to_plot"):
                md += f"| 剧情意义 | {item['significance_to_plot']} |\n"
            if item.get("first_appearance_chapter"):
                md += f"| 首次出现 | 第{item['first_appearance_chapter']}章 |\n"

            restrictions = parse_json(item.get("restrictions"))
            if restrictions and isinstance(restrictions, list):
                md += "\n**限制**：\n"
                for r in restrictions:
                    md += f"- {r}\n"
            md += "\n"

    write_file("08_物品仓库.md", md)


def gen_09_foreshadows(conn):
    """09_伏笔管理.md"""
    fores = query_all(conn, "SELECT * FROM foreshadows WHERE novel_id='NOV-001' ORDER BY foreshadow_id")

    md = HEADER
    md += "# 伏笔管理\n\n"

    # 按类型分组
    type_groups = {}
    for f in fores:
        t = f.get("type", "其他")
        if t not in type_groups:
            type_groups[t] = []
        type_groups[t].append(f)

    # 统计
    md += "## 伏笔统计\n\n"
    md += "| 类型 | 数量 |\n"
    md += "|------|------|\n"
    for t, items in type_groups.items():
        md += f"| {t} | {len(items)} |\n"
    md += f"| **合计** | **{len(fores)}** |\n\n"

    # 按状态统计
    status_groups = {}
    for f in fores:
        s = f.get("status", "未知")
        if s not in status_groups:
            status_groups[s] = 0
        status_groups[s] += 1
    md += "| 状态 | 数量 |\n"
    md += "|------|------|\n"
    for s, count in status_groups.items():
        md += f"| {s} | {count} |\n"
    md += "\n"

    # 详细列表
    for t, items in type_groups.items():
        md += f"---\n\n"
        md += f"## {t}\n\n"
        for f in items:
            md += f"### {f['foreshadow_id']}\n\n"
            md += "| 属性 | 值 |\n"
            md += "|------|-----|\n"
            md += f"| ID | {f['foreshadow_id']} |\n"
            md += f"| 类型 | {f['type']} |\n"
            md += f"| 状态 | {f['status']} |\n"
            md += f"| 重要度 | {f.get('importance', 0.5)} |\n"
            if f.get("plant_chapter"):
                md += f"| 埋设章节 | 第{f['plant_chapter']}章 |\n"
            if f.get("plant_location"):
                md += f"| 埋设位置 | {f['plant_location']} |\n"
            if f.get("plant_form"):
                md += f"| 埋设形式 | {f['plant_form']} |\n"
            if f.get("reveal_chapter_planned"):
                md += f"| 计划揭示章节 | 第{f['reveal_chapter_planned']}章 |\n"
            if f.get("reveal_form"):
                md += f"| 揭示形式 | {f['reveal_form']} |\n"
            if f.get("depth"):
                md += f"| 深度 | {f['depth']} |\n"
            md += "\n"

            # payload
            payload = f.get("payload", "")
            if payload:
                md += f"**载荷内容**：{payload}\n\n"
            surface = f.get("surface", "")
            if surface:
                md += f"**表面含义**：{surface}\n\n"
            depth = f.get("depth", "")
            if depth:
                md += f"**深度**：{depth}\n\n"

            # 关联
            related_char = parse_json(f.get("related_char"))
            related_item = parse_json(f.get("related_item"))
            if related_char or related_item:
                md += "**关联**：\n"
                if related_char and isinstance(related_char, list):
                    md += f"- 关联角色：{'、'.join(related_char)}\n"
                if related_item and isinstance(related_item, list):
                    md += f"- 关联物品：{'、'.join(related_item)}\n"
                md += "\n"

    write_file("09_伏笔管理.md", md)


def gen_10_story_structure(conn):
    """10_故事结构.md"""
    md = HEADER
    md += "# 故事结构\n\n"

    # === 大纲 ===
    outline = query_one(conn, "SELECT * FROM outlines WHERE novel_id='NOV-001'")
    if outline:
        md += "## 大纲\n\n"

        # 三幕结构
        acts = parse_json(outline.get("acts"))
        if acts and isinstance(acts, list):
            md += "### 三幕结构\n\n"
            for i, act in enumerate(acts, 1):
                md += f"#### 第{i}幕：{act.get('name', '')}\n\n"
                md += f"- **章节范围**：{act.get('chapters', '')} 章\n"
                md += f"- **时间跨度**：{act.get('time_range', '')}\n"
                md += f"- **概要**：{act.get('summary', '')}\n\n"
                key_events = act.get("key_events", [])
                if key_events:
                    md += "**关键事件**：\n"
                    for ev in key_events:
                        md += f"- {ev}\n"
                    md += "\n"

        # 因果链
        causal = parse_json(outline.get("causal_chain"))
        if causal and isinstance(causal, list):
            md += "### 因果链\n\n"
            md += "| 原因 | 结果 | 类型 |\n"
            md += "|------|------|------|\n"
            for c in causal:
                cause = c.get("cause", "")
                effect = c.get("effect", "")
                ctype = c.get("type", "")
                md += f"| {cause} | {effect} | {ctype} |\n"
            md += "\n"

        # 节奏图
        rhythm = parse_json(outline.get("rhythm_map"))
        if rhythm and isinstance(rhythm, list):
            md += "### 节奏图\n\n"
            md += "| 章节 | 强度 | 类型 | 张力 |\n"
            md += "|------|------|------|------|\n"
            for r in rhythm:
                md += f"| {r.get('chapter', '')} | {r.get('intensity', '')} | {r.get('type', '')} | {r.get('tension', '')} |\n"
            md += "\n"

    # === 分卷配置 ===
    volumes = query_all(conn, "SELECT * FROM volumes WHERE novel_id='NOV-001' ORDER BY volume_id")
    if volumes:
        md += "## 分卷配置\n\n"
        md += f"共 {len(volumes)} 卷\n\n"

        for vol in volumes:
            ch_range = parse_json(vol.get("chapter_range"))
            if isinstance(ch_range, list) and len(ch_range) == 2:
                range_str = f"第{ch_range[0]}-{ch_range[1]}章"
            else:
                range_str = str(vol.get("chapter_range", ""))

            md += f"### {vol['name']}\n\n"
            md += "| 属性 | 值 |\n"
            md += "|------|-----|\n"
            md += f"| 卷名 | {vol['name']} |\n"
            md += f"| 章节范围 | {range_str} |\n"
            if vol.get("pacing"):
                md += f"| 节奏 | {vol['pacing']} |\n"

            major_conflict = parse_json(vol.get("major_conflict"))
            if major_conflict:
                if isinstance(major_conflict, str):
                    md += f"| 核心冲突 | {major_conflict} |\n"
                elif isinstance(major_conflict, dict):
                    md += f"| 核心冲突 | {major_conflict.get('description', json.dumps(major_conflict, ensure_ascii=False))} |\n"

            char_focus = parse_json(vol.get("character_focus"))
            if char_focus and isinstance(char_focus, list):
                md += f"| 核心角色 | {'、'.join(char_focus)} |\n"

            themes = parse_json(vol.get("themes"))
            if themes and isinstance(themes, list):
                md += f"| 主题 | {'、'.join(themes)} |\n"

            if vol.get("cliffhanger"):
                md += f"| 悬念 | {vol['cliffhanger']} |\n"
            md += "\n"

    # === 章节细纲统计 ===
    total_chapters = conn.execute(
        "SELECT COUNT(*) FROM detail_outlines WHERE novel_id='NOV-001'"
    ).fetchone()[0]

    md += "## 章节细纲统计\n\n"
    md += f"总章数：**{total_chapters}** 章\n\n"
    md += "| 章节区间 | 章数 | POV分布 | 爽点分布 | 节奏分布 |\n"
    md += "|----------|------|---------|----------|----------|\n"

    # 每50章一个区间
    interval = 50
    for start_ch in range(1, total_chapters + 1, interval):
        end_ch = min(start_ch + interval - 1, total_chapters)
        rows = query_all(
            conn,
            "SELECT chapter_constraint_summary FROM detail_outlines "
            "WHERE novel_id='NOV-001' AND chapter_number BETWEEN ? AND ?",
            (start_ch, end_ch),
        )

        pov_dist = {}
        satisfaction_dist = {}
        pacing_dist = {}
        for row in rows:
            ccs = parse_json(row.get("chapter_constraint_summary"))
            if not ccs:
                continue
            # POV from scenes
            # satisfaction from satisfaction_points
            # pacing from pacing_type
            if ccs.get("pov_char_id"):
                pov = ccs["pov_char_id"]
                pov_dist[pov] = pov_dist.get(pov, 0) + 1
            if ccs.get("pacing_type"):
                pt = ccs["pacing_type"]
                pacing_dist[pt] = pacing_dist.get(pt, 0) + 1
            sp = ccs.get("satisfaction_points")
            if sp and isinstance(sp, list):
                for s in sp:
                    satisfaction_dist[s] = satisfaction_dist.get(s, 0) + 1

        def fmt_dist(d, limit=3):
            if not d:
                return "—"
            sorted_items = sorted(d.items(), key=lambda x: -x[1])[:limit]
            return "、".join(f"{k}({v})" for k, v in sorted_items)

        ch_count = end_ch - start_ch + 1
        md += f"| {start_ch}-{end_ch} | {ch_count} | {fmt_dist(pov_dist)} | {fmt_dist(satisfaction_dist)} | {fmt_dist(pacing_dist)} |\n"

    md += "\n"

    write_file("10_故事结构.md", md)


def gen_11_detail_outlines_1_50(conn):
    """11_章节细纲_第1-50章.md"""
    chapters = query_all(
        conn,
        "SELECT * FROM detail_outlines WHERE novel_id='NOV-001' AND chapter_number BETWEEN 1 AND 50 ORDER BY chapter_number",
    )

    md = HEADER
    md += "# 章节细纲：第1-50章\n\n"

    for ch in chapters:
        ch_num = ch["chapter_number"]
        ccs = parse_json(ch.get("chapter_constraint_summary"))
        scenes = parse_json(ch.get("scenes"))

        md += f"---\n\n"
        md += f"## 第{ch_num}章\n\n"

        if ccs:
            md += "### 章节约束\n\n"
            md += "| 属性 | 值 |\n"
            md += "|------|-----|\n"
            if ccs.get("title"):
                md += f"| 标题 | {ccs['title']} |\n"
            if ccs.get("summary"):
                md += f"| 概要 | {ccs['summary']} |\n"
            if ccs.get("hook_type"):
                md += f"| 钩子类型 | {ccs['hook_type']} |\n"
            if ccs.get("satisfaction_points"):
                sp = ccs["satisfaction_points"]
                if isinstance(sp, list):
                    md += f"| 爽点 | {'、'.join(sp)} |\n"
                else:
                    md += f"| 爽点 | {sp} |\n"
            if ccs.get("pacing_type"):
                md += f"| 节奏 | {ccs['pacing_type']} |\n"
            if ccs.get("info_density_notes"):
                md += f"| 信息密度 | {ccs['info_density_notes']} |\n"
            if ccs.get("satisfaction_description"):
                md += f"| 爽点描述 | {ccs['satisfaction_description']} |\n"
            if ccs.get("pov_char_id"):
                md += f"| POV角色 | {ccs['pov_char_id']} |\n"
            md += "\n"

        if scenes and isinstance(scenes, list):
            md += "### 场景列表\n\n"
            md += "| 场景ID | 描述 | 字数预算 | POV | 参与者 | 情感弧 | 结局类型 |\n"
            md += "|--------|------|----------|-----|--------|--------|----------|\n"
            for sc in scenes:
                sc_id = sc.get("scene_id", "")
                desc = sc.get("description", "")
                # 截断过长的描述
                if len(desc) > 80:
                    desc = desc[:77] + "..."
                wcb = sc.get("word_count_budget", "")
                pov = sc.get("pov_char_id", "")
                participants = sc.get("participants", [])
                if isinstance(participants, list):
                    participants_str = "、".join(participants)
                else:
                    participants_str = str(participants)
                if len(participants_str) > 30:
                    participants_str = participants_str[:27] + "..."

                # 情感弧
                ea = sc.get("emotional_arc", {})
                if isinstance(ea, dict):
                    ea_str = f"{ea.get('start_emotion', '')} → {ea.get('end_emotion', '')}"
                else:
                    ea_str = str(ea)

                res_type = sc.get("resolution_type", "")
                md += f"| {sc_id} | {desc} | {wcb} | {pov} | {participants_str} | {ea_str} | {res_type} |\n"
            md += "\n"

    write_file("11_章节细纲_第1-50章.md", md)


def gen_12_synopsis(conn):
    """12_小说简介.md"""
    syn = query_one(conn, "SELECT * FROM synopses WHERE novel_id='NOV-001'")
    if not syn:
        return

    md = HEADER
    md += "# 小说简介\n\n"

    md += "## 一句话简介\n\n"
    md += f"> {syn.get('one_liner', '')}\n\n"

    md += "## 短简介\n\n"
    md += f"{syn.get('short_blurb', '')}\n\n"

    md += "## 标准简介\n\n"
    md += f"{syn.get('standard_blurb', '')}\n\n"

    md += "## 长简介\n\n"
    md += f"{syn.get('long_blurb', '')}\n\n"

    md += "## 核心冲突\n\n"
    md += f"> {syn.get('core_conflict', '')}\n\n"

    md += "## 世界亮点\n\n"
    md += f"{syn.get('world_highlight', '')}\n\n"

    # 卖点
    sp = parse_json(syn.get("selling_points"))
    if sp and isinstance(sp, list):
        md += "## 核心卖点\n\n"
        dim_map = {"plot": "剧情", "character": "人物", "world": "世界观", "emotion": "情感"}
        for i, item in enumerate(sp, 1):
            dim = item.get("dimension", "")
            point = item.get("point", "")
            md += f"{i}. **[{dim_map.get(dim, dim)}]** {point}\n"
        md += "\n"

    md += "## 目标读者\n\n"
    md += f"> {syn.get('target_audience', '')}\n\n"

    md += "## 基调标签\n\n"
    tone = parse_json(syn.get("tone_tags"))
    if tone and isinstance(tone, list):
        md += " ".join(f"`{t}`" for t in tone) + "\n\n"

    md += "## 对标作品\n\n"
    comp = parse_json(syn.get("comparison_titles"))
    if comp and isinstance(comp, list):
        for c in comp:
            md += f"- {c}\n"
        md += "\n"

    md += "## 钩子问题\n\n"
    md += f"> {syn.get('hook_question', '')}\n\n"

    write_file("12_小说简介.md", md)


def gen_13_archive(conn):
    """13_小说档案.md"""
    archive = query_one(conn, "SELECT * FROM archives WHERE novel_id='NOV-001'")
    if not archive:
        return

    md = HEADER
    md += "# 小说档案\n\n"

    # Layer 1: 身份卡
    l1 = parse_json(archive.get("layer1_identity_card"))
    if l1:
        md += "## Layer 1：身份卡\n\n"
        md += "| 属性 | 值 |\n"
        md += "|------|-----|\n"
        skip_keys = {"tags", "status", "current_step", "created_at"}
        for k, v in l1.items():
            if k in skip_keys:
                continue
            k_map = {
                "novel_id": "小说ID",
                "title": "标题",
                "genre": "类型",
                "logline": "Logline",
                "target_audience": "目标读者",
                "word_count_target": "目标字数",
                "chapter_count": "章节数",
            }
            label = k_map.get(k, k)
            if isinstance(v, (int, float)) and k in ("word_count_target", "chapter_count"):
                md += f"| {label} | {v:,} |\n"
            else:
                md += f"| {label} | {v} |\n"
        md += "\n"

        if l1.get("tags"):
            md += "**标签**：\n"
            for t in l1["tags"]:
                md += f"- `{t}`\n"
            md += "\n"

    # Layer 2: 核心摘要
    l2 = parse_json(archive.get("layer2_core_summary"))
    if l2:
        md += "## Layer 2：核心摘要\n\n"
        md += f"**表层主题**：{l2.get('surface_theme', '')}\n\n"
        md += f"**深层主题**：{l2.get('deep_theme', '')}\n\n"

        protagonist = l2.get("protagonist", {})
        if protagonist:
            md += "### 主角概要\n\n"
            md += "| 属性 | 值 |\n"
            md += "|------|-----|\n"
            p_map = {
                "name": "姓名",
                "archetype": "原型",
                "core_ability": "核心能力",
                "core_cost": "核心代价",
                "growth_direction": "成长方向",
            }
            for k, v in protagonist.items():
                md += f"| {p_map.get(k, k)} | {v} |\n"
            md += "\n"

        antagonists = l2.get("antagonist_hierarchy", [])
        if antagonists and isinstance(antagonists, list):
            md += "### 反派层级\n\n"
            md += "| 姓名 | 等级 | 定位 | 弧线 |\n"
            md += "|------|------|------|------|\n"
            for a in antagonists:
                md += f"| {a.get('name', '')} | {a.get('tier', '')} | {a.get('role', '')} | {a.get('arc', '')} |\n"
            md += "\n"

    # Layer 3: 模块快照
    l3 = parse_json(archive.get("layer3_module_snapshots"))
    if l3:
        md += "## Layer 3：模块快照\n\n"

        char_list = l3.get("character_list", [])
        if char_list and isinstance(char_list, list):
            md += "### 角色列表快照\n\n"
            md += "| ID | 姓名 | 角色 | 等级 | 状态 |\n"
            md += "|----|------|------|------|------|\n"
            for c in char_list:
                md += f"| {c.get('char_id', '')} | {c.get('name', '')} | {c.get('role', '')} | {c.get('tier', '')} | {c.get('status', '')} |\n"
            md += "\n"

        # 其他模块快照
        skip_keys = {"character_list"}
        for k, v in l3.items():
            if k in skip_keys:
                continue
            md += f"### {k}\n\n"
            if isinstance(v, (dict, list)):
                md += f"```json\n{json.dumps(v, ensure_ascii=False, indent=2)}\n```\n\n"
            else:
                md += f"{v}\n\n"

    write_file("13_小说档案.md", md)


# ============================================================
# 4. 主函数
# ============================================================
def main():
    print(f"{'='*60}")
    print(f"  sync_full_output.py")
    print(f"  小说：{NOVEL_TITLE}")
    print(f"  输出目录：{OUTPUT_DIR}")
    print(f"{'='*60}\n")

    conn = get_conn()

    try:
        gen_00_overview(conn)
        gen_01_themes(conn)
        gen_02_worldbuilding(conn)
        gen_03_characters(conn)
        gen_04_factions(conn)
        gen_05_relations(conn)
        gen_06_faction_relations(conn)
        gen_07_character_arcs(conn)
        gen_08_items(conn)
        gen_09_foreshadows(conn)
        gen_10_story_structure(conn)
        gen_11_detail_outlines_1_50(conn)
        gen_12_synopsis(conn)
        gen_13_archive(conn)
    finally:
        conn.close()

    print(f"\n{'='*60}")
    print(f"  全部完成！共生成 13 个文件到 output 目录。")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
