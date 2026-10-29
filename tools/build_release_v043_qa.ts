/** Synthetic UI coverage only; never use this military save for economy claims. */
import {writeFileSync} from 'node:fs';
import {newSave,validSave} from '../app/src/core/campaign';
import {database} from '../app/src/core/data';
import {campGrowth} from '../app/src/core/progression';
import {exportSaveFile,importSaveFile} from '../app/src/platform/save-transfer';
async function main(){
 const save=newSave(Date.now(),1851);save.campaign='taiping';
 for(const camp of ['taiping','qing'] as const){
  save.progress[camp]=database.stages.filter(s=>s.campaign===camp).sort((a,b)=>a.chapter-b.chapter||a.order-b.order).map(s=>s.stage_id);
  const g=campGrowth(save,camp);
  for(const h of database.heroes.filter(h=>[camp,'dual'].includes(h.faction)))g.heroes[h.id]={level:100,stars:6};
  g.gear=database.equipment.map((row,i)=>({uid:`qa-v043-${camp}-${i}`,equipmentId:row.equip_id,enhance:0,owner:null}));g.serial=100;
  g.wallet={exp:100000,silver:1000000,iron:10000,tickets:10};
 }
 if(!validSave(save))throw Error('QA fixture invalid');
 const text=await exportSaveFile(save);await importSaveFile(text);
 writeFileSync('assets/reports/release_v043_20261029/qa_all_art.json',text);
 console.log('Synthetic UI fixture: 96 cleared, level100,100 items per camp; QA namespace only.');
}
void main();
