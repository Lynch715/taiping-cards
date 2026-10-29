import unittest
from battle_sim import Battle,read_csv,ROOT
from m1_scenarios import game_data,stage_input,assumed_level
class ChapterProfiles(unittest.TestCase):
 def test_all_chapters_use_endpoint_interpolated_levels(self):
  d=game_data();own=read_csv(ROOT/'data/starter_cards.csv')[0]['cards'].split(';')[:5]
  for row in read_csv(ROOT/'data/stages.csv'):
   if row['campaign']!='taiping':continue
   a,b=stage_input(d,row,own,12)
   self.assertEqual(a['levels'],[assumed_level(int(row['chapter']),int(row['order']))]*5)
 def test_guarding_nanchang_player_defense_is_plus_twenty_percent(self):
  d=game_data();rosters=[['tp_npc_shengbing'],['qing_npc_lvying']]
  land=Battle(d,rosters,lords=(None,None),assigned=('taiping','qing'),terrain='陆战',level=20,stars=1,seed=99)
  guard=Battle(d,rosters,lords=(None,None),assigned=('taiping','qing'),terrain='守城',level=20,stars=1,seed=99)
  self.assertAlmostEqual(guard.stats(guard.teams[0].actors[0])['def'],land.stats(land.teams[0].actors[0])['def']*1.2)
  self.assertAlmostEqual(guard.stats(guard.teams[1].actors[0])['def'],land.stats(land.teams[1].actors[0])['def'])
if __name__=='__main__':unittest.main()
