"""Split one osu map into our three difficulties.

The map maker already decided where the notes go, so we do not invent any.
We only thin: normal keeps the beat, heroic adds the half beat, mythic is
the map as charted.
"""
import sys, io, os
sys.path.insert(0, r'C:/Users/krist/shaiyex/tools')
from osu2chart import convert, as_chart
from collections import Counter

def split(ch, beat):
    def frac(b): return b % 1
    def near(x, target, tol=0.06): return abs(x - target) < tol or abs(x - target) > 1 - tol
    normal, heroic = [], []
    lastN = lastH = -99
    for b, l in ch:
        f = frac(b)
        onbeat = near(f, 0.0)
        onhalf = near(f, 0.5)
        if onbeat and (b - lastN) * beat >= 0.33:
            normal.append((b, l)); lastN = b
        if (onbeat or onhalf) and (b - lastH) * beat >= 0.16:
            heroic.append((b, l)); lastH = b
    return normal, heroic, ch

def report(name, arr, beat):
    times = sorted(set(b for b, _ in arr))
    gaps = [(times[i+1]-times[i])*beat*1000 for i in range(len(times)-1)]
    lanes = Counter(l for _, l in arr)
    per = {}
    last = {}
    for b, l in arr:
        if l in last: per[l] = min(per.get(l, 9e9), (b - last[l]) * beat * 1000)
        last[l] = b
    span = (times[-1]-times[0])*beat
    print("  %-7s %4d notes  %.2f/s  shortest gap %3.0f ms  same lane min %3.0f ms  lanes %s"
          % (name, len(arr), len(arr)/span, min(gaps), min(per.values()),
             [lanes[i] for i in range(4)]))

if __name__ == "__main__":
    src = sys.argv[1]; prefix = sys.argv[2]
    r = convert(src)
    ch = as_chart(r)
    n, h, m = split(ch, r["beat"])
    print("from %s  (%.3f BPM, offset %.3f s)" % (os.path.basename(src), r["bpm"], r["zero"]))
    for nm, arr in (("normal", n), ("heroic", h), ("mythic", m)):
        report(nm, arr, r["beat"])
        io.open(r'C:/Users/krist/shaiyex/tools/charts/%s_%s.txt' % (prefix, nm[0].upper()),
                'w', encoding='utf-8').write(",".join("[%g,%d]" % (b, l) for b, l in arr))
    last = max(b for b, _ in ch)
    print("  last note at %.1f s" % (r["zero"] + last * r["beat"]))
