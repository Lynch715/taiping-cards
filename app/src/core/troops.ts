import {database} from './data';
import {combatBaseStats} from './battle/engine';
import type {BattleLog,Campaign,TeamInput} from './battle/types';
import type {Save} from './campaign';
import {campGrowth,equipmentRow,heroRow} from './progression';
export const TROOP_RECOVERY_MS=2*60*60*1000;
/** A ratio preserves wounded soldiers when level, stars or equipment change. */
export function troopRatio(save:Save,camp:Campaign,id:string,now=Date.now()){const h=campGrowth(save,camp).heroes[id];if(!h)throw Error('尚未获得该武将');if(h.troops===undefined)return 1;return Math.min(1,h.troops+Math.max(0,now-h.troopsAt!)/TROOP_RECOVERY_MS);}
export function troopCapacity(save:Save,camp:Campaign,id:string){const c=campGrowth(save,camp),h=c.heroes[id],row=heroRow(id),gear=c.gear.filter(g=>g.owner===id),ex=database.exclusive_equipment.find(x=>x.hero_id===id);if(!h)throw Error('尚未获得该武将');return Math.round(combatBaseStats(row,h.level,h.stars,gear.map(equipmentRow),gear.map(g=>g.enhance),h.stars>=4,ex?.stat_bonus).hp);}
export function troopStatus(save:Save,camp:Campaign,id:string,now=Date.now()){
 const max=troopCapacity(save,camp,id),ratio=troopRatio(save,camp,id,now),current=Math.floor(max*ratio+1e-7);
 // Imported saves or clock rollback can leave the recovery anchor in the future.
 const waitForClock=Math.max(0,(campGrowth(save,camp).heroes[id].troopsAt??now)-now);
 const minutes=ratio===1?0:Math.ceil((waitForClock+(1-ratio)*TROOP_RECOVERY_MS)/60000);
 return {current,max,ratio,cost:Math.ceil((max-current)*.5),minutes};
}
export function reinforce(save:Save,camp:Campaign,ids:string[],now=Date.now()){if(!ids.length||new Set(ids).size!==ids.length)throw Error('请选择不同武将');let spent=0;for(const id of ids){if(heroRow(id).position==='君主')throw Error('君主不领战斗兵力');spent+=troopStatus(save,camp,id,now).cost;}if(!spent)throw Error('兵力已满');if(campGrowth(save,camp).wallet.silver<spent)throw Error('补兵银两不足');const next=structuredClone(save),c=campGrowth(next,camp);c.wallet.silver-=spent;for(const id of ids){c.heroes[id].troops=1;c.heroes[id].troopsAt=Math.max(now,c.heroes[id].troopsAt??0);}return {save:next,spent};}
export function settleTroops(save:Save,camp:Campaign,team:TeamInput,log:BattleLog,now=Date.now()){const last=[...log.trace].reverse().find(e=>e.event==='state'&&e.teams)?.teams?.[0];if(!last)throw Error('战斗兵力记录不完整');const next=structuredClone(save),c=campGrowth(next,camp);for(const [slot,id]of team.heroes.entries()){const actor=last.actors.find(a=>a.slot===slot);if(!actor||!Number.isFinite(actor.hp)||!Number.isFinite(actor.max_hp)||actor.max_hp<=0)throw Error('战斗兵力记录不完整');c.heroes[id].troops=Math.max(0,Math.min(1,actor.hp/actor.max_hp));c.heroes[id].troopsAt=Math.max(now,c.heroes[id].troopsAt??0);}return next;}
