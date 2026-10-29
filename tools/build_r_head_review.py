#!/usr/bin/env python3
"""Package §8's 17 pending heads, 9/8 grids and all six comparison groups."""
import csv
import hashlib
import json
import shutil
import zipfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from build_sr_head_review import lines, image_tile
ROOT=Path(__file__).resolve().parents[1]
REPORT=ROOT/'assets/reports/r_head_review_v1'
DEST=ROOT/'assets/concepts/r_heads_v1'

def font(size):
    # Songti face0 omits 唎; face1 contains the complete names in this batch.
    return ImageFont.truetype('/System/Library/Fonts/Supplemental/Songti.ttc',size,index=1)

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def label(r):
    prefix='设' if '设'+str(r['age']) in r.get('basis','') else ''
    return f"{r['number']} {r['name']} · {prefix}{r['age']}岁"+(' · 传' if r['id']=='tp_su_sanniang' else '')

def grid(rows,index):
    side,gap,margin,head,lab=400,20,24,114,135
    im=Image.new('RGB',(1288,head+3*(side+lab)+2*gap+margin),'#EDE3CC');d=ImageDraw.Draw(im)
    d.text((24,16),f'普通卡头像确认 · 第{index}批 / 共2批（{len(rows)}人）',font=font(34),fill='#252720')
    d.text((24,66),'历史油画厚涂｜只定脸，待确认后出全身｜面容为美术重构，设定年龄与传说身份见报告',font=font(20),fill='#55594F')
    for i,r in enumerate(rows):
        x,y=margin+i%3*(side+gap),head+i//3*(side+lab+gap)
        image_tile(im,ROOT/r['project_path'],(x,y),side)
        d.text((x,y+side+8),label(r),font=font(25),fill='#252720')
        for j,t in enumerate(lines(d,r['traits'],font(19),side)):
            d.text((x,y+side+45+j*24),t,font=font(19),fill='#55594F')
        d.text((x,y+side+108),r['id'],font=font(15),fill='#73766D')
    if len(rows)==8:
        x,y=margin+2*(side+gap),head+2*(side+lab+gap)
        d.rectangle((x,y,x+side,y+side),outline='#B2A68E',width=2)
        d.text((x+80,y+180),'本批共8人',font=font(30),fill='#73766D')
    path=REPORT/f'batch_{index:02d}_nine_grid.png';im.save(path);return str(path.relative_to(ROOT))

def groups(rows):
    extras=[dict(id='tp_yang_xiuqing',number='SSR',name='杨秀清',age=32,basis='32岁',traits='已确认 heads_v4：黄色风帽、锐利自信',project_path='assets/concepts/heads_v4/tp_yang_xiuqing.png'),dict(id='tp_hong_xuanjiao',number='SR',name='洪宣娇',age=25,basis='设25',traits='已确认SR：女营双刀；仅作并排参照',project_path='assets/concepts/sr_heads_v1/tp_hong_xuanjiao.png')]
    ix={r['id']:r for r in rows+extras}
    gs=[('01 太平普通将领','体面稳重 / 粗壮矿工 / 中年浓须 / 年轻风尘',['tp_hu_yihuang','tp_qin_rigang','tp_huang_wenjin','tp_wang_haiyang']),('02 杨氏区分','头巾戎装 / 黄色风帽；SSR采用已确认v4',['tp_yang_fuqing','tp_yang_xiuqing']),('03 江南大营','老将白须绿营 / 中年黑须补服行褂',['qing_xiang_rong','qing_he_chun']),('04 淮军','清瘦文官 / 精干骑将',['qing_zhang_shusheng','qing_guo_songlin']),('05 外籍','英国青年便装 / 美国青年敞领军装',['tp_lindley','qing_burgevine']),('06 女将','苏三娘骑装长枪 / 洪宣娇双刀（全身阶段执行）',['tp_su_sanniang','tp_hong_xuanjiao'])]
    side,gap,margin,header,gh,lh=260,14,28,118,78,116
    gw=4*side+3*gap;group_h=gh+side+lh;outgap=32
    im=Image.new('RGB',(2*margin+2*gw+outgap,header+3*group_h+2*outgap+margin),'#EDE3CC');d=ImageDraw.Draw(im)
    d.text((margin,16),'第8.1节 · 6组人物同图对比',font=font(36),fill='#252720')
    d.text((margin,70),'杨秀清SSR（heads_v4）与洪宣娇SR采用已确认头像；只在本图并排展示，未作为其他人物的生成参照。',font=font(23),fill='#55594F')
    for i,(title,note,ids) in enumerate(gs):
        gx=margin+i%2*(gw+outgap);gy=header+i//2*(group_h+outgap)
        d.text((gx,gy),title,font=font(29),fill='#252720');d.text((gx,gy+39),note,font=font(21),fill='#55594F')
        for j,id in enumerate(ids):
            r=ix[id];x=gx+j*(side+gap);y=gy+gh
            image_tile(im,ROOT/r['project_path'],(x,y),side)
            d.text((x,y+side+8),label(r),font=font(20),fill='#252720')
            for k,t in enumerate(lines(d,r['traits'],font(17),side)):
                d.text((x,y+side+39+k*23),t,font=font(17),fill='#41643D' if r in extras else '#55594F')
    path=REPORT/'six_groups_comparison.png';im.save(path)
    return dict(path=str(path.relative_to(ROOT)),groups=gs,approved_layout_references=[{**r,'sha256':sha(ROOT/r['project_path'])} for r in extras])

def main():
    plan=json.loads((REPORT/'generation_plan.json').read_text());result=json.loads((REPORT/'generation_results.json').read_text())
    sources={r['id']:r for r in result['results']};sources.update({r['id']:r for r in json.loads((REPORT/'cleanup_results.json').read_text())})
    with (ROOT/'data/characters.csv').open(encoding='utf-8-sig') as f:expected={r['id'] for r in csv.DictReader(f) if r['rarity_draft']=='R'}
    assert len(expected)==17 and set(sources)==expected
    DEST.mkdir(parents=True,exist_ok=True);rows=[]
    for j in plan['subjects']:
        r={**j,**sources[j['id']]};src=Path(r['source_path']);dest=DEST/(r['id']+'.png')
        if dest.exists() and sha(dest)!=sha(src):raise ValueError('Version existing image before replacing: '+str(dest))
        if not dest.exists():shutil.copy2(src,dest)
        if r.get('first_source_path'):
            first=REPORT/'signature_cleanup_before'/f"{r['number']}_{r['id']}.png"
            first.parent.mkdir(parents=True,exist_ok=True)
            if not first.exists():shutil.copy2(r['first_source_path'],first)
            r['cleanup_reference']=dict(path=str(first.relative_to(ROOT)),sha256=sha(first),source_path=r['first_source_path'])
        with Image.open(dest) as im:assert im.width==im.height;r['dimensions']=list(im.size)
        assert not r['refs']
        r.update(project_path=str(dest.relative_to(ROOT)),sha256=sha(dest),approval_status='PENDING_USER_REVIEW')
        rows.append(r)
    protected=json.loads((REPORT/'protected_art_sha256.json').read_text())
    # Protection file is a path->hash map, or the same map inside `files`.
    protected=protected.get('files',protected)
    assert all(sha(ROOT/p)==h for p,h in protected.items()),'Existing approved art changed'
    f=font(40)
    names=''.join(r['name'] for r in rows)+'杨秀清洪宣娇张国梁樑'
    missing=[c for c in set(names) if not f.getmask(c).getbbox() or bytes(f.getmask(c))==bytes(f.getmask('\uffff'))]
    assert not missing,missing
    manifest=dict(stage='17_HEADS_PENDING_USER_APPROVAL',results=rows,nine_grids=[grid(rows[:9],1),grid(rows[9:],2)],six_group_comparison=groups(rows),protected_files_verified=len(protected),font_audit=dict(font='Songti.ttc face1',missing_name_glyphs=missing))
    (REPORT/'generation_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    with zipfile.ZipFile(REPORT/'17_heads_for_review.zip','w',zipfile.ZIP_DEFLATED) as z:
        for r in rows:z.write(ROOT/r['project_path'],f"{r['number']}_{r['name']}_{r['id']}.png")
    text=['# 17张普通卡头像验收（v1）','','状态：全部待用户确认；没有生成这17人的全身，没有启动56人正式合成管线。','',f'9/8两批九宫格；第8.1节6组全部在同一张对比图。既有{len(protected)}个美术文件SHA-256逐项一致。','','## 素材与身份说明','','统一历史油画厚涂，灰底头肩像；未生成胸前文字。所有具体面容均为美术重构，不宣称有已核实历史照片。年龄、史/设/传标记沿用04文件，不视为额外史料考证。杨辅清与杨秀清的族弟关系按文件执行，未独立考证。','','|编号|人物|年龄/依据标记|头像区分点|','|---|---|---|---|']
    text += [f"|{r['number']}|{r['name']}|{r['age']}岁；{r['basis']}|{r['traits']}|" for r in rows]
    text += ['','## 生成与复现','','17人首稿均为纯文字生成，无任何其他人物图像参照。林启荣、黄文金、汪海洋首稿有边角伪签名，仅用各自首稿作参照清除；首稿路径、清除提示词、所选版本记录于manifest。未用程序涂改人物图。','', '杨秀清采用heads_v4；洪宣娇采用已确认sr_heads_v1。两张仅参与验收图排版，没有参与新头像生成。','','原始提示词见generation_plan.json，实际选择与哈希见generation_manifest.json。运行 `python3 tools/build_r_head_review.py` 可重建验收图及压缩包。','','## 确认后的阶段','','逐人只附自己的已确认头像、无脸风格局部和本人的背景板生成全身；服装道具姿态逐人按第8.2节，号衣字补空白。全部完成后再按身高系数跑56人管线，交对照、阵营两行剪影和面部对照。']
    (REPORT/'review_report.md').write_text('\n'.join(text)+'\n');print('Packaged17 heads; protected',len(protected))
if __name__=='__main__':main()
