import {describe,it,expect} from 'vitest';
import {installMobileGestures} from '../src/platform/mobile-gestures';

function setup(){const target=new EventTarget(),dispose=installMobileGestures(target as unknown as Window);return {target,dispose};}
function touch(target:EventTarget,type:string,{count=1,at=100,x=20,y=20,control=false,cancelable=true}={}){
 const e=new Event(type,{cancelable});Object.defineProperties(e,{touches:{value:Array.from({length:count},()=>({clientX:x,clientY:y}))},changedTouches:{value:[{clientX:x,clientY:y}]},timeStamp:{value:at}});
 (target as EventTarget&{closest?:()=>unknown}).closest=()=>control?{}:null;target.dispatchEvent(e);return e;
}
describe('mobile gesture boundary',()=>{
 it('blocks cancelable multi-finger start and move but keeps one-finger scrolling',()=>{const {target}=setup();expect(touch(target,'touchstart').defaultPrevented).toBe(false);expect(touch(target,'touchmove').defaultPrevented).toBe(false);expect(touch(target,'touchstart',{count:2}).defaultPrevented).toBe(true);expect(touch(target,'touchmove',{count:2}).defaultPrevented).toBe(true);});
 it('cancels Safari gesture zoom and safely ignores noncancelable events',()=>{const {target}=setup();for(const type of ['gesturestart','gesturechange']){const e=new Event(type,{cancelable:true});target.dispatchEvent(e);expect(e.defaultPrevented).toBe(true);}expect(touch(target,'touchmove',{count:2,cancelable:false}).defaultPrevented).toBe(false);});
 it('blocks a nearby quick double tap on the same non-control surface',()=>{const {target}=setup();expect(touch(target,'touchend',{count:0,at:100}).defaultPrevented).toBe(false);expect(touch(target,'touchend',{count:0,at:260,x:24}).defaultPrevented).toBe(true);});
 it('preserves repeated control taps, text editing, distant taps and taps after scrolling',()=>{const {target}=setup();touch(target,'touchend',{count:0,at:100,control:true});expect(touch(target,'touchend',{count:0,at:200,control:true}).defaultPrevented).toBe(false);touch(target,'touchend',{count:0,at:400});expect(touch(target,'touchend',{count:0,at:500,x:100}).defaultPrevented).toBe(false);touch(target,'touchend',{count:0,at:1000});expect(touch(target,'touchend',{count:0,at:1400}).defaultPrevented).toBe(false);touch(target,'touchmove',{at:1450});expect(touch(target,'touchend',{count:0,at:1500}).defaultPrevented).toBe(false);});
 it('removes every listener on disposal so reload cannot stack gesture handlers',()=>{const {target,dispose}=setup();dispose();expect(touch(target,'touchstart',{count:2}).defaultPrevented).toBe(false);const e=new Event('gesturestart',{cancelable:true});target.dispatchEvent(e);expect(e.defaultPrevented).toBe(false);});
});
