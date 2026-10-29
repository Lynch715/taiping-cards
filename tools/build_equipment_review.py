#!/usr/bin/env python3
"""Assemble C-batch review from final artifacts and measured evidence."""
from pathlib import Path
import json,html,hashlib,shutil,zipfile
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1]
R=ROOT/'assets/reports/equipment_batch_c_20261029'
def read(name):return json.loads((R/name).read_text())
def h(value):return html.escape(str(value))
def main():
 p=read('equipment_pipeline.json');sizes=read('size_comparison.json');tests=read('tests_final.json');protected=read('protected_validation.json');repeat=read('repeat_validation.json');timings=read('B_timeout_comparison.json')
 build=json.loads((ROOT/'app/dist/pwa-build.json').read_text());assert build['firstInstallUpperBound']==sizes['C_q75_first_install_upper_bound']<=10_000_000
 assert tests['numFailedTests']==0 and tests['numPassedTests']==66
 shutil.copy2(ROOT/'app/dist/pwa-build.json',R/'pwa-build.json')
 font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Songti.ttc',19,index=1);title=ImageFont.truetype('/System/Library/Fonts/Supplemental/Songti.ttc',30,index=1)
 sheet=Image.new('RGB',(1100,1180),'#ede3cc');d=ImageDraw.Draw(sheet);d.text((26,18),'兵装图标 · 128px派生图对照',font=title,fill='#242019')
 sets=['圣兵','勇营','洋械','铁骑','江防'];slots=['兵刃','甲胄','坐骑','兵书']
 for r in p['icons']:
  x=130+slots.index(r['slot'])*240;y=90+sets.index(r['set'])*210
  if r['slot']=='兵刃':d.text((25,y+42),r['set'],font=font,fill='#245249')
  icon=Image.open(ROOT/'assets/equipment'/r['id']/'128.webp').convert('RGBA');sheet.paste(icon,(x,y),icon);d.text((x-5,y+139),r['name'],font=font,fill='#242019');d.text((x+35,y+167),r['slot'],font=font,fill='#665942')
 sheet.save(R/'contact_sheet_128.png',compress_level=9)
 table='\n'.join(f"|{r['set']} · {r['slot']}|{r['name']}|`{r['id']}`|{r['webp64_bytes']}|{r['webp128_bytes']}|OK|" for r in p['icons'])
 terrain='\n'.join(f"|{r['id']}|{r['q80_bytes']:,}|{r['q75_bytes']:,}|{r['saved_bytes']:,}|" for r in sizes['terrain'])
 report=f'''# C批兵装美术验收

日期：2026-10-29。A、B批已获用户确认；C批完成待验收。本次未发布。

## 交付及管线

20个独立兵装图标，五套×四部位；原有100行兵装按套装／部位映射为20图，五品质共用原画。512×512透明PNG母版，物件约80%、3/4视角、左上光，厚涂静物；无背景、无可读文字。马为头颈静物，驮马带鞍绳，舢板整船在画内；骑射卷上的人马是抽象图示。

- 原生生成图：`assets/raw/equipment/generated/{{id}}.png`，均1254×1254，保留原始透明通道。
- 512母版：`assets/raw/equipment/{{id}}.png`。整画布等比缩放、平移；alpha>16用于物件定位，同时保留低alpha原生边缘；不裁物、不抠白。蒙古马初稿耳尖触边退稿，最终版本重新生成，退稿及提示词保留。
- 派生：`assets/equipment/{{id}}/128.webp`、`64.webp`，Q85；20项无UPSCALE／EDGE_CUT。对照：`contact_sheet_128.png`、`contact_sheet_64_actual.png`。
- 正式64：`assets/equipment/sprite-64.webp`，272×340、4列×5行、单元68px（64px画面＋每边2px间距），共{sizes['sprite_bytes']:,}字节。64对照表直接提取正式WebP解码单元，1像素对应1像素，不用独立缩略图替代。
- 新增独立映射`data/equipment_icons.csv`；`equipment.csv`、战斗JSON、公式、种子、候选数、金标准不变。图标元数据位于platform层，未进入核心数值表。
- 军械库／真实首通奖励64，详情128。品质粗／制／精／珍／绝由CSS灰褐／绿／蓝／紫／金边框区分，不增加品质原画。

|套装／部位|名称|icon_id|独立64 WebP字节|128 WebP字节|管线|
|---|---|---|---:|---:|---|
{table}

独立64文件只作派生交付与复核，不进入网页公共目录；网页64只发一张雪碧图。20张128合计{sizes['detail128_bytes']:,}字节，不进入core首装缓存，打开详情按需下载；离线状态或图片加载失败显示放大后的64单元。已看过128允许增量缓存和升级迁移，但不在安装时下载。

## 首装体积与四地形Q75

沿用严格十进制10MB（10,000,000字节）门槛。先实测Q80构建：10,082,144字节，超82,144；按用户指示首先把四张地形WebP统一降至Q75。无重绘、无Python模糊、PNG母版逐字节不变。

|地形|Q80字节|Q75字节|减少字节|
|---|---:|---:|---:|
{terrain}
|合计|{sizes['terrain_q80_bytes']:,}|{sizes['terrain_q75_bytes']:,}|{sizes['terrain_q80_bytes']-sizes['terrain_q75_bytes']:,}|

B批首装上界9,987,608；C批Q80为10,082,144；C批Q75最终为**{build['firstInstallUpperBound']:,}字节（{build['firstInstallUpperBound']/1e6:.6f}MB）**，余量{10_000_000-build['firstInstallUpperBound']:,}字节。缓存本体{build['initialCacheBytes']:,}字节。上界采用原构建口径：首次未缓存页面与安装拉取按两份计，服务工作线程按两份计，另加100,000字节安装图标等余量；不是只报压缩后的缓存本体。全量包含后续章节与按需详情，共{build['totalBytes']:,}字节，不等于首装。

`core`只有`./assets/equipment/sprite-64.webp`一个图标文件，128目录条目0。证据：`pwa-build.json`、`size_comparison.json`、`build_q80.log`（预期超限失败）、`build_final.log`（通过）。Q80备份位于`before/`，Q75编码参数`cwebp -q 75 -m 6 -sns 40`。四图已重新用实际5敌＋5我截图复核，见`battle_q75_*.jpg`；卡位保持B批32px上边距。

## 浏览器与离线验证范围

Codex应用内浏览器、localhost，桌面1280×900与手机模拟390×844；无Chrome降级，无实体手机测试。

- 正常游戏使用`qa=equipment-C-20261029`隔离军册，从阵营选择、首关出征、14回合获胜到真实兵装入库，奖励为太平号衣。64图标、点击128详情、进入军械库均截图留存（`game_first_clear_reward.jpg`／`game_first_clear_detail.jpg`／`game_inventory.jpg`），没有修改正常玩家军册。
- 独立验收页使用生产EquipmentIcon、EquipmentDetails、GrowthPages、EquipmentRewards组件；100件UI样本只在内存，不读写存档，不作为奖励经济正确性的证据。
- 首屏20个图标逐个DOM实测64×64，仅一次雪碧图请求、0个128请求；点击太平腰刀详情后新增对应128请求，naturalWidth=128。五品质同一图标、五种边框颜色实测见`browser_evidence.json`。
- 模拟offline事件后打开此前未看的舢板：详情区域128×128，数据源64雪碧单元，0个128 img元素且不增加该详情请求；这是应用状态模拟，未关闭系统网络。
- 真实加载失败另测：暂移出未访问过的江防图128文件，Vite返回HTML fallback（HTTP200，不能称404），img解码触发onError后改为64；测试后文件恢复并校验字节一致。
- 服务工作线程自动测试另覆盖：离线fetch拒绝、未访问128返回503而已缓存雪碧200、在线访问128后离线再开、更新迁移已有128不提前下载；这与上面的浏览器状态模拟分别记载。
- 手机图标仍为64×64；军械库document.scrollWidth=390；详情宽350px、无横向溢出。见`ui_*mobile*.jpg`。
- 迭代时独立QA页曾因HMR重复createRoot出现开发警告，已补dispose卸载；清洁加载复核另记录。正常游戏及四地形控制台无错误。

## 回归、保护与B批超时调查

- 前端15文件**66/66通过**；完整金标准套件含原100场、养成100场、章节100场及联合100场的日志／结果核对，冻结fixture未重建。默认全局5秒配置不变，最终命令单worker、单测30秒；本次受查用例实际均低于5秒。
- 兵装管线4/4，数据导出6/6；生产构建、TypeScript通过。记录见`tests_final.log/json`、`icon_pipeline_tests.log`、`data_export_tests.log`、`build_final.log`。
- 开始记录479个既有文件，{protected['unchanged']}个SHA256不变，只有4张获准地形WebP变化，意外变更0。包括所有原CSV、core代码／JSON、既有原画、人物派生、地形PNG及冻结fixtures。
- {repeat['outputs']}个新母版／派生／公共图像／元数据重复管线后逐字节一致。原生20图未改；Q80备份留档。证据见`protected_validation.json`、`repeat_validation.json`。
- B批5项：progression-golden 5834ms、chapters-golden 6392ms、joint-golden 7627ms；joint-progression合法独立预测7640ms、地形／克制换阵5967ms。当前单worker分别406.17／450.41／519.20／699.84／959.41ms，四worker均小于1.1秒。
- 战斗100场trace=true中位244.59ms，trace=false108.74ms；一次20候选×20种子的智能建议约362–392ms。布阵测试分别约820／1600场试算，不能把单测总时长说成一局耗时。
- 当前没有复现战斗／布阵持续变慢。B批并行出图编码时其他管线也显著变慢，资源争用最符合记录，但没有当时主机采样，不能唯一归因。完整五项名称、耗时、profile热点、证据限制见[B_timeout_investigation.md](B_timeout_investigation.md)。

## 图源及复现

`docs/reference/npc_sources.md`已补20项，各项注明参考能支持什么、哪些是游戏重建；书卷不声称是真文献摹本。完整提示词与生成路径在`generation_manifest.json`、`prompts/`。

```sh
python3 tools/build_equipment_icons.py --report-dir assets/reports/equipment_batch_c_20261029
python3 tools/build_battle_backgrounds.py --id bg_battle_land --id bg_battle_siege --id bg_battle_defend --id bg_battle_river --quality 75 --report-dir assets/reports/equipment_batch_c_20261029/q75
python3 tools/test_build_equipment_icons.py
python3 -m unittest discover -s tools -p 'test_export_data.py' -v
cd app
npm test -- --maxWorkers=1 --testTimeout=30000
npm run build
```

Python需Pillow／numpy，路径见tools/README.md；验收页面须由HTTP服务提供，不用file://。`tools/build_equipment_review.py`整理图表与zip，不做出图。此包为美术及接入验收材料，未发布。
'''
 (R/'review_report.md').write_text(report)
 cards=[]
 for r in p['icons']:
  ident=r['id'];cell=p['atlas']['icons'][ident]
  cards.append(f'''<article class="icon-card"><h3>{h(r['name'])}</h3><p>{h(r['set'])} · {h(r['slot'])}</p><div class="pair"><figure><span class="sprite" role="img" aria-label="{h(r['name'])}64px" style="background-position:-{cell['x']}px -{cell['y']}px"></span><figcaption>实际64×64</figcaption></figure><figure><img src="../../equipment/{ident}/128.webp" width="128" height="128" alt="{h(r['name'])}128px"><figcaption>详情128×128</figcaption></figure></div><p class="code">{ident}</p><p><a href="../../raw/equipment/{ident}.png">512母版</a> · <a href="../../raw/equipment/generated/{ident}.png">原生透明PNG</a> · <a href="prompts/{'tieqi_zuoqi_revision' if ident=='tieqi_zuoqi' else ident}.txt">提示词</a></p><small>128 WebP {r['webp128_bytes']:,}B · 管线OK</small></article>''')
 def figures(items,cls='gallery'):
  return f'<div class="{cls}">'+''.join(f'<figure><a href="{file}"><img src="{file}" alt="{h(label)}" loading="lazy"></a><figcaption>{h(label)}</figcaption></figure>' for file,label in items)+'</div>'
 screen=figures([('game_first_clear_reward.jpg','正常游戏 · 首关真实奖励64px'),('game_inventory.jpg','正常游戏 · 军械库64px'),('ui_detail_mobile_128.jpg','手机详情 · 按需128px'),('ui_reward_mobile.jpg','四部位奖励组件 · 64px')],'gallery phones')
 terrainpics=figures([(f'battle_q75_{key}.jpg',label+' · Q75实际十卡') for key,label in [('land','陆战'),('siege','攻城'),('defend','守城'),('river','水战')]])
 terrainrows=''.join(f'<tr><td>{h(r["id"])}</td><td>{r["q80_bytes"]:,}</td><td>{r["q75_bytes"]:,}</td><td>{r["saved_bytes"]:,}</td></tr>' for r in sizes['terrain'])
 timeoutrows=''.join(f'<tr><td>{h(r["file"])}<br><small>{h(r["test"])}</small></td><td>{r["B_ms"]}</td><td>{r["current_1worker_ms"]:.2f}</td><td>{r["current_4worker_ms"]:.2f}</td></tr>' for r in timings)
 comparisons=''.join(f'<details><summary>{h(r["id"])} Q80／Q75原图对比</summary><div class="gallery"><figure><img loading="lazy" src="before/{r["id"]}_q80.webp" alt="Q80"><figcaption>Q80 · {r["q80_bytes"]:,}B</figcaption></figure><figure><img loading="lazy" src="../../battle/{r["id"]}.webp" alt="Q75"><figcaption>Q75 · {r["q75_bytes"]:,}B</figcaption></figure></div></details>' for r in sizes['terrain'])
 page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>C批 · 20兵装验收</title><style>
*{box-sizing:border-box}body{margin:0;background:#ede3cc;color:#28231b;font-family:Songti SC,STSong,serif;line-height:1.8}main{max-width:1120px;margin:auto;padding:28px 24px 80px}h1{font-size:32px;margin:8px 0}h2{border-bottom:3px double #9c855f;padding-bottom:8px;margin-top:38px;font-size:23px}h3{font-size:18px;margin:8px 0}p{margin:10px 0}a{color:#245249;text-underline-offset:4px}nav{display:flex;gap:16px;flex-wrap:wrap}.badge{display:inline-block;background:#245249;color:#fff;padding:5px 12px;margin:5px 10px 8px 0}.cards{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px}.icon-card{background:#f5eddc;border:1px solid #ad9975;padding:16px 10px;text-align:center}.icon-card p{font-size:12px}.code{font:11px monospace;overflow-wrap:anywhere}.pair{display:flex;justify-content:center;align-items:center;gap:10px;min-height:175px}.pair figure{margin:0}.pair figcaption{font-size:11px;margin-top:8px}.pair img,.sprite{background-color:#e5dac1;outline:1px solid #9c855f}.sprite{display:block;width:64px;height:64px;flex:none;background-image:url('../../equipment/sprite-64.webp');background-size:272px 340px;background-repeat:no-repeat}.pair img{display:block}.gallery{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}.gallery figure{margin:0}.gallery img{max-width:100%;height:auto;display:block}.gallery figcaption{font-size:13px;margin:8px 0}.phones{grid-template-columns:repeat(4,minmax(0,1fr))}.phones img{width:100%}.contact{display:block;width:100%;max-width:1000px;height:auto}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:13px}td,th{border:1px solid #c1b294;padding:9px;text-align:left}th{background:#dfd0ae}small{font-size:11px;overflow-wrap:anywhere}details{border:1px solid #b3a17e;padding:12px;margin:14px 0}summary{cursor:pointer}.note{border-left:4px solid #a37a39;padding:12px 18px;background:#e6dcc3}.legend{display:flex;gap:16px;flex-wrap:wrap}.legend span{padding:3px 12px;border:2px solid var(--q)}@media(max-width:1000px){.cards{grid-template-columns:repeat(2,minmax(0,1fr))}.phones{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:540px){main{padding:20px 12px 60px}h1{font-size:27px}.cards{grid-template-columns:1fr}.gallery{grid-template-columns:1fr}.phones{grid-template-columns:repeat(2,minmax(0,1fr))}.pair{gap:32px}table{min-width:660px}} </style><main>
<h1>C批 · 二十兵装验收</h1><p>A、B批已通过 · C批待验收 · 2026-10-29 · 未发布</p><nav><a href="#icons">64／128对照</a><a href="#screens">游戏截图</a><a href="#size">体积</a><a href="#timeout">5项超时</a><a href="review_report.md">完整报告</a><a href="../../../docs/reference/npc_sources.md">图源与限度</a><a href="../../../outputs/equipment_batch_c_20261029/C批兵装美术验收包.zip">下载验收包</a></nav>
<p><span class="badge">20／20 无裁切、无放大</span><span class="badge">首装9.799724MB ≤ 10MB</span><span class="badge">回归66／66</span></p><p class="note">列表与奖励使用一张38,004B的64px WebP雪碧图；20张128px合计107,018B，打开详情才下载。离线或加载失败回退64。所有品质共用物件，颜色由界面边框区分。</p>
<h2 id="icons">64px实际效果 · 五套×四部位</h2><p>以下总览直接取正式WebP雪碧图解码单元，各物件64×64、不放大；下方逐项同时提供64及128实际CSS尺寸、512母版和原生透明PNG。</p><a href="contact_sheet_64_actual.png"><img class="contact" src="contact_sheet_64_actual.png" alt="20图64px实际像素对照" width="1000" height="650"></a><p><a href="contact_sheet_128.png">128px总览</a> · <a href="pipeline_report.csv">逐项管线表</a> · <a href="equipment_pipeline.json">机器报告</a> · <a href="generation_manifest.json">生成清单</a></p><div class="legend"><span style="--q:#8a7962">粗</span><span style="--q:#63815c">制</span><span style="--q:#4c7296">精</span><span style="--q:#886099">珍</span><span style="--q:#b8893b">绝</span></div><div class="cards">'''+''.join(cards)+'''</div>
<h2 id="screens">真实游戏与手机界面</h2><p>首通奖励及军械库使用独立测试军册qa=equipment-C-20261029；详情与四部位样本使用生产组件的内存样本页。390×844手机模拟视口，没有实体手机测试。</p>'''+screen+'''<details><summary>在线128、离线64及加载失败64</summary><p>应用offline事件模拟与服务工作线程离线拒绝测试分别记录。另暂移一张未访问128图验证真实img加载失败回退，随后恢复；不是关闭系统网络。详见<a href="browser_evidence.json">浏览器证据</a>与<a href="tests_final.log">SW回归记录</a>。</p>'''+figures([('ui_detail_online_128.jpg','在线 · naturalWidth128'),('ui_detail_offline_64.jpg','离线状态 · 放大64单元'),('ui_detail_network_failure_64.jpg','图像加载失败 · 回退64'),('ui_sheet_desktop.jpg','桌面原生64px对照')])+'''</details>
<h2 id="size">首装上界与地形Q75</h2><p>严格10,000,000字节门槛。先测C批Q80为10,082,144字节，超82,144；依约四张地形统一Q75后，最终9,799,724字节，余200,276字节。PNG母版不变。缓存本体4,731,978字节，完整包含后期内容，不等于首装。</p><div class="scroll"><table><tr><th>地形</th><th>Q80字节</th><th>Q75字节</th><th>节省</th></tr>'''+terrainrows+'''<tr><th>合计</th><th>691,132</th><th>549,922</th><th>141,210</th></tr></table></div><p><a href="size_comparison.json">体积证据</a> · <a href="pwa-build.json">最终预缓存清单</a> · <a href="build_q80.log">Q80超限记录</a> · <a href="build_final.log">最终构建</a></p>'''+comparisons+'''<details><summary>四种Q75地形实际叠卡截图</summary><p>沿用B批生产BattleScene和实际关卡编队，5敌＋5我，32px上边距；只更换了编码质量。</p>'''+terrainpics+'''</details>
<h2 id="timeout">B批默认5秒超时的五项</h2><p>当前同代码单worker／四worker复测全部通过，未复现持续变慢。前三项是100／100／200次批量战斗执行，后两项布阵约820／1600场试算；不能把单测时长当一局耗时。</p><div class="scroll"><table><tr><th>测试及完整用例名</th><th>B批ms</th><th>本批1 worker ms</th><th>本批4 workers ms</th></tr>'''+timeoutrows+'''</table></div><p>当前100场战斗约109–245ms，一次400场布阵试算约362–392ms。B批同时编码／出图时其他管线也显著变慢，资源争用最符合记录；缺少当时CPU／内存采样，不能唯一归因。没有修改战斗算法、候选数、种子或默认5秒配置。</p><p><a href="B_timeout_investigation.md">完整定位报告与限制</a> · <a href="B_timeout_comparison.csv">五项CSV</a> · <a href="combat_benchmark.json">基准</a> · <a href="combat.cpuprofile">CPU采样</a></p>
<h2>验证与图源</h2><p>66/66前端回归，4/4图标管线，6/6数据导出；479个既有文件中475个哈希不变，仅授权的4张地形WebP改变。84个新产物重复构建逐字节一致。100组原战斗金标准及其他冻结fixtures未重建，战斗core、原始CSV及PNG母版不变。</p><p><a href="protected_validation.json">保护检查</a> · <a href="repeat_validation.json">重复构建</a> · <a href="../../../docs/reference/npc_sources.md">20项图源与证据限度</a> · <a href="review_report.md">完整交付说明及复现命令</a></p><p>图源用于品类研究，颜色、书卷、具体鞍具与刀具细节明确标为项目重建；不把游戏兵书称作馆藏文献复制。最终审美和64px辨识度交用户验收。</p></main></html>'''
 (R/'review.html').write_text(page)
 print('Review updated:',R/'review.html')

def package():
 out=ROOT/'outputs/equipment_batch_c_20261029';out.mkdir(parents=True,exist_ok=True)
 files=set()
 for folder in ['assets/raw/equipment','assets/equipment','assets/reports/equipment_batch_c_20261029','app/public/assets/equipment']:
  files.update(p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
 for key in ['land','siege','defend','river']:
  files.update([ROOT/f'assets/battle/bg_battle_{key}.webp',ROOT/f'app/public/assets/battle/bg_battle_{key}.webp'])
 for path in ['data/equipment_icons.csv','docs/01-美术规范.md','docs/03-资产管线.md','docs/09-补充美术资源.md','docs/reference/npc_sources.md','docs/reference/style_swatch_impasto_cloth.png','docs/reference/style_swatch_impasto_sky.png','docs/reference/npc/npm_ruizhou_article.pdf','docs/reference/npc/npm_ruizhou_plate.png','tools/build_equipment_icons.py','tools/build_equipment_review.py','tools/build_battle_backgrounds.py','tools/benchmark_equipment_c.ts','tools/export_data.py','tools/test_build_equipment_icons.py','tools/README.md','app/src/platform/equipment-art.ts','app/src/platform/equipment-icons.generated.json','app/src/ui/EquipmentArt.tsx','app/src/ui/GrowthPages.tsx','app/src/ui/Game.tsx','app/src/ui/style.css','app/src/qa/equipment-art-review.tsx','app/equipment-art-review.html','app/scripts/build-pwa.mjs','app/scripts/sw-template.js','app/tests/equipment-art.test.ts','app/tests/pwa.test.ts','assets/reports/npc_batch_b_20261029/regression_tests.log']:
  files.add(ROOT/path)
 files={p for p in files if p.name not in ['package_manifest.json','CHECKSUMS.sha256','package_build.log']}
 entries={str(p.relative_to(ROOT)):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(files)}
 (R/'package_manifest.json').write_text(json.dumps({'format':'C art and integration review; no player saves; not a release','files':entries},ensure_ascii=False,indent=2)+'\n')
 (R/'CHECKSUMS.sha256').write_text(''.join(v['sha256']+'  '+k+'\n' for k,v in entries.items()))
 files.update([R/'package_manifest.json',R/'CHECKSUMS.sha256'])
 target=out/'C批兵装美术验收包.zip'
 with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for path in sorted(files):z.write(path,path.relative_to(ROOT))
 with zipfile.ZipFile(target) as z:
  assert z.testzip() is None
  for name,record in entries.items():assert hashlib.sha256(z.read(name)).hexdigest()==record['sha256']
 print(json.dumps({'zip':str(target),'files':len(files),'bytes':target.stat().st_size,'sha256':hashlib.sha256(target.read_bytes()).hexdigest()},ensure_ascii=False))

if __name__=='__main__':main();package()
