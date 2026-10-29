import { useState } from 'react';
import { assetUrl } from '../platform/assets';
export function DetailPortrait({id,name}:{id:string;name:string}){const [fallback,setFallback]=useState(0);return <><div className="detail-portrait"><img src={assetUrl(fallback===2?'assets/ui/portrait-unavailable.svg':`assets/characters/${id}/${fallback?'card':'full'}.webp`)} alt={name} onError={()=>setFallback(v=>Math.min(2,v+1))}/><h2>{name}</h2></div>{fallback>0&&<p className="detail-fallback" role="status">{fallback===1?'大图暂不可用，显示卡牌预览':'画像尚未缓存，暂用剪影；联网后可恢复'}</p>}</>;}
