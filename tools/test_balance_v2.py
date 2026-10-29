"""V2 regressions for new CSV effects, genuine controls, and matched diagnostics."""
import copy,unittest,os
from pathlib import Path
from battle_sim import Data,Battle,pools,top_weights,evaluate
from tune_balance_v2 import MANDATORY_SKILLS,MANDATORY_EXCLUSIVES
from balance_diagnostics import constraint_audit

def candidate():
 d=Data()
 for k,v in MANDATORY_SKILLS.items():d.skills[k]['effect']=v
 for k,v in MANDATORY_EXCLUSIVES.items():d.exclusives[k]['effect']=v
 d.compile();return d

class V2Tests(unittest.TestCase):
 def test_promoted_data_all_v2_constraints_and_compound_signatures(self):
  d=Data(Path(os.environ['BATTLE_TEST_DATA_DIR'])) if 'BATTLE_TEST_DATA_DIR' in os.environ else Data();self.assertTrue(constraint_audit(d)['all_valid'])
  p=d.cache['sk_qing_zeng_guofan_p']['features']['death_aura'];self.assertGreaterEqual(min(p[:2]),10)
  a=d.cache['sk_qing_senggelinqin_p'];self.assertTrue(all(o['value']>=.1 for o in a['auras'] if o['stat']=='attack'));self.assertGreaterEqual(a['features']['infantry_damage'][0],10)
 def test_new_roster_is_formal_five_vs_five(self):
  d=Data();self.assertEqual(d.heroes['tp_su_sanniang']['troop'],'骑')
  self.assertEqual(len(pools(d,'taiping','SSR')),6);self.assertEqual(len(pools(d,'qing','SSR')),6)
 def test_ordinary_cap_does_not_cap_damage_or_hp_trigger(self):
  d=candidate();a=constraint_audit(d);self.assertTrue(a['all_valid']);self.assertEqual(len(a['signatures']),56)
  self.assertNotIn('伤害系数',[r['effect'] for r in a['r_effects']])
  d.skills['sk_qing_he_chun_a']['effect']='敌方前排防御 −26%，持续 2 回合。';d.compile();self.assertFalse(constraint_audit(d)['all_valid'])
 def test_resource_free_four_piece_kill_rage_attack_same_for_both_camps(self):
  d=Data()
  for own,foes,camp in [('tp_qin_rigang',['qing_guo_songlin','qing_he_chun','qing_zhang_shusheng','qing_xiang_rong'],'taiping'),('qing_guo_songlin',['tp_qin_rigang','tp_hu_yihuang','tp_huang_wenjin','tp_wang_haiyang'],'qing')]:
   b=Battle(d,[[own],foes],assigned=(camp,'qing' if camp=='taiping' else 'taiping'),gear_set='圣兵');u=b.teams[0].actors[0];faith=b.teams[0].faith;b.round=1
   for v in b.teams[1].actors:u.rage=0;b.apply_loss(v,v.hp+1,u);self.assertEqual(u.rage,20)
   self.assertEqual(u.kills,4);buff=next(x for x in u.buffs if x.source=='set:kill_attack');self.assertAlmostEqual(buff.value,.15);self.assertEqual(b.teams[0].faith,faith)
 def test_yongying_round_heal_both_factions(self):
  for own in ['tp_qin_rigang','qing_guo_songlin']:
   d=Data();d.sets['勇营']['bonus4']='每回合开始时回复自身 3%';d.compile();b=Battle(d,[[own],['tp_hu_yihuang']],gear_set='勇营');u=b.teams[0].actors[0];u.hp=u.max_hp*.5;b.round=1;b.step_start();self.assertAlmostEqual(u.hp/u.max_hp,.53)
 def test_periodic_yongying_preserves_three_percent_and_cadence(self):
  d=Data();d.sets['勇营']['bonus4']='每第 3 回合开始时回复自身 3%';d.compile()
  for own in ['tp_qin_rigang','qing_guo_songlin']:
   b=Battle(d,[[own],['tp_hu_yihuang']],gear_set='勇营');u=b.teams[0].actors[0];u.hp=u.max_hp*.5
   for r in range(1,7):
    b.round=r;b.step_start();self.assertAlmostEqual(u.hp/u.max_hp,.5+.03*(r//3))
 def test_xiao_death_gives_team_rage(self):
  b=Battle(Data(),[['tp_xiao_chaogui','tp_yang_fuqing','tp_qin_rigang'],['qing_guo_songlin']]);u,*rest=b.teams[0].actors
  for v in rest:v.rage=0
  b.apply_loss(u,u.hp+1,b.teams[1].actors[0]);self.assertEqual([v.rage for v in rest],[30,30])
 def test_rengan_policy_but_not_decree_amplification(self):
  b=Battle(candidate(),[['tp_hong_rengan'],['qing_guo_songlin']],lords=('tp_hong_xiuquan',None));self.assertEqual(b.teams[0].faith_cap,130)
  b.teams[0].faith=0;b.round=3;b.step_start();self.assertEqual(b.teams[0].faith,40)
 def test_faith_condition_rescales_max_hp_without_free_healing(self):
  b=Battle(candidate(),[['tp_hong_rengan','tp_yang_xiuqing','tp_feng_yunshan'],['qing_guo_songlin']],lords=('tp_hong_xiuquan',None));u=b.teams[0].actors[1];base=u.max_hp;u.hp=base*.5
  b.resource(0,'信仰',30);self.assertGreater(b.teams[0].faith,80);self.assertAlmostEqual(u.max_hp/base,1.1905);self.assertAlmostEqual(u.hp/u.max_hp,.5)
  b.resource(0,'信仰',-100);self.assertAlmostEqual(u.max_hp,base);self.assertAlmostEqual(u.hp/u.max_hp,.5)
 def test_rengan_death_removes_amplification_immediately(self):
  b=Battle(candidate(),[['tp_hong_rengan','tp_yang_xiuqing','tp_feng_yunshan'],['qing_guo_songlin']],lords=('tp_hong_xiuquan',None));r,u,_=b.teams[0].actors;base=u.max_hp;u.hp=base*.5;b.resource(0,'信仰',30)
  b.apply_loss(r,r.hp+1,b.teams[1].actors[0]);self.assertEqual(b.teams[0].faith_cap,120);self.assertAlmostEqual(u.max_hp/base,1.127);self.assertAlmostEqual(u.hp/u.max_hp,.5)
 def test_rengan_amplifies_policy_suspicion_not_bond_suspicion(self):
  b=Battle(candidate(),[['tp_hong_rengan','tp_yang_xiuqing','tp_wei_changhui'],['qing_guo_songlin']],lords=('tp_hong_xiuquan',None));b.round=1;b.step_start();self.assertAlmostEqual(b.teams[0].suspicion,17.5)
 def test_bao_attacked_every_two_hits(self):
  b=Battle(candidate(),[['qing_bao_chao'],['tp_qin_rigang']]);u=b.teams[0].actors[0];a=b.stats(u)['atk'];u.hits=1;b.invalidate();self.assertAlmostEqual(b.stats(u)['atk'],a)
  u.hits=2;b.invalidate();self.assertAlmostEqual(b.stats(u)['atk'],a*1.1)
  u.hits=100;b.invalidate();self.assertAlmostEqual(b.stats(u)['atk'],a*1.3)
 def test_shi_no_bond_includes_explicit_risk(self):
  b=Battle(candidate(),[['tp_shi_dakai'],['qing_guo_songlin']]);u=b.teams[0].actors[0];self.assertAlmostEqual(b.stats(u)['taken'],.2);self.assertAlmostEqual(u.max_hp/u.base['hp'],1.2)
 def test_single_exclusive_owner_and_stats_only(self):
  d=Data();id='tp_chen_yucheng';b=Battle(d,[[id],[id]],stars=4,exclusive_owners={(0,id)},exclusive_effects=False);u,v=[t.actors[0] for t in b.teams]
  self.assertGreater(u.base['atk'],v.base['atk']);self.assertNotIn('kill_recast',u.feature);self.assertTrue(u.exclusive);self.assertFalse(v.exclusive)
 def test_first_cast_only_exclusive_extra_combo(self):
  d=Data();d.exclusives['tp_hong_xuanjiao']['effect']='「女营双刀」连击 1 次 → 2 次；仅首次释放主动技时生效';b=Battle(d,[['tp_hong_xuanjiao'],['qing_guo_songlin']],stars=4,exclusive_owners={(0,'tp_hong_xuanjiao')},trace=True,limit=12)
  u=b.teams[0].actors[0];v=b.teams[1].actors[0];u.rage=100;u.hp=u.max_hp=1e9;v.hp=v.max_hp=1e9;v.base['atk']=1;b.invalidate();b.run()
  casts=sorted({e['round'] for e in b.trace if e['event']=='damage' and e['source']==u.id and e['active']});self.assertGreaterEqual(len(casts),2)
  counts=[sum(e['event']=='damage' and e['source']==u.id and e['round']==r for e in b.trace) for r in casts[:2]];self.assertEqual(counts,[3,2])
 def test_xianfeng_exclusive_heals_more_at_same_timing(self):
  d=Data();d.exclusives['qing_xianfeng']['effect']='「团练诏」回复 20% → 25%'
  b=Battle(d,[['tp_qin_rigang'],['qing_guo_songlin']],lords=(None,'qing_xianfeng'),stars=4,exclusive_owners={(1,'qing_xianfeng')});u=b.teams[1].actors[0];u.hp=u.max_hp*.5
  b.round=2;b.step_start();self.assertAlmostEqual(u.hp/u.max_hp,.5)
  b.round=3;b.step_start();self.assertAlmostEqual(u.hp/u.max_hp,.75)
 def test_top_cutoff_ties_are_fractional(self):
  rows=[{'id':i,'rate':r} for i,r in enumerate([1,.5,.5,0])];n,w=top_weights(rows,.5);self.assertEqual(n,2);self.assertEqual({r['id']:v for r,v in w},{0:1,1:.5,2:.5})
 def test_monarch_precision_pools_rates_before_cutoff(self):
  from run_monarch_precision_v2 import aggregate
  parts=[]
  for block in range(2):
   rows=[]
   for camp in ['taiping','qing']:
    for i in range(10):
     if camp=='taiping':lord='tp_hong_xiuquan' if block==0 else 'tp_hong_tianguifu';score=([1,.99]+[0]*8)[i] if block==0 else ([.9]+[0]*9)[i]
     else:lord='qing_cixi' if block==0 else 'qing_prince_gong';score=([1]+[0]*9)[i] if block==0 else ([.9]+[0]*9)[i]
     rows.append(dict(id=len(rows),faction=camp,lord=lord,rate=score))
   parts.append(dict(seed=block,total_games=64014,input_sha256={'fixture':'same'},simulator_sha256='same',top_lineups={'rows':rows}))
  x=aggregate(parts,Data());self.assertEqual(x['total_games'],128028);self.assertEqual(x['monarchs']['taiping']['top_count'],2)
  self.assertEqual(x['monarchs']['taiping']['cards']['tp_hong_xiuquan']['rate'],1);self.assertEqual(x['monarchs']['qing']['cards']['qing_cixi']['rate'],.5)
  self.assertEqual(x['monarchs']['qing']['cards']['qing_prince_gong']['rate'],.5)
 def test_monarch_excluded_from_combat_peak_and_formal_size(self):
  r=evaluate(Data(),n=1,lineups=20,opponents=1,seed=991);lords=set(pools(Data(),lords=True));self.assertFalse(lords.intersection(r['top_lineups']['appearances']))
  self.assertTrue(all(x['team_size']==5 for x in r['factions'].values()));self.assertEqual(set(r['monarchs']),{'taiping','qing'})

if __name__=='__main__':unittest.main()
