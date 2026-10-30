/** Same deterministic advisor for the product and the player model. Never consumes the battle/save RNG. */
import {database as db} from './data';
import type {Campaign,Terrain,TeamInput} from './battle/types';
import {runBattle,activeBonds,combatBaseStats} from './battle/engine';
import type {GearItem} from './progression';
import {armyPower,rawUnitPower} from './power';
export interface FormationPool {team:TeamInput}
export interface FormationAdvice {heroes:string[];monarch:string|null;team:TeamInput;wins:number;trials:number;candidates:number;forecastSeed:number;rounds:number;equipmentOwners?:Record<string,string|null>}
export const ADVISOR_CANDIDATES=20,ADVISOR_TRIALS=20,ADVISOR_SEED=0x18515678;
export function subset(pool:TeamInput,ids:string[]):TeamInput{const indices=ids.map(id=>pool.heroes.indexOf(id));if(indices.some(i=>i<0))throw Error('推荐包含未拥有的武将');return {...pool,heroes:[...ids],troopRatios:pool.troopRatios&&indices.map(i=>pool.troopRatios![i]),levels:pool.levels&&indices.map(i=>pool.levels![i]),stars:pool.stars&&indices.map(i=>pool.stars![i]),gear:pool.gear&&indices.map(i=>pool.gear![i]),exclusives:pool.exclusives&&indices.map(i=>pool.exclusives![i])};}
const hero=(id:string)=>db.heroes.find(h=>h.id===id)??db.enemy_units.find(h=>h.id===id)!;
function synergy(team:TeamInput,terrain:Terrain){return activeBonds(team).reduce((n,b)=>{if(b.type==='负面')return n-9;const a=b._ast;if(a.kind==='water_first'&&terrain!=='水战'||a.kind==='defend_aura'&&terrain!=='守城'||a.kind==='siege_aura'&&terrain!=='攻城')return n;return n+3+(b.tier+1)*2;},0);}
export function formationCandidates(pool:TeamInput,enemy:TeamInput,terrain:Terrain,limit=ADVISOR_CANDIDATES,size=Math.min(5,pool.heroes.length)):TeamInput[]{
 if(pool.heroes.length<size||new Set(pool.heroes).size!==pool.heroes.length)throw Error('智能布阵需要至少五名不同武将');
 const counts=enemy.heroes.map(id=>hero(id).troop),scores=new Map(pool.heroes.map((id,i)=>{const h=hero(id),base=rawUnitPower(pool,i);let m=h.troop==='水'?(terrain==='水战'?1.2:.93):1;m+=counts.filter(t=>['骑步','步火','火骑'].includes(h.troop+t)).length*.024;return [id,base*m]as const;}));
 // Bounded roster shortlist; retains the strongest available specialist of each troop.
 const ranked=[...pool.heroes].sort((a,b)=>scores.get(b)!-scores.get(a)!||a.localeCompare(b)),short=ranked.slice(0,9);
 for(const troop of ['步','骑','水','火','谋']){const id=ranked.find(id=>hero(id).troop===troop);if(id&&!short.includes(id))short.push(id);}
 const sets:{ids:string[];score:number}[]=[];function combinations(start:number,ids:string[],sum:number){if(ids.length===size){const team=subset(pool,ids),bonus=synergy(team,terrain);sets.push({ids:[...ids],score:sum*(1+bonus/100)});return;}for(let i=start;i<=short.length-(size-ids.length);i++)combinations(i+1,[...ids,short[i]],sum+scores.get(short[i])!);}
 combinations(0,[],0);sets.sort((a,b)=>b.score-a.score||a.ids.join().localeCompare(b.ids.join()));
 const result:TeamInput[]=[],keys=new Set<string>();
 for(const entry of sets.slice(0,limit)){
  const tank=(id:string)=>{const i=pool.heroes.indexOf(id),h=hero(id);return combatBaseStats(h as typeof db.heroes[number],pool.levels?.[i]??10,pool.stars?.[i]??1,[],0,false).hp*(h.troop==='步'?1.12:1);};
  const ordered=[...entry.ids].sort((a,b)=>tank(b)-tank(a)||a.localeCompare(b));
  for(const ids of [ordered,[ordered[0],ordered[2],ordered[1],...ordered.slice(3)].filter((id):id is string=>!!id)]){const key=ids.join('|');if(!keys.has(key)){keys.add(key);result.push(subset(pool,ids));}}
 }
 // Half the budget covers different compositions; half tests alternate front/back positions.
 return [...result.filter((_,i)=>i%2===0).slice(0,Math.ceil(limit/2)),...result.filter((_,i)=>i%2===1).slice(0,Math.floor(limit/2))].slice(0,limit);
}
export function recommendFormation(pool:TeamInput,enemy:TeamInput,terrain:Terrain,options:{candidates?:number;trials?:number;seed?:number;current?:string[];inventory?:GearItem[];slots?:number}={}):FormationAdvice{
 const trials=options.trials??ADVISOR_TRIALS,seed=(options.seed??ADVISOR_SEED)>>>0,candidates=formationCandidates(options.inventory?{...pool,gear:pool.heroes.map(()=>[])}:pool,enemy,terrain,options.candidates??ADVISOR_CANDIDATES,options.slots??Math.min(5,pool.heroes.length));if(options.current&&options.current.length===(options.slots??Math.min(5,pool.heroes.length))&&new Set(options.current).size===options.current.length&&options.current.every(id=>pool.heroes.includes(id))&&!candidates.some(t=>t.heroes.join()===options.current!.join()))candidates[candidates.length-1]=subset(pool,options.current);if(!Number.isInteger(trials)||trials<1||trials>1000)throw Error('试算局数无效');
 const prepared=options.inventory?candidates.map(t=>allocateEquipment(t,options.inventory!).team):candidates;const advice=evaluateFormations(prepared,enemy,terrain,{trials,seed});if(options.inventory)advice.equipmentOwners=allocateEquipment(advice.team,options.inventory).owners;return advice;
}
export function evaluateFormations(candidates:TeamInput[],enemy:TeamInput,terrain:Terrain,options:{trials?:number;seed?:number}={}):FormationAdvice{
 const trials=options.trials??ADVISOR_TRIALS,seed=(options.seed??ADVISOR_SEED)>>>0;if(!candidates.length)throw Error('没有满足星级等级上限的候选阵容');
 let best:FormationAdvice|undefined,bestQuality=-Infinity;for(const team of candidates){let wins=0,rounds=0,quality=0;for(let n=0;n<trials;n++){const log=runBattle(team,enemy,terrain,(seed+n)>>>0,{allowDuplicates:true,trace:false});wins+=Number(log.winner===0);rounds+=log.rounds;quality+=log.survivors[0].length-log.survivors[1].length;}const advice={heroes:team.heroes,monarch:team.monarch??null,team,wins,trials,candidates:candidates.length,forecastSeed:seed,rounds:rounds/trials};if(!best||wins>best.wins||wins===best.wins&&(quality>bestQuality||quality===bestQuality&&((wins?advice.rounds<best.rounds:advice.rounds>best.rounds)||advice.rounds===best.rounds&&armyPower(team)>armyPower(best.team)))){best=advice;bestQuality=quality;}}
 return best!;
}

/** Calibration only: legal integer individual levels with the exact specified five-person mean. */
export function normalizeLevels(team:TeamInput,mean:number):TeamInput{
 const cap=(s:number)=>({1:35,2:50,3:65,4:80,5:95,6:100}[s]!);const stars=team.stars??team.heroes.map(()=>1),original=team.levels??team.heroes.map(()=>mean),delta=mean-original.reduce((a,b)=>a+b,0)/5,levels=original.map((n,i)=>Math.max(1,Math.min(cap(stars[i]),n+delta)));
 for(let step=0;step<20;step++){const left=mean*5-levels.reduce((a,b)=>a+b,0);if(Math.abs(left)<1e-8)break;const free=levels.map((n,i)=>i).filter(i=>left>0?levels[i]<cap(stars[i])-1e-8:levels[i]>1+1e-8);if(!free.length)throw Error('候选星级上限不足');for(const i of free)levels[i]=Math.max(1,Math.min(cap(stars[i]),levels[i]+left/free.length));}
 const ints=levels.map(n=>Math.floor(n+1e-8));let remaining=Math.round(mean*5)-ints.reduce((a,b)=>a+b,0);for(const i of levels.map((_,i)=>i).sort((a,b)=>(levels[b]-ints[b])-(levels[a]-ints[a])))if(remaining>0&&ints[i]<cap(stars[i])){ints[i]++;remaining--;}if(remaining!==0)throw Error('候选均级无法归一');return {...team,levels:ints};
}

/** Assign existing inventory only. No generation, enhancement, salvage or currency changes. */
export function allocateEquipment(team:TeamInput,inventory:GearItem[]):{team:TeamInput;owners:Record<string,string|null>}{
 const owners=Object.fromEntries(inventory.map(g=>[g.uid,g.owner])),gear=team.heroes.map(()=>[] as {equipmentId:string;enhance:number}[]),selected=new Set<string>();
 const weights:Record<string,number>={'生命':.2,'攻击':1.5,'物防':1,'谋防':1,'速度':10,'暴击率%':0,'开场怒气':0};
 for(const slot of ['兵刃','甲胄','坐骑','兵书']){const score=(g:GearItem)=>{const row=db.equipment.find(r=>r.equip_id===g.equipmentId)!;return(row.main_value*weights[row.main_stat]+row.sub_value*weights[row.sub_stat])*(1+.1*g.enhance);};const items=inventory.filter(g=>db.equipment.find(r=>r.equip_id===g.equipmentId)?.slot===slot).sort((a,b)=>score(b)-score(a)||a.uid.localeCompare(b.uid)).slice(0,team.heroes.length);for(const [i,g]of items.entries()){selected.add(g.uid);owners[g.uid]=team.heroes[i];gear[i].push({equipmentId:g.equipmentId,enhance:g.enhance});}}
 // Clear replaced equipment on the selected five; other reserve ownership remains unchanged.
 for(const g of inventory)if(!selected.has(g.uid)&&g.owner&&team.heroes.includes(g.owner))owners[g.uid]=null;
 return{team:{...team,gear},owners};
}
