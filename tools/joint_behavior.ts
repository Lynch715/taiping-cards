import {spend as playerSpend,spendCore,sweepByPolicy}from './player_policy';
import type {FeastProfile}from '../app/src/core/progression';
/** v0.2 player model: product economy + the exact product formation advisor. */
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {database as db} from '../app/src/core/data';
import {newSave,stageTeams,completeStage,ownedHeroes} from '../app/src/core/campaign';
import type {Save} from '../app/src/core/campaign';
import type {Campaign,TeamInput,Terrain} from '../app/src/core/battle/types';
import {runBattle} from '../app/src/core/battle/engine';
import {recommendFormation} from '../app/src/core/formation';
import {rawUnitPower,armyPower} from '../app/src/core/power';
import {campGrowth,claimIdle,heroTeam,heroRow,assumedLevel,levelCost,levelCap,train,promote,recruit,transfer,salvage,equipmentRow,enhanceGear,sweep,sweepRemaining,dailySweepRemaining,economy,starRule} from '../app/src/core/progression';
const arg=Object.fromEntries(process.argv.slice(2).map(s=>{const i=s.indexOf('=');return[s.slice(0,i),s.slice(i+1)];}));
if(arg.tables){const tables=JSON.parse(fs.readFileSync(arg.tables,'utf8'));for(const key of ['economy_chapters','star_up','stages','enemy_units','stage_level_overrides','feast']as const)if(tables[key])(db as any)[key]=tables[key];}
const start=new Date(2026,0,1,8).getTime(),maxChapter=Number(arg.chapters??8),count=Number(arg.n??4),startSeed=Number(arg.seed??121000),mode=arg.mode??'battle',attemptCap=Number(arg.attempts??3),maxDays=Number(arg.days??80);
const traceEarly=arg.trace_early==='1',referenceDivisor=Number(arg.reference_divisor??1);if(!Number.isSafeInteger(referenceDivisor)||referenceDivisor<1)throw Error('Invalid reference price divisor');
let forecasts=0;const feastProfile=(arg.feast??'off')as FeastProfile|'off';if(!['off','conservative','aggressive'].includes(feastProfile))throw Error('Unknown feast profile');
function simulate(camp:Campaign,seed:number){let save=newSave(start,seed);save.campaign=camp;const stages=db.stages.filter(s=>s.campaign===camp&&s.chapter<=maxChapter).sort((a,b)=>a.chapter-b.chapter||a.order-b.order),profiles:any[]=[],firstChallenges:any[]=[],entries:any[]=[],chapters:any[]=[],waits:any[]=[],sessionWallets:any[]=[];let index=0,lastEnd=0,lastAdvance=0,maxWait=0,attempts=0,failures=0,chapterIncome={exp:0,silver:0,iron:0,tickets:0},sources={idle:0,first:0,sweep:0,feast:0},totalSweeps=0,maxDailySweeps=0;const feastPurchases:any[]=[],earlyFeastOffers:any[]=[];const offerKeys=new Set<string>();let spendNow=start;function spend(s:Save,c:Campaign){return playerSpend(s,c,spendNow,feastProfile,r=>{grant(r.grant,'feast');feastPurchases.push({day:(spendNow-start)/86400000,chapter:r.chapter,silver:r.spent,exp:r.grant.exp});},traceEarly?(state,offer)=>{
 if(offer.chapter>2)return;const c=campGrowth(state,camp),row=stages[index],key=JSON.stringify([spendNow,row?.stage_id,c.wallet,state.formations[camp]]);if(offerKeys.has(key))return;offerKeys.add(key);
 const affordable=c.wallet.silver>=offer.silver,referencePrice=offer.silver/referenceDivisor,record:any={stage_id:row?.stage_id??null,chapter:offer.chapter,day:(spendNow-start)/86400000,silver:c.wallet.silver,exp:c.wallet.exp,price:offer.silver,gain:offer.exp,affordable,reference_price:referencePrice,reference_affordable:c.wallet.silver>=referencePrice,formation:[...state.formations[camp]],levels:state.formations[camp].map(id=>c.heroes[id].level)};
 if(!affordable&&record.reference_affordable&&referenceDivisor>1){
  // Read-only same-state counterfactual: what could the original price train now?
  let shadow=structuredClone(state);campGrowth(shadow,camp).wallet.silver-=referencePrice;campGrowth(shadow,camp).wallet.exp+=offer.exp;shadow=spendCore(shadow,camp);
  record.original_price_level_gains=Object.entries(c.heroes).flatMap(([id,h])=>campGrowth(shadow,camp).heroes[id].level>h.level?[{id,before:h.level,after:campGrowth(shadow,camp).heroes[id].level,main:state.formations[camp].includes(id)}]:[]);
 }
 earlyFeastOffers.push(record);
}:undefined);}const firstSeen=new Set<string>(),seen=new Set<string>(),sweepCounts:Record<string,number>={};
 function grant(g:{exp:number;silver:number;iron:number;tickets:number},kind:keyof typeof sources){sources[kind]+=g.exp;for(const k of ['exp','silver','iron','tickets']as const)chapterIncome[k]+=g[k];}
 function recruitAll(){while(campGrowth(save,camp).wallet.tickets){const n=campGrowth(save,camp).wallet.tickets>=10?10:1;save=recruit(save,camp,n).save;}}
 function sweepAll(now:number){const r=sweepByPolicy(save,camp,stages,index,now);save=r.save;for(const g of r.grants)grant(g,'sweep');totalSweeps+=r.count;const day=new Date(now).toDateString();sweepCounts[day]=(sweepCounts[day]??0)+r.count;maxDailySweeps=Math.max(maxDailySweeps,sweepCounts[day]);}
 for(let session=0;session<maxDays*2+1&&index<stages.length;session++){
  const day=Math.floor(session/2)+(session%2?.25:0),now=start+day*86400000;spendNow=now;const idle=claimIdle(save,camp,now);save=idle.save;grant(idle.grant,'idle');sweepAll(now);recruitAll();
  for(let turn=0;turn<48&&index<stages.length;turn++){
   const row=stages[index];save=spend(save,camp);let pool=heroTeam(save,camp,ownedHeroes(save,camp));const enemy=stageTeams(row,save.formations[camp],save)[1];let advice;for(let planning=0;planning<3;planning++){advice=recommendFormation(pool,enemy,row.terrain as Terrain,{current:save.formations[camp],inventory:campGrowth(save,camp).gear});forecasts+=advice.candidates*advice.trials;const oldMembers=new Set(save.formations[camp]);save.formations[camp]=advice.heroes;for(const item of campGrowth(save,camp).gear)if(advice.equipmentOwners&&item.uid in advice.equipmentOwners)item.owner=advice.equipmentOwners[item.uid];if(!advice.heroes.some(id=>!oldMembers.has(id)))break;const oldPool=JSON.stringify(pool);save=spend(save,camp);pool=heroTeam(save,camp,ownedHeroes(save,camp));if(oldPool===JSON.stringify(pool))break;}const team=heroTeam(save,camp,advice!.heroes),mean=team.levels!.reduce((a,b)=>a+b,0)/5,stars=team.stars!.reduce((a,b)=>a+b,0)/5;
   if(row.order===1&&!seen.has(row.stage_id)){seen.add(row.stage_id);entries.push({chapter:row.chapter,day,mean_stars:stars,mean_level:mean,team});}
   if(!firstSeen.has(row.stage_id)){firstSeen.add(row.stage_id);firstChallenges.push({stage_id:row.stage_id,campaign:camp,chapter:row.chapter,order:row.order,day,team:structuredClone(team),pool:heroTeam(save,camp,ownedHeroes(save,camp)),inventory:structuredClone(campGrowth(save,camp).gear),current:[...advice!.heroes],mean_level:mean,mean_stars:stars,power:armyPower(team),wallet:{...campGrowth(save,camp).wallet}});}
   let victory=mode==='profile'?mean>=assumedLevel(row.chapter,row.order):false;
   if(mode==='battle'){for(let retry=0;retry<attemptCap;retry++){attempts++;const log=runBattle(team,enemy,row.terrain as Terrain,(seed*977+attempts)>>>0,{allowDuplicates:true,trace:false});if(log.winner===0){victory=true;break;}failures++;}}
   if(!victory)break;
   const waited=day-lastAdvance;maxWait=Math.max(maxWait,waited);if(waited>2)waits.push({stage_id:row.stage_id,wait:waited,day,levels:team.levels,stars:team.stars,heroes:team.heroes});profiles.push({stage_id:row.stage_id,campaign:camp,chapter:row.chapter,order:row.order,day,assumed_level:assumedLevel(row.chapter,row.order),team,pool:heroTeam(save,camp,ownedHeroes(save,camp)),inventory:structuredClone(campGrowth(save,camp).gear),current:advice!.heroes,mean_level:mean,mean_stars:stars,power:armyPower(team),forecast:{wins:advice!.wins,trials:advice!.trials,candidates:advice!.candidates},wallet:{...campGrowth(save,camp).wallet}});
   const won=completeStage(save,row);save=won.save;grant(won.grant,'first');index++;lastAdvance=day;sweepAll(now);recruitAll();
   if(row.order===6){save=spend(save,camp);const c=campGrowth(save,camp);chapters.push({chapter:row.chapter,day,duration:day-lastEnd,target_days:economy(row.chapter).target_days,remaining:{...c.wallet},produced:{...chapterIncome},exp_remaining_ratio:c.wallet.exp/Math.max(1,chapterIncome.exp),exp_sources:{...sources},max_stage_wait:maxWait,main:save.formations[camp].map(id=>({id,...c.heroes[id]}))});lastEnd=day;chapterIncome={exp:0,silver:0,iron:0,tickets:0};sources={idle:0,first:0,sweep:0,feast:0};maxWait=0;}
  }
  sessionWallets.push({day,...campGrowth(save,camp).wallet});
 }
 return{campaign:camp,seed,cleared:index,days:lastAdvance,stuck_stage:stages[index]?.stage_id??null,attempts,failures,chapters,entries,profiles,first_challenges:firstChallenges,waits,total_sweeps:totalSweeps,max_daily_sweeps:maxDailySweeps,session_wallets:sessionWallets,final_heroes:campGrowth(save,camp).heroes,final_shards:campGrowth(save,camp).shards,feast_profile:feastProfile,feast_purchases:feastPurchases,...(traceEarly?{early_feast_offers:earlyFeastOffers}:{} )};
}
const camps=(arg.camp?[arg.camp]:['taiping','qing'])as Campaign[],runs:any[]=[];for(const camp of camps)for(let i=0;i<count;i++){const run=simulate(camp,startSeed+i);runs.push(run);console.log(JSON.stringify({camp,seed:run.seed,cleared:run.cleared,days:run.days,chapter_days:run.chapters.map((r:any)=>r.duration),entry_stars:run.entries.filter((r:any)=>[4,6,8].includes(r.chapter)).map((r:any)=>[r.chapter,r.mean_stars])}));}
const out=arg.out??'assets/reports/joint_v2/behavior.json';fs.mkdirSync(out.slice(0,out.lastIndexOf('/')),{recursive:true});fs.writeFileSync(out,JSON.stringify({mode,count_per_campaign:count,seed:startSeed,attempt_cap:attemptCap,forecast_battles:forecasts,advisor:{candidates:20,trials:20,independent_seed:0x18515678},login_hours:[8,14],effective_idle_hours_per_day:18,input_sha256:Object.fromEntries(['economy_chapters','star_up','stages','enemy_units','stage_level_overrides','feast'].map(key=>[key,createHash('sha256').update(JSON.stringify((db as any)[key])).digest('hex')])),runs},null,2));
