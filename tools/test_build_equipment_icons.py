import unittest
import numpy as np
from PIL import Image,ImageDraw
from build_equipment_icons import normalize

class EquipmentIcons(unittest.TestCase):
 def test_keeps_full_canvas_alpha_and_centers_unclipped_object(self):
  source=Image.new('RGBA',(1024,1024));ImageDraw.Draw(source).rectangle((140,100,879,899),fill=(80,60,30,255))
  master,box,scale=normalize(source)
  self.assertEqual(master.size,(512,512));self.assertEqual(master.getchannel('A').getextrema(),(0,255));b=master.getchannel('A').point(lambda a:255 if a>16 else 0).getbbox();self.assertLessEqual(max(b[2]-b[0],b[3]-b[1]),411);self.assertLessEqual(abs((b[0]+b[2])/2-256),1);self.assertLessEqual(abs((b[1]+b[3])/2-256),1)
  self.assertEqual(master.tobytes(),normalize(source)[0].tobytes())
 def test_rejects_cut_edges_and_missing_alpha_without_silently_keying_or_cropping(self):
  opaque=Image.new('RGB',(1024,1024),'white')
  with self.assertRaises(ValueError):normalize(opaque)
  cut=Image.new('RGBA',(1024,1024));ImageDraw.Draw(cut).rectangle((0,100,700,900),fill='red')
  with self.assertRaisesRegex(ValueError,'EDGE_CUT'):normalize(cut)
 def test_preserves_semtransparent_material(self):
  image=Image.new('RGBA',(1024,1024));ImageDraw.Draw(image).ellipse((120,120,900,900),fill=(100,80,40,128));master,_,_=normalize(image);self.assertEqual(master.getpixel((256,256))[3],128)
 def test_faint_source_pixels_do_not_force_cropping(self):
  image=Image.new('RGBA',(1254,1254));ImageDraw.Draw(image).ellipse((250,210,1010,1100),fill=(100,80,40,255));image.putpixel((0,0),(100,80,40,8));image.putpixel((1253,1253),(100,80,40,8))
  master,_,_=normalize(image);self.assertEqual(master.size,(512,512));box=master.getchannel('A').getbbox();self.assertGreaterEqual(min(box[0],box[1],512-box[2],512-box[3]),1)

if __name__=='__main__':unittest.main()
