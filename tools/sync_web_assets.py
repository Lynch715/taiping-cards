#!/usr/bin/env python3
"""Derive quality-85 full WebP from approved PNG masters; copy only WebP to the web app."""
import argparse,csv,hashlib,json,shutil
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
rows=list(csv.DictReader((ROOT/'data/characters.csv').open(encoding='utf-8-sig')))
if (ROOT/'data/npc_portraits.csv').exists():
 rows+=list(csv.DictReader((ROOT/'data/npc_portraits.csv').open(encoding='utf-8-sig')))
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--id',action='append')
parser.add_argument('--report-dir',type=Path,default=ROOT/'assets/reports/web_chapter2')
args=parser.parse_args()
if args.id:
 unknown=set(args.id)-{r['id'] for r in rows}
 if unknown:parser.error('Unknown ids: '+', '.join(sorted(unknown)))
 rows=[r for r in rows if r['id'] in args.id]
report=[]
for row in rows:
 folder=ROOT/'assets/characters'/row['id'];master=folder/'full.png'
 before=hashlib.sha256(master.read_bytes()).hexdigest()
 with Image.open(master) as im:
  if im.size!=(1024,1536):raise ValueError(f'{master}: invalid master size')
  im.convert('RGB').save(folder/'full.webp',quality=85,method=6,exact=True)
 target=ROOT/'app/public/assets/characters'/row['id'];target.mkdir(parents=True,exist_ok=True)
 for name in ['full','card','mini','thumb']:shutil.copy2(folder/f'{name}.webp',target/f'{name}.webp')
 for png in target.glob('*.png'):png.unlink()
 assert hashlib.sha256(master.read_bytes()).hexdigest()==before
 report.append({'id':row['id'],'master_sha256':before,'full_webp_bytes':(folder/'full.webp').stat().st_size,'quality':85,'width':1024,'height':1536})
r=args.report_dir;r.mkdir(exist_ok=True,parents=True);(r/'webp_derivatives.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'portraits':len(report),'full_webp_bytes':sum(x['full_webp_bytes'] for x in report),'master_png_unchanged':True}))
