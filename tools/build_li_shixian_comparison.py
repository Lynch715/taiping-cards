#!/usr/bin/env python3
"""Review-only whole cards, native thumbnails, silhouettes and face details."""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

import build_portraits as pipeline

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "assets/reports/li_shixian_revision_v2"
FONT = "/System/Library/Fonts/Supplemental/Songti.ttc"


def main():
    ids = ["tp_li_shixian", "tp_chen_yucheng"]
    records = pipeline.read_records(ROOT, ids)
    results = [pipeline.process(ROOT, r, tolerance=12.0) for r in records]
    assert all(not r.warnings for r in results)
    sheet = Image.new("RGB", (1296, 916), "#EDE3CC")
    draw = ImageDraw.Draw(sheet)

    def text(x, y, content, size=22, color="#252720"):
        draw.text((x, y), content, font=ImageFont.truetype(FONT, size), fill=color)

    def preview(path, size, box=None):
        with Image.open(path) as image:
            image = image.convert("RGBA")
            if box:
                image = image.crop(box)
            image = ImageOps.contain(image, size, Image.Resampling.LANCZOS)
        tile = Image.new("RGBA", size, "#D8D5CD")
        tile.alpha_composite(image, ((size[0]-image.width)//2,(size[1]-image.height)//2))
        return tile.convert("RGB")

    text(24,14,"李世贤修订 · 与陈玉成同图对比",34)
    text(24,64,"完整400×600卡面、96×144原生缩略图与同倍率剪影。陈玉成素材未改。",20,"#55594F")
    for i,ident in enumerate(ids):
        x = 24+i*424
        sheet.paste(preview(ROOT/"assets/characters"/ident/"card.webp",(400,600)),(x,108))
        text(x,720,records[i]["name"],28)
        note = "新稿：深褐战袍＋皮甲背心" if i==0 else "保留：红短打＋红头巾"
        pose = "长柄大刀拄地 · 正面稳立" if i==0 else "斜持长矛 · 重心前压冲锋"
        text(x,766,note,23)
        text(x,805,pose,23)
    for i,result in enumerate(results):
        x,y=872+i*200,144
        mask=result.silhouette.resize((160,240),Image.Resampling.LANCZOS)
        sheet.paste((0,0,0),(x,y,x+160,y+240),mask)
        draw.line((x,y+round(1392/1536*240),x+159,y+round(1392/1536*240)),fill="#DA302B")
        text(x,y+250,records[i]["name"],21)
        # Display the actual output thumbnail pixel-for-pixel at 96x144.
        with Image.open(ROOT/"assets/characters"/ids[i]/"thumb.webp") as thumb:
            assert thumb.size==(96,144)
            sheet.paste(thumb.convert("RGB"),(x+32,458))
    text(872,108,"人物剪影（无背景、投影、特效）",20)
    text(872,615,"96×144原生小卡，同尺寸比较",20)
    text(872,666,"李世贤：确认头像／新全身头部",20)
    sheet.paste(preview(ROOT/"assets/concepts/sr_heads_v1/tp_li_shixian.png",(160,160)),(872,704))
    sheet.paste(preview(ROOT/"assets/raw/characters/tp_li_shixian.png",(160,160),(350,90,760,500)),(1072,704))
    path=REPORT/"li_shixian_vs_chen_yucheng.png"
    sheet.save(path,compress_level=9)
    print(path)


if __name__ == "__main__":
    main()
