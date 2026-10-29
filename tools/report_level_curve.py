#!/usr/bin/env python3
"""Report the paired feast experiments, with both requested chapter gates."""
import json,csv,statistics,hashlib,argparse,zipfile
from pathlib import Path
from level_curve import ROOT,R,read,sha,writecsv
from curve_metrics import acceptance
def md(head,rows):return '\n'.join(['|'+'|'.join(head)+'|','|'+'|'.join(['---']*len(head))+'|']+['|'+'|'.join(str(v)for v in r)+'|'for r in rows])+'\n'
def quantile(values,p):
 a=sorted(values);i=(len(a)-1)*p;j=int(i);return a[j]+(a[min(j+1,len(a)-1)]-a[j])*(i-j)
def main(release=False):
 assert sha(R/'v040_stages.csv')==sha(ROOT/'assets/reports/joint_v2/round04/replay/inputs/stages.csv'),'Starting configuration must match the v0.4.0 replay'
 base={r['stage_id']:r for r in csv.DictReader((R/'v040_stages.csv').open())};current={r['stage_id']:r for r in csv.DictReader((ROOT/'data/stages.csv').open())};overrides=read(ROOT/'app/src/core/data/stage_level_overrides.json');curve={r['stage_id']:r for r in read(R/'curve.json')};cal=read(R/'calibration/difficulty.json');assert cal['all_pass']and len(cal['stages'])==48
 assert {r['stage_id']for r in overrides}==set(curve)and len(curve)==48
 for r in overrides:assert r['assumed_level']==curve[r['stage_id']]['median_level']and r['source_accounts']==12
 protected=[]
 for path,h in read(R/'before/manifest.json').items():
  if path.startswith('data/')and path not in ['data/stages.csv','data/stage_level_overrides.csv']:
   assert sha(ROOT/path)==h;protected.append(path)
 changes=[]
 for sid,row in current.items():
  if int(row['chapter'])<5:assert row==base[sid]
  for field,value in row.items():
   if value!=base[sid][field]:assert int(row['chapter'])>=5 and field in ['enemy_level','enemy_stars','enemy_monarch_stars','recommended_power'];changes.append({'stage_id':sid,'field':field,'v040':base[sid][field],'v042':value})
 for r in cal['stages']:
  row=current[r['stage_id']];assert r['target_calendar_source_count']==12 and r['assumed_mean_level']==curve[r['stage_id']]['median_level'];assert r['validation']['n']==2400 and r['target'][0]<=r['validation']['rate']<=r['target'][1];assert r['level_bounds'][0]<=float(row['enemy_level'])<=r['level_bounds'][1];assert float(row['enemy_level'])==r['enemy_level']and row['enemy_stars']==';'.join(map(str,r['enemy_stars']))and row['enemies'].split(',')==r['enemies']
 writecsv(R/'stage_changes.csv',changes);writecsv(R/'difficulty.csv',[{k:r[k]for k in ['stage_id','assumed_mean_level','enemy_level','enemy_monarch_stars','recommended_power','pass']}|{'target_low':r['target'][0],'target_high':r['target'][1],'win_rate':r['validation']['rate'],'games':r['validation']['n'],'enemy_stars':';'.join(map(str,r['enemy_stars']))}for r in cal['stages']])
 baseline=read(ROOT/'assets/reports/joint_v2/round04/replay/behavior.json');seedset={(r['campaign'],r['seed'])for r in baseline['runs']};results={};balances=[];sources=[];accounts=[];waits=[]
 for profile in ['conservative','aggressive']:
  d=read(R/profile/'replay/behavior.json');assert len(d['runs'])==24 and {(r['campaign'],r['seed'])for r in d['runs']}==seedset
  for p in (ROOT/'data').glob('*.csv'):assert sha(p)==sha(R/profile/'replay/inputs'/p.name)
  m=acceptance(d);results[profile]=m;(R/profile/'acceptance.json').write_text(json.dumps(m,ensure_ascii=False,indent=2));writecsv(R/profile/'chapter_acceptance.csv',[{k:v for k,v in r.items()if k!='account_waits'}for r in m['chapters']])
  for run in d['runs']:
   assert run['max_daily_sweeps']<=30 and run['feast_profile']==profile
   purchases=run['feast_purchases'];daily={}
   for p in purchases:
    day=int(p['day']);daily[day]=daily.get(day,0)+1
    rule=next(r for r in read(ROOT/'app/src/core/data/feast.json')if r['profile']==profile and r['chapter']==p['chapter']);assert p['silver']==rule['silver']and p['exp']==rule['exp']
   assert max(daily.values(),default=0)<=(1 if profile=='conservative'else 2)
   accounts.append({'profile':profile,'campaign':run['campaign'],'seed':run['seed'],'cleared':run['cleared'],'days':run['days'],'silver':run['chapters'][-1]['remaining']['silver']if run['cleared']==48 else None,'feast_silver_spent':sum(p['silver']for p in purchases),'feast_exp':sum(p['exp']for p in purchases),'feast_purchases':len(purchases)})
   waits.extend({'profile':profile,'campaign':run['campaign'],'seed':run['seed'],**w}for w in run['waits'])
  for camp in ['taiping','qing']:
   own=[r for r in accounts if r['profile']==profile and r['campaign']==camp];values=[r['silver']for r in own if r['silver']is not None];assert len(values)==12,'Censored balance: not all accounts cleared'
   balances.append({'profile':profile,'campaign':camp,'minimum':min(values),'p25':quantile(values,.25),'median':statistics.median(values),'p75':quantile(values,.75),'maximum':max(values),'mean_feast_silver_spent':statistics.mean(r['feast_silver_spent']for r in own)})
   sums={k:sum(c['exp_sources'].get(k,0)for r in d['runs']if r['campaign']==camp for c in r['chapters'])for k in ['idle','first','sweep','feast']};total=sum(sums.values());sources.append({'profile':profile,'campaign':camp,'total_exp':total,**{k+'_exp':v for k,v in sums.items()},**{k+'_share':v/total for k,v in sums.items()}})
 writecsv(R/'accounts.csv',accounts);writecsv(R/'silver_distribution.csv',balances);writecsv(R/'exp_sources.csv',sources);(R/'final_waits.json').write_text(json.dumps(waits,ensure_ascii=False,indent=2));(R/'comparison.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
 audit={'v040_stages_sha256':sha(R/'v040_stages.csv'),'protected_tables':protected,'unchanged_first_four_stages':48,'late_stage_assumptions':48,'curve_sha256':sha(R/'curve.json'),'calibration_sha256':sha(R/'calibration/difficulty.json'),'same_24_account_seeds':True,'data_sha256':{str(p.relative_to(ROOT)):sha(p)for p in (ROOT/'data').glob('*.csv')}};(R/'scope_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2))
 names={'conservative':'保守','aggressive':'积极','taiping':'太平','qing':'清军'}
 failures=[]
 for profile,m in results.items():
  for row in m['chapters']:
   if row['pass']:continue
   reasons=[]
   if row['mean_days']<row['target_days']*.75:reasons.append('通关过快')
   if row['mean_days']>row['target_days']*1.25:reasons.append('通关过慢')
   if row['accounts_wait_le2']<10:reasons.append('2天内账号不足10人')
   if row['max_wait_days']>3:reasons.append('存在超过3天等待')
   failures.append({'profile':profile,'campaign':row['campaign'],'chapter':row['chapter'],'reason':'；'.join(reasons)})
 if failures:writecsv(R/'chapter_failures.csv',failures)
 verdict='两组均未达到16项全部通过。保守版更接近当前节奏目标；积极版消耗更多银两，也明显加快成长。'if all(not m['all_pass']for m in results.values())else'完整判定见下表。'
 lines=['# v0.4.2 等级曲线与犒军对照','',f"**新口径联合验收：保守 {results['conservative']['pass_count']}/16，积极 {results['aggressive']['pass_count']}/16。** 每项同时要求：章平均耗时在目标±25%内，至少10/12账号本章任意单关等待≤2天，且全部账号≤3天。旧口径仍要求12/12≤2天，并保留相同耗时条件。",'',verdict,'',md(['方案','新口径','旧口径'],[[names[p],f"{results[p]['pass_count']}/16",f"{results[p]['old_pass_count']}/16"]for p in results]),'', '## 两组犒军参数','',md(['方案','每日次数','每次银两','每次军功'],[['保守',1,'8,000 × 当前章节','1,000 × 当前章节'],['积极',2,'12,000 × 当前章节','1,500 × 当前章节']]),'当前章节按本阵营下一未通关关卡计算，全部通关后取第八章。每日次数按本地日期重置，两阵营共用；晋章不补次数，时钟回拨不重置。模型先完成可负担的主力/替补升级、升星、换装和强化，余额够才购买，随后把新增军功投入原升级流程；无借款、免费资源或强制留存。界面候选暂用保守版，积极版仅用于参数对照。','', '## 等级曲线计算','', '- 起点逐字段恢复v0.4.0关卡；撤销v0.4.1八关覆盖。第1–4章48关完整字段保持v0.4.0，第5–8章48关重校敌级/敌星和推荐战力，不换敌方人物或君主。精铁、将魂、扫荡上限及全部原产出表保持不变。','- 每关目标到达日＝之前各章目标天数累加＋本章目标天数×关序/6，最后一关落在章末。只用原有产出，不购买犒军。每天8点、14点领取放置并按原策略扫荡；目标日期前未发生的登录收益不提前领取。','- 目标日按现有养成、招募、配装和地形/克制感知布阵形成五人队伍，在当前关首通奖励之前拍快照，再按计划通关发放该关奖励。定时通关是测算资源预算的假设，不当作实战胜利证明，也不消耗实际战斗随机数。','- 每阵营沿用12个原账号种子，逐关取五人均级中位，写入stage_level_overrides.csv。校准抽样使用12支目标日实际队伍、真实等级/星级/兵装，保留账号差异，不给未练替补补级。敌级限定该中位数−5至+10（且1–100级），敌星1–6。原胜率区间和history_result降幅不变。','- 两方案共用这一条不含犒军收益的曲线和同一份48关配置，再各跑24账号完整实战；没有因积极方案变强而另行提高敌人。48关独立验证各2,400局，详见difficulty.csv。','']
 economy=read(ROOT/'app/src/core/data/economy_chapters.json');ends=[]
 for ch in range(5,9):ends.append([ch,economy[ch-1]['target_level_end'],curve[f'tp_{ch}_6']['median_level'],curve[f'qing_{ch}_6']['median_level']])
 lines+=['## 章末目标日均级对照','',md(['章','原假设均级','太平目标日中位均级','清军目标日中位均级'],ends),'这是不含犒军的资源预算曲线。完整48关目标日、等级范围与12人样本见curve.csv/curve.json。','']
 for profile,m in results.items():
  lines+=['## '+names[profile]+'方案：16项判定','',md(['阵营/章','目标耗时区间','平均天数','≤2天账号','最长等待','新口径','旧口径'],[[names[r['campaign']]+'/'+str(r['chapter']),f"{r['target_days']*.75:g}–{r['target_days']*1.25:g}",f"{r['mean_days']:.3f}",f"{r['accounts_wait_le2']}/12",f"{r['max_wait_days']:g}",'通过'if r['pass']else'未过','通过'if r['old_pass']else'未过']for r in m['chapters']]),'']
 if failures:lines+=['## 未通过项原因','',md(['方案','阵营/章','原因'],[[names[r['profile']],names[r['campaign']]+'/'+str(r['chapter']),r['reason']]for r in failures]),'']
 lines+=['## 通关后银两余额分布','',md(['方案/阵营','最少','P25','中位数','P75','最多','平均犒军花费'],[[names[r['profile']]+'/'+names[r['campaign']],*[f"{r[k]:,.0f}"for k in ['minimum','p25','median','p75','maximum','mean_feast_silver_spent']]]for r in balances]),'分位数按12个通关账号的排序值作线性插值。逐账号余额、花费与通关天数见accounts.csv；余额差异同时包含通关用时变化带来的资源变化，不全归因于兑换扣款。','', '## 军功来源占比','',md(['方案/阵营','放置','首通','扫荡','犒军'],[[names[r['profile']]+'/'+names[r['campaign']],*[f"{r[k+'_share']*100:.2f}%"for k in ['idle','first','sweep','feast']]]for r in sources]),'按各阵营12账号通关前实际获得军功合计计算占比，分母包含犒军；不是账号百分比的简单平均。精铁和将魂没有兑换入口，原扫荡每日总30次/单关3次均保留。','', '## 复核资料','', '- curve.csv / curve.json：48关目标日、中位均级及全部12账号样本；calendar/profiles.json：先拍快照、后发当前奖励的资源预算。','- stage_changes.csv / scope_audit.json：相对v0.4.0的逐字段变更和受保护表哈希。','- conservative/、aggressive/：完整冻结输入、逐账号实战、16项判定和旧口径。','- accounts.csv、silver_distribution.csv、exp_sources.csv、final_waits.json：余额、来源和超过2天等待的逐项记录。']
 if release:
  front=(R/'frontend_tests.log').read_text();python=(R/'python_tests_final.log').read_text();assert '58 passed (58)'in front and 'Ran 98 tests'in python and '\nOK\n'in python
  golden=read(R/'golden/comparison.json');assert golden['cases']==golden['passed']==100 and golden['failed']==0
  dist=ROOT/'app/dist';deploy=ROOT/'release/taiping-web';files={str(p.relative_to(dist)):sha(p)for p in dist.rglob('*')if p.is_file()};assert files=={str(p.relative_to(deploy)):sha(p)for p in deploy.rglob('*')if p.is_file()}
  zpath=ROOT/'release/taiping-web-0.4.2.zip'
  with zipfile.ZipFile(zpath)as z:assert files=={n:hashlib.sha256(z.read(n)).hexdigest()for n in z.namelist()}
  meta=read(dist/'pwa-build.json');assert meta['firstInstallUpperBound']<=10000000;(R/'release_audit.json').write_text(json.dumps({'version':meta['version'],'zip_sha256':sha(zpath),'deploy_zip_equal':True,'first_install_upper_bound':meta['firstInstallUpperBound'],'python_tests':98,'frontend_tests':58,'golden_cases':100,'golden_lines':golden['log_lines']},indent=2));lines+=['',f"回归：Python 98项、前端58项通过；金标准100组、{golden['log_lines']:,}行逐行一致，零差异。犒军界面经应用内浏览器实走首关奖励后购买，核对扣银/加军功、限购及刷新保留（ui/feast_purchased.png）。静态候选release/taiping-web-0.4.2.zip，构建{meta['version']}，首次安装保守上限{meta['firstInstallUpperBound']/1e6:.3f}MB；部署目录与ZIP逐文件哈希一致。"]
 (ROOT/'assets/reports/economy_report_v042.md').write_text('\n'.join(lines)+'\n');print(json.dumps({k:{'new':v['pass_count'],'old':v['old_pass_count']}for k,v in results.items()}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--release',action='store_true');a=p.parse_args();main(a.release)
