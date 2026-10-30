import { database } from './data';
import { initialGrowth,validGrowth,rewardClear,heroTeam,assumedLevel,assumedStageLevel,migrateGrowth } from './progression';
import type { GrowthSave } from './progression';
import type { Campaign,TeamInput } from './battle/types';
import type { Stage } from './data/types';
export const initialStars=(rarity:string)=>({SSR:3,SR:2,R:1}[rarity]??1);
export const starters=(campaign:Campaign)=>database.starter_cards.find(x=>x.campaign===campaign)!;
export const chapter=(campaign:Campaign,number=1)=>database.stages.filter(x=>x.campaign===campaign&&x.chapter===number&&x.enemy_level!==null).sort((a,b)=>a.order-b.order);
export const allStages=(campaign:Campaign)=>Array.from({length:8},(_,i)=>chapter(campaign,i+1)).flat();
export const chapterLevel=(number:number)=>Math.floor(assumedLevel(number,1));
export const chapterTitle=(campaign:Campaign,number:number)=>({taiping:['金田起义','定都天京','北伐与西征','天京事变','三河大捷','东征苏常','天京保卫战','余部'],qing:['湘军初练','江西苦战','事变后的反攻','三河之败','安庆之战','淮军东援','攻破天京','平定余部']}[campaign][number-1]??'战役');
export interface Save {rules?:2;introSeen?:boolean;growth?:GrowthSave;version:1;campaign:Campaign|null;seed:number;progress:Record<Campaign,string[]>;formations:Record<Campaign,string[]>}
export function ownedHeroes(save:Save,campaign:Campaign):string[]{if(save.growth)return Object.keys(save.growth[campaign].heroes).filter(id=>database.heroes.find(h=>h.id===id)?.position!=='君主');return [...new Set([...starters(campaign).cards.split(';'),...allStages(campaign).filter(s=>save.progress[campaign].includes(s.stage_id)&&s.reward_unlock).map(s=>s.reward_unlock)])].filter(id=>database.heroes.find(h=>h.id===id)?.position!=='君主');}
export function openChapters(save:Save,campaign:Campaign){return Array.from({length:8},(_,i)=>i+1).filter(n=>chapter(campaign,n).length===6&&(n===1||chapter(campaign,n-1).every(s=>save.progress[campaign].includes(s.stage_id))));}
export function cacheChapters(save:Save){return (['taiping','qing']as const).flatMap(c=>openChapters(save,c).map(n=>c+'_'+n));}
export function stageTeams(stage:Stage,formation:string[],save?:Save):[TeamInput,TeamInput]{
 if(stage.chapter<1||stage.chapter>8||stage.enemy_level===null)throw Error('此关尚未开放');
 const enemyLevel=save?.rules===2?Math.max(1,stage.enemy_level-(stage.chapter===1?9:stage.chapter===2?4:0)):stage.enemy_level,camp=stage.campaign as Campaign,foes=stage.enemies.split(',').slice(0,save?.growth?.[camp].progressive?Math.min(5,stage.chapter+2):5);const hero=(id:string)=>database.heroes.find(x=>x.id===id);
 return [save?.growth?heroTeam(save,camp,formation):{heroes:[...formation],monarch:starters(camp).monarch,faction:camp,levels:formation.map(()=>assumedStageLevel(stage)),stars:formation.map(id=>initialStars(hero(id)!.rarity))},
 {statScale:save?.growth?.[camp].progressive?(stage.chapter===1?(save?.rules===2?.45:.55):stage.chapter===2?.8:stage.chapter===3?.9:1):undefined,heroes:foes,monarch:stage.enemy_monarch||null,faction:camp==='taiping'?'qing':'taiping',levels:foes.map(()=>enemyLevel),stars:stage.enemy_stars.split(';').slice(0,foes.length).map(Number),exclusives:stage.enemy_stars.split(';').slice(0,foes.length).map(s=>Number(s)>=4),monarchStars:stage.enemy_monarch_stars??3,monarchExclusive:(stage.enemy_monarch_stars??3)>=4}];
}
export function formationSlots(save:Save,camp:Campaign){return save.growth?.[camp].progressive?Math.min(5,3+Math.floor(save.progress[camp].length/6)):5;}
export function newSave(now=Date.now(),seed=1851):Save{const growth=initialGrowth(now,seed);return {rules:2,introSeen:false,growth,version:1,campaign:null,seed:seed>>>0,progress:{taiping:[],qing:[]},formations:{taiping:Object.keys(growth.taiping.heroes),qing:Object.keys(growth.qing.heroes)}};}

export function validSave(v:unknown):v is Save {
 if(!v||typeof v!=='object')return false;const s=v as Save;if(s.version!==1||!Number.isSafeInteger(s.seed)||s.seed<0||s.seed>0xffffffff||!['taiping','qing',null].includes(s.campaign))return false;
 if(s.rules!==undefined&&s.rules!==2||s.introSeen!==undefined&&typeof s.introSeen!=='boolean')return false;if(s.growth!==undefined&&!validGrowth(s.growth))return false;
 for(const c of ['taiping','qing']as Campaign[]){const f=s.formations?.[c],p=s.progress?.[c],rows=allStages(c);if(!Array.isArray(p)||new Set(p).size!==p.length||p.some(id=>!rows.some(x=>x.stage_id===id))||rows.slice(0,p.length).some(r=>!p.includes(r.stage_id)))return false;
  if(!Array.isArray(f)||f.length<(s.growth?.[c].progressive?3:5)||f.length>formationSlots(s,c)||new Set(f).size!==f.length||[...f].some(id=>!ownedHeroes(s,c).includes(id)))return false;
 }
 return true;
}
export function unlocked(stage:Stage,save:Save){const rows=allStages(stage.campaign),index=rows.findIndex(s=>s.stage_id===stage.stage_id);return index===0||(index>0&&save.progress[stage.campaign].includes(rows[index-1].stage_id));}
export function completeStage(raw:Save,stage:Stage){const save=migrateGrowth(raw,Date.now());if(!unlocked(stage,save))throw Error('此关尚未解锁');const c=stage.campaign,first=!save.progress[c].includes(stage.stage_id);return rewardClear({...save,progress:{...save.progress,[c]:[...new Set([...save.progress[c],stage.stage_id])]}},stage,first);}

export function selectCampaign(save:Save,camp:Campaign){if(save.campaign&&save.campaign!==camp)throw Error('本局阵营已确定，请新开一局选择其他阵营');return {...save,campaign:camp};}
