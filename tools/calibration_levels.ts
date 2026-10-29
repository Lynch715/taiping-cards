/** Five integer-level heroes give0.2-level means; an even reference group preserves a0.1 median exactly. */
export function calibrationMeans(median:number,count:number):number[]{
 if(!Number.isFinite(median)||median<1||median>100||!Number.isInteger(count)||count<1)throw Error('Invalid calibration reference');
 const low=Math.floor(median*5+1e-8)/5,high=Math.ceil(median*5-1e-8)/5;
 if(Math.abs(low-high)>1e-8&&count%2)throw Error('A half-step median needs an even reference count');
 return Array.from({length:count},(_,i)=>i%2?high:low);
}
