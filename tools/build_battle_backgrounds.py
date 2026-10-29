#!/usr/bin/env python3
"""Normalize uncropped terrain PNGs and encode WebP (default Q80, --quality override)."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / 'assets/raw/battle'

def build(ident, quality=80):
    source = SOURCES / f'{ident}.png'
    with Image.open(source) as image:
        original = image.size
        # Terrain only: normalize the entire canvas; no image content is cropped.
        image = image.convert('RGB').resize((1080, 1350), Image.Resampling.LANCZOS)
    target = ROOT / 'assets/battle'
    public = ROOT / 'app/public/assets/battle'
    target.mkdir(parents=True, exist_ok=True)
    public.mkdir(parents=True, exist_ok=True)
    image.save(target / f'{ident}.png', compress_level=9)
    # Fixed spatial noise shaping preserves broad paint strokes
    # while keeping this intentionally quiet game board below the byte budget.
    subprocess.run(['cwebp', '-quiet', '-q', str(quality), '-m', '6', '-sns', '40',
                    str(target / f'{ident}.png'), '-o', str(target / f'{ident}.webp')], check=True)
    data = (target / f'{ident}.webp').read_bytes()
    if len(data) > 250_000:
        raise ValueError(f'{ident}: WebP exceeds 250KB: {len(data)}')
    (public / f'{ident}.webp').write_bytes(data)
    return dict(id=ident, source_size=original, output_size=[1080,1350],
                normalization='whole-canvas resize; no crop; terrain aspect normalized',
                quality=quality, encoder=f'cwebp -q {quality} -m 6 -sns 40',
                webp_bytes=len(data), sha256=hashlib.sha256(data).hexdigest())

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--id', action='append', choices=['bg_battle_land','bg_battle_siege','bg_battle_defend','bg_battle_river'], required=True)
    parser.add_argument('--report-dir', type=Path, required=True)
    parser.add_argument('--quality', type=int, choices=range(1,101), default=80)
    args = parser.parse_args()
    report = [build(ident,args.quality) for ident in dict.fromkeys(args.id)]
    args.report_dir.mkdir(parents=True, exist_ok=True)
    (args.report_dir/'battle_backgrounds.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))
