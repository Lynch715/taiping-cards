#!/usr/bin/env python3
"""Preserve R v1, package only R01/R15 revisions and record the15 approvals."""
import hashlib,json,shutil
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];REPORT=ROOT/'assets/reports/r_head_review_v2';DEST=ROOT/'assets/concepts/r_heads_v2'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def font(size):return ImageFont.truetype('/System/Library/Fonts/Supplemental/Songti.ttc',size,index=1)
def main():
 results=json.loads((REPORT/'generation_results.json').read_text())['results'];assert {r['id'] for r in results}=={'tp_hong_tianguifu','qing_shengbao'}
 DEST.mkdir(parents=True,exist_ok=True);state_path=ROOT/'assets/reports/r_head_approval_state.json';state=json.loads(state_path.read_text());ix={r['id']:r for r in state['heads']};manifest=[]
 for r in results:
  dest=DEST/f"{r['id']}.png";src=Path(r['source_path'])
  if dest.exists():assert sha(dest)==sha(src)
  else:shutil.copy2(src,dest)
  accepted=ix[r['id']]['approval_status']=='USER_APPROVED' and ix[r['id']]['project_path']==str(dest.relative_to(ROOT))
  row={**r,'project_path':str(dest.relative_to(ROOT)),'sha256':sha(dest),'approval_status':'USER_APPROVED' if accepted else 'PENDING_REVISED_HEAD_REVIEW','reference_sha256':[sha(ROOT/p) for p in r['refs']]};manifest.append(row)
  if not accepted:ix[r['id']].update(candidate_path=row['project_path'],candidate_sha256=row['sha256'],approval_status='PENDING_REVISED_HEAD_REVIEW')
 pending=[r['id'] for r in manifest if r['approval_status']!='USER_APPROVED'];state['stage']='15_APPROVED_FOR_FULL_BODY_2_REVISED_HEADS_PENDING' if pending else 'ALL17_R_HEADS_USER_APPROVED';state['pending_revision_ids']=pending;state_path.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
 status='待确认' if pending else '已确认'
 im=Image.new('RGB',(1128,1464),'#EDE3CC');d=ImageDraw.Draw(im);d.text((24,16),f'R01 / R15 头像修订对比 · v2{status}',font=font(34),fill='#252720');d.text((24,68),'左：v1原稿；右：v2修订。其余15张头像已确认，正在出全身。',font=font(23),fill='#55594F')
 for i,r in enumerate(manifest):
  y=116+i*664
  for j,p in enumerate([r['refs'][0],r['project_path']]):
   with Image.open(ROOT/p) as src:im.paste(src.convert('RGB').resize((530,530),Image.Resampling.LANCZOS),(24+j*550,y))
  name=ix[r['id']]['name'];d.text((24,y+540),f"{r['number']} {name} · v1",font=font(27),fill='#55594F');d.text((574,y+540),f"{r['number']} {name} · v2{status}",font=font(27),fill='#252720')
  note='15岁、稚气惶恐；眉毛加粗，脸型减圆润，保留少年感。' if i==0 else '铁盔改顶戴花翎官帽；保留上扬胡子、昂首神态。'
  d.text((24,y+588),note,font=font(24),fill='#55594F')
 im.save(REPORT/'revision_comparison.png')
 (REPORT/'generation_manifest.json').write_text(json.dumps(dict(tool='built-in image_gen',stage='2_REVISIONS_PENDING_USER_REVIEW' if pending else 'BOTH_REVISED_HEADS_USER_APPROVED',results=manifest),ensure_ascii=False,indent=2)+'\n')
 (REPORT/'review_report.md').write_text(('# R01 / R15 头像修订v2\n\n两张均待复核；未将它们作为已确认头像出全身。其余15张沿用已确认v1，按本人头像+两块无脸风格局部+本人背景板制作全身。\n\n- R01：15岁少年，眉毛加粗，脸型少一点圆润柔和，保留稚气和惶恐，无成年胡须。\n- R15：铁盔换为顶戴花翎官帽，保留上扬胡子和昂首神态。\n\n两个编辑各只附本人v1头像；内置image_gen生成，未用程序绘改人物。v1原图保留，v2保存在assets/concepts/r_heads_v2/。提示词、参照及哈希见generation_manifest.json。\n').replace('两张均待复核；未将它们作为已确认头像出全身。','两张v2已获用户确认，可使用修订版出全身。' if not pending else '两张均待复核；未将它们作为已确认头像出全身。'))
 print('Packaged2 revised heads;15 confirmed originals retained')
if __name__=='__main__':main()
