# -*- coding: utf-8 -*-
"""综合修复脚本：修复数据库中所有空壳数据和扩展大纲"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from datetime import datetime, timezone
from sqlalchemy import text
from src.storage.database.engine import get_engine, init_schema, get_session

NOVEL_ID = "NOV-001"
NOW = datetime.now(timezone.utc).isoformat()


def step_header(msg):
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}")


def count_table(session, table):
    return session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar() or 0


# ─────────────────────────────────────────────────────────────
# 1. 扩展大纲到1500章
# ─────────────────────────────────────────────────────────────
def fix_outlines(session):
    step_header("步骤1: 扩展大纲到1500章")

    acts = [
        {
            "act": 1,
            "title": "崛起篇",
            "time_range": "2010-2015",
            "chapters": 500,
            "summary": "林默穿越回2010年，凭借未来记忆从零开始积累资本。建立林氏资本，组建核心团队，布局新能源与科技投资，在2015年杠杆牛市中完成原始积累。",
            "key_events": [
                "穿越觉醒，确认未来记忆",
                "第一桶金：利用股市信息差",
                "建立林氏资本",
                "招募陈锋、苏晴、赵明轩",
                "布局新能源产业链",
                "创立星河科技",
                "应对张铁军的打压",
                "2015年杠杆牛市暴利",
                "股灾前精准逃顶",
                "崛起篇巅峰：百亿资产"
            ],
        },
        {
            "act": 2,
            "title": "博弈篇",
            "time_range": "2015-2022",
            "chapters": 600,
            "summary": "林默将目光投向国际金融市场，做空日元、瑞郎风暴中获利。然而赵明轩的背叛让林氏资本遭受重创，王志远联合国际势力步步紧逼。林默在绝境中反击，逐一击败对手。",
            "key_events": [
                "进军国际金融市场",
                "做空日元战役",
                "瑞郎风暴惊天获利",
                "全球投资布局",
                "赵明轩暗中动摇",
                "赵明轩背叛，窃取核心机密",
                "林氏资本遭受重创",
                "绝地反击计划启动",
                "王志远势力覆灭",
                "新的国际敌人浮现",
                "全球金融战争",
                "博弈篇巅峰：击败国际做空联盟"
            ],
        },
        {
            "act": 3,
            "title": "巅峰篇",
            "time_range": "2022-2035",
            "chapters": 400,
            "summary": "AI时代来临，林默提前布局英伟达和AI芯片。沈婉清作为间谍潜伏，詹姆斯·洛克操控的黑石集团成为终极对手。林默在AI赛道、国际博弈中走向巅峰，最终完成家国传承。",
            "key_events": [
                "AI黎明：提前布局AI赛道",
                "英伟达暴涨获利万亿",
                "创立AI创新联盟",
                "沈婉清身份暴露",
                "黑石集团全面对抗",
                "国际博弈白热化",
                "家国情怀：科技报国",
                "幕后掌控全球金融格局",
                "传承之路：培养下一代",
                "最终决战：沉默的资本猎手"
            ],
        },
    ]

    causal_chain = [
        {"from": "穿越觉醒", "to": "第一桶金", "type": "直接因果", "weight": 1.0},
        {"from": "第一桶金", "to": "建立林氏资本", "type": "直接因果", "weight": 0.95},
        {"from": "建立林氏资本", "to": "招募核心团队", "type": "直接因果", "weight": 0.9},
        {"from": "招募核心团队", "to": "布局新能源", "type": "直接因果", "weight": 0.85},
        {"from": "布局新能源", "to": "创立星河科技", "type": "直接因果", "weight": 0.9},
        {"from": "创立星河科技", "to": "张铁军打压", "type": "间接因果", "weight": 0.7},
        {"from": "张铁军打压", "to": "击败张铁军", "type": "转折", "weight": 0.8},
        {"from": "击败张铁军", "to": "牛市暴利", "type": "铺垫", "weight": 0.75},
        {"from": "牛市暴利", "to": "股灾逃顶", "type": "直接因果", "weight": 0.95},
        {"from": "股灾逃顶", "to": "进军国际", "type": "直接因果", "weight": 0.9},
        {"from": "进军国际", "to": "做空日元", "type": "直接因果", "weight": 0.85},
        {"from": "做空日元", "to": "瑞郎风暴", "type": "铺垫", "weight": 0.8},
        {"from": "瑞郎风暴", "to": "全球布局", "type": "直接因果", "weight": 0.85},
        {"from": "全球布局", "to": "赵明轩动摇", "type": "铺垫", "weight": 0.7},
        {"from": "赵明轩动摇", "to": "赵明轩背叛", "type": "转折", "weight": 0.95},
        {"from": "赵明轩背叛", "to": "林氏重创", "type": "直接因果", "weight": 0.9},
        {"from": "林氏重创", "to": "绝地反击", "type": "转折", "weight": 0.95},
        {"from": "绝地反击", "to": "王志远覆灭", "type": "直接因果", "weight": 0.85},
        {"from": "王志远覆灭", "to": "新敌人浮现", "type": "伏笔", "weight": 0.8},
        {"from": "新敌人浮现", "to": "金融战争", "type": "直接因果", "weight": 0.9},
        {"from": "金融战争", "to": "AI黎明", "type": "铺垫", "weight": 0.85},
        {"from": "AI黎明", "to": "英伟达暴涨", "type": "直接因果", "weight": 0.95},
        {"from": "英伟达暴涨", "to": "AI创新联盟", "type": "直接因果", "weight": 0.9},
        {"from": "AI创新联盟", "to": "沈婉清暴露", "type": "转折", "weight": 0.85},
        {"from": "沈婉清暴露", "to": "黑石对抗", "type": "直接因果", "weight": 0.9},
        {"from": "黑石对抗", "to": "国际博弈", "type": "直接因果", "weight": 0.85},
        {"from": "国际博弈", "to": "家国传承", "type": "铺垫", "weight": 0.8},
        {"from": "家国传承", "to": "最终决战", "type": "直接因果", "weight": 0.95},
    ]

    rhythm_map = [
        {"chapter": 1, "label": "开篇-穿越觉醒", "intensity": 0.7, "type": "起"},
        {"chapter": 100, "label": "第一幕-资本积累完成", "intensity": 0.6, "type": "承"},
        {"chapter": 200, "label": "第一幕-林氏资本建立", "intensity": 0.75, "type": "承"},
        {"chapter": 300, "label": "第一幕-团队成型", "intensity": 0.65, "type": "承"},
        {"chapter": 400, "label": "第一幕-牛市巅峰", "intensity": 0.9, "type": "转"},
        {"chapter": 500, "label": "第一幕-股灾逃顶/崛起巅峰", "intensity": 0.95, "type": "转"},
        {"chapter": 600, "label": "第二幕-做空日元", "intensity": 0.85, "type": "起"},
        {"chapter": 700, "label": "第二幕-全球布局", "intensity": 0.7, "type": "承"},
        {"chapter": 800, "label": "第二幕-赵明轩背叛", "intensity": 0.95, "type": "转"},
        {"chapter": 900, "label": "第二幕-绝地反击", "intensity": 0.9, "type": "转"},
        {"chapter": 1000, "label": "第二幕-王志远覆灭", "intensity": 0.85, "type": "合"},
        {"chapter": 1100, "label": "第二幕/第三幕-博弈巅峰/AI黎明", "intensity": 0.8, "type": "合"},
        {"chapter": 1200, "label": "第三幕-英伟达暴涨", "intensity": 0.9, "type": "起"},
        {"chapter": 1300, "label": "第三幕-国际博弈", "intensity": 0.85, "type": "承"},
        {"chapter": 1400, "label": "第三幕-家国传承", "intensity": 0.8, "type": "转"},
        {"chapter": 1500, "label": "第三幕-最终决战/大结局", "intensity": 1.0, "type": "合"},
    ]

    session.execute(
        text("""
            INSERT OR REPLACE INTO outlines
            (novel_id, acts, causal_chain, rhythm_map)
            VALUES (:novel_id, :acts, :causal_chain, :rhythm_map)
        """),
        {
            "novel_id": NOVEL_ID,
            "acts": json.dumps(acts, ensure_ascii=False),
            "causal_chain": json.dumps(causal_chain, ensure_ascii=False),
            "rhythm_map": json.dumps(rhythm_map, ensure_ascii=False),
        },
    )
    session.flush()
    cnt = count_table(session, "outlines")
    print(f"  -> 大纲已更新: {cnt} 条记录")
    print(f"  -> 三幕: 崛起篇(500章) + 博弈篇(600章) + 巅峰篇(400章) = 1500章")
    print(f"  -> 因果链: {len(causal_chain)} 条")
    print(f"  -> 节奏标记: {len(rhythm_map)} 个节点")


# ─────────────────────────────────────────────────────────────
# 2. 重新分卷（30卷）
# ─────────────────────────────────────────────────────────────
def fix_volumes(session):
    step_header("步骤2: 重新分卷（30卷）")

    # 删除旧分卷
    session.execute(text("DELETE FROM volume_chapters WHERE volume_id IN (SELECT volume_id FROM volumes WHERE novel_id = :nid)"), {"nid": NOVEL_ID})
    session.execute(text("DELETE FROM volumes WHERE novel_id = :nid"), {"nid": NOVEL_ID})
    session.flush()

    volumes_data = [
        # ── 崛起篇（第1-500章）分10卷 ──
        {"id": "VOL-001", "name": "隐形起步", "chapter_range": [1, 50],
         "boundary_gravity": [{"source": "穿越觉醒的震撼感", "type": "悬念钩子"}],
         "pacing": "slow_build", "major_conflict": "林默适应穿越身份，利用未来记忆获取第一桶金",
         "character_focus": ["林默"], "themes": ["重生", "适应"],
         "cliffhanger": "第一笔投资收益到账，林默意识到未来记忆的真正价值",
         "volume_rhythm_curve": [{"phase": "铺垫", "intensity": 0.5}, {"phase": "觉醒", "intensity": 0.7}],
         "volume_rhythm_evaluation": "开篇节奏稳健，以悬念和适应为主，逐步建立读者代入感"},

        {"id": "VOL-002", "name": "资本积累", "chapter_range": [51, 100],
         "boundary_gravity": [{"source": "第一桶金完成，资本原始积累的关键转折", "type": "里程碑"}],
         "pacing": "medium", "major_conflict": "在股市中利用信息差快速积累，同时避免引起注意",
         "character_focus": ["林默"], "themes": ["资本", "隐忍"],
         "cliffhanger": "林默的异常收益引起监管部门关注",
         "volume_rhythm_curve": [{"phase": "加速", "intensity": 0.6}, {"phase": "紧张", "intensity": 0.75}],
         "volume_rhythm_evaluation": "节奏加快，资本积累的爽感与风险并存"},

        {"id": "VOL-003", "name": "团队建设", "chapter_range": [101, 150],
         "boundary_gravity": [{"source": "从个人作战到团队化运营的转变", "type": "结构转折"}],
         "pacing": "medium", "major_conflict": "招募陈锋、苏晴、赵明轩，建立核心团队",
         "character_focus": ["林默", "陈锋", "苏晴", "赵明轩"], "themes": ["团队", "信任"],
         "cliffhanger": "赵明轩展现出超出预期的能力，但隐约有不寻常的野心",
         "volume_rhythm_curve": [{"phase": "组建", "intensity": 0.6}, {"phase": "暗涌", "intensity": 0.7}],
         "volume_rhythm_evaluation": "角色塑造为主，为后续背叛埋下伏笔"},

        {"id": "VOL-004", "name": "投资布局", "chapter_range": [151, 200],
         "boundary_gravity": [{"source": "从短线投机到长线投资的战略升级", "type": "战略转折"}],
         "pacing": "medium_fast", "major_conflict": "布局新能源和科技产业链，与王志远产生初步冲突",
         "character_focus": ["林默", "王志远"], "themes": ["投资", "竞争"],
         "cliffhanger": "王志远察觉到林默的投资布局，开始暗中调查",
         "volume_rhythm_curve": [{"phase": "布局", "intensity": 0.65}, {"phase": "冲突", "intensity": 0.8}],
         "volume_rhythm_evaluation": "投资线与对抗线交织，张力逐步提升"},

        {"id": "VOL-005", "name": "新能源崛起", "chapter_range": [201, 250],
         "boundary_gravity": [{"source": "新能源产业爆发，林默投资回报丰厚", "type": "里程碑"}],
         "pacing": "fast", "major_conflict": "新能源赛道竞争白热化，张铁军作为地方势力阻挠",
         "character_focus": ["林默", "张铁军"], "themes": ["产业", "对抗"],
         "cliffhanger": "张铁军动用灰色手段打压星河科技",
         "volume_rhythm_curve": [{"phase": "爆发", "intensity": 0.8}, {"phase": "危机", "intensity": 0.85}],
         "volume_rhythm_evaluation": "高潮节奏，爽感与危机感并存"},

        {"id": "VOL-006", "name": "星河科技", "chapter_range": [251, 300],
         "boundary_gravity": [{"source": "星河科技正式成立，从投资者到企业家的转变", "type": "里程碑"}],
         "pacing": "medium", "major_conflict": "星河科技面临技术突破和市场竞争的双重挑战",
         "character_focus": ["林默", "苏晴"], "themes": ["创新", "管理"],
         "cliffhanger": "星河科技获得关键专利，但竞争对手开始抄袭",
         "volume_rhythm_curve": [{"phase": "建设", "intensity": 0.6}, {"phase": "突破", "intensity": 0.75}],
         "volume_rhythm_evaluation": "产业线深入，展现林默的企业家能力"},

        {"id": "VOL-007", "name": "权力暗涌", "chapter_range": [301, 350],
         "boundary_gravity": [{"source": "多方势力暗中角力，权力格局开始变化", "type": "暗流"}],
         "pacing": "slow_build", "major_conflict": "张铁军联合王志远对林默施压，赵明轩暗中接触外部势力",
         "character_focus": ["林默", "张铁军", "王志远", "赵明轩"], "themes": ["权力", "阴谋"],
         "cliffhanger": "赵明轩秘密会见一个神秘人物",
         "volume_rhythm_curve": [{"phase": "暗涌", "intensity": 0.55}, {"phase": "危机", "intensity": 0.8}],
         "volume_rhythm_evaluation": "暗流涌动，多条伏笔同时推进"},

        {"id": "VOL-008", "name": "牛市风云", "chapter_range": [351, 400],
         "boundary_gravity": [{"source": "2015年杠杆牛市全面爆发", "type": "时代背景"}],
         "pacing": "fast", "major_conflict": "在牛市中疯狂获利，同时应对各方势力的觊觎",
         "character_focus": ["林默", "苏晴", "赵明轩"], "themes": ["贪婪", "机遇"],
         "cliffhanger": "牛市疯狂到极点，林默开始秘密减仓",
         "volume_rhythm_curve": [{"phase": "疯狂", "intensity": 0.9}, {"phase": "预警", "intensity": 0.85}],
         "volume_rhythm_evaluation": "高潮节奏，牛市狂欢与危机预警并行"},

        {"id": "VOL-009", "name": "股灾逃顶", "chapter_range": [401, 450],
         "boundary_gravity": [{"source": "2015年股灾，千股跌停的历史性时刻", "type": "灾难转折"}],
         "pacing": "fast", "major_conflict": "股灾中精准逃顶，同时救助被套的合作伙伴",
         "character_focus": ["林默", "陈锋"], "themes": ["危机", "决策"],
         "cliffhanger": "逃顶成功后，林默发现有人在背后追踪他的交易记录",
         "volume_rhythm_curve": [{"phase": "崩塌", "intensity": 0.95}, {"phase": "逃生", "intensity": 0.9}],
         "volume_rhythm_evaluation": "灾难级高潮，紧张刺激"},

        {"id": "VOL-010", "name": "崛起巅峰", "chapter_range": [451, 500],
         "boundary_gravity": [{"source": "第一幕终章，百亿资产达成", "type": "里程碑"}],
         "pacing": "medium", "major_conflict": "巩固国内地位，为进军国际做准备，击败张铁军",
         "character_focus": ["林默", "张铁军", "陈锋"], "themes": ["巅峰", "转折"],
         "cliffhanger": "张铁军倒台，但林默收到来自华尔街的神秘邀请",
         "volume_rhythm_curve": [{"phase": "清算", "intensity": 0.8}, {"phase": "展望", "intensity": 0.7}],
         "volume_rhythm_evaluation": "第一幕完美收官，承上启下"},

        # ── 博弈篇（第501-1100章）分12卷 ──
        {"id": "VOL-011", "name": "国际初探", "chapter_range": [501, 550],
         "boundary_gravity": [{"source": "从国内到国际的跨越", "type": "格局转变"}],
         "pacing": "medium", "major_conflict": "林默首次进入国际金融市场，水土不服",
         "character_focus": ["林默", "苏晴"], "themes": ["国际化", "学习"],
         "cliffhanger": "林默发现国际市场的规则与国内截然不同，遭遇第一次亏损",
         "volume_rhythm_curve": [{"phase": "探索", "intensity": 0.6}, {"phase": "挫折", "intensity": 0.7}],
         "volume_rhythm_evaluation": "新篇章开启，节奏平稳，建立国际线"},

        {"id": "VOL-012", "name": "做空日元", "chapter_range": [551, 600],
         "boundary_gravity": [{"source": "做空日元战役，国际市场首战告捷", "type": "战役转折"}],
         "pacing": "fast", "major_conflict": "利用未来记忆做空日元，与日本金融监管机构博弈",
         "character_focus": ["林默"], "themes": ["金融战", "胆识"],
         "cliffhanger": "做空成功，但引起了国际金融大鳄钱浩天的注意",
         "volume_rhythm_curve": [{"phase": "布局", "intensity": 0.7}, {"phase": "爆发", "intensity": 0.9}],
         "volume_rhythm_evaluation": "国际首战，节奏紧凑，引入新反派"},

        {"id": "VOL-013", "name": "瑞郎风暴", "chapter_range": [601, 650],
         "boundary_gravity": [{"source": "瑞士央行取消欧元兑瑞郎汇率下限，市场崩盘", "type": "历史事件"}],
         "pacing": "fast", "major_conflict": "在瑞郎风暴中获利，同时面临资金链断裂的风险",
         "character_focus": ["林默", "陈锋"], "themes": ["风险", "机遇"],
         "cliffhanger": "瑞郎风暴获利惊人，但瑞士银行开始调查林默的资金来源",
         "volume_rhythm_curve": [{"phase": "风暴", "intensity": 0.95}, {"phase": "余波", "intensity": 0.75}],
         "volume_rhythm_evaluation": "历史级金融事件，紧张刺激"},

        {"id": "VOL-014", "name": "全球布局", "chapter_range": [651, 700],
         "boundary_gravity": [{"source": "从单点突破到全球投资网络", "type": "战略升级"}],
         "pacing": "medium", "major_conflict": "在全球多个市场同时布局，管理难度剧增",
         "character_focus": ["林默", "苏晴", "李雪"], "themes": ["全球化", "管理"],
         "cliffhanger": "李雪发现有人在暗中监视林氏资本的所有海外账户",
         "volume_rhythm_curve": [{"phase": "扩张", "intensity": 0.65}, {"phase": "暗流", "intensity": 0.75}],
         "volume_rhythm_evaluation": "战略布局卷，节奏适中，引入情报线"},

        {"id": "VOL-015", "name": "暗流涌动", "chapter_range": [701, 750],
         "boundary_gravity": [{"source": "多方势力暗中集结，风暴前夕", "type": "暗流"}],
         "pacing": "slow_build", "major_conflict": "钱浩天开始布局针对林默的做空计划，赵明轩动摇加剧",
         "character_focus": ["赵明轩", "钱浩天"], "themes": ["阴谋", "动摇"],
         "cliffhanger": "赵明轩收到钱浩天的秘密联络，面临人生最大抉择",
         "volume_rhythm_curve": [{"phase": "暗涌", "intensity": 0.5}, {"phase": "风暴前", "intensity": 0.8}],
         "volume_rhythm_evaluation": "暴风雨前的宁静，伏笔密集"},

        {"id": "VOL-016", "name": "赵明轩动摇", "chapter_range": [751, 800],
         "boundary_gravity": [{"source": "核心成员的忠诚危机", "type": "人物转折"}],
         "pacing": "medium", "major_conflict": "赵明轩在金钱诱惑和忠诚之间挣扎，开始向钱浩天泄露信息",
         "character_focus": ["赵明轩", "林默"], "themes": ["忠诚", "背叛"],
         "cliffhanger": "赵明轩复制了林氏资本的核心加密文件到U盘",
         "volume_rhythm_curve": [{"phase": "挣扎", "intensity": 0.6}, {"phase": "堕落", "intensity": 0.85}],
         "volume_rhythm_evaluation": "人物心理刻画深刻，背叛前的挣扎"},

        {"id": "VOL-017", "name": "背叛之痛", "chapter_range": [801, 850],
         "boundary_gravity": [{"source": "赵明轩正式背叛，林氏资本遭受重创", "type": "灾难转折"}],
         "pacing": "fast", "major_conflict": "赵明轩将机密交给钱浩天，林氏资本在国际市场遭遇做空攻击",
         "character_focus": ["林默", "赵明轩", "钱浩天"], "themes": ["背叛", "痛苦"],
         "cliffhanger": "林默发现背叛者竟是赵明轩，林氏资本单日亏损超过百亿",
         "volume_rhythm_curve": [{"phase": "背叛", "intensity": 0.95}, {"phase": "崩溃", "intensity": 1.0}],
         "volume_rhythm_evaluation": "全书最大情感冲击点之一"},

        {"id": "VOL-018", "name": "绝地反击", "chapter_range": [851, 900],
         "boundary_gravity": [{"source": "从谷底反弹的转折点", "type": "逆袭转折"}],
         "pacing": "fast", "major_conflict": "林默利用未来记忆中尚未发生的事件策划反击",
         "character_focus": ["林默", "陈锋", "苏晴"], "themes": ["反击", "团结"],
         "cliffhanger": "反击计划第一步成功，林默开始反向做空钱浩天",
         "volume_rhythm_curve": [{"phase": "低谷", "intensity": 0.6}, {"phase": "反击", "intensity": 0.9}],
         "volume_rhythm_evaluation": "从谷底到反击，节奏紧凑有力"},

        {"id": "VOL-019", "name": "王志远覆灭", "chapter_range": [901, 950],
         "boundary_gravity": [{"source": "第一层反派王志远的彻底失败", "type": "反派终结"}],
         "pacing": "fast", "major_conflict": "王志远的灰色交易被曝光，商业帝国崩塌",
         "character_focus": ["王志远", "林默"], "themes": ["正义", "覆灭"],
         "cliffhanger": "王志远入狱前透露背后还有更大的势力",
         "volume_rhythm_curve": [{"phase": "追击", "intensity": 0.85}, {"phase": "终结", "intensity": 0.9}],
         "volume_rhythm_evaluation": "反派终结卷，爽感十足"},

        {"id": "VOL-020", "name": "新的敌人", "chapter_range": [951, 1000],
         "boundary_gravity": [{"source": "第二层反派浮现，格局升级", "type": "格局升级"}],
         "pacing": "medium", "major_conflict": "钱浩天的国际做空联盟浮出水面，沈婉清以盟友身份出现",
         "character_focus": ["钱浩天", "沈婉清", "林默"], "themes": ["新敌", "伪装"],
         "cliffhanger": "沈婉清以AI领域科学家的身份主动接触林默",
         "volume_rhythm_curve": [{"phase": "新局", "intensity": 0.65}, {"phase": "悬念", "intensity": 0.8}],
         "volume_rhythm_evaluation": "新角色引入，为第三幕铺垫"},

        {"id": "VOL-021", "name": "金融战争", "chapter_range": [1001, 1050],
         "boundary_gravity": [{"source": "全球级别的金融战争", "type": "战争升级"}],
         "pacing": "fast", "major_conflict": "林默与钱浩天的国际做空联盟正面交锋",
         "character_focus": ["林默", "钱浩天"], "themes": ["金融战", "博弈"],
         "cliffhanger": "金融战争进入白热化，双方都付出巨大代价",
         "volume_rhythm_curve": [{"phase": "交锋", "intensity": 0.85}, {"phase": "高潮", "intensity": 0.95}],
         "volume_rhythm_evaluation": "大规模对抗，节奏紧张"},

        {"id": "VOL-022", "name": "博弈巅峰", "chapter_range": [1051, 1100],
         "boundary_gravity": [{"source": "第二幕终章，博弈篇巅峰对决", "type": "里程碑"}],
         "pacing": "fast", "major_conflict": "击败钱浩天，但发现其背后还有黑石集团",
         "character_focus": ["林默", "钱浩天", "陈锋"], "themes": ["胜利", "伏笔"],
         "cliffhanger": "钱浩天败北前透露：真正的对手是黑石集团的詹姆斯·洛克",
         "volume_rhythm_curve": [{"phase": "决战", "intensity": 0.95}, {"phase": "转折", "intensity": 0.85}],
         "volume_rhythm_evaluation": "第二幕完美收官，终极悬念揭晓"},

        # ── 巅峰篇（第1101-1500章）分8卷 ──
        {"id": "VOL-023", "name": "AI黎明", "chapter_range": [1101, 1150],
         "boundary_gravity": [{"source": "AI时代来临，新的赛道开启", "type": "时代转折"}],
         "pacing": "medium", "major_conflict": "林默提前布局AI赛道，与全球科技巨头竞争",
         "character_focus": ["林默", "苏晴"], "themes": ["AI", "未来"],
         "cliffhanger": "林默秘密收购了大量英伟达股票和AI初创公司",
         "volume_rhythm_curve": [{"phase": "黎明", "intensity": 0.65}, {"phase": "布局", "intensity": 0.75}],
         "volume_rhythm_evaluation": "新赛道开启，节奏稳健"},

        {"id": "VOL-024", "name": "英伟达暴涨", "chapter_range": [1151, 1200],
         "boundary_gravity": [{"source": "英伟达股价暴涨，AI红利爆发", "type": "财富里程碑"}],
         "pacing": "fast", "major_conflict": "AI芯片需求爆发，林默的早期布局获得惊人回报",
         "character_focus": ["林默"], "themes": ["财富", "AI"],
         "cliffhanger": "林默的AI资产价值突破万亿，成为全球AI领域最有影响力的人物之一",
         "volume_rhythm_curve": [{"phase": "爆发", "intensity": 0.9}, {"phase": "巅峰", "intensity": 0.95}],
         "volume_rhythm_evaluation": "爽感爆发，AI红利兑现"},

        {"id": "VOL-025", "name": "AI创新联盟", "chapter_range": [1201, 1250],
         "boundary_gravity": [{"source": "创立AI创新联盟，从个人到生态", "type": "战略升级"}],
         "pacing": "medium", "major_conflict": "联合全球AI企业组建创新联盟，但联盟内有间谍",
         "character_focus": ["林默", "沈婉清"], "themes": ["联盟", "间谍"],
         "cliffhanger": "李雪的情报系统发现联盟内部有泄密行为",
         "volume_rhythm_curve": [{"phase": "建设", "intensity": 0.6}, {"phase": "暗流", "intensity": 0.8}],
         "volume_rhythm_evaluation": "联盟建设与间谍悬念并行"},

        {"id": "VOL-026", "name": "国际博弈", "chapter_range": [1251, 1300],
         "boundary_gravity": [{"source": "国际政治与商业的深度博弈", "type": "格局升级"}],
         "pacing": "fast", "major_conflict": "黑石集团通过政治手段打压林默的AI联盟，沈婉清身份暴露",
         "character_focus": ["林默", "沈婉清", "詹姆斯·洛克"], "themes": ["国际博弈", "真相"],
         "cliffhanger": "沈婉清被确认为黑石集团间谍，但她说出了詹姆斯·洛克的终极计划",
         "volume_rhythm_curve": [{"phase": "博弈", "intensity": 0.85}, {"phase": "暴露", "intensity": 0.95}],
         "volume_rhythm_evaluation": "间谍暴露，高潮迭起"},

        {"id": "VOL-027", "name": "家国情怀", "chapter_range": [1301, 1350],
         "boundary_gravity": [{"source": "从个人财富到家国情怀的升华", "type": "主题升华"}],
         "pacing": "medium", "major_conflict": "面对国际压力，林默选择将AI技术留在国内，科技报国",
         "character_focus": ["林默", "陈锋"], "themes": ["家国", "情怀"],
         "cliffhanger": "詹姆斯·洛克威胁要摧毁林默的一切",
         "volume_rhythm_curve": [{"phase": "抉择", "intensity": 0.7}, {"phase": "升华", "intensity": 0.85}],
         "volume_rhythm_evaluation": "主题升华，情感深度"},

        {"id": "VOL-028", "name": "幕后掌控", "chapter_range": [1351, 1400],
         "boundary_gravity": [{"source": "林默从台前退到幕后，成为真正的掌控者", "type": "角色转变"}],
         "pacing": "medium_fast", "major_conflict": "林默布局击败黑石集团的最终计划",
         "character_focus": ["林默", "詹姆斯·洛克"], "themes": ["掌控", "布局"],
         "cliffhanger": "最终对决的序幕拉开，双方亮出所有底牌",
         "volume_rhythm_curve": [{"phase": "布局", "intensity": 0.7}, {"phase": "对决前", "intensity": 0.9}],
         "volume_rhythm_evaluation": "最终对决前的紧张布局"},

        {"id": "VOL-029", "name": "传承之路", "chapter_range": [1401, 1450],
         "boundary_gravity": [{"source": "从个人传奇到传承的过渡", "type": "主题升华"}],
         "pacing": "medium", "major_conflict": "林默开始培养接班人，同时完成对黑石集团的最后一击",
         "character_focus": ["林默", "苏晴", "陈锋"], "themes": ["传承", "未来"],
         "cliffhanger": "黑石集团的核心秘密即将被揭露",
         "volume_rhythm_curve": [{"phase": "传承", "intensity": 0.65}, {"phase": "决战前", "intensity": 0.85}],
         "volume_rhythm_evaluation": "传承与决战并行，情感深度"},

        {"id": "VOL-030", "name": "沉默的资本猎手", "chapter_range": [1451, 1500],
         "boundary_gravity": [{"source": "全书终章，沉默的资本猎手传奇落幕", "type": "终章"}],
         "pacing": "fast", "major_conflict": "最终决战：林默 vs 詹姆斯·洛克，全球金融格局重塑",
         "character_focus": ["林默", "詹姆斯·洛克"], "themes": ["终章", "传奇"],
         "cliffhanger": "林默站在全球金融之巅，回望25年穿越之路，微笑着看向未来",
         "volume_rhythm_curve": [{"phase": "决战", "intensity": 1.0}, {"phase": "落幕", "intensity": 0.7}],
         "volume_rhythm_evaluation": "全书高潮与落幕，完美收官"},
    ]

    for vol in volumes_data:
        session.execute(
            text("""
                INSERT OR REPLACE INTO volumes
                (novel_id, volume_id, name, chapter_range,
                 boundary_gravity, pacing, major_conflict,
                 character_focus, themes, cliffhanger,
                 volume_rhythm_curve, volume_rhythm_evaluation)
                VALUES (:novel_id, :volume_id, :name, :chapter_range,
                        :boundary_gravity, :pacing, :major_conflict,
                        :character_focus, :themes, :cliffhanger,
                        :volume_rhythm_curve, :volume_rhythm_evaluation)
            """),
            {
                "novel_id": NOVEL_ID,
                "volume_id": vol["id"],
                "name": vol["name"],
                "chapter_range": json.dumps(vol["chapter_range"], ensure_ascii=False),
                "boundary_gravity": json.dumps(vol["boundary_gravity"], ensure_ascii=False),
                "pacing": vol["pacing"],
                "major_conflict": vol["major_conflict"],
                "character_focus": json.dumps(vol["character_focus"], ensure_ascii=False),
                "themes": json.dumps(vol["themes"], ensure_ascii=False),
                "cliffhanger": vol["cliffhanger"],
                "volume_rhythm_curve": json.dumps(vol["volume_rhythm_curve"], ensure_ascii=False),
                "volume_rhythm_evaluation": vol["volume_rhythm_evaluation"],
            },
        )

    session.flush()
    cnt = count_table(session, "volumes")
    print(f"  -> 分卷已重建: {cnt} 卷")
    print(f"  -> 崛起篇: VOL-001~VOL-010 (第1-500章)")
    print(f"  -> 博弈篇: VOL-011~VOL-022 (第501-1100章)")
    print(f"  -> 巅峰篇: VOL-023~VOL-030 (第1101-1500章)")


# ─────────────────────────────────────────────────────────────
# 3. 补全角色弧线
# ─────────────────────────────────────────────────────────────
def fix_character_arcs(session):
    step_header("步骤3: 补全角色弧线")

    session.execute(text("DELETE FROM character_arcs WHERE novel_id = :nid"), {"nid": NOVEL_ID})
    session.flush()

    arcs = [
        {
            "char_id": "CHAR-001",
            "arc_type": "成长弧",
            "start_state": {"status": "穿越后的迷茫青年", "wealth": "负债累累", "power": "无", "mental": "对未来既恐惧又期待"},
            "catalyst_event": "穿越回2010年，发现自己拥有25年未来记忆",
            "change_process": [
                {"phase": "适应期(1-100章)", "description": "接受穿越现实，利用未来记忆获取第一桶金"},
                {"phase": "积累期(101-300章)", "description": "建立林氏资本，组建核心团队，完成原始积累"},
                {"phase": "扩张期(301-500章)", "description": "杠杆牛市暴利，股灾逃顶，百亿资产达成"},
                {"phase": "国际期(501-900章)", "description": "进军国际金融市场，遭遇背叛，绝地反击"},
                {"phase": "巅峰期(901-1500章)", "description": "AI赛道布局，击败国际势力，走向幕后掌控者"},
            ],
            "end_state": {"status": "幕后掌控者", "wealth": "万亿级", "power": "全球金融影响力", "mental": "沉稳从容，心怀家国"},
            "chapter_mapping": [1, 100, 300, 500, 900, 1500],
        },
        {
            "char_id": "CHAR-002",
            "arc_type": "成长弧",
            "start_state": {"status": "退役特种兵，生活困顿", "loyalty": "无归属", "ability": "单兵作战强但缺乏方向"},
            "catalyst_event": "被林默救助并邀请加入团队",
            "change_process": [
                {"phase": "融入期(40-150章)", "description": "从保镖做起，逐渐信任林默"},
                {"phase": "成长期(151-400章)", "description": "成为安保主管，建立安保体系"},
                {"phase": "考验期(401-850章)", "description": "在赵明轩背叛和金融战争中守护林默"},
                {"phase": "蜕变期(851-1500章)", "description": "从保镖成长为林默最信任的伙伴和战略执行者"},
            ],
            "end_state": {"status": "林默最信任的伙伴", "loyalty": "绝对忠诚", "ability": "战略级安保专家"},
            "chapter_mapping": [40, 150, 400, 850, 1500],
        },
        {
            "char_id": "CHAR-003",
            "arc_type": "成长弧",
            "start_state": {"status": "金融专业实习生", "confidence": "低", "ability": "理论基础好但无实战"},
            "catalyst_event": "被林默看中潜力，破格提拔",
            "change_process": [
                {"phase": "学习期(60-200章)", "description": "在林默指导下快速成长，参与投资项目"},
                {"phase": "独立期(201-500章)", "description": "独立负责投资部门，展现卓越才能"},
                {"phase": "领导期(501-1100章)", "description": "成为投资公司CEO，管理千亿级资产"},
                {"phase": "合伙人期(1101-1500章)", "description": "成为林默的核心合伙人，参与AI战略决策"},
            ],
            "end_state": {"status": "投资公司CEO", "confidence": "极高", "ability": "顶级投资家"},
            "chapter_mapping": [60, 200, 500, 1100, 1500],
        },
        {
            "char_id": "CHAR-004",
            "arc_type": "堕落弧",
            "start_state": {"status": "富二代，王氏投资集团继承人", "wealth": "百亿", "arrogance": "极高"},
            "catalyst_event": "林默的崛起威胁到王氏集团的利益",
            "change_process": [
                {"phase": "敌对期(200-400章)", "description": "将林默视为眼中钉，多次打压未果"},
                {"phase": "疯狂期(401-700章)", "description": "不择手段对抗林默，涉足灰色交易"},
                {"phase": "衰落期(701-900章)", "description": "灰色交易被曝光，商业帝国开始崩塌"},
                {"phase": "覆灭期(901-950章)", "description": "王氏集团破产，王志远入狱"},
            ],
            "end_state": {"status": "入狱", "wealth": "归零", "arrogance": "被击碎"},
            "chapter_mapping": [200, 400, 700, 950],
        },
        {
            "char_id": "CHAR-005",
            "arc_type": "堕落弧",
            "start_state": {"status": "林氏资本核心成员", "loyalty": "表面忠诚", "ambition": "隐藏的野心"},
            "catalyst_event": "钱浩天的金钱诱惑和权力承诺",
            "change_process": [
                {"phase": "潜伏期(100-700章)", "description": "作为核心成员工作，但内心野心逐渐膨胀"},
                {"phase": "动摇期(701-800章)", "description": "接触钱浩天，面临忠诚与利益的抉择"},
                {"phase": "背叛期(801-850章)", "description": "窃取机密，背叛林默，加入钱浩天阵营"},
                {"phase": "结局期(851-900章)", "description": "背叛的后果，被林默击败后消失"},
            ],
            "end_state": {"status": "被击败后消失", "loyalty": "已丧失", "ambition": "破灭"},
            "chapter_mapping": [100, 700, 850, 900],
        },
        {
            "char_id": "CHAR-006",
            "arc_type": "成长弧",
            "start_state": {"status": "财经记者", "ability": "调查能力强但缺乏资源", "motivation": "寻找失踪的哥哥"},
            "catalyst_event": "在调查中发现林默的不凡之处，被招募",
            "change_process": [
                {"phase": "记者期(150-300章)", "description": "以记者身份接触林默，被其格局吸引"},
                {"phase": "转型期(301-600章)", "description": "加入林氏资本，建立情报系统"},
                {"phase": "成熟期(601-1100章)", "description": "成为情报部负责人，多次在关键时刻提供情报"},
                {"phase": "揭秘期(1101-1500章)", "description": "揭开哥哥失踪真相与黑石集团的关联"},
            ],
            "end_state": {"status": "情报部负责人", "ability": "顶级情报专家", "motivation": "已找到哥哥线索"},
            "chapter_mapping": [150, 300, 600, 1100, 1500],
        },
    ]

    for arc in arcs:
        session.execute(
            text("""
                INSERT OR REPLACE INTO character_arcs
                (novel_id, char_id, arc_type, start_state, catalyst_event,
                 change_process, end_state, chapter_mapping)
                VALUES (:novel_id, :char_id, :arc_type, :start_state,
                        :catalyst_event, :change_process, :end_state, :chapter_mapping)
            """),
            {
                "novel_id": NOVEL_ID,
                "char_id": arc["char_id"],
                "arc_type": arc["arc_type"],
                "start_state": json.dumps(arc["start_state"], ensure_ascii=False),
                "catalyst_event": arc["catalyst_event"],
                "change_process": json.dumps(arc["change_process"], ensure_ascii=False),
                "end_state": json.dumps(arc["end_state"], ensure_ascii=False),
                "chapter_mapping": json.dumps(arc["chapter_mapping"], ensure_ascii=False),
            },
        )

    session.flush()
    cnt = count_table(session, "character_arcs")
    print(f"  -> 角色弧线已补全: {cnt} 条")
    for arc in arcs:
        print(f"     {arc['char_id']}: {arc['arc_type']}")


# ─────────────────────────────────────────────────────────────
# 4. 补全伏笔追踪（20条）
# ─────────────────────────────────────────────────────────────
def fix_foreshadows(session):
    step_header("步骤4: 补全伏笔追踪（20条）")

    session.execute(text("DELETE FROM foreshadows WHERE novel_id = :nid"), {"nid": NOVEL_ID})
    session.flush()

    foreshadows = [
        {
            "foreshadow_id": "FS-001", "type": "信息伏笔", "status": "已埋设",
            "plant_chapter": 1, "plant_location": "开篇第一章，林默醒来后看到日历",
            "plant_form": "日历显示2010年，与记忆中的2035年形成对比",
            "reveal_chapter_planned": 1500, "reveal_form": "最终章揭示穿越的真正原因和意义",
            "payload": "林默是穿越者，拥有2010-2035年的25年未来记忆",
            "surface": "一个年轻人对日期的困惑", "depth": "深层",
            "related_char": ["林默"], "related_item": [], "related_plot": ["穿越觉醒"],
            "importance": 1.0, "chroma_id": "NOV-001_FS-001",
        },
        {
            "foreshadow_id": "FS-002", "type": "人物伏笔", "status": "已埋设",
            "plant_chapter": 100, "plant_location": "赵明轩在团队会议上的发言",
            "plant_form": "赵明轩对利润分配方案表现出过度关注",
            "reveal_chapter_planned": 800, "reveal_form": "赵明轩的背叛真相揭露",
            "payload": "赵明轩内心深处对权力和财富的渴望远超忠诚",
            "surface": "一个员工对薪酬的正常关心", "depth": "中层",
            "related_char": ["赵明轩"], "related_item": [], "related_plot": ["赵明轩背叛"],
            "importance": 0.8, "chroma_id": "NOV-001_FS-002",
        },
        {
            "foreshadow_id": "FS-003", "type": "关系伏笔", "status": "已埋设",
            "plant_chapter": 50, "plant_location": "陈锋第一次保护林默时的内心独白",
            "plant_form": "陈锋在危机中本能地挡在林默面前",
            "reveal_chapter_planned": 300, "reveal_form": "陈锋正式宣誓效忠，成为安保主管",
            "payload": "陈锋对林默的忠诚源于林默给了他重新开始的信念",
            "surface": "保镖的职业本能", "depth": "浅层",
            "related_char": ["陈锋", "林默"], "related_item": [], "related_plot": ["团队建设"],
            "importance": 0.6, "chroma_id": "NOV-001_FS-003",
        },
        {
            "foreshadow_id": "FS-004", "type": "情感伏笔", "status": "已埋设",
            "plant_chapter": 80, "plant_location": "苏晴加班时偷偷看林默的背影",
            "plant_form": "苏晴在报告中多写了一段对林默决策的分析",
            "reveal_chapter_planned": 1400, "reveal_form": "苏晴在传承之际向林默表达心意",
            "payload": "苏晴对林默的感情从崇拜逐渐发展为深爱",
            "surface": "实习生对老板的崇拜", "depth": "深层",
            "related_char": ["苏晴", "林默"], "related_item": [], "related_plot": ["情感线"],
            "importance": 0.7, "chroma_id": "NOV-001_FS-004",
        },
        {
            "foreshadow_id": "FS-005", "type": "物品伏笔", "status": "已埋设",
            "plant_chapter": 1, "plant_location": "林默穿越时随身携带的物品",
            "plant_form": "怀表背面刻有家族徽章和一行小字",
            "reveal_chapter_planned": 1200, "reveal_form": "怀表内藏的家族秘密与黑石集团有关联",
            "payload": "老式怀表是林默祖父留下的，内藏家族与黑石集团的历史渊源",
            "surface": "一件普通的传家宝", "depth": "深层",
            "related_char": ["林默"], "related_item": ["老式怀表"], "related_plot": ["家族秘密"],
            "importance": 0.9, "chroma_id": "NOV-001_FS-005",
        },
        {
            "foreshadow_id": "FS-006", "type": "信息伏笔", "status": "已埋设",
            "plant_chapter": 150, "plant_location": "李雪调查一起金融案件时的发现",
            "plant_form": "案件卷宗中提到一个失踪的技术人员",
            "reveal_chapter_planned": 900, "reveal_form": "李雪发现失踪者正是自己的哥哥，被黑石集团控制",
            "payload": "李雪的哥哥是一名AI天才，被黑石集团绑架利用",
            "surface": "一起普通的金融案件", "depth": "中层",
            "related_char": ["李雪"], "related_item": ["李雪哥哥的日记"], "related_plot": ["失踪案"],
            "importance": 0.7, "chroma_id": "NOV-001_FS-006",
        },
        {
            "foreshadow_id": "FS-007", "type": "结构伏笔", "status": "已埋设",
            "plant_chapter": 200, "plant_location": "王志远在一次商业晚宴上的私下交易",
            "plant_form": "王志远与一个神秘人物交换了一个黑色公文包",
            "reveal_chapter_planned": 600, "reveal_form": "黑色公文包中是王志远的黑账本，记录所有灰色交易",
            "payload": "王志远通过灰色势力维持商业帝国，涉及洗钱和行贿",
            "surface": "商业晚宴上的正常社交", "depth": "中层",
            "related_char": ["王志远"], "related_item": ["王志远的黑账本"], "related_plot": ["灰色势力"],
            "importance": 0.8, "chroma_id": "NOV-001_FS-007",
        },
        {
            "foreshadow_id": "FS-008", "type": "信息伏笔", "status": "已埋设",
            "plant_chapter": 500, "plant_location": "林默进军国际市场时收到的匿名警告",
            "plant_form": "一封没有署名的邮件，警告林默不要涉足某些领域",
            "reveal_chapter_planned": 1000, "reveal_form": "匿名邮件来自钱浩天背后的神秘大佬——詹姆斯·洛克",
            "payload": "国际金融市场背后有一个神秘组织在操控一切",
            "surface": "一封普通的威胁邮件", "depth": "深层",
            "related_char": ["钱浩天", "詹姆斯·洛克"], "related_item": [], "related_plot": ["国际做空联盟"],
            "importance": 0.9, "chroma_id": "NOV-001_FS-008",
        },
        {
            "foreshadow_id": "FS-009", "type": "物品伏笔", "status": "已埋设",
            "plant_chapter": 250, "plant_location": "林默在投资报告中提到的芯片公司",
            "plant_form": "林默秘密买入一家名不见经传的芯片公司股票",
            "reveal_chapter_planned": 1150, "reveal_form": "这家公司就是英伟达的早期投资，回报惊人",
            "payload": "林默利用未来记忆提前布局英伟达，这是AI时代的核心资产",
            "surface": "一次普通的科技股投资", "depth": "中层",
            "related_char": ["林默"], "related_item": ["英伟达股票"], "related_plot": ["AI布局"],
            "importance": 0.8, "chroma_id": "NOV-001_FS-009",
        },
        {
            "foreshadow_id": "FS-010", "type": "结构伏笔", "status": "已埋设",
            "plant_chapter": 1100, "plant_location": "AI创新联盟成立时的章程中隐藏条款",
            "plant_form": "联盟章程中有一条关于'技术共享'的模糊条款",
            "reveal_chapter_planned": 1450, "reveal_form": "这条条款是沈婉清植入的，目的是为黑石集团窃取技术",
            "payload": "AI创新联盟的真正目的被黑石集团利用，试图控制全球AI产业链",
            "surface": "一条普通的技术合作条款", "depth": "深层",
            "related_char": ["沈婉清", "詹姆斯·洛克"], "related_item": ["AI芯片原型"], "related_plot": ["AI创新联盟"],
            "importance": 0.9, "chroma_id": "NOV-001_FS-010",
        },
        {
            "foreshadow_id": "FS-011", "type": "人物伏笔", "status": "已埋设",
            "plant_chapter": 30, "plant_location": "张铁军第一次出场时的背景描写",
            "plant_form": "张铁军办公室里挂着与某位高官的合影",
            "reveal_chapter_planned": 350, "reveal_form": "张铁军的政治保护伞被揭露",
            "payload": "张铁军依靠政治关系在地方横行霸道",
            "surface": "一个成功商人的社交展示", "depth": "浅层",
            "related_char": ["张铁军"], "related_item": [], "related_plot": ["地方势力"],
            "importance": 0.5, "chroma_id": "NOV-001_FS-011",
        },
        {
            "foreshadow_id": "FS-012", "type": "关系伏笔", "status": "已埋设",
            "plant_chapter": 300, "plant_location": "李雪与林默关于情报系统的第一次对话",
            "plant_form": "李雪提出建立一个独立于林氏资本的情报网络",
            "reveal_chapter_planned": 750, "reveal_form": "这个独立情报网络在赵明轩背叛时发挥了关键作用",
            "payload": "李雪的情报系统是林默安全的重要保障，独立于主系统避免被渗透",
            "surface": "一个员工的工作建议", "depth": "中层",
            "related_char": ["李雪", "林默"], "related_item": ["情报网络数据库"], "related_plot": ["情报系统"],
            "importance": 0.7, "chroma_id": "NOV-001_FS-012",
        },
        {
            "foreshadow_id": "FS-013", "type": "情感伏笔", "status": "已埋设",
            "plant_chapter": 120, "plant_location": "赵明轩独自在酒吧喝酒时的自言自语",
            "plant_form": "赵明轩说'我值得更多'",
            "reveal_chapter_planned": 780, "reveal_form": "这句话成为赵明轩背叛的心理动机",
            "payload": "赵明轩始终觉得自己被低估，这种不甘最终驱使他背叛",
            "surface": "一个中年人的酒后牢骚", "depth": "中层",
            "related_char": ["赵明轩"], "related_item": [], "related_plot": ["赵明轩背叛"],
            "importance": 0.65, "chroma_id": "NOV-001_FS-013",
        },
        {
            "foreshadow_id": "FS-014", "type": "物品伏笔", "status": "已埋设",
            "plant_chapter": 100, "plant_location": "林默签署的一份法律文件",
            "plant_form": "隐形持股协议，通过多层壳公司持有股份",
            "reveal_chapter_planned": 550, "reveal_form": "隐形持股结构在国际化过程中成为关键保护",
            "payload": "林默通过复杂的持股结构保持低调，避免暴露真实财富",
            "surface": "一份普通的商业法律文件", "depth": "中层",
            "related_char": ["林默"], "related_item": ["隐形持股协议"], "related_plot": ["资产保护"],
            "importance": 0.6, "chroma_id": "NOV-001_FS-014",
        },
        {
            "foreshadow_id": "FS-015", "type": "信息伏笔", "status": "已埋设",
            "plant_chapter": 550, "plant_location": "林默在瑞士银行的开户过程",
            "plant_form": "瑞士银行客户经理提到'特殊客户享受特殊服务'",
            "reveal_chapter_planned": 1100, "reveal_form": "瑞士账户中隐藏的资金成为反击黑石集团的关键",
            "payload": "林默在瑞士银行的秘密账户是最后的底牌",
            "surface": "一次普通的海外银行开户", "depth": "中层",
            "related_char": ["林默"], "related_item": ["国际银行瑞士账户"], "related_plot": ["海外资产"],
            "importance": 0.7, "chroma_id": "NOV-001_FS-015",
        },
        {
            "foreshadow_id": "FS-016", "type": "人物伏笔", "status": "已埋设",
            "plant_chapter": 600, "plant_location": "钱浩天在一次金融峰会上的演讲",
            "plant_form": "钱浩天提到'市场终将被少数人控制'",
            "reveal_chapter_planned": 1000, "reveal_form": "这句话揭示了钱浩天和黑石集团的终极目标",
            "payload": "钱浩天是黑石集团控制全球金融市场的棋子",
            "surface": "一个金融家的市场观点", "depth": "深层",
            "related_char": ["钱浩天", "詹姆斯·洛克"], "related_item": [], "related_plot": ["国际做空联盟"],
            "importance": 0.85, "chroma_id": "NOV-001_FS-016",
        },
        {
            "foreshadow_id": "FS-017", "type": "结构伏笔", "status": "已埋设",
            "plant_chapter": 400, "plant_location": "股灾期间市场异常波动的数据",
            "plant_form": "交易数据中出现不属于任何已知机构的卖单",
            "reveal_chapter_planned": 950, "reveal_form": "这些异常交易来自国际做空联盟的试探性攻击",
            "payload": "2015年股灾背后有国际势力的试探性操作",
            "surface": "股灾期间的市场噪音", "depth": "中层",
            "related_char": ["钱浩天"], "related_item": [], "related_plot": ["股灾", "国际做空"],
            "importance": 0.75, "chroma_id": "NOV-001_FS-017",
        },
        {
            "foreshadow_id": "FS-018", "type": "情感伏笔", "status": "已埋设",
            "plant_chapter": 450, "plant_location": "林默在股灾后独自站在天台",
            "plant_form": "林默看着城市夜景，思考财富的真正意义",
            "reveal_chapter_planned": 1350, "reveal_form": "这个思考最终导向林默选择科技报国的决定",
            "payload": "林默内心深处追求的不是财富，而是改变世界的能力",
            "surface": "一个成功者的深夜沉思", "depth": "深层",
            "related_char": ["林默"], "related_item": [], "related_plot": ["家国情怀"],
            "importance": 0.8, "chroma_id": "NOV-001_FS-018",
        },
        {
            "foreshadow_id": "FS-019", "type": "人物伏笔", "status": "已埋设",
            "plant_chapter": 1100, "plant_location": "沈婉清第一次出场时的细节描写",
            "plant_form": "沈婉清的简历中有一段模糊的海外经历",
            "reveal_chapter_planned": 1260, "reveal_form": "那段海外经历是她在黑石集团的训练",
            "payload": "沈婉清是黑石集团培养的间谍，潜伏在AI领域",
            "surface": "一位科学家的学术背景", "depth": "深层",
            "related_char": ["沈婉清", "詹姆斯·洛克"], "related_item": [], "related_plot": ["间谍线"],
            "importance": 0.85, "chroma_id": "NOV-001_FS-019",
        },
        {
            "foreshadow_id": "FS-020", "type": "信息伏笔", "status": "已埋设",
            "plant_chapter": 1350, "plant_location": "林默整理祖父遗物时的发现",
            "plant_form": "在祖父的书房中发现一封未寄出的信",
            "reveal_chapter_planned": 1480, "reveal_form": "信中揭示林默家族与黑石集团的百年恩怨",
            "payload": "穿越不是偶然，而是家族命运的延续，林默的使命是终结黑石集团的掌控",
            "surface": "一封普通的家书", "depth": "深层",
            "related_char": ["林默", "詹姆斯·洛克"], "related_item": ["老式怀表", "李雪哥哥的日记"], "related_plot": ["家族秘密", "最终决战"],
            "importance": 0.95, "chroma_id": "NOV-001_FS-020",
        },
    ]

    for fore in foreshadows:
        session.execute(
            text("""
                INSERT OR REPLACE INTO foreshadows
                (novel_id, foreshadow_id, type, status,
                 plant_chapter, plant_location, plant_form,
                 reveal_chapter_planned, reveal_form,
                 payload, surface, depth,
                 related_char, related_item, related_plot,
                 importance, chroma_id, created_at, last_modified)
                VALUES (:novel_id, :foreshadow_id, :type, :status,
                        :plant_chapter, :plant_location, :plant_form,
                        :reveal_chapter_planned, :reveal_form,
                        :payload, :surface, :depth,
                        :related_char, :related_item, :related_plot,
                        :importance, :chroma_id, :created_at, :last_modified)
            """),
            {
                "novel_id": NOVEL_ID,
                "foreshadow_id": fore["foreshadow_id"],
                "type": fore["type"],
                "status": fore["status"],
                "plant_chapter": fore["plant_chapter"],
                "plant_location": fore["plant_location"],
                "plant_form": fore["plant_form"],
                "reveal_chapter_planned": fore["reveal_chapter_planned"],
                "reveal_form": fore["reveal_form"],
                "payload": fore["payload"],
                "surface": fore["surface"],
                "depth": fore["depth"],
                "related_char": json.dumps(fore["related_char"], ensure_ascii=False),
                "related_item": json.dumps(fore["related_item"], ensure_ascii=False),
                "related_plot": json.dumps(fore["related_plot"], ensure_ascii=False),
                "importance": fore["importance"],
                "chroma_id": fore["chroma_id"],
                "created_at": NOW,
                "last_modified": NOW,
            },
        )

    session.flush()
    cnt = count_table(session, "foreshadows")
    print(f"  -> 伏笔已补全: {cnt} 条")

    # 统计类型分布
    type_counts = {}
    for fore in foreshadows:
        t = fore["type"]
        type_counts[t] = type_counts.get(t, 0) + 1
    for t, c in sorted(type_counts.items()):
        print(f"     {t}: {c} 条")


# ─────────────────────────────────────────────────────────────
# 5. 补全物品库（15件）
# ─────────────────────────────────────────────────────────────
def fix_items(session):
    step_header("步骤5: 补全物品库（15件）")

    session.execute(text("DELETE FROM items WHERE novel_id = :nid"), {"nid": NOVEL_ID})
    session.flush()

    items = [
        {
            "item_id": "ITEM-001", "name": "未来记忆", "type": "key_item",
            "purpose": "主角核心金手指，25年未来记忆（2010-2035），涵盖股市、科技、政治等重大事件",
            "background_story": "林默穿越时唯一携带的'资产'，以记忆形式存在于大脑中，包含未来25年的关键信息",
            "restrictions": ["记忆会随时间推移逐渐模糊", "改变历史可能导致记忆偏差", "无法回忆起 lottery 号码等纯随机信息"],
            "current_owner": "林默", "significance_to_plot": "全书核心驱动力，所有重大决策的基础",
            "first_appearance_chapter": 1,
        },
        {
            "item_id": "ITEM-002", "name": "林氏资本股权结构图", "type": "daily_item",
            "purpose": "记录林氏资本所有投资项目和持股比例的核心文档",
            "background_story": "随着林氏资本规模扩大，林默亲自设计了复杂的股权结构，通过多层壳公司隐藏真实财富",
            "restrictions": ["需要定期更新", "核心部分只有林默和苏晴知道"],
            "current_owner": "林默", "significance_to_plot": "体现林默的商业布局和隐秘策略",
            "first_appearance_chapter": 200,
        },
        {
            "item_id": "ITEM-003", "name": "老式怀表", "type": "key_item",
            "purpose": "祖父遗物，情感寄托，内藏家族秘密——与黑石集团的历史渊源",
            "background_story": "林默祖父留下的老式怀表，背面刻有家族徽章。穿越时随身携带，是林默与过去的唯一联系",
            "restrictions": ["怀表内部机关需要特定方式才能打开", "家族秘密只有族长才能知晓"],
            "current_owner": "林默", "significance_to_plot": "连接家族历史与黑石集团的核心线索",
            "first_appearance_chapter": 1,
        },
        {
            "item_id": "ITEM-004", "name": "加密笔记本电脑", "type": "technology",
            "purpose": "存储林氏资本所有商业机密和未来记忆整理笔记的加密设备",
            "background_story": "林默专门定制的军用级加密笔记本，所有数据多重加密，即使被获取也无法破解",
            "restrictions": ["需要指纹+密码+动态验证码三重认证", "数据自毁功能"],
            "current_owner": "林默", "significance_to_plot": "保护核心机密的关键道具",
            "first_appearance_chapter": 30,
        },
        {
            "item_id": "ITEM-005", "name": "星河科技早期股份", "type": "key_item",
            "purpose": "林默早期核心投资，星河科技的控制权证明",
            "background_story": "林默在星河科技创立初期持有的原始股份，随着公司发展价值翻了数千倍",
            "restrictions": ["股份协议中有竞业禁止条款", "转让需要董事会批准"],
            "current_owner": "林默", "significance_to_plot": "林默从投资者到企业家的标志",
            "first_appearance_chapter": 250,
        },
        {
            "item_id": "ITEM-006", "name": "英伟达股票", "type": "key_item",
            "purpose": "AI时代核心资产，林默提前布局英伟达的股票持仓",
            "background_story": "林默利用未来记忆在英伟达股价低迷时大量买入，AI时代来临后价值暴涨万亿",
            "restrictions": ["大量持仓需要逐步建仓和平仓", "持仓信息高度机密"],
            "current_owner": "林默", "significance_to_plot": "AI时代财富的核心来源",
            "first_appearance_chapter": 1100,
        },
        {
            "item_id": "ITEM-007", "name": "情报网络数据库", "type": "technology",
            "purpose": "李雪建立的独立情报系统，监控全球金融和政治动态",
            "background_story": "李雪利用记者背景建立的情报网络，独立于林氏资本主系统，避免被渗透",
            "restrictions": ["需要李雪亲自授权才能访问", "部分情报来源不可公开"],
            "current_owner": "李雪", "significance_to_plot": "赵明轩背叛时发挥了关键预警作用",
            "first_appearance_chapter": 300,
        },
        {
            "item_id": "ITEM-008", "name": "隐形持股协议", "type": "daily_item",
            "purpose": "通过多层壳公司持有股份的法律文件，保持低调的法律保障",
            "background_story": "林默律师团队设计的复杂持股结构，通过离岸公司和信托基金隐藏真实持股",
            "restrictions": ["需要专业律师维护", "各国法律变更可能影响结构有效性"],
            "current_owner": "林默", "significance_to_plot": "国际化过程中的资产保护工具",
            "first_appearance_chapter": 100,
        },
        {
            "item_id": "ITEM-009", "name": "陈锋的军刀", "type": "weapon",
            "purpose": "陈锋在特种部队时使用的军刀，忠诚和守护的象征",
            "background_story": "陈锋退役时唯一带走的装备，曾在多次危险中保护林默",
            "restrictions": ["普通武器，无特殊能力"],
            "current_owner": "陈锋", "significance_to_plot": "陈锋忠诚的象征，关键时刻的护身武器",
            "first_appearance_chapter": 40,
        },
        {
            "item_id": "ITEM-010", "name": "苏晴的笔记本", "type": "daily_item",
            "purpose": "苏晴从实习生到CEO的成长见证，记录了所有投资决策的思考过程",
            "background_story": "苏晴入职第一天开始使用的笔记本，记录了她在林默指导下成长的每一步",
            "restrictions": ["普通笔记本，无特殊限制"],
            "current_owner": "苏晴", "significance_to_plot": "苏晴成长弧线的具象化",
            "first_appearance_chapter": 60,
        },
        {
            "item_id": "ITEM-011", "name": "王志远的黑账本", "type": "key_item",
            "purpose": "记录王志远所有灰色交易的秘密账本，是其覆灭的关键证据",
            "background_story": "王志远的财务总监秘密保管的账本，记录了行贿、洗钱等所有违法行为",
            "restrictions": ["需要特定密码才能解读", "账本使用暗语记录"],
            "current_owner": "王志远", "significance_to_plot": "王志远覆灭的关键证据",
            "first_appearance_chapter": 350,
        },
        {
            "item_id": "ITEM-012", "name": "赵明轩的U盘", "type": "key_item",
            "purpose": "赵明轩窃取的林氏资本核心机密，包含投资策略和客户信息",
            "background_story": "赵明轩利用核心成员权限复制的加密U盘，是背叛的物证",
            "restrictions": ["U盘数据加密", "需要林氏资本内部系统才能完全解读"],
            "current_owner": "赵明轩", "significance_to_plot": "赵明轩背叛的核心物证",
            "first_appearance_chapter": 750,
        },
        {
            "item_id": "ITEM-013", "name": "AI芯片原型", "type": "technology",
            "purpose": "AI创新联盟研发的核心技术产品，具有突破性性能",
            "background_story": "AI创新联盟集合全球顶尖人才研发的下一代AI芯片，性能超越市场上所有产品",
            "restrictions": ["技术尚未完全成熟", "需要特定生产线才能量产"],
            "current_owner": "林默", "significance_to_plot": "AI创新联盟的核心资产，黑石集团的觊觎目标",
            "first_appearance_chapter": 1150,
        },
        {
            "item_id": "ITEM-014", "name": "国际银行瑞士账户", "type": "daily_item",
            "purpose": "林默在海外的秘密资金池，用于国际投资和紧急备用",
            "background_story": "林默在瑞士开设的多个匿名账户，通过复杂的资金流转隐藏来源和去向",
            "restrictions": ["需要瑞士银行的特殊授权", "大额转账会触发审查"],
            "current_owner": "林默", "significance_to_plot": "反击黑石集团的秘密资金来源",
            "first_appearance_chapter": 550,
        },
        {
            "item_id": "ITEM-015", "name": "李雪哥哥的日记", "type": "key_item",
            "purpose": "揭开李雪哥哥失踪真相的关键物品，记录了黑石集团的秘密实验",
            "background_story": "李雪哥哥被黑石集团控制前留下的日记，记录了他发现的黑石集团AI实验",
            "restrictions": ["日记部分内容被加密", "需要特定密钥才能完全解读"],
            "current_owner": "李雪", "significance_to_plot": "连接李雪个人线与黑石集团主线的关键道具",
            "first_appearance_chapter": 850,
        },
    ]

    for item in items:
        session.execute(
            text("""
                INSERT OR REPLACE INTO items
                (novel_id, item_id, name, type, purpose, background_story,
                 restrictions, current_owner, significance_to_plot,
                 first_appearance_chapter)
                VALUES (:novel_id, :item_id, :name, :type, :purpose,
                        :background_story, :restrictions, :current_owner,
                        :significance_to_plot, :first_appearance_chapter)
            """),
            {
                "novel_id": NOVEL_ID,
                "item_id": item["item_id"],
                "name": item["name"],
                "type": item["type"],
                "purpose": item["purpose"],
                "background_story": item["background_story"],
                "restrictions": json.dumps(item["restrictions"], ensure_ascii=False),
                "current_owner": item["current_owner"],
                "significance_to_plot": item["significance_to_plot"],
                "first_appearance_chapter": item["first_appearance_chapter"],
            },
        )

    session.flush()
    cnt = count_table(session, "items")
    print(f"  -> 物品已补全: {cnt} 件")
    for item in items:
        print(f"     {item['item_id']}: {item['name']} (owner={item['current_owner']}, ch={item['first_appearance_chapter']})")


# ─────────────────────────────────────────────────────────────
# 6. 新增反派角色（4个）
# ─────────────────────────────────────────────────────────────
def fix_villain_characters(session):
    step_header("步骤6: 新增反派角色（4个）")

    villains = [
        {
            "char_id": "CHAR-010", "name": "张铁军", "role": "反派",
            "layer1_identity": {"age": 40, "occupation": "地产商/地方势力", "origin": "本地地头蛇，依靠政治关系起家", "appearance": "身材魁梧，面相凶悍，常穿名牌西装"},
            "layer2_psychology": {
                "personality": "ESTJ：霸道、控制欲强、注重面子",
                "motivation": "维护地方霸权，不允许任何人挑战他的地位",
                "body_language_dictionary": {
                    "愤怒": ["拍桌子", "摔杯子"],
                    "得意": ["翘二郎腿", "弹雪茄"],
                    "恐惧": ["额头冒汗", "语速加快"],
                    "焦虑": ["来回踱步", "频繁看手机"],
                    "虚伪": ["假笑", "拍对方肩膀"],
                },
            },
            "layer3_ability": {
                "skills": ["地方资源整合", "政治关系运作", "灰色手段", "威胁恐吓"],
                "knowledge_boundaries": {
                    "knows": ["本地政商关系", "灰色产业链", "土地开发规则"],
                    "not_knows": ["国际金融", "高科技产业", "林默的穿越者身份"],
                },
            },
            "layer4_special": {
                "secrets": ["行贿多名地方官员", "通过暴力手段垄断建材市场"],
                "cracks": ["过度依赖政治保护伞", "低估对手的智慧"],
            },
            "weight_tier": "B",
            "weight_score": 0.45,
            "weight_json": {"arc_contribution": 0.4, "plot_driving": 0.5, "theme_carrying": 0.3, "network_centrality": 0.6},
        },
        {
            "char_id": "CHAR-007", "name": "钱浩天", "role": "反派",
            "layer1_identity": {"age": 45, "occupation": "国际对冲基金经理", "origin": "华尔街精英，哈佛MBA，曾在多家顶级投行工作", "appearance": "儒雅斯文，戴金丝眼镜，永远面带微笑"},
            "layer2_psychology": {
                "personality": "INTJ：冷酷、算计、极度理性",
                "motivation": "控制全球金融市场，证明自己是金融界的神",
                "body_language_dictionary": {
                    "愤怒": ["推眼镜", "手指轻敲桌面"],
                    "得意": ["嘴角微扬", "整理袖扣"],
                    "恐惧": ["瞳孔微缩", "握拳"],
                    "焦虑": ["看表", "翻阅文件"],
                    "虚伪": ["真诚微笑", "主动握手"],
                },
            },
            "layer3_ability": {
                "skills": ["金融衍生品交易", "心理战", "资源操控", "跨国资本运作", "市场操纵"],
                "knowledge_boundaries": {
                    "knows": ["国际金融规则", "政治博弈", "各国监管漏洞"],
                    "not_knows": ["林默的穿越者身份", "AI的未来走向"],
                },
            },
            "layer4_special": {
                "secrets": ["曾因内幕交易被SEC调查但逃脱", "与黑石集团有秘密合作协议"],
                "cracks": ["过度自信", "低估对手", "对控制欲的执念可能成为弱点"],
            },
            "weight_tier": "A",
            "weight_score": 0.72,
            "weight_json": {"arc_contribution": 0.8, "plot_driving": 0.85, "theme_carrying": 0.6, "network_centrality": 0.7},
        },
        {
            "char_id": "CHAR-008", "name": "沈婉清", "role": "反派",
            "layer1_identity": {"age": 32, "occupation": "AI领域科学家", "origin": "海外名校博士，表面是顶尖AI研究员", "appearance": "知性优雅，气质出众，善于伪装"},
            "layer2_psychology": {
                "personality": "ENTP：聪明、善于伪装、内心矛盾",
                "motivation": "表面追求科学进步，实际为黑石集团窃取AI技术",
                "body_language_dictionary": {
                    "紧张": ["摸耳垂", "语速略快"],
                    "伪装": ["完美微笑", "眼神真诚"],
                    "矛盾": ["短暂沉默", "看向窗外"],
                    "得意": ["轻抿嘴唇", "低头"],
                    "恐惧": ["手指颤抖", "深呼吸"],
                },
            },
            "layer3_ability": {
                "skills": ["AI技术研发", "社交伪装", "情报收集", "密码学"],
                "knowledge_boundaries": {
                    "knows": ["AI前沿技术", "黑石集团内部运作", "间谍技巧"],
                    "not_knows": ["林默的完整投资策略", "林默的穿越者身份"],
                },
            },
            "layer4_special": {
                "secrets": ["黑石集团培养的间谍", "真实身份是某国情报人员"],
                "cracks": ["对林默产生了真实感情", "内心善良与任务之间的矛盾"],
            },
            "weight_tier": "A",
            "weight_score": 0.68,
            "weight_json": {"arc_contribution": 0.75, "plot_driving": 0.7, "theme_carrying": 0.65, "network_centrality": 0.6},
        },
        {
            "char_id": "CHAR-009", "name": "詹姆斯·洛克", "role": "反派",
            "layer1_identity": {"age": 55, "occupation": "黑石集团创始人", "origin": "英国贵族后裔，剑桥毕业，白手起家建立黑石帝国", "appearance": "银发苍苍但精神矍铄，穿着考究，气场强大"},
            "layer2_psychology": {
                "personality": "INTJ：极度理性、控制欲极强、有宏大愿景",
                "motivation": "控制全球AI产业链，通过技术霸权统治世界金融格局",
                "body_language_dictionary": {
                    "愤怒": ["眼神冰冷", "声音压低"],
                    "得意": ["缓慢鼓掌", "品红酒"],
                    "冷静": ["双手交叉", "面无表情"],
                    "焦虑": ["握紧扶手", "目光锐利"],
                    "虚伪": ["绅士微笑", "优雅鞠躬"],
                },
            },
            "layer3_ability": {
                "skills": ["全球资本操控", "政治影响力运作", "AI战略规划", "跨国阴谋策划", "人才操控"],
                "knowledge_boundaries": {
                    "knows": ["全球金融体系", "AI技术战略价值", "各国政治内幕", "林默家族历史"],
                    "not_knows": ["林默的穿越者身份", "林默怀表中的秘密"],
                },
            },
            "layer4_special": {
                "secrets": ["黑石集团的真实目标是控制全球AI产业链", "与林默家族有百年恩怨", "曾在1980年代策划过类似的技术垄断"],
                "cracks": ["对绝对控制的执念可能导致判断失误", "低估了林默的家国情怀决心"],
            },
            "weight_tier": "S",
            "weight_score": 0.88,
            "weight_json": {"arc_contribution": 0.95, "plot_driving": 0.9, "theme_carrying": 0.85, "network_centrality": 0.9},
        },
    ]

    for char in villains:
        session.execute(
            text("""
                INSERT OR REPLACE INTO characters
                (novel_id, char_id, name, role,
                 layer1_json, layer2_json, layer3_json, layer4_json,
                 weight_tier, weight_score, weight_json)
                VALUES (:novel_id, :char_id, :name, :role,
                        :layer1_json, :layer2_json, :layer3_json, :layer4_json,
                        :weight_tier, :weight_score, :weight_json)
            """),
            {
                "novel_id": NOVEL_ID,
                "char_id": char["char_id"],
                "name": char["name"],
                "role": char["role"],
                "layer1_json": json.dumps(char["layer1_identity"], ensure_ascii=False),
                "layer2_json": json.dumps(char["layer2_psychology"], ensure_ascii=False),
                "layer3_json": json.dumps(char["layer3_ability"], ensure_ascii=False),
                "layer4_json": json.dumps(char["layer4_special"], ensure_ascii=False),
                "weight_tier": char["weight_tier"],
                "weight_score": char["weight_score"],
                "weight_json": json.dumps(char["weight_json"], ensure_ascii=False),
            },
        )

    session.flush()
    cnt = count_table(session, "characters")
    print(f"  -> 反派角色已新增: 当前共 {cnt} 个角色")
    for char in villains:
        print(f"     {char['char_id']}: {char['name']} (tier={char['weight_tier']})")


# ─────────────────────────────────────────────────────────────
# 7. 建立faction_members关联
# ─────────────────────────────────────────────────────────────
def fix_faction_members(session):
    step_header("步骤7: 建立faction_members关联")

    session.execute(text("DELETE FROM faction_members WHERE faction_id IN (SELECT faction_id FROM factions WHERE novel_id = :nid)"), {"nid": NOVEL_ID})
    session.flush()

    members = [
        # 林氏资本
        {"faction_id": "FAC-001", "char_id": "CHAR-001", "role": "创始人", "rank": "S"},
        {"faction_id": "FAC-001", "char_id": "CHAR-002", "role": "安保主管", "rank": "A"},
        {"faction_id": "FAC-001", "char_id": "CHAR-003", "role": "投资部CEO", "rank": "A"},
        {"faction_id": "FAC-001", "char_id": "CHAR-006", "role": "情报部负责人", "rank": "A"},
        # 王氏投资集团
        {"faction_id": "FAC-003", "char_id": "CHAR-004", "role": "创始人", "rank": "S"},
        # 国际做空联盟
        {"faction_id": "FAC-005", "char_id": "CHAR-007", "role": "核心成员", "rank": "A"},
        # 黑石集团
        {"faction_id": "FAC-007", "char_id": "CHAR-009", "role": "创始人", "rank": "S"},
        {"faction_id": "FAC-007", "char_id": "CHAR-008", "role": "潜伏成员", "rank": "A"},
    ]

    for m in members:
        session.execute(
            text("""
                INSERT OR REPLACE INTO faction_members
                (novel_id, faction_id, char_id, role, rank)
                VALUES (:novel_id, :faction_id, :char_id, :role, :rank)
            """),
            {**m, "novel_id": NOVEL_ID},
        )

    session.flush()
    cnt = session.execute(text("SELECT COUNT(*) FROM faction_members")).scalar()
    print(f"  -> faction_members已建立: {cnt} 条关联")


# ─────────────────────────────────────────────────────────────
# 8. 新增势力（黑石集团）
# ─────────────────────────────────────────────────────────────
def fix_factions(session):
    step_header("步骤8: 新增势力（黑石集团）")

    session.execute(
        text("""
            INSERT OR REPLACE INTO factions
            (novel_id, faction_id, name, type,
             hierarchy, goals, resources, doctrines, reputation)
            VALUES (:novel_id, :faction_id, :name, :type,
                    :hierarchy, :goals, :resources, :doctrines, :reputation)
        """),
        {
            "novel_id": NOVEL_ID,
            "faction_id": "FAC-007",
            "name": "黑石集团",
            "type": "商业",
            "hierarchy": json.dumps([
                {"level": "核心", "member": "詹姆斯·洛克", "role": "创始人兼掌舵人"},
                {"level": "核心", "member": "沈婉清", "role": "潜伏间谍"},
                {"level": "外围", "member": "钱浩天", "role": "金融代理人"},
            ], ensure_ascii=False),
            "goals": json.dumps(["控制全球AI产业链", "通过技术霸权统治世界金融格局"], ensure_ascii=False),
            "resources": json.dumps(["万亿级资本", "全球政治影响力", "顶尖AI研发团队", "跨国情报网络"], ensure_ascii=False),
            "doctrines": json.dumps(["绝对控制", "利益至上", "隐秘行动"], ensure_ascii=False),
            "reputation": 0.3,
        },
    )

    session.flush()
    cnt = count_table(session, "factions")
    print(f"  -> 势力已更新: 当前共 {cnt} 个势力")


# ─────────────────────────────────────────────────────────────
# 9. 新增人物关系
# ─────────────────────────────────────────────────────────────
def fix_relations(session):
    step_header("步骤9: 新增人物关系")

    new_relations = [
        {"relation_id": "REL-101", "char_a_id": "CHAR-001", "char_b_id": "CHAR-007", "type": "enmity", "strength": 0.85, "asymmetry": 0.1,
         "history": [{"event": "做空日元后钱浩天注意到林默", "chapter": 600}], "trajectory": [{"phase": "关注", "strength": 0.3}, {"phase": "对抗", "strength": 0.85}]},
        {"relation_id": "REL-102", "char_a_id": "CHAR-001", "char_b_id": "CHAR-008", "type": "enmity", "strength": 0.75, "asymmetry": 0.2,
         "history": [{"event": "沈婉清以盟友身份接近林默", "chapter": 1000}], "trajectory": [{"phase": "伪装盟友", "strength": 0.5}, {"phase": "暴露敌意", "strength": 0.75}]},
        {"relation_id": "REL-103", "char_a_id": "CHAR-001", "char_b_id": "CHAR-009", "type": "enmity", "strength": 0.95, "asymmetry": 0.0,
         "history": [{"event": "发现黑石集团是幕后黑手", "chapter": 1100}], "trajectory": [{"phase": "暗中博弈", "strength": 0.6}, {"phase": "全面对抗", "strength": 0.95}]},
        {"relation_id": "REL-104", "char_a_id": "CHAR-007", "char_b_id": "CHAR-004", "type": "alliance", "strength": 0.5, "asymmetry": 0.3,
         "history": [{"event": "钱浩天利用王志远打压林默", "chapter": 400}], "trajectory": [{"phase": "利用", "strength": 0.5}]},
        {"relation_id": "REL-105", "char_a_id": "CHAR-008", "char_b_id": "CHAR-007", "type": "alliance", "strength": 0.6, "asymmetry": 0.2,
         "history": [{"event": "同属黑石集团阵营", "chapter": 950}], "trajectory": [{"phase": "同僚", "strength": 0.6}]},
        {"relation_id": "REL-106", "char_a_id": "CHAR-009", "char_b_id": "CHAR-007", "type": "alliance", "strength": 0.7, "asymmetry": 0.4,
         "history": [{"event": "詹姆斯·洛克招募钱浩天为代理人", "chapter": 550}], "trajectory": [{"phase": "控制", "strength": 0.7}]},
        {"relation_id": "REL-107", "char_a_id": "CHAR-010", "char_b_id": "CHAR-004", "type": "alliance", "strength": 0.4, "asymmetry": 0.1,
         "history": [{"event": "张铁军与王志远联手打压林默", "chapter": 300}], "trajectory": [{"phase": "利益同盟", "strength": 0.4}]},
        {"relation_id": "REL-108", "char_a_id": "CHAR-010", "char_b_id": "CHAR-001", "type": "enmity", "strength": 0.5, "asymmetry": 0.3,
         "history": [{"event": "张铁军打压星河科技", "chapter": 250}], "trajectory": [{"phase": "打压", "strength": 0.5}]},
    ]

    for rel in new_relations:
        session.execute(
            text("""
                INSERT OR REPLACE INTO relations
                (novel_id, relation_id, char_a_id, char_b_id, type,
                 strength, asymmetry, history, trajectory)
                VALUES (:novel_id, :relation_id, :char_a_id, :char_b_id, :type,
                        :strength, :asymmetry, :history, :trajectory)
            """),
            {
                "novel_id": NOVEL_ID,
                "relation_id": rel["relation_id"],
                "char_a_id": rel["char_a_id"],
                "char_b_id": rel["char_b_id"],
                "type": rel["type"],
                "strength": rel["strength"],
                "asymmetry": rel["asymmetry"],
                "history": json.dumps(rel["history"], ensure_ascii=False),
                "trajectory": json.dumps(rel["trajectory"], ensure_ascii=False),
            },
        )

    session.flush()
    cnt = count_table(session, "relations")
    print(f"  -> 人物关系已新增: 当前共 {cnt} 条关系")
    for rel in new_relations:
        print(f"     {rel['char_a_id']} <-> {rel['char_b_id']}: {rel['type']} (strength={rel['strength']})")


# ─────────────────────────────────────────────────────────────
# 主函数
# ─────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  综合修复脚本 - 修复数据库中所有空壳数据和扩展大纲")
    print("=" * 60)

    # 确保 schema 已初始化（仅建表，不销毁数据）
    init_schema()

    # 确保小说项目存在（使用已有 ID，不覆盖）
    engine = get_engine()
    from src.utils.id_generator import generate_id
    with engine.connect() as conn:
        existing = conn.execute(
            text("SELECT id FROM novels WHERE id = :nid"),
            {"nid": NOVEL_ID},
        ).fetchone()
        if not existing:
            conn.execute(
                text("INSERT INTO novels (id, title, current_step, status, created_at, updated_at) "
                     "VALUES (:id, :title, 1, '创作中', :now, :now)"),
                {"id": NOVEL_ID, "title": "神豪：从零开始的无限财富", "now": NOW},
            )
            conn.commit()
            print(f"\n[初始化] 小说项目 {NOVEL_ID} 已创建")
        else:
            print(f"\n[初始化] 小说项目 {NOVEL_ID} 已存在，跳过")

    # 先执行基础步骤01-10（灵感/主题/世界观/人物/势力/物品/人物关系/势力关系/弧线/伏笔）
    print("\n[初始化] 正在执行基础步骤01-10...")
    from src.storage.vector_store.chroma_client import get_chroma_client
    from src.core.modules.registry import get_registry
    from src.core.workflow.step_executor import StepExecutor

    registry = get_registry()
    registry.initialize()

    # 步骤01：灵感启动
    step1_content = {
        "directions": [{
            "title": "隐形股东：沉默的资本猎手",
            "concept": "2035年的商业帝国掌舵人穿越回2010年，拥有未来25年的完整记忆。他不张扬、不炫富，而是像一个沉默的猎手，以隐形股东的身份精准布局每一次投资。",
            "innovation_score": 0.95,
            "summary": "从2035年穿越回2010年，拥有25年未来记忆。前期国内市场积累资本，中期国际金融市场做空/抄底，后期重仓AI赛道。",
            "emotional_potential": 0.90,
            "differentiation": "穿越时间：2035年回到2010年，25年记忆。三阶段布局：前期国内→中期国际金融→后期AI赛道。"
        }],
        "theme": {
            "surface_theme": "财富与权力",
            "deep_theme": "真正的强大是掌控而非炫耀",
            "emotional_hook": "低调崛起的爽感——当对手发现你的实力时，已经来不及了",
            "theme_statement": "在这个浮躁的时代，最可怕的不是张扬的富豪，而是沉默的资本猎手",
            "reverse_confirmation": "如果主角高调炫富，他会成为众矢之的，失去真正的掌控力"
        }
    }
    step2_content = {
        "theme": {
            "surface_theme": "财富与权力",
            "deep_theme": "真正的强大是掌控而非炫耀",
            "emotional_hook": "低调崛起的爽感——当对手发现你的实力时，已经来不及了",
            "theme_statement": "在这个浮躁的时代，最可怕的不是张扬的富豪，而是沉默的资本猎手",
            "reverse_confirmation": "如果主角高调炫富，他会成为众矢之的，失去真正的掌控力",
            "sub_themes": ["信息不对称的力量", "隐形掌控的艺术", "财富与自由的悖论", "时代的浪潮", "智商碾压的爽感", "家国情怀", "团队与忠诚", "背叛与成长"]
        }
    }
    step3_content = {
        "dimensions": [
            {"name": "时间背景", "rules": [{"description": "故事时间跨度：2010年至2035年，共25年", "scope": "全局", "constraints": "主角从2035年穿越回2010年"}]},
            {"name": "地理空间", "rules": [{"description": "主要舞台：中国（前期）、国际市场（中后期）", "scope": "全局", "constraints": "前期聚焦国内，中后期扩展至全球"}]},
            {"name": "经济体系", "rules": [{"description": "国内经济：2010-2020高速增长期，2020-2025转型期，2025-2035AI驱动期", "scope": "国内", "constraints": "经济周期基于真实趋势"}]},
            {"name": "科技发展", "rules": [{"description": "互联网时代（2010-2015）→移动互联网时代（2015-2020）→AI时代（2020-2035）", "scope": "科技", "constraints": "技术发展遵循真实历史"}]},
            {"name": "政治环境", "rules": [{"description": "国内政策：供给侧改革、双创政策、新能源补贴、AI产业扶持", "scope": "国内", "constraints": "政策基于真实历史"}]},
            {"name": "商业生态", "rules": [{"description": "国内企业使用虚构名称，国际知名企业可使用真实名称", "scope": "全局", "constraints": "投资逻辑遵循真实商业规则"}]},
            {"name": "社会文化", "rules": [{"description": "社会氛围：从追求速度到追求质量，从物质追求到精神追求", "scope": "社会", "constraints": "社会变迁影响人物价值观"}]},
            {"name": "金融规则", "rules": [{"description": "做空机制、抄底逻辑、隐形投资", "scope": "金融", "constraints": "做空操作遵循真实金融规则"}]}
        ]
    }
    step4_content = {
        "characters": [
            {"name": "林默", "role": "主角", "layer1_identity": {"age": 28, "occupation": "穿越前：商业帝国掌舵人", "origin": "普通家庭出身"}, "layer2_psychology": {"personality": "INTJ：理性、战略思维、低调、内敛", "motivation": "用未来记忆创造财富，证明自己的商业智慧"}, "weight": {"tier": "S", "arc_contribution": 1.0}},
            {"name": "陈锋", "role": "关键配角", "layer1_identity": {"age": 26, "occupation": "退役特种兵/主角保镖"}, "layer2_psychology": {"personality": "ISTP：冷静、忠诚、行动派"}, "weight": {"tier": "A", "arc_contribution": 0.7}},
            {"name": "苏晴", "role": "关键配角", "layer1_identity": {"age": 24, "occupation": "主角第一批员工/后成为投资公司CEO"}, "layer2_psychology": {"personality": "ENTJ：果断、野心、执行力强"}, "weight": {"tier": "A", "arc_contribution": 0.8}},
            {"name": "王志远", "role": "反派", "layer1_identity": {"age": 35, "occupation": "投资公司老板"}, "layer2_psychology": {"personality": "ESTP：张扬、冒险、野心勃勃"}, "weight": {"tier": "A", "arc_contribution": 0.6}},
            {"name": "赵明轩", "role": "配角", "layer1_identity": {"age": 30, "occupation": "核心团队成员/后背叛"}, "layer2_psychology": {"personality": "ENFJ：外向、有魅力、善于伪装"}, "weight": {"tier": "B", "arc_contribution": 0.5}},
            {"name": "李雪", "role": "配角", "layer1_identity": {"age": 26, "occupation": "财经记者/情报网络负责人"}, "layer2_psychology": {"personality": "INFP：敏感、理想主义、正义感"}, "weight": {"tier": "B", "arc_contribution": 0.5}}
        ]
    }
    step5_content = {
        "factions": [
            {"name": "林氏资本", "type": "正派", "hierarchy": "主角林默为核心", "goals": "建立横跨国内外市场的商业帝国", "resources": "未来记忆和资本", "doctrines": "低调、隐形、共赢、忠诚", "reputation": 0.95},
            {"name": "星河科技", "type": "中立", "hierarchy": "创始人兼CEO为核心", "goals": "成为国内领先的互联网科技公司", "resources": "技术人才、用户数据", "doctrines": "创新、用户至上", "reputation": 0.85},
            {"name": "王氏投资集团", "type": "反派", "hierarchy": "王志远为核心", "goals": "打败林氏资本，成为商业世界的王者", "resources": "家族资本、人脉网络", "doctrines": "利益至上、不择手段", "reputation": 0.6},
            {"name": "云帆资本", "type": "中立", "hierarchy": "合伙人制度", "goals": "寻找优质投资项目", "resources": "资本、行业资源", "doctrines": "价值投资", "reputation": 0.8},
            {"name": "国际做空联盟", "type": "中立", "hierarchy": "松散的联盟", "goals": "在全球市场寻找做空机会", "resources": "资本、情报网络", "doctrines": "机会主义", "reputation": 0.5},
            {"name": "AI创新联盟", "type": "正派", "hierarchy": "由林氏资本发起", "goals": "推动国内AI产业发展", "resources": "技术、人才、资本", "doctrines": "创新、合作、共赢", "reputation": 0.9}
        ]
    }
    step6_content = {
        "items": [
            {"name": "未来记忆", "type": "核心资产", "description": "主角从2035年穿越回2010年，拥有25年的未来记忆", "owner": "林默", "significance": "主角的核心金手指"},
            {"name": "林氏资本股权结构图", "type": "重要文件", "description": "记录林氏资本所有投资项目的股权结构", "owner": "林默", "significance": "商业帝国的核心机密"},
            {"name": "老式怀表", "type": "象征性物品", "description": "祖父留下的老式怀表", "owner": "林默", "significance": "情感寄托"},
            {"name": "加密笔记本电脑", "type": "工具", "description": "存储所有商业机密", "owner": "林默", "significance": "核心工作工具"},
            {"name": "星河科技早期股份", "type": "资产", "description": "主角在星河科技早期投资的股份", "owner": "林默", "significance": "早期最重要的投资"},
            {"name": "英伟达股票", "type": "资产", "description": "主角在ChatGPT发布前买入的英伟达股票", "owner": "林默", "significance": "后期最重要的投资"},
            {"name": "情报网络数据库", "type": "系统", "description": "李雪负责建立的情报网络数据库", "owner": "林氏资本", "significance": "情报支撑系统"},
            {"name": "隐形持股协议", "type": "文件", "description": "主角与多个壳公司签订的隐形持股协议", "owner": "林默", "significance": "保持低调的法律保障"},
            {"name": "陈锋的军刀", "type": "武器/象征", "description": "陈锋在特种部队时使用的军刀", "owner": "陈锋", "significance": "忠诚和守护的象征"},
            {"name": "苏晴的笔记本", "type": "工具/象征", "description": "苏晴从实习生时期就开始使用的笔记本", "owner": "苏晴", "significance": "成长的见证"}
        ]
    }
    step7_content = {
        "relations": [
            {"char_a_id": "林默", "char_b_id": "陈锋", "type": "master_servant", "strength": 0.95, "asymmetry": 0.3, "history": ["林默帮助陈锋解决妹妹医药费", "陈锋成为保镖"], "trajectory": ["信任加深", "成为生死之交"]},
            {"char_a_id": "林默", "char_b_id": "苏晴", "type": "mentorship", "strength": 0.85, "asymmetry": 0.4, "history": ["林默招募苏晴", "培养成为投资人"], "trajectory": ["师徒关系", "成为商业伙伴"]},
            {"char_a_id": "林默", "char_b_id": "李雪", "type": "alliance", "strength": 0.75, "asymmetry": 0.2, "history": ["李雪因调查接触林默", "加入团队"], "trajectory": ["合作加深", "成为核心团队"]},
            {"char_a_id": "林默", "char_b_id": "王志远", "type": "enmity", "strength": 0.8, "asymmetry": 0.1, "history": ["初期合作", "王志远嫉妒", "暗中针对"], "trajectory": ["合作→竞争→敌对"]},
            {"char_a_id": "林默", "char_b_id": "赵明轩", "type": "enmity", "strength": 0.7, "asymmetry": 0.5, "history": ["招募", "成为核心团队", "背叛"], "trajectory": ["信任→背叛→敌对"]},
            {"char_a_id": "陈锋", "char_b_id": "苏晴", "type": "friendship", "strength": 0.7, "asymmetry": 0.0, "history": ["共同为林默工作", "互相支持"], "trajectory": ["同事→朋友"]},
            {"char_a_id": "苏晴", "char_b_id": "赵明轩", "type": "rivalry", "strength": 0.5, "asymmetry": 0.2, "history": ["同为林默工作", "赵明轩背叛"], "trajectory": ["同事→敌对"]},
            {"char_a_id": "王志远", "char_b_id": "赵明轩", "type": "alliance", "strength": 0.4, "asymmetry": 0.6, "history": ["王志远拉拢", "赵明轩提供情报"], "trajectory": ["利益联盟→失败"]}
        ]
    }
    step8_content = {
        "relations": [
            {"faction_a_id": "林氏资本", "faction_b_id": "星河科技", "type": "alliance", "strength": 0.85, "history": ["早期投资", "长期合作"], "treaties": ["投资协议"], "hidden_agenda": "林氏资本通过隐形持股控制星河科技部分股权"},
            {"faction_a_id": "林氏资本", "faction_b_id": "王氏投资集团", "type": "hostile", "strength": 0.9, "history": ["初期合作", "竞争加剧", "暗中对抗"], "treaties": [], "hidden_agenda": "王志远企图吞并林氏资本"},
            {"faction_a_id": "林氏资本", "faction_b_id": "云帆资本", "type": "alliance", "strength": 0.7, "history": ["合作投资", "互利共赢"], "treaties": ["投资合作协议"], "hidden_agenda": ""},
            {"faction_a_id": "林氏资本", "faction_b_id": "国际做空联盟", "type": "neutral", "strength": 0.5, "history": ["做空日元合作", "某些事件博弈"], "treaties": [], "hidden_agenda": "林默利用做空联盟获取情报"},
            {"faction_a_id": "林氏资本", "faction_b_id": "AI创新联盟", "type": "subordinate", "strength": 0.95, "history": ["发起联盟", "推动AI产业"], "treaties": ["联盟协议"], "hidden_agenda": "林氏资本通过AI创新联盟掌控国内AI产业话语权"},
            {"faction_a_id": "王氏投资集团", "faction_b_id": "星河科技", "type": "neutral", "strength": 0.4, "history": ["投资被拒"], "treaties": [], "hidden_agenda": "王志远企图渗透星河科技"},
            {"faction_a_id": "王氏投资集团", "faction_b_id": "云帆资本", "type": "neutral", "strength": 0.3, "history": ["项目竞争"], "treaties": [], "hidden_agenda": ""},
            {"faction_a_id": "星河科技", "faction_b_id": "AI创新联盟", "type": "alliance", "strength": 0.8, "history": ["加入联盟", "AI技术研发"], "treaties": ["联盟成员协议"], "hidden_agenda": ""}
        ]
    }

    base_steps = [
        (1, step1_content), (2, step2_content), (3, step3_content),
        (4, step4_content), (5, step5_content), (6, step6_content),
        (7, step7_content), (8, step8_content),
    ]

    with get_session() as base_session:
        chroma = get_chroma_client()
        executor = StepExecutor(NOVEL_ID, base_session, chroma)
        for step_num, content in base_steps:
            result = executor.execute(step_num, content)
            status = '成功' if result.success else '失败'
            print(f'  基础步骤 {step_num:02d}: {result.step_name} - {status}')
            if not result.success and result.errors:
                for e in result.errors:
                    print(f'    错误: {e}')

    # 使用get_session执行修复
    with get_session() as session:
        try:
            fix_outlines(session)
            fix_volumes(session)
            fix_character_arcs(session)
            fix_foreshadows(session)
            fix_items(session)
            fix_villain_characters(session)
            fix_factions(session)
            fix_faction_members(session)
            fix_relations(session)

            print("\n" + "=" * 60)
            print("  所有修复完成!")
            print("=" * 60)

            # 最终统计
            print("\n最终数据统计:")
            tables = ["outlines", "volumes", "character_arcs", "foreshadows",
                      "items", "characters", "factions", "faction_members", "relations"]
            for t in tables:
                c = count_table(session, t)
                print(f"  {t:<20} {c} 条")

        except Exception as e:
            print(f"\n[错误] 修复过程中出错: {e}")
            import traceback
            traceback.print_exc()
            raise


if __name__ == "__main__":
    main()
