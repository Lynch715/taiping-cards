#!/usr/bin/env python3
"""Human-readable, source-auditable comparison for battle_sim.py output."""
import json
from pathlib import Path
from battle_sim import ROOT,Data,exclusive_skills

REPORT_DIR=ROOT/'assets/reports/balance_v1'

def targets(r):
 return [
  ('SSR对SR单挑',r['duel']['rate'],.65,.75,'65–75%','percent',r['duel']),
  ('5名SSR对5名SR',r['ssr5_vs_sr5']['rate'],.8,1,'≥80%','percent',r['ssr5_vs_sr5']),
  ('5人完整对局平均回合',r['average_full_team_rounds'],8,12,'8–12','rounds',None),
  ('R阵营：太平对清（5v5）',r['factions']['R']['rate'],.45,.55,'45–55%','percent',r['factions']['R']),
  ('SR阵营：太平对清（5v5）',r['factions']['SR']['rate'],.45,.55,'45–55%','percent',r['factions']['SR']),
  ('SSR阵营：太平对清（4v4替代诊断）',r['factions']['SSR']['rate'],.45,.55,'45–55%（非5v5验收）','percent',r['factions']['SSR']),
  ('胜率前10%阵容的最高单卡出场率',r['top_lineups']['max_appearance'],0,.6,'≤60%','percent',None),
  ('12回合内事变：杨秀清+洪君主、无韦',r['incident']['without_wei']['rate'],0,.5,'<50%','strict_low',r['incident']['without_wei']),
  ('12回合内事变：再加韦昌辉',r['incident']['with_wei']['rate'],.9,1,'>90%','strict_high',r['incident']['with_wei']),
 ]
def passes(v,lo,hi,kind):return v<hi if kind=='strict_low' else v>lo if kind=='strict_high' else lo<=v<=hi

def fmt(v,kind='percent'):return f'{v:.3f}' if kind=='rounds' else f'{v*100:.2f}%'
def compact(r):return {name:dict(value=value,pass_=passes(value,lo,hi,kind),target=goal) for name,value,lo,hi,goal,kind,stat in targets(r)}
def esc(s):return str(s).replace('|','\\|').replace('\n',' ')

def write_report(before,after,path,data=None):
 data=data or Data();path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 changes=json.loads((REPORT_DIR/'changes.json').read_text()) if (REPORT_DIR/'changes.json').exists() else {'changes':[]}
 before_map={x[0]:x[1] for x in targets(before)} if before else {}
 lines=['# 战斗平衡模拟报告 v1','','状态：模拟与CSV调整已完成，提交用户审核；这是自动战斗模型的结果，不等同实机战斗验收。','']
 rows=targets(after);bad=[x[0] for x in rows if not passes(x[1],x[2],x[3],x[5])]
 lines += [('无装备主基线的可执行点估计指标全部进入目标范围。' if not bad else '主基线尚未进入目标范围：'+ '、'.join(bad)+'。'),'', '**套装与四星专属的敏感性出现越界，不能称为整体养成平衡全部通过。** 05文件未指定装备水平，本轮选择同50级、同3星、无装备作主验收口径；装备条件单列诊断。阵营主题套装在对称穿同套时也可能给两方不同收益，敏感性结果不能混入无装备主指标。','', '**SSR纯阵营5v5无法按当前名单实施：太平仅有4名战斗SSR；3名SSR君主不能上阵。** 本报告把双方缩为4v4作替代诊断，明确不据此宣称SSR纯阵营5v5达标。跨阵营抽取的5SSR对5SR测试可正常实施。','','## 调整前后','', '|指标|目标|调整前|调整后|判定|','|---|---|---:|---:|---|']
 for name,v,lo,hi,goal,kind,stat in rows:
  status='通过' if passes(v,lo,hi,kind) else '未通过'
  if '替代诊断' in name:status='诊断在区间' if passes(v,lo,hi,kind) else '诊断超区间'
  lines.append(f"|{name}|{goal}|{fmt(before_map[name],kind) if name in before_map else '未提供'}|{fmt(v,kind)}|{status}|")
 lines+=['','以上判定按点估计，不能解释为每个抽样误差区间都完全落在目标内。每项比例另列按镜像对局成簇计算的近似95%区间；前10%阵容出场率是这批候选阵容的经验统计，未证明全体可能阵容或最优配队。','','|指标|每版对局数|调整后近似95%区间（镜像对局为簇）|','|---|---:|---|']
 for name,v,lo,hi,goal,kind,stat in rows:
  if stat:
   ci=stat.get('paired_normal95',stat['wilson95']);lines.append(f"|{name}|{stat['n']:,}|{fmt(ci[0])}–{fmt(ci[1])}|")
 p=after['parameters'];top=after['top_lineups']
 lines += ['','## 样本与复现','',f"主验收：{after['level']}级、双方同{after['stars']}星、无普通装备/专属。每版{after['total_games']:,}局；前后合计{(after['total_games']+(before or {}).get('total_games',0)):,}局。每个常规场景{p['paired_fixtures_per_scenario']:,}组镜像，共{p['paired_fixtures_per_scenario']*2:,}局；随机种子{after['seed']}。",'',f"阵容赛抽取{top['sampled']}个不重复的‘站位5人+君主’阵容，每阵容{top['games_each']}局（{p['opponents']}名随机对手×攻守镜像），按阵容经验胜率排序，取前{top['top_count']}个。君主也计入单卡出场率，分母是前10%阵容数。平分以固定种子的随机键打破，不按人物ID。",'', '同一配队进行攻守交换，保留相同的对局种子；攻城/守城互换以保留该配队所占的地形角色。比例95%区间以两局镜像平均值为独立簇，使用簇均值标准误的正态近似；JSON另附普通Wilson区间，后者未校正镜像相关性。阵容赛双方可能共享对手与人物，排名仍有抽样波动。','', '单挑与五SSR对五SR无君主，双方都同级同星；大队赛随机抽取自然阵营混编，各队双阵营卡按该队指定阵营计数。同稀有度阵营赛使用纯阵营候选池（双阵营牌可加入两方），君主从本方合法君主等概率抽取。地形在陆战、水战、攻城、守城中等概率抽取，不保证有限样本的每种次数完全相同。','', '事变测试：太平队固定杨秀清+洪秀全君主，分别有/无韦，再随机补足本方SR；对手1清SSR+4清SR+随机清君主；上限12回合。提前结束仍计分母，视为未触发，不为追求触发率延长战斗。','',f"平均回合只计完整5v5（五SSR对五SR、R/SR阵营赛、阵容赛），不计单挑、4v4替代和12回合截断事件测试。调整前{fmt(before['average_full_team_rounds'],'rounds') if before else '—'}，后{fmt(after['average_full_team_rounds'],'rounds')}；后者20回合未决比例{fmt(after['full_team_timeout_rate'])}。",'']
 if before:
  lines += [f"前后模拟器代码哈希相同：{before.get('simulator_sha256')==after.get('simulator_sha256')}；种子与采样参数相同：{before['seed']==after['seed'] and before.get('parameters')==after.get('parameters')}。基线文件是`balance_v1/before/data/`，不是用修改后数据伪造的对照。",'']
 lines += ['```sh','python3 -m unittest discover -s tools -p test_battle_sim.py -v','python3 tools/battle_sim.py --audit-only --output assets/reports/balance_v1/parser_audit.json',f"python3 tools/battle_sim.py --data-dir assets/reports/balance_v1/before/data --n {p['paired_fixtures_per_scenario']} --lineups {p['lineups']} --opponents {p['opponents']} --seed {after['seed']} --output assets/reports/balance_v1/before_metrics.json --no-report",f"python3 tools/battle_sim.py --n {p['paired_fixtures_per_scenario']} --lineups {p['lineups']} --opponents {p['opponents']} --seed {after['seed']} --output assets/reports/balance_v1/after_metrics.json --compare-before assets/reports/balance_v1/before_metrics.json",'```','','输入与模拟器哈希在每份metrics JSON中；全部原CSV备份在`balance_v1/before/data/`。','', '## 技能优先的调参记录','', '先运行原始基线，再进行技能系数候选试调。未改英雄属性、兵种、阵营、羁绊、普通装备或套装；因此没有进入属性调整阶段。专属只同步被调基础技能的旧值→强化值，保持原强化倍率，防止4星时替换失效。主验收使用未参与调参的独立种子；试调结果全部保留，未把试调最优抽样直接当验收。','', '|阶段|对局数|SSR单挑|5SSR胜率|R太平|SR太平|SSR太平4v4|平均回合|最高出场率|','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
 for trial in sorted(REPORT_DIR.glob('trial_*.json')):
  raw=json.loads(trial.read_text())
  if 'metrics' not in raw:continue
  r=raw['metrics'];lines.append(f"|{trial.stem}|{r['total_games']:,}|{fmt(r['duel']['rate'])}|{fmt(r['ssr5_vs_sr5']['rate'])}|{fmt(r['factions']['R']['rate'])}|{fmt(r['factions']['SR']['rate'])}|{fmt(r['factions']['SSR']['rate'])}|{r['average_full_team_rounds']:.3f}|{fmt(r['top_lineups']['max_appearance'])}|")
 lines+=['','早期试调用于检验方向，n、阵容数不同且模拟器仍在验证，不能把各轮的微小差异当成系数的严格因果效应。候选JSON包含每轮完整替换表和实际指标；最终前后比较使用同一份冻结后的模拟器、同一随机种子与参数。','','## 每一处数据改动','',f"共{len(changes['changes'])}处单元格改动；以下列出修改前后全文。属性改动0处。",'','|表 / 行 / 列|修改前|修改后|','|---|---|---|']
 for c in changes['changes']:
  lines.append(f"|{c['file']} / {c['id']} / {c['column']}|{esc(c['before'])}|{esc(c['after'])}|")
 lines += ['','## 属性预算复核','','君主6人豁免；50名战斗卡逐人重算E=统+主攻属性+速。主攻：谋取智，其余取武。','', '|人物|稀有度|E（前→后）|允许区间|判定|','|---|---|---:|---|---|']
 old_data=Data(REPORT_DIR/'before/data') if (REPORT_DIR/'before/data').exists() else data
 old_budget={r['id']:r['E'] for r in old_data.budget()}
 for b in data.budget():
  bounds={'SSR':'265–275','SR':'246–254','R':'226–234'}[b['rarity']]
  lines.append(f"|{b['name']}|{b['rarity']}|{old_budget[b['id']]}→{b['E']}|{bounds}|{'通过' if b['valid'] else '未通过'}|")
 audit=list(data.audit)
 for h in data.heroes.values():
  *_,unparsed=exclusive_skills(data,h,True)
  if unparsed:audit.append(dict(id=h['id'],unparsed=unparsed))
 lines += ['','## 解析审计与测试','',f"读取56人物、112技能、28羁绊、100普通装备、5套装、39专属。无法解析的当前文本共{len(audit)}项。",'', '```json',json.dumps(audit,ensure_ascii=False,indent=2),'```','', '未知技能/羁绊不会以无效果继续模拟；战斗构造时阻止运行。专属的过期原值也会显式报错。支持普通装备混搭、两件/四件门槛、品质、强化，专属4星解锁；主验收固定无装备，另跑装备/星级敏感性，不把额外加成藏入基线。','', '测试日志：`balance_v1/tests.log`。覆盖物攻/谋攻换算与对应防御、克制、顿号并列效果、开场怒气叠加、盾与受击怒气、同源增益、治疗最大生命比例、灼烧吃盾、嘲讽、免死、事变与离场、政令猜忌去重、君主不借战斗卡套装、诏令一次性、粮饷/信仰、4星专属、石达开专属改回复而非触发线、两件套门槛、沉默/眩晕、回合判负和固定种子复现。','','## 规则解释与待审事项','', '以下是文档没有完全规定的执行细节，已显式选定，不属于“无法解析”的文本：','','- “生命最低”按当前/最大生命比例排序，平手按站位；普通单体在合法目标池内随机。前排/后排范围在该排全灭时改打存活另一排。','- 百分比“攻击”同时作用物攻/谋攻；“防御”同时作用物防/谋防。全属性只影响四项衍生属性对应的HP、攻、防、速度，不提高暴击率。','- 数值增益、盾、灼烧从施加回合起计时，到标注末回合结束失效；控制按受影响者接下来的行动次数扣减。速度顺序在每回合开始排好，回合中速度变化下回合生效。','- 灼烧锁定施加时ATK，忽略防御/克制/暴击，但受通用减伤与护盾影响；盾吸收的攻击仍加受击怒气。灼烧也加受伤怒气，但不计受“攻击”被动层数。','- 暴击伤害-30%解释为150%减30个百分点到120%；连击是完整普攻，也获得普攻怒气，但不无限递归触发连击。','- “每少1名存活”按本队初始上阵人数的实际减员算，单挑和4v4的空槽不算阵亡；石达开离场减少存活人数，但不触发阵亡被动。','- 天京事变按文档强制扣当前生命，不走护盾/免死。洪政令的每回合+5与羁绊文字是同一来源，未重复叠加；杨秀清死亡后不再算“在场”。','- 苏三娘在美术表为骑兵装束，但heroes.csv的战斗兵种是“步”；模拟器严格沿用CSV，未自行改兵种。','- SSR纯阵营5v5仍需后续扩充合法战斗SSR或另行批准测试口径；本次4v4只作可复现的诊断。','','## 装备与星级敏感性（诊断）','', '|条件|局数|SSR单挑|5SSR胜率|R太平|SR太平|SSR太平4v4|平均回合|最高出场率|','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
 for f in sorted(REPORT_DIR.glob('sensitivity_*.json')):
  r=json.loads(f.read_text());lines.append(f"|{f.stem}|{r['total_games']:,}|{fmt(r['duel']['rate'])}|{fmt(r['ssr5_vs_sr5']['rate'])}|{fmt(r['factions']['R']['rate'])}|{fmt(r['factions']['SR']['rate'])}|{fmt(r['factions']['SSR']['rate'])}|{r['average_full_team_rounds']:.3f}|{fmt(r['top_lineups']['max_appearance'])}|")
 lines+=['','敏感性样本小于主验收，且按对称穿同套装检验；不能代替所有自由混搭、强化梯度或自然初始星级的养成平衡。若这些条件出现超区间，保留原值供后续设计审核，不据此回改主验收采样口径。','','## 出场率明细','', '|卡牌|前10%阵容出现次数|比例（分母为前10%阵容数）|','|---|---:|---:|']
 for ident,count in sorted(top['appearances'].items(),key=lambda x:(-x[1],x[0])):
  lines.append(f"|{data.heroes[ident]['name']}|{count}/{top['top_count']}|{fmt(count/top['top_count'])}|")
 path.write_text('\n'.join(lines)+'\n')
 (REPORT_DIR/'report_validation.json').write_text(json.dumps(dict(before=compact(before) if before else None,after=compact(after),budget_all_valid=all(x['valid'] for x in data.budget()),unparsed=audit,ssr5_faction_validation='NOT_EXECUTABLE_WITH_CURRENT_ROSTER'),ensure_ascii=False,indent=2)+'\n')

if __name__=='__main__':
 write_report(json.loads((REPORT_DIR/'before_metrics.json').read_text()),json.loads((REPORT_DIR/'after_metrics.json').read_text()),ROOT/'assets/reports/balance_report.md')
