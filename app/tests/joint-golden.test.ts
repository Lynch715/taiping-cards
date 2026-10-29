import { describe,it,expect } from 'vitest';
import { readFileSync,writeFileSync,mkdirSync } from 'node:fs';
import { resolve } from 'node:path';
import { runBattle } from '../src/core/battle/engine';
import { database } from '../src/core/data';
import { Mulberry32 } from '../src/core/rng';
import type { TeamInput,Terrain,BattleOptions,BattleLog } from '../src/core/battle/types';
interface Fixture {id:string;a:TeamInput;b:TeamInput;terrain:Terrain;seed:number;options:BattleOptions;expected:BattleLog}
const root=resolve('..','assets/reports/economy_v042/golden');
const cases=JSON.parse(readFileSync(resolve(root,'fixtures.json'),'utf8')) as Fixture[];
describe('v0.4.2 current96 stages and4 mixed-equipment Python ↔ TypeScript battles',()=>{
 it('matches every event and result, without mutating inputs',()=>{
  const mismatches:unknown[]=[];let lines=0;expect(cases).toHaveLength(100);
  for(const c of cases){const untouched=JSON.stringify(c);if(!c.id.startsWith('mixed_gear_')){const stage=database.stages.find(r=>r.stage_id===c.id)!;expect(c.b.levels).toEqual(Array(5).fill(stage.enemy_level));expect(c.b.stars).toEqual(stage.enemy_stars.split(';').map(Number));expect(c.b.monarch).toBe(stage.enemy_monarch||null);}const actual=runBattle(c.a,c.b,c.terrain,c.seed,c.options);lines+=c.expected.trace.length;expect(runBattle(c.a,c.b,c.terrain,c.seed,{...c.options,trace:false})).toEqual({...actual,trace:[]});
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
