#!/usr/bin/env python3
"""Package the two requested SR edits and a five-person comparison, preserving v1."""
import csv
import hashlib
import html
import json
import shutil
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "assets/reports/sr_head_review_v2"
DEST = ROOT / "assets/concepts/sr_heads_v2"
FONT = "/System/Library/Fonts/Supplemental/Songti.ttc"
EDITED = {"tp_tan_shaoguang", "qing_li_xubin"}
HELD = {"tp_li_shixian", "qing_duolonga"}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def comparison(rows):
    indexed = {r["id"]: r for r in rows}
    side, gap, margin = 400, 22, 28
    sheet = Image.new("RGB", (3 * side + 2 * gap + 2 * margin, 1236), "#EDE3CC")
    draw = ImageDraw.Draw(sheet)
    def text(x, y, value, size=24, fill="#252720"):
        draw.text((x, y), value, font=ImageFont.truetype(FONT, size), fill=fill)
    text(margin, 14, "SR头像修订 · 两组与陈玉成同图对比", 34)
    text(margin, 66, "S05、S16与SSR原图保留；只修订S08、S13。所有图片全幅等比排版。", 20, "#55594F")
    slots = [
        ("tp_li_shixian", 0, 0, "原图保留", "年轻剽悍 · 头巾"),
        ("tp_tan_shaoguang", 1, 0, "修订待确认", "刺绣软王帽 · 神情决绝"),
        ("qing_li_xubin", 0, 1, "修订待确认", "湘军布便帽 · 浓须"),
        ("qing_duolonga", 1, 1, "原图保留", "精悍瘦削 · 八旗军盔"),
    ]
    for ident, col, row, status, note in slots:
        r = indexed[ident]
        x, y = margin + col * (side + gap), 148 + row * 548
        with Image.open(ROOT / r["project_path"]) as im:
            sheet.paste(im.convert("RGB").resize((side, side), Image.Resampling.LANCZOS), (x, y))
        text(x, y + side + 9, f"{r['number']} {r['name']} · {r['age']}岁", 26)
        text(x, y + side + 49, status + "｜" + note, 20, "#55594F")
    x, y = margin + 2 * (side + gap), 422
    path = ROOT / "assets/concepts/heads_v3/tp_chen_yucheng.png"
    with Image.open(path) as im:
        sheet.paste(im.convert("RGB").resize((side, side), Image.Resampling.LANCZOS), (x, y))
    text(x, y - 49, "已确认SSR头像参照", 26)
    text(x, y + side + 9, "SSR 陈玉成 · 22岁", 26)
    text(x, y + side + 49, "风霜少年 · 双眼下小痣 · 红头巾", 20, "#55594F")
    text(x, y + side + 87, "仅用于排版对比，未参与修订生成", 20, "#55594F")
    out = REPORT / "five_character_comparison.png"
    sheet.save(out, compress_level=9)
    return out


def font_page(names):
    # QA page only. Mirrors the real mockup's Google CSS and fallback chain.
    source = (ROOT / "docs/界面样稿.html").read_text()
    link = next(line for line in source.splitlines() if "fonts.googleapis.com/css2" in line)
    cards = "".join(f'<div class="name">{html.escape(n)}</div>' for n in names)
    page = f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>人物名字体覆盖验收</title>
{link}
<style>body{{background:#EDE3CC;color:#1E1915;padding:24px;font-family:"Noto Serif SC","Songti SC","SimSun",serif}}
h1{{font-size:30px}}p{{font-size:18px}}.rare{{font-size:48px;font-weight:900;letter-spacing:.12em}}
.names{{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;max-width:1100px}}
.name{{padding:9px;border:1px solid #C9B994;font-size:25px;font-weight:700}}
.vertical{{writing-mode:vertical-rl;height:130px;font-size:32px;font-weight:900;letter-spacing:.12em}}
pre{{white-space:pre-wrap;font:14px monospace;max-width:1100px}}</style>
<h1>人物名字体覆盖验收 · 55位</h1>
<p>使用界面样稿原有字体链；本页为验收页，不改变游戏界面。</p>
<div class="rare">梁 樑 玕 荃 呤 麟</div><div class="vertical">张国梁　洪仁玕</div>
<div class="names">{cards}</div><h2>本页字体加载状态</h2><pre id="font-status">加载中</pre>
<script>window.addEventListener('load',async()=>{{await document.fonts.ready;
const faces=Array.from(document.fonts),counts={{}};
for(const f of faces){{const key=f.family+' / '+f.weight+' / '+f.status;counts[key]=(counts[key]||0)+1}}
const chars=Array.from(new Set(Array.from(document.querySelector('.names').textContent+'樑梁玕荃呤麟')));
const covers=(f,c)=>f.unicodeRange.split(',').some(part=>{{const range=part.trim().replace(/^U\\+/,'').split('-');
const low=parseInt(range[0],16),high=parseInt(range[1]||range[0],16),point=c.codePointAt(0);return point>=low&&point<=high}});
document.querySelector('#font-status').textContent=JSON.stringify({{
family:getComputedStyle(document.body).fontFamily,status:document.fonts.status,faceCount:faces.length,counts,
declaredMissing:chars.filter(c=>!faces.some(f=>f.family==='Noto Serif SC'&&covers(f,c))),
loadedMissing:chars.filter(c=>!faces.some(f=>f.family==='Noto Serif SC'&&f.status==='loaded'&&covers(f,c)))
}},null,2)}})</script></html>'''
    (REPORT / "font_check.html").write_text(page)


def main():
    DEST.mkdir(exist_ok=True)
    old = json.loads((REPORT / "previous_manifest.json").read_text())
    selected = json.loads((REPORT / "generation_results.json").read_text())["results"]
    requests = json.loads((REPORT / "generation_requests.json").read_text())
    jobs = {r["id"]: r for r in requests["jobs"]}
    by_id = {r["id"]: r for r in selected}
    assert set(by_id) == EDITED
    names = {r["id"]: r["name"] for r in csv.DictReader((ROOT / "data/characters.csv").open())}
    rows = []
    for original in old["results"]:
        row = dict(original)
        ident = row["id"]
        row["name"] = names[ident]
        if ident in EDITED:
            result, job = by_id[ident], jobs[ident]
            src, dest = Path(result["source_path"]), DEST / f"{ident}.png"
            if dest.exists() and sha(dest) != sha(src):
                raise ValueError(f"Version existing image before replacement: {dest}")
            if not dest.exists():
                shutil.copy2(src, dest)
            with Image.open(dest) as im:
                assert im.width == im.height
                dimensions, mode = list(im.size), im.mode
            row.update(previous_version=original, project_path=str(dest.relative_to(ROOT)),
                       source_path=str(src), sha256=sha(dest), dimensions=dimensions, image_mode=mode,
                       subject="Tan Shaoguang, 28; preserve v1 identity, embroidered soft king's Jiaomao, decisive expression." if ident == "tp_tan_shaoguang" else "Li Xubin, 40; preserve v1 identity, Xiang Army soft cloth cap, dense coarse beard, no helmet.",
                       prompt=job["prompt"], refs=job["refs"], reference_sha256=[sha(Path(p)) for p in job["refs"]],
                       approval_status="REVISED_PENDING_USER_REVIEW")
            row.pop("framing_edit", None)
            if ident == "tp_tan_shaoguang":
                row["framing_edit"] = requests["framing"]
                row["first_revision_source_path"] = result["first_source_path"]
                row["traits"] = "年轻刚烈，刺绣织物王帽、神情决绝"
            else:
                row["traits"] = "宽颧强颌、浓须，湘军布便帽，无头盔"
        else:
            row["approval_status"] = "UNCHANGED_PENDING_COMPARISON" if ident in HELD else "USER_APPROVED"
        assert sha(ROOT / row["project_path"]) == row["sha256"]
        rows.append(row)
    preserved = json.loads((REPORT / "preserved_sha256.json").read_text())
    assert all(sha(ROOT / p) == value for p, value in preserved.items())
    assert len(rows) == 25 and sum(r["approval_status"] == "USER_APPROVED" for r in rows) == 21
    state = {"stage": "21 approved; S05/S16 unchanged for comparison; S08/S13 revised awaiting approval",
             "source": "User review in current chat, 2026-10-27",
             "approved_ids": [r["id"] for r in rows if r["approval_status"] == "USER_APPROVED"],
             "pending_ids": [r["id"] for r in rows if r["approval_status"] != "USER_APPROVED"],
             "revised_ids": sorted(EDITED), "unchanged_comparison_ids": sorted(HELD),
             "heads": rows}
    save_json(ROOT / "assets/reports/sr_head_approval_state.json", state)
    out = comparison(rows)
    save_json(REPORT / "generation_manifest.json", {"tool": "built-in image_gen", "results": rows,
        "comparison_path": str(out.relative_to(ROOT)), "comparison_only_ssr": "assets/concepts/heads_v3/tp_chen_yucheng.png"})
    save_json(REPORT / "validation.json", {"sr_heads": 25, "approved": 21, "revised_pending": 2,
        "unchanged_pending_comparison": 2, "comparison_people": 5, "all_preserved_files": len(preserved),
        "preserved_sha256_match": True, "sr_full_bodies_generated": 0})
    with zipfile.ZipFile(REPORT / "25_current_sr_heads.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for row in rows:
            archive.write(ROOT / row["project_path"], f"{row['number']}_{row['id']}.png")
    font_page(list(names.values()))
    print(f"Saved {out}; 21 approved, 2 unchanged comparison heads, 2 revisions; preserved {len(preserved)} images")


if __name__ == "__main__":
    main()
