/** Read-only, deterministic timing/profiling of combat and formation work. */
import fs from 'node:fs';
import {performance} from 'node:perf_hooks';
import {database as db} from '../app/src/core/data';
import {newSave,allStages,stageTeams} from '../app/src/core/campaign';
import {campGrowth,heroTeam,acquire,levelCap} from '../app/src/core/progression';
import {recommendFormation} from '../app/src/core/formation';
import {runBattle} from '../app/src/core/battle/engine';

const save=newSave(new Date(2026,0,1,8).getTime());
const ids=Object.keys(campGrowth(save,'taiping').heroes).filter(id=>id!=='tp_hong_xiuquan');
const pool=heroTeam(save,'taiping',ids),[a,b]=stageTeams(allStages('taiping')[0],save.formations.taiping,save);
const q=newSave(new Date(2026,0,1,8).getTime()),c=campGrowth(q,'qing');
for(const h of db.heroes.filter(h=>h.faction==='qing'&&h.position!=='君主')){acquire(c,h.id);c.heroes[h.id].level=Math.min(50,levelCap(c.heroes[h.id].stars));}
const fullPool=heroTeam(q,'qing',Object.keys(c.heroes).filter(id=>db.heroes.find(h=>h.id===id)!.position!=='君主'));
const enemy={heroes:['tp_shi_dakai','tp_xiao_chaogui','tp_li_xiucheng','tp_chen_yucheng','tp_luo_dagang'],faction:'taiping' as const,levels:[50,50,50,50,50],stars:[3,3,3,3,3],monarch:'tp_hong_xiuquan'};
const result:any={node:process.version,platform:process.platform,measuredAt:new Date().toISOString(),runs:[]};
function measure(label:string,fn:()=>unknown,repeats=3){
 fn();const rows=[];
 for(let i=0;i<repeats;i++){const cpu=process.cpuUsage(),start=performance.now();const value=fn(),wall_ms=performance.now()-start,usage=process.cpuUsage(cpu);rows.push({wall_ms,cpu_ms:(usage.user+usage.system)/1000,summary:typeof value==='object'&&value&&'candidates'in value?{candidates:value.candidates,trials:(value as any).trials}:null});}
 result.runs.push({label,rows,median_ms:rows.map(r=>r.wall_ms).sort((x,y)=>x-y)[Math.floor(rows.length/2)]});
}
measure('100 first-stage battles trace=true',()=>{for(let n=0;n<100;n++)runBattle(a,b,'陆战',n,{allowDuplicates:true,trace:true});});
measure('100 first-stage battles trace=false',()=>{for(let n=0;n<100;n++)runBattle(a,b,'陆战',n,{allowDuplicates:true,trace:false});});
measure('one initial-roster advice (20 candidates x20 trials)',()=>recommendFormation(pool,b,'陆战',{current:save.formations.taiping}));
measure('one full-roster water advice (20 candidates x20 trials)',()=>recommendFormation(fullPool,enemy,'水战'));
const file=process.argv[2]??'assets/reports/equipment_batch_c_20261029/combat_benchmark.json';fs.writeFileSync(file,JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
