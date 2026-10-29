#!/usr/bin/env python3
"""Draw the native four-character seal icon and its web/desktop installation sizes."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json
ROOT=Path(__file__).resolve().parents[1]
PAPER='#EDE3CC';RED='#A8261B';CREAM='#F8EED6';GOLD='#D4B477'
def main():
 out=ROOT/'app/public/icons';out.mkdir(parents=True,exist_ok=True)
 art=ROOT/'assets/ui';art.mkdir(parents=True,exist_ok=True)
 face=ImageFont.truetype('/System/Library/Fonts/Supplemental/Songti.ttc',244,index=1)
 master=Image.new('RGB',(1024,1024),PAPER);d=ImageDraw.Draw(master)
 d.rounded_rectangle((88,88,936,936),radius=160,fill=RED)
 d.rounded_rectangle((140,140,884,884),radius=112,outline=GOLD,width=9)
 d.rounded_rectangle((166,166,858,858),radius=86,outline=CREAM,width=3)
 for char,x,y in [('太',364,366),('平',660,366),('军',364,662),('报',660,662)]:
  box=d.textbbox((0,0),char,font=face,stroke_width=1);left=x-(box[2]-box[0])/2-box[0];top=y-(box[3]-box[1])/2-box[1]
  d.text((left,top),char,font=face,fill=CREAM,stroke_width=1)
 master.save(art/'app-icon-1024.png',optimize=True)
 files={}
 for size,name in [(192,'icon-192.png'),(512,'icon-512.png'),(512,'icon-maskable-512.png'),(180,'apple-touch-icon.png'),(32,'favicon-32.png')]:
  image=master.resize((size,size),Image.Resampling.LANCZOS).quantize(colors=64,method=Image.Quantize.MEDIANCUT)
  image.save(out/name,optimize=True);files[name]={'size':size,'bytes':(out/name).stat().st_size}
 master.save(ROOT/'app/public/favicon.ico',format='ICO',sizes=[(16,16),(32,32),(48,48)])
 svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" viewBox="0 0 1024 1024"><title>太平军报</title><rect width="1024" height="1024" fill="{PAPER}"/><rect x="88" y="88" width="848" height="848" rx="160" fill="{RED}"/><rect x="140" y="140" width="744" height="744" rx="112" fill="none" stroke="{GOLD}" stroke-width="9"/><rect x="166" y="166" width="692" height="692" rx="86" fill="none" stroke="{CREAM}" stroke-width="3"/><g fill="{CREAM}" text-anchor="middle" dominant-baseline="central" font-family="Songti SC,STSong,serif" font-weight="900" font-size="244"><text x="364" y="366">太</text><text x="660" y="366">平</text><text x="364" y="662">军</text><text x="660" y="662">报</text></g></svg>'
 (ROOT/'app/public/favicon.svg').write_text(svg);(art/'app-icon.svg').write_text(svg)
 print(json.dumps({'icons':files,'maskable_meaningful_glyphs':'within central 80 percent circle; outer decorative frame may be clipped','font':face.getname()},ensure_ascii=False))
if __name__=='__main__':main()
