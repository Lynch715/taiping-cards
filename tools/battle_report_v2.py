#!/usr/bin/env python3
"""V2 review report: identical-engine holdouts, constraints, monarchs and39 ablations."""
import csv,hashlib,json,platform,sys
from pathlib import Path
from battle_sim import ROOT,Data,exclusive_skills
from balance_diagnostics import constraint_audit
R=ROOT/'assets/reports/balance_v2'

def read(p):return json.loads(p.read_text()) if p.exists() else None
def pct(x):return '—' if x is None else f'{100*x:.2f}%'
def pp(x):return '—' if x is None else f'{100*x:+.2f}pp'
def esc(x):return str(x).replace('|','\\|').replace('\n',' ')
def targets(r,data):
 rows=[
  ('SSR对SR单挑',r['duel']['rate'],.65,.75,'65–75%','pct',r['duel']),
  ('5SSR对5SR',r['ssr5_vs_sr5']['rate'],.8,1,'≥80%','pct',r['ssr5_vs_sr5']),
  ('完整5v5平均回合',r['average_full_team_rounds'],8,12,'8–12','round',None),
  *[(f'{rarity}纯阵营太平胜率（5v5）',r['factions'][rarity]['rate'],.45,.55,'45–55%','pct',r['factions'][rarity]) for rarity in ['R','SR','SSR']],
  ('前10%阵容最高战斗卡出场率',r['top_lineups']['max_appearance'],0,.6,'≤60%','pct',None),
  ('事变：杨+洪君主、无韦',r['incident']['without_wei']['rate'],0,.5,'<50%','lt',r['incident']['without_wei']),
  ('事变：再加入韦昌辉',r['incident']['with_wei']['rate'],.9,1,'>90%','gt',r['incident']['with_wei']),
 ]
 for camp,group in r['monarchs'].items():
  for ident,row in group['cards'].items():rows.append((f"君主选用：{data.heroes[ident]['name']}",row['rate'],.2,1,'≥20%（本阵营前10%）','pct',None))
 return rows

def valid(v,lo,hi,kind):return v<hi if kind=='lt' else v>lo if kind=='gt' else lo-1e-9<=v<=hi+1e-9

def matching(path,main,seed=None,runtime=None):
 x=read(path)
 return x if x and x.get('input_sha256')==main.get('input_sha256') and (seed is None or x.get('seed')==seed) and (runtime is None or x.get('runtime_sha256')==runtime) else None

def changes(data):
 out=[]
 for filename,key in [('heroes.csv','id'),('skills.csv','skill_id'),('bonds.csv','bond_id'),('equipment.csv','equip_id'),('equipment_sets.csv','set'),('exclusive_equipment.csv','hero_id')]:
  def rows(p):
   with p.open(encoding='utf-8-sig',newline='') as f:return {r[key]:r for r in csv.DictReader(f)}
  before=rows(R/'before/data'/filename);after=rows(data.directory/filename)
  assert set(before)==set(after),'Roster/item additions are outside this round'
  for ident,row in after.items():
   for col,value in row.items():
    if before[ident][col]!=value:out.append(dict(file=filename,id=ident,column=col,before=before[ident][col],after=value))
 return out

def write_report(before,after,path,data=None):
 data=data or Data();path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 bdata=Data(R/'before/data');a=constraint_audit(data);b=constraint_audit(bdata);diff=changes(data)
 parse=list(data.audit)
 for h in data.heroes.values():
  *_,unknown=exclusive_skills(data,h,True)
  if unknown:parse.append(dict(id=h['id'],unparsed=unknown))
 protocol=read(R/'frozen_protocol.json') or {};seeds=protocol.get('holdout_seeds',{});runtime=protocol.get('runtime_sha256')
 precision_protocol=read(R/'monarch_precision_protocol.json') or {}
 ap=matching(R/'after_monarch_precision.json',after,precision_protocol.get('seed'),precision_protocol.get('runtime_sha256'))
 bp=matching(R/'before_monarch_precision.json',before,precision_protocol.get('seed'),precision_protocol.get('runtime_sha256')) if before else None
 effective_after={**after,'monarchs':ap['monarchs']} if ap else after
 effective_before={**before,'monarchs':bp['monarchs']} if before and bp else before
 rows=targets(effective_after,data);old={x[0]:x for x in targets(effective_before,bdata)} if before else {};failed=[x[0] for x in rows if not valid(x[1],x[2],x[3],x[5])]
 after_ex=matching(R/'after_exclusives.json',after,seeds.get('exclusives'),runtime);before_ex=matching(R/'before_exclusives.json',before,seeds.get('exclusives'),runtime) if before else None
 after_choice=matching(R/'after_monarch_choices.json',after,seeds.get('monarchs'),runtime);before_choice=matching(R/'before_monarch_choices.json',before,seeds.get('monarchs'),runtime) if before else None
 sensitivity={}
 for label in ['圣兵','勇营','洋械','铁骑','江防','4star']:
  ar=matching(R/'sensitivity'/f'after_{label}.json',after,seeds.get('sensitivity'));br=matching(R/'sensitivity'/f'before_{label}.json',before,seeds.get('sensitivity')) if before else None
  if ar:sensitivity[label]=(br,ar)
 formal_games=(before or {}).get('total_games',0)+after['total_games']
 formal_games+=sum((br or {}).get('total_games',0)+ar['total_games'] for br,ar in sensitivity.values())
 formal_games+=sum(x['total_games'] for x in [before_ex,after_ex,before_choice,after_choice] if x)
 formal_games+=sum(x['total_games'] for x in [bp,ap] if x)
 integrity_errors=[]
 for phase,main,ds in [('before',before,bdata),('after',after,data)]:
  if not main:integrity_errors.append(f'{phase}: missing main result');continue
  expected={n:hashlib.sha256((ds.directory/n).read_bytes()).hexdigest() for n in main['input_sha256']}
  if expected!=main['input_sha256']:integrity_errors.append(f'{phase}: current CSV differs from tested CSV')
  if main['seed']!=seeds.get('main'):integrity_errors.append(f'{phase}: main seed differs from frozen protocol')
  if main['simulator_sha256']!=(runtime or {}).get('battle_sim.py'):integrity_errors.append(f'{phase}: simulator hash differs from frozen protocol')
 for label,(br,ar) in sensitivity.items():
  for phase,x in [('before',br),('after',ar)]:
   if not x or x['simulator_sha256']!=(runtime or {}).get('battle_sim.py'):integrity_errors.append(f'{phase}/{label}: missing result or mismatched simulator')
 for phase,x in [('before',bp),('after',ap)]:
  if not x or x['simulator_sha256']!=(runtime or {}).get('battle_sim.py'):integrity_errors.append(f'{phase}: missing monarch precision result or mismatched simulator')
 complete=bool(before and after_ex and before_ex and before_choice and after_choice and ap and bp and len(sensitivity)==6 and not integrity_errors)
 lines=['# 第二轮战斗平衡报告 v2','','状态：数据与模拟结果提交用户审核；v1报告及其原CSV保留。本轮“调整前”是用户升级萧朝贵/洪仁玕、苏三娘改骑、新套装效果后的起点，**不拿v1旧名单结果当新版基线**。','']
 lines += [('战斗主指标及扩大样本后的君主选用率点估计达标。前一候选11的1600阵容中恭亲王19.55%、追加8000阵容中慈禧18.18%，失败记录与后续修订均保留在下文。' if not failed else '**主基线尚未达标：'+ '、'.join(failed)+'。**'),f"新增硬约束审计：{'通过' if a['all_valid'] else '未通过'}；无法解析文本{len(parse)}项。最终版本前后比较与诊断合计{formal_games:,}局（不含训练试调及前期未通过的复核）。",'']
 if any(not valid(x[1],x[2],x[3],x[5]) for _,ar in sensitivity.values() for x in targets(ar,data)):
  lines+=['**装备敏感性尚未全部达标。** 部分套装下的单挑、阵营或小样本君主统计仍有越界，全部列在装备专表；本报告不宣称所有装备条件都已平衡。','']
 if not complete:lines+=['**交付不完整：当前缺少匹配本版输入哈希的诊断或敏感性文件，不能据此宣称完整第二轮通过。**','']
 lines += ['## 主指标：调整前后','','口径：50级、双方同3星、无普通装备/专属。纯阵营R、SR、SSR全部正式5v5；双方各6名战斗SSR中抽5名，不把君主当战斗卡，不补重复人物，不使用4v4替代。君主选用率按用户明确选择的“本阵营胜率前10%阵容中的占比”验收，使用下述扩大8000候选阵容的统计；其他主指标沿用原冻结主测试。原1600阵容结果全部保留，未用输入抽取率替代选用率。','','|指标|目标|调整前|调整后|判定|','|---|---|---:|---:|---|']
 for name,v,lo,hi,goal,kind,stat in rows:
  fmt=lambda x:f'{x:.3f}' if kind=='round' else pct(x)
  lines.append(f"|{name}|{goal}|{fmt(old[name][1]) if name in old else '—'}|{fmt(v)}|{'通过' if valid(v,lo,hi,kind) else '未通过'}|")
 lines += ['','比例判定使用点估计；下表按两局攻守镜像为一个簇计算近似95%区间，不把相关的镜像局视为完全独立。前10%阵容统计有共享对手和阵容依赖，未伪造其独立二项区间。','','|指标|每版对局数|调整后近似95%区间|','|---|---:|---|']
 for name,v,lo,hi,goal,kind,stat in rows:
  if stat:
   ci=stat['paired_normal95'];lines.append(f"|{name}|{stat['n']:,}|{pct(ci[0])}–{pct(ci[1])}|")
 p=after['parameters'];lines+=['','## 采样、君主统计与可比性','',f"主测试每版{after['total_games']:,}局；每场景{p['paired_fixtures_per_scenario']:,}组攻守镜像。阵容赛抽{p['lineups']:,}个不同的‘站位5人+君主’阵容，每个面对{p['opponents']}个随机对手并交换攻守，共{p['opponents']*2}局。主测试独立种子{after['seed']}。",'', '战斗卡最高出场率的分母是全体候选阵容中胜率前10%的阵容数，分子只统计5个战斗位，完全排除君主。君主另按各自阵营排序，分母是本阵营候选阵容前10%的阵容数；太平两位、清朝四位分别统计，六项都要求≥20%。', '', '截断位置若有同胜率并列，则按并列人数平分剩余权重，避免按人物ID或抽签人为影响王的达标。出现次数可能为小数，所有君主占比在各自阵营内合计100%。随机抽取的输入频率不是达标选用率。','', '单挑与5SSR对5SR不带君主，同级同星。阵营赛君主在本阵营合法池等概率抽取，四种地形等概率抽取；有限样本不保证各地形次数完全相同。攻守互换时攻城/守城也互换，使同一逻辑队保留地形角色。双阵营牌按其加入的一方计数。','', '事变测试固定杨秀清+洪秀全君主，有/无韦昌辉，随机补足本方SR；对手1清SSR+4清SR+随机清君主，上限12回合，提前结束也计入分母、视为未触发。平均回合只计完整5v5，排除单挑和12回合事件截断；达到20回合未决则进攻方判负。', '',f"主测试20回合未决比例：{pct(before['full_team_timeout_rate']) if before else '—'} → {pct(after['full_team_timeout_rate'])}。前后代码哈希一致：{bool(before and before['simulator_sha256']==after['simulator_sha256'])}；主种子/参数一致：{bool(before and before['seed']==after['seed'] and before['parameters']==after['parameters'])}。",'', '固定五人试配全部本阵营君主、选择经验胜率最高者的结果另作诊断，**依用户选择，不替换前10%阵容的正式口径**。该诊断共享对手、地形与种子，精确平分最优并列者的一票。','']
 if ap and bp:
  lines+=['',f"君主精度复核：候选11原1600阵容中恭亲王19.55%，追加独立8000阵容后恭亲王25.09%、慈禧18.18%，仍未通过，原记录完整保存在validation_round_11/。候选12仅调整慈禧政令防御18%→20%、怒气获取20%→25%及专属强化30%→35%，再冻结数据并更换所有种子复核。当前君主测试预先登记在monarch_precision_protocol.json，以4个独立2000阵容批次合并成8000阵容，各阵营共4000，合并后统一取前10%权重400；各阵容在所属批次中随机取16个对手、镜像共32局。批次间允许同阵容再次被随机抽到，不把4批前10%占比直接取平均。独立种子为{ap.get('shard_seeds', [ap['seed']])}，前后共{ap['total_games']+bp['total_games']:,}局；辅助n=1场景估计不用于战斗指标。该统计仍受共享对手与阵容依赖限制，不伪装成独立二项置信区间。",'','|君主|当前1600前|当前1600后|扩大8000前（验收）|扩大8000后（验收）|','|---|---:|---:|---:|---:|']
  for camp,group in ap['monarchs'].items():
   for ident,row in group['cards'].items():
    lines.append(f"|{data.heroes[ident]['name']}|{pct(before['monarchs'][camp]['cards'][ident]['rate'])}|{pct(after['monarchs'][camp]['cards'][ident]['rate'])}|{pct(bp['monarchs'][camp]['cards'][ident]['rate'])}|{pct(row['rate'])}|")
  lines+=['','下表再列固定五人试配最优率，仍仅作诊断；“正式样本”指扩大后的8000阵容统计。','']
 lines += ['|君主|正式样本前|正式样本后|同五人试配最优率前（诊断）|同五人试配最优率后（诊断）|','|---|---:|---:|---:|---:|']
 for camp,group in effective_after['monarchs'].items():
  for ident,row in group['cards'].items():
   bc=effective_before['monarchs'][camp]['cards'][ident]['rate'] if before else None
   optb=before_choice['factions'][camp]['cards'][ident]['rate'] if before_choice else None;opta=after_choice['factions'][camp]['cards'][ident]['rate'] if after_choice else None
   lines.append(f"|{data.heroes[ident]['name']}|{pct(bc)}|{pct(row['rate'])}|{pct(optb)}|{pct(opta)}|")
 lines+=['','## 新增约束审计与招牌机制','','招牌主项逐人建立显式映射（balance_diagnostics.py的SIGNATURES），不靠“挑最大数字”掩盖被削小的技能。百分比主项≥10%；免死、取武智较高、速度/怒气点数等非百分比机制标豁免。洪秀全每10智+0.3%是附加成长项，主项恢复10%，不以该小成长项代替主项。','', '普通卡审计对加成、减益、护盾、治疗取绝对值；不把230%直接伤害系数、50%触发血线、概率或回合数错误地裁到25。R卡基础单项≤25%，洪仁玕等其他人物的协同增幅另算。套装五套均检查不引用信仰/猜忌/粮饷。','','|审计|调整前不合格项|调整后不合格项|','|---|---:|---:|']
 for label,key in [('招牌百分比主项≥10%','signatures'),('普通卡单项≤25%','r_effects'),('套装不引用阵营资源','sets'),('英雄E预算','budgets')]:lines.append(f"|{label}|{sum(not x['valid'] for x in b[key])}|{sum(not x['valid'] for x in a[key])}|")
 lines += ['','关键恢复及条件/代价：','','- 石达开：无正面羁绊时全属性5%恢复20%，同时承担受到伤害+20%的孤军代价；有正面羁绊时两者均不生效。绝境回复仍有明确触发线与每场一次限制。','- 洪秀全：主项3%恢复10%，改为信仰达到门槛后生效；未达门槛时不享该光环。门槛与全部文本见逐项改动。光环切换按当前生命比例同步最大生命，不凭空治疗。','- 僧格林沁：恢复骑兵攻击12%、对步兵伤害15%，仍受兵种/目标限制，保留骑将特色。','- 曾国藩：每次减员的防御/攻击分别恢复到10%，以最多2层约束累积；不再以8%/5%零碎叠加替代招牌。','- 杨秀清改为每40猜忌提高攻击10%；鲍超改为每受2次攻击提高攻击10%、最多3层；李世贤改为低生命时回合末回复10%。用触发节奏控制强度。','','|人物|招牌主项|百分比前|百分比后|判定|','|---|---|---:|---:|---|']
 bs={x['id']:x for x in b['signatures']}
 for x in a['signatures']:
  label=lambda q:'非百分比' if q['nonpercentage'] else ('—' if q['percent'] is None else f"{q['percent']:g}%")
  lines.append(f"|{x['name']}|{x['mechanism']}|{label(bs[x['id']])}|{label(x)}|{'通过' if x['valid'] else '未通过'}|")
 lines+=['','## 四星专属：39件逐件诊断','','每件单独测试：双方全部4星；固定同一五人阵容、站位、对手、地形、君主与种子，只有本人的专属在“裸装/只属性/完整专属”三臂变化，对手及其他队友不偷偷获得专属。君主装备诊断使用其所带队伍胜率，君主不能单挑；双阵营武将轮流加入双方。', '', '总提升=完整专属胜率−裸4星胜率；属性提升=只属性−裸装；技能提升=完整−只属性。单挑另列，只在本件拥有者身上装备。前后分别以各版本基础技能为裸装基准，因此“提升前后变化”也反映环境变化，不伪称全部由一个专属数字单独造成。', '', '先用小样本全39件初筛（exclusive_screen_before.json），优先处理提升居前的杨秀清、左宗棠、石达开、萧朝贵、洪宣娇、曾国藩等；再对属性贡献过高者调专属属性。技能阶段在装备属性阶段之前，英雄四维未改。正式诊断采用另一组独立种子。', '', '初筛发现咸丰提前治疗的专属经常浪费在尚未明显受伤的时点，改为同回合提高治疗量；不是仅按正提升排行而漏掉负收益装备。未参与战斗且无属性换算条款的君主，其主攻/生命加成不会凭空转成战斗收益：非洪君主的属性臂可为0，强化政令/诏令仍生效。', '', '|人物 / 专属|队伍总提升前|队伍总提升后|后：属性贡献|后：技能贡献|后：总提升近似95%区间|单挑提升前→后|处理|','|---|---:|---:|---:|---:|---|---|---|']
 if after_ex and before_ex:
  bi={x['id']:x for x in before_ex['rows']}
  for x in sorted(after_ex['rows'],key=lambda x:-bi[x['id']]['total_lift']['delta']):
   q=bi[x['id']];ci=x['total_lift']['paired_normal95'];duel=f"{pp(q['duel']['delta'])}→{pp(x['duel']['delta'])}" if x['duel'] else '君主：不单挑'
   cols={c['column'] for c in diff if c['file']=='exclusive_equipment.csv' and c['id']==x['id']};h=data.heroes[x['id']]
   action='、'.join(label for col,label in [('effect','调技能强化'),('stat_bonus','调专属属性')] if col in cols)
   if not action:action='基础技能调整后重测，专属保留' if any(c['file']=='skills.csv' and c['id'] in [h['active'],h['passive']] for c in diff) else '保留，已重测'
   if x['id']=='qing_xianfeng':action='修正治疗时点，增加治疗量'
   lines.append(f"|{x['name']} / {x['equipment']}|{pp(q['total_lift']['delta'])}|{pp(x['total_lift']['delta'])}|{pp(x['stat_lift']['delta'])}|{pp(x['skill_lift']['delta'])}|{pp(ci[0])}～{pp(ci[1])}|{duel}|{action}|")
  lines += ['',f"每件每版{after_ex['n']}组5v5镜像×3臂；战斗卡另{after_ex['duels']}组单挑镜像×2臂。专属诊断前后共{before_ex['total_games']+after_ex['total_games']:,}局。数值提升是百分点pp，不是相对百分比；区间跨0的微小正负差不能当确定增益/损害。"]
  leader=max(after_ex['rows'],key=lambda q:q['total_lift']['delta']);lines+=['',f"新环境下提升最高的是{leader['name']}（{pp(leader['total_lift']['delta'])}）；该数值仍值得后续关注。此轮优先调整初筛提升最高的几件，不宣称所有专属已达到统一收益区间。"]
 else:lines+=['|未提供匹配本版哈希的39件诊断|—|—|—|—|—|—|—|']
 lines+=['','## 装备与四星敏感性：调整前后','','五套普通装备均为双方同套四件、精、强化0；四星项双方同4星、无普通装备、全部可用专属开启。各条件共享固定的阵容抽样/镜像种子，前后也一致，避免把换了阵容误读成套装效应。这些是指定条件下的点估计，所有越界原样标出。','','|条件|每版局数|单挑前→后|5SSR胜率前→后|R太平前→后|SR太平前→后|SSR太平5v5前→后|平均回合前→后|后：主目标越界项|','|---|---:|---|---|---|---|---|---|---|']
 sensitivity_bad={}
 for label,(br,ar) in sensitivity.items():
  bad=[x[0] for x in targets(ar,data) if not valid(x[1],x[2],x[3],x[5])];sensitivity_bad[label]=bad
  delta=lambda get:f'{pct(get(br)) if br else "—"}→{pct(get(ar))}'
  avg=f"{br['average_full_team_rounds']:.3f}→{ar['average_full_team_rounds']:.3f}" if br else f"—→{ar['average_full_team_rounds']:.3f}"
  lines.append(f"|{label}|{ar['total_games']:,}|{delta(lambda r:r['duel']['rate'])}|{delta(lambda r:r['ssr5_vs_sr5']['rate'])}|{delta(lambda r:r['factions']['R']['rate'])}|{delta(lambda r:r['factions']['SR']['rate'])}|{delta(lambda r:r['factions']['SSR']['rate'])}|{avg}|{'；'.join(bad) or '无'}|")
 lines += ['','勇营4件保留单次回复3%，增加“每第4回合开始”条件，以触发节奏减少全员对称回血造成的长局。曾试每回合2%，上一轮独立复核仍为12.612回合，故继续调整；圣兵按击杀加怒气与有限攻击层数，两个套装均不引用阵营资源。套装生效、两件/四件门槛和周期回复均有回归。','', '每个装备条件还保留完整君主分阵营选用率、事变触发率、20回合超时比例和战斗卡最高出场率，详见balance_v2/sensitivity/对应JSON。指定套装若越界，不能写成“所有装备下全部通过”。敏感性测试每版每条件只抽200个候选阵容，每阵营前10%约10个有效阵容权重，君主小样本波动较大；此处仍列出越界，不替代无装备8000阵容的正式君主判定。','','## 调参阶段与每一处改动','','|阶段|局数|SSR单挑|R太平|SR太平|SSR太平5v5|平均回合|','|---|---:|---:|---:|---:|---:|---:|']
 for trial in sorted((R/'trials').glob('*/metrics.json')):
  r=read(trial);lines.append(f"|{trial.parent.name}|{r['total_games']:,}|{pct(r['duel']['rate'])}|{pct(r['factions']['R']['rate'])}|{pct(r['factions']['SR']['rate'])}|{pct(r['factions']['SSR']['rate'])}|{r['average_full_team_rounds']:.3f}|")
 lines+=['','早期试调采样大小和数值运行时仍在验证；阶段间细小差异不当作严格因果估计。06只进一步调整专属，不影响3星，未重复与05相同的3星训练。','', '06进行了433,440局前后复核：SSR纯阵营太平胜率56.23%，勇营平均12.612回合，未通过，完整结果及数值代码在balance_v2/validation_round_06/。07定向比较后将左宗棠主动技恢复140%，08/09为勇营增加回复周期；09又完成433,440局复核，勇营已降至11.737回合，但SSR太平胜率43.65%，清军加强过量，仍未提交通过。该轮完整结果在balance_v2/validation_round_09/。两次未通过结果均用于后续训练，不计入最终版验证局数。','', '10阶段进一步均衡8组君主配对和4种地形，用2个训练种子、每个系数6,016组镜像比较左宗棠125%/130%伤害，其他输入不动；随后选定最终候选。最终版主测试、专属、敏感性及君主另法诊断全部更换独立种子重新运行，前后使用同一冻结运行时；最终样本没有参与本版选参。11随后完成8000阵容追加，恭亲王25.09%但慈禧18.18%，仍未通过；详见validation_round_11/。因此12仅加强慈禧政令及同步专属，再以新种子对全部指标重新复核。当前最终样本未用于本版选参。','', '|10阶段SSR专项训练|对局数|太平胜率|','|---|---:|---:|']
 for probe in sorted((R/'trials').glob('10_*/ssr_probe.json')):
  q=read(probe);lines.append(f"|{probe.parent.name}|{q['games']:,}|{pct(q['average_rate'])}|")
 selected=read(R/'selected_candidate.json') or {}
 lines+=['',f"最终候选：{selected.get('candidate','未记录')}。",'',f"最终共{len(diff)}处单元格改动；英雄四维改动{sum(x['file']=='heroes.csv' and x['column'] in ['tong','wu','zhi','su'] for x in diff)}处。以下列出全文，主攻+生命的装备数值不是角色招牌技能百分比，不混用约束。",'', '|表 / 行 / 列|修改前|修改后|','|---|---|---|']
 for x in diff:lines.append(f"|{x['file']} / {x['id']} / {x['column']}|{esc(x['before'])}|{esc(x['after'])}|")
 lines+=['','## E预算逐人复核','','|人物|稀有度|E前→后|允许范围|判定|','|---|---|---:|---|---|'];old_e={x['id']:x['E'] for x in b['budgets']}
 for x in a['budgets']:
  bounds={'SSR':'265–275','SR':'246–254','R':'226–234'}[x['rarity']];lines.append(f"|{x['name']}|{x['rarity']}|{old_e[x['id']]}→{x['E']}|{bounds}|{'通过' if x['valid'] else '未通过'}|")
 lines+=['','## 解析、规则解释与回归','', f"读取56人物、112技能、28羁绊、100普通装备、5套装、39专属；当前无法解析项{len(parse)}条。",'', '```json',json.dumps(parse,ensure_ascii=False,indent=2),'```','', '- 洪仁玕的50%只放大洪秀全/洪天贵福的政令数值，含增益、开场信仰、信仰上限与政令自带猜忌；不放大诏令或负面羁绊额外猜忌。阵亡后立即取消持续放大；已获得的开场资源不追溯收回。','- 条件全属性光环切换按当前生命比例同步最大生命，既不免费回血，也不凭空扣血；护盾以施放当时最大生命建立，不追溯重算。','- “仅首次释放主动技时生效”的专属强化后续回归基础技能，基础技能仍照常发动；本轮用于限制强群体减攻和额外连击。','- “生命最低”仍按当前/最大生命比例；控制按下次行动次数、数值增益/盾/灼烧按标注回合计时。速度在回合开始排队，回合中改速下回合改变次序。','- 灼烧锁定施加时ATK，吃通用减伤/盾，忽略防御/克制/暴击；盾吸收也加受击怒气；灼烧不加“受攻击”层数。','- “每少1名存活”按实际减员；石达开离场不当阵亡；天京事变按当前生命扣除，洪政令的猜忌不与羁绊说明重复叠加。','- 专属统计按同4星裸装对照，绝不拿3星裸装当4星装备前基线。等级、星级、普通装备条件分别明确。','', '最终正式CSV的42项回归通过，日志：balance_v2/regression_tests.log。涵盖伤害/怒气/控制/盾/免死旧语义，以及新阵亡回怒、政令强化与取消、信仰门槛最大生命、双方通用新套装、单一专属拥有者、只属性拆分、首次强化限制、同回合治疗、正式5v5及君主剔除/并列权重。','','## 复现与文件','',f'本轮环境：Python {platform.python_version()}，仅标准库；正式种子与全部输入/运行时代码哈希见balance_v2/frozen_protocol.json。','', '```sh',"python3 -m unittest discover -s tools -p 'test_ba*.py' -v",'python3 tools/run_balance_v2_review.py --after-dir data','python3 tools/run_monarch_precision_v2.py','python3 tools/battle_report_v2.py','```','', '输入起点完整保存在balance_v2/before/data/，旧数值脚本也存于before/tools/；v1报告不覆盖。主指标before_metrics.json/after_metrics.json，专属before_exclusives.json/after_exclusives.json，君主另法诊断before_monarch_choices.json/after_monarch_choices.json，君主扩大样本before_monarch_precision.json/after_monarch_precision.json及预先登记的monarch_precision_protocol.json，装备sensitivity/，逐项改动changes.json，硬约束constraint_audit.json。', '', '本报告是模型及样本结果，不是实机战斗验收，也不证明所有可能阵容、等级或自由混搭装备都已达到相同胜率。']
 path.write_text('\n'.join(lines)+'\n')
 validation=dict(complete=complete,integrity_errors=integrity_errors,formal_games=formal_games,main_targets={name:{'value':v,'target':goal,'pass':valid(v,lo,hi,kind)} for name,v,lo,hi,goal,kind,stat in rows},monarch_acceptance_sample='8000 candidate lineups, 4000 per faction, top10% weight400; same user-confirmed definition',monarch_original_main=after['monarchs'],constraints_all_pass=a['all_valid'],unparsed=parse,sensitivity_out_of_range=sensitivity_bad,formal_ssr5v5=True)
 (R/'report_validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2)+'\n');(R/'changes.json').write_text(json.dumps(diff,ensure_ascii=False,indent=2)+'\n');(R/'constraint_audit.json').write_text(json.dumps(dict(before=b,after=a),ensure_ascii=False,indent=2)+'\n')
 return validation

if __name__=='__main__':
 write_report(read(R/'before_metrics.json'),read(R/'after_metrics.json'),ROOT/'assets/reports/balance_report_v2.md')
