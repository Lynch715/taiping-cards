import { describe,it,expect } from 'vitest';
import { newSave,validSave,chapter,stageTeams,unlocked,allStages,openChapters,cacheChapters,ownedHeroes,completeStage,chapterLevel,initialStars } from '../src/core/campaign';
import { exportSaveFile,importSaveFile } from '../src/platform/save-transfer';
import { runBattle,activeBonds } from '../src/core/battle/engine';
import { armyPower } from '../src/core/power';
import { database } from '../src/core/data';
describe('eight chapter campaign contract',()=>{
 it('advances through all eight chapters in either campaign, preserving rewards and reloadable progress',async()=>{
  for(const camp of ['taiping','qing']as const){let s=newSave(1800000000000,903);s.campaign=camp;
   for(let n=1;n<=8;n++){
    expect(openChapters(s,camp)).toEqual(Array.from({length:n},(_,i)=>i+1));
    for(const row of chapter(camp,n)){
     expect(unlocked(row,s)).toBe(true);const first=completeStage(s,row);s=first.save;
     if(row.reward_unlock)expect(s.growth![camp].heroes[row.reward_unlock]).toBeDefined();
     const repeat=completeStage(s,row);expect(repeat.grant.exp).toBe(0);expect(repeat.save.growth).toEqual(s.growth);
     expect(validSave(s)).toBe(true);
    }
    const restored=await importSaveFile(await exportSaveFile(s));s=restored.payload;
    expect(s.progress[camp]).toHaveLength(n*6);expect(cacheChapters(s)).toContain(camp+'_'+Math.min(8,n+1));
   }
   expect(s.progress[camp==='taiping'?'qing':'taiping']).toEqual([]);
   expect(openChapters(s,camp)).toEqual([1,2,3,4,5,6,7,8]);
  }
 });
 it('loads every late-stage enemy, historical result and recommendation from the calibrated data',()=>{
  const s=newSave();for(const camp of ['taiping','qing']as const)for(const row of allStages(camp)){
   expect(['胜','败']).toContain(row.history_result);expect(row.recommended_power).toBeGreaterThan(0);
   expect(row.enemy_level).toBeGreaterThanOrEqual(1);expect(row.enemy_level).toBeLessThanOrEqual(100);
   const enemy=stageTeams(row,s.formations[camp],s)[1];
   expect(enemy.heroes).toEqual(row.enemies.split(','));expect(enemy.stars).toEqual(row.enemy_stars.split(';').map(Number));
   expect(enemy.levels).toEqual(Array(5).fill(row.enemy_level));expect(enemy.exclusives).toEqual(enemy.stars!.map(n=>n>=4));
  }
 });
 it('exposes eight six-stage chapters per faction only after clearing all preceding stages',()=>{const s=newSave();for(const c of ['taiping','qing']as const){expect(chapter(c,1)).toHaveLength(6);expect(chapter(c,2)).toHaveLength(6);expect(allStages(c)).toHaveLength(48);for(let n=1;n<=8;n++)expect(chapter(c,n)).toHaveLength(6);expect(openChapters(s,c)).toEqual([1]);expect(unlocked(chapter(c,2)[0],s)).toBe(false);s.progress[c]=chapter(c,1).map(r=>r.stage_id);expect(openChapters(s,c)).toEqual([1,2]);expect(unlocked(chapter(c,2)[0],s)).toBe(true);expect(validSave(s)).toBe(true);}});
 it('preserves old v1 military saves and rejects skipped progress, duplicates and unearned reward cards',()=>{const s=newSave();delete s.growth;expect(validSave(s)).toBe(true);s.progress.taiping=chapter('taiping').map(r=>r.stage_id);expect(validSave(s)).toBe(true);s.formations.taiping[0]='tp_yang_xiuqing';expect(validSave(s)).toBe(false);s.formations.taiping[0]='tp_xiao_chaogui';s.progress.taiping.push('tp_2_3');expect(validSave(s)).toBe(false);});
 it('unlocks each reward once, with the correct initial rarity stars at this chapter profile level',()=>{let s=newSave();for(const r of chapter('taiping'))s=completeStage(s,r).save;for(const r of chapter('taiping',2)){const before=ownedHeroes(s,'taiping'),won=completeStage(s,r);s=won.save;if(r.reward_unlock){expect(won.reward).toBe(r.reward_unlock);expect(before).not.toContain(r.reward_unlock);expect(ownedHeroes(s,'taiping')).toContain(r.reward_unlock);expect(completeStage(s,r).reward).toBeNull();}expect(validSave(s)).toBe(true);}expect(ownedHeroes(s,'taiping')).toHaveLength(11);s.formations.taiping[0]='tp_yang_xiuqing';expect(validSave(s)).toBe(true);const [team]=stageTeams(chapter('taiping',2)[5],s.formations.taiping);expect(team.levels).toEqual([30,30,30,30,30]);expect(team.stars?.[0]).toBe(initialStars(database.heroes.find(h=>h.id==='tp_yang_xiuqing')!.rarity));});
 it('uses Lv10/Lv20 profiles and the same combat-power formula on either side',()=>{const s=newSave();for(const n of [1,2]){const [a,b]=stageTeams(chapter('taiping',n)[0],s.formations.taiping);expect(a.levels).toEqual(Array(5).fill(chapterLevel(n)));expect(armyPower(a)).toBe(armyPower(structuredClone(a)));expect(armyPower(b)).toBeGreaterThan(0);}const a={heroes:['qing_npc_lvying'],faction:'qing'as const,levels:[10],stars:[1]};const h=database.enemy_units.find(h=>h.id===a.heroes[0])!,g=1.54;expect(armyPower(a)).toBe(Math.round((h.tong*24+h.wu*6)*g*.2+h.wu*3*g*1.5+h.tong*1.2*g+h.zhi*g+h.su*10));});
 it('applies Jiangnan camp bonds to the two historical bosses and retains NPC basic-only behavior',()=>{const row=chapter('taiping',2)[5],foes=stageTeams(row,newSave().formations.taiping)[1];expect(activeBonds(foes).some(b=>b.bond_id==='bd_jiangnan')).toBe(true);const [a,b]=stageTeams(chapter('taiping')[0],newSave().formations.taiping);const result=runBattle(a,b,'陆战',903,{allowDuplicates:true});expect(result.trace.filter(e=>e.event==='cast'&&e.side===1)).toEqual([]);a.heroes[1]=a.heroes[0];expect(()=>runBattle(a,b,'陆战',1,{allowDuplicates:true})).toThrow('Duplicate');});
});
