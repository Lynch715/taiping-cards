import {useEffect,useState,useSyncExternalStore} from 'react';
import {assetUrl} from '../platform/assets';
import {equipmentArt,equipmentAtlas,equipmentSpriteStyle} from '../platform/equipment-art';
import {pwaSnapshot,pwaSubscribe} from '../platform/pwa';
import {database} from '../core/data';
import type {Equipment} from '../core/data/types';
import type {GearItem} from '../core/progression';

export function EquipmentIcon({set,slot,name,size=64}:{set:string;slot:string;name:string;size?:64|128}){
 const art=equipmentArt(set,slot),pwa=useSyncExternalStore(pwaSubscribe,pwaSnapshot),[failed,setFailed]=useState(false);
 useEffect(()=>setFailed(false),[art?.id,pwa.online]);
 if(!art)return <span className="equipment-icon-empty" aria-label={slot}>{slot}</span>;
 const high=size===128&&pwa.online&&!failed;
 return <span className="equipment-icon" data-icon-id={art.id} data-icon-resolution={high?128:64} role="img" aria-label={name} style={{...equipmentSpriteStyle(art,size),backgroundImage:`url("${assetUrl(equipmentAtlas.sprite)}")`}}>
  {high&&<img src={assetUrl(`assets/equipment/128/${art.id}.webp`)} width={128} height={128} alt="" onError={()=>setFailed(true)}/>}
 </span>;
}
export function EquipmentDetails({row,enhance=0,onClose}:{row:Equipment;enhance?:number;onClose:()=>void}){
 useEffect(()=>{const escape=(event:KeyboardEvent)=>{if(event.key==='Escape')onClose();};document.addEventListener('keydown',escape);return()=>document.removeEventListener('keydown',escape);},[onClose]);
 const set=database.equipment_sets.find(x=>x.set===row.set);
 return <div className="modal-backdrop" role="presentation" onClick={onClose}><section className={'equipment-detail quality-'+row.quality} role="dialog" aria-modal="true" aria-label={row.name+'详情'} onClick={e=>e.stopPropagation()}>
  <button className="modal-close" aria-label="关闭兵装详情" onClick={onClose}>×</button><div className="equipment-detail-art"><EquipmentIcon set={row.set} slot={row.slot} name={row.name} size={128}/></div>
  <h2>{row.name}</h2><p>{row.quality} · {row.slot} · {row.set} · +{enhance}</p>
  <p>{row.main_stat} +{(row.main_value*(1+.1*enhance)).toFixed(1)}<br/>{row.sub_stat} +{(row.sub_value*(1+.1*enhance)).toFixed(1)}</p>
  {set&&<p className="equipment-set-description">两件：{set.bonus2}<br/>四件：{set.bonus4}</p>}<button className="primary" onClick={onClose}>阅毕</button>
 </section></div>;
}
export function EquipmentRewards({items}:{items:GearItem[]}){
 const [selected,setSelected]=useState<GearItem|null>(null);
 if(!items.length)return null;
 const detail=selected&&database.equipment.find(r=>r.equip_id===selected.equipmentId);
 return <section className="equipment-rewards" aria-label="获得兵装"><h3>兵装入库</h3><div>{items.map(item=>{const row=database.equipment.find(r=>r.equip_id===item.equipmentId)!;return <button key={item.uid} className={'equipment-reward quality-'+row.quality} onClick={()=>setSelected(item)} aria-label={'查看'+row.name+'详情'}><EquipmentIcon set={row.set} slot={row.slot} name={row.name}/><span>{row.name}<small>{row.quality}</small></span></button>;})}</div>{detail&&selected&&<EquipmentDetails row={detail} enhance={selected.enhance} onClose={()=>setSelected(null)}/>}</section>;
}
