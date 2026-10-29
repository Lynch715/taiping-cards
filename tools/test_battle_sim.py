#!/usr/bin/env python3
"""Combat semantics regressions: formulas, CSV interpretation, and cross-system effects."""
import copy
import unittest
from battle_sim import Data,Battle,active_ast,base_stats,exclusive_skills,equipment_loadout,growth

class CombatTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.data=Data()
 def battle(self,left=None,right=None,**kw):
  return Battle(self.data,[left or ['tp_qin_rigang'],right or ['qing_guo_songlin']],**kw)
 def bare(self):
  b=self.battle();b.round=1
  for t in b.teams:
   t.bonds=[];t.enabled=set()
   for u in t.actors:
    u.feature={};u.auras=[];u.base={'hp':10000.,'atk':300.,'int':450.,'def':120.,'res':90.,'speed':80.,'crit':0.,'crit_damage':1.5,'start_rage':0.};u.max_hp=u.hp=10000.;u.hero=copy.deepcopy(u.hero);u.hero['troop']='水'
  b.invalidate();return b,b.teams[0].actors[0],b.teams[1].actors[0]
 def test_all_csv_texts_and_budgets(self):
  self.assertEqual(self.data.audit,[]);self.assertTrue(all(r['valid'] for r in self.data.budget()))
  for h in self.data.heroes.values():
   self.assertEqual(exclusive_skills(self.data,h,True)[-1],[],h['id'])
 def test_unknown_never_silently_runs(self):
  self.assertTrue(active_ast('敌方全体隐身飞行')['unknown'])
  d=copy.deepcopy(self.data);d.skills['sk_tp_qin_rigang_a']['effect']='敌方全体隐身飞行';d.compile()
  with self.assertRaises(ValueError):Battle(d,[['tp_qin_rigang'],['qing_guo_songlin']])
 def test_formula_growth(self):
  h=self.data.heroes['tp_qin_rigang'];s=base_stats(h,50,3)
  g=3.94*1.3;self.assertAlmostEqual(growth(50,3),g)
  self.assertAlmostEqual(s['hp'],(80*24+84*6)*g);self.assertEqual(s['speed'],66)
 def test_damage_physical_and_strategy_use_matching_defense(self):
  b,u,v=self.bare();before=v.hp;b.damage(u,v);self.assertEqual(before-v.hp,int(270*270/(270+120))) # nonwater attack -10%
  u.hero['troop']='谋';b.invalidate();before=v.hp;b.damage(u,v,2,active=True)
  self.assertEqual(before-v.hp,int(2*450*450/(450+90)*1.15))
 def test_troop_counter(self):
  b,u,v=self.bare();u.hero['troop']='骑';v.hero['troop']='步';v.slot=2;b.invalidate();b.damage(u,v)
  self.assertEqual(10000-v.hp,int(300*300/420*1.2))
 def test_two_buffs_separated_by_dunhao(self):
  ast=active_ast('我方全体攻击 +15%、速度 +10 点，持续 2 回合。');self.assertEqual([(o['stat'],o['value']) for o in ast['ops']],[('attack',.15),('speed',10)])
 def test_aura_start_rage_not_overwritten(self):
  b=self.battle(['tp_yang_xiuqing','tp_feng_yunshan','tp_hong_rengan'])
  expected=30+sum(b.teams[0].actors[i].feature[k][0] for i,k in [(0,'start_rage_all'),(1,'start_rage_taiping')]);self.assertEqual([u.rage for u in b.teams[0].actors],[expected]*3)
 def test_rage_and_shield_absorbed_hit(self):
  b,u,v=self.bare();u.base['speed']=90;u.hero['troop']='步';b.invalidate();v.shields=[[10000,2,'test']];before=v.hp
  b.basic(u);self.assertEqual(v.hp,before);self.assertEqual(v.rage,10);self.assertEqual(u.rage,30)
 def test_same_source_strongest_and_other_sources_add(self):
  b,u,v=self.bare();b.buff(u,'a','attack',.2,False,2);b.buff(u,'a','attack',.1,False,3);b.buff(u,'b','attack',.1,False,2)
  self.assertAlmostEqual(b.stats(u)['atk'],300*1.2) # -.1 nonwater +.2+.1
  self.assertEqual(len(u.buffs),2)
 def test_burn_consumes_shield_without_critical_or_defense(self):
  b,u,v=self.bare();v.shields=[[500,2,'test']];v.burns=[[300,1,u]];b.step_end()
  self.assertEqual(v.hp,10000);self.assertEqual(v.shields[0][0],200);self.assertEqual(v.rage,10)
 def test_heal_and_shield_based_on_target_max(self):
  b,u,v=self.bare();u.hp=5000;b.execute(u,active_ast('自身回复 20%；自身获得护盾 25%，持续 2 回合。'),'test')
  self.assertEqual(u.hp,7000);self.assertEqual(u.shields[0][0],2500)
 def test_taunt_redirects_single_not_all(self):
  b=self.battle(right=['qing_guo_songlin','qing_shengbao','qing_he_chun']);b.round=1;u=b.teams[0].actors[0];v=b.teams[1].actors[2];v.control['嘲讽']=2
  self.assertEqual(b.targets(u,'enemy_front_one'),[v]);self.assertEqual(len(b.targets(u,'enemy_all')),3)
 def test_death_save_exactly_once(self):
  b=self.battle(['tp_li_kaifang']);u=b.teams[0].actors[0];v=b.teams[1].actors[0]
  b.apply_loss(u,u.hp+1,v);self.assertEqual(u.hp,1);b.apply_loss(u,1,v);self.assertFalse(u.alive)
 def test_incident_escape_is_not_death_and_cannot_repeat(self):
  b=self.battle(['tp_yang_xiuqing','tp_wei_changhui','tp_shi_dakai'],lords=('tp_hong_xiuquan',None));b.round=1
  ys,wei,shi=b.teams[0].actors;before=[x.hp for x in [ys,wei,shi]];b.resource(0,'猜忌',100)
  self.assertEqual(ys.hp,before[0]*.5);self.assertEqual(wei.hp,before[1]*.5);self.assertTrue(shi.escaped);self.assertEqual(shi.hp,before[2]);b.resource(0,'猜忌',100);self.assertEqual(b.teams[0].suspicion,0)
 def test_hong_bond_suspicion_not_counted_twice(self):
  for wei,expected in [(False,5),(True,15)]:
   ids=['tp_yang_xiuqing']+(['tp_wei_changhui'] if wei else [])
   b=self.battle(ids,lords=('tp_hong_xiuquan',None));b.round=1;b.step_start();self.assertEqual(b.teams[0].suspicion,expected)
 def test_monarch_does_not_borrow_first_actor_set(self):
  b=self.battle(lords=('tp_hong_xiuquan',None),gear_set='圣兵');b.teams[0].bonds=[];b.teams[0].faith=0;b.round=3;b.step_start()
  self.assertEqual(b.teams[0].faith,40);self.assertEqual(len(b.teams[0].actors),1)
  with self.assertRaises(ValueError):self.battle(['tp_hong_xiuquan'])
 def test_full_monarch_edict_once(self):
  b=self.battle(lords=(None,'qing_xianfeng'));u=b.teams[1].actors[0];u.hp=u.max_hp*.5;b.round=3;b.step_start()
  self.assertAlmostEqual(u.hp,u.max_hp*.7);b.step_start();self.assertAlmostEqual(u.hp,u.max_hp*.7)
 def test_grain_faith_and_terrain(self):
  b=self.battle(['tp_qin_rigang','tp_hu_yihuang','tp_huang_wenjin'],['qing_guo_songlin','qing_shengbao','qing_he_chun']);b.round=1
  v=b.teams[1].actors[0];d=b.stats(v)['def'];b.resource(1,'粮饷',30);self.assertAlmostEqual(b.stats(v)['def'],d*1.05)
  b.resource(0,'信仰',50);self.assertEqual(b.teams[0].heaven_until,2);b.round=3;b.step_start();self.assertEqual(b.teams[0].faith,50)
 def test_exclusive_unlock_and_set(self):
  a=self.battle(['tp_chen_yucheng'],use_exclusives=True,stars=3);b=self.battle(['tp_chen_yucheng'],use_exclusives=True,stars=4)
  self.assertFalse(a.teams[0].actors[0].exclusive);self.assertTrue(b.teams[0].actors[0].exclusive)
  self.assertNotIn('kill_recast',a.teams[0].actors[0].feature);self.assertTrue(b.teams[0].actors[0].feature['kill_recast'])
  for name in self.data.sets:self.assertEqual(len(equipment_loadout(self.data,name)),4)
 def test_exclusive_desperation_changes_heal_not_threshold(self):
  h=self.data.heroes['tp_shi_dakai'];a,p,extra,unknown=exclusive_skills(self.data,h,True)
  original=self.data.cache[h['passive']]['features']['desperation']
  self.assertEqual(p['features']['desperation'][0],original[0])
  self.assertGreater(p['features']['desperation'][1],original[1])
 def test_two_piece_set_does_not_enable_four_piece(self):
  ids=[r['equip_id'] for r in equipment_loadout(self.data,'圣兵')[:2]]
  b=self.battle(equipment_ids=ids);u=b.teams[0].actors[0]
  self.assertTrue(any(a['stat']=='attack' for a in u.auras));self.assertNotIn('set_faith_gain',u.feature)
 def test_control_silence_basic_and_stun_skips(self):
  for status,basics in [('沉默',1),('眩晕',0)]:
   b=self.battle(limit=1);u=b.teams[0].actors[0];u.rage=100;u.control[status]=1;b.run();self.assertEqual(u.casts,0);self.assertEqual(u.basics,basics)
 def test_timeout_attacker_loses_and_seed_repeats(self):
  b=self.battle(limit=1);r=b.run();self.assertEqual(r['winner'],1);self.assertTrue(r['timeout']);self.assertEqual(r,self.battle(limit=1).run())

if __name__=='__main__':unittest.main()
