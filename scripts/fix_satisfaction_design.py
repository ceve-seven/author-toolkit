# -*- coding: utf-8 -*-
"""
对1500章细纲进行爽点设计和叙事节奏优化：
1. 为所有1500章添加爽点类型标注 (satisfaction_points)
2. 为所有1500章添加节奏标注 (pacing_type)
3. 为关键爽点章节添加爽点描述 (satisfaction_description)
4. 为包含"装逼打脸"的章节添加打脸节奏标注 (face_slap_target)
"""
import sys
import json
import sqlite3
import random
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config


# ==================== 爽点分配算法 ====================

def get_satisfaction_points(chapter_num):
    """根据章节号分配1-2个爽点类型。"""
    points = []

    # 关键章节强制爽点
    critical_reversal = {50, 100, 200, 300, 400, 450, 500, 600, 650, 800, 850,
                         900, 950, 1000, 1050, 1100, 1150, 1200, 1250, 1300,
                         1400, 1450, 1500}
    critical_emotion = {45, 90, 150, 250, 350, 500, 700, 850, 950, 1050,
                        1200, 1350, 1400, 1480, 1500}

    if chapter_num in critical_reversal:
        points.append("逆袭翻盘")
    if chapter_num in critical_emotion:
        points.append("情感共鸣")

    # 每10章至少1个幽默搞笑
    if chapter_num % 10 == 0:
        if "幽默搞笑" not in points:
            points.append("幽默搞笑")

    # 反派相关章节
    villain_chapters = set(range(200, 950)) | set(range(950, 1500))
    if chapter_num in villain_chapters and chapter_num % 5 == 0:
        if "反派吃瘪" not in points:
            points.append("反派吃瘪")

    # 团队章节
    team_chapters = {50, 100, 150, 250, 300, 450, 500, 850, 900, 1350,
                     1400, 1450, 1480, 1500}
    if chapter_num in team_chapters:
        if "团队忠诚" not in points:
            points.append("团队忠诚")

    # 基础分配（根据阶段）
    if chapter_num <= 100:
        pool = (["智商碾压"] * 4 + ["装逼打脸"] * 3 +
                ["财富展示"] * 2 + ["幽默搞笑"] * 1)
    elif chapter_num <= 300:
        pool = (["智商碾压"] * 3 + ["装逼打脸"] * 2 +
                ["团队忠诚"] * 2 + ["反派吃瘪"] * 2 +
                ["财富展示"] * 1)
    elif chapter_num <= 500:
        pool = (["智商碾压"] * 3 + ["逆袭翻盘"] * 2 +
                ["反派吃瘪"] * 2 + ["装逼打脸"] * 1 +
                ["情感共鸣"] * 1 + ["团队忠诚"] * 1)
    elif chapter_num <= 700:
        pool = (["智商碾压"] * 4 + ["财富展示"] * 3 +
                ["反派吃瘪"] * 2 + ["逆袭翻盘"] * 2 +
                ["装逼打脸"] * 1)
    elif chapter_num <= 900:
        pool = (["情感共鸣"] * 3 + ["逆袭翻盘"] * 2 +
                ["团队忠诚"] * 2 + ["智商碾压"] * 2 +
                ["反派吃瘪"] * 2)
    elif chapter_num <= 1100:
        pool = (["逆袭翻盘"] * 3 + ["反派吃瘪"] * 3 +
                ["智商碾压"] * 3 + ["情感共鸣"] * 2)
    elif chapter_num <= 1300:
        pool = (["智商碾压"] * 3 + ["财富展示"] * 2 +
                ["逆袭翻盘"] * 2 + ["团队忠诚"] * 2 +
                ["装逼打脸"] * 1)
    else:
        pool = (["情感共鸣"] * 3 + ["团队忠诚"] * 2 +
                ["逆袭翻盘"] * 2 + ["智商碾压"] * 2 +
                ["装逼打脸"] * 1)

    # 补充到1-2个
    while len(points) < 1:
        points.append(random.choice(pool))
    if len(points) < 2 and random.random() < 0.6:
        remaining = [p for p in pool if p not in points]
        if remaining:
            points.append(random.choice(remaining))

    return points[:2]  # 最多2个


# ==================== 节奏分配算法 ====================

def get_pacing_type(chapter_num):
    """根据章节号分配节奏类型。"""
    # 关键剧情强制高潮
    critical_highs = {50, 100, 200, 300, 400, 450, 500, 600, 650, 750,
                      800, 850, 900, 950, 1000, 1050, 1100, 1150, 1200,
                      1250, 1300, 1350, 1400, 1450, 1500}
    if chapter_num in critical_highs:
        return "高潮"

    # 基于卷内位置
    pos_in_volume = (chapter_num - 1) % 50  # 0-49
    if pos_in_volume in [9, 24, 39, 49]:  # 第10/25/40/50章
        return "高潮"
    elif pos_in_volume in [10, 25, 40]:  # 高潮后喘息
        return "喘息"
    elif pos_in_volume in [15, 30, 45]:  # 过渡
        return "过渡"
    else:
        return "推进"


# ==================== 打脸目标分配 ====================

def get_face_slap_target(chapter_num):
    """为包含'装逼打脸'的章节分配被打脸对象。"""
    if chapter_num < 200:
        return "张铁军"
    elif chapter_num < 500:
        return "王志远"
    elif chapter_num < 800:
        return "赵明轩/王志远"
    elif chapter_num < 1100:
        return "钱浩天/赵明轩"
    else:
        return "詹姆斯·洛克/沈婉清"


# ==================== 关键章节爽点描述 ====================

SATISFACTION_DESCRIPTIONS = {
    # 崛起篇
    10: "林默精准布局新能源，所有投资人在震惊中看着他——这个年轻人怎么什么都知道？",
    50: "张铁军派人阻挠，林默早已布好局，反将一军。张铁军：'他怎么知道的？！'",
    100: "林氏资本正式成立。一年时间，从一无所有到亿万身家——而这一切只是开始。",
    150: "陈锋面对三个持刀歹徒，面无表情：'有我在。'三秒后，所有人倒地。林默：'……能不能给我留点表现机会？'",
    200: "王志远提议合作，以为自己在施舍。他不知道，林默早已看穿他的每一张底牌。",
    250: "星河科技估值翻百倍。林默的隐形持股价值——连王志远知道了都会腿软。",
    300: "陈锋在极端危险中选择保护林默而非自保——'这条命是你的。'",
    350: "张铁军的靠山倒了。林默早在半年前就预判到了这一步。",
    400: "牛市疯狂，所有人都在加杠杆。只有林默在悄悄减仓——他知道接下来会发生什么。",
    450: "股灾爆发。王志远损失惨重，濒临破产。而林默——早已全身而退。",
    500: "林默站在办公室窗前，俯瞰城市夜景。国内市场已经没有挑战了——是时候走向世界。",

    # 博弈篇
    550: "做空日元成功。单日利润超过大多数基金一年的收益。钱浩天注意到了这个来自中国的年轻人。",
    600: "瑞郎脱钩，市场崩盘。所有人恐慌抛售，只有林默在疯狂买入——他知道这是千载难逢的机会。",
    650: "钱浩天第一次见林默：'你让我想起了年轻时的自己。'林默微笑：'那说明你老了。'",
    700: "沈婉清以AI科学家身份接近林默。她不知道，林默对她的每一个微笑都保持着警惕。",
    750: "赵明轩深夜复制机密文件。U盘在黑暗中闪烁——这是背叛的开始。",
    800: "赵明轩背叛的消息传来。林默沉默了一分钟，然后平静地说：'开始清算。'",
    850: "李雪发现赵明轩与王志远的秘密联系。她的手在颤抖，但她没有犹豫——立即通知林默。",
    900: "林默的反击计划启动。赵明轩和王志远还不知道，他们的一切都在林默的计算之中。",
    950: "王志远破产。他看着林默：'你到底是什么人？'林默：'一个比你看得更远的人。'",
    1000: "林默收到神秘邮件——有一个超越所有已知势力的组织在幕后操控。",
    1050: "钱浩天在金融战中败北。他第一次真正笑了：'你赢了。但你要小心——幕后还有人。'",
    1100: "钱浩天透露幕后有更大的力量。林默站在窗前：'来吧，我等这一天很久了。'",

    # 巅峰篇
    1150: "英伟达暴涨。林默早期投资的回报——翻了上千倍。万亿级资产，而他面不改色。",
    1200: "AI创新联盟成立。沈婉清在联盟中扮演关键角色——但她的真实身份即将暴露。",
    1250: "沈婉清间谍身份被揭穿。林默看着她：'我知道。从第一天起。'沈婉清震惊：'那你为什么……'林默：'因为我想看看幕后的人是谁。'",
    1300: "黑石集团发动全面攻势。林默在国际博弈中维护国家利益——这不是个人恩怨，这是家国之战。",
    1350: "林默的终极反击启动。詹姆斯·洛克第一次感到恐惧——这个中国人的布局远超他的想象。",
    1400: "詹姆斯·洛克认输。林默站在他面前：'你输了，不是因为你不够强，而是因为你选择了控制。'",
    1450: "林默安排传承。苏晴成为接班人，陈锋建立全球安保体系。林默：'是时候退居幕后了。'",
    1480: "林默给2035年某人写了一封永远不会寄出的信。穿越者的孤独——没有人能理解。",
    1500: "林默站在城市最高处，微笑着看向远方。25年的旅程，从零开始到无限财富——但他知道，真正的财富不是钱。",
}


# ==================== 主逻辑 ====================

def main():
    random.seed(42)  # 确保可复现

    db_path = Config.SQLITE_PATH
    print(f"[INFO] 数据库路径: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. 读取所有1500章的现有数据
    cursor.execute(
        "SELECT id, chapter_number, chapter_constraint_summary "
        "FROM detail_outlines ORDER BY chapter_number"
    )
    rows = cursor.fetchall()
    print(f"[INFO] 读取到 {len(rows)} 章数据")

    # 2. 处理每章
    update_data = []  # (id, new_json_str)
    stats = {
        "total": 0,
        "with_satisfaction_points": 0,
        "with_pacing_type": 0,
        "with_description": 0,
        "with_face_slap_target": 0,
        "pacing_stats": {"高潮": 0, "推进": 0, "过渡": 0, "喘息": 0},
        "satisfaction_stats": {},
    }

    for row_id, chapter_num, summary_json in rows:
        stats["total"] += 1

        # 解析现有 JSON
        summary = json.loads(summary_json) if summary_json else {}

        # --- 爽点类型 ---
        satisfaction_points = get_satisfaction_points(chapter_num)
        summary["satisfaction_points"] = satisfaction_points
        stats["with_satisfaction_points"] += 1
        for sp in satisfaction_points:
            stats["satisfaction_stats"][sp] = stats["satisfaction_stats"].get(sp, 0) + 1

        # --- 节奏类型 ---
        pacing_type = get_pacing_type(chapter_num)
        summary["pacing_type"] = pacing_type
        stats["with_pacing_type"] += 1
        stats["pacing_stats"][pacing_type] = stats["pacing_stats"].get(pacing_type, 0) + 1

        # --- 爽点描述（仅关键章节） ---
        if chapter_num in SATISFACTION_DESCRIPTIONS:
            summary["satisfaction_description"] = SATISFACTION_DESCRIPTIONS[chapter_num]
            stats["with_description"] += 1

        # --- 打脸目标（仅包含"装逼打脸"的章节） ---
        if "装逼打脸" in satisfaction_points:
            target = get_face_slap_target(chapter_num)
            summary["face_slap_target"] = target
            stats["with_face_slap_target"] += 1

        # 序列化回 JSON
        new_json = json.dumps(summary, ensure_ascii=False)
        update_data.append((new_json, row_id))

    # 3. 用 executemany 批量更新
    cursor.executemany(
        "UPDATE detail_outlines SET chapter_constraint_summary = ? WHERE id = ?",
        update_data,
    )
    conn.commit()
    print(f"[INFO] 批量更新完成，影响行数: {cursor.rowcount}")

    conn.close()

    # 4. 打印统计信息
    print("\n" + "=" * 60)
    print("  爽点设计与叙事节奏优化 — 统计报告")
    print("=" * 60)
    print(f"\n总处理章节数: {stats['total']}")
    print(f"添加爽点标注: {stats['with_satisfaction_points']} 章")
    print(f"添加节奏标注: {stats['with_pacing_type']} 章")
    print(f"添加爽点描述: {stats['with_description']} 章 (关键章节)")
    print(f"添加打脸目标: {stats['with_face_slap_target']} 章")

    print(f"\n--- 节奏分布 ---")
    total_pacing = sum(stats["pacing_stats"].values())
    for ptype, count in stats["pacing_stats"].items():
        pct = count / total_pacing * 100 if total_pacing > 0 else 0
        print(f"  {ptype}: {count} 章 ({pct:.1f}%)")

    print(f"\n--- 爽点类型分布 ---")
    total_sp = sum(stats["satisfaction_stats"].values())
    for sp, count in sorted(stats["satisfaction_stats"].items(),
                            key=lambda x: -x[1]):
        pct = count / total_sp * 100 if total_sp > 0 else 0
        print(f"  {sp}: {count} 次 ({pct:.1f}%)")

    print(f"\n--- 打脸目标分布 ---")
    face_slap_dist = {}
    for row_id, chapter_num, summary_json in rows:
        summary = json.loads(summary_json) if summary_json else {}
        if "face_slap_target" in summary:
            target = summary["face_slap_target"]
            face_slap_dist[target] = face_slap_dist.get(target, 0) + 1
    for target, count in sorted(face_slap_dist.items(), key=lambda x: -x[1]):
        print(f"  {target}: {count} 章")

    print("\n[DONE] 爽点设计与叙事节奏优化完成！")


if __name__ == "__main__":
    main()
