import 'pixi.js/prepare';
import { assetUrl } from '../platform/assets';
import { Application,Assets,Container,Graphics,Sprite,Text,TextStyle } from 'pixi.js';
import type { ActorState,BattleEvent,TeamInput,Terrain } from '../core/battle/types';
import { database } from '../core/data';
import { battleCardPosition,terrainBackgrounds } from './battleLayout';
export interface SceneController {apply:(event:BattleEvent)=>void;destroy:()=>void}
export async function createBattleScene(host:HTMLDivElement,teams:[TeamInput,TeamInput],terrain:Terrain='陆战'):Promise<SceneController>{
 await document.fonts.load('700 30px "Noto Serif SC"');
 const app=new Application();await app.init({width:1080,height:1350,backgroundAlpha:0,antialias:false,resolution:Math.min(devicePixelRatio||1,2),autoDensity:true,preference:'webgl',powerPreference:'high-performance',autoStart:false});host.appendChild(app.canvas);
 app.canvas.setAttribute('aria-label','敌军在上，我军在下的自动战斗场景');app.canvas.style.width='100%';app.canvas.style.height='100%';
 const nodes=new Map<string,{root:Container;art:Sprite|Graphics;hp:Graphics;rage:Graphics;dead:Text;deadSeal:Graphics;glow:Graphics;homeY:number}>();
 const motes:{text:Text;age:number;life:number}[]=[];const moves:{root:Container;age:number;home:number;direction:number}[]=[];
 const style=new TextStyle({fontFamily:'"Noto Serif SC", "Songti SC", serif',fontSize:30,fontWeight:'bold',fill:0xede3cc});
 const background=terrainBackgrounds[terrain];
 if(background){try{const image=new Sprite(await Assets.load(assetUrl(`assets/battle/${background}.webp`)));image.width=1080;image.height=1350;app.stage.addChild(image);app.stage.addChild(new Graphics().rect(0,0,1080,1350).fill({color:0x15110e,alpha:.55}));}catch{/* Keep the existing field when a terrain image is unavailable offline. */}}
 const land=new Graphics().moveTo(20,660).lineTo(1060,660).stroke({color:0xbaa078,alpha:.18,width:2});app.stage.addChild(land);
 for(const [side,input] of teams.entries())for(const [slot,id] of input.heroes.entries()){
  const top=side===1;const {x,y}=battleCardPosition(side,slot);
  const root=new Container();root.position.set(x,y);app.stage.addChild(root);
  const frame=new Graphics().rect(-5,-5,178,262).fill({color:top?0x1e3550:0xb0281c}).rect(-1,-1,170,254).stroke({color:top?0xb8893b:0xd9a21b,width:2});root.addChild(frame);
  let art:Sprite|Graphics;const hero=database.heroes.find(x=>x.id===id),npc=database.enemy_units.find(x=>x.id===id);
  let texture;try{if(hero||npc)texture=await Assets.load(assetUrl(`assets/characters/${id}/mini.webp`));}catch{/* An offline recruit or an NPC awaiting art can fight using its named silhouette. */}
  if(texture){art=new Sprite(texture);art.width=168;art.height=252;}else art=new Graphics().rect(0,0,168,252).fill(top?0x293344:0x3f2920).ellipse(84,51,26,30).fill(0x0f1215).poly([35,192,50,95,118,95,133,192]).fill(0x0f1215).rect(55,190,22,62).rect(92,190,22,62).fill(0x0f1215).moveTo(142,45).lineTo(142,240).stroke({color:0x91816a,width:5});
  root.addChild(art);const glow=new Graphics().rect(-7,-7,182,266).stroke({color:0xd9a21b,width:8,alpha:.18}).rect(-4,-4,176,260).stroke({color:0xffdb63,width:3,alpha:.95});glow.visible=false;root.addChild(glow);const name=new Text({text:hero?.name??npc?.name??id,style});name.anchor.set(.5,0);name.position.set(84,287);root.addChild(name);
  const base=new Graphics().rect(0,258,168,12).fill(0x090909).rect(0,275,168,6).fill(0x090909);root.addChild(base);
  const hp=new Graphics(),rage=new Graphics();root.addChild(hp,rage);
  const deadSeal=new Graphics().rect(44,110,80,80).fill(0xa8261b).rect(49,115,70,70).stroke({color:0xede3cc,width:2});deadSeal.visible=false;root.addChild(deadSeal);
  const dead=new Text({text:'殁',style:new TextStyle({fontFamily:style.fontFamily,fontSize:66,fontWeight:'bold',fill:0xede3cc})});dead.anchor.set(.5);dead.position.set(84,150);dead.visible=false;root.addChild(dead);
  nodes.set(`${side}:${slot}`,{root,art,hp,rage,dead,deadSeal,glow,homeY:y});
 }
 function state(s:ActorState,side:number){const n=nodes.get(`${side}:${s.slot}`)!;n.hp.clear().rect(0,258,168*Math.max(0,s.hp/s.max_hp),12).fill(side?0xa8261b:0x5e7f45);n.rage.clear().rect(0,275,168*s.rage/100,6).fill(0xd9a21b);const isDead=s.hp<=0||s.escaped;n.art.alpha=isDead?.28:1;n.dead.visible=isDead;n.deadSeal.visible=isDead;n.glow.visible=s.rage>=100&&!isDead;n.dead.text=s.escaped?'离':'殁';if(n.art instanceof Sprite)n.art.tint=isDead?0x777777:0xffffff;}
 const damageStyle=new TextStyle({fontFamily:style.fontFamily,fontWeight:'bold',fontSize:55,fill:0xf1ce76,stroke:{color:0x28150d,width:5}});
 const warmDamage=new Text({text:'−88888',style:damageStyle});warmDamage.visible=false;app.stage.addChild(warmDamage);
 await app.renderer.prepare.upload(app.stage);
 app.render();
 await new Promise<void>(resolve=>requestAnimationFrame(()=>resolve()));
 await new Promise<void>(resolve=>requestAnimationFrame(()=>resolve()));
 app.start();
 performance.mark('m1-scene-ready');
 app.ticker.add(t=>{const dt=t.deltaMS/1000;for(let i=motes.length-1;i>=0;i--){const m=motes[i];m.age+=dt;m.text.y-=dt*90;m.text.alpha=Math.max(0,1-m.age/m.life);if(m.age>=m.life){m.text.destroy();motes.splice(i,1);}}
  for(let i=moves.length-1;i>=0;i--){const m=moves[i];m.age+=dt;m.root.y=m.home+Math.sin(Math.min(1,m.age/.2)*Math.PI)*m.direction*35;if(m.age>=.2){m.root.y=m.home;moves.splice(i,1);}}});
 return {apply(e){if(e.event==='state')e.teams?.forEach((t,side)=>t.actors.forEach(s=>state(s,side)));
  if(e.event==='damage'){const node=nodes.get(`${e.target_side}:${e.target_slot}`),attacker=nodes.get(`${e.source_side}:${e.source_slot}`);if(node){const text=new Text({text:`−${e.amount}`,style:damageStyle});text.anchor.set(.5);text.position.set(node.root.x+84,node.root.y+90);app.stage.addChild(text);motes.push({text,age:0,life:.7});}if(attacker&&!moves.some(x=>x.root===attacker.root))moves.push({root:attacker.root,home:attacker.homeY,age:0,direction:Number(e.source_side)===0?-1:1});}},destroy(){app.destroy(true,{children:true,texture:false,textureSource:false});}};
}
