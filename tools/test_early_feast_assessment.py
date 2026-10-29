import copy,unittest
from early_feast_assessment import assess
class EarlyFeastGate(unittest.TestCase):
 def sample(self):
  r={'campaign':'taiping','seed':1,'chapters':[{'chapter':c,'day':c,'main':[{'level':10*c}for _ in range(5)]}for c in [1,2]],'early_feast_offers':[]};return {'runs':[r]}
 def block(self,d):d['runs'][0]['early_feast_offers']=[{'affordable':False,'reference_affordable':True,'chapter':1,'day':0}]
 def test_temporary_unaffordable_offer_is_not_failure_by_itself(self):
  a=self.sample();b=copy.deepcopy(a);self.block(b);self.assertTrue(assess(a,b)['pass'])
 def test_later_completion_after_a_price_block_fails(self):
  a=self.sample();b=copy.deepcopy(a);self.block(b);b['runs'][0]['chapters'][0]['day']+=.25;self.assertFalse(assess(a,b)['pass'])
 def test_lower_mean_at_same_time_after_price_block_fails(self):
  a=self.sample();b=copy.deepcopy(a);self.block(b);b['runs'][0]['chapters'][0]['main'][0]['level']-=1;self.assertFalse(assess(a,b)['pass'])
 def test_earlier_completion_with_a_lower_level_is_not_called_slow_growth(self):
  a=self.sample();b=copy.deepcopy(a);self.block(b);b['runs'][0]['chapters'][0]['day']-=.25;b['runs'][0]['chapters'][0]['main'][0]['level']-=1;self.assertTrue(assess(a,b)['pass'])
 def test_future_or_original_price_unaffordable_offer_does_not_explain_an_earlier_delay(self):
  for original_unaffordable in [False,True]:
   a=self.sample();b=copy.deepcopy(a);self.block(b);b['runs'][0]['chapters'][0]['day']+=.25
   if original_unaffordable:b['runs'][0]['early_feast_offers'][0]['reference_affordable']=False
   else:b['runs'][0]['early_feast_offers'][0]['day']=3
   self.assertTrue(assess(a,b)['pass'])
if __name__=='__main__':unittest.main()
