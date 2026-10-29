#!/usr/bin/env python3
"""Publish the current 96-stage calibration only after CSV/result consistency checks."""
import csv,json,hashlib,math,statistics
from pathlib import Path
from battle_sim import ROOT,read_csv
from m1_scenarios import game_data,assumed_level
from stage_difficulty import target
from calibrate_growth import power
R=ROOT/'assets/reports/chapters_3_8'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pct(n):return f'{100*n:.1f}%'
def table(header,rows):return '\n'.join(['|'+'|'.join(header)+'|','|'+'|'.join(['---']*len(header))+'|']+['|'+'|'.join(map(str,r))+'|'for r in rows])+'\n'
def report():
 early=json.loads((R/'early_verification/difficulty.json').read_text());late=json.loads((R/'calibration/difficulty.json').read_text());assert len(early['stages'])==24 and len(late['stages'])==72
 lookup={r['stage_id']:r for r in early['stages']+late['stages']};rows=read_csv(ROOT/'data/stages.csv');before={r['stage_id']:r for r in read_csv(R/'before/data/stages.csv')};assert len(lookup)==len(rows)==96
 d=game_data();metrics=[];changes=[]
 for row in rows:
  sid=row['stage_id'];x=lookup[sid];bounds=target(row);v=x['validation'];lo,hi=bounds
  assert list(bounds)==x['target'] and lo<=v['rate']<=hi and x['pass'],sid
  assert float(row['enemy_level'])==x['enemy_level'] and 1<=x['enemy_level']<=100,sid
  assert row['enemy_stars']==';'.join(map(str,x['enemy_stars'])),sid
  recommended=math.floor(statistics.mean(power(d,t) for t in x['profiles'])+.5);assert int(row['recommended_power'])==x['recommended_power']==recommended,sid
  assert abs(x['assumed_mean_level']-assumed_level(int(row['chapter']),int(row['order'])))<1e-8
  for t in x['profiles']:
   assert abs(statistics.mean(t['levels'])-x['assumed_mean_level'])<1e-8
   assert all(1<=s<=6 and 1<=lv<={1:35,2:50,3:65,4:80,5:95,6:100}[s] for s,lv in zip(t['stars'],t['levels']))
  if int(row['chapter'])<=2:assert row==before[sid],'Chapter1/2 configuration changed'
  for k,vv in row.items():
   if vv!=before[sid].get(k):
    assert k in {'enemy_level','recommended_power','enemy_stars','enemy_monarch_stars'},(sid,k)
    changes.append({'stage_id':sid,'name':row['name'],'field':k,'before':before[sid].get(k),'after':vv})
  offset=(0 if row['campaign']=='taiping'else 100000)+int(row['chapter'])*10000+int(row['order'])*1000
  seed=x.get('validation_seed') or ({0:1600000,1:2200000,2:3100000}[len(x.get('repairs',[]))]+offset)
  metrics.append({'stage_id':sid,'campaign':row['campaign'],'chapter':int(row['chapter']),'order':int(row['order']),'name':row['name'],'history_result':row['history_result'],'terrain':row['terrain'],'assumed_player_level':x['assumed_mean_level'],'enemy_level':x['enemy_level'],'enemy_stars':row['enemy_stars'],'enemy_monarch_stars':row['enemy_monarch_stars'],'target_low':lo,'target_high':hi,'wins':v['wins'],'games':v['n'],'actual_win_rate':v['rate'],'wilson95_low':v['wilson95'][0],'wilson95_high':v['wilson95'][1],'timeout_rate':v['timeout_rate'],'recommended_power':recommended,'validation_seed':seed,'pass':True})
 protected={str(p.relative_to(ROOT)):sha(p) for p in sorted((ROOT/'data').glob('*.csv'))if p.name!='stages.csv'}
 for path,h in protected.items():assert sha(R/'before'/path)==h,('Protected input changed',path)
 def write_csv(path,records):
  with path.open('w',newline='',encoding='utf-8-sig')as f:w=csv.DictWriter(f,fieldnames=records[0]);w.writeheader();w.writerows(records)
 write_csv(ROOT/'assets/reports/chapter_difficulty_report.csv',metrics);write_csv(R/'data_changes.csv',changes)
 source=ROOT/'assets/reports/progression/validation_candidate02.json';manifest={'all_pass':True,'stages':metrics,'stage_count':96,'late_stage_count':72,'validation_games':sum(m['games']for m in metrics),'late_validation_games':sum(m['games']for m in metrics if m['chapter']>=3),'first_two_chapters_unchanged':True,'protected_csv':protected,'growth_profile_source':str(source.relative_to(ROOT)),'growth_profile_source_sha256':sha(source),'rules_sha256':sha(ROOT/'docs/07-关卡设计.md'),'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'tools/stage_difficulty.py',ROOT/'tools/calibrate_growth.py',ROOT/'tools/economy_behavior.ts',ROOT/'tools/battle_sim.py',ROOT/'app/src/core/battle/engine.ts',ROOT/'data/stages.csv']}}
 (R/'difficulty.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
 n=manifest['validation_games'];lines=['# 全96关难度报告','',f'第3–8章72关已重新校准，前两章24关配置保持并用新种子复核。**96/96关的抽样单局胜率均在目标区间内**；最终检验共 **{n:,}局**（前两章每关4,000局，后六章每关1,000局），不含训练、粗测和被修订批次。','', '## 口径与规则','', '- 六关含首尾插值，沿用08第4节。第3–8章每章进入/结束均级：30→38、38→46、46→54、54→62、62→70、70→78；保留个人整数等级和星级上限，五人均级精确等于该关假设等级。','- 位置目标：第1关95–100%，第2–3关85–95%，第4–5关70–85%，首领55–70%。第3章以后history_result=败时，两端各减10个百分点、下限50%；不是所有败仗统一50–65%。清线靖港/湖口/樟树镇保留既定50–65%例外。','- 后72关使用当前经济两表与现有96关下已保存的真实战斗玩家行为模型样本，每阵营100账号，种子71000–71099；原输入指纹与本轮开始时的经济、升星、关卡JSON逐一一致。模型每日08/14时上线、领取放置、扫荡全部已通关关卡，优先升级五主力并兼顾两替补，再升星、强化；按统一静态战力选阵容。','- 对每关100份玩家队伍归一到规定均级，取战力从低到高的四个分位（0、33、66、99），保留各自的星级、招募结果、装备及强化。最终每份配置250局。这里的“实际胜率”是这些规定强度配置下的独立单局抽样胜率，不是“反复重试后最终通关”的比例。','- 前24关保持原定稿四份成长配置，采用全新种子每份1,000局复核，敌方等级、星级、推荐战力均未改；前后章节的配置来源在原JSON内保留。','- 敌军等级以0.1为步长且不超过100。沿用此前用户允许的敌军升星：太平8-5嘉应州4→5★、清8-4高楼寨及8-6尹隆河5→6★；这三关百级旧星级仍过易。其余星级保持。人物、技能、杂兵、装备及经济表未改。','- 推荐战力是本关这四份玩家配置的平均战力，非敌方战力；与网页使用同一公式。读取等级、星级、强化、专属属性，君主折算+8%；条件羁绊与技能触发不折入静态战力。','- 二分/细扫使用训练种子；检验失败的参数及旧批次保留在逐关repairs字段，重新训练后换种子检验。新检验仍用于参数验收，不宣称已证明整个自由编队空间或95%置信区间完整落在目标区间内。','', '## 逐关结果','']
 for camp,label in [('taiping','太平天国'),('qing','清朝')]:
  lines+=['### '+label,'',table(['关卡','关名','史实','玩家均级','敌级/星','目标胜率','实际胜率','检验局数','推荐战力'],[[f"{m['chapter']}-{m['order']}",m['name'],m['history_result'],f"{m['assumed_player_level']:g}",f"{m['enemy_level']:g}/"+'/'.join(m['enemy_stars'].split(';')),pct(m['target_low'])+'–'+pct(m['target_high']),pct(m['actual_win_rate']),m['games'],f"{m['recommended_power']:,}"]for m in metrics if m['campaign']==camp]),'']
 lines+=['## 太平第七章败仗梯度','',table(['关','目标','实际'],[[m['name'],pct(m['target_low'])+'–'+pct(m['target_high']),pct(m['actual_win_rate'])]for m in metrics if m['campaign']=='taiping'and m['chapter']==7]),'','## 改动与游戏接入','',f'- 本轮共{len(changes)}处关卡单元格变更，详见 `chapters_3_8/data_changes.csv`；除关卡表外全部{len(protected)}份CSV逐字节不变，前两章整行不变。','- 游戏从同一份生成JSON读取两阵营各48关：前章6关全通才开放后章；章节奖励、君主奖励、逐关首通与重复通关不重复奖励、存档导出导入均纳入回归。推荐战力直接读取本轮写回的recommended_power。','- PWA包含16个章节包，新章解锁后补齐card/mini/thumb，full.webp继续按需缓存。没有将新解锁后的内容全部算进首次安装。','- 应用内浏览器验收使用隔离qa军册，分别检查两条线第三章入口、第七章与第八章、出征和结算；受控军册由产品API创建，不能当作正常游玩18天的证据。截图与具体检查结果见browser_acceptance.json。','', '## 与经济验收的区别','', '本次交付校准单局难度并接入后六章，未改经济两表。上一轮经济报告中的长尾卡关和少数军功结余问题不能据此判定已解决；校准后的完整行为回放若有结果，将另存post_calibration_behavior.json，不把其最终通关率混入上表单局胜率。','', '## 复现','', '```sh','PYTHONPATH=tools python3 tools/calibrate_growth.py --profiles assets/reports/progression/validation_candidate02.json --chapters 3,4,5,6,7,8 --stages assets/reports/chapters_3_8/before/data/stages.csv --out assets/reports/chapters_3_8/calibration --fixed-stars --raise-stars-for tp_8_5,qing_8_4,qing_8_6','python3 tools/verify_early_chapters.py','python3 tools/report_chapter_difficulty.py','python3 tools/export_data.py --check','npm --prefix app test','```','', '上方复现命令通过stages参数只读本轮before快照，不回写正式表；不要对已提升星级的正式表再次使用raise-stars-for。正式表的无调参独立复核，可使用difficulty.json列出的配置、敌级与validation_seed。完整数值CSV见chapter_difficulty_report.csv，含Wilson95%区间、超时率与种子。报告仅为有限样本结果。']
 release=R/'release_audit.json'
 if release.exists():
  a=json.loads(release.read_text());lines+=['','## 构建与回归','',f"生产版本 {a['version']}；前端 {a['frontend_tests']} 项、Python {a['python_tests']} 项回归通过；新增100组金标准 {a['new_golden']['log_lines']:,} 行日志逐行一致（差异0），并检查其敌级和星级与当前关卡表一致。",f"静态目录、dist与ZIP的{a['files']}份文件逐一哈希一致；16个章节内容包齐全，首次安装下载保守上限 {a['first_install_upper_bound']/1e6:.3f}MB；原56张人物主图未改。静态包：release/taiping-web-0.3.1.zip。"]
 post=R/'post_calibration_behavior.json'
 if post.exists():
  behavior=json.loads(post.read_text());lines+=['','## 校准后完整行为回放','',table(['阵营','样本账号','通关48关','全线均值天数','最长单关等待天'],[[label,len(runs:= [r for r in behavior['runs']if r['campaign']==camp]),sum(r['cleared']==48 for r in runs),f"{statistics.mean(r['days']for r in runs):.2f}",max(c['max_stage_wait']for r in runs for c in r['chapters'])]for camp,label in [('taiping','太平'),('qing','清军')]]),'该回放用于复核校准后两条战役能够走完；不替代独立单局检验，也不代表经济全部目标已通过。']
 (ROOT/'assets/reports/chapter_difficulty_report.md').write_text('\n'.join(lines)+'\n');print(json.dumps({'stages':96,'passed':96,'validation_games':n,'changes':len(changes),'protected_csv':len(protected)},ensure_ascii=False))
if __name__=='__main__':report()
