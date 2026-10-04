"""Isometric renders of the Urmodell fleet (fleet/*.airplane.json -> renders/<id>.png), 2026-10-04."""

import json
import multiprocessing as mp
import pathlib

HERE = pathlib.Path(__file__).parent
OUT = HERE / "renders"


def render(path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    import fleet_eval as fe

    d = json.loads(path.read_text())
    plane = fe.asb_plane(d)
    pts, faces = plane.mesh_body(method="quad")
    pts = np.asarray(pts)
    P = pts
    fig = plt.figure(figsize=(4, 3.2), dpi=110)
    ax = fig.add_subplot(projection="3d", proj_type="ortho")
    poly = Poly3DCollection([P[f] for f in faces], facecolor="#c9ccd3", edgecolor="none", linewidths=0)
    # simple shading by face normal
    n = np.cross(P[faces[:, 1]] - P[faces[:, 0]], P[faces[:, 2]] - P[faces[:, 0]])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    light = np.array([-0.4, -0.5, 0.75])
    light /= np.linalg.norm(light)
    s = 0.45 + 0.55 * np.abs(n @ light)
    poly.set_facecolor(np.c_[0.95 * s, 0.6 * s + 0.1, 0.25 * s, np.ones_like(s)])
    ax.add_collection3d(poly)
    lo, hi = P.min(0), P.max(0)
    ax.set_xlim(lo[0], hi[0])
    ax.set_ylim(lo[1], hi[1])
    ax.set_zlim(lo[2], hi[2])
    ax.set_box_aspect(hi - lo, zoom=1.0)  # equal scale on all axes
    ax.view_init(elev=35.264, azim=-135)  # isometric, from front-left above (ASB x points aft)
    ax.set_axis_off()
    fig.subplots_adjust(0, 0, 1, 1)
    fig.savefig(OUT / f"{d['name']}.png", transparent=True)
    plt.close(fig)
    return d["name"]


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    files = sorted((HERE / "fleet").glob("*.airplane.json"))
    with mp.get_context("spawn").Pool(6) as pool:
        for n in pool.imap_unordered(render, files):
            print(n, flush=True)
