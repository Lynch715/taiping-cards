/** Player model calls the shipped economy functions and battle engine directly. */
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {database as db} from '../app/src/core/data';
import {newSave,completeStage} from '../app/src/core/campaign';
import type {Save} from '../app/src/core/campaign';
import type {Campaign,TeamInput,Terrain} from '../app/src/core/battle/types';
import {runBattle,combatBaseStats} from '../app/src/core/battle/engine';
import {rawUnitPower,armyPower} from '../app/src/core/power';
import {acquire,assumedLevel,campGrowth,claimIdle,economy,enhanceGear,equipmentRow,heroRow,heroTeam,levelCap,levelCost,promote,recruit,rewardClear,salvage,sweep,sweepRemaining,train,transfer} from '../app/src/core/progression';
const args=Object.fromEntries(process.argv.slice(2).map(s=>{const i=s.indexOf('=');return [s.slice(0,i),s.slice(i+1)];}));
if(args.tables){const tables=JSON.parse(fs.readFileSync(args.tables,'utf8'));db.economy_chapters=tables.economy_chapters;db.star_up=tables.star_up;}
const mode=args.mode??'profile',count=Number(args.n??1),startSeed=Number(args.seed??41000),maxDays=Number(args.days??80),maxChapter=Number(args.chapters??8),attemptCap=Number(args.attempts??3),out=args.out??'assets/reports/progression/behavior.json';
const start=new Date(2026,0,1,8).getTime();
function strongest(save:Save,camp:Campaign){const c=campGrowth(save,camp);const ids=Object.keys(c.heroes).filter(id=>heroRow(id).position!=='君主').sort((a,b)=>rawUnitPower({heroes:[b],levels:[c.heroes[b].level],stars:[c.heroes[b].stars],exclusives:[c.heroes[b].stars>=4],faction:camp},0)-rawUnitPower({heroes:[a],levels:[c.heroes[a].level],stars:[c.heroes[a].stars],exclusives:[c.heroes[a].stars>=4],faction:camp},0));const top=ids.slice(0,5);top.sort((a,b)=>{const stat=(id:string)=>combatBaseStats(heroRow(id),c.heroes[id].level,c.heroes[id].stars,[],0,false).hp;return stat(b)-stat(a);});return {main:top,reserves:ids.filter(id=>!top.includes(id)).slice(0,2)};}
function kit(save:Save,camp:Campaign){let c=campGrowth(save,camp);const main=strongest(save,camp).main;save.formations[camp]=main;
 // Flat stat equipment contributes identically to the specified power formula for each hero.
 const selected=new Set<string>();for(const slot of ['兵刃','甲胄','坐骑','兵书']){const items=c.gear.filter(g=>equipmentRow(g).slot===slot).sort((a,b)=>{const score=(g:typeof a)=>{const row=equipmentRow(g),weights:Record<string,number>={'生命':.2,'攻击':1.5,'物防':1,'谋防':1,'速度':10,'暴击率%':0,'开场怒气':0};return (row.main_value*weights[row.main_stat]+row.sub_value*weights[row.sub_stat])*(1+.1*g.enhance);};return score(b)-score(a);}).slice(0,5);for(const [i,g]of items.entries()){save=transfer(save,camp,g.uid,main[i]);selected.add(g.uid);}}
 c=campGrowth(save,camp);const unused=c.gear.filter(g=>!selected.has(g.uid));if(unused.length){for(const g of unused)if(g.owner)save=transfer(save,camp,g.uid,null);save=salvage(save,camp,unused.map(g=>g.uid)).save;}return save;
}
function spend(save:Save,camp:Campaign,target:number){let selected=strongest(save,camp);const goal=Math.max(10,Math.ceil(target));
 for(let loop=0;loop<1200;loop++){let changed=false,c=campGrowth(save,camp);selected=strongest(save,camp);const priority=[...selected.main,...selected.reserves].sort((a,b)=>(c.heroes[a].level+(selected.main.includes(a)?0:2))-(c.heroes[b].level+(selected.main.includes(b)?0:2)));
  for(const id of priority){c=campGrowth(save,camp);const h=c.heroes[id],desired=100;if(h.level<desired&&h.level<levelCap(h.stars)&&c.wallet.exp>=levelCost(h.level)){save=train(save,camp,id).save;changed=true;break;}}
  if(changed)continue;
  for(const id of [...selected.main,...selected.reserves]){try{save=promote(save,camp,id);changed=true;break;}catch{/* save resources until a legal star promotion */}}
  if(!changed)break;
 }
 save=kit(save,camp);for(let loop=0;loop<1500;loop++){const c=campGrowth(save,camp),items=c.gear.filter(g=>g.owner).sort((a,b)=>a.enhance-b.enhance);let changed=false;for(const g of items){try{save=enhanceGear(save,camp,g.uid);changed=true;break;}catch{/* next affordable item */}}if(!changed)break;}return save;
}
function simulate(camp:Campaign,seed:number){let save=newSave(start,seed);save.campaign=camp;campGrowth(save,camp).rng=seed>>>0;const stages=db.stages.filter(s=>s.campaign===camp&&s.chapter<=maxChapter).sort((a,b)=>a.chapter-b.chapter||a.order-b.order),profiles:any[]=[],chapters:any[]=[],events:any[]=[];
 let index=0,lastEnd=0,stageWait=0,lastAdvance=0,maxWait=0,attempts=0,failures=0;const stageAttempts:Record<string,number>={};let source={idle:0,first:0,sweep:0},produced={exp:0,silver:0,iron:0,tickets:0},starMilestones:any[]=[],silverZero=0,ironZero=0;
 function record(grant:{exp:number;silver:number;iron:number;tickets:number},kind:keyof typeof source){source[kind]+=grant.exp;for(const k of ['exp','silver','iron','tickets']as const)produced[k]+=grant[k];}
 function summonAll(){while(campGrowth(save,camp).wallet.tickets>0){const n=campGrowth(save,camp).wallet.tickets>=10?10:1;save=recruit(save,camp,n).save;}}
 function sweepAll(now:number){for(const row of stages.slice(0,index))while(sweepRemaining(save,row,now)>0){const r=sweep(save,row,now);save=r.save;record(r.grant,'sweep');}save=kit(save,camp);}
 for(let session=0;session<maxDays*2+1&&index<stages.length;session++){
  const day=Math.floor(session/2)+(session%2?.25:0),now=start+day*86400000;const idle=claimIdle(save,camp,now);save=idle.save;record(idle.grant,'idle');sweepAll(now);summonAll();
  for(let turn=0;turn<48&&index<stages.length;turn++){
   const row=stages[index],target=assumedLevel(row.chapter,row.order);save=spend(save,camp,target);const c=campGrowth(save,camp),team=heroTeam(save,camp,save.formations[camp]);const mean=team.levels!.reduce((n,x)=>n+x,0)/5;
   let victory=false;
   if(mode==='profile')victory=mean+1e-8>=target;
   else {if(row.enemy_level===null)throw Error('Uncalibrated '+row.stage_id);const foes=row.enemies.split(','),enemy:TeamInput={heroes:foes,monarch:row.enemy_monarch||null,faction:camp==='taiping'?'qing':'taiping',levels:foes.map(()=>row.enemy_level!),stars:row.enemy_stars.split(';').map(Number),exclusives:row.enemy_stars.split(';').map(s=>Number(s)>=4),monarchStars:row.enemy_monarch_stars??3,monarchExclusive:(row.enemy_monarch_stars??3)>=4};for(let retry=0;retry<attemptCap;retry++){attempts++;stageAttempts[row.stage_id]=(stageAttempts[row.stage_id]??0)+1;const battle=runBattle(team,enemy,row.terrain as Terrain,(seed*977+attempts)>>>0,{allowDuplicates:true});if(battle.winner===0){victory=true;break;}failures++;}}
   if(!victory)break;
   const waited=day-lastAdvance;maxWait=Math.max(maxWait,waited);profiles.push({stage_id:row.stage_id,campaign:camp,chapter:row.chapter,order:row.order,day,assumed_level:target,team,mean_level:mean,power:armyPower(team),wallet:{...c.wallet}});
   const pending={...save,progress:{...save.progress,[camp]:[...save.progress[camp],row.stage_id]}};const won=rewardClear(pending,row,true);save=won.save;record(won.grant,'first');index++;lastAdvance=day;sweepAll(now);summonAll();
   if(row.order===6){save=spend(save,camp,target);const state=campGrowth(save,camp),selection=strongest(save,camp);const spentExp=produced.exp-state.wallet.exp,ratio=state.wallet.exp/Math.max(1,produced.exp);chapters.push({chapter:row.chapter,day,duration:day-lastEnd,target_days:economy(row.chapter).target_days,remaining:{...state.wallet},produced:{...produced},exp_remaining_ratio:ratio,exp_sources:{...source},max_stage_wait:maxWait,main:selection.main.map(id=>({id,...state.heroes[id]})),reserves:selection.reserves.map(id=>({id,...state.heroes[id]})),stars_ready:selection.main.every(id=>state.heroes[id].level<=levelCap(state.heroes[id].stars)),power:armyPower(heroTeam(save,camp,selection.main))});lastEnd=day;produced={exp:0,silver:0,iron:0,tickets:0};source={idle:0,first:0,sweep:0};maxWait=0;}
  }
  const c=campGrowth(save,camp);silverZero+=Number(c.wallet.silver===0);ironZero+=Number(c.wallet.iron===0);
 }
 return {campaign:camp,seed,cleared:index,days:lastAdvance,attempts,failures,chapters,profiles,stuck_stage:stages[index]?.stage_id??null,silver_zero_sessions:silverZero,iron_zero_sessions:ironZero,stage_attempts:stageAttempts,final_wallet:campGrowth(save,camp).wallet,final_heroes:campGrowth(save,camp).heroes,final_shards:campGrowth(save,camp).shards};
}
const runs:any[]=[];for(const camp of ['taiping','qing']as const)for(let i=0;i<count;i++)runs.push(simulate(camp,startSeed+i));fs.mkdirSync(out.slice(0,out.lastIndexOf('/')),{recursive:true});fs.writeFileSync(out,JSON.stringify({mode,count_per_campaign:count,seed:startSeed,attempt_cap:attemptCap,login_hours:[8,14],effective_idle_hours_per_day:18,input_sha256:Object.fromEntries(['economy_chapters','star_up','stages'].map(name=>[name,createHash('sha256').update(JSON.stringify(db[name as 'economy_chapters'|'star_up'|'stages'])).digest('hex')])),tables_override:args.tables??null,runs},null,2));console.log(JSON.stringify(runs.map(r=>({camp:r.campaign,seed:r.seed,cleared:r.cleared,days:r.days,durations:r.chapters.map((c:any)=>c.duration),stuck:r.stuck_stage}))));
