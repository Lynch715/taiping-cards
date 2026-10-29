import fs from 'node:fs';
import {newSave,completeStage,allStages,validSave} from '../app/src/core/campaign';
import {sweep,campGrowth,dailySweepRemaining} from '../app/src/core/progression';
import {exportSaveFile} from '../app/src/platform/save-transfer';
async function main(){const now=Date.now();let save=newSave(now,154001);save.campaign='taiping';for(const camp of ['taiping','qing']as const)for(const row of allStages(camp).slice(0,6))save=completeStage(save,row).save;for(const row of allStages('taiping').slice(0,6))for(let n=0;n<3;n++)save=sweep(save,row,now).save;for(const row of allStages('qing').slice(0,3))for(let n=0;n<3;n++)save=sweep(save,row,now).save;campGrowth(save,'taiping').shards.tp_shi_dakai=50;if(!validSave(save)||dailySweepRemaining(save,now)!==3)throw Error('Invalid controlled fixture');fs.mkdirSync('assets/reports/joint_v2/fixtures',{recursive:true});fs.writeFileSync('assets/reports/joint_v2/fixtures/limit27.json',await exportSaveFile(save));console.log('Controlled UI fixture: two chapters cleared,27 total daily sweeps,50 Shi Dakai shards; not normal played-through progression.');}
main().catch(e=>{console.error(e);process.exitCode=1;});
