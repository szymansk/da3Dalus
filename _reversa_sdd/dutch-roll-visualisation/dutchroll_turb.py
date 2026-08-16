"""Dutch roll under CONTINUOUS turbulence — the case a pilot actually reports.

The free-decay render answers "how fast does one gust settle?". In gusty air the
mode is re-excited before it settles, so the aircraft never stops moving and the
pilot judges *sustained amplitude*, not decay time.

Same zeta governs both, but it enters differently: a lightly damped mode is a
narrow-band resonant filter on the turbulence spectrum, so RMS response grows
roughly as 1/sqrt(zeta). That is why "it just keeps wallowing" is a damping
complaint even though nothing looks like a decaying transient.

    psi_ddot + 2*zeta*wn*psi_dot + wn^2*psi = wn^2 * w(t)

w(t) = band-limited random gust (first-order filtered white noise). Roll follows
the mode shape: phi = roll_ratio * psi delayed by chi degrees at wd (valid because
the response is narrow-band around wd).
"""
import math, sys, random
sys.path.insert(0, __import__("os").path.dirname(__file__))
from dutchroll_fpv import render_frame, FPS, Image

DUR = 12.0

def simulate(zeta, wn, gust_rms_deg, seed, fps=FPS, tau_gust=0.35):
    rnd = random.Random(seed)
    n = int(fps*DUR); dt = 1.0/fps
    a = math.exp(-dt/tau_gust)
    w = 0.0; psi = 0.0; psid = 0.0
    out = []
    # burn-in so the record starts already in steady state, not from rest
    for k in range(-int(6*fps), n):
        w = a*w + math.sqrt(1-a*a)*rnd.gauss(0, 1)
        psidd = wn*wn*(gust_rms_deg*w) - 2*zeta*wn*psid - wn*wn*psi
        psid += psidd*dt; psi += psid*dt
        if k >= 0: out.append(psi)
    return out

def make(path, zeta, wn=5.0, roll_ratio=1.5, chi_deg=110.0, fov=139.0,
         gust_rms_deg=2.2, seed=7):
    psi = simulate(zeta, wn, gust_rms_deg, seed)
    wd = wn*math.sqrt(max(1e-6, 1-zeta**2))
    lag = int(round((math.radians(chi_deg)/wd)*FPS))   # phase -> frames at wd
    frames = []
    peak = max(abs(p) for p in psi)
    for k in range(len(psi)):
        phi = roll_ratio*psi[max(0, k-lag)]
        frames.append(render_frame(psi[k], phi, 0.0, fov,
                      f"zeta={zeta:.3f}  T={2*math.pi/wn:.1f}s  roll/yaw={roll_ratio:.1f}"))
    pal = frames[0].convert("P", palette=Image.Palette.ADAPTIVE, colors=48)
    frames = [f.quantize(palette=pal, dither=Image.Dither.NONE) for f in frames]
    frames[0].save(path, save_all=True, append_images=frames[1:],
                   duration=int(1000/FPS), loop=0, optimize=True)
    rms = math.sqrt(sum(p*p for p in psi)/len(psi))
    return rms, peak

if __name__ == "__main__":
    out, z = sys.argv[1], float(sys.argv[2])
    wn = float(sys.argv[3]) if len(sys.argv) > 3 else 5.0
    rr = float(sys.argv[4]) if len(sys.argv) > 4 else 1.5
    rms, peak = make(out, z, wn=wn, roll_ratio=rr)
    print(f"{out}  zeta={z} wn={wn} roll/yaw={rr}  T={2*math.pi/wn:.2f}s  "
          f"yaw RMS={rms:.2f} peak={peak:.2f} deg  ->  roll peak={rr*peak:.1f} deg")
