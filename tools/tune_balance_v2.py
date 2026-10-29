#!/usr/bin/env python3
"""Reproducible candidate data staging; source CSVs are only promoted explicitly."""
import csv,json,shutil,sys
from pathlib import Path
from battle_sim import ROOT,Data,evaluate
from balance_diagnostics import constraint_audit
BASE=ROOT/'assets/reports/balance_v2/before/data';TRIALS=ROOT/'assets/reports/balance_v2/trials'
MANDATORY_SKILLS={
 'sk_tp_hong_xiuquan_edict':'信仰达到 80 时，我方太平天国武将全属性 +10%，另按洪秀全智每 10 点再 +0.3%；信仰上限 +20。杨秀清在场时，猜忌每回合 +5。',
 'sk_tp_hong_tianguifu_edict':'我方太平天国武将防御 +10%；开场信仰 +10。',
 'sk_tp_shi_dakai_p':'我方未激活任何正面羁绊时，自身全属性 +20%、受到伤害 +20%；生命首次低于 30% 时回复 15%，并免疫眩晕与沉默 1 回合（大渡河绝境，每场 1 次）。',
 'sk_qing_senggelinqin_p':'我方骑兵攻击 +12%；自身对步兵伤害额外 +15%。',
 'sk_qing_zeng_guofan_p':'我方每有 1 名武将阵亡，我方全体防御 +10%、攻击 +10%（最多 2 层）；粮饷获取 +20%。',
 'sk_tp_yang_xiuqing_p':'战斗开始时我方全体怒气 +15；猜忌每 40 点，自身攻击 +10%。',
 'sk_tp_li_shixian_p':'生命低于 50% 时，每回合结束回复自身 10%。',
 'sk_qing_bao_chao_p':'每受到 2 次攻击，自身攻击 +10%（最多 3 层）。',
 'sk_tp_qin_rigang_p':'自身第一次行动伤害 +25%。',
 'sk_tp_lin_qirong_a':'自身嘲讽并防御 +25%，持续 2 回合。',
 'sk_qing_zhang_shusheng_a':'我方全体防御 +25%，持续 2 回合。',
 'sk_qing_xiang_rong_a':'我方前排获得护盾 25%，持续 2 回合。',
 'sk_qing_he_chun_a':'敌方前排防御 −25%，持续 2 回合。',
 'sk_qing_shengbao_p':'对林凤祥、李开芳伤害 +25%。',
 'sk_qing_luo_bingzhang_p':'对石达开伤害 +25%。',
}
MANDATORY_EXCLUSIVES={
 'tp_hong_xiuquan':'政令「天王诏旨」全属性加成 +10% → +15%',
 'tp_li_shixian':'「浙江转战」每回合回复 10% → 16%',
 'qing_bao_chao':'「悍将」层数上限 3 → 5',
}

def stage(name,skills=None,heroes=None,exclusives=None,sets=None,mandatory=True):
 dest=TRIALS/name/'data';dest.mkdir(parents=True,exist_ok=True)
 for p in BASE.glob('*.csv'):shutil.copy2(p,dest/p.name)
 edit_skills={**(MANDATORY_SKILLS if mandatory else {}),**(skills or {})};edit_ex={**(MANDATORY_EXCLUSIVES if mandatory else {}),**(exclusives or {})};all_changes=[]
 for filename,key,edits in [('skills.csv','skill_id',{k:{'effect':v} for k,v in edit_skills.items()}),('heroes.csv','id',heroes or {}),('exclusive_equipment.csv','hero_id',{k:({'effect':v} if isinstance(v,str) else v) for k,v in edit_ex.items()}),('equipment_sets.csv','set',sets or {})]:
  p=dest/filename
  with p.open(encoding='utf-8-sig',newline='') as f:reader=csv.DictReader(f);fields=reader.fieldnames;rows=list(reader)
  for r in rows:
   for col,value in edits.get(r[key],{}).items():
    old=r[col];r[col]=str(value)
    if old!=r[col]:all_changes.append(dict(file=filename,id=r[key],column=col,before=old,after=r[col]))
  with p.open('w',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(rows)
 d=Data(dest);audit=constraint_audit(d)
 if mandatory:assert audit['all_valid'],audit
 (dest.parent/'changes.json').write_text(json.dumps(all_changes,ensure_ascii=False,indent=2)+'\n');(dest.parent/'constraints.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
 return d

def brief(r):return {'games':r['total_games'],'duel':round(r['duel']['rate'],4),'ssr5':round(r['ssr5_vs_sr5']['rate'],4),'factions':{k:round(v['rate'],4) for k,v in r['factions'].items()},'rounds':round(r['average_full_team_rounds'],3),'incident':{k:round(v['rate'],4) for k,v in r['incident'].items()},'combat_peak':r['top_lineups']['max_appearance'],'monarchs':{f:{h:round(x['rate'],3) for h,x in v['cards'].items()} for f,v in r['monarchs'].items()}}

def run(name,d,n=500,lineups=400,opponents=6,seed=20262701):
 r=evaluate(d,n=n,lineups=lineups,opponents=opponents,seed=seed);(TRIALS/name/'metrics.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print(json.dumps(brief(r),ensure_ascii=False),flush=True);return r
if __name__=='__main__':run('01_mandatory',stage('01_mandatory'))
