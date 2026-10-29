#!/usr/bin/env python3
"""Human-facing SR face details and six full-card comparison groups."""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "assets/reports/sr_full_body_v1"
FONT = "/System/Library/Fonts/Supplemental/Songti.ttc"
# Manually chosen QA windows, never used by the production image pipeline.
BODY_WINDOWS = {
    "tp_xiao_chaogui": (450, 40, 860, 450),
    "tp_feng_yunshan": (330, 10, 740, 420),
    "tp_wei_changhui": (355, 10, 765, 420),
    "tp_hong_rengan": (315, 0, 725, 410),
    "tp_li_shixian": (350, 90, 760, 500),
    "tp_lin_fengxiang": (300, 120, 710, 530),
    "tp_li_kaifang": (310, 0, 720, 410),
    "tp_tan_shaoguang": (300, 0, 710, 410),
    "tp_lai_wenguang": (325, 20, 735, 430),
    "tp_hong_xuanjiao": (310, 50, 720, 460),
    "qing_zeng_guoquan": (325, 0, 735, 410),
    "qing_luo_zenan": (325, 0, 735, 410),
    "qing_li_xubin": (290, 90, 700, 500),
    "qing_taqibu": (325, 0, 735, 410),
    "qing_bao_chao": (370, 70, 780, 480),
    "qing_duolonga": (290, 0, 700, 410),
    "qing_jiang_zhongyuan": (280, 0, 690, 410),
    "qing_yang_zaifu": (280, 10, 690, 420),
    "qing_cheng_xueqi": (280, 0, 690, 410),
    "qing_liu_mingchuan": (300, 50, 710, 460),
    "qing_zhang_guoliang": (325, 0, 735, 410),
    "qing_ward": (310, 0, 720, 410),
    "qing_gordon": (300, 0, 710, 410),
    "qing_prince_gong": (325, 0, 735, 410),
    "qing_sushun": (325, 0, 735, 410),
}


def font(size):
    return ImageFont.truetype(FONT, size)


def tile(path, box, size):
    with Image.open(path) as im:
        preview = im.convert("RGBA")
        if box:
            preview = preview.crop(box)
        preview = ImageOps.contain(preview, size, Image.Resampling.LANCZOS)
    image = Image.new("RGBA", size, "#D8D5CD")
    image.alpha_composite(preview, ((size[0]-preview.width)//2, (size[1]-preview.height)//2))
    return image.convert("RGB")


def main():
    manifest = json.loads((REPORT / "generation_manifest.json").read_text())
    rows = sorted(manifest["results"], key=lambda x: x["number"])
    assert len(rows) == 25
    for batch in range(3):
        selected = rows[batch*9:(batch+1)*9]
        side, gap, margin, head, cell_h = 250, 14, 24, 112, 324
        cell_w = side*2 + gap
        sheet = Image.new("RGB", (2*margin+cell_w*3+gap*2, head+cell_h*3+gap*2+margin), "#EDE3CC")
        draw = ImageDraw.Draw(sheet)
        draw.text((margin,12),f"SR头像与全身头部 · 第{batch+1}批",font=font(32),fill="#252720")
        draw.text((margin,62),"每组左：已确认头像全幅；右：全身原图头部局部。仅验收图放大，不裁游戏立绘。",font=font(20),fill="#55594F")
        for i,row in enumerate(selected):
            x,y = margin+i%3*(cell_w+gap), head+i//3*(cell_h+gap)
            sheet.paste(tile(ROOT/row["approved_head"],None,(side,side)),(x,y))
            sheet.paste(tile(ROOT/row["raw_path"],BODY_WINDOWS[row["id"]],(side,side)),(x+side+gap,y))
            draw.text((x,y+side+8),f"{row['number']} {row['name']}",font=font(25),fill="#252720")
            draw.text((x+side+gap,y+side+8),"全身头部局部",font=font(20),fill="#55594F")
        sheet.save(REPORT/f"face_identity_sr_{batch+1:02d}.png",compress_level=9)
    groups = [
        ("01 三个书生",["tp_feng_yunshan","tp_hong_rengan","qing_luo_zenan"]),
        ("02 北伐双将",["tp_lin_fengxiang","tp_li_kaifang"]),
        ("03 湘军水师",["qing_peng_yulin","qing_yang_zaifu"]),
        ("04 满蒙骑将",["qing_senggelinqin","qing_duolonga","qing_taqibu"]),
        ("05 洋枪队",["qing_ward","qing_gordon"]),
        ("06 政令卡",["qing_prince_gong","qing_sushun"]),
    ]
    import csv
    names={r["id"]:r["name"] for r in csv.DictReader((ROOT/"data/characters.csv").open())}
    side_w,side_h,gap,margin,header=220,330,16,24,90
    group_w,group_h=3*side_w+2*gap,420
    sheet=Image.new("RGB",(2*margin+2*group_w+32,header+3*group_h+2*24+margin),"#EDE3CC")
    draw=ImageDraw.Draw(sheet)
    draw.text((margin,14),"第7.1节 · 六组全身卡面同图比较",font=font(32),fill="#252720")
    for i,(label,ids) in enumerate(groups):
        gx,gy=margin+i%2*(group_w+32),header+i//2*(group_h+24)
        draw.text((gx,gy),label,font=font(25),fill="#252720")
        for j,ident in enumerate(ids):
            x,y=gx+j*(side_w+gap),gy+44
            sheet.paste(tile(ROOT/"assets/characters"/ident/"full.png",None,(side_w,side_h)),(x,y))
            draw.text((x,y+side_h+7),names[ident],font=font(23),fill="#252720")
    sheet.save(REPORT/"six_groups_full_body.png",compress_level=9)
    (REPORT/"face_review_windows.json").write_text(json.dumps(BODY_WINDOWS,ensure_ascii=False,indent=2)+"\n")
    print("Saved3 SR identity sheets and all6 full-body comparison groups")


if __name__ == "__main__":
    main()
