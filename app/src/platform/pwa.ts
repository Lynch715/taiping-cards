import { assetUrl } from './assets';
import { flushSaves } from './storage';
interface InstallPrompt extends Event {prompt:()=>Promise<void>;userChoice:Promise<{outcome:'accepted'|'dismissed'}>}
interface PwaState {online:boolean;ready:boolean;completed:number;total:number;bytes:number;downloadedBytes:number;version:string;update:boolean;installed:boolean;canInstall:boolean;error:string;chapters:string[];heroes:string[]}
const standalone=()=>matchMedia('(display-mode: standalone)').matches||Boolean((navigator as Navigator&{standalone?:boolean}).standalone);
let state:PwaState={online:navigator.onLine,ready:false,completed:0,total:0,bytes:0,downloadedBytes:0,version:'',update:false,installed:standalone(),canInstall:false,error:'',chapters:[],heroes:[]};
let desiredChapters=['taiping_1','qing_1'];
let clientChaptersKnown=false,desiredHeroes:string[]=[];
let requestedMissing='';
function requestMissing(force=false){
 if(!navigator.serviceWorker?.controller)return;
 const chapters=desiredChapters.filter(k=>!state.chapters.includes(k)),heroes=desiredHeroes.filter(k=>!state.heroes.includes(k)),key=JSON.stringify([chapters,heroes]);
 if(!navigator.onLine||(!force&&key===requestedMissing))return;requestedMissing=key;
 if(chapters.length)navigator.serviceWorker.controller?.postMessage({type:'PWA_CHAPTERS',chapters});
 if(heroes.length)navigator.serviceWorker.controller?.postMessage({type:'PWA_HEROES',heroes});
}
const listeners=new Set<()=>void>();let registration:ServiceWorkerRegistration|undefined,prompt:InstallPrompt|undefined,started=false,reloadRequested=false;
const change=(next:Partial<PwaState>)=>{state={...state,...next};for(const fn of listeners)fn();};
export const pwaSnapshot=()=>state;
export const pwaSubscribe=(fn:()=>void)=>{listeners.add(fn);return ()=>{listeners.delete(fn);};};
export function startPwa(){
 if(started)return;started=true;
 window.addEventListener('online',()=>change({online:true}));window.addEventListener('offline',()=>change({online:false}));
 window.addEventListener('beforeinstallprompt',event=>{event.preventDefault();prompt=event as InstallPrompt;change({canInstall:true});});
 window.addEventListener('appinstalled',()=>{prompt=undefined;change({installed:true,canInstall:false});});
 matchMedia('(display-mode: standalone)').addEventListener('change',()=>change({installed:standalone()}));
 if(!import.meta.env.PROD)return;
 if(!('serviceWorker'in navigator)){change({error:'当前浏览器不支持离线安装'});return;}
 let hadController=Boolean(navigator.serviceWorker.controller);
 navigator.serviceWorker.addEventListener('controllerchange',()=>{
  if(reloadRequested){location.reload();return;}
  if(hadController)change({update:true});hadController=true;
  navigator.serviceWorker.controller?.postMessage({type:'PWA_STATUS'});
 });
 navigator.serviceWorker.addEventListener('message',event=>{
  const m=event.data;if(m?.type==='PWA_READY'){
   const chapters:string[]=m.chapters??['taiping_1','qing_1'],heroes:string[]=m.heroes??[];
   change({ready:desiredChapters.every(k=>chapters.includes(k))&&desiredHeroes.every(k=>heroes.includes(k)),chapters,heroes,completed:m.total,total:m.total,bytes:m.bytes,downloadedBytes:m.downloadedBytes??0,version:m.version,error:''});
   if(!state.ready)requestMissing();
   const expected=document.querySelector<HTMLMetaElement>('meta[name="pwa-build-id"]')?.content;
   if(expected===m.version&&clientChaptersKnown&&state.ready)navigator.serviceWorker.controller?.postMessage({type:'CLIENT_READY',version:m.version});
   else if(expected&&expected!=='__PWA_BUILD_ID__'&&expected!==m.version)change({update:true});
  }
  if(m?.type==='PWA_PROGRESS'&&!state.ready)change({completed:m.completed,total:m.total,error:''});
  if(m?.type==='PWA_ERROR')change({error:state.ready?'新版本准备失败，仍可使用当前版本':'离线包未完成，请联网后重试'});
  if(m?.type==='PWA_CHAPTER_ERROR')change({error:'新章节素材尚未备齐，联网后会继续准备'});
 });
 void navigator.serviceWorker.register(assetUrl('sw.js'),{updateViaCache:'none'}).then(reg=>{
  registration=reg;
  const watch=()=>{const worker=reg.installing;if(worker)worker.addEventListener('statechange',()=>{if(worker.state==='installed'&&reg.waiting&&navigator.serviceWorker.controller)change({update:true});});};
  if(reg.waiting)change({update:true});reg.addEventListener('updatefound',watch);watch();
  (navigator.serviceWorker.controller??reg.active)?.postMessage({type:'PWA_STATUS'});
 }).catch(()=>change({error:'离线包未完成，请联网后重试'}));
 const check=()=>{if(document.visibilityState==='visible'&&navigator.onLine)void checkUpdate().catch(()=>{});};
 window.addEventListener('online',()=>requestMissing(true));
 document.addEventListener('visibilitychange',check);setInterval(check,15*60*1000);
}
export async function checkUpdate(){if(registration)await registration.update();}
export function cacheUnlockedChapters(chapters:string[],heroes:string[]=[]){desiredChapters=[...chapters];desiredHeroes=[...heroes];clientChaptersKnown=true;if(!import.meta.env.PROD)return;change({ready:desiredChapters.every(k=>state.chapters.includes(k))&&desiredHeroes.every(k=>state.heroes.includes(k))});requestMissing();navigator.serviceWorker?.controller?.postMessage({type:'PWA_STATUS'});}
export async function activateUpdate(){await flushSaves();reloadRequested=true;if(registration?.waiting)registration.waiting.postMessage({type:'SKIP_WAITING'});else location.reload();}
export async function installPwa(){if(!prompt)return false;const current=prompt;await current.prompt();const choice=await current.userChoice;prompt=undefined;change({canInstall:false});return choice.outcome==='accepted';}
