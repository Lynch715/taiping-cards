export function targetArrivalDay(days:number[],chapter:number,order:number){
 if(days.length!==8||days.some(n=>!Number.isFinite(n)||n<=0)||!Number.isInteger(chapter)||chapter<1||chapter>8||!Number.isInteger(order)||order<1||order>6)throw Error('Invalid target calendar');
 return days.slice(0,chapter-1).reduce((a,b)=>a+b,0)+days[chapter-1]*order/6;
}
