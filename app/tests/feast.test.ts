import {it,expect}from 'vitest';
import {newSave,validSave,allStages,completeStage}from '../src/core/campaign';
import {buyFeast,feastPreview,campGrowth,levelCost,dayKey}from '../src/core/progression';
import {spend}from '../../tools/player_policy';
import {targetArrivalDay}from '../../tools/target_calendar_rules';
const now=new Date(2026,0,1,8).getTime();
it('keeps old saves valid and exchanges silver for experience without RNG, iron, shards or sweep changes',()=>{
 const s=newSave(now);campGrowth(s,'taiping').wallet.silver=100000;const before=JSON.stringify(s);expect(validSave(s)).toBe(true);expect(s.growth!.feastDaily).toBeUndefined();
 const r=buyFeast(s,'taiping',now),a=campGrowth(s,'taiping'),b=campGrowth(r.save,'taiping');expect(JSON.stringify(s)).toBe(before);expect(b.wallet.exp-a.wallet.exp).toBe(1000);expect(a.wallet.silver-b.wallet.silver).toBe(8000);expect({...b,wallet:a.wallet}).toEqual(a);expect(validSave(r.save)).toBe(true);
});
it('shares the daily cap across factions and chapters, resets tomorrow and rejects clock rollback',()=>{
 let s=newSave(now);for(const camp of ['taiping','qing']as const)campGrowth(s,camp).wallet.silver=100000;
 s=buyFeast(s,'taiping',now).save;expect(feastPreview(s,'qing',now).remaining).toBe(0);expect(()=>buyFeast(s,'qing',now)).toThrow('用完');expect(feastPreview(s,'qing',now+86400000).remaining).toBe(1);s=buyFeast(s,'qing',now+86400000).save;expect(()=>buyFeast(s,'taiping',now)).toThrow('回拨');
});
it('enforces both aggressive purchases and insufficient-funds atomicity',()=>{
 let s=newSave(now);campGrowth(s,'taiping').wallet.silver=24000;s=buyFeast(s,'taiping',now,'aggressive').save;s=buyFeast(s,'taiping',now,'aggressive').save;expect(campGrowth(s,'taiping').wallet).toMatchObject({silver:0,exp:3000});expect(()=>buyFeast(s,'taiping',now,'aggressive')).toThrow('用完');expect(validSave(s)).toBe(true);
 const poor=newSave(now),raw=JSON.stringify(poor);expect(()=>buyFeast(poor,'taiping',now)).toThrow('不足');expect(JSON.stringify(poor)).toBe(raw);
});
it('prices by the next challenge chapter and retains that day’s shared usage',()=>{
 let s=newSave(now);campGrowth(s,'taiping').wallet.silver=1000000;s=buyFeast(s,'taiping',now).save;for(const row of allStages('taiping').slice(0,24))s=completeStage(s,row).save;expect(feastPreview(s,'taiping',now)).toMatchObject({chapter:5,silver:40000,exp:5000,remaining:0});
});
it('spends on affordable star growth before deciding whether silver is left for a feast',()=>{
 const s=newSave(now),c=campGrowth(s,'taiping'),id=s.formations.taiping[0];c.heroes[id].stars=3;c.shards[id]=50;c.wallet.silver=15000+7999;
 const next=spend(s,'taiping',now,'conservative');expect(campGrowth(next,'taiping').heroes[id].stars).toBe(4);expect(campGrowth(next,'taiping').wallet.silver).toBe(7999);expect(next.growth!.feastDaily).toBeUndefined();
});
it('records post-growth affordability without changing purchases, training or RNG',()=>{
 const s=newSave(now);campGrowth(s,'taiping').wallet.silver=100000;const raw=JSON.stringify(s),seen:number[]=[];
 const plain=spend(s,'taiping',now,'conservative'),observed=spend(s,'taiping',now,'conservative',undefined,(state,offer)=>seen.push(campGrowth(state,'taiping').wallet.silver-offer.silver));
 expect(observed).toEqual(plain);expect(seen).toEqual([92000]);expect(JSON.stringify(s)).toBe(raw);
});
it('rejects malformed new counters while accepting both profile caps in saved progress',()=>{
 const s=newSave(now);s.growth!.feastDaily={day:dayKey(now),used:2};expect(validSave(s)).toBe(true);for(const used of [-1,.5,11]){s.growth!.feastDaily.used=used;expect(validSave(s)).toBe(false);}
});
it('uses equal sixths of chapter days and includes all previous chapter days',()=>{
 const days=[1,1.5,2,2,2.5,3,3,3.5];expect(targetArrivalDay(days,1,1)).toBeCloseTo(1/6);expect(targetArrivalDay(days,1,6)).toBe(1);expect(targetArrivalDay(days,2,1)).toBe(1.25);expect(targetArrivalDay(days,8,6)).toBe(18.5);expect(()=>targetArrivalDay(days,5,7)).toThrow();
});
