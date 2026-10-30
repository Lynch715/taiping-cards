import {biographies} from '../core/biographies';
export function Biography({id}:{id:string}){const text=biographies[id];return text?<details className="hero-biography"><summary>查看生平简介</summary><p>{text}</p></details>:null;}
