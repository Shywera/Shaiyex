"""
Turn an osu! beatmap into a chart for /beat/.

Works with:
  .osu   a single difficulty
  .osz   the packaged map, picks the difficulty you name or the busiest one

osu!mania maps are ideal: the columns are already there, so the lanes come
straight from the map maker rather than from me guessing. Standard, taiko and
catch maps still work, we take the hit times and lay the lanes out with hand
alternation, same rules the generated charts use.

Usage:
  python osu2chart.py <file.osu|file.osz> [--diff "name"] [--out chart.txt]
"""
import sys, os, re, zipfile, io, random
from collections import defaultdict


def read_osu(text):
    sec, out = None, defaultdict(list)
    meta = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("//"):
            continue
        if line.startswith("[") and line.endswith("]"):
            sec = line[1:-1]
            continue
        if sec in ("General", "Metadata", "Difficulty", "Editor"):
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
        elif sec in ("TimingPoints", "HitObjects"):
            out[sec].append(line)
    return meta, out


def timing(points):
    """uninherited points only: (time_ms, ms_per_beat)"""
    res = []
    for line in points:
        p = line.split(",")
        if len(p) < 2:
            continue
        try:
            t = float(p[0]); beat = float(p[1])
        except ValueError:
            continue
        uninherited = True
        if len(p) >= 7:
            uninherited = p[6].strip() == "1"
        elif beat < 0:
            uninherited = False
        if uninherited and beat > 0:
            res.append((t, beat))
    res.sort()
    return res


def hit_objects(lines, mode, keys):
    """returns [(time_seconds, column_or_None)]"""
    notes = []
    for line in lines:
        p = line.split(",")
        if len(p) < 4:
            continue
        try:
            x = float(p[0]); t = float(p[2])
        except ValueError:
            continue
        col = None
        if mode == 3 and keys:
            col = int(x * keys / 512)
            col = max(0, min(keys - 1, col))
        notes.append((t / 1000.0, col))
        # mania hold notes: the tail is in p[5] before the colon. we only
        # want the press, so the tail is deliberately ignored.
    notes.sort(key=lambda n: n[0])
    return notes


def to_four(notes, keys):
    """map however many mania columns onto our four lanes"""
    if not keys or keys == 4:
        return notes
    out = []
    for t, c in notes:
        out.append((t, None if c is None else min(3, int(c * 4 / keys))))
    return out


def assign_lanes(notes, minjack=0.27, seed=7):
    """for maps with no columns: alternate hands, never jack a finger too fast"""
    random.seed(seed)
    pattern = [0, 2, 1, 3, 1, 2, 0, 3]
    last = {0: -99, 1: -99, 2: -99, 3: -99}
    out, i = [], 0
    for t, c in notes:
        if c is not None:
            out.append((t, c)); last[c] = t; continue
        want = pattern[i % len(pattern)]
        lane = want
        for l in [want] + [x for x in (0, 1, 2, 3) if x != want]:
            if t - last[l] >= minjack:
                lane = l; break
        out.append((t, lane)); last[lane] = t; i += 1
    return out


def dedupe(notes, max_chord=2):
    by, res = defaultdict(list), []
    for t, l in sorted(notes):
        k = round(t, 4)
        if len(by[k]) >= max_chord or l in by[k]:
            continue
        by[k].append(l); res.append((k, l))
    return res


def convert(path, diff=None):
    if path.lower().endswith(".osz"):
        z = zipfile.ZipFile(path)
        cands = [n for n in z.namelist() if n.lower().endswith(".osu")]
        if not cands:
            raise SystemExit("no .osu inside that .osz")
        pick = None
        if diff:
            for n in cands:
                if diff.lower() in n.lower():
                    pick = n; break
        if not pick:
            # the busiest difficulty is usually the one worth charting
            pick = max(cands, key=lambda n: len(z.read(n).decode("utf-8", "ignore")))
        text = z.read(pick).decode("utf-8", "ignore")
        name = pick
    else:
        text = io.open(path, encoding="utf-8", errors="ignore").read()
        name = os.path.basename(path)

    meta, sec = read_osu(text)
    mode = int(float(meta.get("Mode", 0)))
    keys = int(float(meta.get("CircleSize", 4))) if mode == 3 else 0
    tp = timing(sec["TimingPoints"])
    if not tp:
        raise SystemExit("no uninherited timing point, cannot read the grid")
    offset_ms, mspb = tp[0]
    bpm = 60000.0 / mspb

    notes = hit_objects(sec["HitObjects"], mode, keys)
    notes = to_four(notes, keys)
    notes = assign_lanes(notes)
    notes = dedupe(notes)

    return {
        "file": name,
        "audio": meta.get("AudioFilename", "?"),
        "title": meta.get("Title", "?"),
        "version": meta.get("Version", "?"),
        "mode": {0: "standard", 1: "taiko", 2: "catch", 3: "mania"}.get(mode, mode),
        "keys": keys,
        "bpm": bpm,
        "beat": mspb / 1000.0,
        "zero": offset_ms / 1000.0,
        "timing_points": len(tp),
        "notes": notes,
    }


def as_chart(res):
    """our format is [beat, lane], beat measured from the map's own offset"""
    BEAT, ZERO = res["beat"], res["zero"]
    out = []
    for t, l in res["notes"]:
        b = (t - ZERO) / BEAT
        if b < -0.5:
            continue
        out.append((round(max(0.0, b), 4), l))
    return out


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        raise SystemExit(__doc__)
    src = args[0]
    diff = None; out = None
    if "--diff" in args: diff = args[args.index("--diff") + 1]
    if "--out"  in args: out  = args[args.index("--out") + 1]

    r = convert(src, diff)
    ch = as_chart(r)
    lanes = [sum(1 for _, l in ch if l == i) for i in range(4)]
    times = sorted(set(b for b, _ in ch))
    gaps = [(times[i + 1] - times[i]) * r["beat"] for i in range(len(times) - 1)]

    print("map      :", r["file"])
    print("title    :", r["title"], "[" + r["version"] + "]")
    print("audio    :", r["audio"])
    print("mode     :", r["mode"], ("%dK" % r["keys"]) if r["keys"] else "")
    print("bpm      : %.3f   beat %.5f s   offset %.3f s   (%d timing points)"
          % (r["bpm"], r["beat"], r["zero"], r["timing_points"]))
    print("notes    : %d   lanes %s   shortest gap %.0f ms"
          % (len(ch), lanes, (min(gaps) * 1000) if gaps else 0))
    if r["timing_points"] > 1:
        print("note     : the map has more than one timing point, so the tempo")
        print("           changes. our engine assumes one grid, tell me if this")
        print("           map actually changes speed part way through.")
    if out:
        io.open(out, "w", encoding="utf-8").write(
            ",".join("[%g,%d]" % (b, l) for b, l in ch))
        print("written  :", out)
