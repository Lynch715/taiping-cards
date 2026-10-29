#!/usr/bin/env python3
"""Rebuild all 39 SSR/SR cards and validate the actual native cutout geometry."""
import contextlib
import csv
import hashlib
import io
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import build_portraits as pipeline

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "assets/reports/sr_full_body_v1"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def main():
    table_hash = digest(ROOT / "data/characters.csv")
    records = [r for r in pipeline.read_records(ROOT, None)
               if r.get("rarity", r.get("rarity_draft")) in {"SSR", "SR"}]
    assert len(records) == 39
    sr = json.loads((REPORT / "generation_manifest.json").read_text())
    assert len(sr["results"]) == 25 and all(not r["technical_issues"] for r in sr["results"])
    protected = json.loads((REPORT / "protected_input_sha256.json").read_text())
    assert all(digest(ROOT / p) == h for p, h in protected.items())
    argv = ["--root", str(ROOT)]
    for row in records:
        argv += ["--id", row["id"]]
    log = io.StringIO()
    with contextlib.redirect_stdout(log):
        code = pipeline.main(argv)
    (REPORT / "pipeline_run.log").write_text(log.getvalue())
    print(log.getvalue(), end="")
    assert code == 0
    reports = ROOT / "assets/reports"
    metrics = list(csv.DictReader((reports / "pipeline_report.csv").open(encoding="utf-8-sig")))
    assert len(metrics) == 39 and all(not r["warnings"] for r in metrics)
    checks = []
    for row in records:
        ident = row["id"]
        with Image.open(ROOT / "assets/raw/characters" / f"{ident}.png") as source:
            assert source.size == pipeline.SIZE and source.mode == "RGBA"
            box = pipeline.alpha_bbox(source)
            _, scale, fitted = pipeline.fit_foreground(source, box, row["height_scale"])
            final_h = fitted[3] - fitted[1]
            target = pipeline.target_height(row["height_scale"])
            assert min(box[0], box[1], 1024-box[2], 1536-box[3]) >= 4
            assert scale <= 1.25 and abs(final_h - target) <= 2
            dx = math.floor(512 + int(row["x_offset"] or "0") - (fitted[0]+fitted[2])/2 + .5)
            dy = 1392 - fitted[3]
            assert fitted[0]+dx >= 64 and fitted[2]+dx <= 960 and fitted[1]+dy >= 92
            alpha_min, alpha_max = source.getchannel("A").getextrema()
            assert alpha_min == 0 and alpha_max > 240
        with Image.open(ROOT / "assets/raw/backgrounds" / f"{row['bg_id']}.png") as bg:
            assert bg.size == pipeline.SIZE
            assert "A" not in bg.getbands() or bg.getchannel("A").getextrema() == (255,255)
        for filename, size in [("full.png", pipeline.SIZE)] + [(f"{k}.webp", v) for k,v in pipeline.DERIVATIVES.items()]:
            with Image.open(ROOT / "assets/characters" / ident / filename) as image:
                assert image.size == size and image.width*3 == image.height*2
        checks.append({"id":ident,"name":row["name"],"faction":row["faction"],"rarity":row["rarity_draft"],
                       "bg_id":row["bg_id"],"height_scale":float(row["height_scale"]),"target_h":target,
                       "final_h":final_h,"bottom_y":1392,"top_y":fitted[1]+dy,"scale":scale})
    previous = REPORT / "before/assets/characters"
    assert digest(ROOT / "data/characters.csv") == table_hash
    old_derived = list(previous.glob("*/*"))
    assert len(old_derived) == 56
    for path in old_derived:
        assert digest(path) == digest(ROOT / "assets/characters" / path.relative_to(previous))
    groups = pipeline.silhouette_groups([pipeline.Result(r) for r in records])
    validation = {"rendered_count":39,"ssr_count":13,"sr_count":26,"new_sr_count":25,
                  "existing_raw_preserved":14,"previous_derived_preserved":56,"output_files":156,
                  "warnings":[],"data_table_sha256":table_hash,"silhouette_rows":[{"label":label,"count":len(members),
                  "ids":[r.record["id"] for r in members]} for label,members in groups],
                  "character_checks":checks,"protected_input_sha256":protected,"technical_status":"OK",
                  "art_acceptance":"25 SR full bodies pending user art review; all heads already approved"}
    save_json(REPORT / "batch_validation.json",validation)
    save_json(reports / "batch_validation.json",validation)
    ssr=json.loads((reports/"full_body_distinct_v1/generation_manifest.json").read_text())
    combined={"stage":"39 SSR/SR roster ready for human full-body review","selected_ids":[r["id"] for r in records],
              "ssr_generation":ssr,"sr_generation":sr,"unchanged_raw_ids":[Path(p).stem for p in protected if p.startswith("assets/raw/characters/")]}
    save_json(reports/"generation_manifest.json",combined)
    for name in ["contact_sheet.png","silhouette_sheet.png","pipeline_report.csv","pipeline_summary.md"]:
        (REPORT/name).write_bytes((reports/name).read_bytes())
    print("39-person roster built:13 SSR +26 SR;156 full-frame outputs;0warnings;14 old raw and56 derivatives preserved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
