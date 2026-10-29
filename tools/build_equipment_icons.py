#!/usr/bin/env python3
"""Build 512px alpha masters, uncropped 128/64 WebP and one 64px atlas."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
SLOTS=['兵刃','甲胄','坐骑','兵书']
SETS=['圣兵','勇营','洋械','铁骑','江防']
ATLAS_CELL=68

def rows(root):
    records=list(csv.DictReader((root/'data/equipment_icons.csv').open(encoding='utf-8-sig')))
    if len(records)!=20 or {(r['set'],r['slot']) for r in records}!={(s,k) for s in SETS for k in SLOTS}:
        raise ValueError('Expected exactly 5 sets x 4 slots')
    if len({r['icon_id'] for r in records})!=20:raise ValueError('Duplicate icon id')
    return records

def normalize(image):
    image=image.convert('RGBA')
    alpha=image.getchannel('A');box=alpha.point(lambda a:255 if a>16 else 0).getbbox()
    if not box or alpha.getextrema()[0]!=0:raise ValueError('Source must contain a transparent background and a visible object')
    if min(box[0],box[1],image.width-box[2],image.height-box[3])<4:raise ValueError('EDGE_CUT: source object touches canvas edge')
    visible_source=alpha.getbbox()
    scale=min(410/(box[2]-box[0]),410/(box[3]-box[1]),510/(visible_source[2]-visible_source[0]),510/(visible_source[3]-visible_source[1]))
    if scale>1.25:raise ValueError('UPSCALE: source object too small')
    # Resize the entire source canvas; never crop or remove its native alpha.
    scaled=image.resize((max(1,math.floor(image.width*scale)),max(1,math.floor(image.height*scale))),Image.Resampling.LANCZOS)
    b=scaled.getchannel('A').point(lambda a:255 if a>16 else 0).getbbox()
    x=round(256-(b[0]+b[2])/2);y=round(256-(b[1]+b[3])/2)
    visible=scaled.getchannel('A').getbbox()
    # Keep faint native edge pixels too; clamp translation instead of cropping alpha.
    x=max(1-visible[0],min(x,511-visible[2]));y=max(1-visible[1],min(y,511-visible[3]))
    if min(visible[0]+x,visible[1]+y,512-visible[2]-x,512-visible[3]-y)<0:raise ValueError('Visible source would be cropped')
    master=Image.new('RGBA',(512,512));master.alpha_composite(scaled,(x,y))
    return master,box,scale

def build(root,report_dir):
    records=rows(root);out=root/'assets/equipment';public=root/'app/public/assets/equipment'
    report_dir.mkdir(parents=True,exist_ok=True);out.mkdir(parents=True,exist_ok=True)
    (public/'128').mkdir(parents=True,exist_ok=True)
    atlas=Image.new('RGBA',(ATLAS_CELL*4,ATLAS_CELL*5));results=[];metadata={}
    equipment=list(csv.DictReader((root/'data/equipment.csv').open(encoding='utf-8-sig')))
    for row in records:
        ident=row['icon_id'];source=root/'assets/raw/equipment/generated'/f'{ident}.png'
        with Image.open(source) as im:
            src_size=im.size;master,box,scale=normalize(im)
        master_path=root/'assets/raw/equipment'/f'{ident}.png';master.save(master_path,compress_level=9)
        folder=out/ident;folder.mkdir(parents=True,exist_ok=True)
        for size in (128,64):
            image=master.resize((size,size),Image.Resampling.LANCZOS)
            image.save(folder/f'{size}.webp',quality=85,method=6,exact=True)
            if size==128:(public/'128'/f'{ident}.webp').write_bytes((folder/'128.webp').read_bytes())
            else:
                x=SLOTS.index(row['slot'])*ATLAS_CELL+2;y=SETS.index(row['set'])*ATLAS_CELL+2
                atlas.alpha_composite(image,(x,y))
        metadata[ident]={'set':row['set'],'slot':row['slot'],'x':x,'y':y}
        name=next(r['name'] for r in equipment if r['set']==row['set'] and r['slot']==row['slot'])
        results.append(dict(id=ident,name=name,set=row['set'],slot=row['slot'],src_w=src_size[0],src_h=src_size[1],bbox=list(box),scale=scale,master_size=[512,512],warnings='',webp64_bytes=(folder/'64.webp').stat().st_size,webp128_bytes=(folder/'128.webp').stat().st_size,master_sha256=hashlib.sha256(master_path.read_bytes()).hexdigest()))
    atlas.save(out/'sprite-64.png',compress_level=9)
    atlas.save(out/'sprite-64.webp',quality=85,method=6,exact=True)
    (public/'sprite-64.webp').write_bytes((out/'sprite-64.webp').read_bytes())
    data={'sprite':'assets/equipment/sprite-64.webp','width':atlas.width,'height':atlas.height,'cell':ATLAS_CELL,'icons':metadata}
    (root/'app/src/platform/equipment-icons.generated.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    (report_dir/'equipment_pipeline.json').write_text(json.dumps({'icons':results,'atlas':data,'sprite_bytes':(out/'sprite-64.webp').stat().st_size,'total128_bytes':sum(r['webp128_bytes'] for r in results),'quality':85},ensure_ascii=False,indent=2)+'\n')
    with (report_dir/'pipeline_report.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(results[0]));w.writeheader();w.writerows(results)
    sheet=Image.new('RGB',(1000,650),'#ede3cc');draw=ImageDraw.Draw(sheet)
    font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Songti.ttc',18,index=1)
    title=ImageFont.truetype('/System/Library/Fonts/Supplemental/Songti.ttc',27,index=1)
    draw.text((24,16),'兵装图标 · 64px实际像素对照（不放大）',font=title,fill='#242019')
    for slot_index,slot in enumerate(SLOTS):draw.text((180+slot_index*205,65),slot,font=font,fill='#245249')
    decoded_atlas=Image.open(out/'sprite-64.webp').convert('RGBA')
    for set_index,set_name in enumerate(SETS):
        top=105+set_index*105;draw.text((24,top+22),set_name,font=font,fill='#242019')
        for slot_index,slot in enumerate(SLOTS):
            row=next(r for r in results if r['set']==set_name and r['slot']==slot)
            cell=metadata[row['id']]
            # Extract the actual decoded atlas cell, not a separately encoded thumbnail.
            icon=decoded_atlas.crop((cell['x'],cell['y'],cell['x']+64,cell['y']+64));left=180+slot_index*205
            draw.rectangle((left-2,top-2,left+65,top+65),outline='#a37c42',width=2)
            sheet.paste(icon,(left,top),icon);draw.text((left-15,top+68),row['name'],font=font,fill='#242019')
    sheet.save(report_dir/'contact_sheet_64_actual.png',compress_level=9)
    return results,data

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report-dir',type=Path,default=ROOT/'assets/reports/equipment_batch_c_20261029');a=p.parse_args()
    results,data=build(ROOT,a.report_dir);print(json.dumps({'icons':len(results),'sprite_size':[data['width'],data['height']],'sprite_bytes':(ROOT/'assets/equipment/sprite-64.webp').stat().st_size}))
