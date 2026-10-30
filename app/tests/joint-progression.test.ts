import {newSave} from './legacy-fixture';
import {describe,it,expect} from 'vitest';
import {database as db} from '../src/core/data';
import {allStages,completeStage,stageTeams,validSave} from '../src/core/campaign';
import {campGrowth,sweep,sweepRemaining,dailySweepRemaining,heroTeam,acquire,levelCap} from '../src/core/progression';
import {recommendFormation,formationCandidates,normalizeLevels} from '../src/core/formation';
import {runBattle} from '../src/core/battle/engine';
const now=new Date(2026,0,1,8).getTime();
describe('v0.2 joint economy and formation rules',()=>{
 it('shares exactly30 daily sweeps across campaigns and resets only at the next local date',()=>{let s=newSave(now);for(const camp of ['taiping','qing']as const)for(const row of allStages(camp).slice(0,6))s=completeStage(s,row).save;
  for(const row of allStages('taiping').slice(0,6))for(let n=0;n<3;n++)s=sweep(s,row,now).save;
  for(const row of allStages('qing').slice(0,4))for(let n=0;n<3;n++)s=sweep(s,row,now).save;
  expect(dailySweepRemaining(s,now)).toBe(0);expect(sweepRemaining(s,allStages('qing')[4],now)).toBe(0);expect(()=>sweep(s,allStages('qing')[4],now)).toThrow('30');expect(dailySweepRemaining(s,now+86400000)).toBe(30);expect(dailySweepRemaining(s,now-86400000)).toBe(0);expect(validSave(s)).toBe(true);
 });
 it('preserves already-over-budget legacy counters and grants no further attempts that day',()=>{const s=newSave(now),c=campGrowth(s,'taiping');for(const row of allStages('taiping').slice(0,12))c.daily.uses[row.stage_id]=3;expect(validSave(s)).toBe(true);expect(dailySweepRemaining(s,now)).toBe(0);expect(Object.values(c.daily.uses).reduce((a,b)=>a+b,0)).toBe(36);});
 it('fast forecast and animated battle have identical outcomes and do not mutate team inputs',()=>{const s=newSave(now),[a,b]=stageTeams(allStages('taiping')[0],s.formations.taiping,s),raw=JSON.stringify([a,b]);for(let seed=10;seed<30;seed++){const full=runBattle(a,b,'陆战',seed,{allowDuplicates:true}),fast=runBattle(a,b,'陆战',seed,{allowDuplicates:true,trace:false});expect({...full,trace:[]}).toEqual(fast);expect(fast.trace).toEqual([]);}expect(JSON.stringify([a,b])).toBe(raw);});
 it('uses deterministic independent forecasts, legal owned formations and at least the current forecast win count',()=>{const s=newSave(now),ids=Object.keys(campGrowth(s,'taiping').heroes).filter(id=>id!=='tp_hong_xiuquan'),pool=heroTeam(s,'taiping',ids),enemy=stageTeams(allStages('taiping')[0],s.formations.taiping,s)[1],before=JSON.stringify(s);const advice=recommendFormation(pool,enemy,'陆战',{current:s.formations.taiping});expect(advice.candidates).toBe(20);expect(advice.trials).toBe(20);expect(new Set(advice.heroes).size).toBe(5);expect(advice.heroes.every(id=>ids.includes(id))).toBe(true);const again=recommendFormation(pool,enemy,'陆战',{current:s.formations.taiping});expect(again).toEqual(advice);expect(JSON.stringify(s)).toBe(before);let wins=0;for(let n=0;n<20;n++)wins+=Number(runBattle(heroTeam(s,'taiping',s.formations.taiping),enemy,'陆战',advice.forecastSeed+n,{allowDuplicates:true,trace:false}).winner===0);expect(advice.wins).toBeGreaterThanOrEqual(wins);expect(formationCandidates(pool,enemy,'水战').length).toBe(20);});
 it('selects water specialists in water terrain and changes lineups against different troop counters',()=>{
  const s=newSave(now),c=campGrowth(s,'qing');for(const h of db.heroes.filter(h=>h.faction==='qing'&&h.position!=='君主')){acquire(c,h.id);c.heroes[h.id].level=Math.min(50,levelCap(c.heroes[h.id].stars));}
  const pool=heroTeam(s,'qing',Object.keys(c.heroes).filter(id=>db.heroes.find(h=>h.id===id)!.position!=='君主')),enemy={heroes:['tp_shi_dakai','tp_xiao_chaogui','tp_li_xiucheng','tp_chen_yucheng','tp_luo_dagang'],faction:'taiping'as const,levels:[50,50,50,50,50],stars:[3,3,3,3,3],monarch:'tp_hong_xiuquan'};
  const water=recommendFormation(pool,enemy,'水战'),land=recommendFormation(pool,enemy,'陆战');expect(water.heroes).toContain('qing_peng_yulin');expect(water.heroes).toContain('qing_yang_zaifu');expect(water.heroes).not.toEqual(land.heroes);
  const vsInfantry=recommendFormation(pool,{...enemy,heroes:Array(5).fill('tp_npc_shengbing')},'陆战'),vsFire=recommendFormation(pool,{...enemy,heroes:Array(5).fill('tp_npc_qiangshou')},'陆战');expect(vsInfantry.heroes).not.toEqual(vsFire.heroes);const count=(ids:string[],troop:string)=>ids.filter(id=>db.heroes.find(h=>h.id===id)!.troop===troop).length;expect(count(vsInfantry.heroes,'骑')).toBeGreaterThan(count(vsFire.heroes,'骑'));expect(count(vsFire.heroes,'步')).toBeGreaterThan(count(vsInfantry.heroes,'步'));
 });
 it('keeps the revised three-to-four-star shard price at50',()=>expect(db.star_up.find(r=>r.star_from===3)!.shards).toBe(50));
 it('forecasts with the same existing equipment that the button transfers, without spending or changing RNG',()=>{
  let s=newSave(now);for(const row of allStages('taiping').slice(0,6))s=completeStage(s,row).save;
  const c=campGrowth(s,'taiping'),pool=heroTeam(s,'taiping',Object.keys(c.heroes).filter(id=>id!=='tp_hong_xiuquan')),before=JSON.stringify(s),enemy=stageTeams(allStages('taiping')[6],s.formations.taiping,s)[1];
  const advice=recommendFormation(pool,enemy,'水战',{current:s.formations.taiping,inventory:c.gear});expect(JSON.stringify(s)).toBe(before);
  const next=structuredClone(s);next.formations.taiping=advice.heroes;for(const g of campGrowth(next,'taiping').gear)g.owner=advice.equipmentOwners![g.uid];
  expect(validSave(next)).toBe(true);expect(heroTeam(next,'taiping',advice.heroes)).toEqual(advice.team);
  expect({...campGrowth(next,'taiping'),gear:c.gear}).toEqual(c);expect(campGrowth(next,'taiping').gear.map(g=>({...g,owner:null}))).toEqual(c.gear.map(g=>({...g,owner:null})));
 });
 it('normalizes the stated five-person mean without exceeding individual star caps',()=>{
  const s=newSave(now),team=heroTeam(s,'taiping',s.formations.taiping);team.stars=[3,3,4,4,5];team.levels=[60,50,70,75,80];const next=normalizeLevels(team,70);expect(next.levels!.reduce((a,b)=>a+b,0)/5).toBe(70);expect(next.levels!.every((n,i)=>Number.isInteger(n)&&n<=levelCap(next.stars![i]))).toBe(true);expect(()=>normalizeLevels({...team,stars:[1,1,1,1,1]},70)).toThrow();
 });

});
