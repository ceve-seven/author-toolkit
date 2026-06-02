# -*- coding: utf-8 -*-
"""Trae 自主生成章节正文脚本

工作流程:
  步骤1: python scripts/trae_generate_chapter.py --generate --chapter 1
  步骤2: 在 CHAPTER_CONTENT 填入正文
  步骤3: python scripts/trae_generate_chapter.py --inject --chapter 1

注意: 禁止新建额外脚本，所有功能集成于此脚本内。
"""
import argparse, json, sys
from pathlib import Path
from typing import Any, Dict, List
sys.path.insert(0, str(Path(__file__).parent.parent))
from sqlalchemy import text
from src.storage.database.engine import get_session
from src.core.modules.registry import get_registry
from src.core.purifier.pipeline import PurificationPipeline
from src.core.sync.engine import SyncEngine
from src.config.settings import Config
from src.utils.prompt_loader import load_prompt

CHAPTER_CONTENT: List[Dict[str, Any]] = [
    {
        "chapter_number": 1,
        "title": "穿越2010",
        "scenes": [
            {
                "pov_char_id": "林默",
                "scene_id": "ch01_scene01",
                "content": """天花板是灰的。

林默盯着那片剥落的墙皮看了五秒。暗红色的砖露在外面，空气里有股潮湿的霉味，混着廉价洗衣粉的香气。身下是一张硬板床，硌得后背发麻。

他坐起来。

一阵眩晕。手指抓紧床沿，闭上眼，等天旋地转过去。

再睁眼，开始打量这间屋子。不到十平米，生锈的窗框，折叠桌，塑料椅子，角落的电热水壶。桌上搁着一部黑色直板手机，屏幕亮着，日历图标下面一行小字：

2010年1月1日。

十秒钟。他就这么盯着那个日期看了十秒钟。

低头看手。干净的，年轻的，没有老茧。摸了摸脸，光滑的皮肤，眉角到耳根那道旧伤疤消失了。

2035年的伤疤。2035年的一切，都消失了。

他站起来走到窗前。窗外是一条窄巷，对面一排老旧居民楼。有人骑电动车经过，车筐里装着菜。远处传来叫卖声，烤红薯，三块钱一个。

三块钱。

林默闭上眼。

记忆涌上来。完整的，清晰的，带着温度和触感。比特币，从几美分涨到六万美元再跌到两万又冲上十万。特斯拉，濒临破产到万亿市值。英伟达，默默无闻到AI时代的绝对王者，股价翻了三百倍。

2015年杠杆牛市，6月12日那根大阴线。2020年新冠爆发，全球市场恐慌，散户割肉，赢家抄底。ChatGPT，2022年11月30日发布。英伟达从150美元到900美元。

全在脑子里。

他睁开眼。2010年的空气比2035年干净，没有那种无处不在的电子烟雾味。

左手口袋里有个硬物。掏出来，老式怀表，祖父留下的。表壳冰凉，背面一行模糊的刻字。小时候辨认过无数次，从来没认出来。现在他知道了，那是祖父年轻时留下的暗号，跟林家一段不为人知的往事有关。

现在不是想这个的时候。

他把怀表放回口袋，拿起桌上的手机翻了翻。没有SIM卡，存着几个联系人，全是2010年的人。通讯录里备注着"辞职后待办事项"，打开一看，就一行字：

"找个工作。"

二十八岁，刚辞职，普通年轻人。卡里余额三万七，工作五年攒的全部家当。没有公司，没有人脉。

五十三年的阅历装在二十八岁的身体里。脑子里装着未来二十五年的全部记忆。

林默把手机放回桌上，在折叠桌前坐下来。

2035年的林默犯过最大的错，就是太张扬。实力暴露在阳光下，所有人都成了猎人，你是唯一的猎物。觊觎你的人从暗处涌来，用尽一切手段拉你下神坛。

低调。隐形。精准。

掏出怀表，打开表盖。秒针在走，滴答滴答，在安静的房间里格外清晰。盯了三十秒，合上。

第一步，活下去。用2010年的方式活下去。

第二步，积累。最小风险，第一桶金。

第三步，布局。所有人还没反应过来的时候，棋子落在最关键的位置。

他站起来，走到窗前。

对面楼顶的天台上站着一个人。

距离太远，看不清面容。那人朝这边看着，停留了大约三秒，转身消失。

林默盯着那个天台看了两分钟。没有人再出现。

拉上窗帘，回到桌前。

巧合。太紧张了，看错了。

他把"找个工作"那行字看了最后一遍，锁上手机屏幕。

找工作这件事，已经翻篇了。""",
                "word_count": 1580
            },
            {
                "pov_char_id": "林默",
                "scene_id": "ch01_scene02",
                "content": """三天后。

证券营业部大厅里没几个人。几个中年股民盯着大屏幕上的红绿数字，表情各异。有人抽烟，有人打电话，有人在笔记本上写写画画。

林默找了一台自助终端坐下。

2010年的A股，2008年暴跌后的反弹期。大多数人还在恐惧中观望，聪明的资金已经开始悄悄入场。他选这个地方，就因为这个。

屏幕上显示上证指数实时行情：2845.25点。

他闭上眼，在脑子里翻找2035年的记忆。2010年1月4日，上证指数开盘3289.75点，收盘3243.53点，涨幅1.04%。

睁开眼，看了一眼日期。1月4日，周一。九点二十八分。

再过两分钟开盘。

九点半。

上证指数以3289.18点开盘。

记忆中的3289.75，实际3289.18。差0.57点。误差率0.017%。

胃部猛地收缩了一下。不是因为紧张，是因为这个数字意味着一件事：记忆是准确的。宏观层面，未来记忆与这个时空高度吻合。微观层面的微小偏差正常，蝴蝶效应从穿越那一刻就开始累积。

比特币会涨。特斯拉会崛起。AI会改变世界。

这些是确定的。

林默在终端上开了股票账户，转入三万七千块。全副身家。

没有急着买。大盘震荡上行，散户开始兴奋，有人加仓。他等着。

十点十五分。

买入。一只白酒股，2010年还默默无闻，2015年成为十倍牛股。买入价22.35元。全仓。

旁边一个中年股民瞥了他一眼，嘴角动了动，大概想说什么，忍住了。全仓单只股票，在2010年这种行情下，跟赌没什么区别。

林默没看他。屏幕上红色数字在跳。

十一点半，浮盈4.2%。

下午两点，卖出一半。浮盈6.8%。

剩下的持有到三月份。按记忆，一季度这只股票涨到35元以上。

收盘后走出营业部。一月的阳光照在脸上，不刺眼。门口来来往往的人行色匆匆，忙着各自的日子。

街角那家小餐馆，2013年拆迁，老板拿了一笔不菲的补偿款。卖烤红薯的大叔，儿子2018年考上清华。远处那栋在建的写字楼，两年后成为这座城市最贵的商业地产。

全在他脑子里。

此刻他口袋里一块怀表，银行卡里多出两千块浮盈，脑子里装着价值万亿的信息。

林默转身往回走。路过一家网吧，停住。

他需要一台电脑。接入这个时代的信息网络。2010年，信息不对称是最有价值的武器。

开了一台靠角落的机器。登录邮箱，收件箱一封未读邮件。发件人地址陌生，标题为空。

点开。

正文一行字：

"你不是唯一一个回来的人。"

林默的手指停在鼠标上，没有动。屏幕的光打在他脸上，瞳孔缩了一下。

关掉邮箱。删除邮件。清空回收站。

靠在椅背上。

对面楼顶的人影。这封邮件。

巧合。恶作剧。都有可能。

他看着屏幕上跳动的光标，眨了两下眼。

不管对方是谁。低调地走，精准地走，一直走下去。

站起来。系统弹窗问是否保存密码，选了否。走出网吧，2010年一月傍晚的人流从身边涌过。

没人多看他一眼。

三万七千块，二十五年后的记忆，隐形帝国的第一步。已经迈出去了。""",
                "word_count": 1520
            }
        ],
        "word_count": 3100
    }
]

FIELD_LABELS = {
    "characters": {"char_id":"角色ID","name":"姓名","role":"角色定位","layer1_json":"基础设定","layer2_json":"深层设定","layer3_json":"核心设定","background_json":"背景故事"},
    "factions": {"faction_id":"势力ID","name":"名称","type":"类型","hierarchy":"组织架构","goals":"目标","resources":"资源","doctrines":"核心教义","reputation":"声望"},
    "items": {"item_id":"物品ID","name":"名称","type":"类型","purpose":"用途","background_story":"背景故事","restrictions":"限制条件","current_owner":"当前持有者","significance_to_plot":"剧情意义","first_appearance_chapter":"首次出现章节"},
    "world_building": {"dimension_name":"维度名称","rules":"规则"},
    "foreshadows": {"foreshadow_id":"伏笔ID","type":"类型","payload":"内容","plant_chapter":"埋设章节","reveal_chapter_planned":"预期揭示章节","status":"状态"},
    "relations": {"relation_id":"关系ID","char_a_id":"角色A","char_b_id":"角色B","type":"关系类型","strength":"关系强度","history":"历史"},
    "faction_relations": {"relation_id":"关系ID","faction_a_id":"势力A","faction_b_id":"势力B","type":"关系类型","strength":"关系强度","history":"历史"},
    "char_faction_links": {"char_id":"角色ID","faction_id":"势力ID","membership_type":"成员类型","role_in_faction":"角色职位","join_chapter":"加入章节","loyalty":"忠诚度","notes":"备注"},
}


def load_novel_data(novel_id, session):
    tables = ["characters","items","factions","world_building","foreshadows","relations","faction_relations","char_faction_links","outlines","detail_outlines","volumes","manuscripts"]
    data = {}
    for table in tables:
        rows = session.execute(__import__("sqlalchemy").text(f"SELECT * FROM {table} WHERE novel_id = :novel_id ORDER BY rowid"), {"novel_id": novel_id}).fetchall()
        items = []
        for row in rows:
            item = dict(row._mapping)
            for k,v in item.items():
                if isinstance(v, bytes):
                    try: item[k] = __import__("json").loads(v.decode("utf-8"))
                    except: item[k] = v.decode("utf-8", errors="replace")
            items.append(item)
        data[table] = items
    return data

def load_novel_title(novel_id, session):
    row = session.execute(__import__("sqlalchemy").text("SELECT title FROM novels WHERE id = :novel_id"), {"novel_id": novel_id}).fetchone()
    return row[0] if row else novel_id

def print_data(data):
    print("="*70)
    print("数据总览")
    print("="*70)
    for table_name, label in [("characters","角色"),("factions","势力"),("items","物品"),("world_building","世界观"),("foreshadows","伏笔"),("relations","人物关系"),("faction_relations","势力关系"),("char_faction_links","人物-势力关联"),("volumes","分卷"),("detail_outlines","章节细纲"),("manuscripts","正文")]:
        rows = data.get(table_name, [])
        if not rows: continue
        print(f"\n{'─'*60}")
        print(f"  {label} ({len(rows)}条)")
        print(f"{'─'*60}")
        for row in rows:
            name = row.get("name", row.get("title", row.get("dimension_name", row.get("chapter_number", "?"))))
            if isinstance(name, int): name = f"第{name}章"
            summary = ""
            for key in ("summary","description","purpose","goals","major_conflict","chapter_constraint_summary"):
                val = row.get(key)
                if val:
                    if isinstance(val, str) and len(val) > 100: val = val[:97]+"..."
                    summary = str(val)
                    break
            if table_name == "detail_outlines" and not summary:
                ccs = row.get("chapter_constraint_summary")
                if ccs:
                    try: ccs_j = __import__("json").loads(ccs) if isinstance(ccs, str) else ccs
                    except: ccs_j = ccs
                    if isinstance(ccs_j, dict): summary = str(ccs_j.get("summary", ccs_j.get("chapter_summary", "")))[:100]
            fid = row.get("char_id", row.get("faction_id", row.get("item_id", row.get("volume_id", ""))))
            if fid: print(f"  [{fid}] {name}")
            else: print(f"  {name}")
            if summary: print(f"    {summary}")
    print()

def _serialize_val(val, max_len=200):
    if val is None: return "无"
    if isinstance(val, (dict, list)): return json.dumps(val, ensure_ascii=False)[:max_len]
    s = str(val)
    return s[:max_len] + "…" if len(s) > max_len else s

def _section_header(title, width=70):
    return f"\n{'='*width}\n  {title}\n{'-'*width}"

def _format_field(row, key, label):
    val = row.get(key)
    if val is None: return ""
    return f"  {label}: {_serialize_val(val, 300)}\n"

def _format_char_fields(row):
    lines = []
    for key, label in [("name","姓名"),("role","角色定位"),("layer1_json","基础设定"),
                        ("layer2_json","深层设定"),("layer3_json","核心设定"),("background_json","背景故事")]:
        v = row.get(key)
        if v is None: continue
        if isinstance(v, (dict, list)):
            v = json.dumps(v, ensure_ascii=False, indent=2)[:500]
        elif isinstance(v, str) and len(v) > 500:
            v = v[:497] + "…"
        lines.append(f"  {label}: {v}")
    return "\n".join(lines) + "\n"

def build_generation_prompt(data, chapter_number):
    novel_title = data.get("_novel_title", "未命名")
    prompt = f"# 创作任务：为《{novel_title}》生成第 {chapter_number} 章正文\n\n"

    detail_outlines = data.get("detail_outlines", [])
    chapter_outline = None
    for do in detail_outlines:
        if do.get("chapter_number") == chapter_number:
            chapter_outline = do
            break

    if chapter_outline:
        prompt += _section_header("章节约束")
        ccs = chapter_outline.get("chapter_constraint_summary")
        if isinstance(ccs, str):
            try: ccs = json.loads(ccs)
            except: pass
        if isinstance(ccs, dict):
            for k, v in ccs.items():
                if isinstance(v, (dict, list)):
                    prompt += f"  {k}: {json.dumps(v, ensure_ascii=False, indent=2)[:500]}\n"
                else:
                    prompt += f"  {k}: {v}\n"
        elif ccs:
            prompt += f"  {ccs}\n"

        scenes_raw = chapter_outline.get("scenes")
        if scenes_raw:
            if isinstance(scenes_raw, str):
                try: scenes_raw = json.loads(scenes_raw)
                except: pass
            if isinstance(scenes_raw, list):
                prompt += f"\n  场景设计 ({len(scenes_raw)}个场景):\n"
                for i, sc in enumerate(scenes_raw, 1):
                    prompt += f"    场景{i}: POV={sc.get('pov_char_id','?')} 地点={sc.get('setting','?')}"
                    s_summary = sc.get("summary", sc.get("content", ""))
                    if s_summary:
                        prompt += f" 内容={_serialize_val(s_summary, 150)}"
                    prompt += "\n"

    volumes = data.get("volumes", [])
    if volumes:
        prompt += _section_header("分卷信息")
        for vol in volumes:
            if chapter_outline and vol.get("chapter_range"):
                try:
                    cr = vol["chapter_range"]
                    nums = [int(s) for s in cr.replace("章","").split("-") if s.strip().isdigit()]
                    if nums and nums[0] <= chapter_number <= (nums[-1] if len(nums)>1 else nums[0]):
                        prompt += f"  当前分卷: {vol.get('name','?')}\n"
                        prompt += f"  章节范围: {vol.get('chapter_range','?')}\n"
                        mc = vol.get("major_conflict")
                        if isinstance(mc, dict) and mc.get("conflict"):
                            prompt += f"  核心冲突: {_serialize_val(mc['conflict'], 300)}\n"
                        elif mc:
                            prompt += f"  核心冲突: {_serialize_val(mc, 300)}\n"
                        prompt += f"  节奏: {vol.get('pacing','?')}\n"
                        break
                except: pass

    chars = data.get("characters", [])
    if chars:
        prompt += _section_header("角色设定")
        prompt += f"  共 {len(chars)} 个角色\n\n"
        for ch in chars:
            prompt += _format_char_fields(ch)
            prompt += "\n"

    factions = data.get("factions", [])
    if factions:
        prompt += _section_header("势力设定")
        prompt += f"  共 {len(factions)} 个势力\n\n"
        for f in factions:
            prompt += f"  [{f.get('faction_id','?')}] {f.get('name','?')} ({f.get('type','?')})\n"
            for k in ("goals","resources","doctrines","hierarchy"):
                prompt += _format_field(f, k, FIELD_LABELS["factions"].get(k, k))
            prompt += "\n"

    items = data.get("items", [])
    if items:
        prompt += _section_header("物品库")
        prompt += f"  共 {len(items)} 件物品\n\n"
        for it in items:
            prompt += f"  [{it.get('item_id','?')}] {it.get('name','?')} ({it.get('type','?')})\n"
            for k in ("purpose","background_story","restrictions","current_owner","significance_to_plot","first_appearance_chapter"):
                prompt += _format_field(it, k, FIELD_LABELS["items"].get(k, k))
            prompt += "\n"

    world = data.get("world_building", [])
    if world:
        prompt += _section_header("世界观")
        prompt += f"  共 {len(world)} 条世界观设定\n\n"
        for w in world:
            dim_name = w.get("dimension_name", "?")
            rules_val = w.get("rules")
            prompt += f"  维度: {dim_name}\n"
            if rules_val:
                if isinstance(rules_val, str):
                    try: rules_val = json.loads(rules_val)
                    except: pass
                if isinstance(rules_val, list):
                    prompt += f"  规则 ({len(rules_val)}条):\n"
                    for r in rules_val:
                        desc = r.get("description", r.get("rule", ""))
                        scope = r.get("scope", "")
                        prompt += f"    - {_serialize_val(desc, 200)}"
                        if scope: prompt += f" [{scope}]"
                        prompt += "\n"
                elif isinstance(rules_val, dict):
                    for rk, rv in rules_val.items():
                        prompt += f"    {rk}: {_serialize_val(rv, 200)}\n"
                else:
                    prompt += f"  规则: {_serialize_val(rules_val, 300)}\n"
            prompt += "\n"

    foreshadows = data.get("foreshadows", [])
    if foreshadows:
        prompt += _section_header("伏笔管理")
        prompt += f"  共 {len(foreshadows)} 条伏笔\n\n"
        for f in foreshadows:
            pc = f.get("plant_chapter","")
            erc = f.get("reveal_chapter_planned","")
            relevant = False
            try:
                if isinstance(pc, (int,float)) and int(pc) <= chapter_number: relevant = True
                if isinstance(erc, (int,float)) and int(erc) == chapter_number: relevant = True
            except: pass
            if not relevant: continue
            prompt += f"  [{f.get('foreshadow_id','?')}] {f.get('type','?')}\n"
            prompt += f"    埋设章节: {pc} → 预期揭示: {erc}\n"
            prompt += _format_field(f, "payload", "内容")
            prompt += "\n"

    relations = data.get("relations", [])
    if relations:
        prompt += _section_header("人物关系")
        prompt += f"  共 {len(relations)} 条关系\n\n"
        for r in relations:
            prompt += f"  {r.get('char_a_id','?')} ↔ {r.get('char_b_id','?')} [{r.get('type','?')}]\n"
            prompt += _format_field(r, "strength", "关系强度")
            prompt += _format_field(r, "history", "历史")
            prompt += "\n"

    faction_relations = data.get("faction_relations", [])
    if faction_relations:
        prompt += _section_header("势力关系")
        prompt += f"  共 {len(faction_relations)} 条关系\n\n"
        for r in faction_relations:
            prompt += f"  {r.get('faction_a_id','?')} ↔ {r.get('faction_b_id','?')} [{r.get('type','?')}]\n"
            prompt += _format_field(r, "strength", "关系强度")
            prompt += _format_field(r, "history", "历史")

    char_faction_links = data.get("char_faction_links", [])
    if char_faction_links:
        prompt += _section_header("人物-势力关联")
        prompt += f"  共 {len(char_faction_links)} 条关联\n\n"
        for link in char_faction_links:
            prompt += f"  {link.get('char_id','?')} → {link.get('faction_id','?')} [{link.get('membership_type','?')}]\n"
            prompt += f"    职位: {link.get('role_in_faction','?')} 忠诚: {link.get('loyalty','?')}\n"

    prompt += _section_header("创作要求")
    prompt += f"""
  1. 严格按照场景设计（scenes）编写，每个场景的 POV 角色和内容不得偏离
  2. 每个场景正文至少 800 字，确保描写充实、对话自然
  3. 语言风格中性平实，避免过多抒情修饰
  4. 善用动作和对白推进剧情，减少内心独白
  5. 正文必须使用第三人称有限视角（跟随 POV 角色的视角）
  6. 字数: 每个场景 800-2000 字，全章总字数 2000-4000 字
  7. 必须遵守下方正文规则集中的全部规则

请直接编写第 {chapter_number} 章的正文内容。\n
"""

    prompt_rules = load_prompt("manuscript_writer.md")
    if prompt_rules:
        prompt += _section_header("正文规则集（强制遵守）")
        prompt += f"\n{prompt_rules}\n"

    return prompt

def handle_generate(args):
    chapter_number = args.chapter
    with get_session() as session:
        novel = session.execute(
            text("SELECT id, title FROM novels ORDER BY created_at DESC LIMIT 1")
        ).fetchone()
        if not novel:
            print("❌ 数据库中无小说记录")
            print("请先运行 python -m tests.mock_run")
            return
        novel_id, novel_title = novel
        print(f"📖 小说: {novel_title} (ID: {novel_id})")
        print(f"📝 目标章节: 第 {chapter_number} 章\n")

        data = load_novel_data(novel_id, session)
        data["_novel_title"] = novel_title

        print_data(data)

        prompt = build_generation_prompt(data, chapter_number)
        print("\n" + "=" * 70)
        print("📋 创作提示词")
        print("=" * 70)
        print(prompt)

        prompt_path = Path(__file__).parent.parent / "system_data" / f"prompt_ch{chapter_number}.md"
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text(prompt, encoding="utf-8")
        print(f"\n💾 提示词已保存至: {prompt_path}")

def handle_inject(args):
    global CHAPTER_CONTENT
    chapter_number = args.chapter

    if not CHAPTER_CONTENT:
        print("⚠️  CHAPTER_CONTENT 为空！")
        print("请在脚本顶部的 CHAPTER_CONTENT 列表中填入章节正文。")
        print(f"格式示例:")
        print('''CHAPTER_CONTENT = [{
    "chapter_number": 1,
    "title": "第一章 标题",
    "scenes": [
        {
            "pov_char_id": "CHAR-001",
            "scene_id": "ch01_scene01",
            "content": "正文内容...",
            "word_count": 0,
            "emotional_arc": {"start_emotion": "平静", "end_emotion": "紧张"},
            "setting": "地点",
            "time": "时间"
        }
    ]
}]''')
        return

    with get_session() as session:
        novel = session.execute(
            text("SELECT id FROM novels ORDER BY created_at DESC LIMIT 1")
        ).fetchone()
        if not novel:
            print("❌ 数据库中无小说记录")
            return
        novel_id = novel[0]
        print(f"📖 小说 ID: {novel_id}")
        print(f"📝 注入章节: 第 {chapter_number} 章\n")

        deps = {}
        tables = ["characters", "items", "factions", "world_building",
                   "foreshadows", "detail_outlines", "volumes"]
        for table in tables:
            rows = session.execute(
                text(f"SELECT * FROM {table} WHERE novel_id = :novel_id"),
                {"novel_id": novel_id},
            ).fetchall()
            if rows:
                items = []
                for row in rows:
                    item = dict(row._mapping)
                    items.append(item)
                deps[table] = items
            else:
                deps[table] = []

        context = {
            "novel_id": novel_id,
            "db_session": session,
            "dependencies": deps,
            "user_modifications": None,
        }

        registry = get_registry()
        registry.initialize()
        module_cls = registry.get("manuscript_writer")
        module = module_cls()

        content = {
            "chapters": CHAPTER_CONTENT,
            "transition_fixes": [],
        }

        result = module.run(context, content)
        session.flush()

        if result.success:
            print(f"✅ 正文入库成功!")
            print(f"   摘要: {result.summary}")
            print(f"   字数: {result.word_count}")

            issues = module.validate(result)
            if issues:
                print(f"\n⚠️ 质检发现 {len(issues)} 个问题:")
                for issue in issues:
                    print(f"   - {issue}")
            else:
                print(f"\n✅ 质检全部通过，无问题")

            # === AI 痕迹检测与清除 ===
            print(f"\n🔍 运行 AI 痕迹检测...")
            pipeline = PurificationPipeline()
            all_text = ""
            for ch in CHAPTER_CONTENT:
                for scene in ch.get("scenes", []):
                    all_text += scene.get("content", "") + "\n"
            if all_text:
                pur_result = pipeline.purify(all_text)
                if pur_result.issues:
                    print(f"\n⚠️ AI 痕迹检测发现 {len(pur_result.issues)} 个问题:")
                    l1 = len([i for i in pur_result.issues if i.fix_level == 1])
                    l2 = len([i for i in pur_result.issues if i.fix_level == 2])
                    l3 = len([i for i in pur_result.issues if i.fix_level == 3])
                    print(f"   L1 自动修复: {l1} 处")
                    print(f"   L2 半自动: {l2} 处")
                    print(f"   L3 仅报告: {l3} 处")
                    print(f"\n{pur_result.report}")
                else:
                    print(f"\n✅ AI 痕迹检测通过，未发现问题")

            # === 同步到 output 目录 ===
            print(f"\n📁 同步到 output 目录...")
            try:
                engine = SyncEngine(session, Config.USER_VIEW_DIR, Config.SYSTEM_DATA_DIR)
                sync_report = engine.sync_json_to_md(novel_id)
                print(f"   已更新 {sync_report.files_updated} 个文件")
                if sync_report.errors:
                    for err in sync_report.errors:
                        print(f"   ⚠️ {err}")
            except Exception as e:
                print(f"   ⚠️ 同步警告: {e}")
        else:
            print(f"\n❌ 正文入库失败:")
            for err in result.errors:
                print(f"   - {err}")

def main():
    parser = argparse.ArgumentParser(description="Trae 自主生成章节正文")
    parser.add_argument("--generate", action="store_true", help="从数据库加载数据并生成创作提示词")
    parser.add_argument("--inject", action="store_true", help="将填入的正文注入数据库")
    parser.add_argument("--chapter", type=int, default=1, help="章节号 (默认: 1)")
    args = parser.parse_args()

    if args.generate:
        handle_generate(args)
    elif args.inject:
        handle_inject(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
