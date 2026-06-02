# -*- coding: utf-8 -*-
"""
对1500章细纲进行全面优化增强：
1. 开篇三重反转（重写第1-10章）
2. 为所有1500章添加章节钩子类型（hook_type）
3. 增加伏笔密度（新增约200个埋设点）
4. 增加喜剧调节场景（每20章至少1个）
5. 增加信息密度标注（info_density_notes）
"""
import sys
import json
import sqlite3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config


# ==================== 第1-10章完全重写数据 ====================

CHAPTERS_1_10 = {
    1: {
        "chapter_constraint_summary": {
            "title": "穿越2010",
            "summary": "林默醒来，发现自己回到了2010年。检查随身物品——老式怀表、一部旧手机。他以为自己是最幸运的人。但当他走到窗前，看到对面楼顶有一个模糊的人影也在看着他时，心中一惊——难道有人和他一样？",
            "hook_type": "悬念",
            "info_density_notes": "本章信息增量：1.林默穿越回2010年的事实确认 2.随身物品暗示时间锚点（怀表）3.对面楼顶神秘人影暗示存在其他穿越者"
        },
        "scenes": [
            {
                "scene_id": "s1_1",
                "description": "林默醒来，发现自己回到了2010年。检查随身物品——老式怀表、一部旧手机。他以为自己是最幸运的人，开始规划利用未来记忆改变命运。",
                "word_count_budget": 1200,
                "pov_char_id": "林默",
                "participants": ["林默"],
                "emotional_arc": {"start_emotion": "迷茫", "end_emotion": "期待"},
                "resolution_type": "埋设"
            },
            {
                "scene_id": "s1_2",
                "description": "林默走到窗前，看到对面楼顶有一个模糊的人影——那个人也在看着他。林默心中一惊：难道有人和他一样？他试图看清对方，但人影一闪而没。",
                "word_count_budget": 1200,
                "pov_char_id": "林默",
                "participants": ["林默"],
                "emotional_arc": {"start_emotion": "期待", "end_emotion": "震惊"},
                "resolution_type": "埋设"
            }
        ]
    },
    2: {
        "chapter_constraint_summary": {
            "title": "选择低调",
            "summary": "林默决定低调起步。他利用未来记忆，精准判断了当天股市走势，小赚一笔。当晚，他在网上搜索'穿越'相关帖子，发现了一个匿名论坛——有人在2010年之前就发布了2015年的新闻截图。帖子已被删除，但林默截了图。",
            "hook_type": "反转",
            "info_density_notes": "本章信息增量：1.林默确认未来记忆可用 2.匿名论坛帖子暗示存在其他穿越者 3.2015年新闻截图的时间线矛盾"
        },
        "scenes": [
            {
                "scene_id": "s2_1",
                "description": "林默决定低调起步。他利用未来记忆，精准判断了当天股市走势，小赚一笔。一切顺利得让他信心倍增。",
                "word_count_budget": 1200,
                "pov_char_id": "林默",
                "participants": ["林默"],
                "emotional_arc": {"start_emotion": "谨慎", "end_emotion": "自信"},
                "resolution_type": "维持"
            },
            {
                "scene_id": "s2_2",
                "description": "当晚，林默在网上搜索'穿越'相关帖子，发现了一个匿名论坛——有人在2010年之前就发布了2015年的新闻截图。帖子已被删除，但林默截了图。他盯着截图看了很久，手微微发抖。",
                "word_count_budget": 1200,
                "pov_char_id": "林默",
                "participants": ["林默"],
                "emotional_arc": {"start_emotion": "好奇", "end_emotion": "不安"},
                "resolution_type": "埋设"
            }
        ]
    },
    3: {
        "chapter_constraint_summary": {
            "title": "第一桶金",
            "summary": "林默利用未来记忆投资，获得第一桶金。一切顺利得不像话。但林默发现——他的第一桶金来源，与2035年某个已经破产的公司有关。这家公司不应该在2010年存在。",
            "hook_type": "问题",
            "info_density_notes": "本章信息增量：1.林默获得第一桶金 2.资金来源与2035年破产公司关联 3.时间线异常暗示穿越者间的因果纠缠"
        },
        "scenes": [
            {
                "scene_id": "s3_1",
                "description": "林默利用未来记忆投资，获得第一桶金。一切顺利得不像话，他开始相信自己真的可以改变一切。",
                "word_count_budget": 1200,
                "pov_char_id": "林默",
                "participants": ["林默"],
                "emotional_arc": {"start_emotion": "自信", "end_emotion": "兴奋"},
                "resolution_type": "维持"
            },
            {
                "scene_id": "s3_2",
                "description": "但林默发现——他的第一桶金来源，与2035年某个已经破产的公司有关。这家公司不应该在2010年存在。林默查了三遍，确认无误。他感到一阵寒意。",
                "word_count_budget": 1200,
                "pov_char_id": "林默",
                "participants": ["林默"],
                "emotional_arc": {"start_emotion": "兴奋", "end_emotion": "警觉"},
                "resolution_type": "埋设"
            }
        ]
    },
    4: {
        "chapter_constraint_summary": {
            "title": "陈锋的困境",
            "summary": "林默遇到退役特种兵陈锋。陈锋的妹妹重病需要巨额医药费。林默决定帮他。陈锋注意到林默的眼神——'你看人的眼神不像28岁的人，倒像经历了什么大事。'林默心中一紧。",
            "hook_type": "情感",
            "info_density_notes": "本章信息增量：1.陈锋登场及背景（退役特种兵）2.陈锋妹妹重病的软肋 3.陈锋对林默年龄与眼神不符的敏锐观察"
        },
        "scenes": [
            {
                "scene_id": "s4_1",
                "description": "林默遇到退役特种兵陈锋。陈锋的妹妹重病需要巨额医药费，他四处借钱无门。林默在医院走廊看到这个铁骨铮铮的男人蹲在墙角，双手抱头。",
                "word_count_budget": 1200,
                "pov_char_id": "陈锋",
                "participants": ["林默", "陈锋"],
                "emotional_arc": {"start_emotion": "绝望", "end_emotion": "惊讶"},
                "resolution_type": "维持"
            },
            {
                "scene_id": "s4_2",
                "description": "林默决定帮陈锋。陈锋注意到林默的眼神——'你看人的眼神不像28岁的人，倒像经历了什么大事。'林默心中一紧，面上不动声色。",
                "word_count_budget": 1200,
                "pov_char_id": "陈锋",
                "participants": ["林默", "陈锋"],
                "emotional_arc": {"start_emotion": "惊讶", "end_emotion": "感激"},
                "resolution_type": "维持"
            }
        ]
    },
    5: {
        "chapter_constraint_summary": {
            "title": "忠诚的起点",
            "summary": "林默帮助陈锋解决医药费。陈锋说'有我在。'——这是他第一次说这句话。林默帮陈锋时，注意到陈锋军刀上的刻字——那是一个名字，与林默祖父的名字相同。林默没有声张。",
            "hook_type": "悬念",
            "info_density_notes": "本章信息增量：1.陈锋'有我在'口头禅的起源 2.军刀刻字与林默祖父同名 3.陈锋正式成为林默的保镖"
        },
        "scenes": [
            {
                "scene_id": "s5_1",
                "description": "林默帮助陈锋解决医药费。陈锋沉默了很久，最后只说了三个字：'有我在。'——这是他第一次说这句话，从此这三个字将成为他一生的承诺。",
                "word_count_budget": 1200,
                "pov_char_id": "林默",
                "participants": ["林默", "陈锋"],
                "emotional_arc": {"start_emotion": "平静", "end_emotion": "感动"},
                "resolution_type": "维持"
            },
            {
                "scene_id": "s5_2",
                "description": "林默帮陈锋收拾东西时，注意到陈锋军刀上的刻字——那是一个名字，与林默祖父的名字相同。林默没有声张，只是在心里默默记下了这个巧合。",
                "word_count_budget": 1200,
                "pov_char_id": "林默",
                "participants": ["林默", "陈锋"],
                "emotional_arc": {"start_emotion": "感动", "end_emotion": "疑惑"},
                "resolution_type": "埋设"
            }
        ]
    },
    6: {
        "chapter_constraint_summary": {
            "title": "招募苏晴",
            "summary": "林默招募实习生苏晴。苏晴用左手签字——林默注意到但没说什么。苏晴在笔记本上画了一个小太阳——她不知道为什么，只是觉得今天是个好日子。",
            "hook_type": "反转",
            "info_density_notes": "本章信息增量：1.苏晴登场（左撇子细节）2.苏晴对林默的潜意识好感（画太阳）3.林默对细节的敏锐观察力"
        },
        "scenes": [
            {
                "scene_id": "s6_1",
                "description": "林默招募实习生苏晴。面试时苏晴用左手签字——林默注意到但没说什么。苏晴的投资直觉让林默眼前一亮，决定录用她。",
                "word_count_budget": 1200,
                "pov_char_id": "苏晴",
                "participants": ["林默", "苏晴"],
                "emotional_arc": {"start_emotion": "紧张", "end_emotion": "开心"},
                "resolution_type": "维持"
            },
            {
                "scene_id": "s6_2",
                "description": "入职第一天，苏晴在笔记本上画了一个小太阳——她不知道为什么，只是觉得今天是个好日子。也许是因为那个面试官的眼神，让她觉得未来充满希望。",
                "word_count_budget": 1200,
                "pov_char_id": "苏晴",
                "participants": ["苏晴"],
                "emotional_arc": {"start_emotion": "开心", "end_emotion": "憧憬"},
                "resolution_type": "埋设"
            }
        ]
    },
    7: {
        "chapter_constraint_summary": {
            "title": "投资星河科技",
            "summary": "林默投资初创公司星河科技。创始人是一个年轻人，看起来普通但眼神不普通。林默离开后，星河科技创始人打了一个电话：'他来了。和预测的一样。'",
            "hook_type": "问题",
            "info_density_notes": "本章信息增量：1.星河科技投资决策 2.创始人眼神异常暗示其不凡身份 3.创始人电话暗示有人预知林默会来"
        },
        "scenes": [
            {
                "scene_id": "s7_1",
                "description": "林默投资初创公司星河科技。创始人是一个年轻人，看起来普通但眼神不普通——那种眼神，林默在2035年见过。他压下心中的疑虑，完成了投资。",
                "word_count_budget": 1200,
                "pov_char_id": "林默",
                "participants": ["林默"],
                "emotional_arc": {"start_emotion": "冷静", "end_emotion": "疑虑"},
                "resolution_type": "维持"
            },
            {
                "scene_id": "s7_2",
                "description": "林默离开后，星河科技创始人打了一个电话：'他来了。和预测的一样。'电话那头沉默了几秒，然后说：'按计划进行。'创始人挂断电话，望向窗外。",
                "word_count_budget": 1200,
                "pov_char_id": "林默",
                "participants": ["林默"],
                "emotional_arc": {"start_emotion": "疑虑", "end_emotion": "不安"},
                "resolution_type": "埋设"
            }
        ]
    },
    8: {
        "chapter_constraint_summary": {
            "title": "林氏资本成立",
            "summary": "林默正式成立林氏资本。他感到一阵眩晕——脑海中一段2035年的记忆突然模糊了。林默扶住桌子，告诉自己这只是暂时的。但他知道：每使用一次关键记忆，就会遗忘一段2035年的个人记忆。",
            "hook_type": "情感",
            "info_density_notes": "本章信息增量：1.林氏资本正式成立 2.穿越代价机制揭示——使用未来记忆会遗忘个人记忆 3.2035年记忆开始模糊"
        },
        "scenes": [
            {
                "scene_id": "s8_1",
                "description": "林默正式成立林氏资本。在签署文件的瞬间，他感到一阵眩晕——脑海中一段2035年的记忆突然模糊了。那是关于一个人的记忆，但人脸已经看不清了。",
                "word_count_budget": 1200,
                "pov_char_id": "林默",
                "participants": ["林默"],
                "emotional_arc": {"start_emotion": "兴奋", "end_emotion": "眩晕"},
                "resolution_type": "维持"
            },
            {
                "scene_id": "s8_2",
                "description": "林默扶住桌子，告诉自己这只是暂时的。但他知道：每使用一次关键记忆，就会遗忘一段2035年的个人记忆。这是穿越的代价，而他必须承受。",
                "word_count_budget": 1200,
                "pov_char_id": "林默",
                "participants": ["林默"],
                "emotional_arc": {"start_emotion": "眩晕", "end_emotion": "坚定"},
                "resolution_type": "埋设"
            }
        ]
    },
    9: {
        "chapter_constraint_summary": {
            "title": "团队文化",
            "summary": "林默建立团队文化。陈锋、苏晴、赵明轩陆续加入。赵明轩笑着说'为了团队好'——但他的眼神没有在笑。林默在办公室看老照片——2035年的合影。照片中有一个人的脸已经模糊了。",
            "hook_type": "反转",
            "info_density_notes": "本章信息增量：1.核心团队初步成型 2.赵明轩的笑面虎特质首次暴露 3.2035年合影中模糊面孔与记忆丢失对应"
        },
        "scenes": [
            {
                "scene_id": "s9_1",
                "description": "林默建立团队文化。陈锋、苏晴、赵明轩陆续加入。赵明轩笑着说'为了团队好'——但他的眼神没有在笑。只有林默注意到了这个细节。",
                "word_count_budget": 1200,
                "pov_char_id": "赵明轩",
                "participants": ["林默", "陈锋", "苏晴", "赵明轩"],
                "emotional_arc": {"start_emotion": "热情", "end_emotion": "复杂"},
                "resolution_type": "维持"
            },
            {
                "scene_id": "s9_2",
                "description": "深夜，林默在办公室看老照片——2035年的合影。他轻轻叹了口气，把照片收起来。照片中有一个人的脸已经模糊了，就像他脑海中那段正在消失的记忆。",
                "word_count_budget": 1200,
                "pov_char_id": "林默",
                "participants": ["林默"],
                "emotional_arc": {"start_emotion": "疲惫", "end_emotion": "孤独"},
                "resolution_type": "埋设"
            }
        ]
    },
    10: {
        "chapter_constraint_summary": {
            "title": "新能源布局",
            "summary": "林默提前布局新能源。他的判断精准得令人害怕——但他知道，这种精准正在以遗忘为代价。林默收到一条匿名短信：'你不是唯一一个回来的人。'他盯着手机看了很久，然后删除了短信。",
            "hook_type": "悬念",
            "info_density_notes": "本章信息增量：1.新能源布局启动 2.精准判断与记忆遗忘的代价关系 3.匿名短信确认存在其他穿越者（三重反转完成）"
        },
        "scenes": [
            {
                "scene_id": "s10_1",
                "description": "林默提前布局新能源。他的判断精准得令人害怕——但他知道，这种精准正在以遗忘为代价。每次做出精准判断后，他都会短暂失神一秒。",
                "word_count_budget": 1200,
                "pov_char_id": "林默",
                "participants": ["林默"],
                "emotional_arc": {"start_emotion": "坚定", "end_emotion": "疲惫"},
                "resolution_type": "维持"
            },
            {
                "scene_id": "s10_2",
                "description": "林默收到一条匿名短信：'你不是唯一一个回来的人。'他盯着手机看了很久，然后删除了短信。窗外，对面楼顶那个人影又出现了。",
                "word_count_budget": 1200,
                "pov_char_id": "林默",
                "participants": ["林默"],
                "emotional_arc": {"start_emotion": "疲惫", "end_emotion": "震惊"},
                "resolution_type": "埋设"
            }
        ]
    },
}


# ==================== 钩子类型分配 ====================

def get_hook_type(chapter_num):
    """为章节分配钩子类型"""
    # 关键剧情点强制使用特定类型
    key_reversal_chapters = {
        1, 2, 3, 7, 8, 10, 50, 100, 200, 300, 400, 450, 500,
        600, 650, 750, 800, 850, 900, 950, 1000, 1050, 1100,
        1150, 1200, 1250, 1300, 1350, 1400, 1450, 1500
    }
    key_emotion_chapters = {
        5, 45, 150, 250, 350, 500, 700, 850, 950, 1050,
        1200, 1350, 1400, 1480, 1500
    }

    if chapter_num in key_reversal_chapters:
        return "反转"
    if chapter_num in key_emotion_chapters:
        return "情感"

    # 默认轮换：问题→悬念→反转→情感
    cycle = (chapter_num - 1) % 4
    return ["问题", "悬念", "反转", "情感"][cycle]


# ==================== 喜剧场景模板 ====================

COMEDY_TEMPLATES = {
    # 陈锋的"直男式忠诚"
    "chenfeng_protect": [
        "陈锋面无表情地挡在林默身前：'有我在。'三秒内解决了所有人。林默：'……你以后能不能给我留点表现的机会？'陈锋：'不能。'",
        "陈锋在电梯里遇到有人试图接近林默，直接把人拎起来放到走廊上。林默：'陈锋，他只是来送外卖的。'陈锋沉默两秒：'……下次我轻点。'",
        "陈锋给林默买咖啡，结果买了五杯一样的美式。林默：'你为什么买五杯？'陈锋：'万一前四杯有毒。'林默无语。",
        "有人威胁林默，陈锋二话不说把对方的车钥匙扔进了河里。林默：'我们是在谈生意，不是在拍动作片。'陈锋：'谈完了？'林默：'……还没开始。'陈锋：'那我可以继续了。'",
        "陈锋学会了用智能手机，给林默发了第一条微信：'老板安全。'然后又发了十七条同样的消息。林默：'陈锋，你按了一次发送键。'陈锋：'我知道，但十七次更安全。'",
    ],
    # 张铁军的"你知道我是谁吗"
    "zhangtiejun_bluster": [
        "张铁军拍着桌子吼'你知道我是谁吗？'林默平静地回答'知道，所以呢？'张铁军愣住了，这是第一次有人对这句话无动于衷。",
        "张铁军在酒会上故意大声说话吸引注意，结果没人理他。他走到林默面前：'林默，你应该知道在这个城市谁说了算。'林默端着酒杯：'法律？'张铁军差点把酒喷出来。",
        "张铁军派人堵林默的车，结果堵错了——堵了市长的车。张铁军知道后脸色铁青，连夜去道歉。林默听说后笑了整整一天。",
        "张铁军在谈判桌上摔文件，结果把自己假发摔掉了。全场沉默。林默面不改色地捡起来递给他：'张总，您的……装饰品。'张铁军涨红了脸。",
    ],
    # 赵明轩的"笑面虎"表演
    "zhaomingxuan_smile": [
        "赵明轩笑着说'为了团队好'，但他的眼神没有在笑。苏晴悄悄对林默说：'赵总监笑的时候比不笑的时候更可怕。'林默点头：'观察力不错。'",
        "赵明轩在团建时表演魔术，把一张百元大钞变没了。陈锋：'我的钱呢？'赵明轩微笑：'投资有风险。'陈锋面无表情地伸出手。赵明轩乖乖掏出两百块。",
        "赵明轩对竞争对手说'合作愉快'，转头就对林默说'三个月内吞掉他'。林默：'你刚才不是还说合作愉快？'赵明轩微笑：'那是客气。'",
        "赵明轩加班到凌晨三点，第二天依然西装革履、笑容满面。新来的实习生问苏晴：'赵总监是不是不用睡觉？'苏晴：'他不用，但你需要。'",
    ],
}


# ==================== 埋设内容生成（根据章节主题） ====================

def generate_foreshadow_description(chapter_num, title, summary):
    """根据章节主题生成埋设场景描述"""
    templates = [
        # 人物伏笔类
        lambda t, s: f"在处理{s[:20]}相关事务时，林默注意到一个细节——某个人的反应与预期不符。他将这个细节默默记在心里，没有声张。",
        lambda t, s: f"会议结束后，林默独自翻看文件，发现{s[:20]}的数据中有一个微小的异常。这个异常目前看起来无关紧要，但林默的直觉告诉他事情没那么简单。",
        # 物品伏笔类
        lambda t, s: f"林默在整理{s[:20]}相关资料时，发现了一份旧文件，上面有一个被划掉的名字。这个名字他似曾相识，但一时想不起在哪里见过。",
        lambda t, s: f"陈锋在执行{s[:20]}相关任务时，发现了一个不寻常的物品。他本能地觉得这个物品不简单，但没有告诉任何人。",
        # 环境伏笔类
        lambda t, s: f"林默路过{s[:20]}相关的地点时，突然感到一阵莫名的熟悉感——这种熟悉感不是来自2010年，而是来自2035年。他停下脚步，环顾四周。",
        lambda t, s: f"在{s[:20]}的过程中，天气突然变化，林默看着窗外的雨，想起了2035年某个同样下雨的日子。那天的记忆已经模糊了，但那种不安的感觉还在。",
        # 情节伏笔类
        lambda t, s: f"林默在分析{s[:20]}的局势时，脑海中闪过一个念头——如果有人拥有和他一样的信息，会怎么做？他摇了摇头，把这个念头压了下去。",
        lambda t, s: f"处理{s[:20]}事务时，林默收到了一封匿名邮件。邮件内容只有一行字，但让林默沉默了很久。他删除了邮件，但记住了发件时间。",
        # 对话伏笔类
        lambda t, s: f"苏晴在讨论{s[:20]}时无意中说了一句话，让林默愣了一下。那句话的措辞方式，和2035年某个人一模一样。林默没有追问。",
        lambda t, s: f"陈锋在汇报{s[:20]}相关情况时，突然停顿了一下，说'有件事不知道该不该说'。林默看着他：'说。'陈锋犹豫了一秒，然后说了一个看似无关的细节。",
        # 情感伏笔类
        lambda t, s: f"深夜，林默独自坐在办公室，看着{s[:20]}的文件出神。他想起了2035年的某个人，但那个人的脸已经完全模糊了。他闭上眼睛，试图回忆，却什么也抓不住。",
        lambda t, s: f"在{s[:20]}取得进展后，林默短暂地感到一阵眩晕——又一段2035年的记忆消失了。他扶住桌子，深吸一口气。代价，总是要付的。",
    ]
    idx = (chapter_num * 7 + hash(title)) % len(templates)
    return templates[idx](title, summary)


# ==================== 信息密度标注生成 ====================

def generate_info_density_notes(chapter_num, title, summary):
    """根据章节内容生成信息密度标注"""
    # 基于章节位置和标题生成有意义的信息增量描述
    notes_parts = []

    # 根据章节范围添加不同的信息增量
    if chapter_num <= 50:
        notes_parts.append(f"林默在{title}中的关键决策")
    elif chapter_num <= 150:
        notes_parts.append(f"团队在{title}阶段的成长变化")
    elif chapter_num <= 300:
        notes_parts.append(f"商业博弈在{title}中的推进")
    elif chapter_num <= 500:
        notes_parts.append(f"资本积累在{title}阶段的关键节点")
    elif chapter_num <= 800:
        notes_parts.append(f"国际博弈在{title}中的战略布局")
    elif chapter_num <= 1200:
        notes_parts.append(f"AI赛道在{title}中的核心进展")
    else:
        notes_parts.append(f"最终决战在{title}中的关键转折")

    # 根据章节号添加额外信息
    if chapter_num % 100 == 0:
        notes_parts.append("阶段性总结与伏笔回收")
    elif chapter_num % 50 == 0:
        notes_parts.append("中期剧情推进与角色关系变化")
    elif chapter_num % 25 == 0:
        notes_parts.append("子剧情线交汇点")

    return f"本章信息增量：{' '.join([f'{i+1}.{p}' for i, p in enumerate(notes_parts)])}"


# ==================== 主逻辑 ====================

def main():
    db_path = Config.SQLITE_PATH
    print(f"数据库路径: {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # 读取所有1500章
    print("\n[步骤1] 读取所有1500章现有数据...")
    rows = conn.execute(
        "SELECT id, chapter_number, chapter_constraint_summary, scenes FROM detail_outlines ORDER BY chapter_number"
    ).fetchall()
    print(f"  读取到 {len(rows)} 章数据")

    # 统计现有埋设/回收
    existing_埋设_chapters = set()
    existing_回收_chapters = set()
    for row in rows:
        scenes = json.loads(row['scenes'])
        for s in scenes:
            rt = s.get('resolution_type', '')
            if rt == '埋设':
                existing_埋设_chapters.add(row['chapter_number'])
            elif rt == '回收':
                existing_回收_chapters.add(row['chapter_number'])
    print(f"  现有埋设章节数: {len(existing_埋设_chapters)}")
    print(f"  现有回收章节数: {len(existing_回收_chapters)}")

    # ==================== 处理第1-10章（完全重写） ====================
    print("\n[步骤2] 重写第1-10章（开篇三重反转）...")
    rewrite_count = 0
    updates = []
    for row in rows:
        cn = row['chapter_number']
        if cn in CHAPTERS_1_10:
            data = CHAPTERS_1_10[cn]
            updates.append((
                json.dumps(data['chapter_constraint_summary'], ensure_ascii=False),
                json.dumps(data['scenes'], ensure_ascii=False),
                row['id']
            ))
            rewrite_count += 1
    print(f"  重写章节数: {rewrite_count}")

    # ==================== 处理第11-1500章 ====================
    print("\n[步骤3] 处理第11-1500章...")

    # 3a. 添加 hook_type 和 info_density_notes
    print("  3a. 添加 hook_type 和 info_density_notes...")
    hook_stats = {"问题": 0, "悬念": 0, "反转": 0, "情感": 0}
    info_count = 0

    # 3b. 新增伏笔（距上一个埋设章 >= 5章的章节）
    print("  3b. 新增伏笔点...")
    new_埋设_count = 0
    last_埋设_chapter = 0  # 追踪上一个埋设章

    # 3c. 添加喜剧场景（每20章至少1个）
    print("  3c. 添加喜剧调节场景...")
    comedy_count = 0
    last_comedy_chapter = 0

    # 收集所有非1-10章的更新
    updates_11_1500 = []

    # 喜剧模板索引
    comedy_template_keys = list(COMEDY_TEMPLATES.keys())
    chenfeng_idx = 0
    zhang_idx = 0
    zhao_idx = 0

    for row in rows:
        cn = row['chapter_number']
        if cn <= 10:
            continue

        cs = json.loads(row['chapter_constraint_summary'])
        scenes = json.loads(row['scenes'])

        title = cs.get('title', f'第{cn}章')
        summary = cs.get('summary', '')

        # --- 添加 hook_type ---
        hook = get_hook_type(cn)
        cs['hook_type'] = hook
        hook_stats[hook] = hook_stats.get(hook, 0) + 1

        # --- 添加 info_density_notes ---
        cs['info_density_notes'] = generate_info_density_notes(cn, title, summary)
        info_count += 1

        # --- 检查是否需要新增伏笔 ---
        # 追踪上一个埋设章（包括已有的和新增的）
        has_埋设 = cn in existing_埋设_chapters

        if not has_埋设 and (cn - last_埋设_chapter) >= 5:
            # 需要新增一个埋设，将最后一个"维持"场景改为"埋设"
            for s in scenes:
                if s.get('resolution_type') == '维持':
                    # 生成埋设描述，追加到现有描述中
                    foreshadow_desc = generate_foreshadow_description(cn, title, summary)
                    s['description'] = s['description'] + '\n' + foreshadow_desc
                    s['resolution_type'] = '埋设'
                    new_埋设_count += 1
                    last_埋设_chapter = cn
                    break

        # 更新 last_埋设_chapter（如果本章已有埋设）
        if has_埋设 and cn > last_埋设_chapter:
            last_埋设_chapter = cn

        # --- 检查是否需要添加喜剧场景 ---
        if (cn - last_comedy_chapter) >= 20:
            # 选择一个场景添加喜剧元素
            # 根据章节范围选择合适的喜剧模板
            if cn <= 500:
                # 早期：以陈锋的直男忠诚为主
                template_key = 'chenfeng_protect'
                templates = COMEDY_TEMPLATES[template_key]
                template = templates[chenfeng_idx % len(templates)]
                chenfeng_idx += 1
            elif cn <= 1000:
                # 中期：加入张铁军的嚣张
                if cn % 40 < 20:
                    template_key = 'chenfeng_protect'
                    templates = COMEDY_TEMPLATES[template_key]
                    template = templates[chenfeng_idx % len(templates)]
                    chenfeng_idx += 1
                else:
                    template_key = 'zhangtiejun_bluster'
                    templates = COMEDY_TEMPLATES[template_key]
                    template = templates[zhang_idx % len(templates)]
                    zhang_idx += 1
            else:
                # 后期：加入赵明轩的笑面虎
                r = cn % 60
                if r < 20:
                    template_key = 'chenfeng_protect'
                    templates = COMEDY_TEMPLATES[template_key]
                    template = templates[chenfeng_idx % len(templates)]
                    chenfeng_idx += 1
                elif r < 40:
                    template_key = 'zhangtiejun_bluster'
                    templates = COMEDY_TEMPLATES[template_key]
                    template = templates[zhang_idx % len(templates)]
                    zhang_idx += 1
                else:
                    template_key = 'zhaomingxuan_smile'
                    templates = COMEDY_TEMPLATES[template_key]
                    template = templates[zhao_idx % len(templates)]
                    zhao_idx += 1

            # 选择第一个场景添加喜剧描述
            if scenes:
                scenes[0]['description'] = scenes[0]['description'] + '\n【喜剧调节】' + template
                comedy_count += 1
                last_comedy_chapter = cn

        updates_11_1500.append((
            json.dumps(cs, ensure_ascii=False),
            json.dumps(scenes, ensure_ascii=False),
            row['id']
        ))

    print(f"  hook_type 分布: {hook_stats}")
    print(f"  info_density_notes 添加数: {info_count}")
    print(f"  新增埋设点数: {new_埋设_count}")
    print(f"  喜剧场景添加数: {comedy_count}")

    # ==================== 批量更新 ====================
    print("\n[步骤4] 批量更新数据库...")

    # 更新第1-10章
    if updates:
        conn.executemany(
            "UPDATE detail_outlines SET chapter_constraint_summary = ?, scenes = ? WHERE id = ?",
            updates
        )
        print(f"  更新第1-10章: {len(updates)} 条")

    # 更新第11-1500章
    if updates_11_1500:
        conn.executemany(
            "UPDATE detail_outlines SET chapter_constraint_summary = ?, scenes = ? WHERE id = ?",
            updates_11_1500
        )
        print(f"  更新第11-1500章: {len(updates_11_1500)} 条")

    conn.commit()

    # ==================== 验证结果 ====================
    print("\n[步骤5] 验证更新结果...")

    # 重新统计
    verify_rows = conn.execute(
        "SELECT chapter_number, chapter_constraint_summary, scenes FROM detail_outlines ORDER BY chapter_number"
    ).fetchall()

    total_hook = 0
    total_info = 0
    total_埋设 = 0
    total_回收 = 0
    total_comedy = 0
    chapters_with_埋设 = set()

    for row in verify_rows:
        cs = json.loads(row['chapter_constraint_summary'])
        scenes = json.loads(row['scenes'])

        if 'hook_type' in cs:
            total_hook += 1
        if 'info_density_notes' in cs:
            total_info += 1

        has_埋设 = False
        for s in scenes:
            rt = s.get('resolution_type', '')
            if rt == '埋设':
                total_埋设 += 1
                has_埋设 = True
            elif rt == '回收':
                total_回收 += 1
            if '喜剧调节' in s.get('description', ''):
                total_comedy += 1
        if has_埋设:
            chapters_with_埋设.add(row['chapter_number'])

    print(f"  有 hook_type 的章节数: {total_hook}/1500")
    print(f"  有 info_density_notes 的章节数: {total_info}/1500")
    print(f"  埋设场景总数: {total_埋设} (原有95 + 新增{total_埋设 - 95})")
    print(f"  回收场景总数: {total_回收}")
    print(f"  有埋设的章节数: {len(chapters_with_埋设)}")
    print(f"  喜剧场景总数: {total_comedy}")

    # 验证第1-10章
    print("\n  验证第1-10章重写结果:")
    for cn in range(1, 11):
        r = conn.execute(
            "SELECT chapter_constraint_summary, scenes FROM detail_outlines WHERE chapter_number = ?",
            (cn,)
        ).fetchone()
        if r:
            cs = json.loads(r['chapter_constraint_summary'])
            scenes = json.loads(r['scenes'])
            hook = cs.get('hook_type', 'N/A')
            has_info = 'info_density_notes' in cs
            埋设_scenes = sum(1 for s in scenes if s.get('resolution_type') == '埋设')
            print(f"    第{cn:2d}章 [{cs.get('title', 'N/A')}]: "
                  f"hook={hook}, info={has_info}, 埋设场景={埋设_scenes}, "
                  f"场景数={len(scenes)}")

    conn.close()
    print("\n[完成] 1500章细纲优化增强全部完成！")


if __name__ == '__main__':
    main()
