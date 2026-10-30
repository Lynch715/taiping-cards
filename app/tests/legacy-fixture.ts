import {newSave as fresh,starters} from '../src/core/campaign';
import {acquire,campGrowth} from '../src/core/progression';
/** Pre-change roster retained for regression coverage of existing saves. */
export function newSave(now=Date.now(),seed=1851){const s=fresh(now,seed);for(const camp of ['taiping','qing']as const){const c=campGrowth(s,camp),old=starters(camp);c.heroes={};delete c.progressive;delete c.monarchPity;for(const id of [...old.cards.split(';'),old.monarch])acquire(c,id);c.monarch=old.monarch;s.formations[camp]=old.cards.split(';').slice(0,5);}return s;}
