import copy,unittest
from economy_closeout import joint_metrics
class JointCloseoutAcceptance(unittest.TestCase):
 def sample(self):
  targets=[1,1.5,2,2,2.5,3,3,3.5]
  return {'runs':[{'campaign':camp,'seed':s,'cleared':48,'chapters':[{'chapter':i+1,'duration':d,'target_days':d,'max_stage_wait':1,'remaining':{'silver':10000000}}for i,d in enumerate(targets)]}for camp in ['taiping','qing']for s in range(12)]}
 def test_both_requirements_pass_together(self):self.assertEqual(joint_metrics(self.sample())['joint_pass_count'],16)
 def test_wait_failure_is_not_hidden_by_good_mean(self):
  d=self.sample();d['runs'][0]['chapters'][5]['max_stage_wait']=2.25;m=joint_metrics(d);self.assertEqual(m['joint_pass_count'],15);self.assertFalse(m['all_pass'])
 def test_good_wait_does_not_hide_wrong_pace(self):
  d=self.sample()
  for r in d['runs'][:12]:r['chapters'][5]['duration']=4
  self.assertEqual(joint_metrics(d)['joint_pass_count'],15)
 def test_missing_account_or_incomplete_progress_cannot_pass(self):
  for missing in [False,True]:
   d=self.sample()
   if missing:d['runs'].pop()
   else:d['runs'][0]['cleared']=47
   self.assertFalse(joint_metrics(d)['all_pass'])
if __name__=='__main__':unittest.main()
