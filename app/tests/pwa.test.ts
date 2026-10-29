import {describe,it,expect,vi} from 'vitest';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';
import {createHash} from 'node:crypto';
const scope='http://127.0.0.1:5192/taiping/';
const paths=['./index.html','./assets/mini.webp','./assets/characters/reward/card.webp','./assets/characters/reward/full.webp','./assets/equipment/sprite-64.webp','./assets/equipment/128/shengbing_binren.webp','./mobile-checklist-v0.4.4.html'];
const files=paths.map(url=>({url,revision:createHash('sha256').update('data:'+new URL(url,scope).href).digest('hex'),bytes:20}));
function worker(active=false,withEquipment=false){
 const listeners=new Map<string,(e:any)=>unknown>(),data=new Map<string,Map<string,Response>>();let skips=0;const messages:any[]=[],clients=[{id:'tab',url:scope,postMessage:(m:any)=>{messages.push(m);}}];
 const caches={keys:async()=>[...data.keys()],delete:async(n:string)=>data.delete(n),open:async(n:string)=>{if(!data.has(n))data.set(n,new Map());const entries=data.get(n)!;return {match:async(k:string)=>entries.get(k)?.clone(),put:async(k:string,r:Response)=>{entries.set(k,r.clone());}};}};
 const self={registration:{scope,active,installing:null,waiting:null},location:{origin:new URL(scope).origin},clients:{claim:async()=>{},matchAll:async()=>clients},skipWaiting:async()=>{skips++;},addEventListener:(type:string,fn:any)=>listeners.set(type,fn)};
 const network=vi.fn(async(r:Request)=>new Response('data:'+r.url));
 const chapters={taiping_1:{assets:[paths[1]],prerequisites:[]},qing_1:{assets:[paths[1]],prerequisites:[]},taiping_2:{assets:[paths[1],paths[2]],prerequisites:['tp_1_6']}};
 const code=readFileSync('scripts/sw-template.js','utf8').replace('__VERSION__',JSON.stringify('test-v2')).replace('__FILES__',JSON.stringify(files)).replace('__CORE__',JSON.stringify(withEquipment?[paths[0],paths[4],paths[6]]:[paths[0]])).replace('__CHAPTERS__',JSON.stringify(chapters));
 runInNewContext(code,{self,caches,fetch:network,Request,Response,URL,Map,Set,Promise,Error,Uint8Array,crypto,Object,Array});
 async function send(type:string,fields:any={}){let promise:Promise<unknown>|undefined,response:Promise<Response>|undefined;listeners.get(type)!({...fields,waitUntil:(p:Promise<unknown>)=>promise=p,respondWith:(p:Promise<Response>)=>response=p});await promise;return response?await response:undefined;}
 const fetchFile=(url:string)=>send('fetch',{request:new Request(new URL(url,scope))});
 return {send,fetchFile,network,data,messages,clients,self,get skips(){return skips;}};
}
describe('two-layer production service worker',()=>{
 it('opens the precached handset checklist by its own URL offline while the game directory still resolves to index',async()=>{
  const w=worker(false,true);await w.send('install');w.network.mockRejectedValue(Error('offline'));
  const checklist=await w.send('fetch',{request:{url:new URL(paths[6]+'?qa=handset',scope).href,method:'GET',mode:'navigate'}});
  expect(checklist!.status).toBe(200);expect(await checklist!.text()).toContain('mobile-checklist-v0.4.4.html');
  const game=await w.send('fetch',{request:{url:scope+'?qa=handset',method:'GET',mode:'navigate'}});expect(await game!.text()).toContain('index.html');
 });
 it('preloads one equipment atlas, fetches128px only on demand and keeps the atlas usable on an offline detail miss',async()=>{
  const w=worker(false,true);await w.send('install');
  const installed=w.network.mock.calls.map(([r])=>r.url);expect(installed).toContain(new URL(paths[4],scope).href);expect(installed).not.toContain(new URL(paths[5],scope).href);
  w.network.mockRejectedValue(Error('offline'));expect((await w.fetchFile(paths[5]))!.status).toBe(503);expect((await w.fetchFile(paths[4]))!.status).toBe(200);
  const online=worker(false,true);await online.send('install');expect((await online.fetchFile(paths[5]))!.status).toBe(200);online.network.mockRejectedValue(Error('offline'));expect((await online.fetchFile(paths[5]))!.status).toBe(200);
 });
 it('installs only program plus initially unlocked chapter thumbnails, not full images or locked rewards',async()=>{const w=worker();await w.send('install');expect(w.skips).toBe(1);expect(w.network.mock.calls.map(([r])=>r.url)).toEqual([new URL(paths[0],scope).href,new URL(paths[1],scope).href]);expect(w.data.size).toBe(2);w.network.mockRejectedValue(Error('offline'));const page=await w.send('fetch',{request:{url:scope+'?qa=offline',method:'GET',mode:'navigate'}});expect(await page!.text()).toContain('index.html');expect((await w.fetchFile(paths[1]))!.status).toBe(200);});
 it('caches full WebP only on first detail request, and retains it for offline reopening',async()=>{const w=worker();await w.send('install');expect(w.network).toHaveBeenCalledTimes(2);expect((await w.fetchFile(paths[3]))!.status).toBe(200);expect(w.network).toHaveBeenCalledTimes(3);w.network.mockRejectedValue(Error('offline'));expect((await w.fetchFile(paths[3]))!.status).toBe(200);expect(w.network).toHaveBeenCalledTimes(3);});
 it.each([3,5])('migrates unchanged previously viewed detail path %s during update without downloading it',async index=>{const w=worker(true),url=new URL(paths[index],scope).href;w.data.set('taiping-web:'+scope+':old',new Map([[url+'?__tp_revision='+files[index].revision,new Response('data:'+url)]]));await w.send('install');expect(w.network).toHaveBeenCalledTimes(2);await w.send('message',{data:{type:'CLIENT_READY',version:'test-v2'},source:{id:'tab'}});w.network.mockRejectedValue(Error('offline'));expect(await (await w.fetchFile(paths[index]))!.text()).toBe('data:'+url);expect(w.network).toHaveBeenCalledTimes(2);});
 it('returns a cache miss for unvisited offline full image while the card-sized preview remains playable',async()=>{const w=worker();await w.send('install');w.network.mockRejectedValue(Error('offline'));expect((await w.fetchFile(paths[3]))!.status).toBe(503);expect((await w.fetchFile(paths[1]))!.status).toBe(200);});
 it('adds newly unlocked chapter art and reuses it offline without preloading detail pictures',async()=>{const w=worker();await w.send('install');await w.send('message',{data:{type:'PWA_CHAPTERS',chapters:['taiping_2','bad-key']}});expect(w.network).toHaveBeenCalledTimes(3);w.network.mockRejectedValue(Error('offline'));expect((await w.fetchFile(paths[2]))!.status).toBe(200);expect((await w.fetchFile(paths[3]))!.status).toBe(503);});
 it('caches newly recruited hero thumbnails independently of chapter progress without downloading full art',async()=>{const w=worker();await w.send('install');await w.send('message',{data:{type:'PWA_HEROES',heroes:['reward','nonexistent']}});expect(w.network).toHaveBeenCalledTimes(3);w.network.mockRejectedValue(Error('offline'));expect((await w.fetchFile(paths[2]))!.status).toBe(200);expect((await w.fetchFile(paths[3]))!.status).toBe(503);});
 it('waits for explicit activation and rejects incomplete installs or wrong byte revisions',async()=>{const w=worker(true);await w.send('install');expect(w.skips).toBe(0);await w.send('message',{data:{type:'SKIP_WAITING'}});expect(w.skips).toBe(1);const bad=worker(true);bad.data.set('unrelated',new Map());bad.network.mockResolvedValue(new Response('not this release'));await expect(bad.send('install')).rejects.toThrow('revision mismatch');expect(bad.skips).toBe(0);expect([...bad.data.keys()]).toEqual(['unrelated']);});
 it('keeps old cache while another page has not refreshed, and never deletes an installing version',async()=>{const w=worker(true);await w.send('install');const old='taiping-web:'+scope+':old';w.data.set(old,new Map());w.clients.push({id:'old-tab',url:scope,postMessage:()=>{}});const ready=(id:string)=>w.send('message',{data:{type:'CLIENT_READY',version:'test-v2'},source:{id}});await ready('tab');expect(w.data.has(old)).toBe(true);w.self.registration.installing={}as never;await ready('old-tab');expect(w.data.has(old)).toBe(true);w.self.registration.installing=null;await ready('old-tab');expect(w.data.has(old)).toBe(false);expect(w.data.size).toBe(2);});
});
