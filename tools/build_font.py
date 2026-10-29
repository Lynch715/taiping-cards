#!/usr/bin/env python3
"""Offline Noto Serif SC subset, preserving current UI and CSV name glyphs."""
import argparse,json,hashlib
from pathlib import Path
from fontTools import subset
from fontTools.ttLib import TTFont
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('--report',type=Path,default=ROOT/'assets/reports/m1/font_coverage.json');a=p.parse_args()
text=''.join(p.read_text() for p in (ROOT/'data').glob('*.csv'))+''.join(p.read_text() for p in (ROOT/'app/src').rglob('*') if p.suffix in {'.ts','.tsx'})+'0123456789捷败殁离−×★☆呤唎张国梁樑一二三四五六七八九十当前回合继续暂停下一关'
chars=set(map(ord,text));font=TTFont(a.source);missing=chars-set(font.getBestCmap());opts=subset.Options();opts.flavor='woff2';opts.name_IDs=['*'];ss=subset.Subsetter(options=opts);ss.populate(unicodes=chars);ss.subset(font);font.flavor='woff2';out=ROOT/'app/public/fonts/NotoSerifSC-M1.woff2';font.save(out)
report={'family':'Noto Serif SC','source':'https://github.com/notofonts/noto-cjk','characters':len(chars),'codepoints':sorted(chars),'missing_printable':[chr(c) for c in sorted(missing) if chr(c).isprintable()],'woff2_sha256':hashlib.sha256(out.read_bytes()).hexdigest()}
a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');assert not report['missing_printable'];print(out.stat().st_size)
