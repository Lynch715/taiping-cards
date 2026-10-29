#!/usr/bin/env python3
"""Matched ablations for each4-star exclusive and conditional monarch choices."""
import argparse,hashlib,json,math,statistics
from rng import Mulberry32
from collections import Counter
from pathlib import Path
from battle_sim import Data,Battle,ROOT,pools,sample_lord,rate,norm

def fingerprints(data):
 return {n:hashlib.sha256((data.directory/n).read_bytes()).hexdigest() for n in ['heroes.csv','skills.csv','bonds.csv','equipment.csv','equipment_sets.csv','exclusive_equipment.csv']}

def paired_delta(a,b):
 # Each entry is already the mean of an attack/defence pair.
 ds=[y-x for x,y in zip(a,b)];value=statistics.mean(ds)
 se=statistics.stdev(ds)/math.sqrt(len(ds)) if len(ds)>1 else 0
 return dict(delta=value,paired_normal95=[max(-1,value-1.96*se),min(1,value+1.96*se)],pairs=len(ds))

def pair(data,left,right,lords,camps,terrain,seed,focal=None,arm='bare',stars=4,gear_set=None):
 out=[]
 for flip in [0,1]:
  rosters=[right,left] if flip else [left,right];kings=tuple(reversed(lords)) if flip else lords;fac=tuple(reversed(camps)) if flip else camps
  ground={'攻城':'守城','守城':'攻城'}.get(terrain,terrain) if flip else terrain
  owners={(flip,focal)} if arm!='bare' and focal else set()
  result=Battle(data,rosters,kings,fac,ground,stars=stars,seed=seed,gear_set=gear_set,
    exclusive_owners=owners,exclusive_effects=arm!='stats').run()
  out.append(int(result['winner']==flip))
 return statistics.mean(out)

def exclusive_diagnostics(data,n=100,duels=100,seed=20262801):
 rows=[];games=0;terrains=['陆战','水战','攻城','守城']
 for ident,e in data.exclusives.items():
  h=data.heroes[ident];rng=Mulberry32(f'{seed}:{ident}');values={k:[] for k in ['bare','stats','full']}
  camps=['taiping','qing'] if h['faction']=='dual' else [h['faction']]
  for i in range(n):
   camp=camps[i%len(camps)];other='qing' if camp=='taiping' else 'taiping'
   own_pool=[x for x in pools(data,camp) if x!=ident]
   if h['position']=='君主':left=rng.sample(own_pool,5);lord=ident
   else:left=rng.sample(own_pool,4)+[ident];rng.shuffle(left);lord=sample_lord(data,rng,camp)
   right=rng.sample(pools(data,other),5);kings=(lord,sample_lord(data,rng,other));ground=rng.choice(terrains);game_seed=rng.randrange(2**31)
   for arm in values:values[arm].append(pair(data,left,right,kings,(camp,other),ground,game_seed,ident,arm));games+=2
  row=dict(id=ident,name=h['name'],exclusive_id=e['exclusive_id'],equipment=e['name'],team_bare_rate=statistics.mean(values['bare']),team_stats_rate=statistics.mean(values['stats']),team_full_rate=statistics.mean(values['full']),
   total_lift=paired_delta(values['bare'],values['full']),stat_lift=paired_delta(values['bare'],values['stats']),skill_lift=paired_delta(values['stats'],values['full']),team_pairs=n)
  if h['position']!='君主' and duels:
   values={k:[] for k in ['bare','full']}
   for i in range(duels):
    camp=camps[i%len(camps)];other='qing' if camp=='taiping' else 'taiping';foe=rng.choice(pools(data,other));game_seed=rng.randrange(2**31)
    for arm in values:values[arm].append(pair(data,[ident],[foe],(None,None),(camp,other),'陆战',game_seed,ident,arm));games+=2
   row['duel']={'bare_rate':statistics.mean(values['bare']),'full_rate':statistics.mean(values['full']),**paired_delta(values['bare'],values['full'])}
  else:row['duel']=None
  rows.append(row)
 return dict(seed=seed,n=n,duels=duels,total_games=games,input_sha256=fingerprints(data),rows=sorted(rows,key=lambda r:-r['total_lift']['delta']),method='4star all actors, matched same roster/positions/terrain/seed; only focal owner equips. bare/stats-only/full decomposition; dual heroes alternate camps; monarch uses team win rate, cannot duel.')

def monarch_choices(data,formations=100,opponents=8,seed=20262802,stars=3,gear_set=None):
 rng=Mulberry32(seed);out={};games=0;terrains=['陆战','水战','攻城','守城']
 for camp in ['taiping','qing']:
  other='qing' if camp=='taiping' else 'taiping';kings=pools(data,camp,lords=True);counts=Counter();rosters=[]
  for i in range(formations):
   left=rng.sample(pools(data,camp),5);fixtures=[]
   for _ in range(opponents):fixtures.append((rng.sample(pools(data,other),5),sample_lord(data,rng,other),rng.choice(terrains),rng.randrange(2**31)))
   scores={}
   for lord in kings:
    wins=[]
    for right,enemy_lord,terrain,game_seed in fixtures:
     wins.append(pair(data,left,right,(lord,enemy_lord),(camp,other),terrain,game_seed,stars=stars,gear_set=gear_set));games+=2
    scores[lord]=statistics.mean(wins)
   best=max(scores.values());chosen=[k for k in kings if scores[k]==best]
   for k in chosen:counts[k]+=1/len(chosen)
   rosters.append(dict(heroes=left,rates=scores,chosen=chosen))
  out[camp]=dict(formations=formations,opponents=opponents,cards={k:{'selected':counts[k],'rate':counts[k]/formations} for k in kings},rows=rosters)
 return dict(seed=seed,stars=stars,equipment_set=gear_set,total_games=games,input_sha256=fingerprints(data),factions=out,method='Counterfactual choice: same combat formation faces same mirrored opponents/terrains/seeds with every own-camp legal monarch. Highest empirical win rate selected; exact ties split one vote. Never use uniform input sampling as selection rate.')

# Curated identity effects: coefficients vs flat-valued/nonpercentage mechanisms.
SIGNATURES={
 'tp_hong_xiuquan':('p','天王诏旨','hong_all_faith',1), 'tp_hong_tianguifu':('p','幼主继位','aura:defense',0),
 'tp_yang_xiuqing':('a','天父下凡','buff:attack',0),'tp_xiao_chaogui':('p','西王冲锋','target_high_bonus',1),
 'tp_feng_yunshan':('p','拜上帝会','death_attack_all',0),'tp_wei_changhui':('p','阴鸷','target_low_crit',1),
 'tp_shi_dakai':('p','孤军远征','no_bond_risk',0),'tp_chen_yucheng':('p','少年锐气','flat',0),
 'tp_li_xiucheng':('p','苦撑危局','low_alive_defense',1),'tp_hong_rengan':('p','总理朝政','lord_amplify',0),
 'tp_li_shixian':('p','浙江转战','end_heal_below',1),'tp_yang_fuqing':('a','辅王驰援','heal',0),
 'tp_lin_fengxiang':('p','孤军深入','missing_damage',0),'tp_li_kaifang':('p','坚忍','flat',0),
 'tp_luo_dagang':('p','天地会旧部','combo_chance',0),'tp_hu_yihuang':('p','攻坚','siege_damage',0),
 'tp_qin_rigang':('p','先登','first_damage',0),'tp_zeng_tianyang':('p','老当益壮','low_hp_attack',1),
 'tp_lin_qirong':('p','坚城','aura:taken',0),'tp_tan_shaoguang':('p','宁死不降','low_hp_attack',1),
 'tp_huang_wenjin':('p','嗜战','kill_heal',0),'tp_wang_haiyang':('p','机动','flat',0),
 'tp_lai_wenguang':('p','流动作战','flat',0),'tp_lindley':('p','太平之友','rengan_attack',0),
 'tp_hong_xuanjiao':('p','巾帼','aura:crit',0),'tp_su_sanniang':('p','轻骑','aura:taken',0),
 'qing_zeng_guofan':('p','屡败屡战','death_aura',0),'qing_zeng_guoquan':('p','围城断援','enemy_healing_reduction',0),
 'qing_hu_linyi':('p','湖北筹饷','flat',0),'qing_zuo_zongtang':('p','今亮','active_damage',0),
 'qing_luo_zenan':('p','书生带兵','flat',0),'qing_li_xubin':('p','孤军冒进','aura:attack',0),
 'qing_taqibu':('p','满汉合营','flat',0),'qing_bao_chao':('p','悍将','hit_attack_every',1),
 'qing_duolonga':('p','骑射','rear_chance',0),'qing_jiang_zhongyuan':('p','楚勇','flat',0),
 'qing_peng_yulin':('p','水师统帅','aura:attack',0),'qing_yang_zaifu':('p','行伍出身','critical_reduction',0),
 'qing_li_hongzhang':('p','淮军统帅','flat',0),'qing_cheng_xueqi':('p','降将','random_stat',0),
 'qing_liu_mingchuan':('p','铭字营','nth_basic',1),'qing_zhang_shusheng':('p','稳健','aura:taken',0),
 'qing_guo_songlin':('p','快马','flat',0),'qing_senggelinqin':('p','铁骑冲阵','aura:attack',0),
 'qing_xiang_rong':('p','宿将','aura:defense',0),'qing_he_chun':('p','督阵','aura:attack',0),
 'qing_zhang_guoliang':('p','豪强','high_hp_attack',1),'qing_shengbao':('p','追剿','named_damage',1),
 'qing_ward':('p','冒险家','aura:crit_damage',0),'qing_gordon':('p','工兵军官','siege_attack_aura',0),
 'qing_burgevine':('p','倒戈','assigned_taiping_attack',0),'qing_luo_bingzhang':('p','川督','named_damage',1),
 'qing_xianfeng':('p','起用团练','aura:attack',0),'qing_cixi':('p','垂帘听政','aura:defense',0),
 'qing_prince_gong':('p','总理衙门','aura:attack',0),'qing_sushun':('p','重用汉臣','aura:attack',0),
}
R_PERCENT_FIELDS={'first_damage':[0],'siege_damage':[0],'healing_taken':[0],'kill_heal':[0],'end_heal':[0],
 'low_hp_attack':[1],'named_damage':[1],'assigned_taiping_attack':[0]}

def constraint_audit(data):
 caps=[];signatures=[]
 for h in data.heroes.values():
  for col in ['active','passive']:
   ast=data.cache[h[col]]
   if h['rarity']!='R':continue
   for o in ast.get('ops',[]):
    if o['kind'] in {'heal','shield'} or (o['kind']=='buff' and not o['flat']):
     caps.append(dict(id=h['id'],skill_id=h[col],effect=o['kind']+':'+o.get('stat',''),percent=abs(o['value'])*100,valid=abs(o['value'])<=.25+1e-9))
   for o in ast.get('auras',[]):
    if not o['flat']:caps.append(dict(id=h['id'],skill_id=h[col],effect=o['stat'],percent=abs(o['value'])*100,valid=abs(o['value'])<=.25+1e-9))
   for key,indices in R_PERCENT_FIELDS.items():
    if key in ast.get('features',{}):
     for i in indices:
      value=abs(ast['features'][key][i]);caps.append(dict(id=h['id'],skill_id=h[col],effect=key,percent=value,valid=value<=25+1e-9))
 for ident,(col,name,key,index) in SIGNATURES.items():
  h=data.heroes[ident];ast=data.cache[h['active' if col=='a' else 'passive']];value=None
  if key.startswith('aura:'):
   found=[abs(a['value'])*100 for a in ast.get('auras',[]) if a['stat']==key[5:] and not a['flat']];value=found[0] if found else None
  elif key.startswith('buff:'):
   found=[abs(a['value'])*100 for a in ast.get('ops',[]) if a['kind']=='buff' and a['stat']==key[5:]];value=found[0] if found else None
  elif key=='heal':value=next(o['value']*100 for o in ast['ops'] if o['kind']=='heal')
  elif key!='flat':
   feature=ast.get('features',{}).get(key)
   if feature:value=abs(feature[index])
   # Earlier coefficients used simpler unconditional forms.
   elif key=='hong_all_faith' and 'hong_all' in ast.get('features',{}):value=ast['features']['hong_all'][0]
   elif key=='no_bond_risk' and 'no_bond_all' in ast.get('features',{}):value=ast['features']['no_bond_all'][0]
   elif key=='end_heal_below' and 'end_heal' in ast.get('features',{}):value=ast['features']['end_heal'][0]
   elif key=='hit_attack_every' and 'hit_attack' in ast.get('features',{}):value=ast['features']['hit_attack'][0]
  signatures.append(dict(id=ident,name=h['name'],mechanism=name,percent=value,nonpercentage=key=='flat',valid=key=='flat' or value is not None and value>=10-1e-9))
 sets=[dict(set=k,valid=not any(x in r['bonus2']+r['bonus4'] for x in ['信仰','猜忌','粮饷'])) for k,r in data.sets.items()]
 return dict(r_effects=caps,signatures=signatures,sets=sets,budgets=data.budget(),all_valid=all(r['valid'] for r in caps+signatures+sets+data.budget()))

def main():
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['exclusives','monarchs','constraints']);p.add_argument('--data-dir',type=Path,default=ROOT/'data');p.add_argument('--n',type=int,default=100);p.add_argument('--duels',type=int,default=100);p.add_argument('--opponents',type=int,default=8);p.add_argument('--seed',type=int,default=20262801);p.add_argument('--output',type=Path,required=True);a=p.parse_args();d=Data(a.data_dir)
 r=exclusive_diagnostics(d,a.n,a.duels,a.seed) if a.mode=='exclusives' else monarch_choices(d,a.n,a.opponents,a.seed) if a.mode=='monarchs' else constraint_audit(d)
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'mode':a.mode,'games':r.get('total_games'),'all_valid':r.get('all_valid')},ensure_ascii=False))
if __name__=='__main__':main()
