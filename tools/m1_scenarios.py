"""M1 army profiles and CSV-defined stages shared by tuning and golden fixtures."""
from battle_sim import Data,Battle,ROOT,read_csv
INITIAL={'SSR':3,'SR':2,'R':1}
def assumed_level(chapter,order):
 rows=read_csv(ROOT/'data/economy_chapters.csv');end=float(rows[chapter-1]['target_level_end']);start=10 if chapter==1 else float(rows[chapter-2]['target_level_end']);return start+(end-start)*(order-1)/5

def game_data():
 d=Data()
 d.skills['npc_active']={'kind':'主动','effect':'','name':'普攻'};d.skills['npc_passive']={'kind':'被动','effect':'','name':'无'}
 for r in read_csv(ROOT/'data/enemy_units.csv'):
  h={**r,'rarity':'R','position':'前排','active':'npc_active','passive':'npc_passive','exclusive':'','tags':'杂兵'}
  for k in ['tong','wu','zhi','su']:h[k]=int(h[k])
  d.heroes[h['id']]=h
 d.compile();return d

def stage_input(d,row,formation,enemy_level=None):
 foes=row['enemies'].split(',');campaign=row['campaign'];enemy='qing' if campaign=='taiping' else 'taiping'
 own=next(r for r in read_csv(ROOT/'data/starter_cards.csv') if r['campaign']==campaign)
 lev=float(enemy_level or row['enemy_level'])
 player_level=assumed_level(int(row['chapter']),int(row['order']))
 a={'heroes':list(formation),'monarch':own['monarch'],'faction':campaign,'levels':[player_level]*5,'stars':[INITIAL[d.heroes[i]['rarity']] for i in formation]}
 b={'heroes':foes,'monarch':row['enemy_monarch'] or None,'faction':enemy,'levels':[lev]*5,'stars':[int(s) for s in row['enemy_stars'].split(';')],'exclusives':[int(s)>=4 for s in row['enemy_stars'].split(';')],'monarchStars':int(row['enemy_monarch_stars'] or 3),'monarchExclusive':int(row['enemy_monarch_stars'] or 3)>=4}
 return a,b

def run_input(d,a,b,terrain,seed,options=None,trace=True):
 options=options or {};mapping={'gearSet':'gear_set','equipmentIds':'equipment_ids','exclusiveOwners':'exclusive_owners','exclusiveEffects':'exclusive_effects','allowDuplicates':'allow_duplicates','exclusives':'use_exclusives'}
 kw={mapping.get(k,k):v for k,v in options.items()}
 if kw.get('exclusive_owners') is not None:kw['exclusive_owners']={tuple(x) for x in kw['exclusive_owners']}
 if 'gear' in a or 'gear' in b:kw['unit_gear']=[t.get('gear',[[] for _ in t['heroes']]) for t in [a,b]]
 if 'exclusives' in a or 'exclusives' in b:kw['unit_exclusives']=[t.get('exclusives',[False]*len(t['heroes'])) for t in [a,b]]
 if 'monarchStars' in a or 'monarchStars' in b:kw['lord_stars']=[t.get('monarchStars',3) for t in [a,b]]
 if 'monarchExclusive' in a or 'monarchExclusive' in b:kw['lord_exclusives']=[t.get('monarchExclusive',False) for t in [a,b]]
 return Battle(d,[a['heroes'],b['heroes']],lords=(a.get('monarch'),b.get('monarch')),assigned=(a['faction'],b['faction']),terrain=terrain,seed=seed,trace=trace,unit_levels=[a['levels'],b['levels']] if 'levels'in a and 'levels'in b else None,unit_stars=[a['stars'],b['stars']] if 'stars'in a and 'stars'in b else None,**kw).run()
