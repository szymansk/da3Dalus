"""Pseudo-FPV rendering of a dutch-roll disturbance response.

The point is calibration: the pilot judges the *stimulus*, not a number.
So the motion must be the real mode shape and the camera must behave like an
FPV camera, otherwise the threshold that comes back is against the wrong thing.

Mode shape (damped free response to a gust):
    psi(t) = psi0 * exp(-zeta*wn*t) * sin(wd*t)
    phi(t) = roll_ratio * psi0 * exp(-zeta*wn*t) * sin(wd*t + chi)
    wd     = wn * sqrt(1 - zeta^2)

`roll_ratio` and `chi` are the roll/yaw amplitude ratio and phase that make a
dutch roll a *coupled* oscillation rather than a plain yaw wobble. They are
explicit parameters, not hidden constants — challenge them.

Camera: pinhole, body-fixed, distant scene. Yaw pans, pitch tilts, roll rotates
the whole image. Focal length follows from the horizontal FOV, which is why FOV
changes the perceived severity at constant attitude.
"""

import math
from PIL import Image, ImageDraw

W, H = 448, 252
FPS = 25
DURATION_S = 4.0

SKY_TOP = (92, 148, 205)
SKY_HORIZON = (176, 208, 232)
GROUND_NEAR = (104, 122, 68)
GROUND_FAR = (150, 158, 112)
POLE = (58, 52, 44)
OSD = (235, 235, 235)


def render_frame(psi_deg, phi_deg, theta_deg, fov_deg, label=None):
    """One FPV frame. Scene is at infinity: yaw/pitch pan, roll rotates."""
    big = int(math.hypot(W, H)) + 40
    img = Image.new("RGB", (big, big), SKY_TOP)
    d = ImageDraw.Draw(img)

    f = (W / 2) / (math.radians(fov_deg) / 2)  # equidistant: px per radian
    cx, cy = big / 2, big / 2

    # Horizon offset from pitch only; roll is applied by rotating the canvas.
    horizon_y = cy + f * math.radians(theta_deg)
    pan_x = -f * math.radians(psi_deg)

    # Sky gradient
    for y in range(0, int(horizon_y)):
        t = max(0.0, min(1.0, y / max(1.0, horizon_y)))
        c = tuple(int(SKY_TOP[i] + (SKY_HORIZON[i] - SKY_TOP[i]) * t) for i in range(3))
        d.line([(0, y), (big, y)], fill=c)
    # Ground gradient
    for y in range(int(horizon_y), big):
        t = max(0.0, min(1.0, (y - horizon_y) / max(1.0, big - horizon_y)))
        c = tuple(int(GROUND_FAR[i] + (GROUND_NEAR[i] - GROUND_FAR[i]) * t) for i in range(3))
        d.line([(0, y), (big, y)], fill=c)

    d.line([(0, horizon_y), (big, horizon_y)], fill=(70, 90, 70), width=2)

    # Ground objects at fixed world azimuths -> horizontal position follows yaw.
    # Height above horizon encodes distance (nearer = taller).
    objects = [(-38, 46), (-22, 30), (-9, 62), (6, 34), (19, 54), (33, 28), (48, 44)]
    for az_deg, height_px in objects:
        x = cx + pan_x + f * math.radians(az_deg)
        if -60 < x - cx < big + 60:
            d.rectangle([x - 2, horizon_y - height_px, x + 2, horizon_y], fill=POLE)
            d.ellipse(
                [x - 7, horizon_y - height_px - 7, x + 7, horizon_y - height_px + 3],
                fill=(46, 78, 44),
            )

    # A path converging to the horizon: the strongest roll cue in the scene.
    vp_x = cx + pan_x
    d.polygon(
        [(vp_x - 3, horizon_y), (vp_x + 3, horizon_y),
         (vp_x + 130, big), (vp_x - 130, big)],
        fill=(168, 156, 132),
    )

    img = img.rotate(-phi_deg, resample=Image.Resampling.BICUBIC, center=(cx, cy))
    img = img.crop((int(cx - W / 2), int(cy - H / 2), int(cx + W / 2), int(cy + H / 2)))

    # Fixed OSD frame — in FPV the frame is still and the world moves.
    d2 = ImageDraw.Draw(img)
    d2.rectangle([2, 2, W - 3, H - 3], outline=OSD, width=2)
    d2.line([(W / 2 - 26, H / 2), (W / 2 - 8, H / 2)], fill=OSD, width=2)
    d2.line([(W / 2 + 8, H / 2), (W / 2 + 26, H / 2)], fill=OSD, width=2)
    d2.line([(W / 2, H / 2 - 6), (W / 2, H / 2 + 6)], fill=OSD, width=2)
    if label:
        d2.text((10, H - 20), label, fill=OSD)
    return img


def make_gif(path, zeta, wn=5.0, psi0_deg=9.0, roll_ratio=1.5, chi_deg=110.0,
             fov_deg=155.0, label=None):
    wd = wn * math.sqrt(max(1e-6, 1 - zeta**2))
    n = int(FPS * DURATION_S)
    frames = []
    for k in range(n):
        t = k / FPS
        env = math.exp(-zeta * wn * t)
        psi = psi0_deg * env * math.sin(wd * t)
        phi = roll_ratio * psi0_deg * env * math.sin(wd * t + math.radians(chi_deg))
        frames.append(render_frame(psi, phi, 0.0, fov_deg, label))
    pal = frames[0].convert("P", palette=Image.Palette.ADAPTIVE, colors=48)
    frames = [f.quantize(palette=pal, dither=Image.Dither.NONE) for f in frames]
    frames[0].save(path, save_all=True, append_images=frames[1:],
                   duration=int(1000 / FPS), loop=0, optimize=True)
    return path


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "dutchroll.gif"
    zeta = float(sys.argv[2]) if len(sys.argv) > 2 else 0.115
    fov = float(sys.argv[3]) if len(sys.argv) > 3 else 155.0
    make_gif(out, zeta=zeta, fov_deg=fov,
             label=f"zeta={zeta:.3f}  T={2*math.pi/5.0:.2f}s  FOV={fov:.0f}deg h")
    print("wrote", out)
