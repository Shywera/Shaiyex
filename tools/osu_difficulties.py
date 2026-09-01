"""Split one osu map into our three difficulties.

The map maker already decided where the notes go, so we invent nothing.
We only thin: normal keeps the beat, heroic adds the half beat, mythic is
the map as charted. Charts are written in seconds.
"""
import sys, io, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from osu2chart import convert, beat_pos
from collections import Counter

CHARTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "charts")


def split(notes, tp):
    def near(x, target, tol=0.08):
        d = abs((x % 1) - target)
        return d < tol or d > 1 - tol
    normal, heroic = [], []
    lastN = lastH = -99.0
    for t, l in notes:
        b = beat_pos(t, tp)
        onbeat = near(b, 0.0)
        onhalf = near(b, 0.5)
        if onbeat and t - lastN >= 0.33:
            normal.append((t, l)); lastN = t
        if (onbeat or onhalf) and t - lastH >= 0.16:
            heroic.append((t, l)); lastH = t
    return normal, heroic, list(notes)


def report(name, arr):
    times = sorted(set(t for t, _ in arr))
    if len(times) < 2:
        print("  %-7s %4d notes" % (name, len(arr))); return
    gaps = [times[i + 1] - times[i] for i in range(len(times) - 1)]
    lanes = Counter(l for _, l in arr)
    per, last = {}, {}
    for t, l in arr:
        if l in last:
            per[l] = min(per.get(l, 9e9), t - last[l])
        last[l] = t
    span = times[-1] - times[0]
    print("  %-7s %4d notes  %.2f/s  gap %3.0f ms  same lane %3.0f ms  lanes %s"
          % (name, len(arr), len(arr) / span, min(gaps) * 1000,
             min(per.values()) * 1000 if per else 0, [lanes[i] for i in range(4)]))


if __name__ == "__main__":
    src, prefix = sys.argv[1], sys.argv[2]
    diff = sys.argv[sys.argv.index("--diff") + 1] if "--diff" in sys.argv else None
    r = convert(src, diff)
    n, h, m = split(r["notes"], r["tp"])
    print("%s  %.2f BPM, %d timing section%s"
          % (r["file"], r["bpm"], len(r["tp"]), "" if len(r["tp"]) == 1 else "s"))
    for nm, arr in (("normal", n), ("heroic", h), ("mythic", m)):
        report(nm, arr)
        io.open(os.path.join(CHARTS, "%s_%s.txt" % (prefix, nm[0].upper())),
                "w", encoding="utf-8").write(",".join("[%g,%d]" % (t, l) for t, l in arr))
    print("  last note %.1f s" % max(t for t, _ in r["notes"]))
