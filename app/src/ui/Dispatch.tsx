import { dispatchColumns } from '../core/dispatch';
export function Dispatch({text}:{text:string}){return <article className="dispatch"><span>战地军报</span><div className="dispatch-columns" role="paragraph" aria-label={text}>{dispatchColumns(text).map((col,i)=><span className="dispatch-column" aria-hidden="true" key={i}>{col}</span>)}</div></article>;}
