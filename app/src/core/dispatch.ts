/** Balance vertical columns and keep closing punctuation attached to its preceding text. */
export function dispatchColumns(text:string,preferredRows=16):string[]{
 const chars=Array.from(text),count=Math.ceil(chars.length/Math.max(3,preferredRows));
 const columns:string[]=[];let at=0;
 const closing=/[，。！？；：、）》】」』…]/u,opening=/[（《【「『]/u;
 for(let i=0;i<count;i++){
  const remaining=chars.length-at,left=count-i;
  if(left===1){columns.push(chars.slice(at).join(''));break;}
  const ideal=Math.round(remaining/left);
  const options=[ideal-1,ideal,ideal+1].filter(n=>n>=3&&remaining-n>=3*(left-1));
  const score=(n:number)=>Number(closing.test(chars[at+n]??''))*20+Number(opening.test(chars[at+n-1]??''))*20+Math.abs(n-remaining/left);
  options.sort((a,b)=>score(a)-score(b));const n=options[0]??ideal;
  columns.push(chars.slice(at,at+n).join(''));at+=n;
 }
 return columns;
}
