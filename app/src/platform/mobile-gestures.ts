/** Keep the game at its designed scale without swallowing ordinary scroll or form input. */
export function installMobileGestures(target:Window){
 let lastTap:{at:number;x:number;y:number;target:EventTarget|null}|null=null;
 const cancel=(event:Event)=>{if(event.cancelable)event.preventDefault();};
 const multiTouch=(event:TouchEvent)=>{if(event.type==='touchmove')lastTap=null;if(event.touches.length>1){lastTap=null;cancel(event);}};
 const tap=(event:TouchEvent)=>{
  if(event.touches.length){lastTap=null;return;}
  const node=event.target as Element|null;
  if(node?.closest?.('button,a,input,select,textarea,label,[contenteditable="true"],[role="button"]')){lastTap=null;return;}
  const point=event.changedTouches[0];if(!point)return;
  const next={at:event.timeStamp,x:point.clientX,y:point.clientY,target:event.target};
  if(lastTap&&next.target===lastTap.target&&next.at-lastTap.at>=0&&next.at-lastTap.at<300&&Math.hypot(next.x-lastTap.x,next.y-lastTap.y)<24){cancel(event);lastTap=null;}else lastTap=next;
 };
 const options={passive:false,capture:true};
 target.addEventListener('touchstart',multiTouch,options);target.addEventListener('touchmove',multiTouch,options);target.addEventListener('touchend',tap,options);
 target.addEventListener('gesturestart',cancel,options);target.addEventListener('gesturechange',cancel,options);
 return()=>{target.removeEventListener('touchstart',multiTouch,options);target.removeEventListener('touchmove',multiTouch,options);target.removeEventListener('touchend',tap,options);target.removeEventListener('gesturestart',cancel,options);target.removeEventListener('gesturechange',cancel,options);};
}
