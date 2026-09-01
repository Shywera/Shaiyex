"""
Turn an osu! beatmap into a chart for /beat/.

Charts are stored in SECONDS, not beats. osu maps are allowed to change
tempo part way through and several of them do, so a single beat length
cannot describe the whole song. The beat position is still computed, using
whichever timing point is in effect at that moment, but only so the
difficulty split can tell an on beat note from an off beat one.

  .osu   a single difficulty
  .osz   the package, picks the difficulty you name or the busiest one
  folder picks the busiest .osu inside

Usage:
  python osu2chart.py <file.osu|file.osz|folder> [--diff "name"] [--out chart.txt]
"""
import sys, os, io, re, zipfile, random, glob
from collections import defaultdict


def read_osu(text):
    sec, out, meta = None, defaultdict(list), {}
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
    """uninherited points only, as (time_seconds, seconds_per_beat)"""
    res = []
    for line in points:
        p = line.split(",")
        if len(p) < 2:
            continue
        try:
            t = float(p[0]); beat = float(p[1])
        except ValueError:
            continue
        uninherited = p[6].strip() == "1" if len(p) >= 7 else beat > 0
        if uninherited and beat > 0:
            res.append((t / 1000.0, beat / 1000.0))
    res.sort()
    # collapse points that do not actually change the tempo
    out = []
    for t, b in res:
        if not out or abs(out[-1][1] - b) > 1e-9:
            out.append((t, b))
    return out


def beat_pos(t, tp):
    """where t sits on the grid, as a beat number within its timing section"""
    seg = tp[0]
    for p in tp:
        if p[0] <= t + 1e-9:
            seg = p
        else:
            break
    return (t - seg[0]) / seg[1]


def hit_objects(lines, mode, keys):
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
            col = max(0, min(keys - 1, int(x * keys / 512)))
        notes.append((t / 1000.0, col))
    notes.sort(key=lambda n: n[0])
    return notes


def to_four(notes, keys):
    if not keys or keys == 4:
        return notes
    return [(t, None if c is None else min(3, int(c * 4 / keys))) for t, c in notes]


def assign_lanes(notes, minjack=0.27, seed=7):
    """maps without columns: alternate hands, never jack one finger too fast"""
    random.seed(seed)
    pattern = [0, 2, 1, 3, 1, 2, 0, 3]
    last = {0: -99.0, 1: -99.0, 2: -99.0, 3: -99.0}
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


def pick_source(path, diff=None):
    """returns (text, label)"""
    if os.path.isdir(path):
        cands = glob.glob(os.path.join(path, "**", "*.osu"), recursive=True)
        if not cands:
            raise SystemExit("no .osu under " + path)
        if diff:
            m = [c for c in cands if diff.lower() in os.path.basename(c).lower()]
            if m:
                cands = m
        pick = max(cands, key=lambda c: io.open(c, encoding="utf-8", errors="ignore").read().count("\n"))
        return io.open(pick, encoding="utf-8", errors="ignore").read(), os.path.basename(pick)
    if path.lower().endswith(".osz"):
        z = zipfile.ZipFile(path)
        cands = [n for n in z.namelist() if n.lower().endswith(".osu")]
        if not cands:
            raise SystemExit("no .osu inside that .osz")
        if diff:
            m = [n for n in cands if diff.lower() in n.lower()]
            if m:
                cands = m
        pick = max(cands, key=lambda n: len(z.read(n)))
        return z.read(pick).decode("utf-8", "ignore"), pick
    return io.open(path, encoding="utf-8", errors="ignore").read(), os.path.basename(path)


def convert(path, diff=None):
    text, label = pick_source(path, diff)
    meta, sec = read_osu(text)
    mode = int(float(meta.get("Mode", 0)))
    keys = int(float(meta.get("CircleSize", 4))) if mode == 3 else 0

    tp = timing(sec["TimingPoints"])
    if not tp:
        raise SystemExit("no uninherited timing point in " + label)

    notes = dedupe(assign_lanes(to_four(hit_objects(sec["HitObjects"], mode, keys), keys)))

    return {
        "file": label,
        "audio": meta.get("AudioFilename", "?"),
        "title": meta.get("Title", "?"),
        "artist": meta.get("Artist", "?"),
        "version": meta.get("Version", "?"),
        "mode": {0: "standard", 1: "taiko", 2: "catch", 3: "mania"}.get(mode, mode),
        "keys": keys,
        "tp": tp,
        "bpm": 60.0 / tp[0][1],
        "beat": tp[0][1],
        "zero": tp[0][0],
        "notes": notes,          # (seconds, lane)
    }


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        raise SystemExit(__doc__)
    diff = args[args.index("--diff") + 1] if "--diff" in args else None
    out = args[args.index("--out") + 1] if "--out" in args else None
    r = convert(args[0], diff)
    ch = r["notes"]
    lanes = [sum(1 for _, l in ch if l == i) for i in range(4)]
    times = sorted(set(t for t, _ in ch))
    gaps = [times[i + 1] - times[i] for i in range(len(times) - 1)]
    print("map    :", r["file"])
    print("song   :", r["artist"], "-", r["title"], "[" + r["version"] + "]")
    print("audio  :", r["audio"])
    print("mode   :", r["mode"], ("%dK" % r["keys"]) if r["keys"] else "")
    print("tempo  : %.2f BPM at %.3f s, %d timing section%s"
          % (r["bpm"], r["zero"], len(r["tp"]), "" if len(r["tp"]) == 1 else "s"))
    if len(r["tp"]) > 1:
        print("         changes:", ", ".join("%.1fs=%.0fbpm" % (t, 60 / b) for t, b in r["tp"][:6]))
    print("notes  : %d, lanes %s, shortest gap %.0f ms, last at %.1f s"
          % (len(ch), lanes, min(gaps) * 1000, times[-1]))
    if out:
        io.open(out, "w", encoding="utf-8").write(",".join("[%g,%d]" % (t, l) for t, l in ch))
        print("written:", out)
