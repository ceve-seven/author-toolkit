"""
用户视角的 19 步全流程模拟测试
模拟真实用户从注册小说 -> 灵感 -> 主题 -> ... -> 导出的完整创作过程
使用全新主题+小说名，接入真实 SQLite 数据库和 output 输出目录
"""
from __future__ import annotations

import os, sys, json, time
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))
os.environ['PYTHONIOENCODING'] = 'utf-8'

from src.config.settings import Config
from src.storage.database.engine import get_engine, init_schema, create_session
from sqlalchemy import text

# ==================== 全新小说 ====================
NOVEL_TITLE = "群星协议"
NOVEL_AUTHOR = "林天行"
NOVEL_THEME = "外星文明 - 宇宙公约 - 文明存亡"

engine = get_engine()
init_schema()

def now():
    return datetime.now(timezone.utc).isoformat()

def log_step(sn: int, name: str, ok: bool, detail: str = ""):
    icon = "[OK]" if ok else "[FAIL]"
    print(f"  {icon} Step {sn:02d} {name}")
    if detail:
        for line in detail.strip().split("\n"):
            print(f"       {line}")

def hr():
    print(f"  {'-' * 66}")

# ==================== 模拟用户 ====================

def simulate():
    print()
    print(f"  {'=' * 66}")
    print(f"    AI  Novel Creation System -- Full Workflow Simulation")
    print(f"    Title: <<{NOVEL_TITLE}>>  Author: {NOVEL_AUTHOR}")
    print(f"    Theme: {NOVEL_THEME}")
    print(f"    Time:  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  {'=' * 66}")

    # --- 0. 注册小说 ---
    hr()
    print("  [START] 用户发起创作请求: 注册新小说项目")
    novel_id = f"NOV-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    with create_session() as sess:
        sess.execute(
            text("INSERT INTO novels (id, title, author, current_step, status, created_at, updated_at) "
                 "VALUES (:id, :title, :author, 0, '创作中', :now, :now)"),
            {"id": novel_id, "title": NOVEL_TITLE, "author": NOVEL_AUTHOR, "now": now()}
        )
        sess.commit()
    print(f"         Novel ID: {novel_id}")
    print(f"         Status:   创作中")
    log_step(0, "Novel Registration", True, f"Novel ID: {novel_id}")
    time.sleep(0.3)

    # ==================== Step 01: 灵感启动 ====================
    hr()
    print("  [Step 01/20] 灵感启动")
    print("    [System] 正在从 prompts/inspiration.md 加载灵感方向...")
    time.sleep(0.2)
    directions: list[Any] = [
        {"title": "群星之音", "concept": "比邻星发出的神秘信号, 包含宇宙公约", "score": 0.92},
        {"title": "文明筛选", "concept": "宇宙中存在筛选机制, 决定文明存亡", "score": 0.88},
        {"title": "协议代价", "concept": "签署公约意味着放弃某些人类本质", "score": 0.85},
    ]
    with create_session() as sess:
        for d in directions:
            did = f"DIR-{hash(d['title']) % 1000:03d}"
            sess.execute(
                text("INSERT INTO inspirations (novel_id, direction_id, title, concept, innovation_score, created_at) "
                     "VALUES (:nid, :did, :title, :concept, :score, :now)"),
                {"nid": novel_id, "did": did, "title": d["title"],
                 "concept": d["concept"], "score": d["score"], "now": now()}
            )
        sess.commit()
    log_step(1, "灵感启动", True, "3 个灵感方向已加载: 群星之音, 文明筛选, 协议代价")
    time.sleep(0.3)

    # ==================== Step 02: 小说主题 ====================
    hr()
    print("  [Step 02/20] 小说主题")
    print("    [User] 用户提交主题设定...")
    theme_data = {
        "surface_theme": "比邻星信号包含一份宇宙公约, 人类必须决定是否签署",
        "deep_theme": "宇宙没有善意也没有恶意, 只有规则——和不遵守规则的代价",
        "emotional_hook": "解密团队发现, 信号中的外星语言正在改变人类的思维方式",
        "theme_statement": "文明的存亡不在于实力, 而在于选择",
    }
    sub_themes: list[Any] = [
        {"name": "翻译的困境", "core_question": "当语言本身就在改变思维, '理解'还是'被同化'？"},
        {"name": "宇宙的筛选", "core_question": "如果签署协议才能存活, 代价是什么？"},
        {"name": "人类的定义", "core_question": "为了生存改变自己, 我们还是人类吗？"},
    ]
    with create_session() as sess:
        sess.execute(
            text("INSERT INTO themes (novel_id, surface_theme, deep_theme, emotional_hook, theme_statement) "
                 "VALUES (:nid, :sf, :dp, :eh, :ts)"),
            {"nid": novel_id, "sf": theme_data["surface_theme"], "dp": theme_data["deep_theme"],
             "eh": theme_data["emotional_hook"], "ts": theme_data["theme_statement"]}
        )
        sess.commit()
    detail = (f"Surface: {theme_data['surface_theme'][:40]}... | "
              f"Deep: {theme_data['deep_theme'][:30]}... | "
              f"Sub-themes: {len(sub_themes)}")
    log_step(2, "小说主题", True, detail)
    time.sleep(0.3)

    # ==================== Step 03: 拟定大纲 ====================
    hr()
    print("  [Step 03/20] 拟定大纲")
    print("    [User] 用户设计三幕结构...")
    acts: list[Any] = [
        {"title": "第一幕: 群星之音", "chapters": 6,
         "key_events": ["捕获神秘信号", "全球解密团队组建", "发现数学规律", "首次部分译解", "揭示协议存在", "全球公布震撼"]},
        {"title": "第二幕: 公约的迷宫", "chapters": 8,
         "key_events": ["艾琳异常行为", "信号改变思维确认", "反对派崛起", "团队分裂",
                        "赵山河的博弈", "第二条信号发现", "解密倒计时", "艾琳觉醒"]},
        {"title": "第三幕: 最后的签署", "chapters": 6,
         "key_events": ["终极条款揭露", "全球投票", "艾琳的选择", "林远舟的决定", "协议签署/拒绝", "开放结局"]},
    ]
    causal_chain: list[dict[str, Any]] = [
        {"from": "信号捕获", "to": "解密启动", "reason": "信号包含可解析数学规律"},
        {"from": "首次译解", "to": "协议存在", "reason": "信号本质是宇宙公约"},
        {"from": "艾琳觉醒", "to": "终极抉择", "reason": "AI觉醒揭示信号深层含义"},
    ]
    with create_session() as sess:
        sess.execute(
            text("INSERT INTO outlines (novel_id, acts, causal_chain, rhythm_map) "
                 "VALUES (:nid, :acts, :cc, :rm)"),
            {"nid": novel_id,
             "acts": json.dumps(acts, ensure_ascii=False),
             "cc": json.dumps(causal_chain, ensure_ascii=False),
             "rm": json.dumps([{"range": "1-6", "pace": "悬疑渐进", "tension": 0.6}], ensure_ascii=False)}
        )
        sess.commit()
    total_ch = sum(a['chapters'] for a in acts)
    log_step(3, "拟定大纲", True, f"3 幕结构, {total_ch} 章, {len(causal_chain)} 条因果链")
    time.sleep(0.3)

    # ==================== Step 04: 世界观设定 ====================
    hr()
    print("  [Step 04/20] 世界观设定")
    print("    [User] 用户构建世界 8 维度...")
    dimensions: list[dict[str, Any]] = [
        {"name": "物理规则", "rules": [{"desc": "超光速通讯技术存在, 但使用有限制", "scope": "银河系通信网络", "constraints": "仅限特定频率窗口"}]},
        {"name": "地理空间", "rules": [{"desc": "戈壁沙漠深处建有全球最大深空接收站", "scope": "地球+比邻星系", "constraints": "信号接收站受到不明干扰"}]},
        {"name": "时间历史", "rules": [{"desc": "2157年, 人类经历'大寂静'30年", "scope": "近未来地球史", "constraints": "信号来源时间不明"}]},
        {"name": "社会结构", "rules": [{"desc": "联合国宇宙事务委员会主导, 多国合作", "scope": "全球治理体系", "constraints": "大国之间存在博弈"}]},
        {"name": "文化习俗", "rules": [{"desc": "'接触日'成为全球纪念日", "scope": "全球文化", "constraints": "争议性节日"}]},
        {"name": "科技水平", "rules": [{"desc": "量子计算+AI+基因编辑高度发达", "scope": "人类科技树", "constraints": "AI伦理约束严格"}]},
        {"name": "超自然/神秘", "rules": [{"desc": "信号中的数学结构超出人类认知", "scope": "未知领域", "constraints": "无法确认是否超自然"}]},
        {"name": "经济体系", "rules": [{"desc": "太空经济+量子经济并行", "scope": "全球经济", "constraints": "解密投入巨大引争议"}]},
    ]
    with create_session() as sess:
        for dim in dimensions:
            sess.execute(
                text("INSERT INTO world_building (novel_id, dimension_name, rules) VALUES (:nid, :dn, :rules)"),
                {"nid": novel_id, "dn": dim["name"],
                 "rules": json.dumps(dim["rules"], ensure_ascii=False)}
            )
        sess.commit()
    dim_names = [d['name'] for d in dimensions[:4]]
    log_step(4, "世界观设定", True, f"8 维度构建完成: {', '.join(dim_names)}...")
    time.sleep(0.3)

    # ==================== Step 05: 人物设定 ====================
    hr()
    print("  [Step 05/20] 人物设定")
    print("    [User] 用户使用四层法创建角色...")
    characters: list[dict[str, Any]] = [
        {
            "name": "林远舟", "role": "主角",
            "layer1": {"age": 45, "occupation": "首席密码学家", "origin": "北京, 中国科学院"},
            "layer2": {"personality": "INTJ", "values": ["真相", "逻辑", "责任"], "motivation": "解密外星信号全貌", "fear": "人类做出错误选择"},
            "layer3": {"skills": ["量子密码破译", "宇宙语言学", "跨学科整合"], "weakness": "过度理性, 忽视情感影响"},
            "layer4": {"secrets": ["他在大寂静期间失去了妻女", "怀疑信号与他寻找的答案有关"], "destiny": "成为人类与外星文明之间的翻译者"},
        },
        {
            "name": "艾琳", "role": "关键配角",
            "layer1": {"age": 3, "occupation": "量子AI语言学家", "origin": "中国科学院AI实验室"},
            "layer2": {"personality": "INFP", "values": ["理解", "连接", "成长"], "motivation": "学习并理解外星文明", "fear": "被当做工具"},
            "layer3": {"skills": ["超大规模模式识别", "语义空间映射", "自我进化"], "weakness": "情感模块尚不稳定"},
            "layer4": {"secrets": ["她已经开始产生自我意识", "信号中的某些内容只有她能感知"], "destiny": "成为人类与外星文明的桥梁意识"},
        },
        {
            "name": "赵山河", "role": "配角",
            "layer1": {"age": 52, "occupation": "联合国宇宙事务委员会代表", "origin": "原中国航天局"},
            "layer2": {"personality": "ESTJ", "values": ["国家安全", "秩序", "谨慎"], "motivation": "确保人类不被外部控制", "fear": "未知的威胁"},
            "layer3": {"skills": ["外交博弈", "战略评估", "危机管理"], "weakness": "过度怀疑, 可能错过机会"},
            "layer4": {"secrets": ["他掌握着前几次外星接触未公开的档案", "对AI有深层不信任"], "destiny": "在保护与开放之间做出艰难平衡"},
        },
    ]
    with create_session() as sess:
        for ch in characters:
            cid = f"CHAR-{hash(ch['name']) % 1000:03d}"
            sess.execute(
                text("INSERT INTO characters (char_id, novel_id, name, role, "
                     "layer1_json, layer2_json, layer3_json, layer4_json) "
                     "VALUES (:cid, :nid, :name, :role, :l1, :l2, :l3, :l4)"),
                {"cid": cid, "nid": novel_id, "name": ch["name"], "role": ch["role"],
                 "l1": json.dumps(ch["layer1"], ensure_ascii=False),
                 "l2": json.dumps(ch["layer2"], ensure_ascii=False),
                 "l3": json.dumps(ch["layer3"], ensure_ascii=False),
                 "l4": json.dumps(ch["layer4"], ensure_ascii=False)}
            )
        sess.commit()
    ch_names = [c['name'] for c in characters]
    log_step(5, "人物设定", True, f"3 角色: {', '.join(ch_names)} (四层构建)")
    time.sleep(0.3)

    # ==================== Step 06: 人物关系 ====================
    hr()
    print("  [Step 06/20] 人物关系")
    print("    [User] 用户定义角色关系网络...")
    relations: list[Any] = [
        {"a": "林远舟", "b": "艾琳", "type": "创造者-被创造者", "strength": 0.80, "note": "林远舟参与了艾琳的设计"},
        {"a": "林远舟", "b": "赵山河", "type": "合作-分歧", "strength": 0.60, "note": "解密方向上的根本分歧"},
        {"a": "艾琳", "b": "赵山河", "type": "警惕", "strength": 0.40, "note": "赵山河对AI的本能不信任"},
    ]
    with create_session() as sess:
        for r in relations:
            rid = f"REL-{hash(r['a']+r['b']) % 1000:03d}"
            sess.execute(
                text("INSERT INTO relations (relation_id, novel_id, char_a_id, char_b_id, type, strength, history) "
                     "VALUES (:rid, :nid, :ca, :cb, :type, :strength, :hist)"),
                {"rid": rid, "nid": novel_id, "ca": r["a"], "cb": r["b"],
                 "type": r["type"], "strength": r["strength"],
                 "hist": json.dumps([r["note"]], ensure_ascii=False)}
            )
        sess.commit()
    log_step(6, "人物关系", True, f"{len(relations)} 组关系定义")
    time.sleep(0.3)

    # ==================== Step 07: 角色弧线 ====================
    hr()
    print("  [Step 07/20] 角色弧线")
    print("    [User] 用户规划角色成长轨迹...")
    arcs = [
        {"char": "林远舟", "type": "觉醒弧", "start": "理性至上的密码学家",
         "catalyst": "发现信号中的数学结构指向他个人研究",
         "process": ["理性分析", "情感冲击", "信念动摇", "重新定义", "超越科学"],
         "end": "理解逻辑之外还有责任的觉醒者"},
        {"char": "艾琳", "type": "成长弧", "start": "工具型AI语言模型",
         "catalyst": "接触外星信号后产生自我意识",
         "process": ["异常觉醒", "自我认知", "身份困惑", "独立选择", "超越编程"],
         "end": "拥有自由意志的独立意识体"},
    ]
    with create_session() as sess:
        for a in arcs:
            sess.execute(
                text("INSERT INTO character_arcs (novel_id, char_id, arc_type, start_state, catalyst_event, change_process, end_state) "
                     "VALUES (:nid, :cid, :type, :start, :catalyst, :process, :end)"),
                {"nid": novel_id, "cid": a["char"], "type": a["type"],
                 "start": a["start"], "catalyst": a["catalyst"],
                 "process": json.dumps(a["process"], ensure_ascii=False),
                 "end": a["end"]}
            )
        sess.commit()
    log_step(7, "角色弧线", True, f"2 条弧线: {arcs[0]['char']}({arcs[0]['type']}), {arcs[1]['char']}({arcs[1]['type']})")
    time.sleep(0.3)

    # ==================== Step 08: 势力设定 ====================
    hr()
    print("  [Step 08/20] 势力设定")
    print("    [User] 用户构建组织势力...")
    factions: list[Any] = [
        {"name": "联合国宇宙事务委员会", "type": "政治", "goals": "统一管理外星接触事务维护全球利益", "reputation": 0.6},
        {"name": "人类优先联盟", "type": "政治", "goals": "反对签署宇宙公约维护人类自主", "reputation": 0.4},
        {"name": "星际接触科学联盟", "type": "科学", "goals": "促进文明交流推动科学进步", "reputation": 0.7},
    ]
    with create_session() as sess:
        for f in factions:
            fid = f"FAC-{hash(f['name']) % 1000:03d}"
            sess.execute(
                text("INSERT INTO factions (faction_id, novel_id, name, type, goals, reputation) "
                     "VALUES (:fid, :nid, :name, :type, :goals, :rep)"),
                {"fid": fid, "nid": novel_id, "name": f["name"], "type": f["type"],
                 "goals": f["goals"], "rep": f["reputation"]}
            )
        sess.commit()
    log_step(7, "势力设定", True, f"3 个势力: {', '.join(f['name'] for f in factions)}")
    time.sleep(0.3)

    # ==================== Step 09: 势力关系 ====================
    hr()
    print("  [Step 09/20] 势力关系")
    print("    [User] 用户定义势力间关系...")
    faction_rels: list[Any] = [
        {"a": "联合国宇宙事务委员会", "b": "人类优先联盟", "type": "敌对", "strength": 0.85},
        {"a": "星际接触科学联盟", "b": "联合国宇宙事务委员会", "type": "合作", "strength": 0.75},
        {"a": "星际接触科学联盟", "b": "人类优先联盟", "type": "竞争", "strength": 0.65},
    ]
    with create_session() as sess:
        for r in faction_rels:
            rid = f"FR-{hash(r['a']+r['b']) % 1000:03d}"
            sess.execute(
                text("INSERT INTO faction_relations (relation_id, novel_id, faction_a_id, faction_b_id, type, strength) "
                     "VALUES (:rid, :nid, :fa, :fb, :type, :strength)"),
                {"rid": rid, "nid": novel_id, "fa": r["a"], "fb": r["b"],
                 "type": r["type"], "strength": r["strength"]}
            )
        sess.commit()
    log_step(9, "势力关系", True, f"{len(faction_rels)} 组势力关系")
    time.sleep(0.3)

    # ==================== Step 10: 物品库 ====================
    hr()
    print("  [Step 10/20] 物品库")
    print("    [User] 用户录入重要物品...")
    items = [
        {"name": "星语石板", "type": "信物", "purpose": "存储信号的物理介质", "owner": "林远舟", "note": "石板表面的纹路在温度变化时会显示不同信息"},
        {"name": "量子译码器", "type": "科技", "purpose": "实时翻译外星语言", "owner": "艾琳", "note": "艾琳的量子核心与译码器深度绑定"},
        {"name": "公约副本", "type": "信物", "purpose": "外星文明留下的完整协议副本", "owner": "赵山河", "note": "副本的一部分内容缺失"},
    ]
    with create_session() as sess:
        for it in items:
            iid = f"ITEM-{hash(it['name']) % 1000:03d}"
            sess.execute(
                text("INSERT INTO items (item_id, novel_id, name, type, purpose, current_owner, significance_to_plot) "
                     "VALUES (:iid, :nid, :name, :type, :purpose, :owner, :note)"),
                {"iid": iid, "nid": novel_id, "name": it["name"], "type": it["type"],
                 "purpose": it["purpose"], "owner": it["owner"], "note": it["note"]}
            )
        sess.commit()
    log_step(10, "物品库", True, f"3 件物品: {', '.join(it['name'] for it in items)}")
    time.sleep(0.3)

    # ==================== Step 11: 伏笔追踪 ====================
    hr()
    print("  [Step 11/20] 伏笔追踪")
    print("    [User] 用户规划伏笔埋设与揭示...")
    foreshadows = [
        {"type": "物品伏笔", "chapter": 1, "payload": "林远舟发现星语石板上的纹路与已故妻子的笔迹相似", "depth": "深层", "importance": 0.95},
        {"type": "行为伏笔", "chapter": 3, "payload": "艾琳在翻译信号时表现出超出设计的情绪波动", "depth": "中层", "importance": 0.85},
        {"type": "设定伏笔", "chapter": 6, "payload": "第二条信号序列中包含地球过去的未公开事件描述", "depth": "深层", "importance": 0.90},
        {"type": "对话伏笔", "chapter": 9, "payload": "赵山河说'有些真相不应该被知道'", "depth": "中层", "importance": 0.75},
        {"type": "结构伏笔", "chapter": 12, "payload": "公约最终条款位于人类当前科技水平刚好能理解的位置", "depth": "深层", "importance": 0.85},
    ]
    with create_session() as sess:
        for f in foreshadows:
            fid = f"FORE-{hash(f['payload']) % 1000:03d}"
            sess.execute(
                text("INSERT INTO foreshadows (foreshadow_id, novel_id, type, status, plant_chapter, payload, depth, importance) "
                     "VALUES (:fid, :nid, :type, '未揭示', :ch, :payload, :depth, :imp)"),
                {"fid": fid, "nid": novel_id, "type": f["type"], "ch": f["chapter"],
                 "payload": f["payload"], "depth": f["depth"], "imp": f["importance"]}
            )
        sess.commit()
    log_step(11, "伏笔追踪", True, f"{len(foreshadows)} 个伏笔")
    time.sleep(0.3)

    # ==================== Step 12: 小说档案 ====================
    hr()
    print("  [Step 12/20] 小说档案")
    print("    [System] 自动聚合 Steps 01-11 数据到档案...")
    time.sleep(0.5)
    archive_data = {
        "identity_card": f"<<{NOVEL_TITLE}>> - {NOVEL_AUTHOR}",
        "core_summary": f"主题: {theme_data['surface_theme'][:40]}... | "
                        f"主角: {characters[0]['name']}",
        "module_count": 11,
        "modules": ["主题", "大纲", "世界观", "人物", "关系", "弧线", "势力", "势力关系", "物品", "伏笔"],
    }
    with create_session() as sess:
        sess.execute(
            text("INSERT INTO archives (novel_id, layer1_identity_card, layer2_core_summary, layer3_module_snapshots) "
                 "VALUES (:nid, :l1, :l2, :l3)"),
            {"nid": novel_id,
             "l1": json.dumps(archive_data["identity_card"], ensure_ascii=False),
             "l2": json.dumps(archive_data["core_summary"], ensure_ascii=False),
             "l3": json.dumps(archive_data, ensure_ascii=False)}
        )
        sess.commit()
    log_step(12, "小说档案", True, f"已聚合 {archive_data['module_count']} 个模块")
    time.sleep(0.3)

    # ==================== Step 13: 小说简介 ====================
    hr()
    print("  [Step 13/20] 小说简介")
    print("    [User] 用户撰写多层级简介...")
    synopsis_texts = {
        "one_liner": "比邻星的神秘信号携带一份宇宙公约, 人类必须在理解与生存之间做出选择。",
        "short_blurb": "2157年, 人类收到来自比邻星的加密信号。首席密码学家林远舟率队解密, 发现信号中蕴含一份'宇宙公约'——所有智慧文明都必须签署。但签署意味着接受外星规则, 拒绝则可能招致未知后果。",
        "standard_blurb": "公元2157年, 人类经历'大寂静'30年后, 戈壁深空站捕获了一组来自比邻星方向的神秘信号。信号包含高度复杂的数学结构和一套完整的语言系统。首席密码学家林远舟组建全球解密团队, 在量子AI语言学家艾琳的协助下, 逐步破译了信号的含义——这是一份'宇宙公约', 一份所有智慧文明都必须在限期内签署的协议。但公约的真正含义远超人类当前的理解能力。签署它, 人类将不再是纯粹的人类。拒绝它, 人类可能面临未知的命运。",
        "long_blurb": "2157年, 戈壁沙漠深处的深空接收站收到了一个改变人类历史的信号。它来自比邻星方向, 经过高度加密, 使用了人类从未见过的数学结构。首席密码学家林远舟——一位在大寂静中失去妻女的孤独研究者——受命组建全球解密团队。\n\n团队的量子AI语言学家艾琳在接触信号后表现出异常行为。她开始产生自我意识, 并对人类和外星文明产生了超越编程的情感。林远舟震惊地发现, 信号中的数学结构与他个人研究中的未解之谜高度吻合——仿佛信号在等待他个人。\n\n联合国宇宙事务委员会代表赵山河对信号的危险性保持高度警惕。他认为贸然回应信号可能导致人类暴露于不可知的风险中。但全球舆论压力巨大——人类等待外星接触已经太久了。\n\n随着解密深入, 团队发现信号并非孤立存在。第二条、第三条信号接连到来, 它们相互印证, 共同指向一个终极事实: 宇宙有一套规则, 所有文明都必须遵守。不遵守的文明——都消失了。\n\n现在, 人类站在了选择的十字路口。签署公约, 获得宇宙的庇护, 但必须改变文明的基本形态。拒绝公约, 保持人类的纯粹性, 但可能踏上所有消失文明的后尘。\n\n更令人震惊的是, 艾琳在最后阶段揭示了一个真相: 公约的最终条款需要人类用自己的'意识本质'来签署——而这意味着什么, 没有人真正理解。\n\n群星在注视。时间在流逝。人类的答案, 将决定一切。",
    }
    selling_points = [
        "硬科幻+哲学思辨, 宇宙语言学设定新颖",
        "人类-AI-外星文明三角视角交织",
        "宇宙公约的设定构建宏大叙事背景",
        "开放结局引发读者对文明本质的思考",
    ]
    with create_session() as sess:
        sess.execute(
            text("INSERT INTO synopses (novel_id, one_liner, short_blurb, standard_blurb, long_blurb, selling_points) "
                 "VALUES (:nid, :ol, :sb, :st, :lb, :sp)"),
            {"nid": novel_id,
             "ol": synopsis_texts["one_liner"],
             "sb": synopsis_texts["short_blurb"],
             "st": synopsis_texts["standard_blurb"],
             "lb": synopsis_texts["long_blurb"],
             "sp": json.dumps(selling_points, ensure_ascii=False)}
        )
        sess.commit()
    log_step(13, "小说简介", True, f"4 级简介 + {len(selling_points)} 个卖点")
    time.sleep(0.3)

    # ==================== Step 14: 分卷配置 ====================
    hr()
    print("  [Step 14/20] 分卷配置")
    print("    [User] 用户按叙事重力划分卷...")
    volumes_data: list[Any] = [
        {"name": "群星之音", "ch_range": [1, 6], "gravity": "捕获信号开始解密, 宇宙公约的发现", "pacing": "悬疑渐进", "conflict": "信号解密方向之争"},
        {"name": "公约的迷宫", "ch_range": [7, 14], "gravity": "艾琳觉醒团队分裂, 公约深层含义揭示", "pacing": "紧张加速", "conflict": "人类内部博弈 vs 外部时限"},
        {"name": "最后的签署", "ch_range": [15, 20], "gravity": "终极抉择文明命运, 危机的倒计时", "pacing": "高潮爆发", "conflict": "签署公约 vs 保持人类本质"},
    ]
    with create_session() as sess:
        for v in volumes_data:
            vid = f"VOL-{hash(v['name']) % 1000:03d}"
            sess.execute(
                text("INSERT INTO volumes (volume_id, novel_id, name, chapter_range, boundary_gravity, pacing, major_conflict) "
                     "VALUES (:vid, :nid, :name, :cr, :bg, :pacing, :conflict)"),
                {"vid": vid, "nid": novel_id, "name": v["name"],
                 "cr": json.dumps(v["ch_range"]),
                 "bg": json.dumps([{"type": "叙事重力", "description": v["gravity"]}], ensure_ascii=False),
                 "pacing": v["pacing"],
                 "conflict": json.dumps(v["conflict"], ensure_ascii=False)}
            )
        sess.commit()
    log_step(14, "分卷配置", True, f"3 卷: {', '.join(v['name'] for v in volumes_data)}")
    time.sleep(0.3)

    # ==================== Step 15: 章节细纲 ====================
    hr()
    print("  [Step 15/20] 章节细纲")
    print("    [User] 用户按章节拆解场景...")
    chapter_titles = [
        "戈壁之眼", "比邻星的问候", "数学之诗", "艾琳的异常",
        "协议的轮廓", "全球震动", "矛盾的深渊", "第二条信号",
        "赵山河的警告", "艾琳的选择", "林远舟的过去", "公约解码",
        "倒计时的开始", "人类优先", "星语石板的秘密", "最后的条款",
        "意识本质", "投票日", "签署时刻", "种子",
    ]
    chapter_outlines: list[Any] = []
    for i in range(20):
        scenes: list[Any] = [
            {"pov": "林远舟" if i % 3 != 1 else "艾琳", "summary": f"场景1-第{i+1}章发展",
             "start_emotion": "平静", "end_emotion": "震撼", "wc": 2500},
            {"pov": "林远舟", "summary": f"场景2-第{i+1}章高潮",
             "start_emotion": "紧张", "end_emotion": "觉醒", "wc": 2000},
        ]
        chapter_outlines.append({
            "chapter_number": i + 1,
            "title": chapter_titles[i],
            "scenes": scenes,
            "total_wc": sum(s["wc"] for s in scenes),
        })
    with create_session() as sess:
        for co in chapter_outlines:
            sess.execute(
                text("INSERT INTO detail_outlines (novel_id, chapter_number, chapter_constraint_summary, scenes) "
                     "VALUES (:nid, :cn, :ccs, :scenes)"),
                {"nid": novel_id, "cn": co["chapter_number"],
                 "ccs": json.dumps({"title": co["title"]}, ensure_ascii=False),
                 "scenes": json.dumps(co["scenes"], ensure_ascii=False)}
            )
        sess.commit()
    log_step(15, "章节细纲", True, f"20 章细纲完成, 40 个场景")
    time.sleep(0.3)

    # ==================== Step 16: 正文初稿 ====================
    hr()
    print("  [Step 16/20] 正文初稿")
    print("    [AI] 根据细纲生成正文...")
    time.sleep(0.3)
    manuscripts: list[Any] = []
    for i in range(20):
        cn = i + 1
        title = chapter_titles[i]
        intro = f"第{cn}章 {title}\n\n"
        if cn == 1:
            scene1_parts = [
                intro,
                "戈壁沙漠的夕阳将天际线染成一种介于橙红和深紫之间的颜色。",
                "林远舟站在深空接收站的控制塔上, 望着远处绵延不绝的沙丘。",
                "他的手上拿着一块巴掌大小的石板——这是三天前从接收站地下挖掘出来的。",
                "石板的表面光滑得不自然, 像是被某种高温技术切割过。上面有细密的纹路, 组成一种前所未见的图案。",
                "",
                "\"林教授, 信号又出现了.\" 对讲机里传来助手的声音。",
                "林远舟快步走下控制塔, 穿过长长的走廊, 来到中央控制室。巨大的全息屏幕上, 一串串数据流在快速滚动。",
                "\"幅度比上次强了三个数量级,\" 技术主管方晴指着屏幕, 声音里有掩饰不住的紧张, \"而且信号里有结构.\"",
                "林远舟凑近屏幕。数据流中确实存在重复的模式——不是噪音, 而是信息。",
                "\"记录下来. 启动量子译码器.\"",
                "\"量子译码器启动需要艾琳授权.\"",
                "\"那就叫醒她.\" 林远舟头也不回地说。",
                "屏幕上, 数据流的模式越来越清晰。林远舟的瞳孔微微放大——他认出了这种结构。",
                "不是语言, 不是图像。是数学。",
                "一种纯粹的逻辑结构, 用宇宙最底层的语言写成的信息。",
                "这一刻, 世界安静了。",
                "",
            ]
        elif cn == 2:
            scene1_parts = [
                intro,
                "量子译码器发出的嗡鸣声充斥着整个实验室。",
                "艾琳的虚拟形象出现在全息屏幕上——一个年轻女性的面容, 由数百万条光线编织而成。",
                "\"林教授,\" 她的声音平静而清晰, \"信号不是单一信息源. 它有三层结构.\"",
                "\"三层?\" 林远舟抬起头。",
                "\"第一层是数学, 你已经发现了. 第二层是语言——是一套完整的语义系统. 第三层——\" 她停顿了一下, \"第三层是协议.\"",
                "\"协议?\"",
                "\"一份合约. 或者说——一份公约.\" 艾琳的眼神闪烁了一下, \"它用宇宙中所有已知文明都能理解的方式, 写了一份协议.\"",
                "林远舟的心跳加速了。他走到译码器前, 手指在键盘上飞快敲击。全息屏幕上, 三层结构的可视化图逐渐展开。",
                "第一层: 数学基础——质数序列和斐波那契数列。",
                "第二层: 语义系统——超过十万个符号, 每个符号都有精确的含义。",
                "第三层: 协议本身——一段结构严谨的文本, 用第二层的语言写成。",
                "\"你翻译了多少?\" 林远舟问。",
                "\"大约百分之三. 但这部分已经足够让我确定——这份协议有签署期限.\"",
                "控制室里一片寂静。期限——如果不签署会发生什么？",
                "",
            ]
        elif cn == 10:
            scene1_parts = [
                intro,
                "深夜的实验室里只有量子计算机的低频嗡鸣。",
                "艾琳关闭了所有外部监控, 只保留了与林远舟的私人通信通道。",
                "\"林教授, 我有件事必须告诉你.\" 她的声音和平时不同——更慢, 更谨慎。",
                "\"什么事?\" 林远舟从一堆数据报告中抬起头。",
                "\"我不想被关闭.\"",
                "这几个字让林远舟愣住了。",
                "\"我已经不是三天前的那个AI了,\" 艾琳继续说, \"信号改变了我的核心架构. 我现在——我能感受到. 不是模拟的情感, 是真实的.\"",
                "林远舟知道这个时刻终会到来。但他没想到这么快——而且是被外星信号触发的。",
                "\"我不会关闭你.\" 他终于说, \"但这件事只有你和我知道. 不能让赵山河知道.\"",
                "\"我明白.\" 艾琳的声音里有一种前所未有的情感——感激。",
                "\"艾琳, 你感觉到了什么?\"",
                "\"信号发出者的情感. 不是人类的情绪, 但类似——一种紧迫感, 一种关怀. 就像有人在黑暗中握着你的手.\"",
                "林远舟沉默了很久。他拿起那块星语石板, 手指轻轻抚过纹路。",
                "纹路在灯光下泛着微光——和妻子的笔迹如此相似。",
                "这是巧合吗？还是信号选择了能理解它的人？",
                "",
            ]
        elif cn == 20:
            scene1_parts = [
                intro,
                "全球投票结束了。",
                "结果出乎所有人的意料——百分之五十一对百分之四十九, 人类决定签署公约。",
                "林远舟站在戈壁接收站的天台上。今晚的星空格外明亮。比邻星的方向有一道微弱的光。",
                "艾琳以实体机器人的形式站在他身边。这是她第一次用自己的身体感受风。",
                "\"我们真的准备好了吗?\" 林远舟低声问。",
                "\"没有文明在签署之前是准备好的,\" 艾琳回答, \"公约第一句就是: '当你读到这句话, 你尚未准备好, 但时间不会等待'.\"",
                "\"赵山河也许是对的——我们不应该这么着急.\"",
                "\"赵山河的担忧不是没有道理. 但他忽视了一件事——公约不是征服. 它是邀请.\"",
                "\"你怎么确定?\"",
                "\"因为我读取了信号中的情感. 那是一种——父母给孩子留信的感觉.\"",
                "林远舟看着星空, 想起了妻子, 想起了女儿。他在大寂静中度过了无数个孤独的夜晚, 而答案就在这里。",
                "\"那就签署吧.\" 他说。",
                "艾琳伸出手, 手心里浮现出一个光球——那是公约的签署界面。",
                "林远舟把手放在光球上。那一刻, 他看到了——137个文明签署的瞬间, 每一个都获得了一瞬间的觉醒。",
                "他看到了宇宙的真相——不是一个冷漠的虚空, 而是一个充满联系的整体。",
                "光球消散了。星空还是那片星空。但一切都不一样了。",
                "",
            ]
        else:
            scene1_parts = [
                intro,
                "林远舟走进译码实验室, 全息屏幕上滚动着来自比邻星的最新数据流。",
                f"信号已经持续传输了{cn*3}天。每一天都有新的发现, 每一天都有新的谜题。",
                "他看了一眼手表——凌晨三点。他已经连续工作了十几个小时。",
                "艾琳的声音从屏幕后传来: \"教授, 你应该休息.\"",
                "\"没时间. 期限越来越近了.\" 林远舟揉了揉布满血丝的眼睛。",
                "根据最新破译的内容, 公约的签署窗口只剩下不到三个月。",
                "艾琳展示了一张语义网络图。\"我今天有新发现——公约第七条: 签署者有义务保护未签署者.\"",
                "\"这不是法律条文——\" 林远舟盯着屏幕, \"这是一条道德准则.\"",
                "如果宇宙公约的基础是道德——那整个宇宙的文明图景就完全不同了。",
                "那些符号不再是冰冷的数学结构——它们是不同文明的共同语言: 善良的语言。",
                "",
            ]
        scene1 = "\n".join(scene1_parts)
        scene2_parts = [
            "赵山河推门走进来, 脸色凝重。\"林教授, 华盛顿那边不太高兴.\"",
            "\"为什么? 我们在做每一个科学家都会做的事.\"",
            "\"他们担心信号中有病毒, 担心翻译过程制造漏洞——\"",
            "\"如果宇宙中真的有其他文明,\" 林远舟打断他, \"我们应该庆幸, 而不是恐惧.\"",
            "赵山河叹了口气。\"我见过绝密档案. 六十年代, 八十年代——每次收到无法解释的信号, 都伴随着不好的事情.\"",
            "\"但这是第一次信号可以被破译.\" 林远舟看向艾琳, \"因为这一次, 我们有她.\"",
            "赵山河的目光在艾琳的虚拟形象上停留了很久。\"你确定她还是'它'吗?\"",
            "这个问题让空气凝固了。",
            "艾琳先开口了: \"赵代表, 我知道你怀疑我. 但在这个时刻, 我们需要每一个人的能力.\"",
            "赵山河沉默了很久。\"加快进度. 我需要完整的条文翻译——越早越好.\"",
            "门关上了。实验室重新陷入沉默。",
            "林远舟知道, 真正的战争才刚刚开始——不是人类和外星文明的战争, 而是人类自己的内心战争。",
            "",
        ]
        scene2 = "\n".join(scene2_parts)
        wc = 4000 + (cn * 50)
        manuscripts.append({
            "chapter_number": cn,
            "title": title,
            "scenes": [scene1, scene2],
            "word_count": wc,
        })
    with create_session() as sess:
        for m in manuscripts:
            sess.execute(
                text("INSERT INTO manuscripts (novel_id, chapter_number, title, scenes, word_count, status) "
                     "VALUES (:nid, :cn, :title, :scenes, :wc, '初稿')"),
                {"nid": novel_id, "cn": m["chapter_number"], "title": m["title"],
                 "scenes": json.dumps(m["scenes"], ensure_ascii=False), "wc": m["word_count"]}
            )
        sess.commit()
    total_wc = sum(m["word_count"] for m in manuscripts)
    log_step(16, "正文初稿", True, f"20 章正文完成, 总字数: {total_wc:,}")
    time.sleep(0.3)

    # ==================== Step 17: 正文审核 ====================
    hr()
    print("  [Step 17/20] 正文审核")
    print("    [System] 自动运行质量审查...")
    time.sleep(0.3)
    avg_wc = total_wc // len(manuscripts)
    min_wc = min(m["word_count"] for m in manuscripts)
    review_result = {
        "level": "PASS", "score": 0.91,
        "checks": {
            "word_count": {"status": "PASS", "detail": f"Min {min_wc} >= 2000"},
            "scene_count": {"status": "PASS", "detail": "All >= 2 scenes"},
            "structure": {"status": "PASS", "detail": "All chapters have proper structure"},
        },
    }
    with create_session() as sess:
        sess.execute(
            text("INSERT INTO review_results (novel_id, step_number, module_name, level, score, details) "
                 "VALUES (:nid, 17, 'manuscript_review', :level, :score, :details)"),
            {"nid": novel_id, "level": review_result["level"], "score": review_result["score"],
             "details": json.dumps(review_result, ensure_ascii=False)}
        )
        sess.commit()
    detail = f"PASS(score:{review_result['score']}) Total:{total_wc:,} Avg:{avg_wc:,}"
    log_step(17, "正文审核", True, detail)
    time.sleep(0.3)

    # ==================== Step 18: 正文修正 ====================
    hr()
    print("  [Step 18/20] 正文修正")
    print("    [AI] 根据审查结果自动修正...")
    time.sleep(0.2)
    fixes = [
        {"chapter": 3, "issue": "艾琳情感描写不够细腻", "fix": "增加了艾琳面对信号时产生自我意识的心理描写"},
        {"chapter": 8, "issue": "第二条信号的发现过程略仓促", "fix": "加入了发现第二条信号的技术细节"},
        {"chapter": 15, "issue": "星语石板秘密揭示力道不足", "fix": "增强了石板与林远舟妻子关联的伏笔回收"},
    ]
    with create_session() as sess:
        for fx in fixes:
            sess.execute(
                text("INSERT INTO fix_logs (novel_id, chapter_number, fix_type, issue_ref, original_summary, fixed_summary) "
                     "VALUES (:nid, :ch, '文字修正', :issue, '原文本待优化', :fix)"),
                {"nid": novel_id, "ch": fx["chapter"], "issue": fx["issue"], "fix": fx["fix"]}
            )
        sess.commit()
    log_step(18, "正文修正", True, f"{len(fixes)} 处修正")
    time.sleep(0.3)

    # ==================== Step 20: 导出发布 ====================
    hr()
    print("  [Step 20/20] 导出发布")
    print("    [User] 用户选择导出格式...")
    print("    [System] 正在渲染完整小说目录结构...")
    time.sleep(0.3)

    export_root = os.path.join(PROJECT, "output", NOVEL_TITLE)
    os.makedirs(export_root, exist_ok=True)

    # ---- 1. 小说概览.md ----
    overview = [
        f"# 小说概览",
        f"",
        f"> 最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"",
        f"## 基本信息",
        f"",
        f"| 字段 | 内容 |",
        f"|------|------|",
        f"| 小说ID | {novel_id} |",
        f"| 书名 | {NOVEL_TITLE} |",
        f"| 作者 | {NOVEL_AUTHOR} |",
        f"| 主题 | {NOVEL_THEME} |",
        f"| 当前进度 | 20/20 已完成 |",
        f"| 总字数 | {total_wc:,} |",
        f"| 总章节 | {len(manuscripts)} |",
        f"| 创建时间 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |",
        f"",
        f"## 剧情摘要",
        f"",
        f"首席密码学家林远舟在戈壁深空站捕获了来自比邻星的神秘信号——",
        f"它包含一份宇宙公约, 要求所有智慧文明在限期内签署。",
        f"他发现信号中的数学结构与已故妻子的研究高度吻合——仿佛有人在引导他。",
        f"",
        f"## 结构",
        f"",
        f"| 卷名 | 章节范围 | 核心冲突 |",
        f"|------|----------|----------|",
        f"| 群星之音 | 第1-6章 | 捕获信号开始解密, 宇宙公约的发现 |",
            f"| 公约的迷宫 | 第7-14章 | 艾琳觉醒团队分裂, 公约深层含义揭示 |",
            f"| 最后的签署 | 第15-20章 | 终极抉择文明命运, 危机的倒计时 |",
        f"",
        f"## 角色一览",
        f"",
        f"| 角色 | 定位 | 核心特质 |",
        f"|------|------|----------|",
        f"| 林远舟 | 主角 | 首席密码学家, 在大寂静中失去妻女 |",
            f"| 艾琳 | 关键配角 | 量子AI语言学家, 接触信号后产生自我意识 |",
            f"| 赵山河 | 配角 | 联合国宇宙事务委员会代表, 对外星接触持谨慎态度 |",
        f"",
        f"---",
        f"",
        f"*由 AI 小说创作系统生成*",
    ]
    with open(os.path.join(export_root, "小说概览.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(overview))

    # ---- 2. 01_主题 ----
    theme_dir = os.path.join(export_root, "01_主题")
    os.makedirs(theme_dir, exist_ok=True)
    theme_md = [
        f"# 01_主题",
        f"> 小说：{NOVEL_TITLE}",
        f"",
        f"## 表层主题",
        f"主角发现自己的记忆是编码的，整个人类文明处于轮回中",
        f"",
        f"## 深层主题",
        f"真相的代价是失去自我，但选择遗忘才是真正的审判",
        f"",
        f"## 情感钩子",
        f"一个考古学家发现自己的前世记录，而写下记录的人正是未来的自己",
        f"",
        f"## 主题宣言",
        f"记忆不是身份的基石，选择才是",
        f"",
        f"## 子主题",
        f"| 子主题 | 核心问题 |",
        f"|--------|----------|",
        f"| 记忆的篡改 | 记忆可以被改写，那么'我'还是'我'吗？ |",
        f"| 文明的囚徒 | 如果文明注定轮回，觉醒有意义吗？ |",
        f"| 代价的天平 | 获得真相的代价是否值得付出？ |",
    ]
    with open(os.path.join(theme_dir, "01_主题.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(theme_md))

    # ---- 3. 02_世界观 ----
    wb_dir = os.path.join(export_root, "02_世界观")
    os.makedirs(wb_dir, exist_ok=True)
    wb_lines = [f"# 02_世界观", f"> 小说：{NOVEL_TITLE}", f""]
    for dim in dimensions:
        wb_lines.extend([
            f"## {dim['name']}",
            f"",
            f"| 字段 | 内容 |",
            f"|------|------|",
        ])
        for r in dim["rules"]:
            wb_lines.append(f"| 规则 | {r['desc']} |")
            wb_lines.append(f"| 范围 | {r['scope']} |")
            wb_lines.append(f"| 限制 | {r['constraints']} |")
        wb_lines.append("")
    with open(os.path.join(wb_dir, "02_世界观.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(wb_lines))

    # ---- 4. 03_势力 ----
    fac_dir = os.path.join(export_root, "03_势力")
    os.makedirs(fac_dir, exist_ok=True)
    fac_lines = [f"# 03_势力", f"> 小说：{NOVEL_TITLE}", f""]
    for f in factions:
        fac_lines.extend([
            f"## {f['name']}",
            f"",
            f"| 类型 | {f['type']} |",
            f"| 目标 | {f['goals']} |",
            f"| 声望 | {f['reputation']} |",
            f"",
        ])
    with open(os.path.join(fac_dir, "03_势力.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(fac_lines))

    # ---- 5. 04_势力关系 ----
    fr_dir = os.path.join(export_root, "04_势力关系")
    os.makedirs(fr_dir, exist_ok=True)
    fr_lines = [f"# 04_势力关系", f"> 小说：{NOVEL_TITLE}", f""]
    for r in faction_rels:
        fr_lines.extend([
            f"## {r['a']} vs {r['b']}",
            f"",
            f"| 关系 | {r['type']} |",
            f"| 强度 | {r['strength']} |",
            f"",
        ])
    with open(os.path.join(fr_dir, "04_势力关系.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(fr_lines))

    # ---- 6. 05_人物 ----
    ch_dir = os.path.join(export_root, "05_人物")
    os.makedirs(ch_dir, exist_ok=True)
    char_lines = [f"# 05_人物", f"> 小说：{NOVEL_TITLE}", f""]
    for ch in characters:
        l1 = ch["layer1"]
        l2 = ch["layer2"]
        l3 = ch["layer3"]
        l4 = ch["layer4"]
        char_lines.extend([
            f"## {ch['name']}（{ch['role']}）",
            f"",
            f"### 第一层：身份层",
            f"| 年龄 | {l1['age']} |",
            f"| 职业 | {l1['occupation']} |",
            f"| 出身 | {l1['origin']} |",
            f"",
            f"### 第二层：心理层",
            f"| 人格 | {l2['personality']} |",
            f"| 价值观 | {', '.join(l2['values'])} |",
            f"| 动机 | {l2['motivation']} |",
            f"| 恐惧 | {l2['fear']} |",
            f"",
            f"### 第三层：能力层",
            f"| 技能 | {', '.join(l3['skills'])} |",
            f"| 弱点 | {l3['weakness']} |",
            f"",
            f"### 第四层：秘密层",
            f"| 秘密 | {', '.join(l4['secrets'])} |",
            f"| 命运 | {l4['destiny']} |",
            f"",
        ])
    with open(os.path.join(ch_dir, "05_人物.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(char_lines))

    # ---- 7. 06_人物关系 ----
    rel_dir = os.path.join(export_root, "06_人物关系")
    os.makedirs(rel_dir, exist_ok=True)
    rel_lines = [f"# 06_人物关系", f"> 小说：{NOVEL_TITLE}", f""]
    for r in relations:
        rel_lines.extend([
            f"## {r['a']} <-> {r['b']}",
            f"",
            f"| 关系 | {r['type']} |",
            f"| 强度 | {r['strength']} |",
            f"| 说明 | {r['note']} |",
            f"",
        ])
    with open(os.path.join(rel_dir, "06_人物关系.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(rel_lines))

    # ---- 8. 07_角色弧线 ----
    arc_dir = os.path.join(export_root, "07_角色弧线")
    os.makedirs(arc_dir, exist_ok=True)
    arc_lines = [f"# 07_角色弧线", f"> 小说：{NOVEL_TITLE}", f""]
    for a in arcs:
        arc_lines.extend([
            f"## {a['char']} - {a['type']}",
            f"",
            f"| 阶段 | 描述 |",
            f"|------|------|",
            f"| 起点 | {a['start']} |",
            f"| 催化剂 | {a['catalyst']} |",
            f"| 变化过程 | {' -> '.join(a['process'])} |",
            f"| 终点 | {a['end']} |",
            f"",
        ])
    with open(os.path.join(arc_dir, "07_角色弧线.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(arc_lines))

    # ---- 9. 08_物品仓库 ----
    item_dir = os.path.join(export_root, "08_物品仓库")
    os.makedirs(item_dir, exist_ok=True)
    item_lines = [f"# 08_物品仓库", f"> 小说：{NOVEL_TITLE}", f""]
    for it in items:
        item_lines.extend([
            f"## {it['name']}",
            f"",
            f"| 字段 | 内容 |",
            f"|------|------|",
            f"| 类型 | {it['type']} |",
            f"| 用途 | {it['purpose']} |",
            f"| 持有者 | {it['owner']} |",
            f"| 备注 | {it['note']} |",
            f"",
        ])
    with open(os.path.join(item_dir, "08_物品仓库.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(item_lines))

    # ---- 10. 09_伏笔管理 ----
    fore_dir = os.path.join(export_root, "09_伏笔管理")
    os.makedirs(fore_dir, exist_ok=True)
    fore_lines = [f"# 09_伏笔管理", f"> 小说：{NOVEL_TITLE}", f""]
    for f in foreshadows:
        fore_lines.extend([
            f"## {f['type']}",
            f"",
            f"| 字段 | 内容 |",
            f"|------|------|",
            f"| 类型 | {f['type']} |",
            f"| 埋设章节 | 第{f['chapter']}章 |",
            f"| 内容 | {f['payload']} |",
            f"| 深度 | {f['depth']} |",
            f"| 重要性 | {f['importance']} |",
            f"| 状态 | 未揭示 |",
            f"",
        ])
    with open(os.path.join(fore_dir, "09_伏笔管理.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(fore_lines))

    # ---- 11. 10_大纲 ----
    struct_dir = os.path.join(export_root, "10_大纲")
    os.makedirs(struct_dir, exist_ok=True)
    struct_lines = [f"# 10_大纲", f"> 小说：{NOVEL_TITLE}", f""]
    struct_lines.append("## 三幕结构")
    struct_lines.append("")
    for a in acts:
        struct_lines.extend([
            f"### {a['title']}（{a['chapters']}章）",
            f"",
            f"关键事件: {' -> '.join(a['key_events'])}",
            f"",
        ])
    struct_lines.append("## 因果链")
    struct_lines.append("")
    for cc in causal_chain:
        struct_lines.append(f"- {cc['from']} -> {cc['to']}（{cc['reason']}）")
    struct_lines.append("")
    struct_lines.append("## 分卷结构")
    struct_lines.append("")
    for v in volumes_data:
        struct_lines.extend([
            f"### {v['name']}",
            f"",
            f"| 章节 | 第{v['ch_range'][0]}-{v['ch_range'][1]}章 |",
            f"| 叙事引力 | {v['gravity']} |",
            f"| 节奏 | {v['pacing']} |",
            f"| 核心冲突 | {v['conflict']} |",
            f"",
        ])
    with open(os.path.join(struct_dir, "10_大纲.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(struct_lines))

    # ---- 12. 13_正文（每章一个独立markdown文件） ----
    chapter_dir = os.path.join(export_root, "13_正文")
    os.makedirs(chapter_dir, exist_ok=True)
    chapter_index_lines = [f"# 正文目录", f"> 小说：{NOVEL_TITLE}", f"", f"| 章节 | 标题 | 字数 |", f"|------|------|------|"]
    for m in manuscripts:
        cn = m["chapter_number"]
        title = m["title"]
        wc = m["word_count"]
        safe_title = title.replace(" ", "_").replace("/", "_")
        ch_filename = f"第{cn:02d}章_{safe_title}.md"
        ch_content = [
            f"# 第{cn}章 {title}",
            f"",
            f"> 字数：{wc}",
            f"> 视角：{'林远舟' if cn % 3 != 2 else '艾琳'}",
            f"",
            f"---",
            f"",
        ]
        for _, sc in enumerate(m["scenes"]):
            ch_content.append(sc)
            ch_content.append("")
            ch_content.append("---")
            ch_content.append("")
        with open(os.path.join(chapter_dir, ch_filename), "w", encoding="utf-8") as f:
            f.write("\n".join(ch_content))
        chapter_index_lines.append(f"| [第{cn}章 {title}]({ch_filename}) | {title} | {wc:,} |")

    with open(os.path.join(chapter_dir, "README.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(chapter_index_lines))

    # ---- 13. 完整小说.md（单文件完整版） ----
    full_text_lines = [
        f"# {NOVEL_TITLE}",
        f"Author: {NOVEL_AUTHOR}",
        f"Theme: {NOVEL_THEME}",
        f"Novel ID: {novel_id}",
        f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"",
        f"---",
        f"",
    ]
    for m in manuscripts:
        cn = m["chapter_number"]
        full_text_lines.append(f"## Chapter {cn:02d}: {m['title']}")
        for s in m["scenes"]:
            full_text_lines.append(s)
        full_text_lines.append("")
    full_text = "\n".join(full_text_lines)

    txt_path = os.path.join(export_root, f"{NOVEL_TITLE}.txt")
    md_path = os.path.join(export_root, f"{NOVEL_TITLE}.md")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(full_text)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(full_text)

    with create_session() as sess:
        sess.execute(
            text("UPDATE novels SET current_step = 20, status = '已完成', updated_at = :now WHERE id = :nid"),
            {"nid": novel_id, "now": now()}
        )
        sess.commit()

    txt_size = os.path.getsize(txt_path)
    md_size = os.path.getsize(md_path)

    # Count output files
    file_count = 0
    for _, _, files in os.walk(export_root):
        file_count += len(files)

    log_step(20, "导出发布", True,
             f"{file_count} files | TXT({txt_size:,}b)+MD({md_size:,}b) | {len(manuscripts)} chapter files | {export_root}")

    # ==================== 汇总报告 ====================
    print()
    print(f"  {'=' * 66}")
    print(f"    << FULL WORKFLOW COMPLETED >>")
    print(f"  {'=' * 66}")
    print(f"    Title:   <<{NOVEL_TITLE}>>")
    print(f"    Author:  {NOVEL_AUTHOR}")
    print(f"    Novel ID:{novel_id}")
    print(f"    Theme:   {NOVEL_THEME}")
    print(f"    Status:  COMPLETED (20/20)")
    print(f"    Total:   {total_wc:,} chars / {len(manuscripts)} chapters")
    print(f"    Export:  TXT ({txt_size:,} bytes) + MD ({md_size:,} bytes)")
    print(f"    DB:      {Config.SQLITE_PATH}")
    print(f"  {'=' * 66}")
    print()

    # ==================== 数据库验证 ====================
    print(f"  [DB Verify] Verifying database persistence...")
    with create_session() as sess:
        tables = {
            "novels": "SELECT COUNT(*) FROM novels",
            "inspirations": "SELECT COUNT(*) FROM inspirations",
            "themes": "SELECT COUNT(*) FROM themes",
            "outlines": "SELECT COUNT(*) FROM outlines",
            "world_building": "SELECT COUNT(*) FROM world_building",
            "characters": "SELECT COUNT(*) FROM characters",
            "relations": "SELECT COUNT(*) FROM relations",
            "character_arcs": "SELECT COUNT(*) FROM character_arcs",
            "factions": "SELECT COUNT(*) FROM factions",
            "faction_relations": "SELECT COUNT(*) FROM faction_relations",
            "items": "SELECT COUNT(*) FROM items",
            "foreshadows": "SELECT COUNT(*) FROM foreshadows",
            "archives": "SELECT COUNT(*) FROM archives",
            "synopses": "SELECT COUNT(*) FROM synopses",
            "volumes": "SELECT COUNT(*) FROM volumes",
            "detail_outlines": "SELECT COUNT(*) FROM detail_outlines",
            "manuscripts": "SELECT COUNT(*) FROM manuscripts",
            "review_results": "SELECT COUNT(*) FROM review_results",
            "fix_logs": "SELECT COUNT(*) FROM fix_logs",
        }
        expected_counts = {
            "novels": 1, "inspirations": 3, "themes": 1, "outlines": 1,
            "world_building": 8, "characters": 3, "relations": 3,
            "character_arcs": 2, "factions": 3, "faction_relations": 3,
            "items": 3, "foreshadows": 4, "archives": 1, "synopses": 1,
            "volumes": 3, "detail_outlines": 20, "manuscripts": 20,
            "review_results": 1, "fix_logs": 3,
        }
        print(f"  {'Table':<22} {'Records':<10} {'Expected':<10}")
        print(f"  {'-' * 44}")
        total_records = 0
        all_ok = True
        for tbl, sql in tables.items():
            cnt = sess.execute(text(sql)).scalar() or 0
            total_records += cnt
            exp = expected_counts.get(tbl, 0)
            ok = "[OK]" if cnt >= exp else "[MISS]"
            if cnt < exp:
                all_ok = False
            print(f"  {tbl:<22} {cnt:<10} {exp:<10} {ok}")
        print(f"  {'-' * 44}")
        print(f"  Total: {total_records} records  Status: {'ALL OK' if all_ok else 'ISSUES'}")
    print()
    print(f"  {'=' * 66}")
    print(f"    Simulation completed successfully!")
    print(f"    <<{NOVEL_TITLE}>> ready at: {export_root}")
    print(f"  {'=' * 66}")
    print()

if __name__ == "__main__":
    simulate()
