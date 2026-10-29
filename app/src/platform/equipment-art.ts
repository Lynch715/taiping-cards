import atlas from './equipment-icons.generated.json';
export const equipmentAtlas=atlas;
export function equipmentArt(set:string,slot:string){
 const found=Object.entries(atlas.icons).find(([,icon])=>icon.set===set&&icon.slot===slot);
 return found?{id:found[0],...found[1]}:null;
}
export function equipmentSpriteStyle(icon:{x:number;y:number},size:64|128=64){
 const scale=size/64;
 return {width:size,height:size,backgroundPosition:`${-icon.x*scale}px ${-icon.y*scale}px`,backgroundSize:`${atlas.width*scale}px ${atlas.height*scale}px`};
}
