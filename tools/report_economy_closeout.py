#!/usr/bin/env python3
"""One acceptance headline only: chapter mean pace AND each account's longest wait."""
import csv,json,statistics,hashlib,zipfile,argparse
from pathlib import Path
from economy_closeout import ROOT,R,read,sha,joint_metrics,writecsv

def table(head,rows):return '\n'.join(['|'+'|'.join(head)+'|','|'+'|'.join(['---']*len(head))+'|']+['|'+'|'.join(str(c)for c in row)+'|'for row in rows])+'\n'
def main(release=False):
 before=read(ROOT/'assets/reports/joint_v2/round04/replay/behavior.json');after=read(R/'replay_final/behavior.json');old=joint_metrics(before);new=joint_metrics(after);scope=read(R/'scope.json')['targets'];medians=read(R/'first_challenge_medians.json');cal=read(R/'calibration/difficulty.json');assert cal['all_pass'];assert {(r['campaign'],r['seed'])for r in before['runs']}=={(r['campaign'],r['seed'])for r in after['runs']};assert len(after['runs'])==24
 protected=[]
 for name,h in read(R/'before/manifest.json').items():
  if name.startswith('data/')and name!='data/stages.csv':assert sha(ROOT/name)==h;protected.append(name)
 oldrows={r['stage_id']:r for r in csv.DictReader((R/'before/data/stages.csv').open())};rows=list(csv.DictReader((ROOT/'data/stages.csv').open()));newrows={r['stage_id']:r for r in rows};changes=[]
 for row in rows:
  oldrow=oldrows[row['stage_id']]
  for k,v in row.items():
   if v!=oldrow[k]:assert row['stage_id']in scope and k in {'enemy_level','enemy_stars','enemy_monarch_stars','recommended_power'};changes.append({'stage_id':row['stage_id'],'field':k,'before':oldrow[k],'after':v})
 untouched=[s for s in newrows if s not in scope];assert len(untouched)==88 and all(newrows[s]==oldrows[s]for s in untouched)
 overrides={r['stage_id']:float(r['assumed_level'])for r in csv.DictReader((ROOT/'data/stage_level_overrides.csv').open())};assert set(overrides)==set(scope)
 for sid,v in overrides.items():assert v==medians[sid]['median']
 calibration={r['stage_id']:r for r in cal['stages']};stage_summary=[]
 econ=read(ROOT/'app/src/core/data/economy_chapters.json')
 for sid in scope:
  row=newrows[sid];x=calibration[sid];mean=overrides[sid];assert x['assumed_mean_level']==mean and x['first_challenge_source_count']==12;assert x['level_bounds'][0]<=float(row['enemy_level'])<=x['level_bounds'][1];assert x['target'][0]<=x['validation']['rate']<=x['target'][1];assert row['enemies'].split(',')==x['enemies'];assert float(row['enemy_level'])==x['enemy_level'];assert row['enemy_stars']==';'.join(map(str,x['enemy_stars']));ch=int(row['chapter']);order=int(row['order']);start=10 if ch==1 else econ[ch-2]['target_level_end'];oldmean=start+(econ[ch-1]['target_level_end']-start)*(order-1)/5
  stage_summary.append({'stage_id':sid,'name':row['name'],'first_accounts':12,'old_assumed_mean':round(oldmean,1),'new_assumed_mean':mean,'old_enemy_level':float(oldrows[sid]['enemy_level']),'new_enemy_level':float(row['enemy_level']),'old_enemy_stars':oldrows[sid]['enemy_stars'],'new_enemy_stars':row['enemy_stars'],'target_low':x['target'][0],'target_high':x['target'][1],'win_rate':x['validation']['rate'],'n':x['validation']['n'],'recommended_power':int(row['recommended_power'])})
 writecsv(R/'data_changes.csv',changes);writecsv(R/'changed_stages.csv',stage_summary);writecsv(R/'chapter_acceptance.csv',new['chapters'])
 waits=[{'campaign':r['campaign'],'seed':r['seed'],**w}for r in after['runs']for w in r['waits']];(R/'final_waits.json').write_text(json.dumps(waits,ensure_ascii=False,indent=2));(R/'acceptance.json').write_text(json.dumps(new,ensure_ascii=False,indent=2));audit={'protected_tables':protected,'untouched_stages':untouched,'changed_stage_ids':scope,'changes':changes,'baseline_reproduced_identically':all(r['identical_except_new_records']for r in read(R/'baseline_identity.json')),'data_sha256':{str(p.relative_to(ROOT)):sha(p)for p in(ROOT/'data').glob('*.csv')},'replay_sha256':sha(R/'replay_final/behavior.json')};(R/'scope_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2))
 release_info=None
 if release:
  dist=ROOT/'app/dist';deploy=ROOT/'release/taiping-web';files={str(p.relative_to(dist)):sha(p)for p in dist.rglob('*')if p.is_file()};assert files=={str(p.relative_to(deploy)):sha(p)for p in deploy.rglob('*')if p.is_file()};zpath=ROOT/'release/taiping-web-0.4.1.zip'
  with zipfile.ZipFile(zpath)as z:assert files=={n:hashlib.sha256(z.read(n)).hexdigest()for n in z.namelist()}
  meta=read(dist/'pwa-build.json');assert meta['firstInstallUpperBound']<=10000000;release_info={'version':meta['version'],'files':len(files),'zip_sha256':sha(zpath),'first_install_upper_bound':meta['firstInstallUpperBound'],'deploy_zip_equal':True};(R/'release_audit.json').write_text(json.dumps(release_info,indent=2))
 names={'taiping':'太平','qing':'清军'};status='通过'if new['all_pass']else'未通过';lines=['# v0.4.1 经济收尾（快速验收）','',f"**联合验收：{new['joint_pass_count']}/16，{status}。** 每一项必须同时满足章平均耗时在目标±25%内，且该阵营12个账号在本章任何单关等待均≤2天。沿用相同24账号（每阵营12个），v0.4.0同口径为{old['joint_pass_count']}/16；没有更换种子或单列平均耗时通过数。",'', '## 范围与取数','', '- 仅改指定5关及旧final_waits中出现≥2次的其余3关，共8关。其余88关完整字段保持；产出、每日扫荡总30次、将魂/升星、掉落、人物技能、装备与杂兵模板均逐字节不变。','- v0.4.0没有首挑战快照，因此先按原表原种子重放，只加记录；24个账号原有全部结果字段逐项复现一致，再取每关实际到达的12账号首挑战均级中位数。不是胜利等级，不把两阵营各12人误称为每关24人。','- 中位数只用于这8关的校准假设及−5至+10敌级边界，不改玩家升级、放置、扫荡选择或旧军册迁移。覆盖值固定来自旧基线，不随本轮结果滚动抬高。','- 校准直接使用已记录的12支首挑战队伍与装备，归一到中位均级，不替未训练替补免费补等级。五名整数等级武将的均级步长为0.2；遇到54.3等中位数，用相邻0.2档各半的12队保留总体均级，个人等级仍合法。胜率区间不变，敌方阵容/君主身份不变。','', '## 16项联合判定','',table(['阵营/章','目标天数区间','本轮平均天数','本章最长单关等待','联合判定'],[[names[r['campaign']]+'/'+str(r['chapter']),f"{r['target_days']*.75:g}–{r['target_days']*1.25:g}",f"{r['mean_days']:.3f}",f"{r['max_stage_wait']:g}",'通过'if r['pass']else'未过']for r in new['chapters']]),'', '## 8关校准','',table(['关卡','旧/新假设均级','旧/新敌级','旧/新敌星','目标胜率','本轮单局胜率'],[[r['stage_id'],f"{r['old_assumed_mean']:g} / {r['new_assumed_mean']:g}",f"{r['old_enemy_level']:g} / {r['new_enemy_level']:g}",r['old_enemy_stars'].replace(';','/')+' → '+r['new_enemy_stars'].replace(';','/'),f"{r['target_low']*100:g}–{r['target_high']*100:g}%",f"{r['win_rate']*100:.2f}% ({r['n']}局)"]for r in stage_summary]),'', '8关胜率目标与等级边界是配置检验；上表16项联合判定来自整条战役实际回放，两者不混为一个通过结论。', '', '## 已知问题：银两大量结余（本轮不处理）','']
 balances=[]
 for camp in ['taiping','qing']:
  values=[r['chapters'][-1]['remaining']['silver']for r in after['runs']if r['campaign']==camp];balances.append([names[camp],f'{min(values):,}',f'{statistics.median(values):,.0f}',f'{max(values):,}'])
 lines+=[table(['阵营','通关后最少银两','中位银两','最多银两'],balances),'银两规则与消耗本轮均未修改。后续可选：','', '1. **军需商店（实现较快）**：银两限购精铁或指定部位装备，按章节定价；收益容易理解，但需要另验装备/强化节奏。','2. **兵装重铸**：保留装备与强化，花银两重铸副属性；消耗持续，需限制属性上限并控制随机成本，开发和平衡工作更多。','3. **军营与军旗外观**：购买边框、军旗、陈设，不加战斗属性；数值风险低，消耗意愿取决于外观内容。','', '## 证据','', '- scope_audit.json：88关原样及全部受保护CSV哈希；data_changes.csv：逐字段变更。','- baseline_identity.json、first_challenge_medians.json：旧基线复现与12人中位数明细。','- chapter_acceptance.csv、final_waits.json：联合判定及全部超过2天的账号/关卡。','- calibration/：8关检验配置、种子、胜率与搜索轨迹。replay_final/inputs/：本轮完整输入冻结副本。']
 # Distinguish the scoped fix from the end-to-end acceptance result.
 wait_groups={sid:[w for w in waits if w['stage_id']==sid]for sid in sorted({w['stage_id']for w in waits})}
 assert not set(scope)&set(wait_groups), 'A scoped stage still has a long wait; update the diagnosis'
 diagnosis=['## 未通过原因','',f'本轮8个目标关均不再出现超过2天的等待；整条战役仍有{len(waits)}条长等待，分布在另外{len(wait_groups)}关。提前过关后，到达后续关卡的时间、等级、装备及将魂积累也会变化，因此局部降难度没有带来全程联合达标。下表均为本轮未修改关卡，保持原配置。','',table(['等待关卡','账号数','最长等待（天）'],[[sid,len(v),max(w['wait']for w in v)]for sid,v in wait_groups.items()]),'太平第八章还有通关过快的问题：平均1.625天，低于2.625天的下界；清军第八章平均5.208天，高于4.375天的上界。其余失败章见联合判定表。','', '这说明当前候选未通过验收，不代表已证明固定8关内不存在可行解。本轮保留可复核结果，未把新增等待关纳入修改范围。','']
 i=lines.index('## 已知问题：银两大量结余（本轮不处理）');lines[i:i]=diagnosis
 golden=read(R/'golden/comparison.json');assert golden['cases']==golden['passed']==100 and golden['failed']==0
 frontend=(R/'frontend_tests_final.log').read_text();python=(R/'python_tests.log').read_text();assert '51 passed (51)'in frontend and 'Ran 91 tests'in python and '\nOK\n'in python
 verification={'python_tests':91,'frontend_tests':51,'golden_cases':100,'golden_lines':golden['log_lines'],'golden_mismatches':0};(R/'verification.json').write_text(json.dumps(verification,indent=2));lines+=['',f"回归：Python 91项、前端51项通过；Python/TypeScript 100组金标准共{golden['log_lines']:,}行逐行一致，零差异。证据见python_tests.log、frontend_tests_final.log、golden/comparison.json。测试通过不替代上面的经济联合验收。"]
 if release_info:lines+=['',f"待验收静态候选包：release/taiping-web-0.4.1.zip；构建{release_info['version']}。部署目录与ZIP逐文件哈希一致，首次安装下载保守上限{release_info['first_install_upper_bound']/1e6:.3f}MB。经济联合验收未通过，未作为合格版本发布。"]
 (ROOT/'assets/reports/economy_report_v041.md').write_text('\n'.join(lines)+'\n');print(json.dumps({'joint':f"{new['joint_pass_count']}/16",'all_pass':new['all_pass'],'protected_tables':len(protected),'untouched_stages':88},ensure_ascii=False))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--release',action='store_true');a=p.parse_args();main(a.release)
