#!/usr/bin/env python3
"""Package the nine head concepts without touching production/raw portraits."""

from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "assets/reports/head_review_v2"
CONCEPTS = ROOT / "assets/concepts/heads_v2"
FONT = "/System/Library/Fonts/Supplemental/Songti.ttc"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def wrap(draw, text, font, width):
    lines, line = [], ""
    for char in text:
        if line and draw.textlength(line + char, font=font) > width:
            lines.append(line)
            line = ""
        line += char
    if line:
        lines.append(line)
    return lines


def main():
    designs = json.loads((REVIEW / "designs_and_prompts.json").read_text())
    manifest = json.loads((REVIEW / "generation_manifest.json").read_text())
    indexed = {row["id"]: row for row in manifest["results"]}
    subjects = designs["subjects"]
    if len(subjects) != 9 or len(indexed) != 9:
        raise ValueError("Expected exactly nine head concepts")
    CONCEPTS.mkdir(parents=True, exist_ok=True)
    rows = []
    for design in subjects:
        row = dict(indexed[design["id"]])
        src = Path(row["source_path"])
        dest = CONCEPTS / f"{design['id']}.png"
        if dest.exists() and digest(dest) != digest(src):
            raise ValueError(f"Different concept already exists; version it before replacing: {dest}")
        if not dest.exists():
            shutil.copy2(src, dest)
        with Image.open(dest) as image:
            if image.width != image.height:
                raise ValueError(f"Head concept must be square: {dest}")
            row.update(dimensions=list(image.size), mode=image.mode)
        row.update(name=design["name"], age=design["age"], traits=design["traits"],
                   reference_basis=design["basis"], historical_references=design["refs"],
                   initial_prompt=design["subject"] + "\n\n" + designs["global_style_and_framing"],
                   project_path=str(dest.relative_to(ROOT)), sha256=digest(dest),
                   approval_status="PENDING_USER_REVIEW")
        rows.append(row)

    margin, gap, image_size, label_h, header = 28, 24, 480, 138, 126
    cell_h = image_size + label_h
    sheet = Image.new("RGB", (margin * 2 + 3 * image_size + 2 * gap,
                              header + 3 * cell_h + 2 * gap + margin), "#EDE7DC")
    draw = ImageDraw.Draw(sheet)
    title_font = ImageFont.truetype(FONT, 38)
    name_font = ImageFont.truetype(FONT, 30)
    note_font = ImageFont.truetype(FONT, 21)
    id_font = ImageFont.load_default(size=17)
    draw.text((margin, 18), "SSR 头像设定 · 第二轮 / 9 人待确认", font=title_font, fill="#252720")
    draw.text((margin, 74), "本轮确认脸型、年龄感、胡须与头饰；全身服装、姿态及最终画风在确认后制作。", font=note_font, fill="#55594F")
    for index, row in enumerate(rows):
        x = margin + index % 3 * (image_size + gap)
        y = header + index // 3 * (cell_h + gap)
        with Image.open(ROOT / row["project_path"]) as image:
            preview = image.convert("RGB").resize((image_size, image_size), Image.Resampling.LANCZOS)
        sheet.paste(preview, (x, y))
        draw.text((x, y + image_size + 9), f"{index+1:02d}  {row['name']} · {row['age']}岁", font=name_font, fill="#252720")
        for line_no, line in enumerate(wrap(draw, row["traits"], note_font, image_size)):
            draw.text((x, y + image_size + 49 + line_no * 26), line, font=note_font, fill="#55594F")
        draw.text((x, y + image_size + 111), row["id"], font=id_font, fill="#77786F")
    sheet.save(REVIEW / "contact_sheet.png", compress_level=9)
    manifest["results"] = rows
    manifest["contact_sheet"] = "assets/reports/head_review_v2/contact_sheet.png"
    manifest["scope"] = "Head identity approval only; production full-body generation and height-scale rebuild await user confirmation."
    (REVIEW / "generation_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    with zipfile.ZipFile(REVIEW / "nine_ssr_heads_v2.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for row in rows:
            archive.write(ROOT / row["project_path"], f"{row['id']}.png")
    before = json.loads((REVIEW / "production_preservation_before.json").read_text())
    changed = [path for path, sha in before.items() if not (ROOT / path).exists() or digest(ROOT / path) != sha]
    preservation = {"checked_count": len(before), "changed": changed,
                    "status": "UNCHANGED" if not changed else "CHANGED"}
    (REVIEW / "production_preservation_check.json").write_text(json.dumps(preservation, ensure_ascii=False, indent=2) + "\n")
    if changed:
        raise ValueError(f"Production inputs or outputs changed during head review: {changed}")
    print(f"Packaged {len(rows)} heads; {len(before)} production files remain byte-identical.")


if __name__ == "__main__":
    main()
