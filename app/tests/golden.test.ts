import { describe,it,expect } from 'vitest';
import { readFileSync,writeFileSync,mkdirSync } from 'node:fs';
import { resolve } from 'node:path';
import { runBattle } from '../src/core/battle/engine';
import { database } from '../src/core/data';
import { Mulberry32 } from '../src/core/rng';
import type { TeamInput,Terrain,BattleOptions,BattleLog } from '../src/core/battle/types';
interface Fixture {id:string;a:TeamInput;b:TeamInput;terrain:Terrain;seed:number;options:BattleOptions;expected:BattleLog}
const root=resolve('..','assets/reports/web_chapter2/golden');
// Historical engine contract: preserve the NPC inputs belonging to these frozen fixtures.
const historicalData={...database,enemy_units:JSON.parse(readFileSync(resolve('..','assets/reports/joint_v2/before/app/src/core/data/enemy_units.json'),'utf8'))};
const cases=JSON.parse(readFileSync(resolve(root,'fixtures.json'),'utf8')) as Fixture[];
describe('100 golden Python ↔ TypeScript battles',()=>{
 it('matches every event and result, without mutating inputs',()=>{
  const mismatches:unknown[]=[];let lines=0;
  for(const c of cases){const untouched=JSON.stringify(c);const actual=runBattle(c.a,c.b,c.terrain,c.seed,c.options,historicalData);lines+=c.expected.trace.length;
   if(JSON.stringify(actual)!==JSON.stringify(c.expected)){
    const n=Math.max(actual.trace.length,c.expected.trace.length);let line=0;while(line<n&&JSON.stringify(actual.trace[line])===JSON.stringify(c.expected.trace[line]))line++;
    mismatches.push({id:c.id,line,python:c.expected.trace[line],typescript:actual.trace[line],python_result:{...c.expected,trace:[]},typescript_result:{...actual,trace:[]}});
   }
   expect(JSON.stringify(c)).toBe(untouched);
  }
  mkdirSync(root,{recursive:true});writeFileSync(resolve(root,'comparison.json'),JSON.stringify({cases:cases.length,log_lines:lines,passed:cases.length-mismatches.length,failed:mismatches.length,mismatches},null,2));
  expect(mismatches).toEqual([]);
 });
 it('uses deterministic mulberry32 for zero, overflow, Unicode seed and samples',()=>{
  const vectors=JSON.parse(readFileSync(resolve(root,'rng_vectors.json'),'utf8')) as {seed:number|string;draws:number[];sample:number[]}[];
  for(const v of vectors){const rng=new Mulberry32(v.seed);expect(Array.from({length:16},()=>rng.random())).toEqual(v.draws);expect(rng.sample(Array.from({length:10},(_,i)=>i),5)).toEqual(v.sample);}
 });
});
