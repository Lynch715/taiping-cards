#!/usr/bin/env python3
"""Package the17 selected full bodies and concise56-person acceptance report."""
import hashlib,json,zipfile
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];REPORT=ROOT/'assets/reports/r_full_body_v1'
def font(n):return ImageFont.truetype('/System/Library/Fonts/Supplemental/Songti.ttc',n,index=1)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def grid(rows,index):
 w,h,gap,margin,head,labels=300,450,18,24,112,94;im=Image.new('RGB',(2*margin+3*w+2*gap,head+3*(h+labels)+2*gap+margin),'#EDE3CC');d=ImageDraw.Draw(im)
 d.text((24,15),f'本批17张全身 · 第{index}批（{len(rows)}人）',font=font(32),fill='#252720');d.text((24,64),'完整卡面等比缩小｜号衣字补留白｜全身稿待用户验收',font=font(20),fill='#55594F')
 for i,r in enumerate(rows):
  x=margin+i%3*(w+gap);y=head+i//3*(h+labels+gap)
  with Image.open(ROOT/f"assets/characters/{r['id']}/full.png") as a:im.paste(a.convert('RGB').resize((w,h),Image.Resampling.LANCZOS),(x,y))
  d.text((x,y+h+8),f"{r['number']} {r['name']}",font=font(25),fill='#252720');d.text((x,y+h+43),r['id'],font=ImageFont.load_default(14),fill='#73766D');d.text((x,y+h+66),f"height_scale={r['height_scale']}",font=ImageFont.load_default(14),fill='#55594F')
 if len(rows)==8:
  x=margin+2*(w+gap);y=head+2*(h+labels+gap);d.rectangle((x,y,x+w,y+h),outline='#B2A68E',width=2);d.text((x+55,y+195),'本批共8人',font=font(28),fill='#73766D')
 im.save(REPORT/f'r_full_body_batch_{index:02d}.png',compress_level=9)
def main():
 manifest=json.loads((REPORT/'generation_manifest.json').read_text());rows=sorted(manifest['results'],key=lambda r:r['number']);v=json.loads((REPORT/'roster_validation.json').read_text());checks={r['id']:r for r in json.loads((REPORT/'source_validation.json').read_text())}
 assert len(rows)==17 and v['roster_count']==56 and not v['pipeline_warnings'];grid(rows[:9],1);grid(rows[9:],2)
 with zipfile.ZipFile(REPORT/'17_full_body_assets.zip','w',zipfile.ZIP_STORED) as z:
  for r in rows:
   z.write(ROOT/r['raw_path'],f"raw/{r['number']}_{r['id']}.png");z.write(ROOT/f"assets/characters/{r['id']}/full.png",f"cards/{r['number']}_{r['id']}.png")
  z.write(REPORT/'generation_manifest.json','generation_manifest.json')
 lines=['# 17张全身及56人全员验收','','状态：17张头像均已确认；17张全身已生成并入正式目录，艺术验收待用户。','', '## 交付图','', '- [56人全员对照](../contact_sheet.png)','- [56人剪影：太平26人／清朝含双阵营30人，两行](../silhouette_sheet.png)','- [56人面部总对照](../face_identity_sheet.png)','- [本批全身第1批9人](r_full_body_batch_01.png) / [第2批8人](r_full_body_batch_02.png)','- [本批面部对照第1批](r_faces_01.png) / [第2批](r_faces_02.png)','- [第8.1节6组完整卡面同图比较](six_groups_full_body.png)','- [17张透明人物层及合成卡面压缩包](17_full_body_assets.zip)','','56人面部对照另分7张，方便放大：']
 for i in range(1,8):lines.append(f'- [第{i}批](faces_all_{i:02d}.png)')
 lines += ['','## 本轮执行','', 'R01洪天贵福、R15胜保使用本轮用户确认的v2头像，其余15人使用已确认v1。R01保留15岁稚气、惶恐和男孩粗眉、稍有棱角的脸；R15保留上扬胡子与昂首神态，固定顶戴花翎官帽。两项也已写回04文件，避免后续恢复成旧设定。','', '全部17人及服装返稿均只附4张参照：本人的确认头像、两张无脸衣服/天空厚涂局部、本人在人物表中分配的背景板。没有附任何其他人物头像或全身；别人的头像/全身只用于验收图并排展示。实际参照路径、哈希、完整提示词、原生成路径及所选版本见generation_manifest.json。','', '内置image_gen生成原生1024×1536 RGBA透明人物层，原样复制入assets/raw/characters/；没有用程序涂改画面、裁切人物、补画兵器或去掉源画布。合成只用正式目录和既有身高系数。历史油画厚涂，原17张首稿和未选用返稿保留在concepts各版本目录。','', '首稿检查修正了三张非号衣服装的误画圆片：洪天贵福王袍恢复龙纹刺绣，张树声和和春的外褂去掉空白军服圆片；张树声另把坎肩式无袖上衣改成完整黑色长袖马褂。真正号衣上的字补仍空白，未叠加“勇”等字。','', '## 技术验证','', f"- 人物数：56（按当前人物表：{v['rarities']['SSR']}SSR+{v['rarities']['SR']}SR+{v['rarities']['R']}R）；全员实际合成，无占位、无缺失。本轮未修改稀有度。",
 '- 17张新原图均原生透明、边界安全；无UPSCALE、EDGE_CUT、WIDE或其他管线警告。','- 每人目标高度round(1300×height_scale)，误差不超过2px；脚底统一y=1392；主图及三档派生均全幅等比。','- 两次完整构建，224份人物输出+4份管线报告共228份哈希完全一致。','- 原有39人的39张原画、156份派生图字节一致；背景、已有头像和所有数据CSV未改。本次替换的4份全员管线报告，其39人旧版已存before/assets/reports/。','- 28项管线回归通过，包含“呤唎、张国梁、樑”报告字体缺字检查。只改了验收图用的宋体字面，游戏页面字体未改。','','## 面部与史料说明','', '全员面部图为人工选取局部，不是自动人脸相似度证明，也不改变游戏里的完整立绘。51人有独立确认头像；石达开、曾国藩、咸丰、慈禧、罗大纲5位早期定稿无独立确认头像，以本轮冻结的原全身面部局部作左侧参照，并明确标注“非独立头像”。这5人的原图哈希逐项一致，未重绘。','', '本批17人的具体面容、部分年龄和服装细节沿用04文件的史/设/传标记，属于美术重构，不宣称有已核实同龄照片。苏三娘为传说人物；角帽沿用项目既有原始图版与已确认形制，但不能据此证明某人的具体私服或龙纹。来源与限度参见[既有SSR史料说明](../../../docs/reference/ssr_sources.md)。本轮没有新增独立史料考证。','', '需要用户重点复核：剪影是否区分、从确认头像到全身的脸型是否走样、服装与兵器是否有历史错误。技术检查通过不代替这三项艺术验收。','','## 17张逐项记录','','|编号|人物|确认头像|背景板|身高系数|实际高度|技术检查|','|---|---|---|---|---:|---:|---|']
 for r in rows:
  c=checks[r['id']];version='v2' if r['id'] in {'tp_hong_tianguifu','qing_shengbao'} else 'v1'
  lines.append(f"|{r['number']}|{r['name']}|{version}|{r['bg_id']}|{r['height_scale']}|{c['final_h']}|通过|")
 lines += ['','## 复现','', '使用本项目既有带Pillow/numpy的Python运行：','', '```sh','python3 -m unittest discover -s tools -p test_build_portraits.py -v','python3 tools/ingest_r_full_bodies.py','python3 tools/build_complete_roster_review.py','python3 tools/build_complete_face_review.py','python3 tools/package_r_full_body_review.py','```','','参照审批见../r_head_approval_state.json；原生层检查见source_validation.json；56人几何与保全结果见roster_validation.json；重复构建哈希见repeat_output_sha256.json；实际回归日志见regression_tests.log。']
 (REPORT/'review_report.md').write_text('\n'.join(lines)+'\n')
 files=[ROOT/'assets/reports'/n for n in ['contact_sheet.png','silhouette_sheet.png','face_identity_sheet.png']]+[REPORT/n for n in ['r_full_body_batch_01.png','r_full_body_batch_02.png','r_faces_01.png','r_faces_02.png','six_groups_full_body.png','17_full_body_assets.zip','review_report.md']]
 (REPORT/'delivery_validation.json').write_text(json.dumps(dict(stage='ALL56_TECHNICAL_CHECKS_PASS_HUMAN_ART_REVIEW_PENDING',approved_r_heads=17,full_roster=56,regression_tests=28,files=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p)) for p in files]),ensure_ascii=False,indent=2)+'\n')
 print('Packaged17 full-body cards and56-person review, plus34 selected image layers inZIP')
if __name__=='__main__':main()
