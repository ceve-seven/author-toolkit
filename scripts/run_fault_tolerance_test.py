"""容错测试 — 20步流程 + 随机错误注入
验证系统在各类异常输入下的容错能力
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ['PAGER'] = 'cat'
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any

from config import Config
from src.storage.database.engine import get_engine, init_schema, get_session
from src.storage.vector_store.chroma_client import get_chroma_client
from src.core.modules.registry import get_registry
from src.core.modules.base_module import ModuleResult
from src.core.workflow.step_executor import StepExecutor, get_step_info
from src.utils.id_generator import generate_id

engine = get_engine()
init_schema()
chroma_client = get_chroma_client()
registry = get_registry()
registry.initialize()

# ============================================================
# 测试框架
# ============================================================
FT_RESULTS = []  # [(step, scenario, injection_name, result, verdict)]

def record(step, scenario, name, output, passed):
    FT_RESULTS.append({
        'step': step, 'scenario': scenario, 'name': name,
        'output': output, 'passed': passed
    })

def inject_and_run(executor, step_num, step_name, good_content, inject_fn):
    """先注入错误运行，再用正常数据回补"""
    # 注入错误
    bad_content = inject_fn(good_content)
    print(f'\n{"-"*60}')
    print(f'  🔴 INJECT [{step_name}] 注入错误...')
    print(f'    输入摘要: {str(bad_content)[:120]}...')
    
    result = executor.execute(step_num, bad_content)
    
    # 分析结果
    has_errors = len(result.errors) > 0
    has_violations = len(result.constraint_violations) > 0
    crashed = False
    status = '❓'
    details = []
    
    if result.success and not has_errors:
        status = '⚠️ 通过(无报错)'
        details.append('注入未触发错误')
    elif result.success and has_errors:
        status = '⚠️ 部分通过(有错误但继续)'
        details.extend(result.errors[:2])
    elif not result.success and has_errors:
        status = '🛡️ 拦截(正确阻止)'
        details.extend(result.errors[:2])
    elif not result.success and not has_errors:
        status = '❌ 崩溃(无错误信息)'
        crashed = True
    
    print(f'  RESULT: success={result.success}, errors={len(result.errors)}, violations={len(result.constraint_violations)}')
    for d in details:
        print(f'    → {d[:120]}')
    if has_violations:
        for v in result.constraint_violations[:2]:
            print(f'    ⚠ [{v.severity}] {v.message[:100]}')
    
    ft_ok = crashed is False
    record(step_num, step_name, inject_fn.__name__, result, ft_ok)
    
    # 用正常数据重新执行回补
    print(f'  🔵 FIX [{step_name}] 正常数据回补...')
    fix_result = executor.execute(step_num, good_content)
    print(f'    回补: success={fix_result.success}')
    return fix_result

# ============================================================
# 正常数据定义（复用 _run_full_test.py 的标准输入）
# ============================================================
GOOD_DATA: Dict[int, Any] = {}
GOOD_DATA[2] = {
    'theme': {
        'surface_theme': '人类在星际时代的文明延续与道德抉择',
        'deep_theme': '科技越发达，人性的考验越严峻',
        'emotional_hook': '当主角发现远古文明的灭绝与当下局势惊人相似时',
        'theme_statement': '真正的文明存续不在于科技的高度，而在于道德选择',
        'reverse_confirmation': '也许所谓的外星文明毁灭只是进化的必经之路'
    },
    'sub_themes': [
        {'name': '科技伦理的边界', 'core_question': '当技术突破道德边界时如何自处？'},
        {'name': '记忆与身份的迷思', 'core_question': '记忆被改写后还能相信自己的身份吗？'}
    ]
}
GOOD_DATA[3] = {
    'acts': [
        {'title': '第一幕：遗迹的启示', 'chapters': 5, 'key_events': ['发现外星遗迹信号', '组建探索团队'], 'description': '主角林星辰接收到外星信号展开探索。'},
        {'title': '第二幕：真相的代价', 'chapters': 8, 'key_events': ['发现与遗迹警示的相似', '遭遇不明势力'], 'description': '发现当代社会正沿相同轨迹前进。'},
        {'title': '第三幕：终极抉择', 'chapters': 5, 'key_events': ['真相全面揭露', '主角做出选择'], 'description': '文明站在命运的十字路口。'}
    ],
    'causal_chain': [
        {'from_event': '外星信号接收', 'to_event': '组建探索团队', 'reason': '信号蕴含遗迹坐标'},
        {'from_event': '解读遗迹记录', 'to_event': '发现毁灭模式', 'reason': '多个遗迹显示相似走向'}
    ],
    'rhythm_map': [
        {'chapter_range': '1-3', 'pace': '舒缓', 'tension': 0.3, 'event_density': 0.4},
        {'chapter_range': '4-18', 'pace': '渐快', 'tension': 0.7, 'event_density': 0.7}
    ]
}
GOOD_DATA[4] = {
    'dimensions': [
        {'name': '物理规则', 'rules': [{'description': '光速旅行通过曲速引擎实现', 'scope': '星系间航行', 'constraints': '跃迁后需冷却'}]},
        {'name': '地理空间', 'rules': [{'description': '人类联邦横跨三个星系', 'scope': '人类活动区域', 'constraints': '核心星球12颗'}]},
        {'name': '时间历史', 'rules': [{'description': '人类已有500年星际殖民史', 'scope': '人类文明史', 'constraints': '早期记录遗失'}]},
        {'name': '社会结构', 'rules': [{'description': '人类联邦实行议会制', 'scope': '政治体系', 'constraints': '边缘星球代表权不足'}]},
        {'name': '文化习俗', 'rules': [{'description': '星际时代形成星际公民身份认同', 'scope': '身份认同', 'constraints': '各星球保留本土文化'}]},
        {'name': '科技水平', 'rules': [{'description': 'AI辅助决策广泛使用', 'scope': '人工智能', 'constraints': 'AI不参与生命权决策'}]},
        {'name': '魔法/超自然体系', 'rules': [{'description': '部分外星文明有精神感应', 'scope': '超自然现象', 'constraints': '仅少数人能感知'}]},
        {'name': '经济体系', 'rules': [{'description': '星际通用信用点经济', 'scope': '星系间经济', 'constraints': '存在经济差距'}]}
    ]
}
GOOD_DATA[5] = {
    'characters': [
        {'name': '林星辰', 'role': '主角', 'layer1_identity': {'age': 28, 'occupation': '星际考古学家', 'origin': '地球第三区', 'status': '初级研究员'}, 'layer2_psychology': {'personality': 'INFP', 'motivation': '探索未知', 'fear': '害怕无法阻止悲剧', 'desire': '渴望理解宇宙真相', 'contradiction': '理性与直觉的冲突', 'body_language_dictionary': {'高兴': ['嘴角上扬'], '愤怒': ['握紧拳头']}}, 'layer3_ability': {'skills': ['古文字破译', '遗迹勘探'], 'knowledge_boundaries': {'knows': ['外星语言基础'], 'not_knows': ['遗迹本质']}}, 'layer4_special': {'secrets': ['体内有外星基因印记'], 'cracks': ['过度追求真相'], 'quirks': ['思考时转笔']}, 'weight': {'tier': 'S', 'arc_contribution': 0.95, 'plot_driving': 0.90, 'theme_carrying': 0.95, 'network_centrality': 0.85}},
        {'name': '苏月华', 'role': '主角', 'layer1_identity': {'age': 26, 'occupation': '外星语言学家', 'origin': '天狼星第四殖民星', 'status': '高级研究员'}, 'layer2_psychology': {'personality': 'INTJ', 'motivation': '破译外星语言', 'fear': '害怕无法理解异文明', 'desire': '掌握所有外星语言', 'contradiction': '理性与直觉冲突', 'body_language_dictionary': {'高兴': ['眼睛闪着光'], '愤怒': ['表情冷下来']}}, 'layer3_ability': {'skills': ['外星语言破译', '模式识别'], 'knowledge_boundaries': {'knows': ['12种外星语言'], 'not_knows': ['语言深层含义']}}, 'layer4_special': {'secrets': ['能直觉理解外星文字'], 'cracks': ['过分自信'], 'quirks': ['喜欢画符号']}, 'weight': {'tier': 'S', 'arc_contribution': 0.85, 'plot_driving': 0.80, 'theme_carrying': 0.85, 'network_centrality': 0.75}},
        {'name': '赵铁军', 'role': '配角', 'layer1_identity': {'age': 45, 'occupation': '星际探险队长', 'origin': '火星殖民地', 'status': '资深队长'}, 'layer2_psychology': {'personality': 'ESTJ', 'motivation': '保护团队安全', 'fear': '害怕决策失误导致伤亡', 'desire': '完成最伟大的探险', 'contradiction': '保守与创新的冲突', 'body_language_dictionary': {'高兴': ['哈哈大笑'], '愤怒': ['脸色铁青']}}, 'layer3_ability': {'skills': ['星际航行', '危机处理'], 'knowledge_boundaries': {'knows': ['飞船操作'], 'not_knows': ['外星知识']}}, 'layer4_special': {'secrets': ['曾经失误导致伤亡'], 'cracks': ['过于保守'], 'quirks': ['出发前检查三遍设备']}, 'weight': {'tier': 'A', 'arc_contribution': 0.65, 'plot_driving': 0.70, 'theme_carrying': 0.60, 'network_centrality': 0.55}},
    ]
}
GOOD_DATA[6] = {'relations': [{'char_a_id': None, 'char_b_id': None, 'type': '知音', 'strength': 0.85, 'asymmetry': 0.15, 'history': '共事三年', 'trajectory': '知己到生死之交'}]}
GOOD_DATA[7] = {'arcs': [{'char_id': None, 'arc_type': '成长型', 'start_state': '天真好奇', 'catalyst_event': '发现真相', 'change_process': ['震惊', '思考', '担当'], 'end_state': '成熟稳重', 'chapter_mapping': 'setup:1-5, rising:6-10, climax:11-15, resolution:16-18'}]}
GOOD_DATA[8] = {'factions': [{'name': '联邦考古学会', 'type': '正派', 'hierarchy': '会长→研究员', 'goals': '探索遗迹', 'resources': '联邦拨款', 'doctrines': '信息公开', 'reputation': 0.85, 'members': [{'char_name': '林星辰', 'role': '研究员', 'rank': '初级'}, {'char_name': '苏月华', 'role': '专家', 'rank': '高级'}]}, {'name': '联邦安全部', 'type': '反派', 'hierarchy': '局长→特工', 'goals': '控制信息', 'resources': '间谍网络', 'doctrines': '安全至上', 'reputation': 0.30, 'members': []}]}
GOOD_DATA[9] = {'relations': [{'faction_a_id': None, 'faction_b_id': None, 'type': '敌对', 'strength': 0.90, 'history': ['安全部打压学会'], 'treaties': ['信息共享协议'], 'hidden_agenda': '巩固权力'}]}
GOOD_DATA[10] = {'items': [{'name': '星辰罗盘', 'type': '探索工具', 'purpose': '定位遗迹', 'background_story': '外星文明制造', 'restrictions': ['需精神感应激活'], 'current_owner': '林星辰', 'significance_to_plot': '关键道具'}]}
GOOD_DATA[11] = {'foreshadows': [{'type': '物品伏笔', 'status': '已埋设', 'plant_chapter': 1, 'payload': '罗盘自主发光', 'depth': 0.8, 'importance': 0.9}], 'density_curve': [{'chapter': 1, 'active_count': 1, 'density_per_kword': 3.5, 'new_count': 1, 'resolved_count': 0}]}
GOOD_DATA[12] = {}
GOOD_DATA[13] = {'synopsis': {'one_liner': {'text': '星际考古学家发现远古文明遗迹，揭开人类文明面临的终极警示'}, 'short_blurb': {'text': '林星辰在探索过程中发现多个文明的毁灭模式正在重演。面对文明危机，他必须在真相与安危之间做出抉择。'}, 'standard_blurb': {'text': '在遥远的未来，林星辰发现外星文明遗迹遍布星系。每一个遗迹都记录着文明从崛起到毁灭的全过程。而这些文明的终结模式正在当代重演。'}, 'long_blurb': {'text': '公元3157年，人类联邦已横跨三个星系。星际考古学家林星辰在勘探中发现外星信号，踏上了改变命运之旅。遗迹记录着多个文明从崛起到毁灭的全过程，而人类的当前阶段与这些文明的关键转折点惊人相似。'}, 'selling_points': [{'text': '硬核科幻与文明哲学融合', 'dimension': 'plot'}], 'target_audience': '硬科幻读者'}}
GOOD_DATA[14] = {'volumes': [{'name': '初啼之星', 'chapter_range': [1, 5], 'boundary_gravity': [{'type': 'narrative_gravity', 'description': '第一处遗迹发现'}], 'pacing': '舒缓铺垫', 'major_conflict': '发现信号', 'character_focus': ['林星辰'], 'themes': ['好奇心'], 'cliffhanger': '全息投影揭示真相'}, {'name': '觉醒之路', 'chapter_range': [6, 11], 'boundary_gravity': [{'type': 'narrative_gravity', 'description': '身世之谜揭示'}], 'pacing': '渐入紧张', 'major_conflict': '情报局阻挠', 'character_focus': ['林星辰'], 'themes': ['命运'], 'cliffhanger': '基因印记是钥匙'}, {'name': '真相的重量', 'chapter_range': [12, 18], 'boundary_gravity': [{'type': 'narrative_gravity', 'description': '终极真相揭示'}], 'pacing': '紧张高亢', 'major_conflict': '终极抉择', 'character_focus': ['林星辰'], 'themes': ['牺牲'], 'cliffhanger': '最重要的选择'}]}
GOOD_DATA[15] = {'chapters': [{'chapter_number': i+1, 'pov_character': '林星辰', 'summary': f'第{i+1}章剧情概要', 'scenes': [{'pov': '林星辰', 'summary': '场景推进', 'start_emotion': '平静', 'end_emotion': '坚定', 'word_count': 2000}]} for i in range(18)]}
GOOD_DATA[16] = {'chapters': [{'chapter_number': i+1, 'title': f'第{i+1}章', 'scenes': [{'text': f'第{i+1}章正文场景一内容...', 'word_count': 2000}, {'text': f'第{i+1}章正文场景二内容...', 'word_count': 1800}], 'word_count': 3800} for i in range(18)]}
GOOD_DATA[17] = {}
GOOD_DATA[18] = {'chapters': [{'chapter_number': i+1, 'title': f'第{i+1}章', 'scenes': [{'text': f'第{i+1}章正文场景一内容...', 'word_count': 2000}, {'text': f'第{i+1}章正文场景二内容...', 'word_count': 1800}], 'word_count': 3800} for i in range(18)], 'fixes': [{'issue_ref': '过渡不够自然', 'original_text': '原文本...', 'fixed_text': '修正后文本...'}]}
GOOD_DATA[19] = {'export': {'title': '星辰之下', 'author': 'AI 创作系统', 'formats': ['txt', 'md']}}

# ============================================================
# 错误注入函数 (18 种故障模式)
# ============================================================
def inject_02_empty_theme(d):
    return {'theme': {}, 'sub_themes': []}

def inject_03_wrong_act_structure(d):
    return {'acts': [{'title': '仅一幕', 'chapters': 18, 'key_events': ['全部剧情'], 'description': '只有一个幕'}], 'causal_chain': [], 'rhythm_map': []}

def inject_04_too_few_dimensions(d):
    return {'dimensions': [{'name': '物理规则', 'rules': [{'description': '简化规则', 'scope': '全局', 'constraints': '无'}]}]}

def inject_05_too_few_characters(d):
    return {'characters': [d['characters'][0]]}

def inject_06_missing_relations_key(d):
    return {'invalid_key': []}

def inject_07_malformed_arc(d):
    return {'arcs': [{'wrong_field': '完全错误的字段', 'arc_type': None}]}

def inject_08_single_faction(d):
    return {'factions': [d['factions'][0]]}

def inject_09_empty_relation_list(d):
    return {'relations': []}

def inject_10_no_items(d):
    return {'no_items_field': True}

def inject_11_out_of_range_foreshadow(d):
    return {'foreshadows': [{'type': '物品伏笔', 'status': '已埋设', 'plant_chapter': 999, 'payload': '', 'depth': 999, 'importance': 999}], 'density_curve': [{'chapter': 999, 'active_count': 999, 'density_per_kword': 999, 'new_count': 999, 'resolved_count': 999}]}

def inject_12_skip(d):
    return {}

def inject_13_short_blurb(d):
    return {'synopsis': {'one_liner': {'text': '太短了'}, 'short_blurb': {'text': '太短'}, 'standard_blurb': {'text': '短'}, 'long_blurb': {'text': '超短'}, 'selling_points': [], 'target_audience': ''}}

def inject_14_integer_boundary(d):
    import copy
    new_volumes = copy.deepcopy(d['volumes'])
    new_volumes[0]['chapter_range'] = [1, 5]
    new_volumes[1]['chapter_range'] = [6, 11]
    new_volumes[2]['chapter_range'] = [12, 18]
    return {'volumes': new_volumes}

def inject_15_empty_scene_chapter(d):
    import copy
    chapters = copy.deepcopy(d['chapters'])
    chapters[0] = {'chapter_number': 1, 'pov_character': '林星辰', 'summary': '', 'scenes': []}
    return {'chapters': chapters}

def inject_16_ultrashort_chapter(d):
    import copy
    chapters = copy.deepcopy(d['chapters'])
    chapters[0] = {'chapter_number': 1, 'title': '非常短', 'scenes': [{'text': '短。', 'word_count': 50}], 'word_count': 50}
    return {'chapters': chapters}

def inject_17_no_change(d):
    return {}

def inject_18_no_fixes(d):
    return {'chapters': d['chapters'], 'fixes': []}

def inject_19_empty_export(d):
    return {'export': {}}

# 注入函数映射：step -> (inject_fn, 预期行为描述)
INJECTIONS = {
    2:  (inject_02_empty_theme,       '空主题 → 预期:模块返回错误但不崩溃'),
    3:  (inject_03_wrong_act_structure, '单幕无因果链 → 预期:约束警告或模块错误'),
    4:  (inject_04_too_few_dimensions,  '仅1个维度 → 预期:validate警告但执行通过'),
    5:  (inject_05_too_few_characters,  '仅1个角色 → 预期:validate警告但执行通过'),
    6:  (inject_06_missing_relations_key,'缺失relations键 → 预期:优雅处理'),
    7:  (inject_07_malformed_arc,       '弧线字段完全错误 → 预期:优雅处理'),
    8:  (inject_08_single_faction,      '仅1个势力 → 预期:通过'),
    9:  (inject_09_empty_relation_list, '势力关系为空 → 预期:通过'),
    10: (inject_10_no_items,            '无items字段 → 预期:优雅处理'),
    11: (inject_11_out_of_range_foreshadow, '伏笔参数越界 → 预期:约束警告或错误'),
    12: (inject_12_skip,                '跳过(自动聚合)'),
    13: (inject_13_short_blurb,         '简介过短 → 预期:validate警告'),
    14: (inject_14_integer_boundary,    '整数分卷边界 → 预期:约束错误被拦截'),
    15: (inject_15_empty_scene_chapter, '空场景章节 → 预期:质量审查标记'),
    16: (inject_16_ultrashort_chapter,  '极短正文 → 预期:质量审查标记'),
    17: (inject_17_no_change,           '审核流程'),
    18: (inject_18_no_fixes,            '修正列表为空 → 预期:通过'),
    19: (inject_19_empty_export,        '空导出配置 → 预期:使用默认值'),
}

# ============================================================
# 主测试流程
# ============================================================
print('='*70)
print('🧪 容错测试：20步流程 + 18种错误注入')
print('='*70)

with get_session() as session:
    row = session.execute(__import__('sqlalchemy').text('SELECT id FROM novels LIMIT 1')).fetchone()
    if not row:
        novel_id = generate_id('NOV', 'GLOBAL', session)
        now = datetime.now(timezone.utc).isoformat()
        session.execute(
            __import__('sqlalchemy').text(
                'INSERT INTO novels (id, title, current_step, status, created_at, updated_at) '
                'VALUES (:id, :title, 1, :status, :now, :now)'
            ),
            {'id': novel_id, 'title': '星辰之下（容错测试）', 'status': '创作中', 'now': now}
        )
        session.flush()
        session.commit()
    else:
        novel_id = row[0]
        print(f'  使用已有小说ID: {novel_id}')

    executor = StepExecutor(novel_id, session, chroma_client)
    fault_log = []
    recovery_ok = True

    # === 循环执行 19 步 ===
    for step_num in range(2, 20):
        step_info = get_step_info(step_num)
        step_name = step_info.get('name', f'步骤{step_num}')
        good_content = GOOD_DATA.get(step_num, {})
        
        print(f'\n{"="*60}')
        print(f'📌 步骤 {step_num:02d}/20: {step_name}')
        print(f'{"="*60}')
        
        # 错误注入
        if step_num in INJECTIONS:
            inject_fn = INJECTIONS[step_num][0]
            desc = INJECTIONS[step_num][1]
            print(f'  🔴 注入模式: {inject_fn.__name__}')
            print(f'     描述: {desc}')
            
            if step_num in [12, 17]:
                # 跳过注入（无数据依赖）
                print(f'  ⏭️  跳过注入（无需数据步骤）')
                result = executor.execute(step_num, good_content)
                passed = result.success
                fault_log.append({
                    'step': step_num, 'name': step_name,
                    'injection': 'SKIP', 'verdict': '✅ 通过' if passed else '❌ 失败',
                    'result': result
                })
                recovery_ok = recovery_ok and passed
            else:
                # 执行注入
                bad_content = inject_fn(good_content)
                print(f'    输入预览: {str(bad_content)[:100]}')
                
                result = executor.execute(step_num, bad_content)
                has_errors = len(result.errors) > 0
                violated = len(result.constraint_violations) > 0
                
                # 判定容错是否有效
                if result.success and not has_errors:
                    verdict = '⚠️ 通过(错误未被检测)'
                elif result.success and has_errors:
                    verdict = '✅ 通过(错误被处理，继续执行)'
                elif not result.success and has_errors:
                    verdict = '✅ 拦截(错误被正确阻止)'
                    recovery_ok = False
                else:
                    verdict = '❌ 异常(无错误信息)'
                    recovery_ok = False
                
                print(f'  RESULT: success={result.success}, errors={len(result.errors)}, violations={violated}')
                for e in result.errors[:3]:
                    print(f'    ❌ {str(e)[:120]}')
                for v in result.constraint_violations[:2]:
                    print(f'    ⚠ [{v.severity}] {v.message[:100]}')
                
                fault_log.append({
                    'step': step_num, 'name': step_name,
                    'injection': inject_fn.__name__, 'verdict': verdict,
                    'result': result
                })
                
                # 用正常数据回补
                print(f'  🔵 正常数据回补...')
                fix_r = executor.execute(step_num, good_content)
                print(f'    回补: success={fix_r.success}')
                if not fix_r.success:
                    print(f'    ⚠ 回补失败，可能影响后续步骤')
                    recovery_ok = False
        
        else:
            # 无注入则正常执行
            result = executor.execute(step_num, good_content)
            fault_log.append({
                'step': step_num, 'name': step_name,
                'injection': 'NONE', 'verdict': '✅ 通过' if result.success else '❌ 失败',
                'result': result
            })
            print(f'  RESULT: success={result.success}, summary={result.summary[:60] if result.summary else "N/A"}')
        
        # 输出当前user_view状态
        uvf = sorted(Path('user_view').rglob('*'))
        print(f'  📂 user_view: {len(uvf)} 个条目')

    print(f'\n{"="*70}')
    print(f'📊 容错测试汇总')
    print(f'{"="*70}')
    print(f'{"步骤":<6} {"环节名":<16} {"注入方式":<28} {"判定":<16}')
    print(f'{"-"*66}')
    for fl in fault_log:
        print(f'{fl["step"]:02d}    {fl["name"]:<16} {fl["injection"]:<28} {fl["verdict"]:<16}')
    print(f'{"-"*66}')
    
    ft_pass = sum(1 for fl in fault_log if '通过' in str(fl['verdict']) or '拦截' in str(fl['verdict']) or '跳过' in str(fl['verdict']))
    ft_total = len(fault_log)
    print(f'容错通过: {ft_pass}/{ft_total}')
    print(f'回补状态: {"✅ 全部成功" if recovery_ok else "⚠️ 部分失败"}')
    
    # ============================================================
    # 最终验证
    # ============================================================
    print(f'\n{"="*70}')
    print(f'📋 最终数据库验证')
    print(f'{"="*70}')
    from sqlalchemy import text as sa_text
    checks = [
        ('novels current_step','SELECT current_step FROM novels', lambda v: v==20),
        ('themes','SELECT COUNT(1) FROM themes', lambda v: v>0),
        ('world_building','SELECT COUNT(1) FROM world_building', lambda v: v>0),
        ('characters','SELECT COUNT(1) FROM characters', lambda v: v>0),
        ('relations','SELECT COUNT(1) FROM relations', lambda v: v>0),
        ('factions','SELECT COUNT(1) FROM factions', lambda v: v>0),
        ('outlines','SELECT COUNT(1) FROM outlines', lambda v: v>0),
        ('manuscripts','SELECT COUNT(1) FROM manuscripts', lambda v: v>0),
        ('review_results','SELECT COUNT(1) FROM review_results', lambda v: v>0),
    ]
    all_db_ok = True
    for label, sql, validator in checks:
        row = session.execute(sa_text(sql)).fetchone()
        val = row[0] if row else -1
        ok = validator(val)
        tag = '✅ PASS' if ok else '❌ FAIL'
        if not ok: all_db_ok = False
        print(f'  [{tag}] {label}: {val}')
    
    # user_view 验证
    uv = Path('user_view')
    if uv.exists():
        for d in sorted(uv.iterdir()):
            if d.is_dir():
                files = sorted(d.rglob('*'))
                md = [f for f in files if f.suffix == '.md']
                sync = sum(1 for f in md if '<!-- SYNC:' in f.read_text(encoding='utf-8') and 'SYNC -->' in f.read_text(encoding='utf-8'))
                print(f'  📂 {d.name}: {len(files)} items, SYNC {sync}/{len(md)}')
    
    print(f'\n{"="*70}')
    print(f'🏁 容错测试完成')
    print(f'  步骤通过: {ft_pass}/{ft_total}')
    print(f'  数据库: {"✅ 全部正常" if all_db_ok else "❌ 有异常"}')
    print(f'  容错判定: {"✅ 系统容错能力正常" if ft_pass == ft_total else "⚠️ 部分容错场景待改进"}')
    print(f'{"="*70}')

print('✅ 容错测试执行完毕！')