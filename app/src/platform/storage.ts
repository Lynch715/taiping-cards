import { migrateGrowth } from '../core/progression';
import { validSave } from '../core/campaign';
import type { Save } from '../core/campaign';
const qa=new URLSearchParams(location.search).get('qa');
const key=qa?'m1-qa-'+qa.replace(/[^a-zA-Z0-9_-]/g,'')+'-v1':'m1-save-v1';
function db():Promise<IDBDatabase>{return new Promise((resolve,reject)=>{const r=indexedDB.open('taiping-m1',1);r.onupgradeneeded=()=>{if(!r.result.objectStoreNames.contains('slots'))r.result.createObjectStore('slots');};r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);r.onblocked=()=>reject(Error('请关闭其他旧版页面后重试'));});}
async function get(k:string){const d=await db();return new Promise<string|null>((res,rej)=>{const r=d.transaction('slots').objectStore('slots').get(k);r.onsuccess=()=>{res(r.result??null);d.close();};r.onerror=()=>{rej(r.error);d.close();};});}
function decode(raw:string|null):Save|null{try{const value:unknown=raw===null?null:JSON.parse(raw);return validSave(value)?value:null;}catch{return null;}}
export async function loadSave():Promise<{save:Save|null;recovered:boolean}>{const raw=await get(key);if(raw===null)return {save:null,recovered:false};const current=decode(raw);if(current)return {save:migrateGrowth(current,Date.now()),recovered:false};const backup=decode(await get(key+'-backup'));if(backup)return {save:migrateGrowth(backup,Date.now()),recovered:true};throw Error('军册损坏，已保留原记录。可导入备份恢复。');}
let queue:Promise<void>=Promise.resolve();
export function saveGame(save:Save):Promise<void>{
 if(!validSave(save))return Promise.reject(Error('军册校验失败，未写入'));
 const serialized=JSON.stringify(save);
 queue=queue.catch(()=>{}).then(async()=>{const d=await db();return new Promise<void>((resolve,reject)=>{const t=d.transaction('slots','readwrite'),store=t.objectStore('slots'),r=store.get(key);r.onsuccess=()=>{const previous=r.result as string|undefined;if(previous===serialized)return;if(previous&&decode(previous))store.put(previous,key+'-backup');store.put(serialized,key);};t.oncomplete=()=>{d.close();resolve();};t.onabort=t.onerror=()=>{d.close();reject(t.error??Error('军册保存失败'));};});});
 return queue;
}
export async function flushSaves(){await queue;}
export function lifecycle(onPause:()=>void){const pause=()=>{if(document.visibilityState==='hidden')onPause();};document.addEventListener('visibilitychange',pause);window.addEventListener('pagehide',onPause);return ()=>{document.removeEventListener('visibilitychange',pause);window.removeEventListener('pagehide',onPause);};}

/** Keep the previous campaign separate from the rotating autosave backup. */
export function startNewGame(save:Save):Promise<void>{if(!validSave(save)||save.campaign!==null)return Promise.reject(Error('新军册无效'));const serialized=JSON.stringify(save);queue=queue.catch(()=>{}).then(async()=>{const d=await db();return new Promise<void>((resolve,reject)=>{const t=d.transaction('slots','readwrite'),store=t.objectStore('slots'),r=store.get(key);r.onsuccess=()=>{const previous=r.result as string|undefined;const old=decode(previous??null);if(previous&&old&&(old.campaign||old.progress.taiping.length||old.progress.qing.length)){store.put(previous,key+'-previous-game');store.put(previous,key+'-backup');}store.put(serialized,key);};t.oncomplete=()=>{d.close();resolve();};t.onabort=t.onerror=()=>{d.close();reject(t.error??Error('新局未能保存，原军册仍保留'));};});});return queue;}
export async function previousGame(){return decode(await get(key+'-previous-game'));}
