import {describe,it,expect} from 'vitest';
import {battleCardPosition,terrainBackgrounds} from '../src/scene/battleLayout';

describe('battle field safe areas',()=>{
 it('keeps all enemy frames and rage outlines below the top edge, and names above the seam',()=>{
  for(let slot=0;slot<5;slot++){
   const p=battleCardPosition(1,slot);
   expect(p.y-11).toBeGreaterThanOrEqual(16);
   expect(p.y+287+36).toBeLessThanOrEqual(660);
   expect(p.x-11).toBeGreaterThanOrEqual(0);
   expect(p.x+182+4).toBeLessThanOrEqual(1080);
  }
 });
 it('keeps all allied cards below the seam and their labels inside the canvas',()=>{
  for(let slot=0;slot<5;slot++){
   const p=battleCardPosition(0,slot);
   expect(p.y-11).toBeGreaterThan(660);
   expect(p.y+287+36).toBeLessThanOrEqual(1350);
  }
 });
 it('maps the player-facing attack, defence, land and river terrains independently',()=>{
  expect(terrainBackgrounds).toEqual({'陆战':'bg_battle_land','攻城':'bg_battle_siege','守城':'bg_battle_defend','水战':'bg_battle_river'});
 });
});
