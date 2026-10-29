#!/usr/bin/env python3
"""Validate and copy native SR cutouts without touching any approved input."""
import hashlib
import json
import shutil
from pathlib import Path

import numpy as np
from PIL import Image

import build_portraits as pipeline

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "assets/reports/sr_full_body_v1"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    plan = json.loads((REPORT / "generation_plan.json").read_text())
    outputs = json.loads((REPORT / "generation_results.json").read_text())
    jobs = {r["id"]: r for r in plan["subjects"]}
    approved = {r["id"]: r for r in json.loads((ROOT / "assets/reports/sr_head_approval_state.json").read_text())["heads"]}
    protected = json.loads((REPORT / "protected_input_sha256.json").read_text())
    assert all(digest(ROOT / p) == h for p, h in protected.items()), "Protected input changed"
    ids, checks, manifests = set(), [], []
    for result in outputs["results"]:
        ident = result["id"]
        assert ident in jobs and ident not in ids
        ids.add(ident)
        job = jobs[ident]
        assert approved[ident]["approval_status"] == "USER_APPROVED"
        assert job["refs"] == [approved[ident]["project_path"],
                               "docs/reference/style_swatch_impasto_cloth.png",
                               "docs/reference/style_swatch_impasto_sky.png",
                               f"assets/raw/backgrounds/{job['bg_id']}.png"]
        assert all(digest(ROOT / p) == h for p, h in zip(job["refs"], job["reference_sha256"]))
        source = Path(result["source_path"])
        issues, box, scale, final_h = [], None, None, None
        with Image.open(source) as im:
            if im.size != pipeline.SIZE or im.mode != "RGBA":
                issues.append("NATIVE_FORMAT")
            else:
                alpha = np.asarray(im.getchannel("A"))
                if not (np.any(alpha == 0) and np.any(alpha > 240)):
                    issues.append("NO_NATIVE_ALPHA")
                box = pipeline.alpha_bbox(im)
                if min(box[0], box[1], im.width - box[2], im.height - box[3]) < 4:
                    issues.append("EDGE_CUT")
                _, scale, fitted = pipeline.fit_foreground(im, box, job["height_scale"])
                final_h = fitted[3] - fitted[1]
                if scale > 1.25:
                    issues.append("UPSCALE")
                if abs(final_h - pipeline.target_height(job["height_scale"])) > 2:
                    issues.append("WIDE")
        dest = ROOT / "assets/raw/characters" / f"{ident}.png"
        if not issues:
            if dest.exists() and digest(dest) != digest(source):
                history = REPORT / "superseded_raw" / f"{ident}_{digest(dest)[:12]}.png"
                history.parent.mkdir(exist_ok=True)
                shutil.copy2(dest, history)
            shutil.copy2(source, dest)
        checks.append({"id": ident, "bbox": box, "scale": scale, "final_h": final_h,
                       "issues": issues, "promoted": not issues})
        manifests.append({**job, **result, "raw_path": str(dest.relative_to(ROOT)),
                          "source_sha256": digest(source), "technical_issues": issues,
                          "head_status": "USER_APPROVED", "full_body_status": "PENDING_USER_ART_REVIEW"})
    (REPORT / "source_validation.json").write_text(json.dumps(checks, ensure_ascii=False, indent=2) + "\n")
    (REPORT / "generation_manifest.json").write_text(json.dumps({"tool": "built-in image_gen",
        "stage": "25 approved SR heads converted to native full bodies; human body review pending",
        "results": manifests}, ensure_ascii=False, indent=2) + "\n")
    print(f"Validated {len(checks)}/25 generated; promoted {sum(not r['issues'] for r in checks)}")
    for check in checks:
        print(check["id"], ";".join(check["issues"]) or "OK")
    return int(any(r["issues"] for r in checks))


if __name__ == "__main__":
    raise SystemExit(main())
