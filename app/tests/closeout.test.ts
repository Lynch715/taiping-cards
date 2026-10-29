import {it,expect}from 'vitest';
import {database as db}from '../src/core/data';
import {assumedLevel,assumedStageLevel}from '../src/core/progression';
import {newSave,stageTeams}from '../src/core/campaign';
import {calibrationMeans}from '../../tools/calibration_levels';
it('preserves a half-step median with legal five-person means',()=>{const a=calibrationMeans(54.3,4);expect(a).toEqual([54.2,54.4,54.2,54.4]);expect(a.reduce((s,n)=>s+n,0)/4).toBeCloseTo(54.3,10);expect(()=>calibrationMeans(54.3,3)).toThrow();expect(calibrationMeans(54.4,4)).toEqual([54.4,54.4,54.4,54.4]);});
it('changes calibration previews while preserving interpolation and actual saved combat levels',()=>{const old=db.stage_level_overrides;const stage=db.stages.find(r=>r.stage_id==='qing_6_6')!;try{db.stage_level_overrides=[{stage_id:stage.stage_id,assumed_level:52.3,source_accounts:12,source:'test'}];expect(assumedStageLevel(stage)).toBe(52.3);expect(assumedLevel(6,6)).toBe(62);const save=newSave();const team=save.formations.qing;expect(stageTeams(stage,team)[0].levels).toEqual([52.3,52.3,52.3,52.3,52.3]);expect(stageTeams(stage,team,save)[0].levels).toEqual([10,10,10,10,10]);const other=db.stages.find(r=>r.stage_id==='qing_4_5')!;expect(assumedStageLevel(other)).toBe(assumedLevel(4,5));}finally{db.stage_level_overrides=old;}});
