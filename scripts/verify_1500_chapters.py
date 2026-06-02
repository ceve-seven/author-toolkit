# -*- coding: utf-8 -*-
"""验证1500章细纲完整性"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config
import sqlite3
import json

conn = sqlite3.connect(Config.SQLITE_PATH)
cursor = conn.cursor()

# 总章数
total = cursor.execute("SELECT COUNT(*) FROM detail_outlines WHERE novel_id = 'NOV-001'").fetchone()[0]
print(f"总章节数: {total}")

# 章节范围
min_ch = cursor.execute("SELECT MIN(chapter_number) FROM detail_outlines WHERE novel_id = 'NOV-001'").fetchone()[0]
max_ch = cursor.execute("SELECT MAX(chapter_number) FROM detail_outlines WHERE novel_id = 'NOV-001'").fetchone()[0]
print(f"章节范围: {min_ch} - {max_ch}")

# 检查缺失章节
all_chapters = set(row[0] for row in cursor.execute(
    "SELECT chapter_number FROM detail_outlines WHERE novel_id = 'NOV-001'"
).fetchall())
expected = set(range(1, 1501))
missing = expected - all_chapters
extra = all_chapters - expected
print(f"缺失章节: {len(missing)}" + (f" {sorted(missing)[:20]}..." if missing else " 无"))
print(f"多余章节: {len(extra)}" + (f" {sorted(extra)}" if extra else " 无"))

# 按卷统计
volumes = [
    ("崛起篇 卷1-10", 1, 500),
    ("博弈篇 卷11-22", 501, 1100),
    ("巅峰篇 卷23-30", 1101, 1500),
]
for name, start, end in volumes:
    count = cursor.execute(
        "SELECT COUNT(*) FROM detail_outlines WHERE novel_id = 'NOV-001' AND chapter_number BETWEEN ? AND ?",
        (start, end)
    ).fetchone()[0]
    print(f"  {name}: {count}/{end-start+1} 章")

# 总字数预算
rows = cursor.execute("SELECT scenes FROM detail_outlines WHERE novel_id = 'NOV-001'").fetchall()
total_words = 0
total_scenes = 0
for row in rows:
    scenes = json.loads(row[0]) if row[0] else []
    total_scenes += len(scenes)
    for s in scenes:
        total_words += s.get("word_count_budget", 0)

print(f"\n总场景数: {total_scenes}")
print(f"总字数预算: {total_words:,} 字")
print(f"平均每章字数: {total_words/total:.0f} 字")

# 伏笔操作分布
resolution_counts = {"埋设": 0, "维持": 0, "回收": 0}
for row in rows:
    scenes = json.loads(row[0]) if row[0] else []
    for s in scenes:
        rt = s.get("resolution_type", "")
        if rt in resolution_counts:
            resolution_counts[rt] += 1

print(f"\n伏笔操作分布:")
for rt, count in resolution_counts.items():
    print(f"  {rt}: {count} ({count/total_scenes*100:.1f}%)")

# POV分布
pov_counts = {}
for row in rows:
    scenes = json.loads(row[0]) if row[0] else []
    for s in scenes:
        pov = s.get("pov_char_id", "未知")
        pov_counts[pov] = pov_counts.get(pov, 0) + 1

print(f"\nPOV分布:")
for pov, count in sorted(pov_counts.items(), key=lambda x: -x[1]):
    print(f"  {pov}: {count} ({count/total_scenes*100:.1f}%)")

conn.close()
print(f"\n验证完成！{'✅ 全部通过' if total == 1500 and not missing else '❌ 存在问题'}")
