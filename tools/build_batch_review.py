#!/usr/bin/env python3
"""Build this project's SSR inspection batch and the ten-board overview."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import build_portraits as pipeline


ROOT = Path(__file__).resolve().parents[1]
BACKGROUND_IDS = [
    "bg_tp_tianjing", "bg_tp_jintian", "bg_tp_river", "bg_tp_field",
    "bg_qing_camp", "bg_qing_river", "bg_qing_court", "bg_qing_north",
    "bg_west_shanghai", "bg_sichuan_gorge",
]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def background_overview(root):
    # Full-frame 2:3 previews; this never crops or retouches the input boards.
    width, height, gap, margin, header = 320, 480, 20, 24, 104
    columns = 5
    cell_h = height + 66
    image = Image.new("RGB", (2 * margin + columns * width + (columns - 1) * gap,
                              header + 2 * (cell_h + gap) + margin), "#EDE3CC")
    draw = ImageDraw.Draw(image)
    title = ImageFont.load_default(size=26)
    font = ImageFont.load_default(size=17)
    draw.text((margin, 16), "BACKGROUND BOARDS / TEN SCENES", font=title, fill="#1E1915")
    draw.text((margin, 55), "1024x1536 originals | uncropped 320x480 previews | red: figure foot baseline", font=font, fill="#4A4038")
    records = []
    for index, ident in enumerate(BACKGROUND_IDS):
        path = root / "assets/raw/backgrounds" / f"{ident}.png"
        with Image.open(path) as board:
            opaque = "A" not in board.getbands() or board.getchannel("A").getextrema() == (255, 255)
            valid = board.size == pipeline.SIZE and opaque
            records.append({"id": ident, "width": board.width, "height": board.height,
                            "mode": board.mode, "opaque": opaque,
                            "technical_status": "OK" if valid else "INVALID", "sha256": digest(path)})
            if not valid:
                raise ValueError(f"Invalid background board: {ident}")
            preview = board.convert("RGB").resize((width, height), Image.Resampling.LANCZOS)
        x = margin + index % columns * (width + gap)
        y = header + index // columns * (cell_h + gap)
        image.paste(preview, (x, y))
        baseline = round(1392 / 1536 * height)
        draw.line((x, y + baseline, x + width - 1, y + baseline), fill="#A8261B", width=2)
        draw.text((x, y + height + 10), ident, font=font, fill="#1E1915")
        draw.text((x, y + height + 35), "1024x1536 / OPAQUE / OK", font=font, fill="#41643D")
    image.save(root / "assets/reports/background_contact_sheet.png", compress_level=9)
    with (root / "assets/reports/background_report.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)
    return records


def main():
    root = ROOT
    reports = root / "assets/reports"
    with (root / "data/characters.csv").open(encoding="utf-8-sig", newline="") as stream:
        all_records = list(csv.DictReader(stream))
    ssr = [row for row in all_records if row.get("rarity", row.get("rarity_draft")) == "SSR"]
    ids = ["tp_luo_dagang"] + [row["id"] for row in ssr]
    records = pipeline.read_records(root, ids)
    table_hash = digest(root / "data/characters.csv")
    raw_paths = [root / "assets/raw/characters" / f"{ident}.png" for ident in ids]
    raw_paths += [root / "assets/raw/backgrounds" / f"{ident}.png" for ident in BACKGROUND_IDS]
    before = {str(path.relative_to(root)): digest(path) for path in raw_paths}
    command = [sys.executable, str(root / "tools/build_portraits.py")]
    for ident in ids:
        command += ["--id", ident]
    run = subprocess.run(command, capture_output=True, text=True)
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "pipeline_run.log").write_text(run.stdout + run.stderr, encoding="utf-8")
    print(run.stdout, end="")
    if run.returncode:
        print(run.stderr, file=sys.stderr)
        return run.returncode
    with (reports / "pipeline_report.csv").open(encoding="utf-8-sig", newline="") as stream:
        metrics = {row["id"]: row for row in csv.DictReader(stream)}
    checks = []
    for row in records:
        ident = row["id"]
        with Image.open(root / "assets/raw/characters" / f"{ident}.png") as source:
            if source.size != pipeline.SIZE or "A" not in source.getbands():
                raise ValueError(f"Expected 1024x1536 native alpha PNG: {ident}")
            alpha = np.asarray(source.getchannel("A"))
            if not np.any(alpha == 0) or not np.any(alpha > 240):
                raise ValueError(f"Missing meaningful native transparency: {ident}")
            bounds = pipeline.alpha_bbox(source)
            coefficient = pipeline.parse_height_scale(row.get("height_scale"))
            target_h = pipeline.target_height(coefficient)
            resized, scale, box = pipeline.fit_foreground(source, bounds, coefficient)
            dx = math.floor(512 + int(row["x_offset"] or "0") - (box[0] + box[2]) / 2 + 0.5)
            dy = 1392 - box[3]
            if box[1] + dy < 92 or box[0] + dx < 64 or box[2] + dx > 960:
                raise ValueError(f"Safe area violation: {ident}")
            if metrics[ident]["warnings"]:
                raise ValueError(f"Unresolved warnings: {ident}: {metrics[ident]['warnings']}")
            if abs((box[3] - box[1]) - target_h) > 2:
                raise ValueError(f"Height differs from coefficient target by >2px: {ident}")
            info = {"id": ident, "name": row["name"], "bg_id": row["bg_id"],
                    "height_scale": coefficient, "target_h": target_h, "final_h": box[3] - box[1],
                    "top_y": box[1] + dy, "bottom_y": box[3] + dy,
                    "scale": float(metrics[ident]["scale"]),
                    "transparent_percent": round(float((alpha == 0).mean()) * 100, 2)}
        for filename, dimensions in [("full.png", pipeline.SIZE)] + [
                (f"{name}.webp", size) for name, size in pipeline.DERIVATIVES.items()]:
            with Image.open(root / "assets/characters" / ident / filename) as output:
                if output.size != dimensions or output.width * 3 != output.height * 2:
                    raise ValueError(f"Wrong derivative dimensions: {ident}/{filename}")
        checks.append(info)
    boards = background_overview(root)
    if digest(root / "data/characters.csv") != table_hash:
        raise ValueError("Character table was modified")
    if {str(path.relative_to(root)): digest(path) for path in raw_paths} != before:
        raise ValueError("Raw source assets were modified")
    generated = json.loads((reports / "full_body_distinct_v1/generation_manifest.json").read_text())
    preserved = ["tp_shi_dakai", "qing_zeng_guofan", "qing_xianfeng", "qing_cixi", "tp_luo_dagang"]
    generated.update(stage="SSR batch ready for human review", selected_ids=ids,
                     previous_generation_manifest="assets/reports/full_body_distinct_v1/before/assets/reports/generation_manifest.json",
                     unchanged_approved_raw={ident: before[f"assets/raw/characters/{ident}.png"]
                                             for ident in preserved})
    (reports / "generation_manifest.json").write_text(json.dumps(generated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    payload = {"ssr_count": len(ssr), "regenerated_count": len(generated["results"]),
               "preserved_raw_count": len(preserved), "faceless_style_swatch_count": 2,
               "style_reference_paths": ["docs/reference/style_swatch_impasto_cloth.png",
                                         "docs/reference/style_swatch_impasto_sky.png"],
               "rendered_count": len(ids),
               "background_count": len(boards), "character_checks": checks,
               "background_checks": boards, "raw_sha256": before,
               "data_table_sha256": table_hash, "technical_status": "OK",
               "art_acceptance": "Nine approved head identities used; nine new full bodies pending user review; five approved raw characters preserved"}
    (reports / "batch_validation.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Review ready: {len(ssr)} SSR + Luo Dagang reference; {len(boards)} distinct backgrounds.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
