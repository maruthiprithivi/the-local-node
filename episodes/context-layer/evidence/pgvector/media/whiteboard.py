from PIL import Image,ImageDraw,ImageFont
W,H=1920,1080
im=Image.new('RGB',(W,H),'#f8f5ee'); d=ImageDraw.Draw(im)
G='/usr/share/fonts/truetype/sand-box/google/Inter/'
import glob
p=glob.glob(G+'*.ttf')[0]
def F(s,w=700):
    f=ImageFont.truetype(p,s)
    try: f.set_variation_by_axes([14,w] if len(f.get_variation_axes())==2 else [w])
    except Exception: pass
    return f
d.text((120,90),'One JML event, four steps',font=F(64,800),fill='#1b1b1b')
d.text((120,175),'pgvector baseline: the only path that matters is the read back',font=F(34,400),fill='#6b6b6b')
steps=[('1','Event','join, move,\nleave, add,\nchange, remove','#264653'),
       ('2','Write / delete','real INSERT or\nDELETE in\npgvector','#264653'),
       ('3','Read back','is the old access\nreally gone?','#e76f51'),
       ('4','Trap ask','4 axes, scored\none by one','#264653')]
bw,bh,gap=360,360,110; x0=(W-(4*bw+3*gap))//2; y0=380
for i,(n,t,s,c) in enumerate(steps):
    x=x0+i*(bw+gap)
    hot=(c=='#e76f51')
    d.rounded_rectangle([x,y0,x+bw,y0+bh],radius=36,fill='#ffffff',outline=c,width=10 if hot else 4)
    d.text((x+36,y0+30),n,font=F(64,800),fill=c)
    d.text((x+36,y0+120),t,font=F(44,800),fill='#1b1b1b')
    d.multiline_text((x+36,y0+195),s,font=F(32,400),fill='#555',spacing=10)
    if i<3:
        ax=x+bw+14; ay=y0+bh//2
        d.line([ax,ay,ax+gap-40,ay],fill='#1b1b1b',width=8)
        d.polygon([(ax+gap-40,ay-20),(ax+gap-40,ay+20),(ax+gap-8,ay)],fill='#1b1b1b')
d.text((x0,y0+bh+70),'Result so far: 115/115 read backs clean, 0 leaked facts',font=F(40,700),fill='#2a9d8f')
d.text((x0,y0+bh+130),'Weak spot: identity/permission and meaning flips (pgvector ignores who asks, and cannot answer "no longer")',font=F(30,400),fill='#6b6b6b')
im.save('whiteboard_pgvector_jml.png')
