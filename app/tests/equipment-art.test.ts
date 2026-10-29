import {describe,it,expect} from 'vitest';
import {database} from '../src/core/data';
import {equipmentArt,equipmentAtlas,equipmentSpriteStyle} from '../src/platform/equipment-art';

describe('equipment artwork mapping',()=>{
 it('maps all 100 set/slot/quality rows to exactly20 shared icons',()=>{
  const ids=database.equipment.map(row=>equipmentArt(row.set,row.slot)?.id);
  expect(ids.every(Boolean)).toBe(true);expect(new Set(ids).size).toBe(20);
  for(const set of database.equipment_sets)for(const slot of ['兵刃','甲胄','坐骑','兵书']){
   const rows=database.equipment.filter(r=>r.set===set.set&&r.slot===slot);
   expect(rows).toHaveLength(5);expect(new Set(rows.map(r=>equipmentArt(r.set,r.slot)!.id)).size).toBe(1);
  }
 });
 it('keeps every64px cell inside the atlas with transparent separation and scales fallback without changing mapping',()=>{
  for(const icon of Object.values(equipmentAtlas.icons)){
   expect(icon.x).toBeGreaterThanOrEqual(2);expect(icon.y).toBeGreaterThanOrEqual(2);
   expect(icon.x+64).toBeLessThanOrEqual(equipmentAtlas.width-2);
   expect(icon.y+64).toBeLessThanOrEqual(equipmentAtlas.height-2);
   const small=equipmentSpriteStyle(icon),large=equipmentSpriteStyle(icon,128);
   expect(large.width).toBe(small.width*2);expect(large.backgroundPosition).toBe(`${-icon.x*2}px ${-icon.y*2}px`);
  }
  expect(equipmentArt('未知','未知')).toBeNull();
 });
});
