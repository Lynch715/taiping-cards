import { describe,it,expect } from 'vitest';
import { newSave,chapter } from '../src/core/campaign';
import { exportSaveFile,importSaveFile } from '../src/platform/save-transfer';
describe('portable military save integrity',()=>{
 it('round trips both campaigns, formations and uint32 seed without mutating source',async()=>{const save=newSave();save.campaign='qing';save.seed=0xffffffff;save.progress.taiping=chapter('taiping').map(s=>s.stage_id);save.formations.qing.reverse();const original=structuredClone(save);const file=await exportSaveFile(save,'2026-10-28T12:00:00.000Z');const decoded=await importSaveFile(file);expect(decoded.payload).toEqual(save);expect(save).toEqual(original);decoded.payload.formations.qing.reverse();expect(save).toEqual(original);});
 it('rejects bad JSON, unsupported versions, truncated progress, illegal IDs, tampering and oversize files',async()=>{
  const good=JSON.parse(await exportSaveFile(newSave()));
  const cases=['{',JSON.stringify({...good,version:2}),JSON.stringify({...good,payload:{...good.payload,seed:2}}),JSON.stringify({...good,payload:{...good.payload,formations:{taiping:['x'],qing:[]}}}),JSON.stringify({...good,payload:{...good.payload,progress:{taiping:['tp_1_6'],qing:[]}}}),JSON.stringify({...good,checksum:{algorithm:'SHA-256',value:'bad'}}),' '.repeat(1024*1024+1)];
  for(const text of cases)await expect(importSaveFile(text)).rejects.toThrow();
 });
});
