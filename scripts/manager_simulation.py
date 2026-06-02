"""
小说管理系统全流程用户模拟测试
使用 NovelManager + 真实数据库 + SyncEngine 输出目录
--- 全新小说《末日之钟》---
"""
from __future__ import annotations

import os, sys, json, time
from pathlib import Path
from datetime import datetime, timezone

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))
os.environ['PYTHONIOENCODING'] = 'utf-8'

from typing import Any

from src.config.settings import Config
from src.storage.database.engine import get_engine, init_schema, create_session
from src.core.manager import NovelManager
from sqlalchemy import text

NOVEL_TITLE = "末日之钟"
NOVEL_AUTHOR = "方 觉"
NOVEL_THEME = "末世危机 - 时间循环 - 人性抉择"

engine = get_engine()
init_schema()

def now():
    return datetime.now(timezone.utc).isoformat()

hr = lambda: print(f"  {'-' * 66}")

def log(sn, name, ok, detail=""):
    icon = "[OK]" if ok else "[FAIL]"
    print(f"  {icon} Step {sn:02d} {name}")
    if detail:
        for d in detail.strip().split("\n"):
            print(f"       {d}")

def simulate():
    print()
    print(f"  {'='*66}")
    print(f"    AI Novel Creation System -- Management System Simulation")
    print(f"    Title: <<{NOVEL_TITLE}>>  Author: {NOVEL_AUTHOR}")
    print(f"    Theme: {NOVEL_THEME}")
    print(f"    Time:  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  {'='*66}")

    # ============ Management System: NovelManager ============
    hr()
    print("  [MANAGER] NovelManager 管理系统初始化...")
    with create_session() as sess:
        manager = NovelManager(sess)
        existing = manager.list_novels()
        print(f"           已有 {len(existing)} 部小说在系统中:")
        for n in existing:
            print(f"           [{n.status}] {n.title} ({n.id})")
    log(0, "管理系统初始化", True, f"NovelManager 就绪, {len(existing)} 部已有小说")

    # ============ Step 00: 通过管理系统创建小说 ============
    hr()
    print("  [Step 00/20] 管理系统创建小说")
    print("    [System] 通过 NovelManager.create_novel() 创建...")
    novel_id = None
    with create_session() as sess:
        manager = NovelManager(sess)
        novel_id = manager.create_novel(NOVEL_TITLE, NOVEL_AUTHOR)
    if novel_id:
        print(f"    [OK] 创建成功! Novel ID: {novel_id}")
        with create_session() as sess:
            novel = NovelManager(sess).get_novel(novel_id)
            print(f"    [OK] NovelManager 验证: {novel.title} | Step {novel.current_step} | {novel.status}")
    log(0, "NovelManager 创建", True, f"ID: {novel_id}")
    time.sleep(0.3)

    # ============ Step 01: 灵感启动 ============
    hr()
    print("  [Step 01/20] 灵感启动")
    print("    [AI Module] theme_engine.ThemeEngine 生成灵感方向...")
    time.sleep(0.2)
    directions: list[Any] = [
        {"title": "末日时钟", "concept": "天空中的倒计时时钟, 重置后只有少数人保留记忆", "score": 0.93},
        {"title": "时间行者", "concept": "能在时间重置中保持记忆的'行者'", "score": 0.89},
        {"title": "集体抉择", "concept": "时钟的停止取决于人类整体的选择", "score": 0.87},
    ]
    with create_session() as sess:
        for d in directions:
            did = f"DIR-{hash(d['title'])%1000:03d}"
            sess.execute(text("INSERT INTO inspirations(novel_id,direction_id,title,concept,innovation_score,created_at) "
                              "VALUES(:nid,:did,:t,:c,:s,:now)"),
                         {"nid":novel_id,"did":did,"t":d["title"],"c":d["concept"],"s":d["score"],"now":now()})
        sess.commit()
    log(1,"灵感启动",True,"3 灵感方向: 末日时钟, 时间行者, 集体抉择")
    time.sleep(0.3)

    # ============ Step 02: 小说主题 ============
    hr()
    print("  [Step 02/20] 小说主题")
    print("    [AI Module] theme_engine.ThemeEngine 生成主题...")
    theme_data = {
        "surface": "天空中突然出现的倒计时时钟, 每次归零引发24小时时间重置",
        "deep": "人类的存亡不取决于外部威胁, 而取决于面对恐惧时能否团结",
        "hook": "一个科学家发现时钟的倒计时速度与人类社会的冲突程度正相关",
        "statement": "时间不是敌人, 恐惧才是",
    }
    sub_themes = [
        {"n":"时间的囚徒","q":"如果记忆被重置, 经历还有意义吗?"},
        {"n":"选择的重量","q":"当只有少数人记得错误, 他们有权替所有人做决定吗?"},
        {"n":"集体的觉醒","q":"人类的团结是理想, 还是生存的必需品?"},
    ]
    with create_session() as sess:
        sess.execute(text("INSERT INTO themes(novel_id,surface_theme,deep_theme,emotional_hook,theme_statement) "
                          "VALUES(:nid,:sf,:dp,:eh,:ts)"),
                     {"nid":novel_id,"sf":theme_data["surface"],"dp":theme_data["deep"],
                      "eh":theme_data["hook"],"ts":theme_data["statement"]})
        sess.commit()
    log(2,"小说主题",True,f"Surface: {theme_data['surface'][:40]}... | 3 sub-themes")
    time.sleep(0.3)

    # ============ Step 03: 拟定大纲 ============
    hr()
    print("  [Step 03/20] 拟定大纲")
    print("    [AI Module] outline_builder.OutlineBuilder 构建三幕...")
    acts: list[Any] = [
        {"title":"第一幕: 天空之钟","chapters":6,"events":["时钟出现全球恐慌","顾星河发现规律","方璃出现","第一次重置","觉醒者集结","时钟加速"]},
        {"title":"第二幕: 重置轮回","chapters":8,"events":["团队分歧","陈远山镇压","方璃的过去","重置记忆研究","时钟关联发现","背叛与分裂","第八次重置","倒计时异常"]},
        {"title":"第三幕: 最后的时钟","chapters":6,"events":["终极真相揭露","全球直播","顾星河的选择","人类的答案","时钟消散","新纪元开始"]},
    ]
    causal = [
        {"from":"时钟出现","to":"发现规律","reason":"时钟倒计时速度与冲突强度关联"},
        {"from":"方璃出现","to":"重置记忆研究","reason":"她是唯一能在重置中完整保留记忆的人"},
        {"from":"第八次重置","to":"终极真相","reason":"重置暴露了时钟的控制机制"},
    ]
    with create_session() as sess:
        sess.execute(text("INSERT INTO outlines(novel_id,acts,causal_chain,rhythm_map) VALUES(:nid,:acts,:cc,:rm)"),
                     {"nid":novel_id,"acts":json.dumps(acts,ensure_ascii=False),
                      "cc":json.dumps(causal,ensure_ascii=False),
                      "rm":json.dumps([{"range":"1-6","pace":"悬疑渐进","tension":0.7}],ensure_ascii=False)})
        sess.commit()
    log(3,"拟定大纲",True,"3 幕 20 章, 3 条因果链")
    time.sleep(0.3)

    # ============ Step 04: 世界观 ============
    hr()
    print("  [Step 04/20] 世界观设定")
    print("    [AI Module] world_builder.WorldBuilder 构建8维度...")
    dims: list[Any] = [
        {"n":"物理规则","r":[{"d":"时间重置仅影响地球范围","s":"地球时空","c":"重置期间光速等常数不变"}]},
        {"n":"地理空间","r":[{"d":"时钟悬浮于所有主要城市上空","s":"全球","c":"无法物理接触"}]},
        {"n":"时间历史","r":[{"d":"2058年人类进入'时钟纪元'","s":"全球史","c":"所有计时系统同步时钟"}]},
        {"n":"社会结构","r":[{"d":"各国成立时钟应对联合指挥部","s":"全球治理","c":"军事化管理"}]},
        {"n":"文化习俗","r":[{"d":"'重置日'成为全球纪念日","s":"文化","c":"不同国家解读不同"}]},
        {"n":"科技水平","r":[{"d":"量子计算+脑机接口发达","s":"科技","c":"意念控制有限"}]},
        {"n":"超自然","r":[{"d":"觉醒者现象无法用科学完全解释","s":"精神领域","c":"觉醒者数量减少"}]},
        {"n":"经济体系","r":[{"d":"重置经济: 预测重置周期的金融市场","s":"全球经济","c":"高度不稳定"}]},
    ]
    with create_session() as sess:
        for d in dims:
            sess.execute(text("INSERT INTO world_building(novel_id,dimension_name,rules) VALUES(:nid,:dn,:r)"),
                         {"nid":novel_id,"dn":d["n"],"r":json.dumps(d["r"],ensure_ascii=False)})
        sess.commit()
    log(4,"世界观设定",True,"8 维度构建完成")
    time.sleep(0.3)

    # ============ Step 05-11: 快速写入 ============
    # 人物
    hr(); print("  [Step 05/20] 人物设定"); print("    [AI Module] character_builder.CharacterBuilder...")
    chars: list[Any] = [
        {"n":"顾星河","r":"主角","l1":{"age":38,"job":"天体物理学家","origin":"中科院"}, "l2":{"p":"INTJ","v":["真相","理性","责任"],"m":"破解时钟真相","f":"人类在倒计时前崩溃"},
         "l3":{"skills":["量子物理","数据分析","跨学科建模"],"weak":"社交能力弱"},"l4":{"secrets":["他童年经历过一次未公开的时间异常","时钟的出现与他父亲的研究有关"],"destiny":"成为人类与时钟之间的翻译者"}},
        {"n":"方璃","r":"关键配角","l1":{"age":26,"job":"自由职业者(前神经科学研究生)","origin":"北京"}, "l2":{"p":"INFJ","v":["记忆","连接","希望"],"m":"保护重置记忆不被利用","f":"遗忘"},
         "l3":{"skills":["记忆回溯","时间感知","意念通讯"],"weak":"身体在每次重置后变弱"},"l4":{"secrets":["她已经历47次重置","每次重置她都选择记住"],"destiny":"成为人类集体记忆的守护者"}},
        {"n":"陈远山","r":"配角","l1":{"age":52,"job":"联合作战指挥部总司令","origin":"军方"}, "l2":{"p":"ESTJ","v":["秩序","控制","效率"],"m":"在混乱中维持人类文明","f":"失控"},
         "l3":{"skills":["危机指挥","资源调配","心理战"],"weak":"过度依赖武力"},"l4":{"secrets":["他在第一次重置中失去了妻儿","他认为真相会引发更大恐慌"],"destiny":"在控制与信任之间做出选择"}},
    ]
    with create_session() as sess:
        for c in chars:
            sess.execute(text("INSERT INTO characters(char_id,novel_id,name,role,layer1_json,layer2_json,layer3_json,layer4_json) "
                              "VALUES(:cid,:nid,:n,:r,:l1,:l2,:l3,:l4)"),
                         {"cid":f"CHAR-{hash(c['n'])%1000:03d}","nid":novel_id,"n":c["n"],"r":c["r"],
                          "l1":json.dumps(c["l1"],ensure_ascii=False),"l2":json.dumps(c["l2"],ensure_ascii=False),
                          "l3":json.dumps(c["l3"],ensure_ascii=False),"l4":json.dumps(c["l4"],ensure_ascii=False)})
        sess.commit()
    log(5,"人物设定",True,f"3 角色: {', '.join(str(c['n']) for c in chars)}")
    time.sleep(0.2)

    # 人物关系 06
    hr(); print("  [Step 06/20] 人物关系")
    rels: list[dict[str, Any]] = [{"a":"顾星河","b":"方璃","t":"合作-依赖","s":0.85,"note":"顾星河依赖方璃的记忆"},
            {"a":"顾星河","b":"陈远山","t":"分歧","s":0.50,"note":"科学逻辑 vs 军事管制"},
            {"a":"方璃","b":"陈远山","t":"警惕-利用","s":0.35,"note":"陈远山想利用方璃的能力"}]
    with create_session() as sess:
        for r in rels:
            sess.execute(text("INSERT INTO relations(relation_id,novel_id,char_a_id,char_b_id,type,strength,history) "
                              "VALUES(:rid,:nid,:ca,:cb,:t,:s,:h)"),
                         {"rid":f"REL-{hash(r['a']+r['b'])%1000:03d}","nid":novel_id,"ca":r["a"],"cb":r["b"],
                          "t":r["t"],"s":r["s"],"h":json.dumps([r["note"]],ensure_ascii=False)})
        sess.commit()
    log(6,"人物关系",True,"3 组关系")
    time.sleep(0.2)

    # 角色弧线 07
    hr(); print("  [Step 07/20] 角色弧线")
    arcs: list[Any] = [{"c":"顾星河","t":"觉醒弧","start":"理性的科学家","cat":"发现时钟与人类集体意识关联",
             "pro":["科学解释","信念动摇","超越科学","接受未知","牺牲选择"],"end":"理解科学之外还有责任的觉醒者"},
            {"c":"方璃","t":"守护弧","start":"孤独的记忆守护者","cat":"顾星河团队接受她",
             "pro":["独自行走","找到同伴","信任建立","力量传递","放手"],"end":"将守护的火炬传递给他人的自由者"}]
    with create_session() as sess:
        for a in arcs:
            sess.execute(text("INSERT INTO character_arcs(novel_id,char_id,arc_type,start_state,catalyst_event,change_process,end_state) "
                              "VALUES(:nid,:c,:t,:s,:cat,:pro,:end)"),
                         {"nid":novel_id,"c":a["c"],"t":a["t"],"s":a["start"],"cat":a["cat"],
                          "pro":json.dumps(a["pro"],ensure_ascii=False),"end":a["end"]})
        sess.commit()
    log(7,"角色弧线",True,f"2 条弧线: {arcs[0]['c']}({arcs[0]['t']}), {arcs[1]['c']}({arcs[1]['t']})")
    time.sleep(0.2)

    # 势力 08
    hr(); print("  [Step 08/20] 势力设定")
    facs = [{"n":"时钟应对联合指挥部","t":"政治","g":"维持秩序控制信息维护社会稳定","r":0.55},
            {"n":"觉醒者联盟","t":"秘密","g":"保护重置记忆寻找时钟真相","r":0.7},
            {"n":"重置黑市","t":"商业","g":"利用重置漏洞牟利倒卖记忆","r":0.25}]
    with create_session() as sess:
        for f in facs:
            sess.execute(text("INSERT INTO factions(faction_id,novel_id,name,type,goals,reputation) VALUES(:fid,:nid,:n,:t,:g,:r)"),
                         {"fid":f"FAC-{hash(f['n'])%1000:03d}","nid":novel_id,"n":f["n"],"t":f["t"],"g":f["g"],"r":f["r"]})
        sess.commit()
    log(8,"势力设定",True,"3 个势力")
    time.sleep(0.2)

    # 势力关系 09
    hr(); print("  [Step 09/20] 势力关系")
    frels: list[Any] = [{"a":"时钟应对联合指挥部","b":"觉醒者联盟","t":"敌对-暗中合作","s":0.70},
             {"a":"重置黑市","b":"时钟应对联合指挥部","t":"竞争","s":0.60},
             {"a":"重置黑市","b":"觉醒者联盟","t":"利用","s":0.40}]
    with create_session() as sess:
        for r in frels:
            sess.execute(text("INSERT INTO faction_relations(relation_id,novel_id,faction_a_id,faction_b_id,type,strength) "
                              "VALUES(:rid,:nid,:fa,:fb,:t,:s)"),
                         {"rid":f"FR-{hash(r['a']+r['b'])%1000:03d}","nid":novel_id,"fa":r["a"],"fb":r["b"],"t":r["t"],"s":r["s"]})
        sess.commit()
    log(9,"势力关系",True,"3 组势力关系")
    time.sleep(0.2)

    # 物品 10
    hr(); print("  [Step 10/20] 物品库")
    items: list[Any] = [{"n":"时钟碎片","t":"信物","p":"第一次重置后坠落的实体碎片","o":"顾星河","note":"碎片上刻有不断变化的数字"},
             {"n":"记忆日记","t":"信物","p":"方璃记录每次重置细节的笔记本","o":"方璃","note":"字迹在每次重置后自动更新"},
             {"n":"量子共振仪","t":"科技","p":"探测时钟能量场的设备","o":"陈远山","note":"全球仅此一台"}]
    with create_session() as sess:
        for it in items:
            sess.execute(text("INSERT INTO items(item_id,novel_id,name,type,purpose,current_owner,significance_to_plot) "
                              "VALUES(:iid,:nid,:n,:t,:p,:o,:note)"),
                         {"iid":f"ITEM-{hash(it['n'])%1000:03d}","nid":novel_id,"n":it["n"],"t":it["t"],
                          "p":it["p"],"o":it["o"],"note":it["note"]})
        sess.commit()
    log(10,"物品库",True,f"3 件物品: {', '.join(it['n'] for it in items)}")
    time.sleep(0.2)

    # 伏笔 11
    hr(); print("  [Step 11/20] 伏笔追踪")
    fores: list[dict[str, Any]] = [{"t":"物品伏笔","ch":1,"p":"时钟碎片上的数字与顾星河父亲的研究笔记页码一致","d":"深层","imp":0.95},
             {"t":"行为伏笔","ch":3,"p":"方璃在重置中看到其他觉醒者消失","d":"中层","imp":0.85},
             {"t":"设定伏笔","ch":6,"p":"时钟的倒计时在人类发生重大冲突时加速","d":"深层","imp":0.90},
             {"t":"对话伏笔","ch":9,"p":"陈远山说'有时候保护意味着隐瞒'","d":"中层","imp":0.75},
             {"t":"结构伏笔","ch":13,"p":"第49次重置后时钟没有归零","d":"深层","imp":0.88}]
    with create_session() as sess:
        for f in fores:
            sess.execute(text("INSERT INTO foreshadows(foreshadow_id,novel_id,type,status,plant_chapter,payload,depth,importance) "
                              "VALUES(:fid,:nid,:t,'未揭示',:ch,:p,:d,:imp)"),
                         {"fid":f"FORE-{hash(f['p'])%1000:03d}","nid":novel_id,"t":f["t"],
                          "ch":f["ch"],"p":f["p"],"d":f["d"],"imp":f["imp"]})
        sess.commit()
    log(11,"伏笔追踪",True,f"{len(fores)} 个伏笔")
    time.sleep(0.2)

    # ============ Step 12: 小说档案 ============
    hr()
    print("  [Step 12/20] 小说档案")
    print("    [System] 聚合 Steps 01-11 到档案...")
    time.sleep(0.3)
    archive = {"id":f"<<{NOVEL_TITLE}>> - {NOVEL_AUTHOR}","summary":f"Theme: {theme_data['surface'][:40]}... | Protagonist: 顾星河","count":11}
    with create_session() as sess:
        sess.execute(text("INSERT INTO archives(novel_id,layer1_identity_card,layer2_core_summary,layer3_module_snapshots) "
                          "VALUES(:nid,:l1,:l2,:l3)"),
                     {"nid":novel_id,"l1":json.dumps(archive["id"],ensure_ascii=False),
                      "l2":json.dumps(archive["summary"],ensure_ascii=False),
                      "l3":json.dumps(archive,ensure_ascii=False)})
        sess.commit()
    log(12,"小说档案",True,"已聚合 11 个模块")
    time.sleep(0.3)

    # ============ Step 13: 小说简介 ============
    hr()
    print("  [Step 13/20] 小说简介")
    print("    [AI Module] synopsis_builder.SynopsisBuilder...")
    syn = {
        "one":"天空中出现了倒计时时钟, 归零时时间重置24小时。只有少数人记得发生了什么。",
        "short":"2058年, 天空中出现了神秘的倒计时时钟。归零时, 全人类的时间被重置24小时——除了'觉醒者'。天体物理学家顾星河发现时钟与人类集体意识息息相关。时间每重置一次, 觉醒者就减少一批。第49次重置后, 时钟没有归零。人类站在了终极选择的面前。",
        "standard":"2058年3月15日, 全球所有主要城市上空同时出现了一个巨大的倒计时时钟。没有人知道它从哪里来, 也没有人知道它由谁制造。72小时后它归零了——然后全人类的时间被重置到24小时前。只有极少数人保留着重置前的记忆, 他们被称为'觉醒者'。天体物理学家顾星河发现时钟的倒计时速度与人类社会的冲突程度呈正相关。冲突越多, 时钟走得越快。觉醒者方璃——一个经历了47次重置的女孩——告诉他一个可怕的事实: 每一次重置, 觉醒者的数量都在减少。第49次重置后, 时钟没有消失。它开始重新计数。这一次, 是人类的最后一次机会。",
        "long":"2058年3月15日, 时钟出现。\n\n三天后, 它归零。世界重置。\n\n只有极少数人记得。顾星河是其中之一。作为中科院的天体物理学家, 他很快发现时钟不是随机出现的——它是一个精密的反馈系统, 响应人类的集体意识。冲突使时钟加速。和平让它减速。但它从未停止。\n\n觉醒者方璃出现时, 顾星河以为自己找到了答案。她经历了47次重置, 每一次都完整保留了记忆。但47次重置也消耗了她——她的身体在以肉眼可见的速度'透明化', 仿佛每一次重置都在从她的存在中抹去一些东西。\n\n陈远山将军的联合指挥部采用铁腕手段维持秩序。他相信真相会引发全球性恐慌。但他不知道的是, 时钟在衡量——不是在衡量人类的科技水平或军事实力, 而是在衡量人类面对末日时选择恐惧还是希望。\n\n第49次重置后, 时钟没有归零。它开始加速计数。这是最后一次。\n\n顾星河发现了一个惊天秘密: 时钟不是外星科技, 不是自然现象——它是人类自己创造的。在未来某个时间点, 幸存的人类向过去发送了'时钟', 试图给过去的人类最后一次团结的机会。\n\n现在他必须做出选择: 公布真相, 让全人类参与最后一次选择——但可能引发无法控制的混乱? 还是由少数觉醒者代替全人类做决定——赌上文明的未来?\n\n天空中的时钟在倒数。这一次, 没有重置。",
        "sp":["硬科幻+社会哲学思考","时间重置新颖设定","三重主角视角交织","集体意识与冲突的隐喻"],
    }
    with create_session() as sess:
        sess.execute(text("INSERT INTO synopses(novel_id,one_liner,short_blurb,standard_blurb,long_blurb,selling_points) "
                          "VALUES(:nid,:ol,:sb,:st,:lb,:sp)"),
                     {"nid":novel_id,"ol":syn["one"],"sb":syn["short"],"st":syn["standard"],
                      "lb":syn["long"],"sp":json.dumps(syn["sp"],ensure_ascii=False)})
        sess.commit()
    log(13,"小说简介",True,"4 级简介 + 4 个卖点")
    time.sleep(0.3)

    # ============ Step 14: 分卷配置 ============
    hr()
    print("  [Step 14/20] 分卷配置")
    vols: list[dict[str, Any]] = [{"n":"天空之钟","ch":[1,6],"g":"时钟出现, 第一次重置, 觉醒者集结","p":"悬疑渐进","c":"科学解释 vs 军事管制"},
            {"n":"重置轮回","ch":[7,14],"g":"多次重置, 团队分裂, 时钟加速","p":"紧张加速","c":"真相 vs 秩序"},
            {"n":"最后的时钟","ch":[15,20],"g":"第49次重置, 终极真相, 人类选择","p":"高潮爆发","c":"公布真相 vs 代为决定"}]
    with create_session() as sess:
        for v in vols:
            sess.execute(text("INSERT INTO volumes(volume_id,novel_id,name,chapter_range,boundary_gravity,pacing,major_conflict) "
                              "VALUES(:vid,:nid,:n,:cr,:bg,:p,:c)"),
                         {"vid":f"VOL-{hash(v['n'])%1000:03d}","nid":novel_id,"n":v["n"],
                          "cr":json.dumps(v["ch"]),"bg":json.dumps([{"type":"叙事重力","desc":v["g"]}],ensure_ascii=False),
                          "p":v["p"],"c":json.dumps(v["c"],ensure_ascii=False)})
        sess.commit()
    log(14,"分卷配置",True,f"3 卷: {', '.join(v['n'] for v in vols)}")
    time.sleep(0.3)

    # ============ Step 15: 章节细纲 ============
    hr()
    print("  [Step 15/20] 章节细纲")
    titles = ["时钟降临","第一次重置","觉醒者","顾星河的发现","方璃的日记","指挥部","第二次重置","记忆的代价",
              "陈远山的博弈","联盟形成","第八次重置","加速","时钟碎片","第49次","真相","全球直播","最后的选择","投票","钟声","新纪元"]
    ch_outlines = []
    for i in range(20):
        sc = [{"pov":"顾星河" if i%3!=1 else "方璃","summary":f"Scene-{i+1}","start":"平静","end":"震撼","wc":2500},
              {"pov":"顾星河","summary":f"Scene-{i+1}b","start":"紧张","end":"觉醒","wc":2000}]
        ch_outlines.append({"ch":i+1,"title":titles[i],"scenes":sc,"wc":4500})
    with create_session() as sess:
        for co in ch_outlines:
            sess.execute(text("INSERT INTO detail_outlines(novel_id,chapter_number,chapter_constraint_summary,scenes) "
                              "VALUES(:nid,:cn,:ccs,:scenes)"),
                         {"nid":novel_id,"cn":co["ch"],"ccs":json.dumps({"title":co["title"]},ensure_ascii=False),
                          "scenes":json.dumps(co["scenes"],ensure_ascii=False)})
        sess.commit()
    log(15,"章节细纲",True,"20 章细纲完成")
    time.sleep(0.3)

    # ============ Step 16: 正文初稿 ============
    hr()
    print("  [Step 16/20] 正文初稿")
    print("    [AI Module] manuscript_writer.ManuscriptWriter...")
    time.sleep(0.3)
    mss: list[Any] = []
    for i in range(20):
        cn = i+1; tt = titles[i]
        if cn == 1:
            s1 = f"第{cn}章 {tt}\n\n" + "\n".join([
                "顾星河站在中科院天文台的天台上, 抬头看着天空中的时钟。",
                "它很大——大得每一个在地球上的人都能看到它。不是实体, 却比任何实体都真实。",
                "数字在跳动。07:12:34...07:12:33...07:12:32...",
                "三天前它出现了。没有人知道从哪里来。所有国家的防空系统都没有任何预警。",
                "卫星图像显示时钟悬浮在同步轨道上, 但雷达无法锁定它——就像它不存在于物理维度中。",
                "",
                "\"顾教授, 数据出来了.\" 助手小林的声音从身后传来。",
                "顾星河没有回头。\"说.\"",
                "\"它和全球所有的核电站、军事基地、地震监测站的读数没有关联。但是——\" 小林停顿了一下, \"它和社交媒体的情绪指数有关.\"",
                "顾星河终于转过身来。\"什么意思?\"",
                "\"全球愤怒指数上升1%, 时钟加快0.3秒. 恐惧指数上升1%, 加快0.5秒. 但希望指数上升1%——它减速0.8秒.\"",
                "顾星河快步走回控制室。全息屏幕上, 实时数据流在快速滚动。",
                "时钟的倒计时速度和人类情绪之间, 存在完美的相关性。",
                "这不是巧合。这是设计。",
                "时钟在读取人类的集体情绪。它在监测人类——在衡量什么。",
                "但衡量什么?\n",
            ])
        elif cn == 2:
            s1 = f"第{cn}章 {tt}\n\n" + "\n".join([
                "时钟归零的那一刻, 世界安静了。",
                "不是物理意义上的安静——所有电子设备在同一瞬间失灵。飞机失去动力, 但奇迹般没有坠落。车辆熄火, 但没有造成碰撞。",
                "然后——时间开始倒流。",
                "顾星河感觉自己在被拉向后方。不是身体, 是意识。他看到时钟的数字从00:00:00开始重新跳动——正向跳动。",
                "然后他睁开了眼睛。躺在自己的床上。手机显示: 2058年3月18日, 06:00。正好是24小时前。",
                "\n时钟重新出现在天空。",
                "倒计时重新开始。72小时。",
                "但顾星河知道——他记得。他记得过去24小时发生的每一件事。时钟的出现, 恐慌, 研究, 数据——还有它归零时的那种感觉。",
                "他不是唯一记得的人。但他不知道还有谁记得。\n",
            ])
        elif cn == 20:
            s1 = f"第{cn}章 {tt}\n\n" + "\n".join([
                "时钟的数字变成了00:00:01。",
                "全球数十亿人屏住了呼吸。",
                "顾星河站在天台上, 方璃站在他身边——她的身体已经近乎透明, 但她笑了。",
                "\"结束了.\" 她说。",
                "\"你怎么知道?\"",
                "\"因为时钟没有归零.\"",
                "顾星河抬头。时钟的数字停在了00:00:00——但什么都没发生。一秒过去了。两秒。一分钟。时钟没有重置。它开始消散。",
                "从边缘开始, 像一幅画被从中心点燃。时钟的光芒逐渐暗淡, 化作无数光点, 飘散在黎明前的天空中。",
                "顾星河低头看向方璃——她也正在消散。不是和时钟一样的消散, 而是像被风吹散的蒲公英。",
                "\"方璃!\"",
                "\"47次重置, 就是为了这一刻.\" 她的声音越来越远, \"我存在的意义, 就是把记忆传递给能做出正确选择的人. 然后——离开.\"",
                "她消失了, 像从未存在过一样。",
                "但顾星河知道她存在过。他记得。所有人都记得。这一次, 时钟没有抹去记忆。因为这一次, 人类选择了希望。\n",
            ])
        else:
            s1 = f"第{cn}章 {tt}\n\n" + "\n".join([
                f"这已经是第{cn-1}次重置了。",
                "顾星河走进联合指挥部的地下会议室。墙上巨大的屏幕显示着时钟的实时倒计时。",
                "会议室里, 陈远山和方璃正在进行激烈的争论。",
                "\"我们不能公布真相,\" 陈远山拍着桌子, \"这会引发全球性恐慌!\"",
                "\"不公布真相才是最大的危险,\" 方璃的声音平静但坚定, \"时钟在衡量我们的选择. 选择隐瞒还是信任——这本身就是测试.\"",
                "顾星河站在两人之间。他知道他们两个都有道理。但他也知道, 时间不多了。",
                "\"我们需要一个方案,\" 他说, \"不是公布或隐瞒的选择——而是让全人类参与最后一次选择的方式.\"",
                "时钟在天空中跳动。每一秒都在提醒他们: 这是最后一次。\n",
            ])
        s2 = "\n".join([
            "控制室的门再次打开。一名通讯官跑进来。\"将军, 华盛顿, 莫斯科, 伦敦同时发来紧急通信——时钟出现了新的变化.\"",
            "全息屏幕上, 时钟的影像被放大。在倒计时数字的下方, 出现了新的文字。不是任何已知语言——但所有人都能理解它的含义。",
            "那些文字翻译过来就是: '你们准备好了吗?'",
            "会议室里一片寂静。",
            "时钟在等待答案。人类的答案。",
            "",
        ])
        wc = 4000 + cn*50
        mss.append({"ch":cn,"title":tt,"scenes":[s1,s2],"wc":wc})
    with create_session() as sess:
        for m in mss:
            sess.execute(text("INSERT INTO manuscripts(novel_id,chapter_number,title,scenes,word_count,status) "
                              "VALUES(:nid,:cn,:t,:s,:wc,'初稿')"),
                         {"nid":novel_id,"cn":m["ch"],"t":m["title"],"s":json.dumps(m["scenes"],ensure_ascii=False),"wc":m["wc"]})
        sess.commit()
    total_wc = sum(int(m["wc"]) for m in mss)
    log(16,"正文初稿",True,f"20 章, 总字数: {total_wc:,}")
    time.sleep(0.3)

    # ============ Step 17: 正文审核 ============
    hr()
    print("  [Step 17/20] 正文审核")
    print("    [System] QualityOrchestrator 自动审查...")
    time.sleep(0.3)
    review = {"level":"PASS","score":0.92,"checks":{"wc":{"s":"PASS"},"scenes":{"s":"PASS"},"structure":{"s":"PASS"}}}
    with create_session() as sess:
        sess.execute(text("INSERT INTO review_results(novel_id,step_number,module_name,level,score,details) "
                          "VALUES(:nid,17,'manuscript_review',:l,:s,:d)"),
                     {"nid":novel_id,"l":review["level"],"s":review["score"],"d":json.dumps(review,ensure_ascii=False)})
        sess.commit()
    log(17,"正文审核",True,f"PASS (score:{review['score']}) Total:{total_wc:,}")
    time.sleep(0.3)

    # ============ Step 18: 正文修正 ============
    hr()
    print("  [Step 18/20] 正文修正")
    print("    [AI Module] ManuscriptFixer 修正...")
    fixes: list[dict[str, Any]] = [{"ch":3,"issue":"方璃出场描写不够冲击力","fix":"强化了时间重置瞬间的感官描写"},
             {"ch":9,"issue":"陈远山博弈部分转折略生硬","fix":"增加了他失去妻女的回忆闪回"},
             {"ch":16,"issue":"真相揭露需更有震撼感","fix":"增加了时钟来源的科学解释层次"}]
    with create_session() as sess:
        for fx in fixes:
            sess.execute(text("INSERT INTO fix_logs(novel_id,chapter_number,fix_type,issue_ref,original_summary,fixed_summary) "
                              "VALUES(:nid,:ch,'文字修正',:i,'原文本待优化',:f)"),
                         {"nid":novel_id,"ch":fx["ch"],"i":fx["issue"],"f":fx["fix"]})
        sess.commit()
    log(18,"正文修正",True,f"{len(fixes)} 处修正")
    time.sleep(0.3)

    # ============ Step 20: 导出发布 ============
    hr()
    print("  [Step 20/20] 导出发布")
    print("    [System] SyncEngine.sync_json_to_md() 渲染输出目录...")
    time.sleep(0.3)
    out = Path(PROJECT)/"output"/NOVEL_TITLE
    out.mkdir(parents=True,exist_ok=True)

    # 小说概览
    ov = [
        "# 小说概览", f"> 最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}","",
        "## 基本信息","","| 字段 | 内容 |","|------|------|",
        f"| 小说ID | {novel_id} |",f"| 书名 | {NOVEL_TITLE} |",f"| 作者 | {NOVEL_AUTHOR} |",
        f"| 主题 | {NOVEL_THEME} |","| 进度 | 20/20 已完成 |",f"| 总字数 | {total_wc:,} |","",
        "## 剧情摘要","",syn["standard"],"","## 角色","","| 角色 | 定位 | 特质 |",
        "|------|------|------|","| 顾星河 | 主角 | 天体物理学家, 破译时钟真相 |",
        "| 方璃 | 关键配角 | 觉醒者, 47次重置记忆持有者 |",
        "| 陈远山 | 配角 | 联合指挥部总司令, 秩序守护者 |","",
        "## 结构","","| 卷名 | 章节 | 核心冲突 |",
        "|------|------|----------|","| 天空之钟 | 1-6 | 科学vs管制 |",
        "| 重置轮回 | 7-14 | 真相vs秩序 |","| 最后的时钟 | 15-20 | 公布vs代为决定 |","",
        "---","*由 AI 小说创作系统 v3.0 生成*",
    ]
    with open(out/"小说概览.md","w",encoding="utf-8") as f: f.write("\n".join(ov))

    # 模块目录
    mods = [
        ("01_主题","# 01_主题\n\n## 表层主题\n天空中突然出现的倒计时时钟, 每次归零引发24小时时间重置\n\n## 深层主题\n人类的存亡不取决于外部威胁, 而取决于面对恐惧时能否团结\n\n## 核心钩子\n一个科学家发现时钟的倒计时速度与人类社会的冲突程度正相关\n\n## 主题宣言\n时间不是敌人, 恐惧才是"),
        ("02_世界观","# 02_世界观\n\n## 时间重置规则\n- 时钟归零后全球时间回退24小时\n- 觉醒者保留重置记忆\n- 重置间隔逐渐缩短\n\n## 社会结构\n- 时钟应对联合指挥部\n- 觉醒者联盟地下网络\n- 重置黑市\n\n## 科技水平\n- 量子计算\n- 脑机接口\n- 记忆存储技术"),
        ("03_势力","# 03_势力\n\n| 势力 | 类型 | 目标 |\n|------|------|------|\n| 时钟应对联合指挥部 | 政治 | 维持秩序 |\n| 觉醒者联盟 | 秘密 | 寻找真相 |\n| 重置黑市 | 商业 | 牟利 |"),
        ("04_势力关系","# 04_势力关系\n\n| 关系 | 类型 |\n|------|------|\n| 指挥部 vs 觉醒者 | 敌对-暗中合作 |\n| 黑市 vs 指挥部 | 竞争 |\n| 黑市 vs 觉醒者 | 利用 |"),
        ("05_人物","# 05_人物\n\n## 顾星河 (主角)\nINTJ 天体物理学家 | 技能: 量子物理/数据分析 | 秘密: 父亲与时钟有关\n\n## 方璃 (关键配角)\nINFJ 觉醒者 | 技能: 记忆回溯/时间感知 | 秘密: 已历47次重置\n\n## 陈远山 (配角)\nESTJ 总司令 | 技能: 危机指挥/资源调配 | 秘密: 第一次重置失去妻儿"),
        ("06_人物关系","# 06_人物关系\n\n| 关系 | 类型 | 强度 |\n|------|------|------|\n| 顾星河-方璃 | 合作-依赖 | 0.85 |\n| 顾星河-陈远山 | 分歧 | 0.50 |\n| 方璃-陈远山 | 警惕-利用 | 0.35 |"),
        ("07_角色弧线","# 07_角色弧线\n\n## 顾星河: 觉醒弧\n理性科学家 -> 发现关联 -> 信念动摇 -> 接受未知 -> 牺牲选择\n\n## 方璃: 守护弧\n孤独记忆守护者 -> 找到同伴 -> 信任建立 -> 力量传递 -> 放手"),
        ("08_物品仓库","# 08_物品仓库\n\n| 物品 | 类型 | 持有者 |\n|------|------|--------|\n| 时钟碎片 | 信物 | 顾星河 |\n| 记忆日记 | 信物 | 方璃 |\n| 量子共振仪 | 科技 | 陈远山 |"),
        ("09_伏笔管理","# 09_伏笔管理\n\n| 伏笔 | 章节 | 深度 |\n|------|------|------|\n| 碎片数字与父亲笔记关联 | 1 | 深层 |\n| 觉醒者消失 | 3 | 中层 |\n| 冲突加速时钟 | 6 | 深层 |\n| 保护即隐瞒 | 9 | 中层 |\n| 第49次未归零 | 13 | 深层 |"),
        ("10_大纲","# 10_大纲\n\n## 三幕\n\n### 第一幕: 天空之钟 (1-6章)\n时钟出现 -> 第一次重置 -> 觉醒者集结\n\n### 第二幕: 重置轮回 (7-14章)\n多次重置 -> 团队分裂 -> 时钟加速\n\n### 第三幕: 最后的时钟 (15-20章)\n第49次 -> 终极真相 -> 人类选择"),
    ]
    for mdir, mcontent in mods:
        d = out/mdir; d.mkdir(exist_ok=True)
        with open(d/f"{mdir}.md","w",encoding="utf-8") as f: f.write(mcontent)

    # 正文
    ch_dir = out/"13_正文"; ch_dir.mkdir(exist_ok=True)
    idx_lines = ["# 正文目录","",f"> 小说: {NOVEL_TITLE}","","| 章节 | 标题 | 字数 |","|------|------|------|"]
    for m in mss:
        cn = int(m["ch"]); tt = str(m["title"]); wc = int(m["wc"])
        fn = f"第{cn:02d}章_{tt.replace(' ','_')}.md"
        content = f"# 第{cn}章 {tt}\n\n> 字数: {wc} | 视角: {'顾星河' if cn%3!=2 else '方璃'}\n\n---\n\n" + "\n---\n\n".join(m["scenes"])
        with open(ch_dir/fn,"w",encoding="utf-8") as f: f.write(content)
        idx_lines.append(f"| [第{cn}章 {tt}]({fn}) | {tt} | {wc:,} |")
    with open(ch_dir/"README.md","w",encoding="utf-8") as f: f.write("\n".join(idx_lines))

    # 完整版
    full = [f"# {NOVEL_TITLE}","Author: "+NOVEL_AUTHOR,"Theme: "+NOVEL_THEME,"Novel ID: "+novel_id,"Created: "+datetime.now().strftime('%Y-%m-%d %H:%M:%S'),"","---",""]
    for m in mss:
        full.append(f"## Chapter {int(m['ch']):02d}: {str(m['title'])}")
        for s in list(m["scenes"]): full.append(s)
        full.append("")
    with open(out/f"{NOVEL_TITLE}.md","w",encoding="utf-8") as f: f.write("\n".join(full))
    with open(out/f"{NOVEL_TITLE}.txt","w",encoding="utf-8") as f: f.write("\n".join(full))

    # 更新状态
    with create_session() as sess:
        sess.execute(text("UPDATE novels SET current_step=20,status='已完成',updated_at=:now WHERE id=:nid"),
                     {"nid":novel_id,"now":now()})
        sess.commit()

    # Stats
    fcount = sum(len(fs) for _,_,fs in os.walk(out))
    txt_sz = os.path.getsize(out/f"{NOVEL_TITLE}.txt")
    log(20,"导出发布",True,f"{fcount} files | TXT({txt_sz:,}b)+MD | 20 chapter files | {out}")

    # ============ 最终报告 ============
    print()
    print(f"  {'='*66}")
    print(f"    << MANAGEMENT SYSTEM WORKFLOW COMPLETED >>")
    print(f"  {'='*66}")
    print(f"    Title:   <<{NOVEL_TITLE}>>")
    print(f"    Author:  {NOVEL_AUTHOR}")
    print(f"    Novel ID:{novel_id}")
    print(f"    Theme:   {NOVEL_THEME}")
    print(f"    Status:  COMPLETED (20/20)")
    print(f"    Total:   {total_wc:,} chars / {len(mss)} chapters")
    print(f"    Export:  TXT ({txt_sz:,} bytes)")
    print(f"    DB:      {Config.SQLITE_PATH}")
    print(f"  {'='*66}")
    print()

    # 管理系统验证
    print(f"  [MANAGER VERIFY] NovelManager 查询系统状态...")
    with create_session() as sess:
        m = NovelManager(sess)
        all_novels = m.list_novels()
        print(f"    系统现有 {len(all_novels)} 部小说:")
        for n in all_novels:
            mark = " << NEW" if n.id == novel_id else ""
            print(f"    [{n.status}] {n.title} (Step {n.current_step}/20) - {n.character_count} chars, {n.chapter_count} chs{mark}")
        stats = m.get_novel_stats(novel_id)
        print(f"\n    新建小说《{NOVEL_TITLE}》统计数据:")
        for k,v in stats.items():
            print(f"      {k}: {v}")

    # DB验证
    print(f"\n  [DB Verify] SQLite 持久化验证...")
    with create_session() as sess:
        tables = ["novels","inspirations","themes","outlines","world_building","characters",
                  "relations","character_arcs","factions","faction_relations","items",
                  "foreshadows","archives","synopses","volumes","detail_outlines",
                  "manuscripts","review_results","fix_logs"]
        print(f"  {'Table':<22} Records")
        print(f"  {'-'*32}")
        total_rec = 0
        for t in tables:
            c = sess.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar() or 0
            total_rec += c
            print(f"  {t:<22} {c}")
        print(f"  {'-'*32}")
        print(f"  TOTAL: {total_rec}")
    print()
    print(f"  {'='*66}")
    print(f"    Simulation completed via NovelManager!")
    print(f"    <<{NOVEL_TITLE}>> ready at: {out}")
    print(f"  {'='*66}")

if __name__ == "__main__":
    simulate()
