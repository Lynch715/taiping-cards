const VERSION=__VERSION__,FILES=__FILES__,CORE=__CORE__,CHAPTERS=__CHAPTERS__;
const PREFIX='taiping-web:'+self.registration.scope+':',PROGRAM=PREFIX+'core:'+VERSION,CONTENT=PREFIX+'content:'+VERSION;
const readyClients=new Set(),chaptersReady=new Set(),heroesReady=new Set(),inFlight=new Map();
const urls=new Map(FILES.map(f=>[new URL(f.url,self.registration.scope).href,f])),core=new Set(CORE);
const key=f=>new URL(f.url,self.registration.scope).href+'?__tp_revision='+f.revision;
const metaKey=new URL('__chapter_cache_state__',self.registration.scope).href;
const ownedMetaKey=new URL('__owned_hero_cache_state__',self.registration.scope).href;
const heroAssets=id=>FILES.filter(f=>f.url.startsWith('./assets/characters/'+id+'/')&&!f.url.endsWith('/full.webp'));
let downloadedBytes=0;
async function notify(data){for(const c of await self.clients.matchAll({includeUncontrolled:true}))c.postMessage(data);}
async function restoreMeta(){const saved=await (await caches.open(CONTENT)).match(metaKey);if(saved)try{for(const k of await saved.json())if(CHAPTERS[k])chaptersReady.add(k);}catch{/* rebuild missing metadata */}const owned=await (await caches.open(CONTENT)).match(ownedMetaKey);if(owned)try{for(const id of await owned.json())heroesReady.add(id);}catch{}}
async function persistMeta(){await (await caches.open(CONTENT)).put(metaKey,new Response(JSON.stringify([...chaptersReady]),{headers:{'Content-Type':'application/json'}}));await (await caches.open(CONTENT)).put(ownedMetaKey,new Response(JSON.stringify([...heroesReady]),{headers:{'Content-Type':'application/json'}}));}
async function cachedOrFetch(file){
 const cache=await caches.open(core.has(file.url)?PROGRAM:CONTENT),cacheKey=key(file);let response=await cache.match(cacheKey);
 if(response)return response;
 for(const name of await caches.keys())if(name.startsWith(PREFIX)&&name!==PROGRAM&&name!==CONTENT){response=await (await caches.open(name)).match(cacheKey);if(response)break;}
 if(!response){response=await fetch(new Request(new URL(file.url,self.registration.scope),{cache:'reload',credentials:'same-origin'}));if(!response.ok||response.type==='opaque')throw Error('Asset unavailable '+file.url);
  const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',await response.clone().arrayBuffer())),n=>n.toString(16).padStart(2,'0')).join('');
  if(digest!==file.revision)throw Error('Asset revision mismatch '+file.url);downloadedBytes+=file.bytes;
 }
 await cache.put(cacheKey,response.clone());return response;
}
async function populate(list){let next=0,completed=0;await notify({type:'PWA_PROGRESS',completed,total:list.length});
 await Promise.all(Array.from({length:4},async()=>{while(next<list.length){const file=list[next++];await cachedOrFetch(file);completed++;if(completed%5===0||completed===list.length)await notify({type:'PWA_PROGRESS',completed,total:list.length});}}));
}
async function status(){await restoreMeta();const required=new Set([...CORE,...[...chaptersReady].flatMap(k=>CHAPTERS[k].assets),...[...heroesReady].flatMap(id=>heroAssets(id).map(f=>f.url))]),list=FILES.filter(f=>required.has(f.url));return {type:'PWA_READY',version:VERSION,chapters:[...chaptersReady],heroes:[...heroesReady],total:list.length,bytes:list.reduce((n,f)=>n+f.bytes,0),downloadedBytes};}
async function defaultProgress(){
 if(typeof indexedDB==='undefined')return null;
 return new Promise(resolve=>{try{const r=indexedDB.open('taiping-m1',1);r.onupgradeneeded=()=>r.transaction.abort();r.onerror=()=>resolve(null);r.onsuccess=()=>{const db=r.result;if(!db.objectStoreNames.contains('slots')){db.close();resolve(null);return;}const q=db.transaction('slots').objectStore('slots').get('m1-save-v1');q.onsuccess=()=>{db.close();try{resolve(JSON.parse(q.result??'null'));}catch{resolve(null);}};q.onerror=()=>{db.close();resolve(null);};};}catch{resolve(null);}});
}
self.addEventListener('install',event=>event.waitUntil((async()=>{
 const needed=new Set(['taiping_1','qing_1']),saved=await defaultProgress(),progress=saved?.progress,owned=new Set(Object.values(saved?.growth??{}).filter(c=>c&&typeof c==='object').flatMap(c=>Object.keys(c.heroes??{})));
 for(const [k,c] of Object.entries(CHAPTERS)){const camp=k.split('_')[0];if(c.prerequisites.length&&c.prerequisites.every(id=>Array.isArray(progress?.[camp])&&progress[camp].includes(id)))needed.add(k);}
 // Preserve previously unlocked chapter packs across an app update, including isolated QA slots.
 for(const name of await caches.keys())if(name.startsWith(PREFIX)){const stored=await (await caches.open(name)).match(metaKey);if(stored)try{for(const k of await stored.json())if(CHAPTERS[k])needed.add(k);}catch{}}
 for(const name of await caches.keys())if(name.startsWith(PREFIX)){const old=await (await caches.open(name)).match(ownedMetaKey);if(old)try{for(const id of await old.json())owned.add(id);}catch{}}
 const paths=new Set([...CORE,...[...needed].flatMap(k=>CHAPTERS[k].assets),...[...owned].flatMap(id=>heroAssets(id).map(f=>f.url))]);
 try{await populate(FILES.filter(f=>paths.has(f.url)));
  // Migrate only already-cached, unchanged detail images; never download them during install.
  const content=await caches.open(CONTENT);
  for(const file of FILES.filter(f=>f.url.endsWith('/full.webp')||f.url.startsWith('./assets/equipment/128/')))for(const name of await caches.keys())if(name.startsWith(PREFIX)&&name!==PROGRAM&&name!==CONTENT){const saved=await (await caches.open(name)).match(key(file));if(saved){await content.put(key(file),saved);break;}}
  for(const k of needed)chaptersReady.add(k);for(const id of owned)heroesReady.add(id);await persistMeta();if(!self.registration.active)await self.skipWaiting();}
 catch(error){await caches.delete(PROGRAM);await caches.delete(CONTENT);await notify({type:'PWA_ERROR'});throw error;}
})()));
self.addEventListener('activate',event=>event.waitUntil((async()=>{await self.clients.claim();await notify(await status());})()));
async function ensureChapter(k){if(!CHAPTERS[k])return;await restoreMeta();if(chaptersReady.has(k))return;if(inFlight.has(k))return inFlight.get(k);
 const promise=(async()=>{await populate(FILES.filter(f=>CHAPTERS[k].assets.includes(f.url)));chaptersReady.add(k);await persistMeta();await notify(await status());})();inFlight.set(k,promise);
 try{await promise;}finally{inFlight.delete(k);}
}
async function ensureHero(id){if(typeof id!=='string'||heroesReady.has(id)||!heroAssets(id).length)return;const token='hero:'+id;if(inFlight.has(token))return inFlight.get(token);const promise=(async()=>{await populate(heroAssets(id));heroesReady.add(id);})();inFlight.set(token,promise);try{await promise;}finally{inFlight.delete(token);}}
self.addEventListener('message',event=>{
 if(event.data?.type==='SKIP_WAITING')event.waitUntil(self.skipWaiting());
 if(event.data?.type==='PWA_STATUS')event.waitUntil(status().then(m=>event.source?.postMessage(m)));
 if(event.data?.type==='PWA_HEROES')event.waitUntil((async()=>{try{await restoreMeta();for(const id of event.data.heroes??[])await ensureHero(id);await persistMeta();await notify(await status());}catch{await notify({type:'PWA_CHAPTER_ERROR'});}})());
 if(event.data?.type==='PWA_CHAPTERS')event.waitUntil((async()=>{try{for(const k of event.data.chapters??[])await ensureChapter(k);await notify(await status());}catch{await notify({type:'PWA_CHAPTER_ERROR'});}})());
 if(event.data?.type==='CLIENT_READY'&&event.data.version===VERSION){readyClients.add(event.source?.id);event.waitUntil((async()=>{
  if(self.registration.installing||self.registration.waiting)return;
  const clients=(await self.clients.matchAll({includeUncontrolled:true})).filter(c=>c.url.startsWith(self.registration.scope));
  if(clients.every(c=>readyClients.has(c.id)))for(const name of await caches.keys())if(name.startsWith(PREFIX)&&name!==PROGRAM&&name!==CONTENT)await caches.delete(name);
 })());}
});
self.addEventListener('fetch',event=>{
 const request=event.request;if(request.method!=='GET')return;const url=new URL(request.url);if(url.origin!==self.location.origin)return;
 const exact=urls.get(url.origin+url.pathname),file=request.mode==='navigate'?(exact??FILES.find(f=>f.url==='./index.html')):exact;if(!file)return;
 event.respondWith((async()=>{try{return await cachedOrFetch(file);}catch{return new Response('',{status:503,statusText:'Offline asset not cached'});}})());
});
