#!/usr/bin/env python3
"""Build56 formal cards twice, preserving39 approved portraits and all raw art."""
import contextlib,csv,hashlib,io,json
from pathlib import Path
from PIL import Image
import build_portraits as pipeline
ROOT=Path(__file__).resolve().parents[1];REPORT=ROOT/'assets/reports/r_full_body_v1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 records=pipeline.read_records(ROOT,None);assert len(records)==56
 manifest=json.loads((REPORT/'generation_manifest.json').read_text());assert len(manifest['results'])==17 and all(not r['technical_issues'] for r in manifest['results'])
 protected=json.loads((REPORT/'protected_input_sha256.json').read_text());allowed={f'assets/reports/{n}' for n in ['contact_sheet.png','silhouette_sheet.png','pipeline_report.csv','pipeline_summary.md']}
 assert all(sha(ROOT/p)==h for p,h in protected.items() if p not in allowed),'Protected art or data changed'
 outputs={}
 for attempt in [1,2]:
  log=io.StringIO()
  with contextlib.redirect_stdout(log):code=pipeline.main(['--root',str(ROOT)])
  (REPORT/f'pipeline_run_{attempt}.log').write_text(log.getvalue());assert code==0,log.getvalue()
  report_rows=list(csv.DictReader((ROOT/'assets/reports/pipeline_report.csv').open(encoding='utf-8-sig')))
  assert len(report_rows)==56 and all(not r['warnings'] for r in report_rows),[(r['id'],r['warnings']) for r in report_rows if r['warnings']]
  current={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'assets/characters').glob('*/*') if p.name in ['full.png','card.webp','mini.webp','thumb.webp']}
  assert len(current)==224
  current.update({p:sha(ROOT/p) for p in allowed})
  if attempt==1:outputs=current
  else:assert outputs==current,'Repeated builds differ'
  print(f'Pass{attempt}:56 cards,224 derived outputs,zero warnings',flush=True)
 assert all(sha(ROOT/p)==h for p,h in protected.items() if p not in allowed),'Approved original39 portrait bytes changed'
 checks=[]
 for row in records:
  ident=row['id'];source=ROOT/f'assets/raw/characters/{ident}.png'
  with Image.open(source) as im:
   assert im.mode=='RGBA' and im.size==pipeline.SIZE
   box=pipeline.alpha_bbox(im);_,scale,fitted=pipeline.fit_foreground(im,box,row['height_scale']);final_h=fitted[3]-fitted[1];target=pipeline.target_height(row['height_scale'])
   assert min(box[0],box[1],1024-box[2],1536-box[3])>=4 and scale<=1.25 and abs(final_h-target)<=2
  for filename,size in [('full.png',pipeline.SIZE)]+[(k+'.webp',v) for k,v in pipeline.DERIVATIVES.items()]:
   with Image.open(ROOT/f'assets/characters/{ident}/{filename}') as im:assert im.size==size and im.width*3==im.height*2
  checks.append(dict(id=ident,name=row['name'],faction=row['faction'],rarity=row['rarity_draft'],height_scale=float(row['height_scale']),target_h=target,final_h=final_h,bottom_y=1392,scale=scale,source_sha256=sha(source)))
 groups=pipeline.silhouette_groups([pipeline.Result(r) for r in records]);assert len(groups)==2
 val=dict(stage='ALL56_GENERATED_PENDING_HUMAN_ART_REVIEW',roster_count=56,rarities={k:sum(r['rarity_draft']==k for r in records) for k in ['SSR','SR','R']},silhouette_rows={k:len(v) for k,v in groups},new_native_cutouts=17,derived_outputs=224,pipeline_warnings=[],repeat_hashes_match=len(outputs),protected_original_files_verified=len(protected)-len(allowed),original39_art_preserved=True,reference_policy='Own approved head +2faceless swatches +own assigned background only',checks=checks)
 (REPORT/'roster_validation.json').write_text(json.dumps(val,ensure_ascii=False,indent=2)+'\n');(REPORT/'repeat_output_sha256.json').write_text(json.dumps(outputs,ensure_ascii=False,indent=2)+'\n')
 print('Validated56 and preserved original39; repeated hashes',len(outputs),'faction rows',val['silhouette_rows'])
if __name__=='__main__':main()
