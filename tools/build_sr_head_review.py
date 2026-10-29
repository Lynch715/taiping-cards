#!/usr/bin/env python3
"""Package 25 SR head concepts and one six-group identity comparison sheet."""
from pathlib import Path
import csv
import hashlib
import json
import shutil
import zipfile

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "assets/reports/sr_head_review_v1"
DEST = ROOT / "assets/concepts/sr_heads_v1"
FONT = "/System/Library/Fonts/Supplemental/Songti.ttc"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def font(size):
    return ImageFont.truetype(FONT, size)


def lines(draw, text, text_font, width):
    output, current = [], ""
    for char in text:
        if current and draw.textlength(current + char, font=text_font) > width:
            output.append(current)
            current = ""
        current += char
    if current:
        output.append(current)
    return output


def image_tile(sheet, path, xy, side):
    with Image.open(path) as image:
        assert image.width == image.height, path
        sheet.paste(image.convert("RGB").resize((side, side), Image.Resampling.LANCZOS), xy)


def age_label(row):
    if row["id"] in {"tp_lin_fengxiang", "tp_li_kaifang", "tp_hong_xuanjiao"}:
        return f"设{row['age']}岁"
    return f"{row['age']}岁"


def nine_grid(rows, index):
    side, gap, margin, header, labels = 400, 20, 24, 116, 132
    sheet = Image.new("RGB", (2 * margin + 3 * side + 2 * gap,
                              header + 3 * (side + labels) + 2 * gap + margin), "#EDE3CC")
    draw = ImageDraw.Draw(sheet)
    draw.text((margin, 16), f"SR头像确认 · 第{index}批 / 共3批", font=font(34), fill="#252720")
    draw.text((margin, 66), "历史油画厚涂｜本批只定脸，未出全身｜史料、年龄设定与传说身份详见报告", font=font(20), fill="#55594F")
    for i, row in enumerate(rows):
        x, y = margin + i % 3 * (side + gap), header + i // 3 * (side + labels + gap)
        image_tile(sheet, ROOT / row["project_path"], (x, y), side)
        age = age_label(row)
        if row["id"] == "tp_hong_xuanjiao":
            age += " · 传说"
        draw.text((x, y + side + 8), f"{row['number']} {row['name']} · {age}", font=font(25), fill="#252720")
        for n, text in enumerate(lines(draw, row["traits"], font(19), side)):
            draw.text((x, y + side + 45 + n * 24), text, font=font(19), fill="#55594F")
        draw.text((x, y + side + 103), row["id"], font=ImageFont.load_default(size=15), fill="#73766D")
    path = REPORT / f"batch_{index:02d}_nine_grid.png"
    sheet.save(path, compress_level=9)
    return str(path.relative_to(ROOT))


def six_groups(indexed):
    extras = [
        {"id": "qing_peng_yulin", "number": "SSR", "name": "彭玉麟", "age": 45,
         "project_path": "assets/concepts/heads_v3/qing_peng_yulin.png", "traits": "SSR已确认参照：清瘦文人、长浓须"},
        {"id": "qing_senggelinqin", "number": "SSR", "name": "僧格林沁", "age": 43,
         "project_path": "assets/concepts/heads_v2/qing_senggelinqin.png", "traits": "SSR已确认参照：宽脸、粗颈、魁梧"},
    ]
    indexed = {**indexed, **{r["id"]: r for r in extras}}
    groups = [
        ("01 三个书生", "塾师温和 / 王府从容 / 书生带兵", ["tp_feng_yunshan", "tp_hong_rengan", "qing_luo_zenan"]),
        ("02 北伐双将", "冬征冻红、厚实 / 困城疲惫、窄瘦", ["tp_lin_fengxiang", "tp_li_kaifang"]),
        ("03 湘军水师", "清瘦长须 / 粗壮短须", ["qing_peng_yulin", "qing_yang_zaifu"]),
        ("04 满蒙骑将", "宽脸粗颈 / 精悍瘦削 / 高大长方脸", ["qing_senggelinqin", "qing_duolonga", "qing_taqibu"]),
        ("05 洋枪队", "美国冒险家便装 / 英国工兵军官", ["qing_ward", "qing_gordon"]),
        ("06 政令卡", "年轻清秀忧虑 / 中年厚重强硬", ["qing_prince_gong", "qing_sushun"]),
    ]
    side, gap, margin, header, group_header, label_h = 280, 14, 28, 118, 78, 98
    group_w, group_h = 3 * side + 2 * gap, group_header + side + label_h
    outer_gap = 30
    sheet = Image.new("RGB", (2 * margin + 2 * group_w + outer_gap,
                              header + 3 * group_h + 2 * outer_gap + margin), "#EDE3CC")
    draw = ImageDraw.Draw(sheet)
    draw.text((margin, 16), "第7.1节 · 6组人物同图对比", font=font(36), fill="#252720")
    draw.text((margin, 70), "12张SR待确认头像 + 彭玉麟、僧格林沁两张SSR已确认参照；参照仅用于这张验收图，未参与他人生成。", font=font(21), fill="#55594F")
    for i, (title, note, members) in enumerate(groups):
        gx = margin + i % 2 * (group_w + outer_gap)
        gy = header + i // 2 * (group_h + outer_gap)
        draw.text((gx, gy), title, font=font(27), fill="#252720")
        draw.text((gx, gy + 38), note, font=font(20), fill="#55594F")
        for j, ident in enumerate(members):
            row = indexed[ident]
            x, y = gx + j * (side + gap), gy + group_header
            image_tile(sheet, ROOT / row["project_path"], (x, y), side)
            draw.text((x, y + side + 7), f"{row['number']} {row['name']} · {age_label(row)}", font=font(21), fill="#252720")
            for n, text in enumerate(lines(draw, row["traits"], font(17), side)):
                draw.text((x, y + side + 37 + n * 23), text, font=font(17), fill="#41643D" if row["number"] == "SSR" else "#55594F")
    path = REPORT / "six_groups_comparison.png"
    sheet.save(path, compress_level=9)
    return {"path": str(path.relative_to(ROOT)), "groups": groups, "ssr_reference_heads": extras}


def main():
    plan = json.loads((REPORT / "generation_plan.json").read_text())
    sources = json.loads((REPORT / "generation_results.json").read_text())
    by_id = {r["id"]: r for r in sources["results"]}
    with (ROOT / "data/characters.csv").open(encoding="utf-8-sig") as stream:
        expected = {r["id"] for r in csv.DictReader(stream) if r["rarity_draft"] == "SR" and r["id"] != "tp_luo_dagang"}
    assert len(expected) == 25 and set(by_id) == expected
    DEST.mkdir(parents=True, exist_ok=True)
    rows = []
    for job in plan["subjects"]:
        row = {**job, **by_id[job["id"]]}
        src, dest = Path(row["source_path"]), DEST / f"{row['id']}.png"
        if dest.exists() and sha(dest) != sha(src):
            raise ValueError(f"Version existing head before replacement: {dest}")
        if not dest.exists():
            shutil.copy2(src, dest)
        with Image.open(dest) as image:
            assert image.width == image.height
            row.update(dimensions=list(image.size), image_mode=image.mode)
        row.update(project_path=str(dest.relative_to(ROOT)), sha256=sha(dest),
                   reference_sha256=[sha(ROOT / ref) for ref in row["refs"]],
                   approval_status="PENDING_USER_REVIEW")
        assert not any("assets/raw/characters" in ref or "style_swatch" in ref for ref in row["refs"])
        rows.append(row)
    grids = [nine_grid(rows[i:i + 9], i // 9 + 1) for i in range(0, 25, 9)]
    comparison = six_groups({r["id"]: r for r in rows})
    manifest = {"tool": "built-in image_gen", "stage": "25 SR heads pending user approval; no SR full bodies generated",
                "results": rows, "nine_grids": grids, "six_group_comparison": comparison}
    (REPORT / "generation_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    with zipfile.ZipFile(REPORT / "25_sr_heads.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for row in rows:
            archive.write(ROOT / row["project_path"], f"{row['number']}_{row['id']}.png")
    print("Packaged 25 heads, 3 nine-grids (9/9/7), and all 6 groups in one comparison image.")


if __name__ == "__main__":
    main()
