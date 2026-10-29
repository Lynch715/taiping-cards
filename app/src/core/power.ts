import { database } from './data';
import { combatBaseStats } from './battle/engine';
import type { TeamInput } from './battle/types';
export function rawUnitPower(team:TeamInput,i:number){const id=team.heroes[i],h=database.heroes.find(h=>h.id===id)??database.enemy_units.find(h=>h.id===id);if(!h)throw Error('Unknown power unit '+id);const gear=team.gear?.[i]??[],rows=gear.map(g=>database.equipment.find(r=>r.equip_id===g.equipmentId)!);const exclusive=(team.stars?.[i]??1)>=4&&!!team.exclusives?.[i];const ex=database.exclusive_equipment.find(e=>e.hero_id===id);const s=combatBaseStats(h as typeof database.heroes[number],team.levels?.[i]??10,team.stars?.[i]??1,rows,gear.map(g=>g.enhance),exclusive,ex?.stat_bonus);return s.hp*.2+s[h.troop==='谋'?'int':'atk']*1.5+s.def+s.res+s.speed*10;}
export const armyPower=(team:TeamInput)=>Math.round(team.heroes.reduce((n,_,i)=>n+rawUnitPower(team,i),0)*(team.monarch?1.08:1));
