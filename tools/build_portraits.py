#!/usr/bin/env python3
"""Build uncropped portraits and an honest, deterministic asset inspection sheet.

Python 3.11+, Pillow and numpy. Paths are relative to this project, not the cwd.
--check writes reports only; all composition is still performed in memory.
"""

from __future__ import annotations

import argparse
import csv
import math
import re
import sys
import textwrap
from collections import Counter, deque
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageEnhance


ROOT = Path(__file__).resolve().parents[1]
SIZE = (1024, 1536)
DERIVATIVES = {"full": SIZE, "card": (400, 600), "mini": (160, 240), "thumb": (96, 144)}
DEFAULT_HEIGHT_SCALE = 0.96
REPORT_FIELDS = [
    "id", "src_w", "src_h", "bbox_x", "bbox_y", "bbox_w", "bbox_h",
    "height_scale", "scale", "final_h", "warnings",
]
ERRORS = {
    "SRC_MISSING", "SRC_INVALID", "BG_INVALID", "FX_INVALID", "NO_FOREGROUND",
    "REMBG_ERROR", "PLACEMENT_INVALID",
}
BLOCKERS = ERRORS | {"UPSCALE", "EDGE_CUT"}
ID_PATTERN = re.compile(r"(?:tp|qing)_[a-z0-9]+(?:_[a-z0-9]+)*\Z")
BG_PATTERN = re.compile(r"bg_[a-z0-9]+(?:_[a-z0-9]+)*\Z")


@dataclass
class Result:
    record: dict[str, str]
    metrics: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    details: list[str] = field(default_factory=list)
    preview: Image.Image | None = None
    silhouette: Image.Image | None = None

    def warn(self, code: str, detail: str = "") -> None:
        if code not in self.warnings:
            self.warnings.append(code)
        if detail:
            self.details.append(detail)

    @property
    def failed(self) -> bool:
        return bool(ERRORS.intersection(self.warnings))

    def report_row(self) -> dict:
        return {
            **dict.fromkeys(REPORT_FIELDS, ""),
            **self.metrics,
            "id": self.record["id"],
            "warnings": ";".join(self.warnings),
        }


class AssetError(ValueError):
    pass


def parse_height_scale(value=None) -> float:
    """Validate even unselected rows, before any files are written."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return DEFAULT_HEIGHT_SCALE
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise AssetError(f"height_scale must be a number in 0.90..1.00: {value!r}") from exc
    if not math.isfinite(number) or not 0.90 <= number <= 1.00:
        raise AssetError(f"height_scale must be finite and in 0.90..1.00: {value!r}")
    return number


def target_height(value=None) -> int:
    return round(1300 * parse_height_scale(value))


def read_records(root: Path, selected_id: str | list[str] | None) -> list[dict[str, str]]:
    with (root / "data/characters.csv").open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        required = {"id", "bg_id", "x_offset"}
        if not required.issubset(reader.fieldnames or []):
            raise AssetError("characters.csv requires id, bg_id, x_offset columns")
        records = list(reader)
    if not records:
        raise AssetError("characters.csv is empty")
    npc_path = root / "data/npc_portraits.csv"
    if npc_path.exists():
        with npc_path.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if not {"id", "bg_id", "x_offset", "height_scale"}.issubset(reader.fieldnames or []):
                raise AssetError("npc_portraits.csv requires id, bg_id, x_offset, height_scale")
            for row in reader:
                if not re.fullmatch(r"(?:tp|qing)_npc_[a-z0-9_]+", row.get("id", "")):
                    raise AssetError("Invalid NPC portrait id")
                if parse_height_scale(row.get("height_scale")) != 0.93:
                    raise AssetError("NPC height_scale must be 0.93")
                records.append({**row, "rarity": "N", "portrait_kind": "npc"})
    seen = set()
    for row in records:
        for key, value in row.items():
            if key is None or value is None:
                raise AssetError("characters.csv contains a malformed row")
            row[key] = value.strip()
        ident = row["id"]
        if not ID_PATTERN.fullmatch(ident) or ident in seen:
            raise AssetError(f"Invalid or duplicate character id: {ident!r}")
        if not BG_PATTERN.fullmatch(row["bg_id"]):
            raise AssetError(f"Invalid bg_id for {ident}: {row['bg_id']!r}")
        try:
            int(row["x_offset"] or "0")
        except ValueError as exc:
            raise AssetError(f"x_offset must be an integer: {ident}") from exc
        try:
            row["height_scale"] = format(parse_height_scale(row.get("height_scale")), ".15g")
        except AssetError as exc:
            raise AssetError(f"{ident}: {exc}") from exc
        seen.add(ident)
    if selected_id:
        requested = [selected_id] if isinstance(selected_id, str) else selected_id
        indexed = {row["id"]: row for row in records}
        unknown = [ident for ident in requested if ident not in indexed]
        if unknown:
            raise AssetError(f"Unknown id: {', '.join(unknown)}")
        records = [indexed[ident] for ident in dict.fromkeys(requested)]
    return records


def load_image(path: Path) -> Image.Image:
    with Image.open(path) as image:
        image.load()
        if getattr(image, "n_frames", 1) != 1:
            raise AssetError("Animated input is not supported")
        return image.copy()


def rgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    """sRGB -> CIE L*a*b*, D65 white; Delta E below is CIE76."""
    value = np.asarray(rgb, dtype=np.float64) / 255.0
    linear = np.where(value <= 0.04045, value / 12.92,
                      ((value + 0.055) / 1.055) ** 2.4)
    xyz = linear @ np.array([
        [0.4124564, 0.3575761, 0.1804375],
        [0.2126729, 0.7151522, 0.0721750],
        [0.0193339, 0.1191920, 0.9503041],
    ]).T
    xyz /= np.array([0.95047, 1.0, 1.08883])
    delta = 6.0 / 29.0
    mapped = np.where(xyz > delta**3, np.cbrt(xyz),
                      xyz / (3 * delta**2) + 4.0 / 29.0)
    x, y, z = np.moveaxis(mapped, -1, 0)
    return np.stack([116 * y - 16, 500 * (x - y), 200 * (y - z)], axis=-1)


def edge_connected(mask: np.ndarray) -> np.ndarray:
    """Four-connected flood fill, seeded along ALL four canvas edges.

    Fill horizontal spans rather than queueing each pixel. Enclosed matching
    colors remain foreground, even when they exactly match the corner key.
    """
    remaining = mask.copy()
    height, width = remaining.shape
    background = np.zeros_like(remaining)
    seeds = deque()
    for y in (0, height - 1):
        seeds.extend((y, int(x)) for x in np.flatnonzero(remaining[y]))
    for x in (0, width - 1):
        seeds.extend((int(y), x) for y in np.flatnonzero(remaining[:, x]))
    while seeds:
        y, x = seeds.pop()
        if not remaining[y, x]:
            continue
        row = remaining[y]
        stops_left = np.flatnonzero(~row[:x])
        stops_right = np.flatnonzero(~row[x + 1:])
        left = int(stops_left[-1]) + 1 if stops_left.size else 0
        right = x + 1 + int(stops_right[0]) if stops_right.size else width
        remaining[y, left:right] = False
        background[y, left:right] = True
        for neighbor in (y - 1, y + 1):
            if 0 <= neighbor < height:
                segment = remaining[neighbor, left:right]
                # One seed per neighboring run that touches this filled span.
                starts = np.flatnonzero(segment & np.r_[True, ~segment[:-1]])
                seeds.extend((neighbor, left + int(start)) for start in starts)
    return background


def color_key(image: Image.Image, tolerance: float) -> Image.Image:
    """Remove only edge-connected CIE76 matches; feather inward by 1–2px.

    Feather the exterior silhouette, not color transitions inside the figure.
    Background stays exactly transparent; no background RGB is blurred back
    into the edge, which would otherwise introduce pale/gray fringes.
    """
    rgb = np.asarray(image.convert("RGB"))
    corner = np.mean(np.array([rgb[0, 0], rgb[0, -1], rgb[-1, 0], rgb[-1, -1]]), axis=0)
    rgba = np.array(image.convert("RGBA"))
    matches = np.empty((image.height, image.width), dtype=bool)
    # Process strips to avoid several full-sized float arrays for large source art.
    key_lab = rgb_to_lab(corner)
    for start in range(0, image.height, 256):
        distance = np.linalg.norm(rgb_to_lab(rgb[start:start + 256]) - key_lab, axis=-1)
        matches[start:start + 256] = distance < tolerance
    background = edge_connected(matches)
    hard_alpha = Image.fromarray(np.where(background, 0, 255).astype(np.uint8))
    inner_one = hard_alpha.filter(ImageFilter.MinFilter(3))
    inner_two = inner_one.filter(ImageFilter.MinFilter(3))
    # Linear inward ramp: 0 (background), 85, 170, 255 (figure interior).
    # Averaging masks in uint16 avoids overflow and preserves thin details.
    rgba[..., 3] = ((np.asarray(hard_alpha, dtype=np.uint16)
                    + np.asarray(inner_one, dtype=np.uint16)
                    + np.asarray(inner_two, dtype=np.uint16)) // 3).astype(np.uint8)
    return Image.fromarray(rgba)


def alpha_bbox(image: Image.Image, threshold: int = 16):
    alpha = np.asarray(image.getchannel("A"))
    rows = np.flatnonzero((alpha > threshold).any(axis=1))
    cols = np.flatnonzero((alpha > threshold).any(axis=0))
    if not len(rows) or not len(cols):
        return None
    return int(cols[0]), int(rows[0]), int(cols[-1]) + 1, int(rows[-1]) + 1


def neutral_paper() -> Image.Image:
    # Fixed mathematical grain: deterministic and independent of random state.
    y, x = np.indices((SIZE[1], SIZE[0]), dtype=np.int32)
    grain = ((x * 17 + y * 29 + (x * y) % 19) % 7 - 3).astype(np.int16)
    rgb = np.clip(np.array([214, 213, 209]) + grain[..., None], 0, 255).astype(np.uint8)
    return Image.fromarray(rgb).convert("RGBA")


def screen_blend(base: Image.Image, overlay: Image.Image) -> Image.Image:
    b = np.asarray(base.convert("RGB"), dtype=np.float32) / 255
    f = np.asarray(overlay.convert("RGBA"), dtype=np.float32) / 255
    mixed = 1 - (1 - b) * (1 - f[..., :3])
    rgb = b * (1 - f[..., 3:4]) + mixed * f[..., 3:4]
    return Image.fromarray(np.floor(np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8)).convert("RGBA")


def fit_foreground(source: Image.Image, bounds, height_scale=None) -> tuple[Image.Image, float, tuple]:
    """Resize the WHOLE source, including transparent padding; never crop."""
    bw, bh = bounds[2] - bounds[0], bounds[3] - bounds[1]
    target_h = target_height(height_scale)
    scale = min(target_h / bh, 896 / bw)
    # Lanczos may extend the alpha>16 bbox by a pixel. Shrink minimally until
    # the measured figure fits, preserving the 92px head band and 896px width.
    for _ in range(16):
        dimensions = (max(1, math.floor(source.width * scale)),
                      max(1, math.floor(source.height * scale)))
        resized = source.resize(dimensions, Image.Resampling.LANCZOS)
        box = alpha_bbox(resized)
        if box is None:
            raise AssetError("Foreground disappeared while scaling")
        width, height = box[2] - box[0], box[3] - box[1]
        if width <= 896 and height <= target_h:
            return resized, scale, box
        scale *= min(896 / width, target_h / height) * 0.9999
    raise AssetError("Could not fit foreground inside the specified safe area")


def process(root: Path, record: dict[str, str], tolerance: float,
            remove_background=None) -> Result:
    result = Result(record)
    ident = record["id"]
    height_scale = parse_height_scale(record.get("height_scale"))
    target_h = target_height(height_scale)
    result.metrics["height_scale"] = format(height_scale, ".15g")
    if "planned_bg_id" in record:
        result.details.append(f"Review background override: {record['bg_id']}; planned scene preserved in CSV: {record['planned_bg_id']}")
    source_path = root / "assets/raw/characters" / f"{ident}.png"
    bg_path = root / "assets/raw/backgrounds" / f"{record['bg_id']}.png"
    fx_path = root / "assets/raw/fx" / f"{ident}.png"
    source = background = fx = None
    try:
        source = load_image(source_path)
        result.metrics.update(src_w=source.width, src_h=source.height)
    except FileNotFoundError:
        result.warn("SRC_MISSING", f"Missing source: assets/raw/characters/{ident}.png")
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        result.warn("SRC_INVALID", f"Source could not be read: {exc}")
    try:
        background = load_image(bg_path).convert("RGBA")
        if background.size != SIZE:
            raise AssetError(f"Expected {SIZE}, got {background.size}; background was not resized")
        if background.getchannel("A").getextrema()[0] != 255:
            raise AssetError("Background board must be opaque")
    except FileNotFoundError:
        result.warn("BG_MISSING", f"Missing background: assets/raw/backgrounds/{record['bg_id']}.png")
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        result.warn("BG_INVALID", f"Invalid background: {exc}")
    rarity = record.get("rarity", record.get("rarity_draft", "")).upper()
    if rarity == "SSR" and fx_path.exists():
        try:
            fx = load_image(fx_path).convert("RGBA")
            if fx.size != SIZE:
                raise AssetError(f"Expected {SIZE}, got {fx.size}; FX was not resized")
        except (OSError, ValueError, Image.DecompressionBombError) as exc:
            result.warn("FX_INVALID", f"Invalid effect: {exc}")
    if source is None:
        return result
    if "A" in source.getbands() or "transparency" in source.info:
        foreground = source.convert("RGBA")
    elif remove_background is not None:
        try:
            foreground = remove_background(source).convert("RGBA")
            if foreground.size != source.size:
                raise AssetError("rembg changed the source canvas dimensions")
        except Exception as exc:
            result.warn("REMBG_ERROR", str(exc))
            return result
    else:
        foreground = color_key(source, tolerance)
        result.warn("NO_ALPHA_FALLBACK", "Edge-connected CIE76 color key with 2px inward feather; inspect edges manually")
    box = alpha_bbox(foreground)
    if box is None:
        result.warn("NO_FOREGROUND", "No pixels with alpha > 16 remain")
        return result
    x0, y0, x1, y1 = box
    bw, bh = x1 - x0, y1 - y0
    result.metrics.update(bbox_x=x0, bbox_y=y0, bbox_w=bw, bbox_h=bh)
    nominal = min(target_h / bh, 896 / bw)
    if nominal > 1.25:
        result.warn("UPSCALE", f"Required scale {nominal:.6f} exceeds 1.25")
    if min(x0, y0, source.width - x1, source.height - y1) < 4:
        result.warn("EDGE_CUT", "Source foreground bbox is less than 4px from an edge")
    if bw * (target_h / bh) > 896:
        result.warn("WIDE", f"Width cap controls scaling; figure will be shorter than its {target_h}px target")
    try:
        scaled, scale, scaled_box = fit_foreground(foreground, box, height_scale)
    except AssetError as exc:
        result.warn("PLACEMENT_INVALID", str(exc))
        return result
    a, b, c, d = scaled_box
    final_w, final_h = c - a, d - b
    result.metrics.update(scale=f"{scale:.9f}", final_h=final_h)
    center_x = 512 + int(record["x_offset"] or "0")
    dx = math.floor(center_x - (a + c) / 2 + 0.5)
    dy = 1392 - d
    # No visible source pixels may be clipped, including faint alpha<=16 fringe.
    visible = alpha_bbox(scaled, threshold=0)
    if (a + dx < 64 or c + dx > 960 or b + dy < 1392 - target_h or d + dy != 1392
            or visible[0] + dx < 0 or visible[2] + dx > SIZE[0]
            or visible[1] + dy < 0 or visible[3] + dy > SIZE[1]):
        result.warn("PLACEMENT_INVALID", "x_offset or alpha fringe exceeds canvas/safe area; no clipping performed")
    if result.failed:
        return result
    composed = background if background is not None else neutral_paper()
    if record.get("portrait_kind") == "npc":
        composed = ImageEnhance.Color(composed).enhance(0.45)
    shadow = Image.new("RGBA", SIZE)
    draw = ImageDraw.Draw(shadow)
    half_width = final_w * 0.6 / 2
    draw.ellipse((center_x - half_width, 1372, center_x + half_width, 1412),
                 fill=(0, 0, 0, round(255 * 0.35)))
    composed = Image.alpha_composite(composed, shadow.filter(ImageFilter.GaussianBlur(12)))
    # Only transparent padding may fall off canvas; the visible bbox was checked.
    composed.alpha_composite(scaled, dest=(dx, dy))
    # Only the placed character mask: no scenery, cast shadow or SSR effects.
    placed = Image.new("RGBA", SIZE)
    placed.alpha_composite(scaled, dest=(dx, dy))
    result.silhouette = placed.getchannel("A").point(lambda value: 255 if value > 16 else 0)
    if fx is not None:
        composed = screen_blend(composed, fx)
    result.preview = composed
    return result


def save_portrait(root: Path, result: Result) -> None:
    folder = root / "assets/characters" / result.record["id"]
    folder.mkdir(parents=True, exist_ok=True)
    result.preview.save(folder / "full.png", compress_level=9)
    for name, dimensions in DERIVATIVES.items():
        result.preview.resize(dimensions, Image.Resampling.LANCZOS).convert("RGB").save(
            folder / f"{name}.webp", quality=85, method=6, exact=True)


def draw_dashed_line(draw, x, top, bottom):
    for y in range(top, bottom, 16):
        draw.line((x, y, x, min(y + 8, bottom)), fill="#93928c", width=2)


def name_font(size: int):
    """Use a local CJK font for names when available; keep reports portable."""
    for path, index in (
        ("/System/Library/Fonts/Supplemental/Songti.ttc", 1),
        ("/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc", 0),
    ):
        try:
            return ImageFont.truetype(path, size, index=index)
        except OSError:
            pass
    return ImageFont.load_default(size=size)


def contact_sheet(results: list[Result]) -> Image.Image:
    columns = min(6, len(results))
    cell_w, cell_h, gap, margin, header = 400, 752, 20, 24, 116
    rows = math.ceil(len(results) / columns)
    sheet = Image.new("RGB", (2 * margin + columns * cell_w + (columns - 1) * gap,
                              header + rows * (cell_h + gap) + margin), "#EDE3CC")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=18)
    title = ImageFont.load_default(size=28)
    draw.text((margin, 12), "PORTRAIT PIPELINE / INSPECTION SHEET", font=title, fill="#1E1915")
    rendered = sum(r.preview is not None for r in results)
    draw.text((margin, 47), f"Listed: {len(results)}   Rendered: {rendered}   Missing/invalid: {len(results) - rendered}",
              font=font, fill="#A8261B")
    draw.text((margin, 75), "CYAN: head 6%   RED: feet 90.6%   DASHED: left/right 64px safe margins",
              font=font, fill="#4A4038")
    for index, result in enumerate(results):
        x = margin + index % columns * (cell_w + gap)
        y = header + index // columns * (cell_h + gap)
        if result.preview is not None:
            tile = result.preview.resize((400, 600), Image.Resampling.LANCZOS).convert("RGB")
        else:
            tile = Image.new("RGB", (400, 600), "#D6D5D1")
            tile_draw = ImageDraw.Draw(tile)
            tile_draw.line((35, 160, 365, 440), fill="#B7AAA0", width=2)
            tile_draw.line((365, 160, 35, 440), fill="#B7AAA0", width=2)
            label = "SOURCE MISSING" if "SRC_MISSING" in result.warnings else "BUILD ERROR"
            tile_draw.rectangle((40, 274, 360, 328), fill="#D6D5D1")
            tile_draw.text((200, 300), label, font=title, fill="#A8261B", anchor="mm")
        sheet.paste(tile, (x, y))
        draw.line((x, y + 36, x + 399, y + 36), fill="#00CCD2", width=2)
        baseline = round(600 * 0.906)
        draw.line((x, y + baseline, x + 399, y + baseline), fill="#DA302B", width=2)
        for offset in (25, 375):
            draw_dashed_line(draw, x + offset, y, y + 599)
        draw.text((x, y + 608), result.record.get("name", result.record["id"]),
                  font=name_font(24), fill="#1E1915")
        draw.text((x, y + 640), result.record["id"], font=font, fill="#4A4038")
        codes = "; ".join(result.warnings) or "OK"
        for line_no, line in enumerate(textwrap.wrap(codes, width=32, break_long_words=False)):
            draw.text((x, y + 670 + line_no * 23), line, font=font,
                      fill="#A8261B" if result.warnings else "#41643D")
    return sheet


def silhouette_groups(results: list[Result]) -> list[tuple[str, list[Result]]]:
    """Group once per character; dual-faction Qing-era cards join the Qing row."""
    taiping, qing = [], []
    for result in results:
        faction = result.record.get("faction", "")
        is_taiping = faction == "taiping" or (not faction and result.record["id"].startswith("tp_"))
        (taiping if is_taiping else qing).append(result)
    return [("太平天国", taiping), ("清朝（含双阵营）", qing)]


def silhouette_sheet(results: list[Result]) -> Image.Image:
    """Two faction rows, whole-frame silhouettes, shared scale and foot baseline."""
    width, height, gap, margin, header, row_header, row_h = 160, 240, 16, 24, 100, 36, 380
    groups = silhouette_groups(results)
    columns = max((len(members) for _, members in groups), default=0)
    sheet = Image.new("RGB", (max(720, 2 * margin + columns * (width + gap) - gap),
                              header + 2 * row_h + margin), "#EDE3CC")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=12)
    draw.text((margin, 12), "人物剪影 · 按阵营两行对比", font=name_font(28), fill="#1E1915")
    draw.text((margin, 54), "仅人物与道具；无背景、投影或特效。同一缩放比例，各行独立对齐脚底。双阵营只计一次。",
              font=name_font(18), fill="#4A4038")
    for row_index, (label, members) in enumerate(groups):
        row_top = header + row_index * row_h
        draw.text((margin, row_top), f"{label} · {len(members)}人", font=name_font(22), fill="#1E1915")
        for index, result in enumerate(members):
            x, y = margin + index * (width + gap), row_top + row_header
            if result.silhouette is not None:
                mask = result.silhouette.resize((width, height), Image.Resampling.LANCZOS)
                sheet.paste((0, 0, 0), (x, y, x + width, y + height), mask)
            else:
                draw.text((x + 8, y + 114), "MISSING / INVALID", font=font, fill="#A8261B")
            draw.line((x, y + round(92 / 1536 * height), x + width - 1, y + round(92 / 1536 * height)), fill="#00CCD2")
            draw.line((x, y + round(1392 / 1536 * height), x + width - 1, y + round(1392 / 1536 * height)), fill="#DA302B")
            name = result.record.get("name", result.record["id"])
            if result.record.get("faction") == "dual":
                name += "（双）"
            draw.text((x, y + height + 7), name, font=name_font(18), fill="#1E1915")
            for line_no, line in enumerate(textwrap.wrap(result.record["id"], width=23)):
                draw.text((x, y + height + 33 + line_no * 15), line, font=font, fill="#4A4038")
            coefficient = result.metrics.get("height_scale", format(DEFAULT_HEIGHT_SCALE, ".15g"))
            draw.text((x, y + height + 70), f"height_scale={coefficient}", font=font, fill="#4A4038")
    return sheet


def write_reports(root: Path, results: list[Result], check: bool, rembg: bool,
                  report_dir: Path | None = None) -> None:
    folder = report_dir or root / "assets/reports"
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / "pipeline_report.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=REPORT_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(r.report_row() for r in results)
    contact_sheet(results).save(folder / "contact_sheet.png", compress_level=9)
    silhouette_sheet(results).save(folder / "silhouette_sheet.png", compress_level=9)
    counts = Counter(code for result in results for code in result.warnings)
    rendered = sum(r.preview is not None for r in results)
    blocked = sum(bool(BLOCKERS.intersection(r.warnings)) for r in results)
    summary = [
        "# 资产管线运行报告", "",
        f"- 模式：{'检查（只更新报告，不写入人物派生图）' if check else '构建'}。",
        f"- 去背景：{'rembg（模型推理结果需人工复核）' if rembg else '保留输入透明通道；无透明通道时仅移除与四边四连通的 CIE76 ΔE 近底色区域，并向人物边缘内侧羽化 1–2px'}。",
        f"- 人物表：本次 {len(results)} 人；成功合成 {rendered} 人；缺失或无效 {len(results) - rendered} 人。",
        f"- 阻断验收：{blocked} 人（素材错误、UPSCALE 或 EDGE_CUT）。",
        "- 未合成项只在对照表显示占位与警告，不创建虚假人物立绘；缺失输入不借用旧输出。",
        "- 对照表为 400×600 等比预览，青线=6% 头顶线，红线=90.6% 脚底线，灰虚线=左右安全边。",
        "- 剪影图按太平天国／清朝分成两行，各行按同一脚底基线排列，只显示人物（包括所持道具）；不含场景、脚下阴影或SSR特效。",
        "- 报告和对照表反映本次选中人物；可重复使用 --id 指定一批人物，顺序与参数一致。",
        f"- 本次共用背景覆盖：{results[0].record['bg_id'] if 'planned_bg_id' in results[0].record else '无，按人物表逐人读取'}；人物表原始场景不变。",
        "- 保留完整人物源画布，只做等比 Lanczos 缩放与平移；派生图由 full.png 全幅缩小。",
        "- 人物目标高度=round(1300×height_scale)，系数缺省0.96、范围0.90..1.00；脚底固定1392。宽度优先封顶896，触发WIDE时会低于目标身高。",
        "- Lanczos 边缘可能扩展1px；按实际alpha>16外框微调，常规人物final_h距目标不超过2px。",
        "- 本次失败项不会覆盖其已有派生图；已有文件不能视为本次构建成功。", "",
        "## 警告统计", "", "| 代码 | 人数 |", "|---|---:|",
    ]
    summary.extend(f"| {code} | {count} |" for code, count in sorted(counts.items()))
    if not counts:
        summary.append("| 无警告 | 0 |")
    summary += ["", "## 逐项详情", ""]
    for result in results:
        summary.append(f"- `{result.record['id']}`：{'；'.join(result.warnings) or 'OK'}")
        summary.extend(f"  - {detail}" for detail in result.details)
    (folder / "pipeline_summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", action="append", help="Build/check selected id; repeat for a batch")
    parser.add_argument("--background", help="Use one background for this run, without editing the CSV")
    parser.add_argument("--check", action="store_true", help="Write reports only, never portrait outputs")
    parser.add_argument("--rembg", action="store_true", help="Use optional rembg for opaque sources")
    parser.add_argument("--tolerance", type=float, default=12.0, help="CIE76 Delta E threshold (default: 12)")
    parser.add_argument("--root", type=Path, default=ROOT, help="Project root (also useful for isolated tests)")
    parser.add_argument("--report-dir", type=Path, help="Keep batch reports separate from the full-roster report")
    args = parser.parse_args(argv)
    if not math.isfinite(args.tolerance) or args.tolerance <= 0:
        parser.error("--tolerance must be a positive finite number")
    if args.background and not BG_PATTERN.fullmatch(args.background):
        parser.error("--background must be a valid bg_ identifier")
    root = args.root.resolve()
    try:
        records = read_records(root, args.id)
        if args.background:
            for record in records:
                record["planned_bg_id"] = record["bg_id"]
                record["bg_id"] = args.background
    except (OSError, ValueError) as exc:
        print(f"Input table error: {exc}", file=sys.stderr)
        return 2
    remover = None
    if args.rembg:
        try:
            from rembg import new_session, remove
            session = new_session()
            remover = lambda image: remove(image, session=session)
        except Exception as exc:
            print(f"Optional rembg unavailable: {exc}", file=sys.stderr)
            return 2
    results = []
    for record in records:
        result = process(root, record, args.tolerance, remover)
        if result.preview is not None and not args.check:
            save_portrait(root, result)
        # Retain only the card preview for the sheet; full images can be large.
        if result.preview is not None:
            result.preview = result.preview.resize(DERIVATIVES["card"], Image.Resampling.LANCZOS)
        if result.silhouette is not None:
            result.silhouette = result.silhouette.resize(DERIVATIVES["mini"], Image.Resampling.LANCZOS)
        results.append(result)
        print(f"{record['id']}: {';'.join(result.warnings) or 'OK'}")
    write_reports(root, results, args.check, args.rembg, args.report_dir)
    rendered = sum(r.preview is not None for r in results)
    blocked = sum(bool(BLOCKERS.intersection(r.warnings)) for r in results)
    print(f"Listed={len(results)} Rendered={rendered} Blocked={blocked}")
    print(f"Reports: {args.report_dir or root / 'assets/reports'}")
    return 1 if blocked else 0


if __name__ == "__main__":
    raise SystemExit(main())
