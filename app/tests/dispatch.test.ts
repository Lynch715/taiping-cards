import { describe,it,expect } from 'vitest';
import { dispatchColumns } from '../src/core/dispatch';
import { database } from '../src/core/data';
describe('balanced vertical battle dispatch',()=>{
 it('retains every character and avoids one/two-character final columns across all reports',()=>{for(const row of database.stages)for(const text of [row.report_win,row.report_lose]){const columns=dispatchColumns(text);expect(columns.join('')).toBe(text);if(Array.from(text).length>2)expect(Array.from(columns.at(-1)!).length).toBeGreaterThanOrEqual(3);const n=columns.map(c=>Array.from(c).length);expect(Math.max(...n)-Math.min(...n)).toBeLessThanOrEqual(3);}});
 it('balances lengths around wrap boundaries and preserves astral characters',()=>{for(let n=1;n<=200;n++){const text='𠮷'.repeat(n),cols=dispatchColumns(text);expect(cols.join('')).toBe(text);const lengths=cols.map(c=>Array.from(c).length);expect(Math.max(...lengths)-Math.min(...lengths)).toBeLessThanOrEqual(1);if(n>2)expect(Math.min(...lengths)).toBeGreaterThanOrEqual(3);}});
 it('attaches punctuation to preceding text instead of starting a column with it',()=>{const text='甲'.repeat(8)+'，'+'乙'.repeat(8)+'。';expect(dispatchColumns(text).every(c=>!/[，。]/.test(c[0]))).toBe(true);expect(dispatchColumns(text).join('')).toBe(text);});
});
