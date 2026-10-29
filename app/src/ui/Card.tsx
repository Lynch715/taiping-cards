import { assetUrl } from '../platform/assets';
import { database } from '../core/data';
import { initialStars } from '../core/campaign';
export function Card({id,selected=false,onClick,small=false,label,level=10,stars}:{id:string;selected?:boolean;onClick?:()=>void;small?:boolean;label?:string;level?:number;stars?:number}){
 const h=database.heroes.find(x=>x.id===id)!;const art=assetUrl(`assets/characters/${id}/${small?'mini':'card'}.webp`);
 const body=<><div className="card-art"><img src={art} alt={h.name} draggable={false} onError={e=>{if(!e.currentTarget.src.endsWith("portrait-unavailable.svg"))e.currentTarget.src=assetUrl("assets/ui/portrait-unavailable.svg");}}/><span className={`faction-badge ${h.faction==='taiping'?'tp':h.faction==='dual'?'dual':'qing'}`}>{h.faction==='taiping'?'太平':h.faction==='dual'?'双':'清'}</span><b className="rarity-seal">{{SSR:'绝',SR:'精',R:'凡'}[h.rarity]}</b><span className="troop-badge">{h.troop==='-'?'君':h.troop}</span><span className="stars">{'★'.repeat((stars??initialStars(h.rarity)))}<i>{'☆'.repeat(6-(stars??initialStars(h.rarity)))}</i></span>{selected&&<span className="chosen-seal">列</span>}</div><div className="card-name"><strong>{h.name}</strong><small>{label??`Lv.${level}`}</small></div></>;
 return onClick?<button className={`hero-card ${h.rarity.toLowerCase()} ${selected?'selected':''} ${small?'small':''}`} aria-label={`${h.name}${selected?'，已上阵':''}`} onClick={onClick} aria-pressed={selected}>{body}</button>:<div className={`hero-card ${h.rarity.toLowerCase()} ${small?'small':''}`}>{body}</div>;
}
