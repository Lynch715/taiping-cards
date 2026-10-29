#!/usr/bin/env python3
"""Render human-review face details; never change production portrait pixels."""
from pathlib import Path
import json
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "assets/reports/full_body_distinct_v1"
# Manually selected QA windows, not face detection or automated identity proof.
# These crops are used ONLY in the review sheet, never in game assets.
WINDOWS = {
    "tp_hong_xiuquan": ((400, 400, 855, 1005), (424, 157, 610, 405)),
    "tp_yang_xiuqing": ((440, 220, 930, 875), (472, 109, 655, 352)),
    "tp_chen_yucheng": ((405, 240, 960, 980), (412, 196, 665, 532)),
    "tp_li_xiucheng": ((470, 260, 1025, 1000), (465, 75, 665, 341)),
    "qing_hu_linyi": ((410, 445, 825, 1000), (431, 145, 620, 395)),
    "qing_zuo_zongtang": ((320, 280, 1010, 1050), (382, 122, 584, 391)),
    "qing_peng_yulin": ((315, 195, 995, 1105), (425, 94, 620, 354)),
    "qing_li_hongzhang": ((440, 420, 920, 1060), (470, 139, 637, 361)),
    "qing_senggelinqin": ((400, 325, 895, 985), (440, 117, 638, 380)),
}


def main():
    state = json.loads((FOLDER / "approved_heads_snapshot.json").read_text())
    manifest = json.loads((FOLDER / "generation_manifest.json").read_text())
    bodies = {r["id"]: r for r in manifest["results"]}
    width, height, gap, margin, header, label = 310, 420, 16, 28, 116, 74
    cell_w, cell_h = width * 2 + gap, height + label
    sheet = Image.new("RGB", (2 * margin + 3 * cell_w + 2 * gap,
                              header + 3 * cell_h + 2 * gap + margin), "#EDE3CC")
    draw = ImageDraw.Draw(sheet)
    font_path = "/System/Library/Fonts/Supplemental/Songti.ttc"
    font = ImageFont.truetype(font_path, 26)
    small = ImageFont.truetype(font_path, 21)
    draw.text((margin, 14), "头像与全身面部对照 · 9 位 SSR", font=ImageFont.truetype(font_path, 36), fill="#252720")
    draw.text((margin, 67), "每组左：确认头像  /  右：全身原图局部。仅验收图使用局部放大；正式立绘全幅等比缩放。", font=small, fill="#55594F")
    for i, head in enumerate(state["heads"]):
        ident = head["id"]
        x = margin + i % 3 * (cell_w + gap)
        y = header + i // 3 * (cell_h + gap)
        paths = [ROOT / head["project_path"], ROOT / bodies[ident]["project_path"]]
        for side, (path, box) in enumerate(zip(paths, WINDOWS[ident])):
            with Image.open(path) as source:
                preview = source.convert("RGBA").crop(box)
                preview = ImageOps.contain(preview, (width, height), Image.Resampling.LANCZOS)
            tile = Image.new("RGBA", (width, height), "#D8D5CD")
            tile.alpha_composite(preview, dest=((width - preview.width) // 2, (height - preview.height) // 2))
            sheet.paste(tile.convert("RGB"), (x + side * (width + gap), y))
        draw.text((x, y + height + 8), f"{head['number']}  {head['name']} · {head['age']}岁", font=font, fill="#252720")
        draw.text((x + width + gap, y + height + 8), "全身原图局部", font=small, fill="#55594F")
    sheet.save(ROOT / "assets/reports/face_identity_sheet.png", compress_level=9)
    (FOLDER / "face_review_windows.json").write_text(json.dumps(WINDOWS, ensure_ascii=False, indent=2) + "\n")
    print("Face identity review sheet rendered; production assets unchanged.")


if __name__ == "__main__":
    main()
