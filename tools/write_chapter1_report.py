#!/usr/bin/env python3
import json,csv,hashlib
from battle_sim import ROOT,read_csv
R=ROOT/'assets/reports/m1/chapter1';x=json.loads((R/'difficulty.json').read_text());old={r['stage_id']:r for r in read_csv(R/'stages_before.csv')};current=read_csv(ROOT/'data/stages.csv');heroes={r['id']:r for r in read_csv(ROOT/'data/heroes.csv')}
changes=[]
for r in current:
 for k,v in r.items():
  if old[r['stage_id']][k]!=v:changes.append({'id':r['stage_id'],'column':k,'before':old[r['stage_id']][k],'after':v})
assert len(changes)==12 and all(r['column']=='enemy_level' for r in changes)
lines=['# M1 第一章难度报告','','状态：两条战役线共12关的独立复核点估计全部达标。只调整stages.csv的enemy_level，人物、技能、羁绊、装备数值未改。用户已确认允许0.1级步进。','','## 固定条件','','- 玩家固定10级，SSR3星/SR2星/R1星；开局1君主+7战斗卡，选5人，前2后3；不带装备或专属。','- 杂兵用enemy_units.csv，只有普攻；首领用heroes.csv及完整技能、羁绊、宿敌。重复杂兵按(side,slot)区分。','- 玩家始终为进攻方，不用攻守镜像代替关卡难度；20回合未决按玩家失败。地形和敌阵保持原表。','- 两端共用mulberry32。先训练选级，再用独立种子验证；最终结果见下，不把训练胜率当验证胜率。','','|战役/关卡|原等级|定稿等级|目标|独立样本|玩家胜率|95% Wilson区间|判定|','|---|---:|---:|---|---:|---:|---|---|']
for r in x['stages']:
 v=r['validation'];lo,hi=r['target'];ci=v['wilson95'];goal=f'{lo*100:.0f}–{hi*100:.0f}%' if lo<.95 else '≥95%';name=('太平' if r['campaign']=='taiping' else '清朝')+' · '+r['name']
 lines.append(f"|{name}|{old[r['stage_id']]['enemy_level']}|{r['enemy_level']}|{goal}|{v['n']}|{v['rate']*100:.2f}%|{ci[0]*100:.2f}–{ci[1]*100:.2f}%|{'通过' if r['pass'] else '未通过'}|")
lines+=['',f"最终独立验收合计{sum(r['validation']['n'] for r in x['stages']):,}局。目标按点估计判定，不要求整个区间都落入目标带。",'','## 编队与搜索范围','','每关首轮完整筛查7P5=2520种有序编队，每种4个训练种子，24强各96局复核；之后用256个训练种子选择敌方等级。临界关再在实际敌方等级完整复筛2520种编队（每种8个种子），32强各512局复核。此后只细调等级，不回头用最终验收种子挑编队。所得是样本搜索找到的经验最佳候选，并非数学证明的全局最优。','','|关卡|前排1 / 前排2|后排1 / 后排2 / 后排3|最终验证起始种子|','|---|---|---|---:|']
for r in x['stages']:
 names=[heroes[i]['name'] for i in r['formation']];lines.append(f"|{r['name']}|{' / '.join(names[:2])}|{' / '.join(names[2:])}|{r['validation_seed']}|")
lines+=['','## 临界关与修订记录','','首轮和后续整数试调的未通过记录保留在difficulty_round1.json、difficulty_round2.json、difficulty_integer_rounds.json。没有删除失败轮次。','', '围攻桂林和蓑衣渡的相邻整数等级使胜率跨过目标带，因此在用户明确允许后，按0.1级重新训练、选择并用3000个独立种子验收；最终为36.7/38.6级。靖港则在重新搜索编队后用整数51级达标。','', 'enemy_level不要求随关号单调递增：敌方兵种、地形、首领稀有度及初始星级不同。首领有正式技能，杂兵无技能；不能仅用关号或等级数字比较敌阵强度。','', '史实结果不同的关卡，胜利军报保留原表对史实的说明；靖港仍按50–65%的专项目标判定。','','## 每处数据变更','','|关卡ID|字段|原值|新值|','|---|---|---:|---:|']
for c in changes:lines.append(f"|{c['id']}|{c['column']}|{c['before']}|{c['after']}|")
lines+=['','## 复现与证据','','- difficulty.json及逐关JSON：编队、训练等级、全部验证胜率与种子。','- tools/tune_chapter1.py、refine_chapter1.py、reoptimize_chapter1.py、tune_chapter1_tenths.py：各阶段脚本；靖港51级补验脚本保存在本报告目录。','- stages_before.csv：调整前原表；最终游戏数据由tools/export_data.py生成。','',f"最终stages.csv SHA256：`{hashlib.sha256((ROOT/'data/stages.csv').read_bytes()).hexdigest()}`。"]
(ROOT/'assets/reports/m1/chapter1_difficulty_report.md').write_text('\n'.join(lines)+'\n');(R/'changes.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2)+'\n')
