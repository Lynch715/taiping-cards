import copy,unittest
from closeout_acceptance import acceptance
class FinalCloseoutGate(unittest.TestCase):
 def sample(self):
  days=[1,1.5,2,2,2.5,3,3,3.5]
  return {'runs':[{'campaign':camp,'seed':seed,'cleared':48,'days':18.5,'chapters':[{'chapter':i+1,'duration':d,'target_days':d,'max_stage_wait':1}for i,d in enumerate(days)]}for camp in ['taiping','qing']for seed in range(12)]}
 def test_all_sixteen_chapters_and_two_campaigns_pass(self):
  m=acceptance(self.sample());self.assertEqual((m['chapter_pass_count'],m['campaign_pass_count']),(16,2));self.assertTrue(m['all_pass'])
 def test_fast_chapter_is_allowed_when_whole_campaign_is_long_enough(self):
  d=self.sample()
  for r in d['runs']:r['chapters'][7]['duration']=.5;r['days']=15.5
  self.assertTrue(acceptance(d)['all_pass'])
 def test_whole_campaign_uses_literal_13_9_not_13_875(self):
  d=self.sample()
  for r in d['runs']:r['days']=13.875
  self.assertEqual(acceptance(d)['campaign_pass_count'],0)
  for r in d['runs']:r['days']=13.9
  self.assertEqual(acceptance(d)['campaign_pass_count'],2)
 def test_two_tail_accounts_can_wait_three_days(self):
  d=self.sample()
  for r in d['runs'][:2]:r['chapters'][5]['max_stage_wait']=3
  self.assertTrue(acceptance(d)['all_pass'])
 def test_nine_short_accounts_or_one_over_three_fails(self):
  for n,wait in [(3,2.25),(1,3.25)]:
   d=self.sample()
   for r in d['runs'][:n]:r['chapters'][5]['max_stage_wait']=wait
   self.assertEqual(acceptance(d)['chapter_pass_count'],15)
 def test_upper_pace_limit_is_still_enforced(self):
  d=self.sample()
  for r in d['runs'][:12]:r['chapters'][5]['duration']=4;r['days']+=1
  self.assertEqual(acceptance(d)['chapter_pass_count'],15)
 def test_missing_duplicate_or_unfinished_accounts_cannot_pass(self):
  for change in ['missing','duplicate','unfinished']:
   d=self.sample()
   if change=='missing':d['runs'].pop()
   elif change=='duplicate':d['runs'][1]['seed']=d['runs'][0]['seed']
   else:d['runs'][0]['cleared']=47
   self.assertFalse(acceptance(d)['all_pass'])
if __name__=='__main__':unittest.main()
