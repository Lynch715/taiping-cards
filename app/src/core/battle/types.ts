import type { Hero, Skill, BondRow, Equipment, EquipmentSet, ExclusiveEquipment, CharacterArt, EnemyUnit, Stage, StarterCards, ProgressionLevel, StarUp, RecruitRule, EquipEnhance, EconomyChapter, StageLevelOverride, FeastRule } from '../data/types';
export type Campaign = 'taiping' | 'qing';
export type Terrain = '陆战' | '水战' | '攻城' | '守城';
export type FeatureValue = (number|string)[] | boolean | number;
export type Features = Record<string,FeatureValue>;
export interface Aura {target:string;stat:string;value:number;flat:boolean}
export interface Op {kind:string;target:string;duration:number;condition?:string|null;probability?:number;value:number;stat?:string;flat?:boolean;status?:string;resource?:string}
export interface AST {ops?:Op[];features?:Features;auras?:Aura[];meta?:Record<string,unknown>;round?:number|null;unknown:string[]}
export interface BondAST {kind:string;values:number[];text:string;members:string[];left?:string[];right?:string[];speed?:number;rate?:number;start_round?:number}
export interface ActiveBond extends BondRow {tier:number;_ast:BondAST}
export interface Compiled {skills:Record<string,AST>;bonds:Record<string,BondAST>;sets:Record<string,{aura:Aura;filter_fire:boolean;water_only:boolean;four:Features}>;exclusives:Record<string,{active:AST;passive:AST;extra:Features}>}
export interface Database {feast?:FeastRule[];stage_level_overrides?:StageLevelOverride[];heroes:Hero[];skills:Skill[];bonds:BondRow[];equipment:Equipment[];equipment_sets:EquipmentSet[];exclusive_equipment:ExclusiveEquipment[];characters:CharacterArt[];enemy_units:EnemyUnit[];stages:Stage[];starter_cards:StarterCards[];progression_levels:ProgressionLevel[];star_up:StarUp[];recruit:RecruitRule[];equip_enhance:EquipEnhance[];economy_chapters:EconomyChapter[];compiled:Compiled}
export interface EquippedInput {equipmentId:string;enhance:number}
export interface TeamInput {gear?:EquippedInput[][];exclusives?:boolean[];monarchStars?:number;monarchExclusive?:boolean;heroes:string[];monarch?:string|null;faction:Campaign;levels?:number[];stars?:number[]}
export interface BattleOptions {trace?:boolean;level?:number;stars?:number;gearSet?:string;quality?:string;enhance?:number;exclusives?:boolean;limit?:number;equipmentIds?:string[];exclusiveOwners?:[number,string][];exclusiveEffects?:boolean;allowDuplicates?:boolean}
export interface ActorState {id:string;slot:number;hp:number;max_hp:number;rage:number;escaped:boolean;control:Record<string,number>}
export interface TeamState {faith:number;suspicion:number;grain:number;actors:ActorState[]}
export interface BattleEvent {round:number;event:string;teams?:TeamState[];[key:string]:unknown}
export interface BattleLog {winner:number;rounds:number;timeout:boolean;incidents:(number|null)[];survivors:string[][];trace:BattleEvent[]}
export interface Buff {source:string;stat:string;value:number;flat:boolean;expires:number}
export interface Actor {hero:Hero;side:number;slot:number;faction:string;feature:Features;auras:Aura[];active:AST;base:Record<string,number>;max_hp:number;hp:number;rage:number;buffs:Buff[];shields:[number,number,string][];control:Record<string,number>;burns:[number,number,Actor][];actions:number;basics:number;casts:number;hits:number;kills:number;escaped:boolean;saved:boolean;desperation_used:boolean;immune_until:number;bonus_speed:number;exclusive:boolean;acted_round?:number}
export interface Lord {hero:Hero;active:AST;passive:AST;exclusive:boolean}
export interface Team {actors:Actor[];lord:Lord|null;assigned:Campaign;bonds:ActiveBond[];faith:number;faith_cap:number;heaven_until:number;suspicion:number;incident_round:number|null;grain:number;enabled:Set<string>;triggered_edict:boolean}
