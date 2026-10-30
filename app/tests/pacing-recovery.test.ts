import {expect,it} from 'vitest';
import {newSave,selectCampaign,allStages,completeStage,validSave,stageTeams} from '../src/core/campaign';
import {campGrowth,growthEconomy,economy,claimIdle,idlePreview,sweep,summon,summonCost,recruitPool} from '../src/core/progression';
import {troopStatus,troopRatio,reinforce} from '../src/core/troops';
import {exportSaveFile,importSaveFile} from '../src/platform/save-transfer';
import v050 from './fixtures/legacy-v050-save.json';
import type {Save} from '../src/core/campaign';
const now=new Date(2026,0,1,8).getTime();
it('reports the true recovery deadline for future timestamps without granting rollback healing',()=>{
 for(const camp of ['taiping','qing']as const)for(const ratio of [0,.25,.999,1])for(const ahead of [0,1,86400000]){
  const s=newSave(now),id=s.formations[camp][0],c=campGrowth(s,camp);c.heroes[id].troops=ratio;c.heroes[id].troopsAt=now+ahead;
  const raw=JSON.stringify(s),status=troopStatus(s,camp,id,now),deadline=now+status.minutes*60000;
  expect(troopRatio(s,camp,id,now)).toBe(ratio);expect(troopRatio(s,camp,id,deadline)).toBe(1);
  if(status.minutes>0)expect(troopRatio(s,camp,id,deadline-60000)).toBeLessThan(1);
  expect(JSON.stringify(s)).toBe(raw);
  if(status.cost){c.wallet.silver=status.cost;const full=reinforce(s,camp,[id],now).save;expect(troopStatus(full,camp,id,now).minutes).toBe(0);expect(validSave(full)).toBe(true);}
 }
});
it('never drops future or enemy shards from early progressive sweeps, and keeps the daily limit',()=>{
 for(const camp of ['taiping','qing']as const){let s:Save=selectCampaign(newSave(now,903),camp);for(const stage of allStages(camp).slice(0,6))s=completeStage(s,stage).save;
  const allowed=new Set(recruitPool(s,camp).map(h=>h.id));
  for(let day=0;day<12;day++)for(const stage of allStages(camp).slice(0,6))for(let n=0;n<3;n++){
   const r=sweep(s,stage,now+day*86400000);s=r.save;
   for(const drop of [r.grant.shards,r.grant.battleShards])if(drop)expect(allowed.has(drop.id)).toBe(true);
   expect(validSave(s)).toBe(true);
  }
 }
});
it('keeps pre-existing future shards intact until their chapter opens, then allows level-one synthesis',async()=>{
 let s:Save=selectCampaign(newSave(now),'taiping');for(const r of allStages('taiping').slice(0,6))s=completeStage(s,r).save;
 const id='tp_chen_yucheng';campGrowth(s,'taiping').shards[id]=summonCost(id);const raw=JSON.stringify(s);
 expect(()=>summon(s,'taiping',id)).toThrow('尚未登场');expect(JSON.stringify(s)).toBe(raw);
 s=(await importSaveFile(await exportSaveFile(s))).payload;expect(campGrowth(s,'taiping').shards[id]).toBe(summonCost(id));
 for(const r of allStages('taiping').slice(6,24))s=completeStage(s,r).save;
 s=summon(s,'taiping',id);expect(campGrowth(s,'taiping').heroes[id].level).toBe(1);expect(validSave(s)).toBe(true);
});
it('boosts level-one training from the third chapter while preserving silver, shards and legacy economics',()=>{
 const fresh=newSave(now),old=structuredClone(v050)as Save,raw=JSON.stringify(old);
 for(const camp of ['taiping','qing']as const)for(let chapter=1;chapter<=8;chapter++){
  const current=growthEconomy(fresh,camp,chapter),base=economy(chapter);
  expect(growthEconomy(old,camp,chapter)).toEqual(base);
  for(const key of ['idle_silver_per_hour','first_clear_silver','sweep_silver','sweep_shards']as const)expect(current[key]).toBe(base[key]);
  expect(current.idle_exp_per_hour).toBeGreaterThanOrEqual(base.idle_exp_per_hour);
  if(chapter<=2)expect(current).toEqual(base);
 }
 expect(JSON.stringify(old)).toBe(raw);
});
it('uses the same enhanced rates for preview, fractional offline claims, sweeps and first clears without rewriting old heroes',()=>{
 for(const camp of ['taiping','qing']as const){let s:Save=selectCampaign(newSave(now),camp);const stages=allStages(camp);for(const r of stages.slice(0,31))s=completeStage(s,r).save;
  const c=campGrowth(s,camp),id=s.formations[camp][0];c.heroes[id].troops=.25;c.heroes[id].troopsAt=now;
  const raw=JSON.stringify(s),preview=idlePreview(s,camp,now+3600000),claimed=claimIdle(s,camp,now+3600000),rules=growthEconomy(s,camp,6);
  expect(preview.exp).toBe(rules.idle_exp_per_hour);expect(claimed.grant.exp).toBe(preview.exp);expect(claimed.save.formations).toEqual(s.formations);
  expect(campGrowth(claimed.save,camp).heroes).toEqual(c.heroes);expect(JSON.stringify(s)).toBe(raw);
  const a=claimIdle(s,camp,now+1234567),b=claimIdle(a.save,camp,now+3600000);expect(a.grant.exp+b.grant.exp).toBe(preview.exp);
  expect(sweep(s,stages[30],now).grant.exp).toBe(rules.sweep_exp);
  expect(completeStage(s,stages[31]).grant.exp).toBe(rules.first_clear_exp);
  expect(validSave(claimed.save)).toBe(true);
 }
});

it('eases only the level-one sixth boss while keeping legacy combat and adjacent stages intact',()=>{
 for(const camp of ['taiping','qing']as const){const s=newSave(now),old=structuredClone(v050)as Save,boss=allStages(camp)[35],prior=allStages(camp)[34];
  expect(stageTeams(boss,s.formations[camp],s)[1].statScale).toBe(.9);
  expect(stageTeams(prior,s.formations[camp],s)[1].statScale).toBe(1);
  const before=JSON.stringify(old),legacyBoss=stageTeams(boss,old.formations[camp],old)[1];
  expect(legacyBoss.statScale).toBe(old.growth![camp].progressive?1:undefined);expect(JSON.stringify(old)).toBe(before);
 }
});
