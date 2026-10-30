import {newSave as fresh,starters} from '../src/core/campaign';
import {acquire,campGrowth} from '../src/core/progression';
/** Pre-change roster retained for regression coverage of existing saves. */
export function newSave(now=Date.now(),seed=1851){const s=fresh(now,seed);delete s.rules;delete s.introSeen;for(const camp of ['taiping','qing']as const){const c=campGrowth(s,camp),old=starters(camp);c.heroes={};delete c.progressive;delete c.recruitsAtOne;delete c.monarchPity;for(const id of [...old.cards.split(';'),old.monarch])acquire(c,id);for(const h of Object.values(c.heroes))h.level=10;c.monarch=old.monarch;s.formations[camp]=old.cards.split(';').slice(0,5);}return s;}
