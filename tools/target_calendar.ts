/** Resource forecast on a fixed target calendar. No feasts, battle wins, or future rewards. */
import fs from 'node:fs';
import {database as db}from '../app/src/core/data';
import {newSave,ownedHeroes,completeStage,stageTeams}from '../app/src/core/campaign';
import type {Campaign,Terrain}from '../app/src/core/battle/types';
import {campGrowth,claimIdle,heroTeam,recruit,economy}from '../app/src/core/progression';
import {recommendFormation}from '../app/src/core/formation';
import {armyPower}from '../app/src/core/power';
import {spendCore,sweepByPolicy}from './player_policy';
import {targetArrivalDay}from './target_calendar_rules';
const arg=Object.fromEntries(process.argv.slice(2).map(s=>{const i=s.indexOf('=');return[s.slice(0,i),s.slice(i+1)];}));
if(arg.tables){const t=JSON.parse(fs.readFileSync(arg.tables,'utf8'));for(const key of ['economy_chapters','star_up','stages','enemy_units','stage_level_overrides','feast']as const)if(t[key])(db as any)[key]=t[key];}
const start=new Date(2026,0,1,8).getTime(),camp=arg.camp as Campaign,seed=Number(arg.seed),count=Number(arg.n??1),runs:any[]=[];
for(let account=0;account<count;account++){
 let save=newSave(start,seed+account),nextSession=0,index=0,sweeps=0;save.campaign=camp;
 const profiles:any[]=[],claims:any[]=[],stages=db.stages.filter(s=>s.campaign===camp).sort((a,b)=>a.chapter-b.chapter||a.order-b.order);
 const recruitAll=()=>{while(campGrowth(save,camp).wallet.tickets){const n=campGrowth(save,camp).wallet.tickets>=10?10:1;save=recruit(save,camp,n).save;}};
 for(const row of stages){
  const day=targetArrivalDay(db.economy_chapters.map(r=>r.target_days),row.chapter,row.order);
  // Exactly the same two idle/sweep logins as the live model. Never claim at a later login.
  while(Math.floor(nextSession/2)+(nextSession%2?.25:0)<=day+1e-9){
   const login=Math.floor(nextSession/2)+(nextSession%2?.25:0),now=start+login*86400000;
   const idle=claimIdle(save,camp,now);save=idle.save;const swept=sweepByPolicy(save,camp,stages,index,now);save=swept.save;sweeps+=swept.count;recruitAll();save=spendCore(save,camp);
   claims.push({day:login,hours:idle.grant.hours,exp:idle.grant.exp,sweeps:swept.count});nextSession++;
  }
  save=spendCore(save,camp);let pool=heroTeam(save,camp,ownedHeroes(save,camp));const enemy=stageTeams(row,save.formations[camp],save)[1];let advice;
  for(let planning=0;planning<3;planning++){
   advice=recommendFormation(pool,enemy,row.terrain as Terrain,{current:save.formations[camp],inventory:campGrowth(save,camp).gear});
   const old=new Set(save.formations[camp]);save.formations[camp]=advice.heroes;for(const g of campGrowth(save,camp).gear)if(advice.equipmentOwners&&g.uid in advice.equipmentOwners)g.owner=advice.equipmentOwners[g.uid];
   if(!advice.heroes.some(id=>!old.has(id)))break;const previous=JSON.stringify(pool);save=spendCore(save,camp);pool=heroTeam(save,camp,ownedHeroes(save,camp));if(JSON.stringify(pool)===previous)break;
  }
  const team=heroTeam(save,camp,advice!.heroes),c=campGrowth(save,camp);
  profiles.push({stage_id:row.stage_id,campaign:camp,chapter:row.chapter,order:row.order,day,team:structuredClone(team),pool:heroTeam(save,camp,ownedHeroes(save,camp)),inventory:structuredClone(c.gear),mean_level:team.levels!.reduce((a,b)=>a+b,0)/5,mean_stars:team.stars!.reduce((a,b)=>a+b,0)/5,power:armyPower(team),wallet:{...c.wallet},cleared_before:save.progress[camp].length,completed_rewards:save.progress[camp].slice()});
  // The scheduled clear is an economic assumption, not an observed victory. Its reward arrives AFTER this stage's snapshot.
  save=completeStage(save,row).save;recruitAll();index++;
 }
 runs.push({campaign:camp,seed:seed+account,profiles,claims,total_sweeps:sweeps});console.log(JSON.stringify({camp,seed:seed+account,stages:profiles.length,last_mean:profiles.at(-1).mean_level}));
}
fs.writeFileSync(arg.out,JSON.stringify({mode:'target-calendar',feast:'off',login_days:[0,.25],runs},null,2));
