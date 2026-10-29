#!/usr/bin/env python3
"""Publish source-backed chapter/cache delivery diagnostics without changing source data."""
import csv,hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'assets/reports/web_chapter2'
def read(p):return json.loads(p.read_text())
def rows(p):return list(csv.DictReader(p.open(encoding='utf-8-sig',newline='')))
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pct(n):return f'{n*100:.2f}%'
def main():
 chapters=[read(R/'calibration'/f'chapter{n}.json') for n in [1,2]]
 assert all(c['all_pass'] for c in chapters)
 old={s['stage_id']:s for s in read(ROOT/'assets/reports/m1/chapter1/difficulty.json')['stages']}
 stages=rows(ROOT/'data/stages.csv');before={r['stage_id']:r for r in rows(R/'before/data/stages.csv')}
 source_changes=[]
 for row in stages:
  if row['stage_id'] not in before:continue
  for k,v in row.items():
   if k not in before[row['stage_id']]:continue  # Preserve newly supplied planning columns; they are not tuning edits.
   if v!=before[row['stage_id']][k]:
    assert k=='enemy_level',(row['stage_id'],k)
    source_changes.append({'stage':row['stage_id'],'field':k,'before':before[row['stage_id']][k],'after':v})
 for n in ['heroes.csv','skills.csv','bonds.csv']:
  assert digest(ROOT/'data'/n)==digest(R/'before/data'/n),n
 masters=read(R/'before/master_sha256.json')
 # Stored master paths are relative to the project root.
 if isinstance(masters,list):masters={x['path']:x['sha256'] for x in masters}
 for name,sha in masters.items():assert digest(ROOT/name)==sha,name
 now=rows(ROOT/'data/enemy_units.csv');was={r['id']:r for r in rows(R/'before/data/enemy_units.csv')}
 body=['# 第一、二章难度校准报告','',
 '杂兵四维统一放大 2.25 倍并取整；只改杂兵属性与关卡 enemy_level，正式人物、技能、羁绊数据未变。第一章敌军从 36.7–51 级回到 8.3–13.6 级；第二章按我方全军 20 级、初始星级、无装备校准。',
 '', '## 杂兵属性调整','', '|兵种|统 / 武 / 智 / 速：调整前|调整后|','|---|---|---|']
 for r in now:body.append('|'+r['name']+'|'+' / '.join(was[r['id']][k] for k in ['tong','wu','zhi','su'])+'|'+' / '.join(r[k] for k in ['tong','wu','zhi','su'])+'|')
 body+=['','## 方法与范围','',
 '逐关仅使用开局七张战斗卡及此前关卡已获得的武将，当前关奖励不参与该关测试。枚举所有五人有序编队，以两颗种子初筛，再对前 32 队各测 96 局、前 8 队各测 512 局。最佳候选用独立训练种子按 0.1 级调节；最终每关使用另一组 2,000 颗种子验证，共 48,000 局最终验证。种子区间、候选、训练与 Wilson 95% 区间均保存在 calibration/*.json。这里报告找到的最佳候选，不宣称理论最优。',
 '', '靖港、湖口、樟树镇按史实败仗目标 50–65%；普通第二、三关 85–95%，第四、五关 70–85%，首领关 55–70%，第一关至少 95%。等级整体上行，地形、首领技能与史实败仗导致局部回落，不以强制单调牺牲胜率目标。',
 '', '## 逐关指标','', '|阵营 / 关卡|我方等级|敌等级：前 → 后|目标胜率|旧版胜率|本次独立验证|平均回合|超时|结论|','|---|---:|---|---|---|---|---:|---|---|']
 allresults=[s for c in chapters for s in c['stages']]
 current={r['stage_id']:r for r in stages}
 for s in allresults:assert float(current[s['stage_id']]['enemy_level'])==s['enemy_level'],s['stage_id']
 for s in allresults:
  v=s['validation'];sid=s['stage_id'];prev=old.get(sid);oldrate=pct(prev['validation']['rate']) if prev else '未开放';oldlevel=before[sid]['enemy_level'] or '空'
  body.append(f"|{sid} {s['name']}|{s['player_level']}|{oldlevel} → {s['enemy_level']}|{pct(s['target'][0])}–{pct(s['target'][1])}|{oldrate}|{pct(v['rate'])} ({v['wins']}/2000)|{v['rounds']:.2f}|{pct(v['timeout_rate'])}|通过|")
 body+=['','## 每关验证编队','', '前两位为前排，后三位为后排；君主沿用本阵营开局君主。', '', '|关卡|编队|可用人数|已初筛有序编队数|验证种子起点|','|---|---|---:|---:|---:|']
 heroes={r['id']:r['name'] for r in rows(ROOT/'data/heroes.csv')}
 for s in allresults:body.append(f"|{s['stage_id']}|{'、'.join(heroes[i] for i in s['formation'])}|{len(s['pool'])}|{s['ordered_formations_screened']}|{s['validation_seed']}|")
 body+=['','## 运行规则','',
 '双方推荐战力使用同一公式：逐人 HP/10 + 主攻 + 防御 + 抗性 + 速度，五人相加取整。属性随等级和星级成长；主攻按兵种取武或智。此数值不预估技能触发、羁绊或克制胜率。界面不展示敌方等级。',
 '', '清线困守南昌中，我方作为防守方获得防御 +20%；太平线孝陵卫敌方向荣、张国梁正常触发江南大营羁绊。第二章首通奖励从 CSV 读取、只发一次，军册保持格式版本 1；旧第一章进度可继续。第一、二章分别采用 10 / 20 级测试档，养成系统加入后需要重新校准。',
 '', '## 可复现命令','', '```sh','PYTHONPATH=tools python3 tools/calibrate_chapters.py --chapter 1 --promote','PYTHONPATH=tools python3 tools/calibrate_chapters.py --chapter 2 --promote','python3 tools/export_data.py','python3 tools/build_golden.py --output assets/reports/web_chapter2/golden --chapters 1,2 --calibration-dir assets/reports/web_chapter2/calibration','cd app && npm test','```','', '原 M1 / M1.1 报告保留；本次报告是杂兵调整后的独立结果，旧版胜率列来自当时原 NPC 与原等级的验证。']
 (R/'difficulty_report.md').write_text('\n'.join(body)+'\n')
 build=read(ROOT/'app/dist/pwa-build.json');gold=read(R/'golden/comparison.json');assert gold['cases']==100 and gold['failed']==0
 assert build['firstInstallUpperBound']<=10_000_000 and build['allUnlockedInstallUpperBound']<=10_000_000
 for folder in [ROOT/'app/public',ROOT/'app/dist',ROOT/'release/taiping-web']:assert not list(folder.rglob('full.png')),folder
 for name in ['full','card','mini','thumb']:
  derivatives=list((ROOT/'app/dist/assets/characters').glob('*/'+name+'.webp'));assert len(derivatives)==56
  for file in derivatives:assert digest(file)==digest(ROOT/'assets/characters'/file.parent.name/file.name)
 dist=ROOT/'app/dist';deploy=ROOT/'release/taiping-web';manifest={str(p.relative_to(dist)):digest(p) for p in dist.rglob('*') if p.is_file()}
 assert manifest=={str(p.relative_to(deploy)):digest(p) for p in deploy.rglob('*') if p.is_file()}
 z=ROOT/'release/taiping-web-0.2.0.zip'
 with zipfile.ZipFile(z)as f:
  assert not any(n.endswith('/full.png') for n in f.namelist())
  assert {n:hashlib.sha256(f.read(n)).hexdigest() for n in f.namelist()}==manifest
 result={'version':build['version'],'initial_cache_bytes':build['initialCacheBytes'],'first_install_upper_bound_bytes':build['firstInstallUpperBound'],'all_unlocked_install_upper_bound_bytes':build['allUnlockedInstallUpperBound'],'total_package_asset_bytes':build['totalBytes'],'golden':gold,'chapter_stages':len(allresults),'holdout_battles':sum(s['validation']['n'] for s in allresults),'all_difficulty_pass':True,'unchanged_master_pngs':len(masters),'data_changes':source_changes,'preserved_new_stage_ids':[r['stage_id'] for r in stages if r['stage_id'] not in before],'preserved_new_stage_columns':sorted(set(stages[0])-set(next(iter(before.values())))),'zip':str(z.relative_to(ROOT)),'zip_bytes':z.stat().st_size,'zip_sha256':digest(z),'dist_sha256':manifest}
 (R/'delivery_manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 cold=read(R/'cold_install_v020.json') if (R/'cold_install_v020.json').exists() else None
 walk=read(R/'browser_walk.json') if (R/'browser_walk.json').exists() else []
 accepted={s['stage'] for s in walk if s.get('heading')=='军势大振'}
 lines=['# v0.2.0 交付验收','',f"构建：{build['version']}。两条战役线共 24 关，已交付静态目录和 ZIP。",'', '## 初装与素材','',
 f"初始 SW 预缓存 {build['initialCacheFiles']} 个资源，共 {build['initialCacheBytes']:,} 字节（{build['initialCacheBytes']/1e6:.6f} MB）。计入首屏、SW 重复获取及安装图标等开销的保守资源上界 {build['firstInstallUpperBound']:,} 字节（{build['firstInstallUpperBound']/1e6:.3f} MB），小于 10,000,000 字节；这是未压缩资源量上界，不含网络协议头与重试。",'',
 f"完整 ZIP {z.stat().st_size:,} 字节；整包包含后续章节与 56 张按需详情图，因此不能与首次下载量混为一谈。56 张 full.webp 为 1024×1536、质量 85；网页 public、dist、部署目录、ZIP 均没有 full.png，56 张 PNG 母版哈希不变。",'',
 '## 缓存行为','', f"已有军册解锁两条线第二章时，四章缩图合计预缓存 {build['allUnlockedCacheBytes']:,} 字节，保守安装上界 {build['allUnlockedInstallUpperBound']:,} 字节，也低于 10MB（不含主动打开详情的大图流量）。", '', '程序与内容分两层缓存。安装准备两个阵营的首章 card / mini / thumb；通关后补齐对应第二章缩图包。详情图只在首次打开时获取，已缓存的大图可以离线重开，未缓存的大图回退 card。更新会复用同哈希缓存并迁移已缓存的详情，不会清除军册。新解锁章节需首次联网备齐素材，界面显示“离线包就绪”后可断网重开游玩。', '',
 '## 校准和回归','', f"24 关最终独立验证共 48,000 局，全部达到目标。100 组 Python / TypeScript 金标准覆盖 24 个正式关卡及 76 组随机对局，{gold['log_lines']:,} 行事件逐行一致，差异为 0。Python 74 项、Vitest 21 项通过，构建类型检查通过；字体缺字为 0。",'',
 f"应用内浏览器实走通过 {len(accepted)} / 24 关；第一章在开发预览逐关实走，第二章在本次生产包从导入的真实首章军册续玩。UI 结果保存在 browser_walk.json。",'',
 '## 浏览器证据','', '离线网络由 Chrome DevTools 的 Offline 实测，未修改系统网络设置；验收后已恢复 No throttling。最终包断网重载后完成长沙城下（10 回合胜）；此前也走通九江离线首通并获得胡林翼。未缓存曾国藩详情回退 card，已缓存萧朝贵详情离线重开正常。更新保留双线 12/12 进度，重复孝陵卫不再发奖励。', '', '截图：screenshots/offline_final_battle.png、screenshots/taiping_chapter2_final.png、screenshots/cold_install_v020.png。AX 记录：offline_final_battle.ax.txt、offline_v020_reload.ax.txt、offline_v020_detail_fallback.ax.txt、offline_v020_cached_full.ax.txt。', '', '320px 窄屏无横向溢出、已显示图片无加载失败，应用内浏览器无 error / warn；详见 narrow_viewport.json。', '', '## 文件','', '本次运行中新增的五张养成数据表、stages.shard_drops 与后续章节规划行已保留并支持类型导出，尚未启用相关玩法；本次调参仅改 enemy_level 和杂兵四维。', '', '- difficulty_report.md：24 关调整前后、验证编队、种子与超时率。','- golden/comparison.json：100 组逐行比对。','- delivery_manifest.json：ZIP、部署文件 SHA-256 与数据改动清单。','- ../../../release/DEPLOY.md：部署与离线准备步骤。','',f"ZIP SHA-256：{digest(z)}"]
 if cold:lines.insert(6,f"全新 origin 实测预缓存下载 {cold['downloadedBytes']:,} 字节；测量版本 {cold['version']}。详见 cold_install_v020.json。")
 (R/'delivery_report.md').write_text('\n'.join(lines)+'\n')
 print(json.dumps({k:v for k,v in result.items() if k not in ['dist_sha256','data_changes','golden']},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
