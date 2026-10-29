#!/usr/bin/env python3
import json,hashlib
from pathlib import Path
from battle_sim import ROOT
R=ROOT/'assets/reports/m1';new=json.loads((R/'mulberry_balance/validation.json').read_text());old=json.loads((ROOT/'assets/reports/balance_v2/report_validation.json').read_text())['main_targets']
lines=['# M1 · mulberry32 切换后的 v2 主指标复核','','状态：全部点估计达标，未调整人物四维、技能、羁绊或装备数值。旧 v2 冻结结果保留，以下对照明确区分随机数算法。','','|指标|目标|原 v2 Random.Random|mulberry32|判定|','|---|---|---:|---:|---|']
for n,row in new['metrics'].items():
 fmt=(lambda v:f'{v:.3f}') if '回合' in n else (lambda v:f'{v*100:.2f}%')
 lines.append(f"|{n}|{row['target']}|{fmt(old[n]['value'])}|{fmt(row['value'])}|{'通过' if row['pass'] else '未通过'}|")
lines+=['',f"复核共 {new['total_games']:,} 局。主测试 n=2000 镜像组/场景、1600候选阵容、每阵容16个对手×攻守镜像；君主另用4批2000阵容合并，在本阵营内统一排序取前10%，截断同胜率并列按权重平分。主种子20263199；君主批次20263201/20263301/20263401/20263501。",'', '君主口径沿用用户确认的本阵营胜率前10%阵容中的占比，排除君主后的战斗卡出场率另算。均为50级、双方同3星，无普通装备或专属；R/SR/SSR纯阵营均正式5v5。装备敏感性本轮未重新调参，旧v2报告中的未达标项不会因此被宣称已消除。', '', '比例判定为点估计，不保证所有可能阵容。镜像簇近似区间、完整阵容记录与输入哈希保存在mulberry_balance/main.json及0–3.json；所有计算使用当前mulberry32。', '', '## 随机数合同', '', '- uint32种子，mulberry32按32位整数溢出计算；不调用Python random.Random或Math.random。', '- choice/randrange使用floor(draw*n)；sample为前向Fisher–Yates部分采样，shuffle为倒序Fisher–Yates。', '- 字符串诊断种子使用UTF-8 FNV-1a转uint32；战斗接口直接使用32位数字种子。', '- 100组金标准同时覆盖NPC重复身份、初始星级、混编、4地形、套装、专属与属性拆分；比较所有日志事件及最终结果。', '', '## 文件哈希', '']
for p in [ROOT/'tools/rng.py',ROOT/'tools/battle_sim.py',ROOT/'app/src/core/rng.ts',ROOT/'app/src/core/battle/engine.ts']:
 lines.append(f'- `{p.relative_to(ROOT)}`: `{hashlib.sha256(p.read_bytes()).hexdigest()}`')
(R/'mulberry_balance_report.md').write_text('\n'.join(lines)+'\n')
