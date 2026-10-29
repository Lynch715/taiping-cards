#!/usr/bin/env python3
"""Seeded CSV-driven combat simulator; unknown text is audited, never silently run.

Only standard-library dependencies. See balance_report.md for interpretation,
sampling, paired attack/defence games, confidence intervals and tuning history.
"""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import math
from rng import Mulberry32
import re
import statistics
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NUM = r"([+-]?\d+(?:\.\d+)?)"
BOUNDS = {"SSR": (265,275), "SR": (246,254), "R": (226,234)}
STAT = {"攻击":"attack", "防御":"defense", "速度":"speed", "智":"zhi",
        "全属性":"all", "受到伤害":"taken", "伤害":"damage", "暴击率":"crit",
        "暴击伤害":"crit_damage", "物防":"physical_defense", "怒气获取":"rage_gain"}


def norm(text):
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC",text)).replace("−","-").replace("≤","<=").rstrip("。.")


def read_csv(path):
    with path.open(encoding="utf-8-sig",newline="") as stream:
        return list(csv.DictReader(stream))


def numbers(text):
    return [float(x) for x in re.findall(r"[+-]?\d+(?:\.\d+)?",norm(text))]


def selector(text, default="self"):
    text=norm(text).removeprefix("并").removeprefix("并使其")
    if "使其" in text or text.startswith("其"):
        return "hit"
    if "回复我方生命最低者" in text or "我方生命最低" in text:
        return "ally_low"
    if "随机" in text and "敌人" in text:
        return "random:"+re.search(r"随机(\d+)",text).group(1)
    if "敌方" in text:
        if "生命最低" in text:
            return "enemy_back_low" if "后排" in text else "enemy_low"
        if "全体" in text:return "enemy_all"
        if "后排" in text:return "enemy_back_one" if "单体" in text else "enemy_back"
        if "前排" in text:return "enemy_front_one" if "单体" in text else "enemy_front"
        return "enemy_one"
    for label,key in [("湘军、淮军","xiang_huai"),("洋枪队","洋枪队"),("太平天国","taiping"),
                      ("湘军","湘军"),("淮军","淮军"),("外籍","外籍"),("火器","troop:火"),
                      ("骑兵","troop:骑"),("水师","troop:水")]:
        if label in text:return "ally:"+key
    if "我方全体" in text:return "ally_all"
    if "我方前排" in text:return "ally_front"
    if "自身" in text:return "self"
    return default


def active_ast(text):
    """Parse clauses by damage/heal/shield/stat/status/resource keywords."""
    text=norm(text);result={"ops":[],"unknown":[],"round":None,"meta":{}}
    scheduled=re.match(r"第(\d+)回合开始时发动:",text)
    if scheduled:
        result["round"]=int(scheduled.group(1));text=text[scheduled.end():]
    for block in re.split(r"[;；。]",text):
        if not block:continue
        duration_match=re.search(r"持续(\d+)回合",block)
        duration=int(duration_match.group(1)) if duration_match else 0
        block=re.sub(r"[,，]?持续\d+回合", "",block)
        if block.startswith("若击杀,怒气返还"):
            result["meta"]["kill_rage"]=numbers(block)[0];continue
        if block.startswith("若击杀,对另一名后排追加伤害"):
            result["meta"]["kill_followup"]=numbers(block)[0]/100;continue
        if block.startswith("目标为") and "伤害翻倍" in block:
            result["meta"]["target_double_name"]=block[3:block.index("时")];continue
        if block.startswith("目标为") and "伤害+" in block:
            result["meta"]["target_bonus"]=(block[3:block.index("时")],numbers(block)[0]/100);continue
        if block.startswith("若在第") and "回合释放" in block:
            a=numbers(block);result["meta"]["first_round_bonus"]=(int(a[0]),a[1]/100);continue
        if block.startswith("水战时改为"):
            result["meta"]["water_target"]=selector(block);continue
        if block.startswith("攻城地形时伤害+"):
            result["meta"]["siege_bonus"]=numbers(block)[0]/100;continue
        target="self"
        # Conjunctions inherit the preceding explicit target.
        for piece in re.split(r"[,，、]|并",block):
            if not piece:continue
            condition=None
            if piece.startswith("水战时"):
                condition="水战";piece=piece[3:]
            if piece.startswith("使其"):
                target="hit";piece=piece[2:]
            else:target=selector(piece,target)
            op={"target":target,"duration":duration,"condition":condition}
            probability=re.search(r"(\d+(?:\.\d+)?)%概率",piece)
            op["probability"]=float(probability.group(1))/100 if probability else 1.
            if "造成伤害" in piece or "追加伤害" in piece:
                match=re.search(r"(?:造成|追加)伤害"+NUM+r"%",piece)
                if match:
                    result["ops"].append({**op,"kind":"damage","value":float(match.group(1))/100});target="hit";continue
            if "回复" in piece:
                match=re.search(r"回复(?:自身)?"+NUM+r"%",piece)
                if not match:match=re.search(r"回复我方生命最低者"+NUM+r"%",piece)
                if match:result["ops"].append({**op,"kind":"heal","value":float(match.group(1))/100});continue
            if "护盾" in piece:
                match=re.search(r"护盾"+NUM+r"%",piece)
                if match:result["ops"].append({**op,"kind":"shield","value":float(match.group(1))/100});continue
            if "驱散" in piece:
                match=re.search(r"(\d+)个",piece)
                result["ops"].append({**op,"kind":"dispel","value":int(match.group(1)) if match else 999});continue
            status=next((x for x in ["眩晕","沉默","嘲讽"] if x in piece),None)
            if status:
                match=re.search(status+r"(\d+)回合",piece)
                result["ops"].append({**op,"kind":"status","status":status,"duration":int(match.group(1)) if match else duration or 1});continue
            match=re.search(r"灼烧"+NUM+r"%",piece)
            if match:result["ops"].append({**op,"kind":"burn","value":float(match.group(1))/100});continue
            match=re.search(r"连击(\d+)次",piece)
            if match:result["ops"].append({**op,"kind":"combo","value":int(match.group(1))});continue
            match=re.search(r"(信仰|猜忌|粮饷|怒气)(?:立即)?"+NUM,piece)
            if match:result["ops"].append({**op,"kind":"resource","resource":match.group(1),"value":float(match.group(2))});continue
            match=re.search(r"(攻击|防御|速度|受到伤害)"+NUM+r"(%|点)?",piece)
            if match:
                result["ops"].append({**op,"kind":"buff","stat":STAT[match.group(1)],
                    "value":float(match.group(2))/(100 if match.group(3)=="%" else 1),"flat":match.group(3)!="%"});continue
            result["unknown"].append(piece)
    return result


def passive_ast(text):
    """Full-match templates capture every coefficient from text, not hero-id constants."""
    text=norm(text);features={};auras=[];unknown=[]
    def feature(key,values):features[key]=values
    rules=[
      (r"战斗开始时我方全体怒气\+(\d+)","start_rage_all"),
      (r"战斗开始时我方太平天国武将怒气\+(\d+)","start_rage_taiping"),
      (r"猜忌每(\d+)点,自身攻击\+(\d+(?:\.\d+)?)%","suspicion_attack"),
      (r"攻击生命高于(\d+)%的敌人时伤害\+(\d+)%","target_high_bonus"),
      (r"自身阵亡时,我方全体攻击\+(\d+)%至战斗结束","death_attack_all"),
      (r"自身阵亡时,我方全体怒气\+(\d+)\(长沙殉难\)","death_rage_all"),
      (r"对生命低于(\d+)%的敌人暴击率\+(\d+)%","target_low_crit"),
      (r"我方未激活任何正面羁绊时,自身全属性\+(\d+)%","no_bond_all"),
      (r"我方未激活任何正面羁绊时,自身全属性\+(\d+)%、受到伤害\+(\d+)%","no_bond_risk"),
      (r"生命首次低于(\d+)%时回复(\d+)%,并免疫眩晕与沉默(\d+)回合\(大渡河绝境,每场1次\)","desperation"),
      (r"第1回合速度\+(\d+)\(必定先手\)","first_speed"),
      (r"普攻(?:有)?(\d+)%概率改打后排","rear_chance"),
      (r"我方存活人数<=(\d+)时,我方全体防御\+(\d+)%","low_alive_defense"),
      (r"洪秀全在君主位时,自身智\+(\d+)%","hong_zhi"),
      (r"每回合结束时回复自身(\d+(?:\.\d+)?)%","end_heal"),
      (r"生命低于(\d+)%时,每回合结束回复自身(\d+(?:\.\d+)?)%","end_heal_below"),
      (r"自身受到的治疗\+(\d+)%","healing_taken"),
      (r"我方每少1名存活武将,自身伤害\+(\d+)%","missing_damage"),
      (r"免死\(每场1次\)","death_save"),
      (r"水战时自身速度\+(\d+)点","water_speed"),
      (r"普攻有(\d+)%概率连击","combo_chance"),
      (r"攻城地形时自身伤害\+(\d+)%","siege_damage"),
      (r"自身第一次行动伤害\+(\d+)%","first_damage"),
      (r"生命低于(\d+)%时攻击\+(\d+)%","low_hp_attack"),
      (r"免疫攻击降低类减益","attack_debuff_immune"),
      (r"击杀敌人后回复自身(\d+)%","kill_heal"),
      (r"每次行动后自身速度\+(\d+)点\(最多\+(\d+)点\)","action_speed"),
      (r"洪仁玕在场时自身攻击\+(\d+)%","rengan_attack"),
      (r"我方每有1名武将阵亡,我方全体防御\+(\d+)%、攻击\+(\d+)%\(最多(\d+)层\)","death_aura"),
      (r"粮饷获取\+(\d+)%","grain_gain"),
      (r"自身在场时,敌方受到的治疗-(\d+)%","enemy_healing_reduction"),
      (r"粮饷每满(\d+),我方全体怒气\+(\d+)","grain_rage"),
      (r"主动技伤害\+(\d+)%","active_damage"),
      (r"首次释放主动技后怒气返还(\d+)","first_refund"),
      (r"自身普攻和技能取武、智中较高者计算","max_attack"),
      (r"每次受到攻击,自身攻击\+(\d+)%\(最多(\d+)层\)","hit_attack"),
      (r"每受到(\d+)次攻击,自身攻击\+(\d+)%\(最多(\d+)层\)","hit_attack_every"),
      (r"开场怒气\+(\d+)","start_rage"),
      (r"自身受到火器伤害-(\d+)%","firearm_reduction"),
      (r"自身受到的暴击伤害-(\d+)%","critical_reduction"),
      (r"我方每有1名淮军武将,我方全体速度\+(\d+)点","huai_speed"),
      (r"战斗开始时我方洋枪队武将防御\+(\d+)%","start_foreign_defense"),
      (r"战斗开始时随机获得攻击\+(\d+)%或防御\+(\d+)%","random_stat"),
      (r"每第(\d+)次普攻伤害\+(\d+)%","nth_basic"),
      (r"自身对步兵伤害额外\+(\d+)%","infantry_damage"),
      (r"生命高于(\d+)%时攻击\+(\d+)%","high_hp_attack"),
      (r"对(.+?)伤害\+(\d+)%","named_damage"),
      (r"编入太平天国阵营时自身攻击\+(\d+)%","assigned_taiping_attack"),
      (r"攻城地形时我方全体攻击\+(\d+)%","siege_attack_aura"),
      (r"开场信仰\+(\d+)","start_faith"),
      (r"信仰上限\+(\d+)","faith_cap"),
      (r"杨秀清在场时,猜忌每回合\+(\d+)","yang_round_suspicion"),
      (r"我方太平天国武将全属性\+(\d+(?:\.\d+)?)%,另按洪秀全智每(\d+)点再\+(\d+(?:\.\d+)?)%","hong_all"),
      (r"信仰达到(\d+)时,我方太平天国武将全属性\+(\d+(?:\.\d+)?)%,另按洪秀全智每(\d+)点再\+(\d+(?:\.\d+)?)%","hong_all_faith"),
      (r"洪秀全或洪天贵福在君主位时,君主政令的效果\+(\d+)%\(总理朝政\)","lord_amplify"),
    ]
    # Semicolons and full stops are true effect boundaries; commas are not.
    for part in re.split(r"[;；。]",text):
        if not part:continue
        matched=False
        for pattern,key in rules:
            m=re.fullmatch(pattern,part)
            if m:
                values=[]
                for v in m.groups():
                    try:values.append(float(v))
                    except ValueError:values.append(v)
                feature(key,values or True);matched=True;break
        if matched:continue
        # Multiple simple stat bonuses may share one target and comma.
        target=selector(part,"self")
        pattern=r"(全属性|攻击|防御|速度|智|受到伤害|暴击率|暴击伤害|怒气获取)"+NUM+r"(%|点)?"
        found=list(re.finditer(pattern,part))
        if found:
            residual=re.sub(pattern,"",part)
            residual=re.sub(r"我方|全体|前排|自身|太平天国武将|湘军、淮军武将|湘军武将|火器武将|骑兵|水师武将|外籍武将|[,，、]", "",residual)
            if not residual:
                for m in found:
                    auras.append({"target":target,"stat":STAT[m.group(1)],"value":float(m.group(2))/(100 if m.group(3)=="%" else 1),"flat":m.group(3)!="%"})
                continue
        unknown.append(part)
    return {"features":features,"auras":auras,"unknown":unknown}


class Data:
    def __init__(self, directory=ROOT/"data"):
        self.directory=Path(directory)
        self.heroes={r["id"]:r for r in read_csv(self.directory/"heroes.csv")}
        self.skills={r["skill_id"]:r for r in read_csv(self.directory/"skills.csv")}
        self.bonds=read_csv(self.directory/"bonds.csv")
        self.equipment={r["equip_id"]:r for r in read_csv(self.directory/"equipment.csv")}
        self.sets={r["set"]:r for r in read_csv(self.directory/"equipment_sets.csv")}
        self.exclusives={r["hero_id"]:r for r in read_csv(self.directory/"exclusive_equipment.csv")}
        self.names={r["name"]:r["id"] for r in self.heroes.values()}
        self.audit=[];self.cache={}
        for h in self.heroes.values():
            for key in ["tong","wu","zhi","su"]:h[key]=int(h[key])
            for key in ["active","passive"]:
                if h[key] not in self.skills:raise ValueError(f"Missing skill {h[key]}")
        self.compile()

    def compile(self):
        self.cache={};self.audit=[]
        for ident,row in self.skills.items():
            ast=active_ast(row["effect"]) if row["kind"] in {"主动","诏令"} else passive_ast(row["effect"])
            self.cache[ident]=ast
            if ast["unknown"]:self.audit.append({"table":"skills.csv","id":ident,"text":row["effect"],"unparsed":ast["unknown"]})
        for row in self.bonds:
            row["_ast"]=bond_ast(row,self.names)
            if row["_ast"]["kind"]=="unknown":self.audit.append({"table":"bonds.csv","id":row["bond_id"],"text":row["effect"],"unparsed":[row["effect"]]})
        self.set_ast={}
        for name,row in self.sets.items():
            first=norm(row["bonus2"]);second=norm(row["bonus4"])
            stat=re.search(r"(攻击|物防|速度)"+NUM+r"(%|点)",first)
            if not stat:raise ValueError("Unparsed equipment2:"+first)
            aura={"target":"self","stat":STAT[stat.group(1)],"value":float(stat.group(2))/(100 if stat.group(3)=="%" else 1),"flat":stat.group(3)!="%"}
            four={}
            if re.fullmatch(r"击杀后自身怒气\+\d+,攻击\+\d+%\(最多\d+层\)",second):
                v=numbers(second);four["set_kill_rage"]=[v[0]];four["set_kill_attack"]=[v[1]/100,v[2]]
            elif re.fullmatch(r"每回合开始时回复自身\d+(?:\.\d+)?%",second):
                four["set_start_heal"]=[numbers(second)[0]/100]
            elif re.fullmatch(r"每第\d+回合开始时回复自身\d+(?:\.\d+)?%",second):
                v=numbers(second);four['set_periodic_heal']=[v[0],v[1]/100]
            elif "信仰获取" in second:
                four["set_faith_gain"]=[float(re.search(r"信仰获取\+(\d+)%",second).group(1))/100]
                four["set_kill_rage"]=[float(re.search(r"怒气\+(\d+)",second).group(1))]
            elif "粮饷每满" in second:
                v=numbers(second);four["set_grain_heal"]=[v[0],v[1]/100]
            elif "概率追加" in second:
                v=numbers(second);four["set_extra_hit"]=[v[0]/100,v[1]/100]
            elif "第1回合伤害" in second:four["set_first_damage"]=[numbers(second)[1]/100]
            elif "水战时受到伤害" in second:four["set_water_taken"]=[numbers(second)[0]/100]
            else:raise ValueError("Unparsed equipment4:"+second)
            self.set_ast[name]={"aura":aura,"filter_fire":"火器武将" in first,"water_only":"水战时" in first,"four":four}

    def budget(self):
        rows=[]
        for h in self.heroes.values():
            if h["position"]=="君主":continue
            e=h["tong"]+(h["zhi"] if h["troop"]=="谋" else h["wu"])+h["su"]
            low,high=BOUNDS[h["rarity"]]
            rows.append({"id":h["id"],"name":h["name"],"rarity":h["rarity"],"E":e,"valid":low<=e<=high})
        return rows


@dataclass
class Buff:
    source: str
    stat: str
    value: float
    flat: bool
    expires: int


@dataclass
class Actor:
    hero: dict
    side: int
    slot: int
    faction: str
    feature: dict
    auras: list
    active: dict
    base: dict
    max_hp: float
    hp: float
    rage: float=0
    buffs: list=field(default_factory=list)
    shields: list=field(default_factory=list)
    control: dict=field(default_factory=dict)
    burns: list=field(default_factory=list)
    actions: int=0
    basics: int=0
    casts: int=0
    hits: int=0
    kills: int=0
    escaped: bool=False
    saved: bool=False
    desperation_used: bool=False
    immune_until: int=0
    bonus_speed: float=0
    exclusive: bool=False
    set_name: str=""
    set_pieces: int=0

    @property
    def id(self):return self.hero["id"]

    @property
    def alive(self):return self.hp>0 and not self.escaped


@dataclass
class Team:
    actors: list
    lord: dict|None
    assigned: str
    bonds: list=field(default_factory=list)
    faith: float=50
    faith_cap: float=100
    heaven_until: int=0
    suspicion: float=0
    incident_round: int|None=None
    grain: float=0
    enabled: set=field(default_factory=set)
    triggered_edict: bool=False

    def living(self):return [u for u in self.actors if u.alive]


def growth(level,stars):
    if not (1<=level<=100 and 1<=stars<=6):raise ValueError("level1..100 / stars1..6")
    return (1+.06*(level-1))*(1+.15*(stars-1))


def equipment_loadout(data, set_name, quality="精", enhance=0):
    rows=[r for r in data.equipment.values() if r["set"]==set_name and r["quality"]==quality]
    if len(rows)!=4:raise ValueError(f"Expected4 equipment slots: {set_name}/{quality}")
    if len({r["slot"] for r in rows})!=4:raise ValueError("Duplicate equipment slot")
    for r in rows:
        if not 0<=enhance<=int(r["enhance_max"]):raise ValueError("Enhancement out of range")
    return rows


def base_stats(h,level,stars,gear=(),enhance=0,exclusive=False,exrow=None):
    g=growth(level,stars);main="zhi" if h["troop"]=="谋" else "wu"
    mult=1.
    hp_mult=1.
    if exclusive and exrow:
        values=numbers(exrow["stat_bonus"]);mult+=values[0]/100;hp_mult+=values[1]/100
    w=h["wu"]*(mult if main=="wu" else 1);z=h["zhi"]*(mult if main=="zhi" else 1)
    s={"hp":(h["tong"]*24+w*6)*g*hp_mult,"atk":w*3*g,"int":z*3*g,
       "def":h["tong"]*1.2*g,"res":z*g,"speed":h["su"],"crit":.05,"crit_damage":1.5,"start_rage":0}
    mapping={"攻击":["atk","int"],"生命":["hp"],"物防":["def"],"谋防":["res"],"速度":["speed"],"开场怒气":["start_rage"],"暴击率%":["crit"]}
    for gear_index,row in enumerate(gear):
        for stat_key,val_key in [("main_stat","main_value"),("sub_stat","sub_value")]:
            value=float(row[val_key])*(1+.1*(enhance[gear_index] if isinstance(enhance,list) else enhance))
            if row[stat_key].endswith("%"):value/=100
            for key in mapping[row[stat_key]]:s[key]+=value
    return s


def feature(u,key,index=0,default=0):
    value=u.feature.get(key)
    return value[index] if isinstance(value,list) else (default if not value else 1)


def exclusive_skills(data,h,enabled):
    """Apply named-skill arrow replacements, then parse the resulting keyword text."""
    active=data.skills[h["active"]]["effect"];passive=data.skills[h["passive"]]["effect"]
    extra={};unknown=[]
    if not enabled or h["id"] not in data.exclusives:
        return copy.deepcopy(data.cache[h["active"]]),copy.deepcopy(data.cache[h["passive"]]),extra,unknown
    raw=norm(data.exclusives[h["id"]]["effect"])
    quoted=re.search(r"「([^」]+)」",raw)
    target="active" if quoted and data.skills[h["active"]]["name"]==quoted.group(1) else "passive"
    text=norm(active if target=="active" else passive)
    pairs=re.findall(r"([+-]?\d+(?:\.\d+)?%?)(回合|次)?→(?:每第)?([+-]?\d+(?:\.\d+)?%?)(回合|次)?",raw)
    for old,old_unit,new,new_unit in pairs:
        old+=old_unit;new+=new_unit
        if "层数上限" in raw:
            old,new="最多"+old+"层","最多"+new+"层"
        elif "速度上限" in raw:
            old,new="最多"+old+"点","最多"+new+"点"
        elif "每第" in raw:
            old,new="每第"+old,"每第"+new
        elif "提前到第" in raw:
            old,new="第"+old+"回合","第"+new+"回合"
        if "绝境回复" in raw:
            old,new="回复"+old,"回复"+new
        if old not in text:
            # Output explicitly lists stale arrow clauses after a coefficient edit.
            unknown.append("专属替换找不到原值:"+old+" in "+text)
        else:text=text.replace(old,new,1)
    if "提前到第" in raw and not pairs:
        n=int(numbers(raw)[0]);text=re.sub(r"第\d+回合开始",f"第{n}回合开始",text)
    if "取消防御惩罚" in raw:text=re.sub(r"[;；]?自身防御-\d+%", "",text)
    if target=="active":active=text
    else:passive=text
    a,p=active_ast(active),passive_ast(passive)
    if "额外使敌方全体怒气" in raw:
        rage_value=float(re.search(r"敌方全体怒气([+-]\d+)",raw).group(1))
        a["ops"].append({"kind":"resource","target":"enemy_all","resource":"怒气","value":rage_value,"duration":0,"condition":None,"probability":1.})
        extra["suspicion_multiplier"]=1-float(re.search(r"猜忌-(\d+)%",raw).group(1))/100
    if "并攻击+" in raw and "绝境" in raw:
        m=re.search(r"并攻击\+(\d+)%,持续(\d+)回合",raw);extra["desperation_attack"]=[float(m.group(1))/100,int(m.group(2))]
    if "触发后自身攻击+" in raw:
        m=re.search(r"攻击\+(\d+)%,持续(\d+)回合",raw);extra["save_attack"]=[float(m.group(1))/100,int(m.group(2))]
    if "击杀后可立即再释放一次" in raw:extra["kill_recast"]=True
    if "额外使敌方全体攻击" in raw:
        n=numbers(raw);a["ops"].append({"kind":"buff","target":"enemy_all","stat":"attack","value":n[0]/100,"flat":False,"duration":int(n[1]),"condition":None,"probability":1.})
    if "附带" in raw and "概率眩晕" in raw:
        n=numbers(raw);a["ops"].append({"kind":"status","target":"hit","status":"眩晕","probability":n[0]/100,"duration":int(n[1]),"condition":None})
    if "驱散1个→全部减益" in raw:
        for op in a["ops"]:
            if op["kind"]=="dispel":op["value"]=999
    if raw.startswith("水战时我方全体受到伤害"):
        extra["water_team_reduction"]=-numbers(raw)[0]/100
    if '仅首次释放主动技时生效' in raw:extra['first_enhancement_only']=True
    # Every currently documented non-arrow suffix is named above.
    known=bool(pairs) or any(s in raw for s in ["提前到第","额外使","并攻击+","触发后自身攻击+","击杀后可立即再释放一次","附带","驱散1个→全部减益","水战时我方全体受到伤害"])
    if not known:unknown.append(raw)
    unknown+=a["unknown"]+p["unknown"]
    return a,p,extra,unknown


def bond_ast(row,names):
    text=norm(row["effect"]);pcts=[float(x)/100 for x in re.findall(r"([+-]?\d+(?:\.\d+)?)%",text)]
    out={"kind":"unknown","values":pcts,"text":text,"members":row["members"].split(";")}
    if row["type"]=="宿敌":
        left,right=row["members"].split(">");out.update(left=left.split(";"),right=right.split(";"))
        out["kind"]="block_desperation" if "绝境不能触发" in text else "rival_reduce" if "受到" in text else "rival_damage"
        return out
    for word,kind in [
        ("信仰获取","faith_gain"),("后行动者","second_pair"),("每少1名存活","missing_pair"),
        ("第1回合伤害","water_first"),("任一人阵亡","partner_death"),("守城地形","defend_aura"),
        ("粮饷获取","grain_gain"),("曾国荃攻击","siege_aura"),("罗泽南在场","presence_pair"),
        ("水战时两人全属性","water_pair_all"),("成员骑兵攻击","member_cavalry"),
        ("成员攻击","member_attack"),("成员速度","member_speed"),("我方前排防御","front_defense"),
        ("我方火器武将攻击","fire_aura"),("两人暴击率","pair_crit"),
        ("猜忌每回合","suspicion"),("概率罢战","refuse")]:
        if word in text:out["kind"]=kind;break
    if out["kind"]=="member_speed":out["values"]=[float(x) for x in re.findall(r"[+](\d+)",text)]
    if out["kind"]=="water_first":out["speed"]=float(re.search(r"速度\+(\d+)",text).group(1))
    if out["kind"]=="suspicion":out["rate"]=float(re.search(r"再\+(\d+)",text).group(1))
    if out["kind"]=="refuse":out["start_round"]=int(re.search(r"第(\d+)回合",text).group(1))
    return out


def canonical(value):
    if isinstance(value,float):return math.floor(value*1_000_000+.5)/1_000_000
    if isinstance(value,list):return [canonical(x) for x in value]
    if isinstance(value,dict):return {k:canonical(v) for k,v in value.items()}
    return value


class Battle:
    def __init__(self,data,rosters,lords=(None,None),assigned=("taiping","qing"),
                 terrain="陆战",level=50,stars=3,seed=1,gear_set=None,quality="精",enhance=0,
                 use_exclusives=False,limit=20,trace=False,equipment_ids=None,
                 exclusive_owners=None,exclusive_effects=True,unit_levels=None,unit_stars=None,allow_duplicates=False,unit_gear=None,unit_exclusives=None,lord_stars=None,lord_exclusives=None):
        if data.audit:raise ValueError("Unparsed skills: "+str(data.audit))
        self.data=data;self.rng=Mulberry32(seed);self.terrain=terrain;self.round=0
        self.limit=limit;self.version=0;self.cache={};self.trace=[] if trace else None
        self.exclusive_unknown=[];self.recast_used=set();self.teams=[]
        for side,ids in enumerate(rosters):
            if len(ids)!=len(set(ids)) and not (allow_duplicates and all(data.heroes[i].get("tags")=="杂兵" for i in ids if ids.count(i)>1)):raise ValueError("Duplicate hero in a roster")
            if not 1<=len(ids)<=5:raise ValueError("Roster must contain1..5 combat heroes")
            actors=[]
            for slot,ident in enumerate(ids):
                h=data.heroes[ident]
                if h["position"]=="君主":raise ValueError("Monarch cannot fight: "+ident)
                actor_stars=unit_stars[side][slot] if unit_stars else stars
                actor_level=unit_levels[side][slot] if unit_levels else level
                enabled=actor_stars>=4 and (unit_exclusives[side][slot] if unit_exclusives is not None else use_exclusives if exclusive_owners is None else (side,ident) in exclusive_owners)
                act,pas,extra,unknown=exclusive_skills(data,h,enabled and exclusive_effects)
                self.exclusive_unknown += [{"id":ident,"unparsed":x} for x in unknown]
                actor_enhance=enhance
                if unit_gear is not None:
                    entries=unit_gear[side][slot];gear=[data.equipment[x['equipmentId']] for x in entries];actor_enhance=[x['enhance'] for x in entries]
                    if len(gear)>4 or len({r['slot'] for r in gear})!=len(gear):raise ValueError('Duplicate equipment slot')
                    if any(not isinstance(n,int) or not 0<=n<=int(r['enhance_max']) for n,r in zip(actor_enhance,gear)):raise ValueError('Enhancement out of range')
                elif equipment_ids is not None:
                    gear=[data.equipment[x] for x in equipment_ids]
                    if len(gear)>4 or len({r["slot"] for r in gear})!=len(gear):raise ValueError("Duplicate equipment slot or more than4 pieces")
                    if any(not 0<=enhance<=int(r["enhance_max"]) for r in gear):raise ValueError("Enhancement out of range")
                else:gear=equipment_loadout(data,gear_set,quality,enhance) if gear_set else []
                stats=base_stats(h,actor_level,actor_stars,gear,actor_enhance,enabled,data.exclusives.get(ident))
                f=copy.deepcopy(pas["features"]);f.update(extra)
                actor=Actor(h,side,slot,assigned[side] if h["faction"]=="dual" else h["faction"],
                    f,copy.deepcopy(pas["auras"]),act,stats,stats["hp"],stats["hp"],
                    exclusive=enabled and ident in data.exclusives,
                    set_name=gear_set or "",set_pieces=len(gear))
                for set_name,pieces in Counter(r["set"] for r in gear).items():
                    set_ast=data.set_ast[set_name]
                    if pieces>=2 and (not set_ast["filter_fire"] or h["troop"]=="火") and (not set_ast["water_only"] or terrain=="水战"):
                        actor.auras.append(copy.deepcopy(set_ast["aura"]))
                    if pieces>=4:actor.feature.update(copy.deepcopy(set_ast["four"]))
                actors.append(actor)
            lord=None
            if lords[side]:
                h=data.heroes[lords[side]]
                if h["position"]!="君主":raise ValueError("Combat hero in monarch slot")
                enabled=(lord_stars[side] if lord_stars else stars)>=4 and (lord_exclusives[side] if lord_exclusives is not None else use_exclusives if exclusive_owners is None else (side,h['id']) in exclusive_owners)
                aa,pp,extra,unknown=exclusive_skills(data,h,enabled and exclusive_effects)
                self.exclusive_unknown += [{"id":h["id"],"unparsed":x} for x in unknown]
                lord={"hero":h,"active":aa,"passive":pp,"exclusive":enabled}
            team=Team(actors,lord,assigned[side])
            counts=Counter(u.faction for u in actors)
            team.enabled={f for f,n in counts.items() if n>=3}
            self.teams.append(team)
        if self.exclusive_unknown:raise ValueError("Unparsed exclusive: "+str(self.exclusive_unknown))
        self._setup_bonds()
        self._start()
        self.record_state()

    def log(self,event,**values):
        if self.trace is not None:self.trace.append(canonical({"round":self.round,"event":event,**values}))

    def record_state(self):
        if self.trace is None:return
        self.log('state',teams=[{'faith':t.faith,'suspicion':t.suspicion,'grain':t.grain,'actors':[{'id':u.id,'slot':u.slot,'hp':u.hp,'max_hp':u.max_hp,'rage':u.rage,'escaped':u.escaped,'control':dict(u.control)} for u in t.actors]} for t in self.teams])

    def invalidate(self):self.version+=1;self.cache.clear()

    def policy_factor(self,team):
        if not team.lord or team.lord['hero']['id'] not in {'tp_hong_xiuquan','tp_hong_tianguifu'}:return 1.
        key=('policy',id(team),self.version)
        if key not in self.cache:self.cache[key]=1+sum(feature(u,'lord_amplify')/100 for u in team.living())
        return self.cache[key]

    def sync_max_hp(self,side):
        """Conditional all-stat auras preserve HP ratio, never grant free healing."""
        changed=False
        for u in self.teams[side].living():
            maximum=self.stats(u)['hp']
            if abs(maximum-u.max_hp)>1e-7:
                u.hp*=maximum/u.max_hp;u.max_hp=maximum;changed=True
        if changed:self.invalidate()

    def _members(self,team):
        return {u.id for u in team.actors}|({team.lord["hero"]["id"]} if team.lord else set())

    def _setup_bonds(self):
        for team in self.teams:
            ids=self._members(team)
            for b in self.data.bonds:
                if b["type"]=="宿敌":continue
                members=b["members"].split(";");count=len(set(members)&ids)
                if b["type"]=="负面":
                    # Conditions remain in the effect, not generic minimum counts.
                    if "猜忌" in b["effect"]:
                        if {"tp_yang_xiuqing","tp_wei_changhui"}<=ids:team.bonds.append({**b,"tier":0})
                    elif {"qing_li_hongzhang","qing_gordon"}<=ids:team.bonds.append({**b,"tier":0})
                    continue
                thresholds=[int(x) for x in b["need"].split("/")]
                tier=sum(count>=n for n in thresholds)-1
                if tier>=0:team.bonds.append({**b,"tier":tier})
            self.log("bonds",side=self.teams.index(team),ids=[b["bond_id"] for b in team.bonds])

    def matches(self,u,scope,owner):
        if scope=="self":return u is owner
        if scope=="hit":return False
        if scope=="ally_all":return u.side==owner.side
        if scope=="ally_front":return u.side==owner.side and u.slot<2
        if scope.startswith("ally:"):
            key=scope[5:]
            if u.side!=owner.side:return False
            if key in {"taiping","qing"}:return u.faction==key
            if key.startswith("troop:"):return u.hero["troop"]==key[6:]
            tags=u.hero["tags"].split(";")
            return any(x in tags for x in ["湘军","淮军"]) if key=="xiang_huai" else key in tags
        return False

    def _start(self):
        for side,team in enumerate(self.teams):
            if team.lord:
                f=team.lord["passive"]["features"]
                factor=self.policy_factor(team)
                team.faith_cap+=f.get("faith_cap",[0])[0]*factor
                team.faith+=f.get("start_faith",[0])[0]*factor
            for u in team.actors:
                u.rage=u.base["start_rage"]+(30 if u.hero["troop"]=="谋" else 0)+feature(u,"start_rage")
            for u in team.actors:
                for v in team.actors:
                    self.rage(v,feature(u,"start_rage_all"))
                    if v.faction=="taiping":self.rage(v,feature(u,"start_rage_taiping"))
                    if "洋枪队" in v.hero["tags"] and feature(u,"start_foreign_defense"):
                        self.buff(v,"start:"+u.id,"defense",feature(u,"start_foreign_defense")/100,False,999)
                if feature(u,"random_stat"):
                    key=self.rng.choice(["attack","defense"])
                    self.buff(u,"random:"+u.id,key,feature(u,"random_stat",0 if key=="attack" else 1)/100,False,999)
        # Initialize maximum HP after permanent all-attribute and terrain modifiers.
        for team in self.teams:
            for u in team.actors:u.max_hp=self.stats(u)["hp"];u.hp=u.max_hp;u.rage=min(100,u.rage)
        self.invalidate()

    def buffs_for(self,u):
        bonuses=defaultdict(float);flats=defaultdict(float)
        def add(key,value,flat=False):
            (flats if flat else bonuses)[key]+=value
        for b in u.buffs:
            if b.expires>=self.round:add(b.stat,b.value,b.flat)
        team=self.teams[u.side]
        for owner in team.living():
            for a in owner.auras:
                if self.matches(u,a["target"],owner):add(a["stat"],a["value"],a["flat"])
            if feature(owner,"low_alive_defense") and len(team.living())<=feature(owner,"low_alive_defense"):
                add("defense",feature(owner,"low_alive_defense",1)/100)
            if feature(owner,"death_aura"):
                dead=sum(v.hp<=0 and not v.escaped for v in team.actors);layers=min(dead,feature(owner,"death_aura",2))
                add("defense",layers*feature(owner,"death_aura")/100);add("attack",layers*feature(owner,"death_aura",1)/100)
            if feature(owner,"huai_speed"):
                add("speed",sum("淮军" in v.hero["tags"] for v in team.actors)*feature(owner,"huai_speed"),True)
            if self.terrain=="攻城" and feature(owner,"siege_attack_aura"):add("attack",feature(owner,"siege_attack_aura")/100)
            if self.terrain=="水战" and owner.feature.get("water_team_reduction"):add("taken",-owner.feature["water_team_reduction"])
        if team.lord:
            lord=team.lord
            fake=team.actors[0]
            for a in lord["passive"]["auras"]:
                if self.matches(u,a["target"],fake):add(a["stat"],a["value"]*self.policy_factor(team),a["flat"])
            f=lord["passive"]["features"]
            hong=f.get('hong_all')
            conditional=f.get('hong_all_faith')
            if conditional and team.faith>=conditional[0]:hong=conditional[1:]
            if hong and u.faction=="taiping":
                base,step,value=hong
                ex=self.data.exclusives.get(lord["hero"]["id"])
                zhi=lord["hero"]["zhi"]*(1+numbers(ex["stat_bonus"])[0]/100 if lord["exclusive"] and ex else 1)
                add("all",(base+math.floor(zhi/step)*value)/100*self.policy_factor(team))
        if feature(u,"no_bond_all") and not any(b["type"]=="正面" for b in team.bonds):add("all",feature(u,"no_bond_all")/100)
        if feature(u,'no_bond_risk') and not any(b['type']=='正面' for b in team.bonds):
            add('all',feature(u,'no_bond_risk')/100);add('taken',feature(u,'no_bond_risk',1)/100)
        ratio=u.hp/u.max_hp if u.max_hp else 1
        if feature(u,"low_hp_attack") and ratio<feature(u,"low_hp_attack")/100:add("attack",feature(u,"low_hp_attack",1)/100)
        if feature(u,"high_hp_attack") and ratio>feature(u,"high_hp_attack")/100:add("attack",feature(u,"high_hp_attack",1)/100)
        if feature(u,"suspicion_attack"):add("attack",math.floor(team.suspicion/feature(u,"suspicion_attack"))*feature(u,"suspicion_attack",1)/100)
        if feature(u,"hit_attack"):add("attack",min(u.hits,feature(u,"hit_attack",1))*feature(u,"hit_attack")/100)
        if feature(u,'hit_attack_every'):
            every,bonus,cap=u.feature['hit_attack_every'];add('attack',min(math.floor(u.hits/every),cap)*bonus/100)
        if feature(u,"hong_zhi") and team.lord and team.lord["hero"]["id"]=="tp_hong_xiuquan":add("zhi",feature(u,"hong_zhi")/100)
        if feature(u,"rengan_attack") and any(v.id=="tp_hong_rengan" for v in team.living()):add("attack",feature(u,"rengan_attack")/100)
        if feature(u,"assigned_taiping_attack") and u.faction=="taiping":add("attack",feature(u,"assigned_taiping_attack")/100)
        if self.round==1:add("speed",feature(u,"first_speed")+(20 if u.hero["troop"]=="骑" else 0),True)
        if self.terrain=="水战":add("speed",feature(u,"water_speed"),True)
        if self.terrain=="水战" and u.hero["troop"]=="水":add("all",.2)
        elif u.hero["troop"]=="水":add("attack",-.1)
        add("speed",u.bonus_speed,True)
        if u.faction=="taiping" and self.round<=team.heaven_until and team.heaven_until>0:add("attack",.2)
        if u.faction=="qing" and "qing" in team.enabled:add("defense",min(5,int(team.grain//30))*.05)
        defender=1 if self.terrain=="攻城" else 0 if self.terrain=="守城" else None
        if u.side==defender:add("defense",.2)
        self.bond_bonuses(u,add)
        return bonuses,flats

    def stats(self,u):
        key=(id(u),self.version)
        if key in self.cache:return self.cache[key]
        b,f=self.buffs_for(u);s=u.base.copy();all_bonus=b["all"]
        s["hp"]*=max(.05,1+all_bonus)
        s["atk"]*=max(.05,1+all_bonus+b["attack"])
        s["int"]*=max(.05,1+all_bonus+b["zhi"]+b["attack"])
        s["def"]*=max(.05,1+all_bonus+b["defense"]+b["physical_defense"])
        s["res"]*=max(.05,1+all_bonus+b["zhi"]+b["defense"])
        s["speed"]=s["speed"]*max(.05,1+all_bonus+b["speed"])+f["speed"]
        s["crit"]=min(1,max(0,s["crit"]+b["crit"]))
        s["crit_damage"]=max(1,s["crit_damage"]+b["crit_damage"])
        s["damage_bonus"]=b["damage"];s["taken"]=b["taken"];s["rage_gain"]=max(0,1+b["rage_gain"])
        self.cache[key]=s;return s

    def buff(self,u,source,stat,value,flat,duration):
        if value<0 and stat=="attack" and feature(u,"attack_debuff_immune"):return
        expires=self.round+duration-1 if duration<999 else 999
        previous=next((b for b in u.buffs if b.source==source and b.stat==stat and b.flat==flat),None)
        if previous:
            # Same named source does not stack; refresh the strongest magnitude.
            previous.value=max(previous.value,value) if value>=0 else min(previous.value,value)
            previous.expires=max(previous.expires,expires)
        else:u.buffs.append(Buff(source,stat,value,flat,expires))
        self.invalidate()

    def rage(self,u,amount):
        # Avoid recursive stats during initial construction.
        gain=1.
        team=self.teams[u.side] if len(self.teams)>u.side else None
        if amount>0 and team and team.lord:
            for a in team.lord["passive"]["auras"]:
                if a["stat"]=="rage_gain":gain+=a["value"]
        u.rage=max(0,min(100,u.rage+amount*gain))

    def bond_bonuses(self,u,add):
        team=self.teams[u.side];living=team.living();alive={v.id for v in living}
        for b in team.bonds:
            a=b["_ast"];kind=a["kind"];p=a["values"];member=u.id in a["members"]
            val=p[min(b["tier"],len(p)-1)] if p else 0
            if kind=="second_pair" and member:add("attack",p[0])
            elif kind=="missing_pair" and member:add("attack",(len(team.actors)-len(living))*p[0])
            elif kind=="water_first" and member and self.terrain=="水战":add("speed",a["speed"],True)
            elif kind=="defend_aura" and self.terrain=="守城":add("defense",p[0])
            elif kind=="fire_aura" and u.hero["troop"]=="火":add("attack",val)
            elif kind=="pair_crit" and member:add("crit",p[0])
            elif kind=="siege_aura":
                if self.terrain=="攻城":add("damage",p[0])
                if member and u.id==a["members"][-1]:add("attack",p[1])
            elif kind=="presence_pair":
                if u.id==a["members"][1] and a["members"][0] in alive:add("crit",p[0])
                if u.id==a["members"][0] and a["members"][1] in alive:add("defense",p[1])
            elif kind=="water_pair_all" and member and self.terrain=="水战":add("all",p[0])
            elif kind=="member_attack" and member:add("attack",val)
            elif kind=="member_cavalry" and member and u.hero["troop"]=="骑":add("attack",val)
            elif kind=="member_speed" and member:add("speed",val,True)
            elif kind=="front_defense" and u.slot<2:add("defense",val)

    def resource(self,side,key,value,source=None):
        team=self.teams[side]
        if key=="信仰":
            if team.lord:team.faith_cap=100+team.lord['passive']['features'].get('faith_cap',[0])[0]*self.policy_factor(team)
            mult=1.
            for b in team.bonds:
                if b["_ast"]["kind"]=="faith_gain":mult+=b["_ast"]["values"][b["tier"]]
            if source:mult+=feature(source,"set_faith_gain")
            team.faith=max(0,min(team.faith_cap,team.faith+value*mult))
            if "taiping" in team.enabled and team.faith>=100 and not team.heaven_until:
                team.heaven_until=self.round+1;self.log("heaven",side=side)
        elif key=="猜忌":
            if team.incident_round is not None:return
            if source:value*=source.feature.get("suspicion_multiplier",1.)
            team.suspicion=max(0,min(100,team.suspicion+value))
            if team.suspicion>=100:
                team.incident_round=self.round;team.suspicion=0
                for u in team.living():
                    if u.id in {"tp_yang_xiuqing","tp_wei_changhui"}:u.hp*=.5
                    if u.id=="tp_shi_dakai":u.escaped=True
                self.log("tianjing_incident",side=side)
        elif key=="粮饷":
            mult=1+sum(feature(u,"grain_gain")/100 for u in team.living())
            for b in team.bonds:
                if b["_ast"]["kind"]=="grain_gain":mult+=b["_ast"]["values"][0]
            previous=team.grain;team.grain=max(0,team.grain+value*mult)
            for owner in team.living():
                threshold=feature(owner,"grain_rage")
                if threshold:
                    count=int(team.grain//threshold)-int(previous//threshold)
                    for u in team.living():self.rage(u,count*feature(owner,"grain_rage",1))
                if feature(owner,"set_grain_heal"):
                    threshold=feature(owner,"set_grain_heal")
                    count=int(team.grain//threshold)-int(previous//threshold)
                    if count:self.heal(owner,feature(owner,"set_grain_heal",1)*count,owner)
        self.invalidate()
        if key=='信仰' and team.lord and team.lord['passive']['features'].get('hong_all_faith'):self.sync_max_hp(side)

    def targets(self,source,scope,hit=None):
        ally=self.teams[source.side].living();enemy=self.teams[1-source.side].living()
        if scope=="self":return [source] if source.alive else []
        if scope=="hit":return [u for u in hit or [] if u.alive]
        if scope=="ally_low":return [min(ally,key=lambda u:(u.hp/u.max_hp,u.slot))] if ally else []
        if scope.startswith("ally"):return [u for u in ally if self.matches(u,scope,source)]
        if not enemy:return []
        taunting=[u for u in enemy if u.control.get("嘲讽",0)>0]
        one=scope in {"enemy_one","enemy_front_one","enemy_back_one","enemy_low","enemy_back_low"}
        if one and taunting:return [min(taunting,key=lambda u:u.slot)]
        if scope=="enemy_all":return enemy
        if scope.startswith("random:"):return self.rng.sample(enemy,min(len(enemy),int(scope.split(":")[1])))
        front=[u for u in enemy if u.slot<2];back=[u for u in enemy if u.slot>=2]
        if scope.startswith("enemy_front"):pool=front or back
        elif scope.startswith("enemy_back"):pool=back or front
        else:pool=enemy
        if scope in {"enemy_front","enemy_back"}:return pool
        if "low" in scope:return [min(pool,key=lambda u:(u.hp/u.max_hp,u.slot))]
        return [self.rng.choice(pool)] if pool else []

    def normal_target(self,u):
        if u.hero["troop"]=="火":return self.targets(u,"enemy_low")
        chance=max(.3 if u.hero["troop"]=="骑" else 0,feature(u,"rear_chance")/100)
        return self.targets(u,"enemy_back_one" if self.rng.random()<chance else "enemy_front_one")

    def heal(self,target,fraction,source=None):
        if not target.alive:return 0
        mult=1+feature(target,"healing_taken")/100
        mult-=sum(feature(u,"enemy_healing_reduction")/100 for u in self.teams[1-target.side].living())
        amount=max(0,fraction*target.max_hp*max(0,mult));before=target.hp
        target.hp=min(target.max_hp,target.hp+amount);self.invalidate()
        return target.hp-before

    def rival_bonus(self,attacker,target):
        value=0.
        for b in self.data.bonds:
            a=b["_ast"]
            if a["kind"]=="rival_damage" and attacker.id in a["left"] and target.id in a["right"]:
                value+=a["values"][0]
            elif a["kind"]=="rival_reduce" and target.id in a["left"] and attacker.id in a["right"]:
                value+=a["values"][0]  # value already negative
        return value

    def desperation_blocked(self,u):
        enemy={v.id for v in self.teams[1-u.side].living()}
        return any(b["_ast"]["kind"]=="block_desperation" and u.id in b["_ast"]["right"]
                   and enemy.intersection(b["_ast"]["left"]) for b in self.data.bonds)

    def after_death(self,u,killer):
        self.log("death",id=u.id,side=u.side,slot=u.slot)
        team=self.teams[u.side]
        for v in team.living():
            if feature(u,"death_attack_all"):self.buff(v,"death:"+u.id,"attack",feature(u,"death_attack_all")/100,False,999)
            if feature(u,'death_rage_all'):self.rage(v,feature(u,'death_rage_all'))
        for b in team.bonds:
            a=b["_ast"]
            if a["kind"]=="partner_death" and u.id in a["members"]:
                for v in team.living():
                    if v.id in a["members"]:self.buff(v,"bond:"+b["bond_id"],"attack",a["values"][0],False,999)
        if killer:
            if "taiping" in self.teams[killer.side].enabled:self.resource(killer.side,"信仰",10,killer)
            if killer.alive:
                killer.kills+=1
                if feature(killer,"kill_heal"):self.heal(killer,feature(killer,"kill_heal")/100,killer)
                self.rage(killer,feature(killer,"set_kill_rage"))
                if feature(killer,'set_kill_attack'):
                    self.buff(killer,'set:kill_attack','attack',min(killer.kills,feature(killer,'set_kill_attack',1))*feature(killer,'set_kill_attack'),False,999)
        self.invalidate()
        if feature(u,'lord_amplify'):
            if team.lord:
                team.faith_cap=100+team.lord['passive']['features'].get('faith_cap',[0])[0]*self.policy_factor(team)
                team.faith=min(team.faith,team.faith_cap)
            self.sync_max_hp(u.side)

    def apply_loss(self,target,amount,source,allow_save=True):
        if not target.alive:return False
        if amount>=target.hp and allow_save and feature(target,"death_save") and not target.saved:
            target.hp=1;target.saved=True
            if target.feature.get("save_attack"):
                v,d=target.feature["save_attack"];self.buff(target,"exclusive:save","attack",v,False,d)
        else:target.hp=max(0,target.hp-amount)
        self.invalidate()
        if target.hp<=0:self.after_death(target,source);return True
        if feature(target,"desperation") and not target.desperation_used and target.hp/target.max_hp<feature(target,"desperation")/100 and not self.desperation_blocked(target):
            target.desperation_used=True;self.heal(target,feature(target,"desperation",1)/100,target)
            target.immune_until=self.round+int(feature(target,"desperation",2))-1
            target.control.pop("眩晕",None);target.control.pop("沉默",None)
            if target.feature.get("desperation_attack"):
                v,d=target.feature["desperation_attack"];self.buff(target,"exclusive:desperation","attack",v,False,d)
        return False

    def damage(self,u,target,coefficient=1.,active=False,basic=False,meta=None):
        if not u.alive or not target.alive:return False
        a=self.stats(u);d=self.stats(target)
        magical=u.hero["troop"]=="谋"
        if feature(u,"max_attack"):magical=a["int"]>a["atk"]
        attack=a["int"] if magical else a["atk"];defense=d["res"] if magical else d["def"]
        mult=1.2 if (u.hero["troop"],target.hero["troop"]) in {("骑","步"),("步","火"),("火","骑")} else 1.
        bonus=a["damage_bonus"]+self.rival_bonus(u,target)
        if active:bonus+=feature(u,"active_damage")/100+(.15 if u.hero["troop"]=="谋" else 0)
        if self.terrain=="攻城":bonus+=feature(u,"siege_damage")/100
        if u.actions==0:bonus+=feature(u,"first_damage")/100
        if target.hp/target.max_hp>feature(u,"target_high_bonus")/100 and feature(u,"target_high_bonus"):bonus+=feature(u,"target_high_bonus",1)/100
        bonus+=(len(self.teams[u.side].actors)-len(self.teams[u.side].living()))*feature(u,"missing_damage")/100
        if target.hero["troop"]=="步":bonus+=feature(u,"infantry_damage")/100
        named=u.feature.get("named_damage")
        if named and target.hero["name"] in str(named[0]).split("、"):bonus+=named[1]/100
        if basic and feature(u,"nth_basic") and u.basics%int(feature(u,"nth_basic"))==0:bonus+=feature(u,"nth_basic",1)/100
        if self.round==1:bonus+=feature(u,"set_first_damage")
        for b in self.teams[u.side].bonds:
            ast=b["_ast"]
            if u.id not in ast["members"]:continue
            if ast["kind"]=="water_first" and self.terrain=="水战" and self.round==1:bonus+=ast["values"][0]
            if ast["kind"]=="second_pair" and any(v.id in ast["members"] and v.id!=u.id and getattr(v,"acted_round",0)==self.round for v in self.teams[u.side].actors):bonus+=ast["values"][1]
        taken=d["taken"]
        if target.hero["troop"]=="步" and target.slot<2:taken-=.1
        if target.hero["troop"]=="火" and target.slot>=2:taken-=.1
        if u.hero["troop"]=="火":taken-=feature(target,"firearm_reduction")/100
        if self.terrain=="水战":taken+=feature(target,"set_water_taken")
        if active and meta:
            if meta.get("first_round_bonus",(None,))[0]==self.round:bonus+=meta["first_round_bonus"][1]
            if meta.get("target_double_name")==target.hero["name"]:coefficient*=2
            if meta.get("target_bonus"):
                name,val=meta["target_bonus"]
                if name=="太平天国武将" and target.faction=="taiping":bonus+=val
            if self.terrain=="攻城":bonus+=meta.get("siege_bonus",0)
        crit=a["crit"]
        if feature(u,"target_low_crit") and target.hp/target.max_hp<feature(u,"target_low_crit")/100:crit+=feature(u,"target_low_crit",1)/100
        crit_mult=max(1,a["crit_damage"]-feature(target,"critical_reduction")/100) if self.rng.random()<min(1,crit) else 1.
        # Same category adds; final combined additive multiplier floors at0.4.
        value=max(1,int(coefficient*attack*attack/(attack+defense)*mult*max(.4,1+bonus+taken)*crit_mult))
        original=value
        value=self.absorb_shields(target,value)
        killed=self.apply_loss(target,value,u) if value else False
        # Hit-based rage/stacking includes shield-absorbed hits, but not empty AoE targets.
        target.hits+=1
        if target.alive:self.rage(target,10)
        self.invalidate();self.log("damage",source=u.id,target=target.id,amount=original,hp_loss=value,active=active,source_side=u.side,source_slot=u.slot,target_side=target.side,target_slot=target.slot)
        return killed

    def absorb_shields(self,target,value):
        for shield in sorted(target.shields,key=lambda x:x[1]):
            if shield[1]<self.round:continue
            consumed=min(value,shield[0]);shield[0]-=consumed;value-=consumed
            if not value:break
        target.shields=[x for x in target.shields if x[0]>0 and x[1]>=self.round]
        return value

    def basic(self,u,allow_proc=True):
        targets=self.normal_target(u)
        if not targets:return
        u.basics+=1
        self.damage(u,targets[0],1.,basic=True)
        self.rage(u,25+max(0,self.stats(u)["speed"]-80)*.5)
        if allow_proc and u.alive:
            if self.rng.random()<feature(u,"combo_chance")/100:self.basic(u,False)
            if feature(u,"set_extra_hit") and self.rng.random()<feature(u,"set_extra_hit"):
                next_targets=self.normal_target(u)
                if next_targets:self.damage(u,next_targets[0],feature(u,"set_extra_hit",1))

    def execute(self,u,ast,source_name,active=True):
        hits=[];killed=[]
        for op in ast["ops"]:
            if not u.alive:break
            if op.get("condition") and self.terrain!=op["condition"]:continue
            scope=op["target"]
            if op["kind"]=="damage" and self.terrain=="水战":scope=ast["meta"].get("water_target",scope)
            targets=self.targets(u,scope,hits)
            if op["kind"]=="damage":
                hits=targets[:]
                for target in targets:
                    if self.damage(u,target,op["value"],active=active,meta=ast["meta"]):killed.append(target)
                continue
            if op["kind"]=="combo":
                for _ in range(op["value"]):
                    if u.alive:self.basic(u,False)
                continue
            if op["kind"]=="resource" and op["resource"]!="怒气":
                # A monarch decree has no equipment/source features of its
                # temporary target-selection proxy.
                self.resource(u.side,op["resource"],op["value"],None if source_name.startswith("monarch:") else u);continue
            for target in targets:
                if self.rng.random()>op.get("probability",1):continue
                if op["kind"]=="heal":self.heal(target,op["value"],u)
                elif op["kind"]=="shield":
                    expires=self.round+op["duration"]-1
                    # Same source shields refresh strongest, different sources coexist.
                    old=next((s for s in target.shields if s[2]==source_name),None)
                    if old:old[0]=max(old[0],target.max_hp*op["value"]);old[1]=max(old[1],expires)
                    else:target.shields.append([target.max_hp*op["value"],expires,source_name])
                elif op["kind"]=="buff":self.buff(target,source_name,op["stat"],op["value"],op["flat"],op["duration"] or 999)
                elif op["kind"]=="status":
                    if op["status"] in {"眩晕","沉默"} and target.immune_until>=self.round:continue
                    target.control[op["status"]]=max(target.control.get(op["status"],0),op["duration"])
                elif op["kind"]=="burn":
                    snap=self.stats(u)["atk"]*op["value"];expires=self.round+op["duration"]-1
                    target.burns=[b for b in target.burns if b[2].id!=u.id]+[[snap,expires,u]]
                elif op["kind"]=="resource":self.rage(target,op["value"])
                elif op["kind"]=="dispel":
                    negatives=[b for b in target.buffs if b.value<0]
                    for b in negatives[:op["value"]]:target.buffs.remove(b)
                    left=op["value"]-min(op["value"],len(negatives))
                    for status in ["眩晕","沉默"]:
                        if left and status in target.control:target.control.pop(status);left-=1
                    if left:target.burns=target.burns[min(left,len(target.burns)):]
            self.invalidate()
        if killed:
            if ast["meta"].get("kill_rage"):self.rage(u,ast["meta"]["kill_rage"])
            if ast["meta"].get("kill_followup"):
                pool=[v for v in self.teams[1-u.side].living() if v.slot>=2 and v not in hits]
                if pool:self.damage(u,self.rng.choice(pool),ast["meta"]["kill_followup"],active=active)
            if u.feature.get("kill_recast") and u.id not in self.recast_used:
                self.recast_used.add(u.id);self.execute(u,ast,source_name,active)

    def step_start(self):
        self.invalidate()
        for side,team in enumerate(self.teams):
            if team.heaven_until and self.round>team.heaven_until:team.heaven_until=0;team.faith=50
            self.sync_max_hp(side)
            for u in team.living():
                if feature(u,'set_start_heal'):self.heal(u,feature(u,'set_start_heal'),u)
                if feature(u,'set_periodic_heal') and self.round%int(feature(u,'set_periodic_heal'))==0:
                    self.heal(u,feature(u,'set_periodic_heal',1),u)
            if "qing" in team.enabled:self.resource(side,"粮饷",10)
            ids=self._members(team)
            # Hong's+5 comes only from his policy, never duplicated by the bond text.
            rate=0
            if team.lord and any(u.id=="tp_yang_xiuqing" for u in team.living()):
                rate+=team.lord["passive"]["features"].get("yang_round_suspicion",[0])[0]*self.policy_factor(team)
            for b in team.bonds:
                if b["_ast"]["kind"]=="suspicion":rate+=b["_ast"]["rate"]
            if rate:self.resource(side,"猜忌",rate)
            if team.lord and not team.triggered_edict and team.lord["active"]["round"]==self.round:
                team.triggered_edict=True
                # Off-field monarch borrows a living source only for target selection;
                # damage is absent in all current decrees, actor identity is not altered.
                if team.living():
                    self.log("cast",id=team.lord["hero"]["id"],side=side,slot=-1,skill=team.lord["hero"]["active"])
                    self.execute(team.living()[0],team.lord["active"],"monarch:"+team.lord["hero"]["id"],False)

    def step_end(self):
        for team in self.teams:
            for u in list(team.living()):
                for amount,expires,owner in list(u.burns):
                    if expires>=self.round and u.alive:
                        taken=self.stats(u)["taken"]
                        if u.hero["troop"]=="步" and u.slot<2:taken-=.1
                        if u.hero["troop"]=="火" and u.slot>=2:taken-=.1
                        if self.terrain=="水战":taken+=feature(u,"set_water_taken")
                        value=self.absorb_shields(u,max(1,int(amount*max(.4,1+taken))))
                        if value:self.apply_loss(u,value,owner)
                        if u.alive:self.rage(u,10)
                u.burns=[b for b in u.burns if b[1]>self.round]
                if u.alive and feature(u,"end_heal"):self.heal(u,feature(u,"end_heal")/100,u)
                if u.alive and feature(u,'end_heal_below') and u.hp/u.max_hp<feature(u,'end_heal_below')/100:
                    self.heal(u,feature(u,'end_heal_below',1)/100,u)
                u.buffs=[b for b in u.buffs if b.expires>self.round]
                u.shields=[s for s in u.shields if s[1]>self.round]
        self.invalidate()

    def run(self):
        for self.round in range(1,self.limit+1):
            self.step_start()
            self.record_state()
            queue=sorted([u for t in self.teams for u in t.living()],key=lambda u:(-self.stats(u)["speed"],u.side,u.slot))
            for u in queue:
                if not u.alive:continue
                skip=False
                if u.control.get("眩晕",0)>0:skip=True
                for b in self.teams[u.side].bonds:
                    a=b["_ast"]
                    if a["kind"]=="refuse" and u.id=="qing_gordon" and self.round>=a["start_round"]:
                        chance=a["values"][0]+(a["values"][1] if "qing_cheng_xueqi" in self._members(self.teams[u.side]) else 0)
                        if self.rng.random()<chance:skip=True
                if not skip:
                    if u.rage>=100 and not u.control.get("沉默",0) and u.hero.get("tags")!="杂兵":
                        u.rage=0;u.casts+=1
                        ast=self.data.cache[u.hero['active']] if feature(u,'first_enhancement_only') and u.casts>1 else u.active
                        self.log("cast",id=u.id,side=u.side,slot=u.slot,skill=u.hero["active"])
                        self.execute(u,ast,u.hero["active"])
                        if "taiping" in self.teams[u.side].enabled:self.resource(u.side,"信仰",5,u)
                        if u.casts==1:self.rage(u,feature(u,"first_refund"))
                    else:self.basic(u)
                    u.actions+=1;u.acted_round=self.round
                    if feature(u,"action_speed"):
                        u.bonus_speed=min(feature(u,"action_speed",1),u.bonus_speed+feature(u,"action_speed"))
                for key in list(u.control):
                    u.control[key]-=1
                    if u.control[key]<=0:del u.control[key]
                self.invalidate()
                self.record_state()
                if not self.teams[0].living() or not self.teams[1].living():return self.result(False)
            self.step_end()
            self.record_state()
            if not self.teams[0].living() or not self.teams[1].living():return self.result(False)
        return self.result(True)

    def result(self,timeout):
        winner=0 if self.teams[0].living() and not self.teams[1].living() else 1
        return {"winner":winner,"rounds":self.round,"timeout":timeout,
                "incidents":[t.incident_round for t in self.teams],
                "survivors":[[u.id for u in t.living()] for t in self.teams],"trace":self.trace}


def wilson(wins,total,z=1.96):
    if not total:return [None,None]
    p=wins/total;den=1+z*z/total
    center=(p+z*z/(2*total))/den
    radius=z*math.sqrt(p*(1-p)/total+z*z/(4*total*total))/den
    return [max(0,center-radius),min(1,center+radius)]


def rate(values):
    wins=sum(values);n=len(values)
    pairs=[statistics.mean(values[i:i+2]) for i in range(0,n,2)]
    margin=1.96*statistics.stdev(pairs)/math.sqrt(len(pairs)) if len(pairs)>1 else 0
    return {"wins":wins,"n":n,"rate":wins/n if n else None,"wilson95":wilson(wins,n),
            "paired_normal95":[max(0,wins/n-margin),min(1,wins/n+margin)] if n else [None,None]}


def pools(data,faction=None,rarity=None,lords=False):
    return [h["id"] for h in data.heroes.values() if (h["position"]=="君主")==lords
            and (not faction or h["faction"] in {faction,"dual"}) and (not rarity or h["rarity"]==rarity)]


def sample_lord(data,rng,faction):
    return rng.choice(pools(data,faction,lords=True))


def top_weights(rows,fraction=.1):
    """Split the cutoff tie, avoiding arbitrary hero-id or random tie advantages."""
    take=max(1,math.ceil(len(rows)*fraction));ordered=sorted(rows,key=lambda r:-r['rate'])
    cutoff=ordered[take-1]['rate'];above=sum(r['rate']>cutoff for r in rows);tied=sum(r['rate']==cutoff for r in rows)
    return take,[(r,1. if r['rate']>cutoff else (take-above)/tied) for r in ordered if r['rate']>=cutoff]


def evaluate(data,n=1000,lineups=200,opponents=4,seed=20261027,stars=3,gear_set=None,use_exclusives=False,
             level=50,quality="精",enhance=0,equipment_ids=None):
    """Paired attack/defence fixtures. No duplicate heroes inside a team.

    n means *paired fixtures* per scenario; every fixture plays two games.
    Every faction-rarity fixture is a formal5v5; insufficient pools fail loudly.
    """
    if n<1 or lineups<2 or opponents<1:raise ValueError("n>=1, lineups>=2, opponents>=1")
    rng=Mulberry32(seed);terrains=["陆战","水战","攻城","守城"]
    logs=[];counts=Counter();total_games=0
    def fixture(left,right,assigned=("taiping","qing"),lords=(None,None),terrain="陆战",limit=20):
        nonlocal total_games
        game_seed=rng.randrange(2**31)
        out=[]
        for flip in [False,True]:
            rosters=(right,left) if flip else (left,right)
            fac=tuple(reversed(assigned)) if flip else assigned
            kings=tuple(reversed(lords)) if flip else lords
            # Swap siege/defence terrain so the same logical team retains its role.
            ground={"攻城":"守城","守城":"攻城"}.get(terrain,terrain) if flip else terrain
            battle=Battle(data,rosters,kings,fac,ground,stars=stars,seed=game_seed,level=level,quality=quality,enhance=enhance,
                          gear_set=gear_set,use_exclusives=use_exclusives,limit=limit,equipment_ids=equipment_ids)
            result=battle.run();logical=1-result["winner"] if flip else result["winner"]
            incident=result["incidents"][1 if flip else 0]
            out.append((logical,result["rounds"],result["timeout"],incident))
            total_games+=1
        return out
    duel=[];duel_timeout=[]
    ssr,sr=pools(data,rarity="SSR"),pools(data,rarity="SR")
    for _ in range(n):
        left,right=rng.choice(ssr),rng.choice(sr)
        assigned=(data.heroes[left]["faction"],data.heroes[right]["faction"])
        assigned=tuple("qing" if f=="dual" else f for f in assigned)
        for win,rounds,timeout,_ in fixture([left],[right],assigned):
            duel.append(int(win==0));duel_timeout.append(timeout)
    team=[];durations=[];team_timeouts=[]
    for _ in range(n):
        for win,rounds,timeout,_ in fixture(rng.sample(ssr,5),rng.sample(sr,5)):
            team.append(int(win==0));durations.append(rounds);team_timeouts.append(timeout)
    faction={};full_rounds=list(durations);all_timeouts=list(team_timeouts)
    for rarity in ["R","SR","SSR"]:
        a,b=pools(data,"taiping",rarity),pools(data,"qing",rarity)
        if min(len(a),len(b))<5:raise ValueError(f'Formal5v5 unavailable: {rarity} pool sizes {len(a)}/{len(b)}')
        size=5;wins=[];round_values=[];timeouts=[]
        for _ in range(n):
            lords=(sample_lord(data,rng,"taiping"),sample_lord(data,rng,"qing"))
            for win,rounds,timeout,_ in fixture(rng.sample(a,size),rng.sample(b,size),lords=lords,terrain=rng.choice(terrains)):
                wins.append(int(win==0));round_values.append(rounds);timeouts.append(timeout)
        faction[rarity]={**rate(wins),"team_size":size,"average_rounds":statistics.mean(round_values),"timeout_rate":statistics.mean(timeouts)}
        if size==5:full_rounds+=round_values;all_timeouts+=timeouts
    incident={}
    for include_wei in [False,True]:
        values=[];last_rounds=[]
        for _ in range(n):
            left=["tp_yang_xiuqing"]+(["tp_wei_changhui"] if include_wei else [])
            available=[h for h in pools(data,"taiping","SR") if h!="tp_wei_changhui"]
            left+=rng.sample(available,5-len(left));rng.shuffle(left)
            right=rng.sample(pools(data,"qing","SSR"),1)+rng.sample(pools(data,"qing","SR"),4);rng.shuffle(right)
            lords=("tp_hong_xiuquan",sample_lord(data,rng,"qing"))
            for win,rounds,timeout,event in fixture(left,right,lords=lords,terrain=rng.choice(terrains),limit=12):
                values.append(int(event is not None and event<=12));last_rounds.append(rounds)
        incident["with_wei" if include_wei else "without_wei"]={**rate(values),"average_observed_rounds":statistics.mean(last_rounds)}
    # Each distinct lineup plays the same number of paired fixtures. Ranking is
    # by empirical lineup win rate, NOT appearances among single-game winners.
    lineup_rows=[];seen=set()
    for i in range(lineups):
        faction_name="taiping" if i%2==0 else "qing"
        while True:
            ids=rng.sample(pools(data,faction_name),5);lord=sample_lord(data,rng,faction_name)
            signature=(tuple(ids),lord,faction_name)
            if signature not in seen:seen.add(signature);break
        lineup_rows.append({"id":i,"heroes":ids,"lord":lord,"faction":faction_name,"wins":0,"games":0})
    for row in lineup_rows:
        for _ in range(opponents):
            other=rng.choice([r for r in lineup_rows if r["id"]!=row["id"]])
            for win,rounds,timeout,_ in fixture(row["heroes"],other["heroes"],
                assigned=(row["faction"],other["faction"]),lords=(row["lord"],other["lord"]),terrain=rng.choice(terrains)):
                row["wins"]+=int(win==0);row["games"]+=1
                full_rounds.append(rounds);all_timeouts.append(timeout)
        row["rate"]=row["wins"]/row["games"]
    top_n=max(1,math.ceil(len(lineup_rows)*.1))
    # Ties are broken using a pre-generated seeded random key, never hero id.
    for row in lineup_rows:row["tie_key"]=rng.random()
    ranked=sorted(lineup_rows,key=lambda r:(-r["rate"],r["tie_key"]))
    top_n,weighted=top_weights(ranked);appearances=Counter()
    for r,weight in weighted:
        for h in r['heroes']:appearances[h]+=weight
    peak=max(appearances.values(),default=0)/top_n
    monarchs={}
    for camp in ['taiping','qing']:
        own=[r for r in ranked if r['faction']==camp];take,chosen=top_weights(own)
        counts=Counter()
        for r,weight in chosen:counts[r['lord']]+=weight
        available=pools(data,camp,lords=True)
        monarchs[camp]={'sampled_lineups':len(own),'top_count':take,'denominator':'Top10% lineups within this faction; not the uniform input-sampling frequency',
            'cards':{h:{'count':counts[h],'rate':counts[h]/take} for h in available}}
    return {"seed":seed,"level":level,"stars":stars,"equipment_set":gear_set,"equipment_ids":equipment_ids,"quality":quality,"enhance":enhance,"exclusives":use_exclusives,
        "parameters":{"paired_fixtures_per_scenario":n,"lineups":lineups,"opponents":opponents},
        "input_sha256":{name:hashlib.sha256((data.directory/name).read_bytes()).hexdigest() for name in ["heroes.csv","skills.csv","bonds.csv","equipment.csv","equipment_sets.csv","exclusive_equipment.csv"]},
        "simulator_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "total_games":total_games,"duel":{**rate(duel),"timeout_rate":statistics.mean(duel_timeout)},
        "ssr5_vs_sr5":{**rate(team),"average_rounds":statistics.mean(durations),"timeout_rate":statistics.mean(team_timeouts)},
        "factions":faction,"faction_equal_weight_rate":statistics.mean(x["rate"] for x in faction.values()),
        "average_full_team_rounds":statistics.mean(full_rounds),"full_team_timeout_rate":statistics.mean(all_timeouts),
        "incident":incident,"top_lineups":{"sampled":lineups,"games_each":opponents*2,"top_count":top_n,
        "max_appearance":peak,"appearances":dict(appearances),"rows":ranked},
        "monarchs":monarchs,
        "assumptions":{"duel_and_rarity_teams":"no monarch, samelevel/stars; rarity-team factions assigned independently from natural factions",
        "faction_fixtures":"same combat rarity, compatible monarch sampled uniformly,4terrains equally likely",
        "ssr_pure_team_limit":"Formal5v5; each side has6 combatSSR candidates; no monarch substitutes",
        "incident_denominator":"all fixtures; early battle end counts as no trigger, not forcibly extended"}}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir",type=Path,default=ROOT/"data")
    parser.add_argument("--output",type=Path,default=ROOT/"assets/reports/balance_v2/evaluation.json")
    parser.add_argument("--n",type=int,default=1000,help="paired fixtures per scenario")
    parser.add_argument("--lineups",type=int,default=200)
    parser.add_argument("--opponents",type=int,default=4)
    parser.add_argument("--seed",type=int,default=20261027)
    parser.add_argument("--stars",type=int,default=3)
    parser.add_argument("--level",type=int,default=50)
    parser.add_argument("--quality",choices=["粗","制","精","珍","绝"],default="精")
    parser.add_argument("--enhance",type=int,default=0)
    parser.add_argument("--gear-set",choices=["圣兵","勇营","洋械","铁骑","江防"])
    parser.add_argument("--equipment-ids",nargs="+",help="up to4 distinct slots, including mixed2-piece sets")
    parser.add_argument("--exclusives",action="store_true")
    parser.add_argument("--audit-only",action="store_true")
    parser.add_argument("--compare-before",type=Path,help="baseline evaluation JSON using the same frozen engine/seed")
    parser.add_argument("--report",type=Path,default=ROOT/"assets/reports/balance_report_v2.md")
    parser.add_argument("--no-report",action="store_true")
    args=parser.parse_args();data=Data(args.data_dir)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    if args.audit_only:
        audit=list(data.audit)
        for h in data.heroes.values():
            if h["id"] in data.exclusives:
                *_,unknown=exclusive_skills(data,h,True)
                if unknown:audit.append({"table":"exclusive_equipment.csv","id":h["id"],"unparsed":unknown})
        payload={"heroes":len(data.heroes),"skills":len(data.skills),"bonds":len(data.bonds),
                 "equipment":len(data.equipment),"sets":len(data.sets),"exclusives":len(data.exclusives),
                 "unparsed":audit,"budget":data.budget()}
    else:payload=evaluate(data,args.n,args.lineups,args.opponents,args.seed,args.stars,args.gear_set,args.exclusives,args.level,args.quality,args.enhance,args.equipment_ids)
    args.output.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n")
    if not args.audit_only and not args.no_report:
        from battle_report_v2 import write_report
        before=json.loads(args.compare_before.read_text()) if args.compare_before else None
        write_report(before,payload,args.report,data)
    print(json.dumps({k:v for k,v in payload.items() if k not in {"top_lineups","budget","assumptions"}},ensure_ascii=False))
    return int(bool(payload.get("unparsed")))


if __name__=="__main__":
    import sys,os
    if '--economy' in sys.argv:
        os.execv(sys.executable,[sys.executable,str(ROOT/'tools/economy_sim.py'),*[x for x in sys.argv[1:] if x!='--economy']])
    raise SystemExit(main())
