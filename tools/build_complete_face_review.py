#!/usr/bin/env python3
"""56 face comparisons,17 new-card sheets, and §8.1 full-card groups; QA crops only."""
import csv,hashlib,json,math,shutil
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageOps
from build_distinct_review import WINDOWS as SSR_WINDOWS
from build_sr_full_body_details import BODY_WINDOWS as SR_WINDOWS
ROOT=Path(__file__).resolve().parents[1];REPORT=ROOT/'assets/reports/r_full_body_v1'
R_WINDOWS={
 'tp_hong_tianguifu':(340,25,710,445),'tp_yang_fuqing':(380,20,710,420),'tp_hu_yihuang':(340,10,710,410),
 'tp_qin_rigang':(320,20,710,440),'tp_zeng_tianyang':(340,95,720,510),'tp_lin_qirong':(350,25,710,445),
 'tp_huang_wenjin':(310,50,690,450),'tp_wang_haiyang':(400,20,790,450),'tp_lindley':(340,20,710,445),
 'tp_su_sanniang':(350,40,730,450),'qing_zhang_shusheng':(350,10,730,450),'qing_guo_songlin':(350,10,720,440),
 'qing_xiang_rong':(330,20,730,470),'qing_he_chun':(350,0,750,440),'qing_shengbao':(350,10,760,440),
 'qing_luo_bingzhang':(340,0,740,470),'qing_burgevine':(340,25,740,450),
}
FIVE_WINDOWS={'tp_shi_dakai':(380,20,720,420),'qing_zeng_guofan':(370,15,710,440),'qing_xianfeng':(350,10,710,420),'qing_cixi':(350,10,710,430),'tp_luo_dagang':(310,5,750,450)}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def font(n):return ImageFont.truetype('/System/Library/Fonts/Supplemental/Songti.ttc',n,index=1)
def tile(path,box,size):
 with Image.open(path) as im:
  a=im.convert('RGBA');a=a.crop(box) if box else a;a=ImageOps.contain(a,size,Image.Resampling.LANCZOS)
 out=Image.new('RGBA',size,'#D8D5CD');out.alpha_composite(a,((size[0]-a.width)//2,(size[1]-a.height)//2));return out.convert('RGB')
def face_sheet(rows,path,title):
 side,gap,margin,header,labels=250,14,24,112,100;cell_w=side*2+gap;cell_h=side+labels
 cols=min(3,len(rows));nr=math.ceil(len(rows)/cols);im=Image.new('RGB',(2*margin+cols*cell_w+(cols-1)*gap,header+nr*cell_h+(nr-1)*gap+margin),'#EDE3CC');d=ImageDraw.Draw(im)
 d.text((margin,12),title,font=font(34),fill='#252720');d.text((margin,61),'每组左：确认头像（5位无独立头像者用原定稿局部）；右：全身原图局部。只作人工验收，游戏立绘不裁切。',font=font(19),fill='#55594F')
 for i,r in enumerate(rows):
  x=margin+i%cols*(cell_w+gap);y=header+i//cols*(cell_h+gap)
  im.paste(tile(ROOT/r['head'],r['head_box'],(side,side)),(x,y));im.paste(tile(ROOT/r['body'],r['body_box'],(side,side)),(x+side+gap,y))
  d.text((x,y+side+7),f"{r['number']} {r['name']}",font=font(24),fill='#252720');d.text((x+side+gap,y+side+7),'全身面部',font=font(22),fill='#55594F')
  d.text((x,y+side+40),'原定稿局部（非独立头像）' if r['fallback'] else '已确认头像',font=font(18),fill='#55594F');d.text((x,y+side+70),r['id'],font=ImageFont.load_default(14),fill='#73766D')
 im.save(path,compress_level=9)
def main():
 records=list(csv.DictReader((ROOT/'data/characters.csv').open(encoding='utf-8-sig')));assert len(records)==56
 heads={}
 for r in json.loads((ROOT/'assets/reports/full_body_distinct_v1/generation_manifest.json').read_text())['results']:
  refs=r.get('references',r.get('refs',[]));head=next(p for p in refs if p.startswith('assets/concepts/heads_'));heads[r['id']]=dict(head=head,head_box=SSR_WINDOWS[r['id']][0],body_box=SSR_WINDOWS[r['id']][1],number='SSR')
 for r in json.loads((ROOT/'assets/reports/sr_full_body_v1/generation_manifest.json').read_text())['results']:
  heads[r['id']]=dict(head=r['approved_head'],head_box=None,body_box=SR_WINDOWS[r['id']],number=r['number'])
 for r in json.loads((REPORT/'generation_manifest.json').read_text())['results']:
  heads[r['id']]=dict(head=r['approved_head'],head_box=None,body_box=R_WINDOWS[r['id']],number=r['number'])
 rows=[]
 for r in records:
  ident=r['id'];fallback=ident not in heads
  if fallback:
   assert ident in FIVE_WINDOWS;dest=REPORT/'before/assets/raw/characters'/f'{ident}.png';dest.parent.mkdir(parents=True,exist_ok=True)
   if not dest.exists():shutil.copy2(ROOT/f'assets/raw/characters/{ident}.png',dest)
   assert sha(dest)==sha(ROOT/f'assets/raw/characters/{ident}.png')
   h=dict(head=str(dest.relative_to(ROOT)),head_box=FIVE_WINDOWS[ident],body_box=FIVE_WINDOWS[ident],number=r['rarity_draft'])
  else:h=heads[ident]
  rows.append({**h,'id':ident,'name':r['name'],'body':f'assets/raw/characters/{ident}.png','fallback':fallback,'rarity':r['rarity_draft']})
 assert sum(r['fallback'] for r in rows)==5
 face_sheet(rows,ROOT/'assets/reports/face_identity_sheet.png','全员面部对照 · 56人（51张确认头像 + 5张原定稿局部）')
 pages=[]
 for i in range(0,56,9):
  path=REPORT/f'faces_all_{i//9+1:02d}.png';face_sheet(rows[i:i+9],path,f'全员面部对照 · 第{i//9+1}批');pages.append(str(path.relative_to(ROOT)))
 r_rows=sorted([r for r in rows if r['rarity']=='R'],key=lambda r:r['number'])
 for i in [0,9]:face_sheet(r_rows[i:i+9],REPORT/f'r_faces_{i//9+1:02d}.png',f'本批17人面部对照 · 第{i//9+1}批')
 groups=[('01 太平普通将领',['tp_hu_yihuang','tp_qin_rigang','tp_huang_wenjin','tp_wang_haiyang']),('02 杨氏',['tp_yang_fuqing','tp_yang_xiuqing']),('03 江南大营',['qing_xiang_rong','qing_he_chun']),('04 淮军',['qing_zhang_shusheng','qing_guo_songlin']),('05 外籍',['tp_lindley','qing_burgevine']),('06 女将',['tp_su_sanniang','tp_hong_xuanjiao'])]
 side_w,side_h,gap,margin,header,gh,lh=250,375,14,28,110,56,88;gw=4*side_w+3*gap;gheight=gh+side_h+lh;ogap=28
 im=Image.new('RGB',(2*margin+gw*2+ogap,header+gheight*3+ogap*2+margin),'#EDE3CC');d=ImageDraw.Draw(im);d.text((margin,14),'第8.1节 · 6组完整卡面同图对比',font=font(34),fill='#252720');d.text((margin,66),'全部为完整卡面等比缩小；杨秀清、洪宣娇采用既有定稿，17张新全身仍待人工验收。',font=font(22),fill='#55594F');ix={r['id']:r for r in records}
 for i,(title,ids) in enumerate(groups):
  gx=margin+i%2*(gw+ogap);gy=header+i//2*(gheight+ogap);d.text((gx,gy),title,font=font(27),fill='#252720')
  for j,id in enumerate(ids):
   x,y=gx+j*(side_w+gap),gy+gh;im.paste(tile(ROOT/f'assets/characters/{id}/full.png',None,(side_w,side_h)),(x,y));d.text((x,y+side_h+8),ix[id]['name'],font=font(23),fill='#252720');d.text((x,y+side_h+43),id,font=ImageFont.load_default(14),fill='#73766D')
 im.save(REPORT/'six_groups_full_body.png',compress_level=9)
 (REPORT/'face_review_windows.json').write_text(json.dumps(dict(rows=rows,all_face_pages=pages,interpretation='Manual QA windows only; no automated identity proof; production images are never cropped'),ensure_ascii=False,indent=2)+'\n')
 print('Rendered56 face pairs,7 paginated sheets,2 R sheets and6 full-body groups')
if __name__=='__main__':main()
