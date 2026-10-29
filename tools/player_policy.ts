/** Shared player policy; no budget, reward, sweep or hero rules live here. */
import type {Stage}from '../app/src/core/data/types';
import type {Save}from '../app/src/core/campaign';
import {ownedHeroes}from '../app/src/core/campaign';
import type {Campaign}from '../app/src/core/battle/types';
import {rawUnitPower}from '../app/src/core/power';
import {campGrowth,heroTeam,levelCost,levelCap,train,promote,transfer,salvage,equipmentRow,enhanceGear,buyFeast,feastPreview,sweep,sweepRemaining,dailySweepRemaining,starRule,assumedLevel}from '../app/src/core/progression';
import type {FeastProfile}from '../app/src/core/progression';
function reserves(save:Save,camp:Campaign){const c=campGrowth(save,camp);return ownedHeroes(save,camp).filter(id=>!save.formations[camp].includes(id)).sort((a,b)=>rawUnitPower(heroTeam(save,camp,[b]),0)-rawUnitPower(heroTeam(save,camp,[a]),0)).slice(0,2);}
function kit(save:Save,camp:Campaign){const c=campGrowth(save,camp),main=save.formations[camp],selected=new Set<string>();for(const slot of ['兵刃','甲胄','坐骑','兵书']){const items=c.gear.filter(g=>equipmentRow(g).slot===slot).sort((a,b)=>{const score=(g:typeof a)=>{const r=equipmentRow(g),w:Record<string,number>={'生命':.2,'攻击':1.5,'物防':1,'谋防':1,'速度':10,'暴击率%':0,'开场怒气':0};return(r.main_value*w[r.main_stat]+r.sub_value*w[r.sub_stat])*(1+.1*g.enhance);};return score(b)-score(a);}).slice(0,5);for(const[i,g]of items.entries()){save=transfer(save,camp,g.uid,main[i]);selected.add(g.uid);}}
 const unused=campGrowth(save,camp).gear.filter(g=>!selected.has(g.uid));if(unused.length){for(const g of unused)if(g.owner)save=transfer(save,camp,g.uid,null);save=salvage(save,camp,unused.map(g=>g.uid)).save;}return save;
}
export function spendCore(save:Save,camp:Campaign){const main=save.formations[camp],bench=reserves(save,camp);
 for(let loop=0;loop<1500;loop++){let changed=false;const c=campGrowth(save,camp),ids=[...main,...bench].sort((a,b)=>(c.heroes[a].level+(main.includes(a)?0:2))-(c.heroes[b].level+(main.includes(b)?0:2)));
  for(const id of ids){const h=c.heroes[id];if(h.level<levelCap(h.stars)&&c.wallet.exp>=levelCost(h.level)){save=train(save,camp,id).save;changed=true;break;}}if(changed)continue;
  for(const id of [...main,...bench]){try{save=promote(save,camp,id);changed=true;break;}catch{}}if(!changed)break;
 }
 save=kit(save,camp);for(let loop=0;loop<1500;loop++){let changed=false;for(const g of [...campGrowth(save,camp).gear].filter(g=>g.owner).sort((a,b)=>a.enhance-b.enhance)){try{save=enhanceGear(save,camp,g.uid);changed=true;break;}catch{}}if(!changed)break;}return save;
}

export function spend(save:Save,camp:Campaign,now:number,profile:FeastProfile|'off'='off',onPurchase?:(r:ReturnType<typeof buyFeast>)=>void,onOffer?:(save:Save,offer:ReturnType<typeof feastPreview>)=>void){
 save=spendCore(save,camp);
 if(profile!=='off')for(let i=0;i<10;i++){
  const r=feastPreview(save,camp,now,profile);if(!r.remaining)break;onOffer?.(save,r);if(campGrowth(save,camp).wallet.silver<r.silver)break;
  const purchase=buyFeast(save,camp,now,profile);onPurchase?.(purchase);save=spendCore(purchase.save,camp);
 }
 return save;
}

export function sweepByPolicy(save:Save,camp:Campaign,stages:Stage[],index:number,now:number){
 const cleared=stages.slice(0,index),grants=[];let used=0;
 while(cleared.length&&dailySweepRemaining(save,now)>0){const c=campGrowth(save,camp),main=save.formations[camp],eligible=cleared.filter(r=>sweepRemaining(save,r,now)>0);if(!eligible.length)break;
  const needs=new Map(main.flatMap(id=>{const h=c.heroes[id],rule=starRule(h.stars);return rule&&(c.shards[id]??0)<rule.shards?[[id,levelCap(h.stars)<assumedLevel(stages[index]?.chapter??8,stages[index]?.order??6)?12:h.level>=levelCap(h.stars)-5?5:1]as const]:[]}));
  eligible.sort((a,b)=>{const deficit=(r:Stage)=>r.shard_drops.split(';').reduce((sum,id)=>sum+(needs.get(id)??0),0)/Math.max(1,r.shard_drops.split(';').length);const score=(r:Stage)=>(used>=18?deficit(r)*10000:0)+r.chapter*100+r.order;return score(b)-score(a);});
  const r=sweep(save,eligible[0],now);save=r.save;grants.push(r.grant);used++;
 }return {save,grants,count:used};
}
