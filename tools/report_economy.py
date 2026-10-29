#!/usr/bin/env python3
"""Build the review report from independently saved simulation, calibration and release evidence."""
import csv,json,hashlib,statistics,zipfile
from pathlib import Path
from economy_sim import summarize
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'assets/reports/progression'
def load(name):return json.loads((R/name).read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def table(head,rows):return '\n'.join(['|'+'|'.join(head)+'|','|'+'|'.join(['---']*len(head))+'|']+['|'+'|'.join(map(str,r))+'|' for r in rows])+'\n'
def pct(v):return f'{v*100:.1f}%'
def csvread(p):return list(csv.DictReader(p.open(encoding='utf-8-sig',newline='')))
def quantile(v,q):return sorted(v)[round((len(v)-1)*q)]
def analyse(data):
 groups=summarize(data);waits=[]
 for run in data['runs']:
  previous=0
  for p in run['profiles']:
   wait=p['day']-previous;previous=p['day']
   if wait>2:waits.append({'campaign':run['campaign'],'seed':run['seed'],'stage_id':p['stage_id'],'wait':wait,'clear_day':p['day'],'levels':p['team']['levels'],'stars':p['team']['stars'],'heroes':p['team']['heroes']})
 return groups,waits
if __name__=='__main__':
 before=load('validation_baseline02.json');after=load('validation_candidate02.json');bg,bw=analyse(before);ag,aw=analyse(after)
 (R/'validation_candidate02_summary.json').write_text(json.dumps(ag,ensure_ascii=False,indent=2));(R/'long_waits.json').write_text(json.dumps(sorted(aw,key=lambda r:-r['wait']),ensure_ascii=False,indent=2))
 changes=[];source=load('before/source_sha256.json');immutable=[]
 allowed={'data/economy_chapters.csv','data/star_up.csv','data/stages.csv'}
 for path,oldhash in source.items():
  if path.startswith('data/') and path not in allowed:immutable.append({'path':path,'before':oldhash,'after':sha(ROOT/path),'unchanged':sha(ROOT/path)==oldhash})
 assert all(x['unchanged'] for x in immutable)
 for name in ['economy_chapters.csv','star_up.csv','stages.csv']:
  old=csvread(R/'before/data'/name);new=csvread(ROOT/'data'/name);key={'economy_chapters.csv':'chapter','star_up.csv':'star_from','stages.csv':'stage_id'}[name];lookup={r[key]:r for r in old}
  for row in new:
   for field,value in row.items():
    prev=lookup[row[key]].get(field,'<新增列>')
    if value!=prev:
     if name=='stages.csv':assert field in {'enemy_level','recommended_power','enemy_stars','enemy_monarch_stars'}
     changes.append({'file':name,'id':row[key],'field':field,'before':prev,'after':value})
 (R/'source_audit.json').write_text(json.dumps({'immutable':immutable,'changes':changes,'model_sha256':{str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'tools/economy_behavior.ts',ROOT/'tools/economy_sim.py',ROOT/'tools/battle_sim.py',ROOT/'app/src/core/progression.ts',ROOT/'app/src/core/battle/engine.ts']}},ensure_ascii=False,indent=2))
 with (R/'data_changes.csv').open('w',newline='')as f:w=csv.DictWriter(f,fieldnames=['file','id','field','before','after']);w.writeheader();w.writerows(changes)
 difficulty=load('calibration/difficulty.json');assert len(difficulty['stages'])==96 and difficulty['all_pass']
 assert all(1<=s['enemy_level']<=100 and all(1<=v<=6 for v in s['enemy_stars']) for s in difficulty['stages'])
 meta=json.loads((ROOT/'app/dist/pwa-build.json').read_text());dist=ROOT/'app/dist';deploy=ROOT/'release/taiping-web';files={str(p.relative_to(dist)):sha(p) for p in dist.rglob('*') if p.is_file()};assert files=={str(p.relative_to(deploy)):sha(p) for p in deploy.rglob('*') if p.is_file()}
 zip_path=ROOT/'release/taiping-web-0.3.0.zip'
 with zipfile.ZipFile(zip_path)as z:assert {p:hashlib.sha256(z.read(p)).hexdigest() for p in z.namelist()}==files
 masters=json.loads((ROOT/'assets/reports/web_chapter2/before/master_sha256.json').read_text());assert all(sha(ROOT/p)==h for p,h in masters.items())
 assert not list(dist.rglob('full.png')) and len(list(dist.rglob('full.webp')))==56
 release={'version':meta['version'],'files':len(files),'deployment_equal':True,'zip_equal':True,'zip_bytes':zip_path.stat().st_size,'zip_sha256':sha(zip_path),'first_install_upper_bound':meta['firstInstallUpperBound'],'initial_cache_bytes':meta['initialCacheBytes'],'master_images_unchanged':len(masters),'full_png_in_web':0,'full_webp':56};(R/'release_audit.json').write_text(json.dumps(release,indent=2))
 golden=load('golden/comparison.json');assert golden['passed']==100 and golden['failed']==0
 names={'taiping':'太平','qing':'清军'};lines=['# 养成系统与八章经济验收报告','',f"版本 `{meta['version']}`。**功能与交付验证已完成；经济平衡仍有未通过项，不能视为全部数值验收通过。**",'','## 验收结论','']
 means=sum(g.get('pace_pass',False) for g in ag);remaining_fail=sum(c['exp_remaining_ratio']>=.2 for r in after['runs'] for c in r['chapters'])
 lines+=[f"独立样本为每阵营 {after['count_per_campaign']} 个账号，共 {len(after['runs'])} 个，种子 {after['seed']}–{after['seed']+after['count_per_campaign']-1}。全部 {sum(r['cleared']==48 for r in after['runs'])}/{len(after['runs'])} 个通关各自48关。{means}/16 个阵营章节的平均耗时在目标±25%内；{len({(w['campaign'],w['seed'])for w in aw})} 个账号出现合计 {len(aw)} 次超过2天的单关等待，最长 {max((w['wait'] for w in aw),default=0):.2f} 天。单个账号章末军功比例≥20%的记录 {remaining_fail}/1600 条。",'',table(['项目','结果'],[['功能','升级、升星、放置、扫荡、掉装、强化、分解、转移、招募与战力已接入'],['关卡难度',f"96/96关抽样胜率达到对应区间，最终独立复核共{sum(s['validation']['n'] for s in difficulty['stages']):,}局"],['章内等级','六关含首尾插值；第二章20、22、24、26、28、30'],['敌军成长','按用户追加许可提升星级，最高6★；等级≤100；4★专属随星级生效'],['经济平均节奏',f'{means}/16；详见下表'],['卡关目标',f'未通过：{len(aw)}次等待超过2天'],['军功结余',f'逐账号严格口径有{remaining_fail}条未通过；各章均值与最大值分别报告'],['人物与技能',f'{len(immutable)}份受保护CSV逐字节未变'],['跨语言金标准',f"新增100组/ {golden['log_lines']:,}行，差异0；旧100组亦保留回归"],['回归','37项前端、74项Python通过；日志见 tests_final.log / python_tests_final.log']]),'','这些结果只证明当前有限样本和下述行为策略。没有将平均值等同于每个账号都达标，也没有将“星级不越上限”当成所有稀有度都被主力实际使用的证明。','', '## 模拟口径与调整过程','', '- 经济模型直接调用产品的 TypeScript 纯函数和战斗引擎，Python入口为 `tools/battle_sim.py --economy`。两端战斗继续使用mulberry32；招募/掉落随机状态随军册持久化。','- 每天08:00、14:00上线，两次间隔6h/18h，受12h封顶影响，每天有效放置18h。扫荡全部历史已通关关卡的3次额度；新通关关卡当天同样可扫荡。资源先升最强战力的五名主力并兼顾两名替补（替补落后约2级），再升星，最后强化。','- 最强阵容按统一静态战力排序，前排取基础生命较高两人；没有读取未来战斗结果来选人。装备给主力，每部位选战力贡献最高五件，闲置装备在模型中主动分解。游戏不会自动分解玩家装备。君主沿用开局君主。','- 每关每次上线最多连续尝试3局，失败后下次上线再试。这是模拟行为假设，游戏本身没有体力或尝试次数限制；另跑1局/10局敏感性样本。','- 新获得武将按已拥有最高五名战斗武将均级入营，受初始星级上限约束。剧情提前被招募的人物再次解锁时转同稀有度将魂，避免奖励落空。','- 先用资源模型建立18–19天参考曲线，再以该曲线的星级、装备配置，在每关规定均级下校准敌军。参考样本10账号/阵营，按战力分位抽四队，非理论最优阵容。保留整数个人等级和星级上限，五人平均等于插值等级。','- 参考表冻结在 `reference_inputs/`；以 tables= 覆盖复跑与 profile_tune_02.json 逐对象一致。之后进行14轮真实战斗经济试调（训练种子42000–42011）。选样标准与后续修订见 `selected_candidate.json`。','- 首轮独立复核种子51000–51099发现清军第7章偏快及个别末章军功结余，随后只降低第7章收益与第8章首通军功。该轮已成为调参证据，未冒充最终独立样本。最终重新使用71000–71099。','- 前后对比使用同一最终96关、同一行为模型与同组账号种子，仅切换原始/最终两张经济表；不是把旧关卡和新关卡混在一起比较。','- 3→4★将魂由80降至20，防止SSR在65级附近长期堵住；其他升星行不变。所有经济单元格改动在后文逐项列出。','', '## 每章前后对比','', '天数为该章相对上一章通关时间的增量，均值按100个账号统计；范围为第10/90百分位。卡关、军功最大值按逐账号严格统计。','',table(['阵营/章','目标天','调整前均值','调整后均值','P10–P90','均值合格','最大等待天','军功余量均值/最大'],[[names[g['campaign']]+'/'+str(g['chapter']),g['target'],f"{bg[i]['mean_days']:.2f}",f"{g['mean_days']:.2f}",f"{quantile([c['duration'] for r in after['runs'] if r['campaign']==g['campaign'] for c in r['chapters'] if c['chapter']==g['chapter']],.1):.2f}–{quantile([c['duration'] for r in after['runs'] if r['campaign']==g['campaign'] for c in r['chapters'] if c['chapter']==g['chapter']],.9):.2f}",'是' if g['pace_pass'] else '**否**',g['max_stage_wait'],pct(g['exp_remaining_ratio_mean'])+'/'+pct(g['exp_remaining_ratio_max'])]for i,g in enumerate(ag)]),'']
 for camp in names:
  old=[r['days'] for r in before['runs'] if r['campaign']==camp];new=[r['days'] for r in after['runs'] if r['campaign']==camp];lines+=[f"{names[camp]}全线平均 {statistics.mean(old):.2f} → {statistics.mean(new):.2f} 天；最终范围 {min(new):.2f}–{max(new):.2f} 天，中位 {statistics.median(new):.2f} 天。"]
 lines+=['','## 长尾卡关与未通过项','', '以下是最长的20条，完整记录见 `progression/long_waits.json`。关卡等待包含两次上线间隔以及补充资源时间；不能据此断言全部等待都由某一种材料短缺导致。最强静态战力阵容不保证最优胜率，这是后续应单独诊断的因素。当前14轮仅改变两张经济表的尝试未消除这些长尾；本报告不证明两表调参在数学上不可能达标。','',table(['阵营','种子','关卡','等待天','通关时个人等级','星级'],[[names[w['campaign']],w['seed'],w['stage_id'],w['wait'],'/'.join(map(str,w['levels'])),'/'.join(map(str,w['stars']))]for w in sorted(aw,key=lambda r:-r['wait'])[:20]]),'','## 资源、升星与来源占比','',table(['阵营/章','最少章末银两','最少章末精铁','军功来源 放置/首通/扫荡'],[[names[g['campaign']]+'/'+str(g['chapter']),g['silver_min'],g['iron_min'],' / '.join(pct(statistics.mean(c['exp_sources'][kind]/max(1,c['produced']['exp']) for r in after['runs'] if r['campaign']==g['campaign'] for c in r['chapters'] if c['chapter']==g['chapter']))for kind in ['idle','first','sweep'])]for g in ag]),'','来源占比未保持设计的60%/25%/15%。每天扫荡全部历史关卡会持续增加旧关收入；本轮没有改掉“每关每天3次”规则，因此将实际占比单独报告，不声称设计比例已实现。章末军功分母为本章新增产出，分子含上章结转，可能超过100%。','']
 for camp in names:
  runs=[r for r in after['runs'] if r['campaign']==camp]
  lines+=[f"{names[camp]}：银两为零的会话合计 {sum(r['silver_zero_sessions'] for r in runs)}，精铁为零的会话合计 {sum(r['iron_zero_sessions'] for r in runs)}（包含初始零资源会话）；章末最小余额见表，不由单个正余额推出整个过程从未短缺。"]
 rarity={h['id']:h['rarity']for h in json.loads((ROOT/'app/src/core/data/heroes.json').read_text())};starrows=[]
 for camp in names:
  for tier,threshold,need in [('R',35,2),('SR',50,3),('SSR',65,4)]:
   use=[(h,s) for r in after['runs'] if r['campaign']==camp for p in r['profiles'] for h,l,s in zip(p['team']['heroes'],p['team']['levels'],p['team']['stars'])if rarity[h]==tier and l>threshold];starrows.append([names[camp],tier,threshold,len(use),sum(s>=need for h,s in use),','.join(sorted({h for h,s in use}))or'未实际使用该类主力'])
 lines+=[table(['阵营','稀有度','跨越等级','主力关卡人次','已达所需星级','实际人物'],starrows),'','## 行为敏感性','']
 for file in ['sensitivity_attempt1.json','sensitivity_attempt10.json']:
  d=load(file);sg,sw=analyse(d);lines+=[f"每次上线每关尝试 {d['attempt_cap']} 局，每阵营30账号（种子81000–81029）：{sum(r['cleared']==48 for r in d['runs'])}/60通关，平均节奏 {sum(g['pace_pass']for g in sg)}/16项通过，最长等待 {max((w['wait']for w in sw),default=0):.2f}天；太平/清军全线均值 {statistics.mean(r['days']for r in d['runs']if r['campaign']=='taiping'):.2f}/{statistics.mean(r['days']for r in d['runs']if r['campaign']=='qing'):.2f}天。"]
 lines+=['','## 逐关难度与推荐战力','', '最终检验每关前两章2000局、后六章1000局。重新调参使用另一个训练种子，修订前未通过的独立批次保留于各关repairs字段；最终检验数不含训练/修订旧批次。置信区间见原JSON。校准只证明这些参考阵容的抽样胜率达标，不证明所有自由编队达标。','',table(['关卡','假设均级','敌军级','敌军星级','目标','复核胜率/局数','推荐战力'],[[s['stage_id'],s['assumed_mean_level'],s['enemy_level'],'/'.join(map(str,s['enemy_stars'])),pct(s['target'][0])+'–'+pct(s['target'][1]),pct(s['validation']['rate'])+'/'+str(s['validation']['n']),s['recommended_power']]for s in difficulty['stages']]),'','推荐战力是参考玩家队伍的平均静态战力，非敌军原始战力。静态战力读取实际等级、星级、强化和专属属性；条件光环、羁绊、套装触发与技能不折入该静态估值。君主统一折算+8%。','', '## 全部经济单元格改动','',table(['表','行','字段','原值','新值'],[[x['file'],x['id'],x['field'],x['before'],x['after']]for x in changes if x['file']!='stages.csv']),'','关卡只改enemy_level、recommended_power及追加获准的enemy_stars / enemy_monarch_stars；逐单元格详单含全部关卡见 `progression/data_changes.csv`。受保护原表哈希见 `progression/source_audit.json`。','', '## 产品、存档与离线证据','', '- 旧version=1存档首次迁移保留两线进度与编队，补入已通关首通资源和相应等级；放置从迁移时刻开始。导入迁移在原子写入前完成，并保留替换前备份。升级、星级、装备归属/强化、将魂、随机数、保底、每日次数均在军册中。','- 应用内浏览器真实首战→5330军功/10660银两/266精铁/1令/1件兵装；石达开10→11级消耗950军功；腰刀强化+1后两次转移仍+1，卸下分解得5铁；单抽后新将入营。更新后等级、钱包与保底保留，UI导出证据 `fixtures/ui-earned-export.json`。','- 12小时封顶、35级R卡升星解锁50级、40抽保底与十连，使用 `build_progression_fixture.ts` 经真实产品API生成的模拟时钟测试军册；通过界面导入。它是受控测试，不伪称实际等待31天。截图见screenshots。','- 320×568与390×844页面检查无横向溢出；IAB完成养成、装备、招募、战斗与更新操作。原生Chrome仅用于IAB不具备的Network Offline断网验证。具体范围见 browser_acceptance.json。',f"- 生产静态包 {release['files']} 份文件，部署目录与dist、ZIP逐文件哈希一致；{len(masters)}份原画哈希未变；网页full.png=0，full.webp=56。首次缓存 {meta['initialCacheBytes']/1e6:.3f}MB，含初次页面加载和安装开销的保守下载上限 {meta['firstInstallUpperBound']/1e6:.3f}MB。",'- 新招募英雄独立缓存card/mini/thumb，不预缓存full；未缓存大图断网降级为card，新画像完全未缓存时显示剪影。Service Worker不改军册。','', '## 复现与证据索引','', '```sh','python3 tools/export_data.py','npm --prefix app test','python3 tools/build_progression_golden.py','node --import ./app/node_modules/tsx/dist/loader.mjs tools/economy_behavior.ts mode=battle n=100 seed=71000 attempts=3 tables=assets/reports/progression/selected_tables.json out=assets/reports/progression/reproduce_after.json','node --import ./app/node_modules/tsx/dist/loader.mjs tools/economy_behavior.ts mode=battle n=100 seed=71000 attempts=3 tables=assets/reports/progression/baseline_tables.json out=assets/reports/progression/reproduce_before.json','python3 tools/report_economy.py','npm --prefix app run package:static','```','', '关键证据：validation_candidate02.json / validation_baseline02.json；calibration/difficulty.json；golden/comparison.json；selected_candidate.json；reference_inputs；release_audit.json；font_coverage.json。已知丢失个人装备输入的早期校准被隔离在discarded_calibration_missing_unit_state，未用于最终结论。']
 text='\n'.join(lines)+'\n';(ROOT/'assets/reports/economy_report.md').write_text(text);(R/'economy_report.md').write_text(text);print(json.dumps({'mean_pace_pass':means,'total_chapter_metrics':16,'long_waits':len(aw),'max_wait':max((w['wait']for w in aw),default=0),'resource_outliers':remaining_fail,'release':release},ensure_ascii=False))
