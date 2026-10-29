import { describe,it,expect } from 'vitest';
import { readFileSync,writeFileSync,mkdirSync } from 'node:fs';
import { resolve } from 'node:path';
import { runBattle } from '../src/core/battle/engine';
import { database } from '../src/core/data';
import type { TeamInput,Terrain,BattleOptions,BattleLog } from '../src/core/battle/types';
interface Fixture {id:string;a:TeamInput;b:TeamInput;terrain:Terrain;seed:number;options:BattleOptions;expected:BattleLog}
const root=resolve('..','assets/reports/chapters_3_8/golden');
// Historical engine contract: preserve the NPC inputs belonging to these frozen fixtures.
const historicalData={...database,enemy_units:JSON.parse(readFileSync(resolve('..','assets/reports/joint_v2/before/app/src/core/data/enemy_units.json'),'utf8'))};
const cases=JSON.parse(readFileSync(resolve(root,'fixtures.json'),'utf8')) as Fixture[];
describe('current 96-stage calibration and Python ↔ TypeScript integration',()=>{
 it('matches every event and result, without mutating inputs',()=>{
  const mismatches:unknown[]=[];let lines=0;
  for(const c of cases){const stage=JSON.parse(readFileSync(resolve('..','assets/reports/joint_v2/before/app/src/core/data/stages.json'),'utf8')).find((s:{stage_id:string;enemy_level:number;enemy_stars:string})=>s.stage_id===c.id);if(stage){expect(c.b.levels).toEqual(Array(5).fill(stage.enemy_level));expect(c.b.stars).toEqual(stage.enemy_stars.split(';').map(Number));}
   const untouched=JSON.stringify(c);const actual=runBattle(c.a,c.b,c.terrain,c.seed,c.options,historicalData);lines+=c.expected.trace.length;
   if(JSON.stringify(actual)!==JSON.stringify(c.expected)){
    const n=Math.max(actual.trace.length,c.expected.trace.length);let line=0;while(line<n&&JSON.stringify(actual.trace[line])===JSON.stringify(c.expected.trace[line]))line++;
    mismatches.push({id:c.id,line,python:c.expected.trace[line],typescript:actual.trace[line],python_result:{...c.expected,trace:[]},typescript_result:{...actual,trace:[]}});
   }
   expect(JSON.stringify(c)).toBe(untouched);
  }
  mkdirSync(root,{recursive:true});writeFileSync(resolve(root,'comparison.json'),JSON.stringify({cases:cases.length,log_lines:lines,passed:cases.length-mismatches.length,failed:mismatches.length,mismatches},null,2));
  expect(mismatches).toEqual([]);
 });
});
