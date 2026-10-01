import numpy as np, aerosandbox as asb
m, g = 1.5, 9.81
af = asb.Airfoil("naca2412")
wing = asb.Wing(name="Main Wing", symmetric=True, xsecs=[
    asb.WingXSec(xyz_le=[0,0,0], chord=0.20, airfoil=af),
    asb.WingXSec(xyz_le=[0,0.70,0], chord=0.20, airfoil=af)])
plane = asb.Airplane(name="rc-trainer", xyz_ref=[0.05,0,0], wings=[wing])
atm = asb.Atmosphere(altitude=0)

def opt(objective):
    o=asb.Opti()
    V=o.variable(init_guess=12, lower_bound=2, upper_bound=40)
    a=o.variable(init_guess=5, lower_bound=-5, upper_bound=25)
    r=asb.AeroBuildup(plane, asb.OperatingPoint(atm, velocity=V, alpha=a)).run()
    o.subject_to(r["L"]==m*g)
    o.minimize({"V":V, "D":r["D"], "DV":r["D"]*V}[objective])
    s=o.solve(verbose=False)
    return s(V), s(a), s(r["CL"]/r["CD"]), s(r["D"]*V/(m*g))

# Gegenprobe ueber einen dichten Geschwindigkeitssweep mit L = W je Punkt
def sweep():
    Vs=np.linspace(8.6,25,400); best=[]
    for V in Vs:
        al=np.linspace(-4,16,161)
        r=asb.AeroBuildup(plane, asb.OperatingPoint(atm, velocity=np.full_like(al,V), alpha=al)).run()
        L=np.asarray(r["L"]); i=np.argmin(abs(L-m*g))
        best.append((V, float(np.asarray(r["D"])[i])))
    b=np.array(best)
    return b[np.argmin(b[:,1]),0], b[np.argmin(b[:,1]*b[:,0]),0]

for name,key in (("Abriss V_S","V"),("bestes Gleiten V_md","D"),("geringstes Sinken V_mp","DV")):
    V,a,E,w=opt(key)
    print(f"{name:24s} V = {V:7.3f} m/s   alpha = {a:6.2f} deg   E = {E:5.2f}   w = {w:5.3f} m/s")
vmd, vmp = sweep()
print(f"\nSweep-Gegenprobe:  V_md = {vmd:.3f}   V_mp = {vmp:.3f}   (Raster 0,04 m/s)")
