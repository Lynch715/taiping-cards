/** UI fixture: real economy actions under a simulated clock; no browser storage mutation. */
import fs from 'node:fs';
import {newSave,completeStage,chapter,validSave} from '../app/src/core/campaign';
import {campGrowth,claimIdle,recruit,salvage,sweep,train} from '../app/src/core/progression';
import {exportSaveFile} from '../app/src/platform/save-transfer';
(async()=>{
const now=Date.now(),day=86400000,start=now-31*day,camp='taiping';let save=newSave(start);save.campaign=camp;
for(const row of chapter(camp))save=completeStage(save,row).save;
for(let d=0;d<30;d++){for(const row of chapter(camp))for(let i=0;i<3;i++)save=sweep(save,row,start+d*day).save;for(const h of [6,24])save=claimIdle(save,camp,start+d*day+h*3600000).save;}
save=train(save,camp,'tp_hu_yihuang',25).save;
const c=campGrowth(save,camp);save=salvage(save,camp,c.gear.slice(4).map(g=>g.uid)).save;
for(let seed=1;seed<1000;seed++){const candidate=structuredClone(save);campGrowth(candidate,camp).rng=seed;const result=recruit(candidate,camp,10);let trial=result.save;for(let n=0;n<29;n++)trial=recruit(trial,camp).save;if(campGrowth(trial,camp).pity===39){save=trial;break;}}
if(campGrowth(save,camp).pity!==39)throw Error('No pity fixture found');
if(!validSave(save))throw Error('Invalid fixture');fs.mkdirSync('assets/reports/progression/fixtures',{recursive:true});fs.writeFileSync('assets/reports/progression/fixtures/ui-growth.json',await exportSaveFile(save));console.log({wallet:campGrowth(save,camp).wallet,pity:campGrowth(save,camp).pity,R:campGrowth(save,camp).heroes.tp_hu_yihuang,shards:campGrowth(save,camp).shards.tp_hu_yihuang,lastClaim:campGrowth(save,camp).lastClaim,now});

})().catch(e=>{console.error(e);process.exitCode=1;});
