/** Review snapshots built through product save/reward APIs; not normal earned-play saves. */
import fs from 'node:fs';
import {newSave,completeStage,allStages,validSave,stageTeams} from '../app/src/core/campaign';
import {campGrowth,acquire,dayKey} from '../app/src/core/progression';
import {exportSaveFile} from '../app/src/platform/save-transfer';
import {runBattle} from '../app/src/core/battle/engine';
import type {Campaign,TeamInput,Terrain} from '../app/src/core/battle/types';
async function main(){
const root='assets/reports/joint_v2',now=Date.now();fs.mkdirSync(root+'/fixtures',{recursive:true});
const manifest:any[]=[];
for(const [label,target]of [['elite','7_3'],['chapter8','8_6']]as const){let baseSeed=9250001;const plans:any={};
 for(;;baseSeed++){let both=true;for(const [side,camp]of (['taiping','qing']as Campaign[]).entries()){const id=(camp==='taiping'?'tp':'qing')+'_'+target,ref=JSON.parse(fs.readFileSync(root+'/round04/calibration/'+id+'.json','utf8')),row=allStages(camp).find(r=>r.stage_id===id)!;const index=ref.profiles.findIndex((team:TeamInput)=>runBattle(team,stageTeams(row,team.heroes)[1],row.terrain as Terrain,baseSeed+side+1,{allowDuplicates:true}).winner===0);if(index<0){both=false;break;}plans[camp]={ref,index,stage:id,seed:baseSeed+side+1};}if(both)break;if(baseSeed>9251001)throw Error('No deterministic review victory');}
 let save=newSave(now,baseSeed);save.campaign='taiping';
 for(const camp of ['taiping','qing']as Campaign[]){const id=(camp==='taiping'?'tp':'qing')+'_'+target;const rows=allStages(camp),idx=rows.findIndex(r=>r.stage_id===id);for(const row of rows.slice(0,idx))save=completeStage(save,row).save;
  const ref=plans[camp].ref,team=ref.profiles[plans[camp].index]as TeamInput,c=campGrowth(save,camp);
  for(const [i,id]of team.heroes.entries()){acquire(c,id);c.heroes[id]={level:team.levels![i],stars:team.stars![i]};}
  if(team.monarch){acquire(c,team.monarch);c.monarch=team.monarch;c.heroes[team.monarch].stars=team.monarchStars??3;}
  save.formations[camp]=[...team.heroes];c.gear=[];c.serial=0;
  for(const [i,items]of (team.gear??[]).entries())for(const item of items)c.gear.push({uid:camp+'-gear-'+(++c.serial),equipmentId:item.equipmentId,enhance:item.enhance,owner:team.heroes[i]});
  c.lastClaim=now;c.daily={day:dayKey(now),uses:{}};c.wallet={exp:0,silver:0,iron:0,tickets:0};
 }
 if(!validSave(save))throw Error('Invalid review snapshot '+label);fs.writeFileSync(root+'/fixtures/'+label+'.json',await exportSaveFile(save));manifest.push({label,baseSeed,controlled:true,purpose:'Deterministic UI victory to exercise next-stage/end-campaign controls, not win-rate evidence',plans:Object.fromEntries(Object.entries(plans).map(([camp,p]:[string,any])=>[camp,{stage:p.stage,profile:p.index,seed:p.seed}]))});
}
fs.writeFileSync(root+'/fixtures/manifest.json',JSON.stringify(manifest,null,2));
console.log('Two QA review snapshots; each contains both campaigns, calibrated profile formation and real reward-unlock ownership.');

}
main().catch(e=>{console.error(e);process.exitCode=1;});
