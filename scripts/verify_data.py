# -*- coding: utf-8 -*-
"""验证数据库数据"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config
import sqlite3

conn = sqlite3.connect(Config.SQLITE_PATH)
cursor = conn.cursor()

# 检查小说项目
cursor.execute('SELECT id, title, current_step FROM novels')
print('=== 小说项目 ===')
for row in cursor.fetchall():
    print(f'  ID: {row[0]}, 标题: {row[1]}, 当前进度: {row[2]}')

# 检查灵感数据
cursor.execute('SELECT direction_id, title FROM inspirations WHERE novel_id = "NOV-001"')
print('\n=== 灵感启动 ===')
for row in cursor.fetchall():
    print(f'  ID: {row[0]}, 标题: {row[1]}')

# 检查主题数据
cursor.execute('SELECT id, surface_theme, deep_theme FROM themes WHERE novel_id = "NOV-001"')
print('\n=== 小说主题 ===')
for row in cursor.fetchall():
    print(f'  ID: {row[0]}, 表层主题: {row[1]}, 深层主题: {row[2]}')

# 检查大纲数据
cursor.execute('SELECT id, novel_id FROM outlines WHERE novel_id = "NOV-001"')
print('\n=== 大纲 ===')
for row in cursor.fetchall():
    print(f'  ID: {row[0]}, Novel: {row[1]}')

# 检查分卷数据
cursor.execute('SELECT volume_id, name, chapter_range FROM volumes WHERE novel_id = "NOV-001"')
print('\n=== 分卷配置 ===')
for row in cursor.fetchall():
    print(f'  ID: {row[0]}, 名称: {row[1]}, 章节: {row[2]}')

# 检查章节细纲数量
cursor.execute('SELECT COUNT(*) FROM detail_outlines WHERE novel_id = "NOV-001"')
count = cursor.fetchone()[0]
print(f'\n=== 章节细纲 ===')
print(f'  章节数量: {count}')

# 检查人物数量
cursor.execute('SELECT COUNT(*) FROM characters WHERE novel_id = "NOV-001"')
count = cursor.fetchone()[0]
print(f'\n=== 人物设定 ===')
print(f'  人物数量: {count}')

# 检查势力数量
cursor.execute('SELECT COUNT(*) FROM factions WHERE novel_id = "NOV-001"')
count = cursor.fetchone()[0]
print(f'\n=== 势力设定 ===')
print(f'  势力数量: {count}')

# 检查物品数量
cursor.execute('SELECT COUNT(*) FROM items WHERE novel_id = "NOV-001"')
count = cursor.fetchone()[0]
print(f'\n=== 物品库 ===')
print(f'  物品数量: {count}')

# 检查人物关系数量
cursor.execute('SELECT COUNT(*) FROM relations WHERE novel_id = "NOV-001"')
count = cursor.fetchone()[0]
print(f'\n=== 人物关系 ===')
print(f'  关系数量: {count}')

# 检查势力关系数量
cursor.execute('SELECT COUNT(*) FROM faction_relations WHERE novel_id = "NOV-001"')
count = cursor.fetchone()[0]
print(f'\n=== 势力关系 ===')
print(f'  关系数量: {count}')

# 检查角色弧线数量
cursor.execute('SELECT COUNT(*) FROM character_arcs WHERE novel_id = "NOV-001"')
count = cursor.fetchone()[0]
print(f'\n=== 角色弧线 ===')
print(f'  弧线数量: {count}')

# 检查伏笔数量
cursor.execute('SELECT COUNT(*) FROM foreshadows WHERE novel_id = "NOV-001"')
count = cursor.fetchone()[0]
print(f'\n=== 伏笔追踪 ===')
print(f'  伏笔数量: {count}')

# 检查章节细纲内容
cursor.execute('SELECT chapter_number, chapter_constraint_summary FROM detail_outlines WHERE novel_id = "NOV-001" LIMIT 5')
print('\n=== 章节细纲示例（前5章）===')
for row in cursor.fetchall():
    print(f'  第{row[0]}章: {row[1][:50] if row[1] else "无"}...')

conn.close()
print('\n验证完成！')
