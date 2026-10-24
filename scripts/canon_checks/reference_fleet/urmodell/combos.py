"""All-typical combinations of the Urmodell selection graph (auswahl.json), 2026-10-03."""

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[4]
D = json.loads((ROOT / "_reversa_sdd" / "calculations" / "auswahl" / "auswahl.json").read_text())
S = {s["id"]: s for s in D["schritte"]}
B = D["bewertung"]


def _holds(c, p):
    return all((p.get(k) in v) if isinstance(v, list) else p.get(k) == v for k, v in c.items())


def _ok(o, p):
    return (not o.get("wenn") or _holds(o["wenn"], p)) and not any(
        p.get(k) in v for k, v in (o.get("wenn_nicht") or {}).items())


def rating(o, p):
    if o.get("typisch_immer"):
        return "T"
    r = B.get(p["mission"], {}).get(o.get("bewertung_von") or o["id"])
    return r or ("T" if p["mission"] in (o.get("typisch") or []) else "P")


def combos(only_typical=True):
    out = []
    for mo in S["motor"]["optionen"]:
        p0 = {"motor": mo["id"]}
        for mi in (o for o in S["mission"]["optionen"] if _ok(o, p0)):
            p1 = dict(p0, mission=mi["id"])
            for tr in S["trag"]["optionen"]:
                p2 = dict(p1, trag=tr["id"])
                r2 = rating(tr, p2)
                lagen = S["lage"]["optionen"] if tr["id"] == "eindecker" else [None]
                for la in lagen:
                    p3 = dict(p2, lage=la["id"] if la else None)
                    r3 = rating(la, p3) if la else "T"
                    for lw in (o for o in S["leitwerk"]["optionen"] if _ok(o, p3)):
                        p4 = dict(p3, leitwerk=lw["id"])
                        r4 = rating(lw, p4)
                        for st in (o for o in S["steuerung"]["optionen"] if _ok(o, p4)):
                            p5 = dict(p4, steuerung=st["id"])
                            rs = (r2, r3, r4, rating(st, p5))
                            if "N" in rs or (only_typical and any(r != "T" for r in rs)):
                                continue
                            out.append(p5)
    return out


if __name__ == "__main__":
    import collections
    c = combos()
    print(len(c))
    for m, n in collections.Counter(x["mission"] for x in c).items():
        print(m, n, sorted({(x["trag"], str(x["lage"]), x["leitwerk"], x["steuerung"]) for x in c if x["mission"] == m}))
