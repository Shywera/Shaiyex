import json, math, struct, sys
SP=r"C:/Users/krist/AppData/Local/Temp/claude/C--Users-krist/717ac1b9-c394-4b2a-80e8-1f8722b59f0f/scratchpad"
d=open(SP+"/fur.pcm","rb").read(); n=len(d)//2
s=struct.unpack("<%dh"%n,d); SR=22050; H=256; N=1024
w=[0.5-0.5*math.cos(2*math.pi*i/N) for i in range(N)]
def fft(a):
    L=len(a)
    if L==1: return a
    ev=fft(a[0::2]); od=fft(a[1::2]); out=[0]*L
    for k in range(L//2):
        t=complex(math.cos(-2*math.pi*k/L),math.sin(-2*math.pi*k/L))*od[k]
        out[k]=ev[k]+t; out[k+L//2]=ev[k]-t
    return out
prev=None; f=[]
for i in range(0,n-N,H):
    fr=[s[i+j]/32768.0*w[j] for j in range(N)]
    sp=[abs(x) for x in fft([complex(v,0) for v in fr])[:N//2]]
    if prev is not None: f.append(sum(max(0.0,sp[k]-prev[k]) for k in range(len(sp))))
    prev=sp
fps=SR/H; m=sum(f)/len(f); f=[max(0.0,x-m) for x in f]
def sc(per,ph,t0,t1):
    tot=0;c=0
    for k in range(int(math.ceil((t0-ph)/per)), int((t1-ph)/per)):
        i=int(round((ph+k*per)*fps))
        if 0<i<len(f)-1: tot+=max(f[i-1],f[i],f[i+1]); c+=1
    return tot/c if c else 0
PER=60.0/155.0
best=None; ph=0.0
while ph<PER:
    v=sc(PER,ph,10,300)
    if best is None or v>best[1]: best=(ph,v)
    ph+=0.0005
print("map says   : beat %.5f s, offset 1.652 s"%PER)
print("audio says : best phase %.4f s  (map offset mod beat = %.4f)"%(best[0], 1.652 % PER))
print("difference : %.0f ms"%(abs(best[0]-(1.652%PER))*1000))
