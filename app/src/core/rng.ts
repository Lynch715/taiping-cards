/** mulberry32 uint32; all draws, including target selection, use this object. */
export class Mulberry32 {
  state: number;
  constructor(seed:number|string) {
    if(typeof seed==='string'){let v=2166136261;for(const b of new TextEncoder().encode(seed))v=Math.imul(v^b,16777619)>>>0;this.state=v;}
    else this.state=seed>>>0;
  }
  random(){this.state=(this.state+0x6D2B79F5)>>>0;let t=Math.imul(this.state^(this.state>>>15),1|this.state);t^=t+Math.imul(t^(t>>>7),61|t);return ((t^(t>>>14))>>>0)/4294967296;}
  randrange(n:number){if(n<=0)throw Error('n must be positive');return Math.floor(this.random()*n);}
  choice<T>(a:readonly T[]):T {if(!a.length)throw Error('Empty choice');return a[this.randrange(a.length)];}
  sample<T>(a:readonly T[],k:number):T[]{if(k<0||k>a.length)throw Error('Invalid sample');const p=[...a];for(let i=0;i<k;i++){const j=i+this.randrange(p.length-i);[p[i],p[j]]=[p[j],p[i]];}return p.slice(0,k);}
  shuffle<T>(a:T[]){for(let i=a.length-1;i>0;i--){const j=this.randrange(i+1);[a[i],a[j]]=[a[j],a[i]];}}
}
