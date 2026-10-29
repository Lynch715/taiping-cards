#!/usr/bin/env python3
"""Final18 checks; conditionally adopt a price-only conservative variant."""
import argparse,csv,json,statistics,hashlib,zipfile,subprocess
from pathlib import Path
from feast_closeout import ROOT,R,BASE,read,sha
from closeout_acceptance import acceptance
from early_feast_assessment import assess
def writecsv(path,rows):
 with path.open('w',newline='',encoding='utf-8')as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def table(head,rows):return '\n'.join(['|'+'|'.join(head)+'|','|'+'|'.join(['---']*len(head))+'|']+['|'+'|'.join(str(v)for v in r)+'|'for r in rows])+'\n'
def q(values,p):
 a=sorted(values);i=(len(a)-1)*p;j=int(i);return a[j]+(a[min(j+1,len(a)-1)]-a[j])*(i-j)
def main(apply=False,release=False):
 original=read(BASE/'behavior.json');trial=read(R/'price_x3/behavior.json');groups={'original':original,'price_x3':trial};results={k:acceptance(v)for k,v in groups.items()};early=assess(original,trial)
 assert len(original['runs'])==len(trial['runs'])==24 and {(r['campaign'],r['seed'])for r in original['runs']}=={(r['campaign'],r['seed'])for r in trial['runs']}
 oldtables=read(BASE/'inputs/tables.json');newtables=read(R/'price_x3/inputs/tables.json');expected=read(BASE/'inputs/tables.json')
 for row in expected['feast']:
  if row['profile']=='conservative':row['silver']*=3
 assert newtables==expected,'Comparison changed more than conservative silver prices'
 assert len(read(R/'logging_identity.json'))==2 and all(r['identical_except_new_observation']for r in read(R/'logging_identity.json'))
 for key,d in groups.items():
  folder=BASE/'inputs'if key=='original'else R/'price_x3/inputs'
  for p in (R/'before/data').glob('*.csv'):
   if key=='original'or p.name!='feast.csv':assert sha(p)==sha(folder/p.name)
  for run in d['runs']:
   assert run['cleared']==48 and {c['chapter']for c in run['chapters']}==set(range(1,9));assert abs(sum(c['duration']for c in run['chapters'])-run['days'])<1e-9;assert run['max_daily_sweeps']<=30
   totals={}
   for purchase in run['feast_purchases']:
    ch=purchase['chapter'];assert purchase['exp']==ch*1000 and purchase['silver']==ch*(8000 if key=='original'else 24000)
    day=int(purchase['day']);totals[day]=totals.get(day,0)+1
   assert max(totals.values(),default=0)<=1
 selection={'selected_price_multiplier':3 if results['price_x3']['all_pass']and early['pass']else 1,'original_all18_pass':results['original']['all_pass'],'price_x3_all18_pass':results['price_x3']['all_pass'],'price_x3_no_early_slowdown':early['pass'],'early_affected_accounts':early['affected_accounts']}
 manifest=read(R/'before/manifest.json');protected=[]
 for path,h in manifest.items():
  if path.startswith('data/')and path!='data/feast.csv':assert sha(ROOT/path)==h;protected.append(path)
 target=BASE/'inputs/feast.csv'if selection['selected_price_multiplier']==1 else R/'price_x3/inputs/feast.csv'
 if apply and (ROOT/'data/feast.csv').read_bytes()!=target.read_bytes():
  (ROOT/'data/feast.csv').write_bytes(target.read_bytes());subprocess.run(['python3','tools/export_data.py'],cwd=ROOT,check=True)
 assert sha(ROOT/'data/feast.csv')==sha(target),'UI table does not match conditional selection'
 for path in ['app/src/core/progression.ts','app/src/ui/GrowthPages.tsx']:assert sha(ROOT/path)==manifest[path],'Product growth/UI code should remain unchanged'
 if apply:(R/'selection.json').write_text(json.dumps(selection,ensure_ascii=False,indent=2))
 writecsv(R/'early_paired_chapters.csv',early['rows']);(R/'early_assessment.json').write_text(json.dumps(early,ensure_ascii=False,indent=2));(R/'acceptance.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
 for key,m in results.items():writecsv(R/(key+'_chapter_acceptance.csv'),m['chapters']);writecsv(R/(key+'_campaign_acceptance.csv'),m['campaigns'])
 paired=[];balances=[];times=[];old={(r['campaign'],r['seed']):r for r in original['runs']}
 for run in trial['runs']:
  a=old[run['campaign'],run['seed']];paired.append({'campaign':run['campaign'],'seed':run['seed'],'original_days':a['days'],'price_x3_days':run['days'],'original_silver':a['chapters'][-1]['remaining']['silver'],'price_x3_silver':run['chapters'][-1]['remaining']['silver'],'original_feast_silver':sum(p['silver']for p in a['feast_purchases']),'price_x3_feast_silver':sum(p['silver']for p in run['feast_purchases'])})
 for key,d in groups.items():
  for camp in ['taiping','qing']:
   own=[r for r in d['runs']if r['campaign']==camp];values=[r['chapters'][-1]['remaining']['silver']for r in own];days=[r['days']for r in own]
   balances.append({'group':key,'campaign':camp,'minimum':min(values),'p25':q(values,.25),'median':statistics.median(values),'p75':q(values,.75),'maximum':max(values),'mean_feast_silver':statistics.mean(sum(p['silver']for p in r['feast_purchases'])for r in own)})
   times.append({'group':key,'campaign':camp,'minimum_days':min(days),'p25_days':q(days,.25),'median_days':statistics.median(days),'p75_days':q(days,.75),'maximum_days':max(days),'mean_days':statistics.mean(days)})
 writecsv(R/'paired_accounts.csv',paired);writecsv(R/'silver_distribution.csv',balances);writecsv(R/'completion_days.csv',times)
 audit={'protected_tables':protected,'feast_price_selected':selection['selected_price_multiplier'],'all96_stages_unchanged':True,'all48_assumptions_unchanged':True,'price_only_intervention':True,'same24_seeds':True,'before_hashes':{k:v for k,v in manifest.items()if k.startswith('data/')},'after_hashes':{str(p.relative_to(ROOT)):sha(p)for p in(ROOT/'data').glob('*.csv')},'baseline_replay_sha256':sha(BASE/'behavior.json'),'comparison_replay_sha256':sha(R/'price_x3/behavior.json')};audit['unchanged_csv_tables']=[p for p,h in audit['before_hashes'].items()if audit['after_hashes'][p]==h];audit['unchanged_csv_count']=len(audit['unchanged_csv_tables']);(R/'scope_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2))
 names={'original':'保守原价','price_x3':'保守三倍价','taiping':'太平','qing':'清军'};chosen=names['price_x3'if selection['selected_price_multiplier']==3 else'original'];lines=['# v0.4.2 收尾：最终验收与犒军单价对照','',f"**正式采用：{chosen}，每日1次，每次{24000 if selection['selected_price_multiplier']==3 else 8000:,}×章节银两换1,000×章节军功。** 48关等级曲线沿用v0.4.2；96关配置和全部原产出、精铁、将魂、每日总30次/单关3次扫荡规则均保持。",'',table(['方案','章节判定','主线总时长判定','18项全部通过','早期无价格受阻'],[[names[k],f"{v['chapter_pass_count']}/16",f"{v['campaign_pass_count']}/2",'是'if v['all_pass']else'否','基线'if k=='original'else('是'if early['pass']else'否')]for k,v in results.items()]),'', '## 最终口径与切价条件','', '- 章：平均耗时≤目标×1.25，至少10/12账号本章所有单关等待≤2天，全部账号≤3天；不再设置章耗时下限。','- 主线：分别检查两阵营12账号总通关天数中位数≥13.9天。按用户明确给出的13.9判定，不下调为13.875。','- 单价对照只把保守版银两价格从8,000×章节改为24,000×章节；军功1,000×章节、每日1次、养成优先顺序均不变。仍用原24账号与原战斗种子。原价结果复用上轮完整冻结回放；追加两个完整账号重放验证新记录代码不改变旧结果，全部原字段逐项一致。','- 第1–2章按同账号配对：原价可买而三倍价买不起，且实际章节完成更晚，或在同日完成时五人均级更低，记为价格导致的成长受阻。仅暂时买不起不直接失败；更早通关时的较低等级不记为成长变慢。','- 三倍价须同时满足18项全部通过且无上述早期受阻才采用；否则界面保留原价。','']
 if not selection['selected_price_multiplier']==3:
  failed='、'.join(names[c['campaign']]+'第'+str(c['chapter'])+'章'for c in results['price_x3']['chapters']if not c['pass'])or'无'
  at=lines.index('## 最终口径与切价条件');lines[at:at]=[f"三倍价未通过的章节：{failed}；前两章价格受阻账号：{early['affected_accounts']}个。依照切价条件保留原价。",'']
 for key,m in results.items():
  lines+=['## '+names[key]+'：16项章节判定','',table(['阵营/章','平均天数上限','实际平均天数','≤2天账号','最长等待','判定'],[[names[c['campaign']]+'/'+str(c['chapter']),f"{c['maximum_mean_days']:g}",f"{c['mean_days']:.3f}",f"{c['accounts_wait_le2']}/12",f"{c['max_wait_days']:g}",'通过'if c['pass']else'未过']for c in m['chapters']]),'', '### 2项主线总时长判定','',table(['阵营','中位数下限','实际中位数','最少/最多天数','判定'],[[names[c['campaign']],'13.9',f"{c['median_days']:g}",f"{c['minimum_days']:g} / {c['maximum_days']:g}",'通过'if c['pass']else'未过']for c in m['campaigns']]),'']
 affected=[r for r in early['rows']if r['growth_slowed_after_price_block']];lines+=['## 第1–2章：是否因价格成长受阻','',f"24账号中，{early['temporarily_blocked_accounts']}个出现过原价能买而三倍价买不起；其中{early['affected_accounts']}个账号出现符合上述定义的实际成长受阻。逐账号、逐章配对见early_paired_chapters.csv，原始购买记录见price_x3/。",'']
 if affected:lines+=[table(['阵营/种子','章','原价/三倍价完成日','原价/三倍价均级'],[[names[x['campaign']]+'/'+str(x['seed']),x['chapter'],f"{x['base_completion_day']:g} / {x['trial_completion_day']:g}",f"{x['base_mean_level']:g} / {x['trial_mean_level']:g}"]for x in affected]),'三倍价未满足“早期无受阻”条件，因此保留原价。']
 lines+=['', '## 通关后银两分布','',table(['方案/阵营','最少','P25','中位数','P75','最多','平均犒军花费'],[[names[b['group']]+'/'+names[b['campaign']],*[f"{b[k]:,.0f}"for k in ['minimum','p25','median','p75','maximum','mean_feast_silver']]]for b in balances]),'分位数对12账号排序后线性插值；余额差异包含购买成本与通关时长造成的收益变化。','', '## 总通关天数分布','',table(['方案/阵营','最少','P25','中位数','P75','最多','平均'],[[names[t['group']]+'/'+names[t['campaign']],*[f"{t[k]:.3f}"for k in ['minimum_days','p25_days','median_days','p75_days','maximum_days','mean_days']]]for t in times]),'24账号的两组通关天数、银两余额和犒军花费逐项放在paired_accounts.csv；两组均保留完整实战记录，不替换种子或剔除尾部账号。','', '## 证据','', '- acceptance.json：两组16项＋2项判定；selection.json：条件选择结果。','- scope_audit.json：96关、48假设及产出表哈希；baseline/inputs/与price_x3/inputs/：冻结输入。','- logging_identity.json：原价两个完整重放账号的全部原字段逐项一致；新增记录只观察，不反馈资源或消耗随机数。','- early_assessment.json、early_paired_chapters.csv：购买受阻与实际章节配对；同资源原价补买一次的局部升级记录只作机制解释，不反馈到实际回放。']
 if release:
  tests=(R/'frontend_tests.log').read_text();py=(R/'python_tests.log').read_text();assert '59 passed (59)'in tests and 'Ran 110 tests'in py and '\nOK\n'in py
  golden=read(ROOT/'assets/reports/economy_v042/golden/comparison.json');assert golden['passed']==100 and golden['failed']==0
  dist=ROOT/'app/dist';deploy=ROOT/'release/taiping-web';files={str(p.relative_to(dist)):sha(p)for p in dist.rglob('*')if p.is_file()};assert files=={str(p.relative_to(deploy)):sha(p)for p in deploy.rglob('*')if p.is_file()}
  zpath=ROOT/'release/taiping-web-0.4.2.zip'
  with zipfile.ZipFile(zpath)as z:assert files=={n:hashlib.sha256(z.read(n)).hexdigest()for n in z.namelist()}
  meta=read(dist/'pwa-build.json');assert meta['firstInstallUpperBound']<=10000000;(R/'release_audit.json').write_text(json.dumps({'version':meta['version'],'selected_price_multiplier':selection['selected_price_multiplier'],'zip_sha256':sha(zpath),'first_install_upper_bound':meta['firstInstallUpperBound'],'zip_deploy_match':True,'python_tests':110,'frontend_tests':59,'golden_cases':100,'golden_lines':golden['log_lines']},indent=2));lines+=['',f"回归：Python110项、前端59项通过；100组金标准共{golden['log_lines']:,}行一致。v0.4.2静态包已重新打包并与部署目录逐文件校验，首次安装保守上限{meta['firstInstallUpperBound']/1e6:.3f}MB。"]
 (ROOT/'assets/reports/economy_report_v042_final.md').write_text('\n'.join(lines)+'\n');print(json.dumps({'results':{k:{'chapters':m['chapter_pass_count'],'campaigns':m['campaign_pass_count']}for k,m in results.items()},'selection':selection},ensure_ascii=False))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');p.add_argument('--release',action='store_true');a=p.parse_args();main(a.apply,a.release)
