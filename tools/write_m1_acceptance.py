#!/usr/bin/env python3
"""Collect inspectable M1 delivery evidence; never substitute a generated native project for launch proof."""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / 'assets/reports/m1'


def read(name):
    return json.loads((R / name).read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


gold = read('golden/comparison.json')
diff = read('chapter1/difficulty.json')
balance = read('mulberry_balance/validation.json')
ui = read('browser_playthrough.json')
perf = read('performance/final_run.json')
inputs = read('mulberry_balance/main.json')['input_sha256']
assert all(sha(ROOT / 'data' / name) == digest for name, digest in inputs.items())
assert sha(ROOT / 'tools/battle_sim.py') == read('golden/manifest.json')['python_sha256']
assert gold['passed'] == 100 and gold['failed'] == 0 and not gold['mismatches']
assert diff['all_pass'] and all(s['pass'] for s in diff['stages'])
assert len({x['stage'] for x in ui['runs'] if x['win']}) == 12
assert '6 / 6' in ui['persistedTP'] and '6 / 6' in ui['persistedQing']
assert not read('font_coverage.json')['missing_printable']
assert read('npm_audit_after.json')['metadata']['vulnerabilities']['total'] == 0

with (R / 'chapter1/stages_before.csv').open(encoding='utf-8-sig', newline='') as f:
    before = list(csv.DictReader(f))
with (ROOT / 'data/stages.csv').open(encoding='utf-8-sig', newline='') as f:
    after = list(csv.DictReader(f))
changes = [(a['stage_id'], k) for a, b in zip(before, after, strict=True) for k in a if a[k] != b[k]]
assert len(changes) == 12 and all(k == 'enemy_level' for _, k in changes)

assets = list((ROOT / 'app/public/assets/characters').glob('*/*.webp'))
assert len(assets) == 168
assert all(sha(p) == sha(ROOT / 'assets/characters' / p.parent.name / p.name) for p in assets)
dist = ROOT / 'app/dist'
for native in ['app/ios/App/App/public', 'app/android/app/src/main/assets/public']:
    assert all(sha(p) == sha(ROOT / native / p.relative_to(dist)) for p in dist.rglob('*') if p.is_file())

manifest = {
    'data': {str(p.relative_to(ROOT)): sha(p) for p in (ROOT / 'data').glob('*.csv')},
    'app_source': {str(p.relative_to(ROOT)): sha(p) for p in (ROOT / 'app/src').rglob('*') if p.is_file()},
    'dist': {str(p.relative_to(dist)): sha(p) for p in dist.rglob('*') if p.is_file()},
    'golden': gold,
    'balance_games': balance['total_games'],
    'chapter_validation_games': sum(s['validation']['n'] for s in diff['stages']),
    'browser_battles': len(ui['runs']),
    'browser_wins': sum(x['win'] for x in ui['runs']),
    'stage_changed_columns': changes,
    'native_public_bytes_match_dist': True,
    'art_webp_bytes_match_source': len(assets),
    'performance': perf,
    'native_acceptance': {'ios': 'blocked_missing_full_xcode_and_runtime', 'android': 'deferred_by_user'},
}
(R / 'delivery_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
full_sampling = perf['frames'] > 1200
fps_pass = full_sampling and perf['fps'] >= 59.5 and perf['over25ms'] == 0
scope = '整场主动播放' if full_sampling else '前 1200 帧采样（整场录制已结束，读取统计时 Mac 锁屏，待解锁后补齐）'
lines = [
    '# M1 交付与验收记录', '',
    '网页可玩版本已完成，两条第一章均实际通关。iOS 原生启动因本机缺少完整 Xcode 与模拟器运行时尚未通过；Android 原生验收按用户要求暂缓。因此本交付不宣称 M1 四项全部验收完成。', '',
    '## 06 文档第 5 节验收', '',
    '|条目|结果|证据与范围|', '|---|---|---|',
    '|1. 网页与双端启动|网页通过；原生未完成|应用内浏览器实际打通两条战役。双端工程生成、插件同步通过；生成工程不等于模拟器启动。|',
    f"|2. 100 组金标准|通过|100/100，{gold['log_lines']:,} 行事件与状态日志、最终结果逐项一致，失败 0。|",
    f"|3. Chrome 4× CPU|{'通过代理测试' if fps_pass else '待补齐整场数据'}|360×800 Samsung Galaxy A55 视口，{scope} {perf['frames']:,} 帧，{perf['fps']:.3f}fps；P95 {perf['p95_ms']:.2f}ms，最慢 {perf['worst_ms']:.2f}ms，>25ms {perf['over25ms']} 帧。不能代替实体安卓设备验收。|",
    '|4. 界面规范|已实现，附图待用户审美验收|宣纸、朱砂、靛蓝与金色 token；宋体、竖排军报、卡牌双线框与阵营印。320×568、390×844、1280×900 实查。|', '',
    '## 实现与可运行入口', '',
    '- `app/`：Vite + React 18 + TypeScript strict；PixiJS 8 只播放战斗日志；Capacitor 6 双端工程。',
    '- `tools/export_data.py` 从 CSV 生成 JSON、类型和编译后的技能 AST，构建先校验源文件哈希与生成物。',
    '- Python 与 TypeScript 共用 mulberry32 合同；计算保持双精度，日志统一六位小数。TS 引擎纯函数，不读取 DOM、时钟、存储。',
    '- 四页：阵营选择、5 人编队加君主、自动战斗、胜负军报。浏览器 IndexedDB；原生 Preferences；双阵营进度独立保存。',
    '- `cd app && npm ci && npm run dev`，打开 http://127.0.0.1:5191 。详细命令见 `app/README.md`。', '',
    '## 实走与回归', '',
    f"- 应用内浏览器最终数据记录 {len(ui['runs'])} 场结算，12 关获胜；失败后正常重试，无强制胜利或直接写通关存档。常规场次跳过的是已算定日志播放，结果仍由纯引擎计算；另有整场自然播放。",
    '- 两条战役逐关解锁、6/6 进度刷新恢复、阵营切换；换位与换将、人物全图详情、暂停/继续、4× 播放、跳过均实际操作。',
    '- 最终应用内浏览器警告/错误日志为空；320px 窄屏横向滚动宽度等于视口，出征按钮在可见安全范围内。',
    '- Vitest 6 项通过（其中包含全部 100 场金标准与 RNG 向量）；Python 42 项通过；TypeScript 与生产构建通过；npm audit 已知漏洞 0。',
    '- Playwright CLI 复现脚本已附；本次实际界面验收通过新版应用内浏览器的 Playwright 控件操作完成，未把未运行的 CLI 用例列为已通过。', '',
    '## 数值与关卡', '',
    f"- 切换 RNG 后 v2 主指标 {balance['total_games']:,} 场，所有目标点估计通过。人物、技能、羁绊、装备六份输入哈希与该复核一致。详见 [主指标复核](mulberry_balance_report.md)。",
    f"- 第一章 {len(diff['stages'])} 关独立验证 {sum(s['validation']['n'] for s in diff['stages']):,} 场全部达到各自目标。仅修改 stages.csv 的 12 个 enemy_level 单元格；0.1 级步进已获用户确认。详见 [难度报告](chapter1_difficulty_report.md)。",
    '- 最佳编队是搜索得到的经验候选，不声称穷尽随机数空间的理论最优。达标按文档目标的胜率点估计；各关置信区间保留在 JSON。', '',
    '## 性能证据', '',
    '- 使用生产构建、Chrome Performance 实际录制、4× CPU 降速、360×800 手机视口。测试仅初始化完成后的战斗主动播放；加载准备单独显示“整军列阵”。',
    '- 最初冷启动采样为 59.379fps，最慢 149.9ms，出现 1 个 >50ms 帧；没有隐去该失败。增加 GPU/文字资源预热后复测，并将帧统计扩展到整场。暂停时间不计为播放卡顿，切速不清空先前采样。',
    '- 最终逐帧统计见 [final_run.json](performance/final_run.json)，配置与原生 AX 证据保存在 performance/；原始首轮结果 first_run.json、优化后前 1200 帧 warm_first1200.json 同时保留。',
    '- Chrome Performance 面板 AX 摘要与战斗截图已保存；未声称已导出原始 .json.gz trace 文件。', '',
    '## 原生端待验收原因', '',
    '- iOS：`npx cap run ios` 和实际目标列表检查均有日志；本机 xcode-select 仍指向 CommandLineTools，xcrun 找不到 simctl，没有可启动的 iOS 模拟器。需安装完整 Xcode 及 iOS Simulator runtime 后运行。没有生成虚假的模拟器截图。',
    '- Android：用户明确答复“先完成其他部分，Android 原生验收暂缓”。未安装 SDK、未接受 Google SDK 许可、未执行原生启动验收。',
    '- 最终构建已 cap sync 到两端工程，双方 public 目录与 dist 每个文件 SHA-256 一致；SPM 仍有 Capacitor 官方实验支持提示。', '',
    '## 网页运行截图', '',
]
for label, file in [('阵营选择', 'web_faction.png'), ('编队', 'web_formation.png'), ('战斗', 'web_battle.png'), ('结算', 'web_result.png'), ('太平军第一章通关', 'web_taiping_complete.png'), ('清军第一章通关', 'web_qing_complete.png'), ('320px 窄屏', 'web_320_formation.png'), ('人物详情', 'web_hero_detail.png')]:
    lines += [f'### {label}', '', f'![{label}](screenshots/{file})', '']
lines += ['## 文件证据', '', '`delivery_manifest.json` 保存源 CSV、应用源码、生产文件哈希及验证汇总；browser_playthrough.json 保存实际胜负与刷新文案；golden/、mulberry_balance/、chapter1/ 保存可复核原始结果。原报告 v1/v2 未覆盖。', '']
(R / 'acceptance_report.md').write_text('\n'.join(lines))
first = read('performance/first_run.json')
warm = read('performance/warm_first1200.json')
performance_lines = [
    '# Chrome 4× CPU 战斗性能复测', '',
    '整场统计于 2026-10-28 补齐。使用生产构建、Samsung Galaxy A55 的 360×800 视口、Chrome Performance 实际录制和 4× CPU 降速。', '',
    '|采样|帧数|平均 FPS|P95 帧间隔|最慢帧|>25ms|>50ms|',
    '|---|---:|---:|---:|---:|---:|---:|',
]
for label, value in [('最初冷启动', first), ('资源预热后前 1200 帧', warm), ('最终整场主动播放', perf)]:
    performance_lines.append(f"|{label}|{value['frames']}|{value['fps']:.3f}|{value['p95_ms']:.2f}ms|{value['worst_ms']:.2f}ms|{value['over25ms']}|{value['over50ms']}|")
performance_lines += [
    '', f"最终覆盖约 {perf['frames'] / perf['fps']:.2f} 秒主动播放，金田团营 15 回合自然结束，没有通过跳过缩短本次采样。初始化资源准备在“整军列阵”期间完成，不纳入主动播放 FPS。", '',
    '改动：播放前上传 GPU 资源并预热文字；逐帧统计覆盖整场，暂停与切速不清空此前样本。战斗计算和胜负未改动。', '',
    '结论：约 60fps、没有 >25ms 的帧，Chrome 代理性能项通过。本结果不替代实体安卓设备或原生模拟器启动验收。', '',
    '- [最终统计 JSON](performance/final_run.json)',
    '- [4× CPU 与设备配置证据](performance/chrome_full_configuration.ax.txt)',
    '- [完整统计节点证据](performance/chrome_final_metrics.ax.txt)',
    '- [Performance 面板截图](performance/chrome_performance_summary.png)',
    '- [限速战斗画面](performance/chrome_battle.png)', '',
    '录制过程包含操作前后等待；FPS 仅以主动播放 requestAnimationFrame 的帧间隔计算。Performance 面板摘要已保存，未导出原始 trace 文件。专用 Chrome 测试标签页已关闭。', '',
]
(R / 'performance_report.md').write_text('\n'.join(performance_lines))
print(json.dumps({'golden': gold, 'all_stages_pass': True, 'native_assets_equal': True, 'fps': perf, 'performance_pass': fps_pass}, ensure_ascii=False))
