import {readFile,writeFile,readdir,stat} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {join,relative} from 'node:path';
import {fileURLToPath} from 'node:url';
const dir=fileURLToPath(new URL('../dist/',import.meta.url));
const hash=b=>createHash('sha256').update(b).digest('hex');
const indexPath=join(dir,'index.html');
await writeFile(indexPath,(await readFile(indexPath,'utf8')).replace(/(<meta name="pwa-build-id" content=")[^"]*("\s*\/?>)/,'$1__PWA_BUILD_ID__$2'));
async function walk(path){const all=[];for(const name of await readdir(path)){const file=join(path,name);if((await stat(file)).isDirectory())all.push(...await walk(file));else all.push(file);}return all;}
const files=[];
for(const path of (await walk(dir)).sort()){
 const name=relative(dir,path);if(['sw.js','pwa-build.json'].includes(name))continue;
 if(name.endsWith('/full.png'))throw Error('PNG master must not enter the web package: '+name);
 const bytes=await readFile(path);files.push({url:'./'+name.replaceAll('\\','/'),revision:hash(bytes),bytes:bytes.length});
}
const tables=async name=>JSON.parse(await readFile(new URL('../src/core/data/'+name+'.json',import.meta.url),'utf8'));
const stages=await tables('stages'),starters=await tables('starter_cards'),heroes=await tables('heroes');const heroIds=new Set(heroes.map(h=>h.id));
const npcIds=new Set(files.flatMap(f=>f.url.match(/^\.\/assets\/characters\/((?:tp|qing)_npc_[a-z0-9_]+)\/mini\.webp$/)?.slice(1)??[]));
const chapters={};
for(const camp of ['taiping','qing'])for(const number of Array.from({length:8},(_,i)=>i+1)){
 const own=starters.find(s=>s.campaign===camp),ids=new Set([own.monarch,...own.cards.split(';')]);
 const rows=stages.filter(s=>s.campaign===camp&&s.chapter<=number);
 for(const row of rows){if(row.reward_unlock)ids.add(row.reward_unlock);if(row.chapter===number)for(const id of row.enemies.split(','))if(heroIds.has(id)||npcIds.has(id))ids.add(id);if(row.enemy_monarch)ids.add(row.enemy_monarch);}
 const urls=[...ids].flatMap(id=>(npcIds.has(id)?['mini','thumb']:['card','mini','thumb']).map(name=>'./assets/characters/'+id+'/'+name+'.webp'));
 for(const url of urls)if(!files.some(f=>f.url===url))throw Error('Missing chapter asset '+url);
 chapters[camp+'_'+number]={assets:urls,prerequisites:stages.filter(s=>s.campaign===camp&&s.chapter<number).map(s=>s.stage_id)};
}
const core=files.filter(f=>!f.url.startsWith('./assets/characters/')&&!f.url.startsWith('./assets/equipment/128/')).map(f=>f.url);
const initialUrls=new Set([...core,...chapters.taiping_1.assets,...chapters.qing_1.assets]);
const initialBytes=files.filter(f=>initialUrls.has(f.url)).reduce((n,f)=>n+f.bytes,0);
const template=await readFile(new URL('./sw-template.js',import.meta.url),'utf8');
const pkg=JSON.parse(await readFile(new URL('../package.json',import.meta.url),'utf8'));
const release=process.env.PWA_RELEASE??pkg.version;
const version=release+'-'+hash(JSON.stringify(files)+template+JSON.stringify(chapters)).slice(0,12);
const html=(await readFile(indexPath,'utf8')).replace('__PWA_BUILD_ID__',version);
await writeFile(indexPath,html);const indexFile=files.find(f=>f.url==='./index.html');indexFile.revision=hash(html);const htmlDelta=Buffer.byteLength(html)-indexFile.bytes;indexFile.bytes=Buffer.byteLength(html);
const sw=template.replace('__VERSION__',JSON.stringify(version)).replace('__FILES__',JSON.stringify(files)).replace('__CORE__',JSON.stringify(core)).replace('__CHAPTERS__',JSON.stringify(chapters));
await writeFile(join(dir,'sw.js'),sw);
// Includes one uncached initial page load plus all install fetches, SW and install-icon overhead.
const firstInstallUpperBound=2*(initialBytes+htmlDelta)+2*Buffer.byteLength(sw)+100_000;
if(firstInstallUpperBound>10_000_000)throw Error('Cold installation exceeds 10MB: '+firstInstallUpperBound);
const allUnlockedUrls=new Set([...core,...Object.values(chapters).flatMap(c=>c.assets)]);
const allUnlockedCacheBytes=files.filter(f=>allUnlockedUrls.has(f.url)).reduce((n,f)=>n+f.bytes,0);
const allUnlockedInstallUpperBound=2*allUnlockedCacheBytes+2*Buffer.byteLength(sw)+100_000;
// The 10MB gate applies to a fresh installation; later unlocked chapters are incremental content.
const metadata={version,files,core,chapters,totalBytes:files.reduce((n,f)=>n+f.bytes,0),initialCacheFiles:initialUrls.size,initialCacheBytes:initialBytes+htmlDelta,firstInstallUpperBound,allUnlockedCacheBytes,allUnlockedInstallUpperBound};
await writeFile(join(dir,'pwa-build.json'),JSON.stringify(metadata,null,2)+'\n');
console.log(JSON.stringify({version,packageMB:metadata.totalBytes/1e6,initialCacheMB:metadata.initialCacheBytes/1e6,firstInstallUpperBoundMB:firstInstallUpperBound/1e6}));
