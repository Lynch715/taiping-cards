import {recommendFormation} from '../core/formation';
import type {GearItem} from '../core/progression';
import type {TeamInput,Terrain} from '../core/battle/types';
self.onmessage=(event:MessageEvent<{pool:TeamInput;enemy:TeamInput;terrain:Terrain;current:string[];inventory:GearItem[]}>)=>{try{self.postMessage({result:recommendFormation(event.data.pool,event.data.enemy,event.data.terrain,{current:event.data.current,inventory:event.data.inventory})});}catch(error){self.postMessage({error:error instanceof Error?error.message:String(error)});}};
