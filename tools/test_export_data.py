import json,unittest
from unittest.mock import patch
import export_data
from export_data import build
class ExportTables(unittest.TestCase):
 def test_growth_tables_export_with_explicit_numeric_types(self):
  out=build();levels=json.loads(out['progression_levels.json']);self.assertEqual(levels[0]['level'],1);self.assertIsInstance(levels[0]['exp_to_next'],int)
  economy=json.loads(out['economy_chapters.json']);self.assertEqual(economy[1]['target_days'],1.5)
  stars=json.loads(out['star_up.json']);self.assertEqual(stars[0]['star_to'],2)
 def test_empty_salvage_is_nullable_and_recruit_rates_preserve_percent_units(self):
  out=build();gear=json.loads(out['equip_enhance.json']);self.assertIsNone(gear[1]['salvage_iron']);self.assertGreater(gear[0]['salvage_iron'],0)
  self.assertEqual(json.loads(out['recruit.json'])[0]['rate_SSR'],'4%')
 def test_history_result_and_complete_chapter_grid_are_required(self):
  original=export_data.csv.DictReader
  def reader_for(transform):
   class Reader:
    def __init__(self,file,*args,**kwargs):
     real=original(file,*args,**kwargs);self.fieldnames=real.fieldnames;self.rows=list(real)
     if str(file.name).endswith('stages.csv'):self.rows=transform(self.rows)
    def __iter__(self):return iter(self.rows)
   return Reader
  def invalid(rows):rows[0]['history_result']='';return rows
  def high_level(rows):rows[0]['enemy_level']='21';return rows
  def low_level(rows):rows[0]['enemy_level']='1';return rows
  for transform in [invalid,lambda rows:rows[:-1],high_level,low_level]:
   with patch.object(export_data.csv,'DictReader',reader_for(transform)):
    with self.assertRaises(AssertionError):build()
 def test_stage_specific_assumption_is_used_for_enemy_bounds(self):
  original=export_data.csv.DictReader
  class Reader:
   def __init__(self,file,*args,**kwargs):
    real=original(file,*args,**kwargs);self.fieldnames=real.fieldnames;self.rows=list(real)
    if str(file.name).endswith('stage_level_overrides.csv'):
     self.rows=[r for r in self.rows if r['stage_id']!='qing_6_6']+[{'stage_id':'qing_6_6','assumed_level':'52.3','source_accounts':'12','source':'test'}]
    elif str(file.name).endswith('stages.csv'):
     for r in self.rows:
      if r['stage_id']=='qing_6_6':r['enemy_level']='54'
   def __iter__(self):return iter(self.rows)
  with patch.object(export_data.csv,'DictReader',Reader):
   out=build();self.assertEqual(next(r for r in json.loads(out['stage_level_overrides.json'])if r['stage_id']=='qing_6_6')['assumed_level'],52.3)
 def test_feast_profiles_cover_every_chapter_and_prices_increase(self):
  out=build();rules=json.loads(out['feast.json']);self.assertEqual(len(rules),16)
  for profile in ['conservative','aggressive']:
   rows=sorted((r for r in rules if r['profile']==profile),key=lambda r:r['chapter']);self.assertEqual([r['chapter']for r in rows],list(range(1,9)));self.assertTrue(all(a['silver']<b['silver']for a,b in zip(rows,rows[1:])))
 def test_invalid_feast_daily_budget_is_rejected(self):
  original=export_data.csv.DictReader
  class Reader:
   def __init__(self,file,*args,**kwargs):
    real=original(file,*args,**kwargs);self.fieldnames=real.fieldnames;self.rows=list(real)
    if str(file.name).endswith('/feast.csv'):self.rows[0]['daily_limit']='-1'
   def __iter__(self):return iter(self.rows)
  with patch.object(export_data.csv,'DictReader',Reader):
   with self.assertRaises(AssertionError):build()
if __name__=='__main__':unittest.main()
