"""20 步完整流程测试脚本"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['PAGER'] = 'cat'
from pathlib import Path
from datetime import datetime, timezone

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
            {'id': novel_id, 'title': '星辰之下', 'status': '创作中', 'now': now}
        )
        session.flush()
    else:
        novel_id = row[0]

    executor = StepExecutor(novel_id, session, chroma_client)
    results_log = []

    def run_step(step_num, step_name, content, extra_checks=None):
        print(f'\n{"="*60}')
        print(f'📝 步骤 {step_num:02d}/20: {step_name}')
        print(f'{"="*60}')
        result = executor.execute(step_num, content)
        print(f'  result.success = {result.success}')
        print(f'  result.summary = {result.summary}')
        if result.errors:
            for e in result.errors:
                print(f'  ⚠ {e}')
        if result.sync_status:
            print(f'  result.sync_status = {result.sync_status}')
        checks = {}
        checks[f'{step_num:02d}-1'] = '✅ 通过' if result.success else '❌ 不通过'
        if extra_checks:
            checks.update(extra_checks)
        uvf = sorted(Path('user_view').rglob('*'))
        print(f'  📂 user_view: {len(uvf)} 个条目')
        all_pass = all('✅' in v for v in checks.values())
        print(f'  📋 步骤 {step_num:02d} 判定: {"✅ 通过" if all_pass else "❌ 不通过"}')
        results_log.append({'step': step_num, 'name': step_name, 'success': result.success, 'checks': checks, 'passed': all_pass})
        return result

    # === 步骤 02 ===
    r2 = run_step(2, '小说主题', {
        'theme': {
            'surface_theme': '人类在星际时代的文明延续与道德抉择',
            'deep_theme': '科技越发达，人性的考验越严峻——每一个文明的终结都是对另一个文明的警示',
            'emotional_hook': '当主角发现远古文明的灭绝与当下局势惊人相似时，那种毛骨悚然的宿命感',
            'theme_statement': '真正的文明存续不在于科技的高度，而在于能否在道德困境中做出正确的选择',
            'reverse_confirmation': '也许所谓的外星文明毁灭只是进化的必经之路，而我们终将超越恐惧'
        },
        'sub_themes': [
            {'name': '科技伦理的边界', 'core_question': '当技术能够突破道德边界时，人类应该如何自处？'},
            {'name': '记忆与身份的迷思', 'core_question': '如果记忆可以被读取和改写，我们还能相信自己的身份吗？'},
            {'name': '文明循环的宿命', 'core_question': '每一个文明是否注定要重复前人的错误，直到彻底觉醒？'}
        ]
    })

    # === 步骤 03 ===
    r3 = run_step(3, '拟定大纲', {
        'acts': [
            {'title': '第一幕：遗迹的启示', 'chapters': 5,
             'key_events': ['发现外星遗迹信号', '组建探索团队', '解读第一个遗迹记录', '发现文明毁灭的共同模式', '决定深入调查'],
             'description': '主角林星辰意外接收到来自宇宙深处的外星信号，由此展开一场跨越星系的考古探索。'},
            {'title': '第二幕：真相的代价', 'chapters': 8,
             'key_events': ['发现当代社会与遗迹警示的惊人相似', '遭遇不明势力的阻挠', '团队内部出现分歧', '主角发现身世与外星文明有关', '揭开终极真相'],
             'description': '随着调查深入，主角发现当代人类社会正沿着与那些毁灭文明相同的轨迹前进。'},
            {'title': '第三幕：终极抉择', 'chapters': 5,
             'key_events': ['终极真相全面揭露', '人类面临文明转折点', '主角必须做出选择', '道德与生存的终极考验', '结局揭晓'],
             'description': '真相全面揭露后，人类文明站在了命运的十字路口。主角必须做出影响整个文明走向的终极选择。'}
        ],
        'causal_chain': [
            {'from_event': '外星信号接收', 'to_event': '组建探索团队', 'reason': '信号蕴含的信息表明这是外星文明的遗迹坐标'},
            {'from_event': '解读遗迹记录', 'to_event': '发现毁灭模式', 'reason': '多个遗迹记录显示相似的历史走向'},
            {'from_event': '发现毁灭模式', 'to_event': '与当代对比', 'reason': '当代社会呈现出相同的危险征兆'},
            {'from_event': '真相揭露', 'to_event': '主角面临抉择', 'reason': '主角发现自己是唯一能改变历史走向的关键人物'}
        ],
        'rhythm_map': [
            {'chapter_range': '1-3', 'pace': '舒缓', 'tension': 0.3, 'event_density': 0.4},
            {'chapter_range': '4-5', 'pace': '渐快', 'tension': 0.5, 'event_density': 0.6},
            {'chapter_range': '6-10', 'pace': '紧凑', 'tension': 0.7, 'event_density': 0.7},
            {'chapter_range': '11-13', 'pace': '紧张', 'tension': 0.85, 'event_density': 0.8},
            {'chapter_range': '14-18', 'pace': '高亢', 'tension': 0.9, 'event_density': 0.9}
        ]
    })

    ob_cls = get_registry().get('outline_builder')
    if ob_cls:
        ob = ob_cls()
        mr = ModuleResult(data=r3.module_data or {})
        ob_issues = ob.validate(mr)
        print(f'\n[03-4 模块validate] 三幕+因果链: {"✅ 通过" if len(ob_issues)==0 else "⚠ "+str(ob_issues[:3])}')

    # === 步骤 04 ===
    r4 = run_step(4, '世界观设定', {
        'dimensions': [
            {'name': '物理规则', 'rules': [
                {'description': '光速旅行通过曲速引擎实现', 'scope': '星系间航行', 'constraints': '曲速引擎消耗大量能量，每次跃迁后需冷却'},
                {'description': '量子纠缠通讯为跨星系实时通讯提供可能', 'scope': '跨星系通讯', 'constraints': '需建立量子中继站，距离越远信号衰减越严重'}
            ]},
            {'name': '地理空间', 'rules': [
                {'description': '人类联邦横跨三个星系，包含百余颗殖民星球', 'scope': '人类活动区域', 'constraints': '核心星球12颗，边缘星球与中央存在信息差'},
                {'description': '外星遗迹多分布在危险区域', 'scope': '探索区域', 'constraints': '遗迹周围常有未知能量场干扰'}
            ]},
            {'name': '时间历史', 'rules': [
                {'description': '人类已有500年星际殖民史', 'scope': '人类文明史', 'constraints': '早期殖民记录大量遗失'},
                {'description': '至少存在三个已毁灭的外星文明', 'scope': '外星文明史', 'constraints': '毁灭时间跨度在10万年至5000年前'}
            ]},
            {'name': '社会结构', 'rules': [
                {'description': '人类联邦实行议会制，由12个核心星球代表组成', 'scope': '政治体系', 'constraints': '边缘星球在议会中代表权不足'},
                {'description': '考古学会为独立学术机构，不受联邦直接管辖', 'scope': '学术体系', 'constraints': '资金来源受联邦制约'}
            ]},
            {'name': '文化习俗', 'rules': [
                {'description': '星际时代形成星际公民身份认同', 'scope': '身份认同', 'constraints': '各星球仍保留本土文化传统'},
                {'description': '考古发现被视为文明瑰宝', 'scope': '文化价值观', 'constraints': '部分信息被联邦列为机密'}
            ]},
            {'name': '科技水平', 'rules': [
                {'description': 'AI辅助决策广泛使用，但重大决策保留人类最终决定权', 'scope': '人工智能', 'constraints': 'AI不得参与涉及生命权的决策'},
                {'description': '基因编辑技术成熟但受严格管制', 'scope': '生物科技', 'constraints': '仅限医疗用途，严禁优生学应用'}
            ]},
            {'name': '魔法/超自然体系', 'rules': [
                {'description': '部分外星文明遗留了类似精神感应的能力', 'scope': '超自然现象', 'constraints': '仅少数人能够感知且使用有限'},
                {'description': '遗迹中存在未知的能量场', 'scope': '未知现象', 'constraints': '能量场对电子设备有干扰作用'}
            ]},
            {'name': '经济体系', 'rules': [
                {'description': '星际通用信用点为基础的经济体系', 'scope': '星系间经济', 'constraints': '边缘星球与核心星球存在经济差距'},
                {'description': '考古发现可为持有人带来巨大经济利益', 'scope': '文物经济', 'constraints': '利益驱动导致黑市交易'}
            ]}
        ]
    })

    wb_cls = get_registry().get('world_builder')
    if wb_cls:
        wb = wb_cls()
        mr = ModuleResult(data=r4.module_data or {})
        wb_issues = wb.validate(mr)
        print(f'\n[04-4 模块validate] 世界观维度: {"✅ 通过" if len(wb_issues)==0 else "⚠ "+str(wb_issues[:3])}')

    # === 步骤 05 ===
    r5 = run_step(5, '人物设定', {
        'characters': [
            {'name': '林星辰', 'role': '主角',
             'layer1_identity': {'age': 28, 'occupation': '星际考古学家', 'origin': '地球第三区', 'status': '联邦考古学会初级研究员'},
             'layer2_psychology': {'personality': 'INFP', 'motivation': '探索未知，为人类文明寻找历史答案', 'fear': '害怕人类重蹈覆辙却无力阻止', 'desire': '渴望理解宇宙的终极真相', 'contradiction': '理性与直觉的冲突',
               'body_language_dictionary': {'高兴': ['嘴角不自觉上扬', '眼睛微微眯起'], '愤怒': ['额头青筋暴起', '握紧拳头'], '悲伤': ['眼眶泛红', '低头沉默'], '恐惧': ['瞳孔微微放大', '后退半步'], '惊讶': ['眉毛猛地扬起', '倒吸一口凉气']}},
             'layer3_ability': {'skills': ['古文字破译', '遗迹勘探技术', '量子通讯操作', '星际导航'], 'knowledge_boundaries': {'knows': ['外星语言基础知识', '遗迹能量场特征', '星际地理'], 'not_knows': ['遗迹能量的本质', '自己的真实身世', '联邦高层的秘密计划']}},
             'layer4_special': {'secrets': ['体内有外星文明的基因印记', '能够感应遗迹的能量波动'], 'cracks': ['过度追求真相导致偏执', '不相信队友的建议'], 'quirks': ['喜欢在思考时转笔', '对古代文字有特殊共鸣']},
             'weight': {'tier': 'S', 'arc_contribution': 0.95, 'plot_driving': 0.90, 'theme_carrying': 0.95, 'network_centrality': 0.85}},
            {'name': '苏月华', 'role': '主角',
             'layer1_identity': {'age': 26, 'occupation': '外星语言学家', 'origin': '天狼星第四殖民星', 'status': '语言研究所高级研究员'},
             'layer2_psychology': {'personality': 'INTJ', 'motivation': '破译所有外星语言，建立宇宙语言谱系', 'fear': '害怕永远无法理解异文明的思维方式', 'desire': '成为第一个完全掌握外星语言的人类', 'contradiction': '理性分析与本能的语言直觉冲突',
               'body_language_dictionary': {'高兴': ['眼睛闪着光', '语速变快'], '愤怒': ['表情冷下来', '话语变得尖刻'], '悲伤': ['咬着下唇', '目光失焦'], '恐惧': ['身体微微后倾', '声音发颤'], '惊讶': ['眨了眨眼睛', '手中的笔掉在桌上']}},
             'layer3_ability': {'skills': ['多种外星语言破译', '模式识别', '密码学', '文化人类学分析'], 'knowledge_boundaries': {'knows': ['12种外星语言', '文明发展模式理论', '符号学'], 'not_knows': ['部分语言的深层含义', '语言背后的真实历史', '联邦的语言管制政策']}},
             'layer4_special': {'secrets': ['能够直觉理解部分外星文字的含义'], 'cracks': ['过分自信', '难以与人合作'], 'quirks': ['总是不自觉地在纸上画符号', '喜欢自言自语用外星语言']},
             'weight': {'tier': 'S', 'arc_contribution': 0.85, 'plot_driving': 0.80, 'theme_carrying': 0.85, 'network_centrality': 0.75}},
            {'name': '赵铁军', 'role': '配角',
             'layer1_identity': {'age': 45, 'occupation': '星际探险队长', 'origin': '火星殖民地', 'status': '联邦探险队资深队长'},
             'layer2_psychology': {'personality': 'ESTJ', 'motivation': '保护团队成员安全完成任务', 'fear': '害怕因自己的决策失误导致队员死亡', 'desire': '完成职业生涯最伟大的探险', 'contradiction': '保守经验与创新突破的冲突',
               'body_language_dictionary': {'高兴': ['哈哈大笑', '拍拍对方肩膀'], '愤怒': ['脸色铁青', '压低嗓音说话'], '悲伤': ['深吸一口气', '转过身去'], '恐惧': ['肌肉紧绷', '目光警惕地扫视四周'], '惊讶': ['瞪大了眼睛', '猛地站起来']}},
             'layer3_ability': {'skills': ['星际航行', '危机处理', '团队指挥', '生存技巧'], 'knowledge_boundaries': {'knows': ['各类飞船操作', '星系航线', '应急急救'], 'not_knows': ['外星文明知识', '先进科技原理', '考古学专业知识']}},
             'layer4_special': {'secrets': ['曾经因为失误导致队友伤亡'], 'cracks': ['过于保守', '面对未知事物容易紧张'], 'quirks': ['每次出发前都要检查三遍设备', '喜欢在休息时做木工']},
             'weight': {'tier': 'A', 'arc_contribution': 0.65, 'plot_driving': 0.70, 'theme_carrying': 0.60, 'network_centrality': 0.55}},
            {'name': '伊莎贝拉·陈', 'role': '配角',
             'layer1_identity': {'age': 35, 'occupation': '生物基因工程师', 'origin': '半人马座α星', 'status': '联邦科学院基因工程部主任'},
             'layer2_psychology': {'personality': 'ENTP', 'motivation': '探索基因与文明的深层联系', 'fear': '害怕基因技术被滥用', 'desire': '证明所有文明都有基因上的关联', 'contradiction': '科学伦理与探索欲望的冲突',
               'body_language_dictionary': {'高兴': ['笑得眯起眼睛', '击掌庆祝'], '愤怒': ['脸颊泛红', '语速极快'], '悲伤': ['咬紧牙关', '仰望天花板'], '恐惧': ['脸色苍白', '后退几步'], '惊讶': ['眼镜滑到鼻尖', '张着嘴忘了合上']}},
             'layer3_ability': {'skills': ['基因序列分析', '跨物种基因比对', '生物能量场研究', '实验室管理'], 'knowledge_boundaries': {'knows': ['人类基因组', '外星生物基因特征', '基因编辑技术'], 'not_knows': ['基因与文明关系的真相', '外星科技原理', '联邦的信息屏蔽']}},
             'layer4_special': {'secrets': ['私自保留了外星基因样本'], 'cracks': ['好奇心过重不顾危险', '对规则不够尊重'], 'quirks': ['总是一边做实验一边哼歌', '实验室必须一尘不染']},
             'weight': {'tier': 'A', 'arc_contribution': 0.70, 'plot_driving': 0.65, 'theme_carrying': 0.75, 'network_centrality': 0.60}},
            {'name': '神秘观察者', 'role': '配角',
             'layer1_identity': {'age': '未知', 'occupation': '未知', 'origin': '未知', 'status': '身份成谜的追踪者'},
             'layer2_psychology': {'personality': '未知', 'motivation': '阻止主角团队接近真相', 'fear': '未知', 'desire': '未知', 'contradiction': '未知',
               'body_language_dictionary': {'高兴': ['嘴角浮现诡异的微笑', '眼睛闪过一丝光芒'], '愤怒': ['周围的温度似乎降低', '握紧藏在袖中的武器'], '悲伤': ['眼中闪过一丝哀伤', '转身离去'], '恐惧': ['呼吸变得急促', '手指微微颤抖'], '惊讶': ['瞳孔收缩', '身体僵住了片刻']}},
             'layer3_ability': {'skills': ['高级隐身技术', '精神干扰', '精密暗杀'], 'knowledge_boundaries': {'knows': ['遗迹的真实秘密', '主角的身世', '联邦内部的派系斗争'], 'not_knows': ['自己的真实使命', '幕后主使者的身份']}},
             'layer4_special': {'secrets': ['可能是远古文明的守护者'], 'cracks': ['执行命令从不质疑', '对目标的执念过深'], 'quirks': ['总在阴影中出没', '从不使用电子设备']},
             'weight': {'tier': 'B', 'arc_contribution': 0.50, 'plot_driving': 0.75, 'theme_carrying': 0.55, 'network_centrality': 0.45}}
        ]
    })

    cb_cls = get_registry().get('character_builder')
    if cb_cls:
        cb = cb_cls()
        mr = ModuleResult(data=r5.module_data or {})
        cb_issues = cb.validate(mr)
        print(f'\n[05-4 模块validate] 角色验证: {"✅ 通过" if len(cb_issues)==0 else "⚠ 问题: "+str(cb_issues[:3])}')

    # === 步骤 06 ===
    r6 = run_step(6, '人物关系', {
        'relations': [
            {'char_a_id': None, 'char_b_id': None, 'type': '知音', 'strength': 0.85, 'asymmetry': 0.15, 'history': '林星辰与苏月华在联邦考古学会共事三年', 'trajectory': '从学术知己到生死之交'},
            {'char_a_id': None, 'char_b_id': None, 'type': '师徒', 'strength': 0.75, 'asymmetry': 0.30, 'history': '赵铁军曾是林星辰父亲的老部下', 'trajectory': '从保护到平等互信'},
            {'char_a_id': None, 'char_b_id': None, 'type': '同门', 'strength': 0.70, 'asymmetry': 0.10, 'history': '苏月华与伊莎贝拉因理念相近成为好友', 'trajectory': '学术友谊在冒险中深化'},
            {'char_a_id': None, 'char_b_id': None, 'type': '宿敌', 'strength': 0.60, 'asymmetry': 0.40, 'history': '神秘观察者一直暗中跟踪主角团队', 'trajectory': '从敌对到复杂的亦敌亦友'},
            {'char_a_id': None, 'char_b_id': None, 'type': '传承', 'strength': 0.65, 'asymmetry': 0.35, 'history': '赵铁军对林星辰的照顾源于对林父的承诺', 'trajectory': '从执行承诺到家人般的感情'}
        ]
    })

    # === 步骤 07 ===
    r7 = run_step(7, '角色弧线', {
        'arcs': [
            {'char_id': None, 'arc_type': '成长型', 'start_state': '天真好奇的年轻考古学家', 'catalyst_event': '发现文明毁灭记录', 'change_process': ['震惊于真相', '经历背叛', '学会独立思考', '理解真相的代价', '从被动到主动担当'], 'end_state': '成熟稳重的文明守护者', 'chapter_mapping': 'setup:1-5, rising:6-10, climax:11-15, resolution:16-18'},
            {'char_id': None, 'arc_type': '转变型', 'start_state': '冷静理性的语言学家', 'catalyst_event': '破译语言深层含义', 'change_process': ['理性信念动摇', '相信直觉', '感性与理性平衡', '用心理解世界'], 'end_state': '兼具理性与感性的智慧学者', 'chapter_mapping': 'setup:1-4, rising:5-9, climax:10-14, resolution:15-18'}
        ]
    })

    # === 步骤 08 ===
    r8 = run_step(8, '势力设定', {
        'factions': [
            {'name': '联邦考古学会', 'type': '正派', 'hierarchy': '会长→副院长→主任→研究员→助理', 'goals': '探索文明遗迹', 'resources': '联邦拨款、独立基金', 'doctrines': '知识自由、信息公开', 'reputation': 0.85, 'members': [{'char_name': '林星辰', 'role': '核心研究员', 'rank': '初级研究员'}, {'char_name': '苏月华', 'role': '语言专家', 'rank': '高级研究员'}]},
            {'name': '联邦安全部情报局', 'type': '反派', 'hierarchy': '局长→副局长→处长→特工', 'goals': '控制外星信息，维护统治', 'resources': '安全预算、间谍网络', 'doctrines': '信息即权力、安全高于一切', 'reputation': 0.30, 'members': [{'char_name': '神秘观察者', 'role': '特工', 'rank': '高级特工'}]},
            {'name': '自由探索者联盟', 'type': '中立', 'hierarchy': '盟主→核心成员→外围成员', 'goals': '突破信息封锁', 'resources': '民间捐赠、地下网络', 'doctrines': '真理不可被掩埋', 'reputation': 0.55, 'members': [{'char_name': '伊莎贝拉·陈', 'role': '科学顾问', 'rank': '核心成员'}]}
        ]
    })

    # === 步骤 09 ===
    r9 = run_step(9, '势力关系', {
        'relations': [
            {'faction_a_id': None, 'faction_b_id': None, 'type': '敌对', 'strength': 0.90, 'history': ['安全部多次打压考古学会的信息公开'], 'treaties': ['名义上的信息共享协议'], 'hidden_agenda': '通过控制考古发现巩固权力'},
            {'faction_a_id': None, 'faction_b_id': None, 'type': '合作', 'strength': 0.60, 'history': ['联盟曾为学会提供未公开的遗迹数据'], 'treaties': ['秘密信息共享协议'], 'hidden_agenda': '借助学会的官方身份获取信息'},
            {'faction_a_id': None, 'faction_b_id': None, 'type': '敌对', 'strength': 0.85, 'history': ['安全部多次追捕联盟成员'], 'treaties': ['无'], 'hidden_agenda': '视联盟为威胁联邦稳定的组织'}
        ]
    })

    # === 步骤 10 ===
    r10 = run_step(10, '物品库', {
        'items': [
            {'name': '星辰罗盘', 'type': '探索工具', 'purpose': '定位隐藏的外星遗迹', 'background_story': '由第一个外星文明制造，林星辰在考古挖掘中发现', 'restrictions': ['需特殊精神感应激活', '使用后需24小时充能'], 'current_owner': '林星辰', 'significance_to_plot': '贯穿全书的关键道具'},
            {'name': '文明记忆晶核', 'type': '信息载体', 'purpose': '存储文明完整历史记录', 'background_story': '每个遗迹中心有一颗晶核，记录文明从诞生到毁灭', 'restrictions': ['读取时与读取者精神共鸣', '多次读取可能造成负荷'], 'current_owner': '联邦考古学会', 'significance_to_plot': '揭示文明灭亡模式的关键线索'},
            {'name': '量子护符', 'type': '防护装备', 'purpose': '在遗迹能量场中保护使用者', 'background_story': '来自已消亡文明的科技遗产', 'restrictions': ['能量吸收有上限', '高强度使用后暂时失效'], 'current_owner': '赵铁军', 'significance_to_plot': '保护团队穿过危险能量场'},
            {'name': '基因密钥', 'type': '身份验证工具', 'purpose': '解锁遗迹最深处的秘密', 'background_story': '林星辰体内的外星基因印记是打开终极遗迹的钥匙', 'restrictions': ['只有特定基因序列能激活', '激活后可能有不可逆影响'], 'current_owner': '林星辰（体内）', 'significance_to_plot': '揭开身世之谜和通往最终真相的关键'}
        ]
    })

    # === 步骤 11 ===
    r11 = run_step(11, '伏笔追踪', {
        'foreshadows': [
            {'type': '物品伏笔', 'status': '已埋设', 'plant_chapter': 1, 'payload': '星辰罗盘自主发光', 'depth': 0.8, 'importance': 0.9},
            {'type': '对话伏笔', 'status': '已埋设', 'plant_chapter': 2, 'payload': '赵铁军提到林父死亡原因有蹊跷', 'depth': 0.6, 'importance': 0.7},
            {'type': '事件伏笔', 'status': '已埋设', 'plant_chapter': 3, 'payload': '林星辰读取晶核时出现幻觉', 'depth': 0.7, 'importance': 0.85},
            {'type': '设定伏笔', 'status': '已埋设', 'plant_chapter': 4, 'payload': '能量场对林星辰反应更强烈', 'depth': 0.75, 'importance': 0.8},
            {'type': '角色伏笔', 'status': '已埋设', 'plant_chapter': 5, 'payload': '神秘观察者不出手干扰', 'depth': 0.65, 'importance': 0.75}
        ],
        'density_curve': [
            {'chapter': 1, 'active_count': 1, 'density_per_kword': 3.5, 'new_count': 1, 'resolved_count': 0},
            {'chapter': 3, 'active_count': 3, 'density_per_kword': 4.2, 'new_count': 2, 'resolved_count': 0},
            {'chapter': 6, 'active_count': 5, 'density_per_kword': 5.0, 'new_count': 2, 'resolved_count': 0},
            {'chapter': 10, 'active_count': 4, 'density_per_kword': 3.8, 'new_count': 1, 'resolved_count': 2},
            {'chapter': 15, 'active_count': 3, 'density_per_kword': 3.0, 'new_count': 0, 'resolved_count': 1}
        ]
    })

    # === 步骤 12 (自动聚合) ===
    r12 = run_step(12, '小说档案', {})

    # === 步骤 13 ===
    r13 = run_step(13, '小说简介', {
        'synopsis': {
            'one_liner': {'text': '星际考古学家发现远古文明遗迹，揭开人类文明面临的终极警示'},
            'short_blurb': {'text': '林星辰，一名年轻的星际考古学家，意外接收到来自宇宙深处的外星信号。在探索过程中，他发现了一个横跨数个星系的古老遗迹网络。每一个遗迹都记录着一个伟大文明从崛起到毁灭的全过程。更令人不安的是，这些文明的毁灭模式正在当代人类社会重演。面对文明危机，林星辰必须在真相与安危之间做出抉择。'},
            'standard_blurb': {'text': '在遥远的未来，人类已经实现了星际殖民，建立了横跨三个星系的人类联邦。年轻的星际考古学家林星辰在一次例行勘探中，意外发现了一个古老外星文明留下的遗迹。这个发现让他踏上了一段改变人类命运的旅程。\n\n随着探索的深入，林星辰发现外星文明遗迹遍布整个星系，每一个遗迹都完整记录着一个文明从崛起到毁灭的全过程。而最令人不安的是，这些文明的终结模式——科技爆发后因道德沦丧导致内部分裂——正在当代人类社会重演。\n\n在考古学家苏月华、探险队长赵铁军和基因工程师伊莎贝拉的协助下，林星辰逐渐揭开了遗迹背后隐藏的真相。但与此同时，一股强大的势力正试图掩盖这些发现，而林星辰自己的身世之谜，竟与远古文明有着千丝万缕的联系。'},
            'long_blurb': {'text': '公元3157年，人类联邦已横跨英仙座、猎户座和天鹅座三个星系。在长达五百年的星际殖民史中，人类一直以为自己是宇宙中唯一的智慧文明——直到那一天。年轻的星际考古学家林星辰在英仙座旋臂边缘的一次例行勘探中，接收到了一段无法解释的外星信号。在联邦考古学会的支持下，林星辰组建了一支跨学科探索团队。他们在信号指引的位置发现了一个保存完好的外星遗迹，完整记录了创造该文明从原始时代到最终毁灭的全过程。随着探索深入，团队发现类似的遗迹遍布多个星系，每一个的结局都惊人一致。更令林星辰不安的是，人类文明的当前阶段与这些逝去文明的关键转折点惊人地相似。在一次深入探索中，林星辰发现了自己身世的惊人秘密：他体内的基因印记正是打开终极遗迹的钥匙。当真相的面纱层层揭开，林星辰面临整个人类文明命运的抉择。'},
            'selling_points': [
                {'text': '硬核科幻与文明哲学的深度融合', 'dimension': 'plot'},
                {'text': '四层立体人物塑造体系', 'dimension': 'character'},
                {'text': '跨越数百万年的文明史诗格局', 'dimension': 'world'}
            ],
            'target_audience': '喜欢《三体》风格的硬科幻读者、对科技伦理感兴趣的思考型读者'
        }
    })

    sb_cls = get_registry().get('synopsis_builder')
    if sb_cls:
        sb = sb_cls()
        mr = ModuleResult(data=r13.module_data or {})
        sb_issues = sb.validate(mr)
        print(f'\n[13-3 模块validate] 简介验证: {"✅ 通过" if len(sb_issues)==0 else "⚠ "+str(sb_issues)}')

    # === 步骤 14 (约束检测) ===
    r14 = run_step(14, '分卷配置', {
        'volumes': [
            {'name': '初啼之星', 'chapter_range': [1, 5], 'boundary_gravity': [{'type': 'narrative_gravity', 'description': '第一处遗迹发现'}], 'pacing': '舒缓铺垫', 'major_conflict': '发现外星信号', 'character_focus': ['林星辰', '苏月华'], 'themes': ['好奇心与求知欲'], 'cliffhanger': '全息投影揭示了文明毁灭的可怕真相'},
            {'name': '觉醒之路', 'chapter_range': [6, 11], 'boundary_gravity': [{'type': 'narrative_gravity', 'description': '身世之谜揭示'}], 'pacing': '渐入紧张', 'major_conflict': '情报局阻挠', 'character_focus': ['林星辰', '神秘观察者'], 'themes': ['身份认同', '命运与选择'], 'cliffhanger': '体内基因印记是打开终极遗迹的钥匙'},
            {'name': '真相的重量', 'chapter_range': [12, 18], 'boundary_gravity': [{'type': 'narrative_gravity', 'description': '终极真相揭示'}], 'pacing': '紧张高亢', 'major_conflict': '终极抉择', 'character_focus': ['林星辰', '所有角色'], 'themes': ['牺牲与救赎', '文明的意义'], 'cliffhanger': '林星辰做出了可能是人类文明史上最重要的选择'}
        ]
    })

    if r14.constraint_violations:
        for cv in r14.constraint_violations:
            print(f'  ⚠ 约束违规: [{cv.severity}] {cv.message}')

    print(f'  [14-3 约束检查] 分卷边界: {"✅ 通过" if not any(c.severity=="error" for c in r14.constraint_violations) else "❌ 不通过"}')

    # === 步骤 15 (带质量审查) ===
    char_rows = session.execute(__import__('sqlalchemy').text("SELECT char_id, name FROM characters WHERE novel_id=:nid"), {'nid': novel_id}).fetchall()
    char_map = {r[1]: r[0] for r in char_rows}
    print(f'\n  📋 角色映射: {char_map}')

    scenes_per_ch = [
        [{'pov': '林星辰', 'summary': '勘探发现异常能量波动', 'start_emotion': '平静好奇', 'end_emotion': '震惊兴奋', 'word_count': 2000},
         {'pov': '林星辰', 'summary': '信号分析显示远超人类科技', 'start_emotion': '疑惑', 'end_emotion': '确信', 'word_count': 1800},
         {'pov': '赵铁军', 'summary': '准备探险事宜', 'start_emotion': '犹豫', 'end_emotion': '决心', 'word_count': 1500}],
        [{'pov': '苏月华', 'summary': '受邀加入团队', 'start_emotion': '好奇', 'end_emotion': '兴奋', 'word_count': 1800},
         {'pov': '苏月华', 'summary': '发现从未见过的语言体系', 'start_emotion': '挫败', 'end_emotion': '挑战欲', 'word_count': 2000},
         {'pov': '林星辰', 'summary': '星辰罗盘微微发光', 'start_emotion': '惊讶', 'end_emotion': '期待', 'word_count': 1500}],
    ]
    for i in range(3, 19):
        scenes_per_ch.append([{'pov': '林星辰', 'summary': f'第{i}章剧情推进', 'start_emotion': '好奇', 'end_emotion': '坚定', 'word_count': 2000},
                              {'pov': '苏月华', 'summary': f'第{i}章副线发展', 'start_emotion': '专注', 'end_emotion': '洞察', 'word_count': 1800}])

    r15 = run_step(15, '章节细纲', {
        'chapters': [{'chapter_number': i+1, 'pov_character': '林星辰', 'summary': f'第{i+1}章剧情概要', 'scenes': scenes_per_ch[i]} for i in range(18)]
    })
    print(f'  [15-7 质量审查]: {"✅ 已执行" if r15.review_result else "❌ 未执行"}')
    if r15.review_result:
        print(f'    评分: {r15.review_result.get("data",{}).get("score","N/A")}')

    # === 步骤 16 (正文初稿) ===
    chapters_16 = [{'chapter_number': i+1, 'title': f'第{i+1}章', 'scenes': [{'text': f'第{i+1}章正文场景一内容...', 'word_count': 2000}, {'text': f'第{i+1}章正文场景二内容...', 'word_count': 1800}], 'word_count': 3800} for i in range(18)]
    r16 = run_step(16, '正文初稿', {'chapters': chapters_16})
    print(f'  [16-6 质量审查]: {"✅ 已执行" if r16.review_result else "❌ 未执行"}')
    if r16.review_result:
        print(f'    评分: {r16.review_result.get("data",{}).get("score","N/A")}')

    # === 步骤 17 (正文审核) ===
    r17 = run_step(17, '正文审核', {})
    print(f'  [17-3 四层审查]: {"✅ 已执行" if r17.review_result else "❌ 未执行"}')
    if r17.review_result:
        rd = r17.review_result.get('data',{})
        print(f'    级别: {rd.get("level","N/A")}, 评分: {rd.get("score","N/A")}')

    # === 步骤 18 (正文修正) ===
    r18 = run_step(18, '正文修正', {
        'chapters': chapters_16,
        'fixes': [{'issue_ref': '过渡不够自然', 'original_text': '原文本...', 'fixed_text': '修正后文本...'}]
    })
    print(f'  [18-3 质量审查]: {"✅ 已执行" if r18.review_result else "❌ 未执行"}')

    # === 步骤 20 (导出发布) ===
    r20 = run_step(20, '导出发布', {
        'export': {'title': '星辰之下', 'author': 'AI 创作系统', 'formats': ['txt', 'md']}
    })

    # === 汇总 ===
    print(f'\n\n{"="*70}')
    print(f'📊 20 步流程测试汇总')
    print(f'{"="*70}')
    print(f'{"步骤":<6} {"环节名":<16} {"成功":<8} {"判定":<12}')
    print(f'{"-"*42}')
    for r in results_log:
        status = '✅ 通过' if r['passed'] else '❌ 不通过'
        print(f'{r["step"]:02d}    {r["name"]:<16} {str(r["success"]):<8} {status}')
    print(f'{"-"*42}')
    total_pass = sum(1 for r in results_log if r['passed'])
    print(f'合计: {total_pass}/{len(results_log)} 步通过')
    print(f'{"="*70}')

print('✅ 19 步流程执行完毕！')
