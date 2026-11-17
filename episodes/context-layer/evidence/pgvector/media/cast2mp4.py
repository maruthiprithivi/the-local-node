import json,sys,subprocess,os,shutil
import pyte
from PIL import Image,ImageDraw,ImageFont
cast,out=sys.argv[1],sys.argv[2]
lines=open(cast).read().splitlines(); hdr=json.loads(lines[0]); W,H=hdr['width'],hdr['height']
ev=[json.loads(l) for l in lines[1:]]
f=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',21)
fb=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf',21)
cw,ch=1920/ W, 1080/H
screen=pyte.Screen(W,H); st=pyte.Stream(screen)
pal={'default':None,'black':'#1e1e2e','red':'#f38ba8','green':'#a6e3a1','brown':'#f9e2af','blue':'#89b4fa','magenta':'#cba6f7','cyan':'#94e2d5','white':'#cdd6f4','brightblack':'#6c7086'}
def col(c,d):
    if c=='default': return d
    if c in pal and pal[c]: return pal[c]
    if len(c)==6: return '#'+c
    return d
def render(path):
    im=Image.new('RGB',(1920,1080),'#11111b'); d=ImageDraw.Draw(im)
    for y in range(H):
        for x in range(W):
            c=screen.buffer[y][x]
            if c.data!=' ' :
                d.text((x*cw,y*ch+2),c.data,font=fb if c.bold else f,fill=col(c.fg,'#cdd6f4'))
    im.save(path)
shutil.rmtree('fr',ignore_errors=True); os.mkdir('fr')
times=[];n=0;last=0
def snap(t):
    global n
    render(f'fr/{n:05d}.png'); times.append(t); n+=1
step=0.15; nextsnap=0
for t,k,d in ev:
    if k!='o': continue
    st.feed(d)
    if t>=nextsnap:
        snap(t); nextsnap=t+step
snap(ev[-1][0]+0.1); snap(ev[-1][0]+3)
with open('fr/list.txt','w') as l:
    for i in range(len(times)):
        dur=(times[i+1]-times[i]) if i+1<len(times) else 1
        l.write(f"file '{i:05d}.png'\nduration {max(dur,0.04):.3f}\n")
    l.write(f"file '{len(times)-1:05d}.png\n".replace('.png\n',".png'\n"))
subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-i','fr/list.txt','-vf','fps=10,format=yuv420p','-c:v','libx264','-crf','20',out],check=True)
# final frame png for screenshot
shutil.copy(f'fr/{n-1:05d}.png',out.replace('.mp4','_last.png'))
