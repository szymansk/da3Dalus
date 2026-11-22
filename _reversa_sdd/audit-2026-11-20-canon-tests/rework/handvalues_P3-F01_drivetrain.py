import json, math, bisect
T=json.load(open('/Users/szymanski/Projects/da3Dalus/cad-modelling-service/aero_kernel/reference/powertrain/apc_13x8e.json'))['table']
B=T['blocks']
RHO,D,U,KV,I0,RM=1.225,13*0.0254,14.8,900.0,1.2,0.082
KVR=2*math.pi*KV/60
def interp1(x,xs,ys):
    if x<xs[0] or x>xs[-1]: raise ValueError(('out',x,xs[0],xs[-1]))
    i=max(1,bisect.bisect_left(xs,x)); i=min(i,len(xs)-1)
    t=(x-xs[i-1])/(xs[i]-xs[i-1]); return ys[i-1]+t*(ys[i]-ys[i-1])
def coef(rpm,j):
    rp=[b['rpm'] for b in B]
    return (interp1(rpm,rp,[interp1(j,b['j'],b['ct']) for b in B]), interp1(rpm,rp,[interp1(j,b['j'],b['cp']) for b in B]))
def resid(rpm,v):
    n=rpm/60; ct,cp=coef(rpm,v/(n*D))
    qp=cp*RHO*n*n*D**5/(2*math.pi)
    I=(U-2*math.pi*n/KVR)/RM
    return (I-I0)/KVR-qp
def tfull(v):
    lo,hi=B[0]['rpm'],min(KV*U,B[-1]['rpm'])
    # scan for sign change
    xs=[lo+(hi-lo)*i/400 for i in range(401)]
    prev=None; root=None
    for x in xs:
        try: r=resid(x,v)
        except ValueError: prev=None; continue
        if prev is not None and prev[1]>0>=r:
            a,b=prev[0],x
            for _ in range(100):
                m=(a+b)/2
                if resid(m,v)>0:a=m
                else:b=m
            root=(a+b)/2
        prev=(x,r)
    if root is None: return None
    n=root/60; ct,cp=coef(root,v/(n*D)); return root, ct*RHO*n*n*D**4, v/(n*D)
if __name__=='__main__':
    print('rpm blocks',[b['rpm'] for b in B][:3],'...',B[-1]['rpm'],'Jmax',[max(b['j']) for b in B][:3])
    for v in [0,6,10,15,19,20,22,25,30,35,40,42,43,43.3,44,45,50]:
        r=tfull(v); 
        print(v, r and tuple(round(x,3) for x in r), 'D1=%.2f'%(0.06*v*v), 'D2=%.3f'%(9000/v/v if v else 0))
