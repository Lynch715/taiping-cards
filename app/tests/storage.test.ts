import {beforeEach,describe,it,expect,vi} from 'vitest';
import {IDBFactory} from 'fake-indexeddb';
import {newSave,chapter} from '../src/core/campaign';
import {migrateGrowth} from '../src/core/progression';
import {importSaveFile,exportSaveFile} from '../src/platform/save-transfer';
async function rawRead(key:string){return new Promise<string|undefined>((resolve,reject)=>{const r=indexedDB.open('taiping-m1',1);r.onsuccess=()=>{const db=r.result,q=db.transaction('slots').objectStore('slots').get(key);q.onsuccess=()=>{resolve(q.result);db.close();};q.onerror=()=>reject(q.error);};});}
beforeEach(()=>{vi.resetModules();vi.stubGlobal('indexedDB',new IDBFactory());vi.stubGlobal('location',{search:'?qa=storage-tests'});});
describe('existing IndexedDB military records',()=>{
 it('keeps the original schema/key and atomically preserves the pre-import valid backup',async()=>{const {saveGame,loadSave}=await import('../src/platform/storage');const old=newSave();await saveGame(old);const next=newSave();next.seed=808;next.campaign='qing';await saveGame(next);await saveGame(next);expect((await loadSave()).save).toEqual(next);expect(JSON.parse((await rawRead('m1-qa-storage-tests-v1-backup'))!)).toEqual(old);});
 it('rejects invalid import and invalid save without touching either stored record',async()=>{const {saveGame,loadSave}=await import('../src/platform/storage');const old=newSave();old.seed=101;await saveGame(old);const raw=await exportSaveFile(old);await expect(importSaveFile(raw.replace('"seed": 101','"seed": 999'))).rejects.toThrow();await expect(saveGame({...old,version:2} as never)).rejects.toThrow();expect((await loadSave()).save).toEqual(old);expect(await rawRead('m1-qa-storage-tests-v1-backup')).toBeUndefined();});
 it('migrates a legacy import before its atomic write so autosave preserves the pre-import backup',async()=>{const {saveGame}=await import('../src/platform/storage');const old=newSave();old.seed=77;await saveGame(old);const raw=newSave();delete raw.growth;raw.campaign='qing';raw.progress.qing=chapter('qing').map(r=>r.stage_id);const imported=migrateGrowth(raw,Date.now());await saveGame(imported);await saveGame(imported);expect(JSON.parse((await rawRead('m1-qa-storage-tests-v1-backup'))!)).toEqual(old);});

});
