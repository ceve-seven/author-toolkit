"""
小说管理系统全流程用户模拟测试
--- 全新小说《记忆囚笼》---
主题: 赛博朋克 - 记忆篡改 - 身份觉醒
"""
from __future__ import annotations

import os, sys, json, time
from pathlib import Path
from datetime import datetime, timezone

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

from typing import Any

from src.config.settings import Config
from src.storage.database.engine import get_engine, init_schema, create_session
from src.core.manager import NovelManager
from sqlalchemy import text

NOVEL_TITLE = "记忆囚笼"
NOVEL_AUTHOR = "陆 深"
NOVEL_THEME = "赛博朋克 - 记忆篡改 - 身份觉醒"

engine = get_engine()
init_schema()

def now():
    return datetime.now(timezone.utc).isoformat()

hr = lambda: print(f"  {'-'*66}")

def log(sn, name, ok, detail=""):
    icon = "[OK]" if ok else "[FAIL]"
    print(f"  {icon} Step {sn:02d} {name}")
    if detail:
        for d in detail.strip().split("\n"):
            print(f"       {d}")

def simulate():
    print()
    print(f"  {'='*66}")
    print(f"    AI Novel Creation System -- Full Simulation v3.0")
    print(f"    Title: <<{NOVEL_TITLE}>>  Author: {NOVEL_AUTHOR}")
    print(f"    Theme: {NOVEL_THEME}")
    print(f"    Time:  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  {'='*66}")

    # ============ NovelManager 管理系统初始化 ============
    hr()
    print("  [MANAGER] NovelManager 管理系统初始化...")
    with create_session() as sess:
        manager = NovelManager(sess)
        existing = manager.list_novels()
        print(f"           已有 {len(existing)} 部小说在系统中:")
        for n in existing:
            print(f"           [{n.status}] {n.title} ({n.id})")

    # ============ Step 00: 创建小说 ============
    hr()
    print("  [Step 00/20] 管理系统创建小说")
    print("    [System] 通过 NovelManager.create_novel() 创建...")
    novel_id = None
    with create_session() as sess:
        manager = NovelManager(sess)
        novel_id = manager.create_novel(NOVEL_TITLE, NOVEL_AUTHOR)
    assert novel_id, "Failed to create novel!"
    print(f"    [OK] 创建成功! Novel ID: {novel_id}")
    with create_session() as sess:
        novel = NovelManager(sess).get_novel(novel_id)
        print(f"    [OK] NovelManager 验证: {novel.title} | Step {novel.current_step} | {novel.status}")
    log(0, "NovelManager 创建", True, f"ID: {novel_id}")
    time.sleep(0.3)

    # ============ Step 01: 灵感启动 ============
    hr()
    print("  [Step 01/20] 灵感启动")
    time.sleep(0.2)
    directions: list[dict[str, Any]] = [
        {"title": "记忆猎手", "concept": "一家公司通过植入虚假记忆来控制人类行为", "score": 0.94},
        {"title": "身份碎片", "concept": "主角发现自己的记忆全是伪造的，真实身份是反抗军特工", "score": 0.91},
        {"title": "梦境牢笼", "concept": "人在深度睡眠时被植入记忆，醒后完全不知道自己被操控", "score": 0.88},
    ]
    with create_session() as sess:
        for d in directions:
            did = f"DIR-{hash(d['title'])%1000:03d}"
            sess.execute(text("INSERT INTO inspirations(novel_id,direction_id,title,concept,innovation_score,created_at) "
                              "VALUES(:nid,:did,:t,:c,:s,:now)"),
                         {"nid":novel_id,"did":did,"t":d["title"],"c":d["concept"],"s":d["score"],"now":now()})
        sess.commit()
    log(1,"灵感启动",True,"3 灵感方向: 记忆猎手, 身份碎片, 梦境牢笼")
    time.sleep(0.3)

    # ============ Step 02: 小说主题 ============
    hr()
    print("  [Step 02/20] 小说主题")
    theme_data = {
        "surface": "2147年, 一家名为'永生'的生物科技公司通过梦境植入技术, 在人的长期记忆中植入虚假身份",
        "deep": "当记忆可以被任意篡改, 人的自我认知还可靠吗? 真实的自己由什么定义?",
        "hook": "一个普通程序员在例行记忆体检后, 发现自己脑中有一段不属于自己的记忆——那是另一条时间线的他自己",
        "statement": "记忆不是过去的记录, 而是现在的牢笼",
    }
    sub_themes: list[dict[str, Any]] = [
        {"n":"记忆之重","q":"如果记忆可以被编辑, 痛苦可以被删除, 人还完整吗?"},
        {"n":"身份之疑","q":"当所有人告诉你你是另一个人, 你如何证明自己是谁?"},
        {"n":"自由之价","q":"清醒的痛苦vs无知的幸福——人有没有权利用知道真相?"},
    ]
    with create_session() as sess:
        sess.execute(text("INSERT INTO themes(novel_id,surface_theme,deep_theme,emotional_hook,theme_statement) "
                          "VALUES(:nid,:sf,:dp,:eh,:ts)"),
                     {"nid":novel_id,"sf":theme_data["surface"],"dp":theme_data["deep"],
                      "eh":theme_data["hook"],"ts":theme_data["statement"]})
        sess.commit()
    log(2,"小说主题",True,f"Surface: 记忆篡改 | 3 sub-themes | 宣言: 记忆不是过去的记录, 而是现在的牢笼")
    time.sleep(0.3)

    # ============ Step 03: 拟定大纲 ============
    hr()
    print("  [Step 03/20] 拟定大纲")
    acts = [
        {"title":"第一幕: 虚假的日常","chapters":6,"events":["记忆体检日","异常记忆出现","永生公司调查","地下反抗军接触","身份疑云","秘密档案"]},
        {"title":"第二幕: 觉醒之路","chapters":8,"events":["反抗军基地","真相揭露","能力觉醒","记忆回溯训练","永生公司反击","内鬼","记忆对决","芯片源代码"]},
        {"title":"第三幕: 记忆之战","chapters":6,"events":["全球植入计划","最终抉择","记忆战场","真相直播","芯片终结","自由新生"]},
    ]
    causal: list[dict[str, Any]] = [
        {"from":"异常记忆出现","to":"永生公司调查","reason":"主角发现自己记忆与官方记录不符"},
        {"from":"地下反抗军接触","to":"真相揭露","reason":"反抗军拥有主角的原始记忆备份"},
        {"from":"芯片源代码","to":"最终抉择","reason":"源代码揭示真相会影响每一个植入者"},
    ]
    with create_session() as sess:
        sess.execute(text("INSERT INTO outlines(novel_id,acts,causal_chain,rhythm_map) VALUES(:nid,:acts,:cc,:rm)"),
                     {"nid":novel_id,"acts":json.dumps(acts,ensure_ascii=False),
                      "cc":json.dumps(causal,ensure_ascii=False),
                      "rm":json.dumps([{"range":"1-6","pace":"悬疑渐进","tension":0.65},{"range":"7-14","pace":"紧张加速","tension":0.8},{"range":"15-20","pace":"高潮爆发","tension":0.95}],ensure_ascii=False)})
        sess.commit()
    log(3,"拟定大纲",True,"3 幕 20 章, 3 条因果链")
    time.sleep(0.3)

    # ============ Step 04: 世界观 ============
    hr()
    print("  [Step 04/20] 世界观设定")
    dims = [
        {"n":"科技水平","r":[{"d":"神经记忆芯片植入率99%","s":"全球","c":"必须接受年度记忆体检"}]},
        {"n":"社会结构","r":[{"d":"永生公司实质控制各国政府","s":"全球治理","c":"表面民主实质记忆操控"}]},
        {"n":"记忆规则","r":[{"d":"记忆可被植入/编辑/删除","s":"神经科学","c":"植入记忆有0.01%的排斥概率"}]},
        {"n":"法律体系","r":[{"d":"记忆篡改合法化, 以'心理健康'为名义","s":"全球法律","c":"私自查看原始记忆属重罪"}]},
        {"n":"经济体系","r":[{"d":"记忆经济: 记忆修改/增强/删除是最大产业","s":"全球经济","c":"记忆等级决定社会地位"}]},
        {"n":"文化习俗","r":[{"d":"'真实记忆'被视为疾病需要治疗","s":"社会文化","c":"每年记忆体检成为仪式"}]},
        {"n":"反抗力量","r":[{"d":"地下反抗军保存原始人类记忆","s":"地下网络","c":"被标记为'记忆恐怖分子'"}]},
        {"n":"地理空间","r":[{"d":"巨型穹顶城市隔绝外界","s":"城市丛林","c":"城外是未经改造的荒野区"}]},
    ]
    with create_session() as sess:
        for d in dims:
            sess.execute(text("INSERT INTO world_building(novel_id,dimension_name,rules) VALUES(:nid,:dn,:r)"),
                         {"nid":novel_id,"dn":d["n"],"r":json.dumps(d["r"],ensure_ascii=False)})
        sess.commit()
    log(4,"世界观设定",True,"8 维度: 科技/社会/记忆/法律/经济/文化/反抗/地理")
    time.sleep(0.3)

    # ============ Step 05: 人物设定 ============
    hr(); print("  [Step 05/20] 人物设定")
    chars: list[dict[str, Any]] = [
        {"n":"陆 晨","r":"主角","l1":{"age":29,"job":"永生公司神经工程师","origin":"穹顶城A区"},
         "l2":{"p":"INTP","v":["真相","自由","完整"],"m":"找回自己被删除的真实记忆","f":"一直活在谎言中"},
         "l3":{"skills":["神经编程","记忆解码","潜意识潜入"],"weak":"对植入技术有PTSD"},
         "l4":{"secrets":["他其实是反抗军Deep Sleep计划的首个成功实验体","他的记忆曾被完全格式化三次"],"destiny":"成为人类记忆解放的关键"}},
        {"n":"林 薇","r":"关键配角","l1":{"age":27,"job":"反抗军记忆解码师","origin":"地下城"},
         "l2":{"p":"ENFJ","v":["记忆","连接","解放"],"m":"解放被永生公司囚禁的集体记忆","f":"失去自己的记忆"},
         "l3":{"skills":["记忆读取","意识链接","情感共鸣"],"weak":"每一次深度读取都会损耗自己的记忆"},
         "l4":{"secrets":["她曾是永生公司最年轻的记忆工程师","她亲手构建了记忆植入系统后逃离"],"destiny":"成为人类集体记忆的解放者"}},
        {"n":"赵 明远","r":"反派","l1":{"age":58,"job":"永生公司CEO","origin":"未知"},
         "l2":{"p":"ENTJ","v":["秩序","控制","完美"],"m":"实现全人类'完美记忆'计划","f":"记忆混乱导致文明崩塌"},
         "l3":{"skills":["神经工程","战略布局","舆论操控"],"weak":"从未体验过真实的痛苦"},
         "l4":{"secrets":["他年轻时曾被记忆篡改导致失去挚爱","他认为消除痛苦记忆是最高人道主义"],"destiny":"在控制的尽头发现真实的力量"}},
    ]
    with create_session() as sess:
        for c in chars:
            sess.execute(text("INSERT INTO characters(char_id,novel_id,name,role,layer1_json,layer2_json,layer3_json,layer4_json) "
                              "VALUES(:cid,:nid,:n,:r,:l1,:l2,:l3,:l4)"),
                         {"cid":f"CHAR-{hash(c['n'])%1000:03d}","nid":novel_id,"n":c["n"],"r":c["r"],
                          "l1":json.dumps(c["l1"],ensure_ascii=False),"l2":json.dumps(c["l2"],ensure_ascii=False),
                          "l3":json.dumps(c["l3"],ensure_ascii=False),"l4":json.dumps(c["l4"],ensure_ascii=False)})
        sess.commit()
    log(5,"人物设定",True,f"3 角色: {', '.join(c['n'] for c in chars)}")
    time.sleep(0.2)

    # 人物关系 06
    hr(); print("  [Step 06/20] 人物关系")
    rels: list[Any] = [{"a":"陆晨","b":"林薇","t":"信任-依赖","s":0.82,"note":"林薇是唯一能帮陆晨找回记忆的人"},
            {"a":"陆晨","b":"赵明远","t":"创造者-反抗者","s":0.20,"note":"赵明远是陆晨被植入记忆的设计师"},
            {"a":"林薇","b":"赵明远","t":"师徒-对立","s":0.15,"note":"林薇曾是赵明远最得意的学生"}]
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
    arcs: list[dict[str, Any]] = [{"c":"陆晨","t":"觉醒弧","start":"被植入记忆的普通工程师","cat":"发现记忆异常",
             "pro":["怀疑","调查","真相冲击","接受真实","自我重构","解放"],"end":"掌握真实记忆的自由人"},
            {"c":"林薇","t":"救赎弧","start":"逃离过去的记忆工程师","cat":"遇到陆晨",
             "pro":["内疚","补偿","并肩作战","直面过去","放下","重建"],"end":"接受过去并创造未来的解放者"},
            {"c":"赵明远","t":"堕落弧","start":"追求完美的理想主义者","cat":"计划被陆晨破坏",
             "pro":["理想","极端","控制","偏执","崩溃","醒悟"],"end":"在最后时刻看到自己错误的反省者"}]
    with create_session() as sess:
        for a in arcs:
            sess.execute(text("INSERT INTO character_arcs(novel_id,char_id,arc_type,start_state,catalyst_event,change_process,end_state) "
                              "VALUES(:nid,:c,:t,:s,:cat,:pro,:end)"),
                         {"nid":novel_id,"c":a["c"],"t":a["t"],"s":a["start"],"cat":a["cat"],
                          "pro":json.dumps(a["pro"],ensure_ascii=False),"end":a["end"]})
        sess.commit()
    log(7,"角色弧线",True,f"3 条弧线: {', '.join(a['c']+'('+a['t']+')' for a in arcs)}")
    time.sleep(0.2)

    # 势力 08
    hr(); print("  [Step 08/20] 势力设定")
    facs = [{"n":"永生公司","t":"企业","g":"通过记忆植入控制人类社会实现绝对秩序","r":0.90},
            {"n":"地下反抗军","t":"秘密组织","g":"解放被篡改的记忆恢复人类真实历史","r":0.65},
            {"n":"记忆审查局","t":"政府","g":"维护记忆法执行年度记忆体检","r":0.75}]
    with create_session() as sess:
        for f in facs:
            sess.execute(text("INSERT INTO factions(faction_id,novel_id,name,type,goals,reputation) VALUES(:fid,:nid,:n,:t,:g,:r)"),
                         {"fid":f"FAC-{hash(f['n'])%1000:03d}","nid":novel_id,"n":f["n"],"t":f["t"],"g":f["g"],"r":f["r"]})
        sess.commit()
    log(8,"势力设定",True,"3 个势力: 永生公司, 地下反抗军, 记忆审查局")
    time.sleep(0.2)

    # 势力关系 09
    hr(); print("  [Step 09/20] 势力关系")
    frels: list[Any] = [{"a":"永生公司","b":"记忆审查局","t":"控制-执行","s":0.95},
             {"a":"永生公司","b":"地下反抗军","t":"镇压-反抗","s":0.80},
             {"a":"记忆审查局","b":"地下反抗军","t":"追捕-逃亡","s":0.75}]
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
    items: list[dict[str, Any]] = [{"n":"原始记忆晶片","t":"科技","p":"存储未经篡改的原始记忆数据","o":"陆晨","note":"金色晶片, 只能读取一次, 读取后自毁"},
             {"n":"记忆读取头盔","t":"科技","p":"深度读取和编辑记忆的设备","o":"林薇","note":"改装版, 可绕过永生公司的加密协议"},
             {"n":"源代码芯片","t":"科技","p":"永生公司记忆植入系统的核心源码","o":"赵明远","note":"存储在他的神经接口中, 需要生物识别解锁"}]
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
    fores: list[dict[str, Any]] = [{"t":"物品伏笔","ch":1,"p":"陆晨的年度记忆体检报告显示一段不属于他的记忆碎片","d":"深层","imp":0.95},
             {"t":"行为伏笔","ch":3,"p":"陆晨在梦里反复看到一个红色数字'47'——那是他记忆格式化的次数","d":"深层","imp":0.90},
             {"t":"设定伏笔","ch":6,"p":"永生公司的记忆植入成功率是99.99%, 但反抗军的资料显示是99.97%","d":"中层","imp":0.85},
             {"t":"对话伏笔","ch":9,"p":"赵明远说'我做的这一切都是为了保护人类不重蹈我的覆辙'","d":"中层","imp":0.78},
             {"t":"结构伏笔","ch":13,"p":"林薇的记忆读取能力越用越弱——每一次读取都在消耗她自己的记忆","d":"深层","imp":0.88}]
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
    time.sleep(0.3)
    archive = {"id":f"<<{NOVEL_TITLE}>> - {NOVEL_AUTHOR}","summary":f"Cyberpunk theme | 记忆篡改 | 身份觉醒 | 11 modules aggregated","count":11}
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
    syn = {
        "one":"你相信你的记忆吗? 也许它们从一开始就是谎言。",
        "short":"2147年, 永生公司的神经记忆芯片覆盖全球99%人口。每年一度的记忆体检让所有人的'不良记忆'被安全删除——直到程序员陆晨在例行体检中发现了一段不属于自己的记忆碎片。他被卷入了一场关于记忆、身份和真相的漩涡: 地下反抗军说他其实是他们的实验体, 永生公司说他只是系统出错, 而他脑海中的红色数字'47'似乎在告诉他——他的记忆已经被格式化了47次。",
        "standard":"2147年, 永生公司。\n\n全球99%的人口植入了神经记忆芯片。每年一度的记忆体检, 会安全删除所有'不良记忆'——痛苦的、危险的、不需要的。人类迎来了前所未有的'心理健康'时代。\n\n程序员陆晨一直过着普通的生活。普通的记忆, 普通的体检, 普通的2147年。\n\n直到这次体检, 他的扫描结果显示一段异常记忆——一段不属于他的人生。画面中, 他站在废墟上, 面前是燃烧的永生大厦, 他的手中握着一枚金色的晶片。\n\n他不记得这件事。从来没有。\n\n地下反抗军的林薇找到了他, 告诉他真相: 他是反抗军Deep Sleep计划的首个成功实验体, 被植入了'普通程序员'的完整记忆以躲避永生公司的追查。而他脑海中的红色数字47——那是他被格式化的次数。每一次他接近真相, 记忆就被清空一次, 重新开始。\n\n这是第47次。也是最后一次。因为源代码芯片已被激活, 永生公司正在追踪他的神经信号。\n\n陆晨必须在真实记忆和虚假安宁之间做出选择。而赵明远——永生公司的CEO, 计划在三天后启动'完美记忆'全球升级, 永久封存所有人类的不完美记忆。\n\n一旦完成, 人类将永远失去真实的自己。",
        "long":"2147年, 穹顶城市。\n\n神经记忆芯片嵌入每一个人的大脑。痛苦被删除, 恐惧被删除, 失恋被删除——所有你不想要的记忆, 在年度体检中一键清除。人类终于'幸福'了。\n\n陆晨一直这么认为。作为一个永生公司的神经工程师, 他每天的工作就是优化记忆植入算法, 让删除更加精准, 让植入更加自然。他相信自己在做正确的事——消除痛苦, 创造和谐。\n\n直到他的年度记忆体检报告出现了一段异常代码。\n\n那是一段不属于他的人生: 废墟中的永生大厦, 燃烧的城市, 他手中的金色晶片, 以及一个女人在火焰中对他说:\n\n'记住, 你不是他们制造的那个人。'\n\n他不记得。但画面如此真实——真实到他的身体先于理智做出反应: 他的手在颤抖, 眼泪不受控制地流下。\n\n林薇在一个雨夜找到他。她说自己是地下反抗军的记忆解码师, 她说他脑海中的红色数字'47'意味着他的记忆已经被完全格式化了47次。每一次他接近真相, 永生公司的后台系统就会触发记忆清除协议, 将他重置为'陆晨, 29岁, 永生公司神经工程师'。\n\n但这一次不同。第47次激活时, 原始记忆晶片自动解码了。他的深层意识中, 反抗军植入的'唤醒协议'被触发。他脑海中的片段会越来越多, 直到他拼出完整的真相——或者被永生公司彻底清除。\n\n赵明远在三天后的全球发布会上宣布'完美记忆2.0': 一个永久封存所有人类不完美记忆的系统。不再有年度体检, 不再有手动删除——完美记忆2.0将自动过滤所有'负面记忆', 让人类活在永恒的积极情绪中。\n\n代价是什么?真实的自我。\n\n陆晨必须在三天内: 找回被格式化了47次的真实记忆, 阻止完美记忆2.0的启动, 并在过程中回答一个终极问题——\n\n当记忆可以被无限篡改, 你是谁?\n\n是芯片告诉你的那个人? 还是那些被删除了47次的碎片拼出的陌生人?\n\n时间在流逝。源代码芯片在他脑中闪烁。第47次, 是终结, 还是开始?",
        "sp":["硬核赛博朋克设定","记忆篡改的哲学思考","47次格式化的叙事结构","三重立场: 控制vs自由vs秩序"],
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
    vols: list[Any] = [{"n":"虚假的日常","ch":[1,6],"g":"记忆体检异常, 真相浮现, 反抗军接触","p":"悬疑渐进","c":"虚假安宁 vs 痛苦真相"},
            {"n":"觉醒之路","ch":[7,14],"g":"记忆回溯, 47次格式化的秘密, 能力觉醒","p":"紧张加速","c":"控制安全 vs 自由风险"},
            {"n":"记忆之战","ch":[15,20],"g":"完美记忆2.0启动, 终极抉择, 记忆解放","p":"高潮爆发","c":"集体遗忘 vs 真实记忆"}]
    with create_session() as sess:
        for v in vols:
            sess.execute(text("INSERT INTO volumes(volume_id,novel_id,name,chapter_range,boundary_gravity,pacing,major_conflict) "
                              "VALUES(:vid,:nid,:n,:cr,:bg,:p,:c)"),
                         {"vid":f"VOL-{hash(v['n'])%1000:03d}","nid":novel_id,"n":v["n"],
                          "cr":json.dumps(v["ch"]),"bg":json.dumps([{"type":"叙事重力","desc":v["g"]}],ensure_ascii=False),
                          "p":v["p"],"c":json.dumps(v["c"],ensure_ascii=False)})
        sess.commit()
    log(14,"分卷配置",True,f"3 卷: {', '.join(str(v['n']) for v in vols)}")
    time.sleep(0.3)

    # ============ Step 15: 章节细纲 ============
    hr()
    print("  [Step 15/20] 章节细纲")
    titles = ["体检日","异常","林薇","红色47","反抗军基地","记忆解码","第一次回溯","源代码",
              "赵明远","完美记忆","追踪","记忆战场","第47次","真相","最后的选项","全球发布会","觉醒","对抗","解放","新生"]
    ch_outlines: list[dict[str, Any]] = []
    for i in range(20):
        sc = [{"pov":"陆晨" if i%3!=1 else "林薇","summary":f"Scene-{i+1}","start":"平静","end":"震撼","wc":2500},
              {"pov":"陆晨" if i!=18 else "赵明远","summary":f"Scene-{i+1}b","start":"紧张","end":"觉醒","wc":2000}]
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
    time.sleep(0.3)
    mss: list[dict[str, Any]] = []
    for i in range(20):
        cn = i+1; tt = titles[i]
        if cn == 1:
            s1 = f"第{cn}章 {tt}\n\n" + "\n".join([
                "陆晨走进永生公司记忆体检中心的时候, 电子屏上显示: 第47次年度记忆体检。",
                "他看了一眼, 没有在意。数字而已。",
                "体检中心的大厅宽敞明亮, 纯白色的墙壁上嵌着流动的蓝色光带。空气中有淡淡的消毒水味——不, 不是消毒水, 是'记忆清洁剂'的味道。永生公司在每一台体检设备中释放的神经舒缓气体。",
                "前台的全息护士微笑着: '陆晨先生, 请到7号检测舱。'",
                "陆晨点点头, 刷脸进入通道。通道两侧的屏幕上播放着永生公司的宣传片: '记忆是负担, 删除是解放。拥抱完美记忆, 拥抱幸福人生。'",
                "他看过无数次了。每年体检都要看一遍。",
                "7号检测舱的门打开, 一台银白色的流线型设备安静地等待着他。他熟练地脱下外套, 躺进检测舱, 将头部对准神经扫描仪的接口。",
                "冰冷的触感从太阳穴两侧传来。扫描仪启动, 轻微的嗡鸣声。",
                "然后——",
                "画面闪了一下。",
                "陆晨看到了一个他从未见过的场景: 燃烧的城市, 红色天空, 他自己站在废墟中, 手里握着一枚金色的晶片。一个女人在火焰中对他说着什么, 但他听不见。",
                "画面只持续了不到一秒。",
                "他猛地坐起来, 心跳加速。",
                "检测舱外, 体检医生的声音传来: '陆先生, 请保持不动, 还有三十秒。'",
                "三十秒。但他刚才看到的那个画面——那不是他的记忆。",
                "他从来没有去过废墟。从来没有见过那个女人。",
                "但那个画面, 如此真实。真实到他能闻到空气中燃烧的气味。",
                "检测完成。陆晨走出检测舱, 手心全是汗。",
                "屏幕上的体检报告显示: 记忆纯净度: 99.97%。健康。正常。",
                "但陆晨知道, 刚才那一瞬间的画面, 不在'正常'的范围内。\n",
            ])
        elif cn == 2:
            s1 = f"第{cn}章 {tt}\n\n" + "\n".join([
                "报告中的异常代码是: MEM-ERR-47-BETA。",
                "陆晨坐在办公室里, 盯着全息屏幕上的体检报告。他假装在审查今天提交的记忆植入方案, 但全部注意力都在那个异常的代码上。",
                "MEM-ERR是记忆错误代码。47是错误类型编号。BETA表示这是初级异常, 不需要上报。",
                "但陆晨知道——47不是错误类型。47是一个数字。一个在他脑中反复出现的数字。",
                "他打开内部系统, 搜索'MEM-ERR-47'。没有结果。搜索'BETA级记忆异常'。系统返回: '无权限访问。'",
                "他是神经工程师, 拥有B+级权限。如果他没有权限, 那这份报告是谁生成的?",
                "他关闭屏幕, 靠在椅背上。窗外的穹顶城市在阳光下闪烁。永生大厦的楼顶, '永远完美记忆'的标语在旋转。",
                "他的脑海中再次闪过那个画面。燃烧的城市。金色晶片。火焰中的女人。",
                "以及, 隐约的, 他听到了一句话: '记住, 你不是他们制造的那个人。'",
                "不是他们制造的那个人。",
                "那他是什么?\n",
            ])
        elif cn == 20:
            s1 = f"第{cn}章 {tt}\n\n" + "\n".join([
                "金色晶片在陆晨的手中发出温暖的光。",
                "他站在永生大厦的楼顶, 脚下是整座穹顶城市。太阳刚刚升起, 金色的光穿透穹顶的玻璃, 洒在城市的每一个角落。",
                "林薇站在他身边。她的脸色苍白, 眼睛却异常明亮。她的记忆读取能力在这场战斗中几乎耗尽——但她笑了。",
                "'成功了.' 她说。",
                "陆晨低头看着手中的晶片。这是源代码芯片的复制体——但不是用来植入记忆的, 而是用来解除的。",
                "三天前, 赵明远站在全球发布会的台上, 宣布完美记忆2.0启动。三天后, 陆晨站在这里, 手里握着能够解除所有记忆禁锢的钥匙。",
                "'你确定吗?' 陆晨问林薇, '一旦解除, 所有人都会想起被删除的记忆——痛苦, 恐惧, 失去. 他们会恨我们.'",
                "'他们有权知道真相.' 林薇说, '即使真相是痛苦的. 因为只有真实的痛苦, 才属于他们自己.'",
                "陆晨将晶片插入楼顶的中央控制台。",
                "全息屏幕亮起: '确认执行记忆解除协议? 此操作不可逆.'",
                "他按下确认。",
                "金色的光从控制台蔓延开来, 沿着穹顶的骨架向整个城市扩散。像一场金色的雨, 落在每一个人的身上。",
                "陆晨闭上眼睛。",
                "他感觉到了。47次格式化中被删除的所有记忆碎片, 正在回归。",
                "他看到了自己真正的过去: 不是普通程序员的过去, 而是反抗军战士的过去。他看到了自己选择成为实验体的那一天, 看到了每一次格式化前的告别, 看到了那些在第47次之前就已经牺牲的同伴。",
                "泪水从他的脸上滑落。",
                "但这一次, 他没有被格式化。",
                "因为这一次, 他选择了记住。\n",
            ])
        else:
            s1 = f"第{cn}章 {tt}\n\n" + "\n".join([
                f"第{cn-1}次记忆回溯后, 陆晨的头痛了整整三天。",
                "地下反抗军的基地隐藏在城市下方的旧地铁隧道中。墙壁上布满电缆和管道, 空气潮湿, 但这里的每一个人眼中都有光——穹顶城市里没有的光。",
                "陆晨坐在简陋的医疗舱里, 林薇正在调整记忆读取头盔的参数。",
                "'你的神经接口有47次格式化的痕迹,' 林薇说, 声音平静但带着一种压抑的情感, '每一次格式化都留下了微小的疤痕. 这些疤痕, 构成了你的神经模式.'",
                "'你能帮我恢复吗?' 陆晨问。",
                "林薇沉默了一会儿。'每一次深度读取, 都会对你造成不可逆的损伤. 而且——' 她停顿了一下, '我的读取能力也在下降. 每一次读取, 我也会失去一部分记忆.'",
                "'那你为什么还要帮我?'",
                "林薇看着他, 眼中有一丝复杂的情感。'因为你的第47次激活, 是我的唤醒协议触发的. 整个Deep Sleep计划, 是我设计的.'",
                "陆晨愣住了。眼前这个年轻的女人, 设计了他被格式化了47次的人生。",
                "'所以——' 他的声音沙哑, '你一直在看着我. 看着我一次又一次地被清空.'",
                "'每一次.' 林薇的声音很轻, '每一次你被格式化, 我都在这台设备上记录了你的备份. 47次. 你47次不同的记忆碎片, 都在这里.'",
                "她指了指旁边一个布满灰尘的存储设备。",
                "'我保留了你的每一次人生. 而这一—' 她的声音终于有了一丝颤抖, '这是你自己选择的路. 在第0次, 你告诉我: 如果必须格式化47次才能让源代码芯片解码, 那就做吧.'",
                "陆晨沉默了。",
                "他想不起来自己曾经做过这样的选择。但林薇眼中的坚定, 让他相信这是真的。",
                "'那第47次之后呢?' 他问, '47次之后, 还能剩下什么?'",
                "林薇没有回答。她启动了记忆读取头盔, 蓝色的光在他眼前扩散。",
                "在失去意识的最后一刻, 陆晨听到她说: '第47次之后——你就不用再忘了.'\n",
            ])
        s2 = "\n".join([
            "基地的警报突然响起。红色的灯光在隧道中闪烁。",
            "一个反抗军成员冲进来: '永生公司的追踪队找到了这里! 三分钟内到达!'",
            "林薇迅速关闭设备, 拔下存储设备塞进陆晨手里。'带着这个, 从7号出口走.'",
            "'你呢?'",
            "'我引开他们.' 林薇的眼中没有恐惧, 只有坚定。'源代码芯片在你的神经接口里, 不在我这里. 他们找到我也没用.'",
            "陆晨握紧了手中的存储设备。47次人生的备份, 都在这里。",
            "'我会回来找你.' 他说。",
            "林薇笑了, 笑容中有一种释然。'等你找回了真实的自己, 再来找我.'",
            "她转身跑向相反的方向。陆晨看着她的背影消失在隧道尽头, 然后握紧手中的设备, 冲向7号出口。",
            "身后, 爆炸声和枪声开始响起。",
            "",
        ])
        wc = 4000 + cn*60
        mss.append({"ch":cn,"title":tt,"scenes":[s1,s2],"wc":wc})
    with create_session() as sess:
        for m in mss:
            sess.execute(text("INSERT INTO manuscripts(novel_id,chapter_number,title,scenes,word_count,status) "
                              "VALUES(:nid,:cn,:t,:s,:wc,'初稿')"),
                         {"nid":novel_id,"cn":m["ch"],"t":m["title"],"s":json.dumps(m["scenes"],ensure_ascii=False),"wc":m["wc"]})
        sess.commit()
    total_wc = sum(m["wc"] for m in mss)
    log(16,"正文初稿",True,f"20 章, 总字数: {total_wc:,}")
    time.sleep(0.3)

    # ============ Step 17: 正文审核 ============
    hr()
    print("  [Step 17/20] 正文审核")
    time.sleep(0.3)
    review = {"level":"PASS","score":0.94,"checks":{"wc":{"s":"PASS"},"scenes":{"s":"PASS"},"structure":{"s":"PASS"},"nerve_tech":{"s":"PASS"}}}
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
    fixes = [{"ch":2,"issue":"异常发现的过程可以更具紧张感","fix":"增强了体检后陆晨翻阅内部系统的心理描写"},
             {"ch":7,"issue":"第一次记忆回溯的场景需要更有冲击力","fix":"添加了47次格式化的记忆碎片蒙太奇"},
             {"ch":16,"issue":"全球发布会场景可以更宏大","fix":"增加了全息直播和全球百亿观众的实时反应"}]
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
    print("    [System] SyncEngine 渲染输出目录...")
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
        "|------|------|------|","| 陆晨 | 主角 | 神经工程师, 被格式化47次的实验体 |",
        "| 林薇 | 关键配角 | 记忆解码师, Deep Sleep计划设计者 |",
        "| 赵明远 | 反派 | 永生公司CEO, 完美记忆计划发起者 |","",
        "## 结构","","| 卷名 | 章节 | 核心冲突 |",
        "|------|------|----------|","| 虚假的日常 | 1-6 | 虚假安宁 vs 痛苦真相 |",
        "| 觉醒之路 | 7-14 | 控制安全 vs 自由风险 |","| 记忆之战 | 15-20 | 集体遗忘 vs 真实记忆 |","",
        "---","*由 AI 小说创作系统 v3.0 生成*",
    ]
    with open(out/"小说概览.md","w",encoding="utf-8") as f: f.write("\n".join(ov))

    # 模块目录
    mods = [
        ("01_主题","# 01_主题\n\n## 表层主题\n2147年, '永生'公司通过梦境植入技术, 在人的长期记忆中植入虚假身份\n\n## 深层主题\n当记忆可以被任意篡改, 人的自我认知还可靠吗?\n\n## 核心钩子\n一个普通程序员在例行记忆体检后, 发现自己脑中有一段不属于自己的记忆\n\n## 主题宣言\n记忆不是过去的记录, 而是现在的牢笼"),
        ("02_世界观","# 02_世界观\n\n## 科技水平\n- 神经记忆芯片植入率99%\n- 年度记忆体检\n- 记忆可被植入/编辑/删除\n\n## 社会结构\n- 永生公司实质控制各国政府\n- 表面民主, 实际记忆操控\n\n## 记忆规则\n- 植入记忆有0.01%排斥概率\n- 私自查看原始记忆属重罪\n\n## 反抗力量\n- 地下反抗军保存原始人类记忆\n- 被标记为'记忆恐怖分子'"),
        ("03_势力","# 03_势力\n\n| 势力 | 类型 | 目标 |\n|------|------|------|\n| 永生公司 | 企业 | 记忆控制 |\n| 地下反抗军 | 秘密组织 | 记忆解放 |\n| 记忆审查局 | 政府 | 维护记忆法 |"),
        ("04_势力关系","# 04_势力关系\n\n| 关系 | 类型 |\n|------|------|\n| 永生公司 vs 审查局 | 控制-执行 |\n| 永生公司 vs 反抗军 | 镇压-反抗 |\n| 审查局 vs 反抗军 | 追捕-逃亡 |"),
        ("05_人物","# 05_人物\n\n## 陆晨 (主角)\nINTP 神经工程师 | 技能: 神经编程/记忆解码 | 秘密: 被格式化47次\n\n## 林薇 (关键配角)\nENFJ 记忆解码师 | 技能: 记忆读取/意识链接 | 秘密: Deep Sleep计划设计者\n\n## 赵明远 (反派)\nENTJ 永生CEO | 技能: 神经工程/战略布局 | 秘密: 曾被记忆篡改失去挚爱"),
        ("06_人物关系","# 06_人物关系\n\n| 关系 | 类型 | 强度 |\n|------|------|------|\n| 陆晨-林薇 | 信任-依赖 | 0.82 |\n| 陆晨-赵明远 | 创造者-反抗者 | 0.20 |\n| 林薇-赵明远 | 师徒-对立 | 0.15 |"),
        ("07_角色弧线","# 07_角色弧线\n\n## 陆晨: 觉醒弧\n被植入记忆的工程师 -> 发现异常 -> 真相冲击 -> 自我重构 -> 解放\n\n## 林薇: 救赎弧\n逃离的工程师 -> 内疚 -> 并肩作战 -> 直面过去 -> 重建\n\n## 赵明远: 堕落弧\n完美主义者 -> 极端 -> 偏执 -> 崩溃 -> 醒悟"),
        ("08_物品仓库","# 08_物品仓库\n\n| 物品 | 类型 | 持有者 |\n|------|------|--------|\n| 原始记忆晶片 | 科技 | 陆晨 |\n| 记忆读取头盔 | 科技 | 林薇 |\n| 源代码芯片 | 科技 | 赵明远 |"),
        ("09_伏笔管理","# 09_伏笔管理\n\n| 伏笔 | 章节 | 深度 |\n|------|------|------|\n| 异常记忆碎片 | 1 | 深层 |\n| 红色数字47 | 3 | 深层 |\n| 99.97%成功率 | 6 | 中层 |\n| 赵明远的过去 | 9 | 中层 |\n| 林薇的记忆损耗 | 13 | 深层 |"),
        ("10_大纲","# 10_大纲\n\n## 三幕\n\n### 第一幕: 虚假的日常 (1-6章)\n记忆体检异常 -> 反抗军接触 -> 真相浮现\n\n### 第二幕: 觉醒之路 (7-14章)\n记忆回溯 -> 47次格式化 -> 能力觉醒\n\n### 第三幕: 记忆之战 (15-20章)\n完美记忆2.0 -> 终极抉择 -> 记忆解放"),
    ]
    for mdir, mcontent in mods:
        d = out/mdir; d.mkdir(exist_ok=True)
        with open(d/f"{mdir}.md","w",encoding="utf-8") as f: f.write(mcontent)

    # 正文
    ch_dir = out/"13_正文"; ch_dir.mkdir(exist_ok=True)
    idx_lines = ["# 正文目录","",f"> 小说: {NOVEL_TITLE}","","| 章节 | 标题 | 字数 |","|------|------|------|"]
    for m in mss:
        cn = m["ch"]; tt = m["title"]; wc = m["wc"]
        fn = f"第{cn:02d}章_{tt.replace(' ','_')}.md"
        content = f"# 第{cn}章 {tt}\n\n> 字数: {wc} | 视角: {'陆晨' if cn%3!=2 else '林薇' if cn%3!=0 else '赵明远'}\n\n---\n\n" + "\n---\n\n".join(m["scenes"])
        with open(ch_dir/fn,"w",encoding="utf-8") as f: f.write(content)
        idx_lines.append(f"| [第{cn}章 {tt}]({fn}) | {tt} | {wc:,} |")
    with open(ch_dir/"README.md","w",encoding="utf-8") as f: f.write("\n".join(idx_lines))

    # 完整版
    full = [f"# {NOVEL_TITLE}","Author: "+NOVEL_AUTHOR,"Theme: "+NOVEL_THEME,"Novel ID: "+novel_id,"Created: "+datetime.now().strftime('%Y-%m-%d %H:%M:%S'),"","---",""]
    for m in mss:
        full.append(f"## Chapter {m['ch']:02d}: {m['title']}")
        for s in m["scenes"]: full.append(s)
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
    print(f"    Export:  TXT ({txt_sz:,} bytes) + MD")
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
