import { database } from '../data';
import { Mulberry32 } from '../rng';
import type { Hero, Equipment } from '../data/types';
import type { Actor, AST, Aura, BattleEvent, BattleLog, BattleOptions, Buff, Database, Features, Lord, Team, TeamInput, Terrain, ActiveBond } from './types';
const clone = <T>(x:T):T => structuredClone(x);
const nums=(s:string):number[] => [...s.matchAll(/[+-]?\d+(?:\.\d+)?/g)].map(m=>Number(m[0]));
const live=(t:Team)=>t.actors.filter(alive);
const alive=(u:Actor)=>u.hp>0&&!u.escaped;
const fv=(f:Features,k:string,i=0,d=0):number=>Array.isArray(f[k])?Number((f[k] as (number|string)[])[i]??d):f[k]?1:d;
const f=(u:Actor,k:string,i=0,d=0)=>fv(u.feature,k,i,d);
const numeric=(x:unknown,d=0)=>typeof x==='number'?x:d;
const canonical=(v:unknown):unknown=>typeof v==='number'?Math.floor(v*1e6+.5)/1e6:Array.isArray(v)?v.map(canonical):v&&typeof v==='object'?Object.fromEntries(Object.entries(v).map(([k,x])=>[k,canonical(x)])):v;
const empty:AST={ops:[],features:{},auras:[],meta:{},round:null,unknown:[]};
export function growth(level:number,stars:number){if(level<1||level>100||stars<1||stars>6)throw Error('level1..100 / stars1..6');return (1+.06*(level-1))*(1+.15*(stars-1));}
export function combatBaseStats(h:Hero,level:number,stars:number,gear:Equipment[],enhance:number|number[],exclusive:boolean,bonus?:string):Record<string,number>{
    const g=growth(level,stars),main=h.troop==='谋'?'zhi':'wu';let mult=1,hpm=1;
    if(exclusive&&bonus){const v=nums(bonus);mult+=v[0]/100;hpm+=v[1]/100;}
    const w=h.wu*(main==='wu'?mult:1),z=h.zhi*(main==='zhi'?mult:1);
    const s:Record<string,number>={hp:(h.tong*24+w*6)*g*hpm,atk:w*3*g,int:z*3*g,def:h.tong*1.2*g,res:z*g,speed:h.su,crit:.05,crit_damage:1.5,start_rage:0};
    const mapping:Record<string,string[]>={'攻击':['atk','int'],'生命':['hp'],'物防':['def'],'谋防':['res'],'速度':['speed'],'开场怒气':['start_rage'],'暴击率%':['crit']};
    for(const [i,row] of gear.entries())for(const [key,value]of [[row.main_stat,row.main_value],[row.sub_stat,row.sub_value]] as [string,number][]){let v=value*(1+.1*(Array.isArray(enhance)?enhance[i]:enhance));if(key.endsWith('%'))v/=100;for(const k of mapping[key])s[k]+=v;}
    return s;
  }
class Combat {
  data:Database;heroes:Record<string,Hero>;rng:Mulberry32;terrain:Terrain;round=0;version=0;limit:number;teams:Team[]=[];trace:BattleEvent[]=[];tracing:boolean;
  cache=new Map<Actor,Record<string,number>>();policyCache=new Map<Team,number>();recastUsed=new Set<string>();
  constructor(a:TeamInput,b:TeamInput,terrain:Terrain,seed:number,options:BattleOptions,data:Database){
    this.data=data;this.tracing=options.trace!==false;this.heroes=Object.fromEntries(data.heroes.map(h=>[h.id,h]));this.rng=new Mulberry32(seed);this.terrain=terrain;this.limit=options.limit??20;
    for(const n of data.enemy_units)this.heroes[n.id]={...n,rarity:'R',position:'前排',active:'npc_active',passive:'npc_passive',exclusive:'',tags:'杂兵'};
    for(const [side,input] of [a,b].entries()){
      const ids=input.heroes;
      if(ids.length<1||ids.length>5)throw Error('Roster must contain1..5 combat heroes');
      if(ids.some((id,i)=>ids.indexOf(id)!==i&&!(options.allowDuplicates&&this.heroes[id]?.tags==='杂兵')))throw Error('Duplicate hero');
      const actors:Actor[]=ids.map((id,slot)=>{
        const h=this.heroes[id];if(!h||h.position==='君主')throw Error('Invalid combat hero '+id);
        const stars=input.stars?.[slot]??options.stars??3,level=input.levels?.[slot]??options.level??50;
        const enabled=stars>=4&&(input.exclusives?!!input.exclusives[slot]:options.exclusiveOwners?options.exclusiveOwners.some(([s,n])=>s===side&&n===id):!!options.exclusives);
        const compiled=enabled&&options.exclusiveEffects!==false?data.compiled.exclusives[id]:null;
        const active=clone(compiled?.active??this.ast(h.active));const passive=clone(compiled?.passive??this.ast(h.passive));
        const features:Features={...passive.features,...clone(compiled?.extra??{})};const auras=clone(passive.auras??[]);
        const ownGear=input.gear?.[slot];const gear=ownGear?ownGear.map(x=>{const r=data.equipment.find(e=>e.equip_id===x.equipmentId);if(!r)throw Error('Unknown equipment');return r;}):options.equipmentIds?options.equipmentIds.map(x=>{const r=data.equipment.find(e=>e.equip_id===x);if(!r)throw Error('Unknown equipment');return r;}):options.gearSet?data.equipment.filter(r=>r.set===options.gearSet&&r.quality===(options.quality??'精')):[];
        if(gear.length>4||new Set(gear.map(x=>x.slot)).size!==gear.length)throw Error('Duplicate equipment slot');
        if(!ownGear&&options.gearSet&&!options.equipmentIds&&gear.length!==4)throw Error('Expected4 equipment slots');
        const enhance=ownGear?ownGear.map(g=>g.enhance):options.enhance??0;if(gear.some((g,i)=>{const n=Array.isArray(enhance)?enhance[i]:enhance;return !Number.isInteger(n)||n<0||n>g.enhance_max;}))throw Error('Enhancement out of range');
        const ex=data.exclusive_equipment.find(e=>e.hero_id===id);const s=this.baseStats(h,level,stars,gear,enhance,enabled,ex?.stat_bonus);
        const count:Record<string,number>={};for(const row of gear)count[row.set]=(count[row.set]??0)+1;
        for(const [name,pieces]of Object.entries(count)){const st=data.compiled.sets[name];if(pieces>=2&&(!st.filter_fire||h.troop==='火')&&(!st.water_only||terrain==='水战'))auras.push(clone(st.aura));if(pieces>=4)Object.assign(features,clone(st.four));}
        return {hero:h,side,slot,faction:h.faction==='dual'?input.faction:h.faction,feature:features,auras,active,base:s,max_hp:s.hp,hp:s.hp,rage:0,buffs:[],shields:[],control:{},burns:[],actions:0,basics:0,casts:0,hits:0,kills:0,escaped:false,saved:false,desperation_used:false,immune_until:0,bonus_speed:0,exclusive:enabled&&!!ex};
      });
      let lord:Lord|null=null;
      if(input.monarch){const h=this.heroes[input.monarch];if(!h||h.position!=='君主')throw Error('Invalid monarch');
        const enabled=(input.monarchStars??options.stars??3)>=4&&(input.monarchExclusive!==undefined?input.monarchExclusive:options.exclusiveOwners?options.exclusiveOwners.some(([s,n])=>s===side&&n===h.id):!!options.exclusives);
        const compiled=enabled&&options.exclusiveEffects!==false?data.compiled.exclusives[h.id]:null;
        lord={hero:h,active:clone(compiled?.active??this.ast(h.active)),passive:clone(compiled?.passive??this.ast(h.passive)),exclusive:enabled};}
      const counts:Record<string,number>={};for(const u of actors)counts[u.faction]=(counts[u.faction]??0)+1;
      this.teams.push({actors,lord,assigned:input.faction,bonds:[],faith:50,faith_cap:100,heaven_until:0,suspicion:0,incident_round:null,grain:0,enabled:new Set(Object.keys(counts).filter(k=>counts[k]>=3)),triggered_edict:false});
    }
    this.setupBonds();this.start();this.recordState();
  }
  ast(id:string):AST {const a=this.data.compiled.skills[id];if(a)return a;if(id==='npc_active'||id==='npc_passive')return empty;throw Error('Unknown skill '+id);}
  baseStats(h:Hero,level:number,stars:number,gear:Equipment[],enhance:number|number[],exclusive:boolean,bonus?:string){return combatBaseStats(h,level,stars,gear,enhance,exclusive,bonus);}
  log(event:string,values:Record<string,unknown>={}){if(this.tracing)this.trace.push(canonical({round:this.round,event,...values}) as BattleEvent);}
  recordState(){if(this.tracing)this.log('state',{teams:this.teams.map(t=>({faith:t.faith,suspicion:t.suspicion,grain:t.grain,actors:t.actors.map(u=>({id:u.hero.id,slot:u.slot,hp:u.hp,max_hp:u.max_hp,rage:u.rage,escaped:u.escaped,control:{...u.control}}))}))});}
  invalidate(){this.version++;this.cache.clear();this.policyCache.clear();}
  policyFactor(t:Team){if(!t.lord||!['tp_hong_xiuquan','tp_hong_tianguifu'].includes(t.lord.hero.id))return 1;if(!this.policyCache.has(t))this.policyCache.set(t,1+live(t).reduce((s,u)=>s+f(u,'lord_amplify')/100,0));return this.policyCache.get(t)!;}
  syncMaxHP(side:number){let changed=false;for(const u of live(this.teams[side])){const max=this.stats(u).hp;if(Math.abs(max-u.max_hp)>1e-7){u.hp*=max/u.max_hp;u.max_hp=max;changed=true;}}if(changed)this.invalidate();}
  members(t:Team){return new Set([...t.actors.map(u=>u.hero.id),...(t.lord?[t.lord.hero.id]:[])]);}
  setupBonds(){for(const [side,t]of this.teams.entries()){const ids=this.members(t);for(const b of this.data.bonds){if(b.type==='宿敌')continue;
    if(b.type==='负面'){if(b.effect.includes('猜忌')?ids.has('tp_yang_xiuqing')&&ids.has('tp_wei_changhui'):ids.has('qing_li_hongzhang')&&ids.has('qing_gordon'))t.bonds.push({...b,_ast:this.data.compiled.bonds[b.bond_id],tier:0});continue;}
    const count=b.members.split(';').filter(x=>ids.has(x)).length,tier=b.need.split('/').map(Number).filter(n=>count>=n).length-1;if(tier>=0)t.bonds.push({...b,_ast:this.data.compiled.bonds[b.bond_id],tier});}
    this.log('bonds',{side,ids:t.bonds.map(b=>b.bond_id)});}}
  matches(u:Actor,scope:string,owner:Actor){if(scope==='self')return u===owner;if(scope==='hit')return false;if(scope==='ally_all')return u.side===owner.side;if(scope==='ally_front')return u.side===owner.side&&u.slot<2;
    if(scope.startsWith('ally:')){const key=scope.slice(5);if(u.side!==owner.side)return false;if(['taiping','qing'].includes(key))return u.faction===key;if(key.startsWith('troop:'))return u.hero.troop===key.slice(6);const tags=u.hero.tags.split(';');return key==='xiang_huai'?tags.includes('湘军')||tags.includes('淮军'):tags.includes(key);}return false;}
  start(){for(const t of this.teams){if(t.lord){const ft=t.lord.passive.features??{},p=this.policyFactor(t);t.faith_cap+=fv(ft,'faith_cap')*p;t.faith+=fv(ft,'start_faith')*p;}
    for(const u of t.actors)u.rage=u.base.start_rage+(u.hero.troop==='谋'?30:0)+f(u,'start_rage');
    for(const u of t.actors){for(const v of t.actors){this.rage(v,f(u,'start_rage_all'));if(v.faction==='taiping')this.rage(v,f(u,'start_rage_taiping'));if(v.hero.tags.includes('洋枪队')&&f(u,'start_foreign_defense'))this.buff(v,'start:'+u.hero.id,'defense',f(u,'start_foreign_defense')/100,false,999);}
      if(f(u,'random_stat')){const key=this.rng.choice(['attack','defense']);this.buff(u,'random:'+u.hero.id,key,f(u,'random_stat',key==='attack'?0:1)/100,false,999);}}
    }for(const t of this.teams)for(const u of t.actors){u.max_hp=this.stats(u).hp;u.hp=u.max_hp;u.rage=Math.min(100,u.rage);}this.invalidate();}
  bonuses(u:Actor){const b:Record<string,number>={},fl:Record<string,number>={};const add=(key:string,v:number,flat=false)=>{const d=flat?fl:b;d[key]=(d[key]??0)+v;};
    for(const x of u.buffs)if(x.expires>=this.round)add(x.stat,x.value,x.flat);const t=this.teams[u.side];
    for(const o of live(t)){for(const a of o.auras)if(this.matches(u,a.target,o))add(a.stat,a.value,a.flat);
      if(f(o,'low_alive_defense')&&live(t).length<=f(o,'low_alive_defense'))add('defense',f(o,'low_alive_defense',1)/100);
      if(f(o,'death_aura')){const dead=t.actors.filter(v=>v.hp<=0&&!v.escaped).length,layers=Math.min(dead,f(o,'death_aura',2));add('defense',layers*f(o,'death_aura')/100);add('attack',layers*f(o,'death_aura',1)/100);}
      if(f(o,'huai_speed'))add('speed',t.actors.filter(v=>v.hero.tags.includes('淮军')).length*f(o,'huai_speed'),true);
      if(this.terrain==='攻城'&&f(o,'siege_attack_aura'))add('attack',f(o,'siege_attack_aura')/100);
      if(this.terrain==='水战'&&o.feature.water_team_reduction)add('taken',-Number(o.feature.water_team_reduction));}
    if(t.lord){const l=t.lord;for(const a of l.passive.auras??[])if(this.matches(u,a.target,t.actors[0]))add(a.stat,a.value*this.policyFactor(t),a.flat);
      const features=l.passive.features??{};let hong=features.hong_all as number[]|undefined;const conditional=features.hong_all_faith as number[]|undefined;if(conditional&&t.faith>=conditional[0])hong=conditional.slice(1);
      if(hong&&u.faction==='taiping'){const [base,step,value]=hong,ex=this.data.exclusive_equipment.find(x=>x.hero_id===l.hero.id);const zhi=l.hero.zhi*(l.exclusive&&ex?1+nums(ex.stat_bonus)[0]/100:1);add('all',(base+Math.floor(zhi/step)*value)/100*this.policyFactor(t));}}
    const positive=t.bonds.some(x=>x.type==='正面');if(f(u,'no_bond_all')&&!positive)add('all',f(u,'no_bond_all')/100);if(f(u,'no_bond_risk')&&!positive){add('all',f(u,'no_bond_risk')/100);add('taken',f(u,'no_bond_risk',1)/100);}
    const ratio=u.max_hp?u.hp/u.max_hp:1;
    if(f(u,'low_hp_attack')&&ratio<f(u,'low_hp_attack')/100)add('attack',f(u,'low_hp_attack',1)/100);
    if(f(u,'high_hp_attack')&&ratio>f(u,'high_hp_attack')/100)add('attack',f(u,'high_hp_attack',1)/100);
    if(f(u,'suspicion_attack'))add('attack',Math.floor(t.suspicion/f(u,'suspicion_attack'))*f(u,'suspicion_attack',1)/100);
    if(f(u,'hit_attack'))add('attack',Math.min(u.hits,f(u,'hit_attack',1))*f(u,'hit_attack')/100);
    if(f(u,'hit_attack_every'))add('attack',Math.min(Math.floor(u.hits/f(u,'hit_attack_every')),f(u,'hit_attack_every',2))*f(u,'hit_attack_every',1)/100);
    if(f(u,'hong_zhi')&&t.lord?.hero.id==='tp_hong_xiuquan')add('zhi',f(u,'hong_zhi')/100);
    if(f(u,'rengan_attack')&&live(t).some(v=>v.hero.id==='tp_hong_rengan'))add('attack',f(u,'rengan_attack')/100);
    if(f(u,'assigned_taiping_attack')&&u.faction==='taiping')add('attack',f(u,'assigned_taiping_attack')/100);
    if(this.round===1)add('speed',f(u,'first_speed')+(u.hero.troop==='骑'?20:0),true);
    if(this.terrain==='水战')add('speed',f(u,'water_speed'),true);
    if(this.terrain==='水战'&&u.hero.troop==='水')add('all',.2);else if(u.hero.troop==='水')add('attack',-.1);
    add('speed',u.bonus_speed,true);
    if(u.faction==='taiping'&&this.round<=t.heaven_until&&t.heaven_until>0)add('attack',.2);
    if(u.faction==='qing'&&t.enabled.has('qing'))add('defense',Math.min(5,Math.floor(t.grain/30))*.05);
    const defender=this.terrain==='攻城'?1:this.terrain==='守城'?0:null;if(u.side===defender)add('defense',.2);
    this.bondBonuses(u,add);return [b,fl];}
  stats(u:Actor){const cached=this.cache.get(u);if(cached)return cached;const [b,fl]=this.bonuses(u),g=(k:string)=>b[k]??0,s={...u.base},all=g('all');
    s.hp*=Math.max(.05,1+all);s.atk*=Math.max(.05,1+all+g('attack'));s.int*=Math.max(.05,1+all+g('zhi')+g('attack'));
    s.def*=Math.max(.05,1+all+g('defense')+g('physical_defense'));s.res*=Math.max(.05,1+all+g('zhi')+g('defense'));s.speed=s.speed*Math.max(.05,1+all+g('speed'))+(fl.speed??0);
    s.crit=Math.min(1,Math.max(0,s.crit+g('crit')));s.crit_damage=Math.max(1,s.crit_damage+g('crit_damage'));s.damage_bonus=g('damage');s.taken=g('taken');s.rage_gain=Math.max(0,1+g('rage_gain'));this.cache.set(u,s);return s;}
  buff(u:Actor,source:string,stat:string,value:number,flat:boolean,duration:number){if(value<0&&stat==='attack'&&f(u,'attack_debuff_immune'))return;const expires=duration<999?this.round+duration-1:999,prev=u.buffs.find(b=>b.source===source&&b.stat===stat&&b.flat===flat);if(prev){prev.value=value>=0?Math.max(prev.value,value):Math.min(prev.value,value);prev.expires=Math.max(prev.expires,expires);}else u.buffs.push({source,stat,value,flat,expires});this.invalidate();}
  rage(u:Actor,amount:number){let gain=1;const t=this.teams[u.side];if(amount>0&&t?.lord)for(const a of t.lord.passive.auras??[])if(a.stat==='rage_gain')gain+=a.value;u.rage=Math.max(0,Math.min(100,u.rage+amount*gain));}
  bondBonuses(u:Actor,add:(key:string,v:number,flat?:boolean)=>void){const t=this.teams[u.side],living=live(t),ids=new Set(living.map(v=>v.hero.id));for(const b of t.bonds){const a=b._ast,k=a.kind,p=a.values,m=a.members.includes(u.hero.id),val=p.length?p[Math.min(b.tier,p.length-1)]:0;
    if(k==='second_pair'&&m)add('attack',p[0]);else if(k==='missing_pair'&&m)add('attack',(t.actors.length-living.length)*p[0]);else if(k==='water_first'&&m&&this.terrain==='水战')add('speed',a.speed!,true);
    else if(k==='defend_aura'&&this.terrain==='守城')add('defense',p[0]);else if(k==='fire_aura'&&u.hero.troop==='火')add('attack',val);else if(k==='pair_crit'&&m)add('crit',p[0]);
    else if(k==='siege_aura'){if(this.terrain==='攻城')add('damage',p[0]);if(m&&u.hero.id===a.members.at(-1))add('attack',p[1]);}
    else if(k==='presence_pair'){if(u.hero.id===a.members[1]&&ids.has(a.members[0]))add('crit',p[0]);if(u.hero.id===a.members[0]&&ids.has(a.members[1]))add('defense',p[1]);}
    else if(k==='water_pair_all'&&m&&this.terrain==='水战')add('all',p[0]);else if(k==='member_attack'&&m)add('attack',val);else if(k==='member_cavalry'&&m&&u.hero.troop==='骑')add('attack',val);else if(k==='member_speed'&&m)add('speed',val,true);else if(k==='front_defense'&&u.slot<2)add('defense',val);}}
  resource(side:number,key:string,value:number,source?:Actor){const t=this.teams[side];
    if(key==='信仰'){if(t.lord)t.faith_cap=100+fv(t.lord.passive.features??{},'faith_cap')*this.policyFactor(t);let mult=1;for(const b of t.bonds)if(b._ast.kind==='faith_gain')mult+=b._ast.values[b.tier];if(source)mult+=f(source,'set_faith_gain');t.faith=Math.max(0,Math.min(t.faith_cap,t.faith+value*mult));if(t.enabled.has('taiping')&&t.faith>=100&&!t.heaven_until){t.heaven_until=this.round+1;this.log('heaven',{side});}}
    else if(key==='猜忌'){if(t.incident_round!==null)return;if(source)value*=Number(source.feature.suspicion_multiplier??1);t.suspicion=Math.max(0,Math.min(100,t.suspicion+value));if(t.suspicion>=100){t.incident_round=this.round;t.suspicion=0;for(const u of live(t)){if(['tp_yang_xiuqing','tp_wei_changhui'].includes(u.hero.id))u.hp*=.5;if(u.hero.id==='tp_shi_dakai')u.escaped=true;}this.log('tianjing_incident',{side});}}
    else if(key==='粮饷'){let mult=1+live(t).reduce((s,u)=>s+f(u,'grain_gain')/100,0);for(const b of t.bonds)if(b._ast.kind==='grain_gain')mult+=b._ast.values[0];const previous=t.grain;t.grain=Math.max(0,t.grain+value*mult);
      for(const o of live(t)){let threshold=f(o,'grain_rage');if(threshold){const count=Math.floor(t.grain/threshold)-Math.floor(previous/threshold);for(const u of live(t))this.rage(u,count*f(o,'grain_rage',1));}if(f(o,'set_grain_heal')){threshold=f(o,'set_grain_heal');const count=Math.floor(t.grain/threshold)-Math.floor(previous/threshold);if(count)this.heal(o,f(o,'set_grain_heal',1)*count);}}}
    this.invalidate();if(key==='信仰'&&t.lord?.passive.features?.hong_all_faith)this.syncMaxHP(side);
  }
  targets(u:Actor,scope:string,hit:Actor[]=[]):Actor[]{const ally=live(this.teams[u.side]),enemy=live(this.teams[1-u.side]);
    if(scope==='self')return alive(u)?[u]:[];if(scope==='hit')return hit.filter(alive);if(scope==='ally_low')return ally.length?[this.lowest(ally)]:[];if(scope.startsWith('ally'))return ally.filter(v=>this.matches(v,scope,u));if(!enemy.length)return [];
    const taunt=enemy.filter(v=>(v.control['嘲讽']??0)>0);if(['enemy_one','enemy_front_one','enemy_back_one','enemy_low','enemy_back_low'].includes(scope)&&taunt.length)return [taunt.sort((a,b)=>a.slot-b.slot)[0]];
    if(scope==='enemy_all')return enemy;if(scope.startsWith('random:'))return this.rng.sample(enemy,Math.min(enemy.length,Number(scope.split(':')[1])));
    const front=enemy.filter(v=>v.slot<2),back=enemy.filter(v=>v.slot>=2);const pool=scope.startsWith('enemy_front')?(front.length?front:back):scope.startsWith('enemy_back')?(back.length?back:front):enemy;
    if(['enemy_front','enemy_back'].includes(scope))return pool;if(scope.includes('low'))return [this.lowest(pool)];return pool.length?[this.rng.choice(pool)]:[];
  }
  lowest(pool:Actor[]){return [...pool].sort((a,b)=>a.hp/a.max_hp-b.hp/b.max_hp||a.slot-b.slot)[0];}
  normalTarget(u:Actor){if(u.hero.troop==='火')return this.targets(u,'enemy_low');const chance=Math.max(u.hero.troop==='骑'?.3:0,f(u,'rear_chance')/100);return this.targets(u,this.rng.random()<chance?'enemy_back_one':'enemy_front_one');}
  heal(target:Actor,fraction:number){if(!alive(target))return 0;let mult=1+f(target,'healing_taken')/100;mult-=live(this.teams[1-target.side]).reduce((s,u)=>s+f(u,'enemy_healing_reduction')/100,0);const amount=Math.max(0,fraction*target.max_hp*Math.max(0,mult)),before=target.hp;target.hp=Math.min(target.max_hp,target.hp+amount);this.invalidate();return target.hp-before;}
  rivalBonus(u:Actor,v:Actor){let value=0;for(const b of this.data.bonds){const a=this.data.compiled.bonds[b.bond_id];if(a.kind==='rival_damage'&&a.left!.includes(u.hero.id)&&a.right!.includes(v.hero.id))value+=a.values[0];else if(a.kind==='rival_reduce'&&a.left!.includes(v.hero.id)&&a.right!.includes(u.hero.id))value+=a.values[0];}return value;}
  blocked(u:Actor){const ids=new Set(live(this.teams[1-u.side]).map(v=>v.hero.id));return this.data.bonds.some(b=>{const a=this.data.compiled.bonds[b.bond_id];return a.kind==='block_desperation'&&a.right!.includes(u.hero.id)&&a.left!.some(x=>ids.has(x));});}
  afterDeath(u:Actor,killer:Actor){this.log('death',{id:u.hero.id,side:u.side,slot:u.slot});const t=this.teams[u.side];
    for(const v of live(t)){if(f(u,'death_attack_all'))this.buff(v,'death:'+u.hero.id,'attack',f(u,'death_attack_all')/100,false,999);if(f(u,'death_rage_all'))this.rage(v,f(u,'death_rage_all'));}
    for(const b of t.bonds){const a=b._ast;if(a.kind==='partner_death'&&a.members.includes(u.hero.id))for(const v of live(t))if(a.members.includes(v.hero.id))this.buff(v,'bond:'+b.bond_id,'attack',a.values[0],false,999);}
    if(this.teams[killer.side].enabled.has('taiping'))this.resource(killer.side,'信仰',10,killer);
    if(alive(killer)){killer.kills++;if(f(killer,'kill_heal'))this.heal(killer,f(killer,'kill_heal')/100);this.rage(killer,f(killer,'set_kill_rage'));if(f(killer,'set_kill_attack'))this.buff(killer,'set:kill_attack','attack',Math.min(killer.kills,f(killer,'set_kill_attack',1))*f(killer,'set_kill_attack'),false,999);}
    this.invalidate();if(f(u,'lord_amplify')){if(t.lord){t.faith_cap=100+fv(t.lord.passive.features??{},'faith_cap')*this.policyFactor(t);t.faith=Math.min(t.faith,t.faith_cap);}this.syncMaxHP(u.side);}
  }
  applyLoss(target:Actor,amount:number,source:Actor,allowSave=true){if(!alive(target))return false;
    if(amount>=target.hp&&allowSave&&f(target,'death_save')&&!target.saved){target.hp=1;target.saved=true;if(target.feature.save_attack){const [v,d]=target.feature.save_attack as number[];this.buff(target,'exclusive:save','attack',v,false,d);}}
    else target.hp=Math.max(0,target.hp-amount);this.invalidate();if(target.hp<=0){this.afterDeath(target,source);return true;}
    if(f(target,'desperation')&&!target.desperation_used&&target.hp/target.max_hp<f(target,'desperation')/100&&!this.blocked(target)){target.desperation_used=true;this.heal(target,f(target,'desperation',1)/100);target.immune_until=this.round+Math.trunc(f(target,'desperation',2))-1;delete target.control['眩晕'];delete target.control['沉默'];if(target.feature.desperation_attack){const [v,d]=target.feature.desperation_attack as number[];this.buff(target,'exclusive:desperation','attack',v,false,d);}}
    return false;
  }
  damage(u:Actor,v:Actor,coefficient=1,active=false,basic=false,meta:Record<string,unknown>={}){if(!alive(u)||!alive(v))return false;const a=this.stats(u),d=this.stats(v);let magic=u.hero.troop==='谋';if(f(u,'max_attack'))magic=a.int>a.atk;
    const attack=magic?a.int:a.atk,defense=magic?d.res:d.def,mult=['骑步','步火','火骑'].includes(u.hero.troop+v.hero.troop)?1.2:1;let bonus=a.damage_bonus+this.rivalBonus(u,v);
    if(active)bonus+=f(u,'active_damage')/100+(u.hero.troop==='谋'?.15:0);if(this.terrain==='攻城')bonus+=f(u,'siege_damage')/100;if(u.actions===0)bonus+=f(u,'first_damage')/100;
    if(v.hp/v.max_hp>f(u,'target_high_bonus')/100&&f(u,'target_high_bonus'))bonus+=f(u,'target_high_bonus',1)/100;
    bonus+=(this.teams[u.side].actors.length-live(this.teams[u.side]).length)*f(u,'missing_damage')/100;if(v.hero.troop==='步')bonus+=f(u,'infantry_damage')/100;
    const named=u.feature.named_damage as (string|number)[]|undefined;if(named&&String(named[0]).split('、').includes(v.hero.name))bonus+=Number(named[1])/100;
    if(basic&&f(u,'nth_basic')&&u.basics%Math.trunc(f(u,'nth_basic'))===0)bonus+=f(u,'nth_basic',1)/100;if(this.round===1)bonus+=f(u,'set_first_damage');
    for(const b of this.teams[u.side].bonds){const ast=b._ast;if(!ast.members.includes(u.hero.id))continue;if(ast.kind==='water_first'&&this.terrain==='水战'&&this.round===1)bonus+=ast.values[0];if(ast.kind==='second_pair'&&this.teams[u.side].actors.some(v=>ast.members.includes(v.hero.id)&&v.hero.id!==u.hero.id&&(v.acted_round??0)===this.round))bonus+=ast.values[1];}
    let taken=d.taken;if(v.hero.troop==='步'&&v.slot<2)taken-=.1;if(v.hero.troop==='火'&&v.slot>=2)taken-=.1;if(u.hero.troop==='火')taken-=f(v,'firearm_reduction')/100;if(this.terrain==='水战')taken+=f(v,'set_water_taken');
    if(active){const first=meta.first_round_bonus as number[]|undefined;if(first?.[0]===this.round)bonus+=first[1];if(meta.target_double_name===v.hero.name)coefficient*=2;const target=meta.target_bonus as [string,number]|undefined;if(target&&target[0]==='太平天国武将'&&v.faction==='taiping')bonus+=target[1];if(this.terrain==='攻城')bonus+=numeric(meta.siege_bonus);}
    let crit=a.crit;if(f(u,'target_low_crit')&&v.hp/v.max_hp<f(u,'target_low_crit')/100)crit+=f(u,'target_low_crit',1)/100;
    const cm=this.rng.random()<Math.min(1,crit)?Math.max(1,a.crit_damage-f(v,'critical_reduction')/100):1;
    const original=Math.max(1,Math.trunc(coefficient*attack*attack/(attack+defense)*mult*Math.max(.4,1+bonus+taken)*cm)),loss=this.absorb(v,original),killed=loss?this.applyLoss(v,loss,u):false;
    v.hits++;if(alive(v))this.rage(v,10);this.invalidate();this.log('damage',{source:u.hero.id,target:v.hero.id,amount:original,hp_loss:loss,active,source_side:u.side,source_slot:u.slot,target_side:v.side,target_slot:v.slot});return killed;
  }
  absorb(u:Actor,value:number){for(const s of [...u.shields].sort((a,b)=>a[1]-b[1])){if(s[1]<this.round)continue;const consume=Math.min(value,s[0]);s[0]-=consume;value-=consume;if(!value)break;}u.shields=u.shields.filter(x=>x[0]>0&&x[1]>=this.round);return value;}
  basic(u:Actor,proc=true){const targets=this.normalTarget(u);if(!targets.length)return;u.basics++;this.damage(u,targets[0],1,false,true);this.rage(u,25+Math.max(0,this.stats(u).speed-80)*.5);
    if(proc&&alive(u)){if(this.rng.random()<f(u,'combo_chance')/100)this.basic(u,false);if(f(u,'set_extra_hit')&&this.rng.random()<f(u,'set_extra_hit')){const target=this.normalTarget(u);if(target.length)this.damage(u,target[0],f(u,'set_extra_hit',1));}}
  }
  execute(u:Actor,ast:AST,name:string,active=true){let hits:Actor[]=[];const killed:Actor[]=[];const meta=ast.meta??{};
    for(const op of ast.ops??[]){if(!alive(u))break;if(op.condition&&this.terrain!==op.condition)continue;let scope=op.target;if(op.kind==='damage'&&this.terrain==='水战')scope=typeof meta.water_target==='string'?meta.water_target:scope;const targets=this.targets(u,scope,hits);
      if(op.kind==='damage'){hits=[...targets];for(const target of targets)if(this.damage(u,target,op.value,active,false,meta))killed.push(target);continue;}
      if(op.kind==='combo'){for(let i=0;i<op.value;i++)if(alive(u))this.basic(u,false);continue;}
      if(op.kind==='resource'&&op.resource!=='怒气'){this.resource(u.side,op.resource!,op.value,name.startsWith('monarch:')?undefined:u);continue;}
      for(const target of targets){if(this.rng.random()>(op.probability??1))continue;
        if(op.kind==='heal')this.heal(target,op.value);
        else if(op.kind==='shield'){const expires=this.round+op.duration-1,old=target.shields.find(s=>s[2]===name);if(old){old[0]=Math.max(old[0],target.max_hp*op.value);old[1]=Math.max(old[1],expires);}else target.shields.push([target.max_hp*op.value,expires,name]);}
        else if(op.kind==='buff')this.buff(target,name,op.stat!,op.value,!!op.flat,op.duration||999);
        else if(op.kind==='status'){if(['眩晕','沉默'].includes(op.status!)&&target.immune_until>=this.round)continue;target.control[op.status!]=Math.max(target.control[op.status!]??0,op.duration);}
        else if(op.kind==='burn'){const snap=this.stats(u).atk*op.value,expires=this.round+op.duration-1;target.burns=[...target.burns.filter(b=>b[2].hero.id!==u.hero.id),[snap,expires,u]];}
        else if(op.kind==='resource')this.rage(target,op.value);
        else if(op.kind==='dispel'){const negative=target.buffs.filter(b=>b.value<0);for(const b of negative.slice(0,op.value))target.buffs.splice(target.buffs.indexOf(b),1);let left=op.value-Math.min(op.value,negative.length);for(const st of ['眩晕','沉默'])if(left&&st in target.control){delete target.control[st];left--;}if(left)target.burns=target.burns.slice(Math.min(left,target.burns.length));}
      }this.invalidate();
    }
    if(killed.length){if(meta.kill_rage)this.rage(u,Number(meta.kill_rage));if(meta.kill_followup){const pool=live(this.teams[1-u.side]).filter(v=>v.slot>=2&&!hits.includes(v));if(pool.length)this.damage(u,this.rng.choice(pool),Number(meta.kill_followup),active);}if(u.feature.kill_recast&&!this.recastUsed.has(u.hero.id)){this.recastUsed.add(u.hero.id);this.execute(u,ast,name,active);}}
  }
  stepStart(){this.invalidate();for(const [side,t]of this.teams.entries()){if(t.heaven_until&&this.round>t.heaven_until){t.heaven_until=0;t.faith=50;}this.syncMaxHP(side);
    for(const u of live(t)){if(f(u,'set_start_heal'))this.heal(u,f(u,'set_start_heal'));if(f(u,'set_periodic_heal')&&this.round%Math.trunc(f(u,'set_periodic_heal'))===0)this.heal(u,f(u,'set_periodic_heal',1));}
    if(t.enabled.has('qing'))this.resource(side,'粮饷',10);let rate=0;if(t.lord&&live(t).some(u=>u.hero.id==='tp_yang_xiuqing'))rate+=fv(t.lord.passive.features??{},'yang_round_suspicion')*this.policyFactor(t);
    for(const b of t.bonds)if(b._ast.kind==='suspicion')rate+=b._ast.rate!;if(rate)this.resource(side,'猜忌',rate);
    if(t.lord&&!t.triggered_edict&&t.lord.active.round===this.round){t.triggered_edict=true;if(live(t).length){this.log('cast',{id:t.lord.hero.id,side,slot:-1,skill:t.lord.hero.active});this.execute(live(t)[0],t.lord.active,'monarch:'+t.lord.hero.id,false);}}}}
  stepEnd(){for(const t of this.teams)for(const u of [...live(t)]){for(const [amount,expires,owner]of [...u.burns])if(expires>=this.round&&alive(u)){let taken=this.stats(u).taken;if(u.hero.troop==='步'&&u.slot<2)taken-=.1;if(u.hero.troop==='火'&&u.slot>=2)taken-=.1;if(this.terrain==='水战')taken+=f(u,'set_water_taken');const v=this.absorb(u,Math.max(1,Math.trunc(amount*Math.max(.4,1+taken))));if(v)this.applyLoss(u,v,owner);if(alive(u))this.rage(u,10);}
    u.burns=u.burns.filter(b=>b[1]>this.round);if(alive(u)&&f(u,'end_heal'))this.heal(u,f(u,'end_heal')/100);if(alive(u)&&f(u,'end_heal_below')&&u.hp/u.max_hp<f(u,'end_heal_below')/100)this.heal(u,f(u,'end_heal_below',1)/100);u.buffs=u.buffs.filter(b=>b.expires>this.round);u.shields=u.shields.filter(s=>s[1]>this.round);
    }this.invalidate();}
  run():BattleLog {for(this.round=1;this.round<=this.limit;this.round++){this.stepStart();this.recordState();const queue=this.teams.flatMap(live).sort((a,b)=>this.stats(b).speed-this.stats(a).speed||a.side-b.side||a.slot-b.slot);
    for(const u of queue){if(!alive(u))continue;let skip=(u.control['眩晕']??0)>0;
      for(const b of this.teams[u.side].bonds){const a=b._ast;if(a.kind==='refuse'&&u.hero.id==='qing_gordon'&&this.round>=a.start_round!){const chance=a.values[0]+(this.members(this.teams[u.side]).has('qing_cheng_xueqi')?a.values[1]:0);if(this.rng.random()<chance)skip=true;}}
      if(!skip){if(u.rage>=100&&!u.control['沉默']&&u.hero.tags!=='杂兵'){u.rage=0;u.casts++;const ast=f(u,'first_enhancement_only')&&u.casts>1?this.ast(u.hero.active):u.active;this.log('cast',{id:u.hero.id,side:u.side,slot:u.slot,skill:u.hero.active});this.execute(u,ast,u.hero.active);if(this.teams[u.side].enabled.has('taiping'))this.resource(u.side,'信仰',5,u);if(u.casts===1)this.rage(u,f(u,'first_refund'));}else this.basic(u);u.actions++;u.acted_round=this.round;if(f(u,'action_speed'))u.bonus_speed=Math.min(f(u,'action_speed',1),u.bonus_speed+f(u,'action_speed'));}
      for(const k of Object.keys(u.control)){u.control[k]--;if(u.control[k]<=0)delete u.control[k];}this.invalidate();this.recordState();if(!live(this.teams[0]).length||!live(this.teams[1]).length)return this.result(false);
    }this.stepEnd();this.recordState();if(!live(this.teams[0]).length||!live(this.teams[1]).length)return this.result(false);
    }this.round=this.limit;return this.result(true);}
  result(timeout:boolean):BattleLog {return {winner:live(this.teams[0]).length&&!live(this.teams[1]).length?0:1,rounds:this.round,timeout,incidents:this.teams.map(t=>t.incident_round),survivors:this.teams.map(t=>live(t).map(u=>u.hero.id)),trace:this.trace};}
}
/** Pure deterministic calculation. No clock, storage, DOM, animation or global RNG. */
export function runBattle(teamA:TeamInput,teamB:TeamInput,terrain:Terrain,seed:number,options:BattleOptions={},data:Database=database):BattleLog {
  return new Combat(teamA,teamB,terrain,seed,options,data).run();
}
export function activeBonds(team:TeamInput,data:Database=database):ActiveBond[]{const ids=new Set([...team.heroes,team.monarch??'']);return data.bonds.filter(b=>b.type!=='宿敌').flatMap(b=>{let tier=b.need.split('/').map(Number).filter(n=>b.members.split(';').filter(x=>ids.has(x)).length>=n).length-1;
  if(b.type==='负面'){const a=data.compiled.bonds[b.bond_id];tier=a.kind==='suspicion'?(ids.has('tp_yang_xiuqing')&&ids.has('tp_wei_changhui')?0:-1):(ids.has('qing_li_hongzhang')&&ids.has('qing_gordon')?0:-1);}
  return tier>=0?[{...b,tier,_ast:data.compiled.bonds[b.bond_id]}]:[];});}
