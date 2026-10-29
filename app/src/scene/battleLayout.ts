import type { Terrain } from '../core/battle/types';

// Includes the outer frame and rage outline above the sprite's origin.
export const ENEMY_TOP_INSET=32;
export const terrainBackgrounds:Record<Terrain,string>={
 '陆战':'bg_battle_land','攻城':'bg_battle_siege',
 '守城':'bg_battle_defend','水战':'bg_battle_river',
};
export function battleCardPosition(side:number,slot:number){
 const front=slot<2,x=(front?[390,690][slot]:[240,540,840][slot-2])-84;
 const y=side===1?(front?295:0)+ENEMY_TOP_INSET:(front?720:1015);
 return {x,y};
}
