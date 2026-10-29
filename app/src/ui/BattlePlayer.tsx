import { useEffect,useRef,useState } from 'react';
import type { SceneController } from '../scene/BattleScene';
import type { BattleLog,TeamInput,BattleEvent,Terrain } from '../core/battle/types';
import { database } from '../core/data';
import { lifecycle } from '../platform/storage';
export interface FrameMetrics {frames:number;fps:number;p95_ms:number;worst_ms:number;over25ms:number;over50ms:number;outliers:{frame:number;ms:number}[]}
export function BattlePlayer({log,teams,terrain,onFinish}:{log:BattleLog;teams:[TeamInput,TeamInput];terrain:Terrain;onFinish:(metrics:FrameMetrics)=>void}){
 const host=useRef<HTMLDivElement>(null),scene=useRef<SceneController|null>(null),index=useRef(0),done=useRef(false);
 const [ready,setReady]=useState(false),[error,setError]=useState(''),[speed,setSpeed]=useState(1),[playing,setPlaying]=useState(true),[round,setRound]=useState(0),[skill,setSkill]=useState('');
 const [resource,setResource]=useState({faith:50,suspicion:0,grain:0});
 const frameSamples=useRef<number[]>([]);
 const finish=()=>{if(done.current)return;done.current=true;performance.mark('m1-playback-end');const a=frameSamples.current,sorted=[...a].sort((x,y)=>x-y);onFinish({frames:a.length,fps:a.length?1000/(a.reduce((s,v)=>s+v,0)/a.length):0,p95_ms:sorted[Math.floor(sorted.length*.95)]??0,worst_ms:sorted.at(-1)??0,over25ms:a.filter(x=>x>25).length,over50ms:a.filter(x=>x>50).length,outliers:a.flatMap((ms,frame)=>ms>25?[{frame,ms}]:[]).slice(0,50)});};
 useEffect(()=>{let disposed=false;void import('../scene/BattleScene').then(({createBattleScene})=>createBattleScene(host.current!,teams,terrain)).then(s=>{if(disposed){s.destroy();return;}scene.current=s;setReady(true);}).catch(e=>{if(!disposed)setError(String(e));});return()=>{disposed=true;scene.current?.destroy();scene.current=null;};},[teams,terrain]);
 useEffect(()=>lifecycle(()=>setPlaying(false)),[]);
 useEffect(()=>{if(!ready||!playing)return;performance.mark('m1-playback-start');let last=0,elapsed=0,id=0,frames=0;const samples=frameSamples.current;
  const apply=(e:BattleEvent)=>{scene.current?.apply(e);setRound(e.round);if(e.event==='state'&&e.teams){const t=e.teams[0];setResource({faith:t.faith,suspicion:t.suspicion,grain:t.grain});}if(e.event==='cast')setSkill(database.skills.find(x=>x.skill_id===e.skill)?.name??'军令');else if(e.event==='state')setSkill('');};
  const tick=(now:number)=>{if(last){const dt=now-last;elapsed+=dt;samples.push(dt);}last=now;frames++;
    if(host.current&&frames%60===0){host.current.dataset.frameCount=String(samples.length);host.current.dataset.frameTimes=JSON.stringify(samples.slice(-1200));}
    while(elapsed>=145/speed&&index.current<log.trace.length){elapsed-=145/speed;apply(log.trace[index.current++]);}
    if(index.current>=log.trace.length){finish();return;}id=requestAnimationFrame(tick);};id=requestAnimationFrame(tick);return()=>cancelAnimationFrame(id);
 },[ready,playing,speed,log]);
 return <><div className="battle-status"><span>第 <b>{round}</b> 回</span><span>{teams[0].faction==='taiping'?`信仰 ${Math.round(resource.faith)} · 猜忌 ${Math.round(resource.suspicion)}`:`粮饷 ${Math.round(resource.grain)}`}</span></div><div className="battle-scene" ref={host} data-testid="battle-scene" aria-busy={!ready}>{!ready&&!error&&<p className="scene-message">整军列阵…</p>}{error&&<p className="scene-message" role="alert">画面载入失败，请返回编队重试。<small>{error}</small></p>}{skill&&<div className="skill-banner">{skill}</div>}<span className="field-label enemy-label">敌 军</span><span className="field-label ally-label">我 军</span></div><footer className="battle-controls"><button className="ghost dark" onClick={()=>setPlaying(!playing)}>{playing?'暂停':'继续'}</button><div className="speed-controls">{[1,2,4].map(n=><button key={n} aria-pressed={speed===n} className={speed===n?'on':''} onClick={()=>setSpeed(n)}>{n}×</button>)}</div><button onClick={finish} className="primary" disabled={!ready}>跳过</button></footer><p className="battle-hint">自动交锋 · 军报已成，静观战局</p></>;
}
