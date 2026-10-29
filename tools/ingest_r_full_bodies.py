#!/usr/bin/env python3
"""Promote17 approved-identity native cutouts; reject geometry/alpha violations."""
import hashlib,json,shutil
from pathlib import Path
import numpy as np
from PIL import Image
import build_portraits as pipeline
ROOT=Path(__file__).resolve().parents[1];REPORT=ROOT/'assets/reports/r_full_body_v1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 jobs=json.loads((REPORT/'generation_plan.json').read_text())['subjects'];approved={r['id']:r for r in json.loads((ROOT/'assets/reports/r_head_approval_state.json').read_text())['heads']}
 assert len(jobs)==17 and all(r['approval_status']=='USER_APPROVED' for r in approved.values())
 protected=json.loads((REPORT/'protected_input_sha256.json').read_text())
 updated_reports={f'assets/reports/{n}' for n in ['contact_sheet.png','silhouette_sheet.png','pipeline_report.csv','pipeline_summary.md']}
 assert all(sha(ROOT/p)==h for p,h in protected.items() if p not in updated_reports),'Protected input changed'
 assert all(sha(REPORT/'before'/p)==protected[p] for p in updated_reports),'Original39 reports archive changed'
 outputs=[json.loads(p.read_text()) for p in (REPORT/'outputs').glob('*.json')];ix={r['id']:r for r in outputs};assert len(outputs)==len(ix)==17
 for folder in ['revised_outputs','final_outputs']:
  for p in (REPORT/folder).glob('*.json'):
   row=json.loads(p.read_text());row['first_draft']=ix[row['id']];ix[row['id']]=row
 outputs=list(ix.values())
 manifests=[];checks=[]
 for j in jobs:
  r=ix[j['id']];a=approved[j['id']];expected=[a['project_path'],'docs/reference/style_swatch_impasto_cloth.png','docs/reference/style_swatch_impasto_sky.png',f"assets/raw/backgrounds/{j['bg_id']}.png"]
  assert j['refs']==r['refs']==expected
  assert [sha(ROOT/p) for p in expected]==j['reference_sha256']==r['reference_sha256']
  assert a['sha256']==sha(ROOT/j['approved_head']);source=ROOT/r['project_path'];assert sha(source)==sha(Path(r['source_path']))
  issues=[];box=None;scale=None;final_h=None
  with Image.open(source) as im:
   if im.size!=pipeline.SIZE or im.mode!='RGBA':issues.append('NATIVE_FORMAT')
   else:
    alpha=np.asarray(im.getchannel('A'))
    if not (np.any(alpha==0) and np.any(alpha>240)):issues.append('NO_NATIVE_ALPHA')
    box=pipeline.alpha_bbox(im);margin=min(box[0],box[1],im.width-box[2],im.height-box[3])
    if margin<4:issues.append('EDGE_CUT')
    _,scale,fitted=pipeline.fit_foreground(im,box,j['height_scale']);final_h=fitted[3]-fitted[1]
    if scale>1.25:issues.append('UPSCALE')
    if abs(final_h-pipeline.target_height(j['height_scale']))>2:issues.append('WIDE')
  dest=ROOT/'assets/raw/characters'/f"{j['id']}.png"
  if not issues:
   if dest.exists():assert sha(dest)==sha(source),'Refuse to overwrite a different approved raw input'
   else:shutil.copy2(source,dest)
  checks.append(dict(id=j['id'],number=j['number'],name=j['name'],bbox=box,scale=scale,final_h=final_h,issues=issues,promoted=not issues))
  manifests.append({**j,**r,'raw_path':str(dest.relative_to(ROOT)),'source_sha256':sha(source),'technical_issues':issues,'head_status':'USER_APPROVED','full_body_status':'PENDING_USER_ART_REVIEW'})
 (REPORT/'source_validation.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n');(REPORT/'generation_manifest.json').write_text(json.dumps(dict(tool='built-in image_gen',stage='17_APPROVED_HEADS_TO_NATIVE_FULL_BODIES_HUMAN_ART_REVIEW_PENDING',results=manifests),ensure_ascii=False,indent=2)+'\n');(REPORT/'generation_results.json').write_text(json.dumps(dict(results=outputs),ensure_ascii=False,indent=2)+'\n')
 for c in checks:print(c['number'],c['name'],';'.join(c['issues']) or 'OK')
 return int(any(c['issues'] for c in checks))
if __name__=='__main__':raise SystemExit(main())
