import React,{useState} from 'react';
import {createRoot} from 'react-dom/client';
import {database} from '../core/data';
import {newSave} from '../core/campaign';
import {campGrowth} from '../core/progression';
import {startPwa} from '../platform/pwa';
import {EquipmentIcon,EquipmentDetails,EquipmentRewards} from '../ui/EquipmentArt';
import {GrowthPages} from '../ui/GrowthPages';
import '../ui/style.css';

const initial=newSave(1793275200000,1851),growth=campGrowth(initial,'taiping');
growth.gear=database.equipment.map((row,i)=>({uid:'qa-equipment-'+i,equipmentId:row.equip_id,enhance:0,owner:null}));
growth.wallet.silver=1000000;growth.wallet.iron=1000000;
startPwa();
function Review(){
 const [save,setSave]=useState(initial),[view,setView]=useState('sheet'),[id,setId]=useState<string|null>(null),[offline,setOffline]=useState(false),[requests,setRequests]=useState<unknown[]>([]);
 const rows=database.equipment.filter(row=>row.quality==='粗'),row=database.equipment.find(r=>r.equip_id===id);
 return <main className="qa-equipment-review"><h1>C批 · 兵装图标</h1><p>64px实际显示 · 同套同部位共用图标 · 独立UI样本，不读写玩家军册</p><nav><button onClick={()=>setView('sheet')}>20图对照</button><button onClick={()=>setView('inventory')}>军械库</button><button onClick={()=>setView('rewards')}>奖励</button><button aria-pressed={offline} onClick={()=>{const value=!offline;setOffline(value);window.dispatchEvent(new Event(value?'offline':'online'));}}>{offline?'恢复联网显示':'模拟离线显示'}</button></nav>
 {view==='sheet'&&<><div className="qa-icon-sheet">{['圣兵','勇营','洋械','铁骑','江防'].map(set=><section key={set}><h2>{set}</h2>{rows.filter(r=>r.set===set).map(r=><button key={r.equip_id} className={'qa-icon quality-'+r.quality} onClick={()=>setId(r.equip_id)}><EquipmentIcon set={r.set} slot={r.slot} name={r.name}/><span>{r.name}</span><small>{r.slot}</small></button>)}</section>)}</div><p>点击图标查看详情。</p></>}
 {view==='inventory'&&<div className="phone-shell"><GrowthPages page="equipment" save={save} camp="taiping" onSave={setSave}/></div>}
 {view==='rewards'&&<div className="phone-shell qa-rewards"><EquipmentRewards items={growth.gear.filter((_,i)=>i%5===0).slice(0,4)}/></div>}
 <details className="qa-request-log"><summary>图像请求记录（验收用）</summary><button onClick={()=>setRequests(performance.getEntriesByType('resource').filter(e=>e.name.includes('/assets/equipment/')).map(e=>({url:new URL(e.name).pathname,durationMs:Math.round(e.duration),bytes:(e as PerformanceResourceTiming).transferSize,status:(e as PerformanceResourceTiming).responseStatus})))}>刷新图像请求记录</button><pre style={{whiteSpace:'pre-wrap',overflowWrap:'anywhere'}}>{JSON.stringify(requests,null,2)}</pre></details>
 {row&&<EquipmentDetails key={row.equip_id} row={row} onClose={()=>setId(null)}/>}
 </main>;
}
const style=document.createElement('style');style.textContent=`.qa-equipment-review{max-width:1040px;margin:auto;padding:28px 20px}.qa-equipment-review>h1{font-size:28px}.qa-equipment-review>p{font-size:13px;line-height:1.8;margin:12px 0}.qa-equipment-review>nav{display:flex;flex-wrap:wrap;gap:12px;margin:20px 0}.qa-equipment-review>nav button{border:1px solid #9c855f;padding:8px 12px;min-height:40px}.qa-icon-sheet{display:grid;gap:16px}.qa-icon-sheet>section{display:grid;grid-template-columns:100px repeat(4,1fr);align-items:center;gap:14px;border-bottom:1px solid #c4b79c;padding:8px 0 20px}.qa-icon-sheet h2{font-size:18px}.qa-icon{display:grid;justify-items:center;gap:5px;font-size:13px}.qa-icon>.equipment-icon{outline:2px solid var(--gear-frame);outline-offset:2px;background-color:#e6dac0}.qa-icon small{font-size:11px}.qa-rewards{padding:20px;min-height:0}@media(max-width:600px){.qa-icon-sheet>section{grid-template-columns:repeat(4,minmax(64px,1fr));gap:10px}.qa-icon-sheet h2{grid-column:1/-1}.qa-equipment-review{padding:20px 12px}.qa-icon{font-size:11px}}`;document.head.appendChild(style);
const root=createRoot(document.querySelector('#root')!);root.render(<Review/>);
if(import.meta.hot)import.meta.hot.dispose(()=>{root.unmount();style.remove();});
