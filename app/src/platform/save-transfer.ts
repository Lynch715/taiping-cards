import { validSave } from '../core/campaign';
import type { Save } from '../core/campaign';
const FORMAT='taiping-military-save';
const LIMIT=5*1024*1024;
export interface SaveFile {format:typeof FORMAT;version:1;exportedAt:string;payload:Save;checksum:{algorithm:'SHA-256';value:string}}
function copySave(s:Save):Save{return {...(s.growth?{growth:structuredClone(s.growth)}:{}),version:1,campaign:s.campaign,seed:s.seed,progress:{taiping:[...s.progress.taiping],qing:[...s.progress.qing]},formations:{taiping:[...s.formations.taiping],qing:[...s.formations.qing]}};}
async function digest(text:string){return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text))),x=>x.toString(16).padStart(2,'0')).join('');}
function body(payload:Save,exportedAt:string){return {format:FORMAT,version:1 as const,exportedAt,payload:copySave(payload)};}
export async function exportSaveFile(save:Save,exportedAt=new Date().toISOString()):Promise<string>{if(!validSave(save))throw Error('当前军册无效，无法导出');const data=body(save,exportedAt);return JSON.stringify({...data,checksum:{algorithm:'SHA-256',value:await digest(JSON.stringify(data))}},null,2)+'\n';}
export async function importSaveFile(text:string):Promise<SaveFile>{
 if(new TextEncoder().encode(text).byteLength>LIMIT)throw Error('存档文件超过 5MB，未导入');
 let value:unknown;try{value=JSON.parse(text);}catch{throw Error('不是有效的 JSON 存档，现有进度未改动');}
 if(!value||typeof value!=='object')throw Error('存档格式不正确，现有进度未改动');
 const v=value as Partial<SaveFile>;
 if(v.format!==FORMAT||v.version!==1)throw Error('不支持此存档版本，现有进度未改动');
 if(typeof v.exportedAt!=='string'||!Number.isFinite(Date.parse(v.exportedAt))||!validSave(v.payload))throw Error('存档内容不完整，现有进度未改动');
 if(v.checksum?.algorithm!=='SHA-256'||typeof v.checksum.value!=='string'||v.checksum.value!==await digest(JSON.stringify(body(v.payload,v.exportedAt))))throw Error('存档完整性校验失败，现有进度未改动');
 return {...body(v.payload,v.exportedAt),format:FORMAT,checksum:v.checksum};
}
export async function downloadSave(save:Save){const text=await exportSaveFile(save),url=URL.createObjectURL(new Blob([text],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='太平天国-军册-'+new Date().toISOString().replace(/[:.]/g,'-')+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),10000);}
