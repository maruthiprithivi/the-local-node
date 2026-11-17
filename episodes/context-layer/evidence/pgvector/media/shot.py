import sys
from PIL import Image,ImageDraw,ImageFont
def shot(lines,title,out,w=1600):
    f=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',22)
    lh=32; pad=28; bar=44
    mx=max(len(l) for l in lines); W=max(w,int(mx*13.3)+2*pad); H=bar+pad*2+lh*len(lines)
    im=Image.new('RGB',(W,H),'#11111b'); d=ImageDraw.Draw(im)
    d.rectangle([0,0,W,bar],fill='#1e1e2e')
    for i,c in enumerate(['#f38ba8','#f9e2af','#a6e3a1']): d.ellipse([18+i*28,14,34+i*28,30],fill=c)
    d.text((W/2-len(title)*6.5,10),title,font=f,fill='#9399b2')
    for i,l in enumerate(lines):
        c='#cdd6f4'
        if l.startswith('#'): c='#89b4fa'
        if '| meaning_flip' in l or '| identity_permission' in l: c='#f9e2af'
        d.text((pad,bar+pad+i*lh),l,font=f,fill=c)
    im.save(out)
