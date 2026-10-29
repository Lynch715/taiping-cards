# 人物资产管线

按 `docs/03-资产管线.md` 实现，Python 3.11+。

## 依赖与运行

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r tools/requirements.txt
.venv/bin/python tools/build_portraits.py
.venv/bin/python tools/build_portraits.py --id tp_shi_dakai
.venv/bin/python tools/build_portraits.py --check
.venv/bin/python tools/build_portraits.py --id tp_luo_dagang --id tp_shi_dakai --id qing_zeng_guofan --background bg_shared_river_camp
.venv/bin/python -m unittest discover -s tools -p 'test_build_portraits.py' -v
.venv/bin/python tools/build_batch_review.py
.venv/bin/python tools/build_head_review.py
.venv/bin/python tools/build_distinct_review.py
.venv/bin/python tools/build_sr_head_review.py
.venv/bin/python tools/build_sr_revision_review.py
.venv/bin/python tools/ingest_sr_full_bodies.py
.venv/bin/python tools/build_roster_review.py
.venv/bin/python tools/build_sr_full_body_details.py
.venv/bin/python tools/build_li_shixian_comparison.py
```

本次实际使用 Codex 已有的 Python 3.12.14、Pillow 12.3.0、numpy 2.3.5 完成验证；系统 `python3` 当前缺少 numpy。现有运行时可直接使用：

```sh
/Users/ruis/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 tools/build_portraits.py
```

`--rembg` 需要另行安装 rembg 和相应推理后端、准备模型；首次初始化可能下载模型。本次未运行真实 rembg 模型，测试通过注入移除函数验证参数分支。需要逐字节复现时，固定 Python、Pillow、numpy、WebP 编码器版本；使用 rembg 时还需要固定模型和推理后端。

## 输入与输出

- 读取 `data/characters.csv`、可选的 `data/npc_portraits.csv` 及 `assets/raw/` 正式目录，不会自动收录 `output/imagegen/` 中的测试插画。杂兵映射单独维护，固定身高系数0.93；背景合成饱和度45%，无SSR特效。
- 支持当前表的 `rarity_draft`；若有 `rarity` 列则优先使用，SSR 才叠加同 id 特效。
- 背景与特效必须为 1024×1536，不自动裁切或调整尺寸。背景必须不透明。
- 保留整个源画布，按 alpha>16 的外框决定缩放和定位，不裁掉人物或武器。Lanczos 产生的像素级外框扩展会通过轻微缩小处理。
- 人物目标高度为 `round(1300 * height_scale)`，缺少列或空值时用 `0.96`；非有限数值或超出 `0.90–1.00` 的值使人物表校验失败，退出码为 `2`，不会开始写入输出。即便只选部分 id，也先校验整张表。
- 先按目标高度等比缩放，再以宽度 `896px` 封顶。脚底固定在 `y=1392`，水平中心固定在 `512 + x_offset`；常规人物实际高度与目标相差不超过 `2px`，`WIDE` 人物因宽度限制会更矮。报告包含 `height_scale`。
- 主图 1024×1536，WebP 派生图分别为 400×600、160×240、96×144，质量 85。
- 无透明通道时，以四角均值为底色估计，按 CIE76 ΔE 建立候选区域，再从画布四边做四连通洪水填充；封闭在人物内部的近底色区域不会被移除。外轮廓向内羽化 1–2px，alpha 为 0→85→170→255，已移除的背景保持 alpha=0，不把底色模糊回边缘。
- 缺失背景时使用确定性的中性灰纸纹。缺失人物时不生成任何人物派生图，只在对照表放占位。
- `--check` 仍在内存中执行合成，仅更新 `assets/reports/`，不新建或覆盖人物派生图。
- `--id` 的报告与对照表只包含所选人物，可重复传参形成小批次；报告按传参顺序排列，重复 id 自动去重。交付全量验收图前需再次运行不带 `--id` 的命令。
- `--background bg_shared_river_camp` 仅为本次运行指定共用背景，不修改人物表中的原始分场景背景。汇总报告逐项记录原定与本次背景。

每次自动更新：`assets/reports/pipeline_report.csv`、`contact_sheet.png`、`silhouette_sheet.png`、`pipeline_summary.md`。剪影图将人物按实际合成位置全幅缩小后按太平天国／清朝两行排列（双阵营按清军时期形象计入清朝行，只出现一次），仅包含人物及其道具，不包含背景、脚下阴影或SSR特效；失败项显示占位。

`build_batch_review.py` 从人物表选择全部SSR，再加已通过的罗大纲一同验收，按各自原定背景合成。另生成10张正式背景总览 `background_contact_sheet.png`、背景尺寸/透明性报告 `background_report.csv`、结构化验证 `batch_validation.json`，并从 `full_body_distinct_v1/generation_manifest.json` 汇总当前批完整生成提示词。9张新人物的输入只能是本人确认头像、两个无脸风格局部和本人背景板；罗大纲全图不作为生成参考。它不会使用共用测试背景覆盖人物表，缺少本批输入时直接报错。全表缺失审计单独保存在 `full_body_distinct_v1/full_roster_audit/`。

`build_head_review.py` 只打包 `head_review_v2` 清单中的9张头像，在 `assets/concepts/heads_v2/` 保存独立原图并生成单独的头像九宫格、ZIP与原有资产保护校验。不会生成全身图或运行正式合成；头像确认后才进入全身阶段。

`build_distinct_review.py` 生成 `face_identity_sheet.png`，把9张确认头像与全身原图中的脸部局部并列放大。局部坐标是人工选取，只用于验收图，不改变游戏主立绘或派生图，也不代表自动证明了人脸相似度。

`build_sr_head_review.py` 从 `sr_head_review_v1` 生成记录打包25张SR头像，按9/9/7排成3张九宫格，并将第7.1节全部6组放进一张对比图。对比图里的彭玉麟、僧格林沁是已确认SSR头像参照，只参与排版，不用于他人生成。正式SR全身仍须等头像确认后制作。

`build_sr_revision_review.py` 保留v1原图，在v2目录保存S08/S13两张修订，与未改的S05/S16及SSR陈玉成组成五人对比图；保存21张通过、4张待同图复核的确认状态和当前25张打包。该脚本只用于本轮指定修订，不会自动生成全身。`audit_name_glyphs.swift`只读检查本机字体实际字形；远程webfont与界面显示另通过应用内浏览器验收，记录见`assets/reports/sr_head_review_v2/review_report.md`。

25张SR头像已全部确认，S08/S13固定v2。`ingest_sr_full_bodies.py`按`sr_full_body_v1`记录校验原生透明人物层、本人参考组合与安全边界后入正式目录；`build_roster_review.py`选择人物表中全部13位SSR及26位SR（39人）重新合成，保留R卡缺失情况在独立目录盘点中，不往39人验收图加占位。重复构建验证156份人物输出及6份主要报告。剪影固定两行：太平天国16人／清朝23人，程学启与张国梁标“双”且仅计一次。`build_sr_full_body_details.py`只在验收图中放大全身头部局部，并生成六组全身比较图，正式主图与派生图始终全幅等比。

`build_li_shixian_comparison.py`生成李世贤深褐战袍／皮甲背心／竖持大刀稳立的新稿与未改的陈玉成对比：400×600完整卡面、96×144原生小卡、同倍率剪影及李世贤的确认头像和全身头部局部。仅用于验收排版，不改变人物资产。

`build_r_head_review.py` 打包第8节17张待确认头像，生成9/8两批九宫格、全部6组同图对比、独立PNG压缩包和生成清单。杨秀清固定heads_v4，洪宣娇固定已确认SR版，仅用于并排验收。使用宋体face1覆盖“呤唎”等名字；重建前校验247份既有美术文件。17人头像确认前，不生成全身或重跑56人合成。

17张R头像现已全部确认：R01洪天贵福、R15胜保固定v2，其余15人用v1。`build_r_head_revision_review.py`保存两张修订对比并保留确认状态；`ingest_r_full_bodies.py`按本轮生成记录逐人核对四张参照、头像确认、原生透明度与几何安全边界，再入正式目录。17人均只提交本人头像、两个无脸局部和本人背景板；服装修正稿沿用同一组合，不混入别人的脸。

`build_complete_roster_review.py`按人物表构建全部56人（当前表15SSR+24SR+17R），原39人的原画和派生图都保持字节一致。重复两次比较224份人物输出及4份管线报告；全员剪影为太平26人／清朝含双阵营30人两行。`build_complete_face_review.py`另出56人面部总对照、7张分页、本批17人的两张面部对照和第8.1节6组全身比较。5位早期定稿没有独立头像，用冻结的原全身面部局部对照，明确标注，不当成独立的人脸验证。

```sh
python3 tools/ingest_r_full_bodies.py
python3 tools/build_complete_roster_review.py
python3 tools/build_complete_face_review.py
```

本批汇总与完整提示词见 `assets/reports/r_full_body_v1/`。人工验收局部只用于报告，正式卡面始终全幅等比缩放。报告字体修正为宋体face1，新增“呤唎 / 张国梁 / 樑”缺字回归；没有更改游戏页面字体。

## 战斗平衡模拟

`battle_sim.py` 只依赖 Python 标准库，读取 05 文件规定的六张 CSV，按关键词编译技能、羁绊、套装与专属。未知效果阻止战斗，`--audit-only` 输出无法解析项和逐人 E 预算。本轮使用用户更新后的 15 SSR + 24 SR + 17 R；君主 6 位、战斗卡 50 位。太平与清朝各有 6 位战斗 SSR，纯阵营 R / SR / SSR 均正式 5v5，候选池不足 5 人会报错。

第二轮总报告为 `assets/reports/balance_report_v2.md`；调整前输入、阶段试调、独立复核、39 件专属逐件诊断、装备敏感性、哈希与逐单元格改动均在 `assets/reports/balance_v2/`。v1 报告及 `balance_v1/` 保留历史原样；v1 的旧名单只有 4 位太平战斗 SSR，其 4v4 诊断不能与本轮 5v5 结果混用。复现 v1 须使用当时保留的脚本和输入。

```sh
python3 -m unittest discover -s tools -p 'test_ba*.py' -v
python3 tools/battle_sim.py --audit-only --output assets/reports/balance_v2/parser_audit.json
python3 tools/run_balance_v2_review.py --after-dir data
python3 tools/run_monarch_precision_v2.py
python3 tools/battle_report_v2.py
```

完整复核固定种子及参数，运行前记录输入和数值代码哈希，基础复核前后共 433,440 局，包含主测试、五套装备与四星专属敏感性、39 件专属三臂测试及君主另法诊断。运行期间不要修改 `battle_sim.py`、`balance_diagnostics.py`、`run_balance_v2_review.py`、`run_monarch_precision_v2.py` 或输入 CSV。前三次未通过的复核保留在 `balance_v2/validation_round_06/`、`validation_round_09/`、`validation_round_11/`；最终候选与选择记录见 `selected_candidate.json`。

`--n` 是每场景的镜像对局组数，每组交换攻守各打一局。默认 50 级同 3 星、无装备；支持 `--level`、`--stars`、`--gear-set 圣兵`、`--quality 精`、`--enhance 0`、`--exclusives`（4 星解锁），也可用 `--equipment-ids` 指定最多 4 件不重复部位，检验混搭与两件套门槛。`--no-report` 仅保存 JSON，避免试调覆盖总报告。

```sh
python3 tools/battle_sim.py --n 500 --lineups 200 --opponents 6 --seed 20263192 --gear-set 勇营 --output /tmp/yongying-check.json --no-report
python3 tools/balance_diagnostics.py exclusives --n 200 --duels 120 --seed 20263191 --output /tmp/exclusive-check.json
python3 tools/balance_diagnostics.py constraints --output /tmp/constraints-check.json
```

战斗卡出场率排除君主；依用户确认，君主的正式选用率为“本阵营胜率前 10% 阵容中的君主占比”，截断处并列按权重平分，太平 2 位、清朝 4 位分别要求至少 20%。等概率抽君主的输入频率不作为达标证明。候选11原1600阵容中恭亲王19.55%，独立扩大8000阵容后为25.09%，但慈禧18.18%仍不达标；完整记录保存在validation_round_11/。候选12仅调整慈禧，再用新种子复核全部项目。当前君主精度测试分4批独立2000阵容，合并后统一取本阵营前10%，每阵容在所属批次中面对16个随机对手并镜像，共32局。批次间允许同阵容再次被抽到；不把4批的选用率直接平均。扩大样本前后另512,112局，含每批辅助n=1场景，辅助场景估计不用于战斗指标。固定五人试配全部君主的最优率另列诊断，不替代正式口径。

专属逐件测试在双方同 4 星、相同阵容/对手/站位/地形/种子下，比较裸装、只有本件属性、完整本件专属，只有本人装备。君主使用其队伍胜率，战斗武将另列单挑收益。英雄四维预算、招牌机制与 R 卡单项上限独立审计。勇营周期回血、首次主动强化、洪仁玕政令强化及取消等新语义均有回归。

CSV 系数是本轮待审稿；模拟结果不代表实机战斗验收，也不证明所有等级与自由混搭装备均达到相同胜率。

## 警告与退出码

规范规定的 `UPSCALE`、`EDGE_CUT`、`WIDE`、`NO_ALPHA_FALLBACK`、`BG_MISSING` 均保留。

为避免空目录或坏素材被误判通过，增加 `SRC_MISSING`、`SRC_INVALID`、`BG_INVALID`、`FX_INVALID`、`NO_FOREGROUND`、`REMBG_ERROR`、`PLACEMENT_INVALID`。检查发现错误时继续处理其余人物，完整报告每个 id。超出安全区域或会裁到可见像素的定位不生成主图。

- 退出码 `0`：无错误及 UPSCALE / EDGE_CUT；其他警告仍需人工复核。
- 退出码 `1`：已生成报告，但存在上述阻断验收项。
- 退出码 `2`：人物表、参数或可选 rembg 初始化错误，无法开始正常处理。

失败项不会删除或覆盖以前的派生图。验收以本次 CSV 为准，不能以旧文件仍然存在判断本次成功。

## 自动回归范围

28 项测试使用临时目录中的合成素材，覆盖：Lab 色差、alpha 阈值、四边连通抠图、人物内部 ΔE<5 区域在抠图与合成后保留、1–2px 羽化、四连通与开放通道、全画布缩放与脚底/中心定位、过宽与放大警告、缺失与无效输入、禁止裁切、SSR 滤色与 alpha、rembg 分支、四档尺寸、输出字节复现、检查模式不改人物输出、单人筛选与表格校验、小批次顺序与去重、共用背景覆盖且不改人物表；新增身高系数的缺省兼容、边界值与非整数目标、非法值退出码和输出保护、未选中行校验、随系数变化的宽度/放大阈值、不同身高的字节复现、只含人物的剪影及检查模式报告。

这些是管线功能验证，不代表正式人物的画风、服饰、全身构图或照片相似度通过验收。

## 养成与八章模拟（0.3.0 评审稿）

CSV 导出与经济模型复用产品纯函数，Node.js 22+ 使用 `--import` 启动 tsx，不使用 CLI 的 IPC 服务。推荐从项目根目录运行：

```sh
python3 tools/export_data.py
python3 tools/battle_sim.py --economy --mode battle --n 100 --seed 71000 --label replay
node --import ./app/node_modules/tsx/dist/loader.mjs tools/economy_behavior.ts mode=battle n=100 seed=71000 attempts=3 tables=assets/reports/progression/selected_tables.json out=assets/reports/progression/reproduce_after.json
python3 tools/build_progression_golden.py
npm --prefix app test
python3 tools/report_economy.py
```

`--economy --tune` 会写入两张经济表，普通复跑不调参。0.3.0历史候选的独立复核是 `validation_candidate02.json`；相同种子的原始两表对照是 `validation_baseline02.json`。`tables=` 在进程内覆盖经济数据，不覆盖正式 CSV。每关每次上线尝试三局是模型假设，产品不限制尝试次数；1/10局敏感性另列。报告为 `assets/reports/economy_report.md`，逐项披露未达标，不因功能回归通过而判定经济全部通过。

`calibrate_growth.py` 使用冻结的成长参考配置，将五人均级归一到六关含首尾插值，再校准敌军等级；用户另准许后期敌军提升星级至6★、等级仍不超过100。`--promote` 仅在96关抽样胜率全部合格时写入关卡。人物、技能、基础杂兵、装备规则均受原表哈希保护。运行期间不要改战斗源码或输入；失败与修订批次保留在逐关JSON中。

## 后六章难度校准（0.3.1）

全96关的逐关结果见 `assets/reports/chapter_difficulty_report.md` 和同名CSV；本轮原表快照、四分位玩家配置、训练/独立检验、全部数值改动与浏览器证据保存在 `assets/reports/chapters_3_8/`。

`stage_difficulty.py` 集中实现07第5.4节：第三章以后史实败仗在位置目标两端各减10个百分点、最低50%；太平第七章不是统一难度。导出器要求完整的两阵营8×6关卡网格，拒绝缺失或非法的history_result。

```sh
PYTHONPATH=tools python3 tools/calibrate_growth.py --profiles assets/reports/progression/validation_candidate02.json --chapters 3,4,5,6,7,8 --stages assets/reports/chapters_3_8/before/data/stages.csv --out assets/reports/chapters_3_8/replay_calibration --fixed-stars --raise-stars-for tp_8_5,qing_8_4,qing_8_6
python3 tools/verify_early_chapters.py
python3 tools/report_chapter_difficulty.py
```

上方校准命令只读本轮输入快照，不覆盖正式关卡。`--promote` 仅在所选关卡全部通过时回写enemy_level、recommended_power与获准星级。不要将raise-stars-for重复应用到已升星的当前表；需要续跑时仍传本轮before快照。正常结束长任务优先等其完成；若必须停止，SIGINT可能被进程池捕获后继续处理排队任务，完整停止本任务进程和子进程后再续跑，避免两个作业争写同一结果目录。

## 养成与难度联合校准（08第11节）

新默认入口是`joint_behavior.ts`，模型和游戏直接共享`formation.ts`的地形/克制试算。每日两次登录，每关3次扫荡、整个军册每日最多30次；真实战斗模式才计入节奏验收。`mode=profile`只按假设均级收集成长训练参照，不代表实际通关结果。

```sh
python3 tools/export_data.py
python3 tools/joint_cohort.py --out assets/reports/joint_v2/replay --n 20 --seed 151000 --workers 4
python3 tools/joint_iteration.py --profiles assets/reports/joint_v2/replay/behavior.json --out assets/reports/joint_v2/replay_calibration --workers 6 --n 1000
python3 tools/refine_joint.py --profiles assets/reports/joint_v2/replay/behavior.json --out assets/reports/joint_v2/refine_calibration --workers 6 --n 1000
python3 tools/verify_joint.py --profiles assets/reports/joint_v2/replay/behavior.json --out assets/reports/joint_v2/fixed_verification --workers 6 --n 1000
```

`joint_iteration.py`从冻结的最初关卡种子搜索历史增员、星级、限定等级；`refine_joint.py`保留已有配置，在目标范围内平滑章内梯度，触及上限后先提升敌星再继续搜等级。两者只有显式`--promote`且96关全部通过才写回正式关卡表。`verify_joint.py`只复核当前配置，不写正式数据。

`joint_metrics.py`按账号检查最长等待、章末军功比例、入章主力星级与总扫荡次数，章耗时另按阵营样本均值检查。中间轮次和失败样本全部保留，不能把`mode=profile`结果或历史金标准当作最终实际战役验收。

## C批兵装图标

读取独立映射 `data/equipment_icons.csv`；不修改 `equipment.csv` 或战斗JSON。原生透明图留在 `assets/raw/equipment/generated/`，等比缩放、平移输出 `assets/raw/equipment/{id}.png` 的512×512母版。主要物件按alpha>16约80%居中，同时保留全部原生低alpha边缘，不裁物、不抠白。源图触边或过小会中止。

```sh
python3 tools/build_equipment_icons.py --report-dir assets/reports/equipment_batch_c_20261029
python3 tools/test_build_equipment_icons.py
python3 tools/build_equipment_review.py
```

产物为Q85的128与64 WebP；实际网页只分发一张272×340的64px雪碧图（4列×5行，68px单元、每边2px间距）和20张按需128图。军械库及奖励使用64，详情128；离线事件或加载失败时，详情放大64单元回退。雪碧图进入首装缓存，128目录排除在core之外，已看过的128可增量缓存并迁移。64对照表直接取解码后正式雪碧单元，以原尺寸排版。

四张地形降质采用 `tools/build_battle_backgrounds.py --quality 75`；默认仍为09的Q80。C批为守住10MB首装上界将四图降至Q75，保留Q80备份与所有PNG母版。复建C批版本须指定Q75，不要误用默认Q80覆盖。体积与历史超时调查见C批报告目录。
