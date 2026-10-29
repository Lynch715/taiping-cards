import unittest
from stage_difficulty import target
from calibrate_growth import adjusted_team

class DifficultyRules(unittest.TestCase):
 def row(self,ch,o,history='胜',sid=None):return {'chapter':str(ch),'order':str(o),'history_result':history,'stage_id':sid or f'tp_{ch}_{o}'}
 def test_all_six_positions_keep_gradient_in_defeat_chapter(self):
  self.assertEqual([target(self.row(7,o,'败'))for o in range(1,7)],[(.85,.9),(.75,.85),(.75,.85),(.6,.75),(.6,.75),(.5,.6)])
 def test_normal_positions_and_named_early_exceptions(self):
  self.assertEqual([target(self.row(3,o))for o in range(1,7)],[(.95,1),(.85,.95),(.85,.95),(.7,.85),(.7,.85),(.55,.7)])
  for sid in ['qing_1_3','qing_2_3','qing_2_5']:self.assertEqual(target(self.row(int(sid.split('_')[1]),int(sid.split('_')[2]),'败',sid)),(.5,.65))
  self.assertEqual(target(self.row(1,5,'败')),(.7,.85))
 def test_invalid_history_does_not_silently_use_easier_target(self):
  with self.assertRaises(ValueError):target(self.row(7,3,''))
 def test_profile_normalization_obeys_individual_star_caps_and_exact_mean(self):
  original={'heroes':['a','b','c','d','e'],'levels':[65,82,80,80,80],'stars':[3,5,4,4,4],'gear':[[],[],[],[],[]]}
  adjusted=adjusted_team(original,78)
  self.assertEqual(sum(adjusted['levels']),390)
  self.assertLessEqual(adjusted['levels'][0],65)
  self.assertEqual(original['levels'],[65,82,80,80,80])
  self.assertTrue(all(isinstance(x,int)for x in adjusted['levels']))
if __name__=='__main__':unittest.main()
