"""Add osu beatmap folders as dungeons.

  python tools/add_maps.py "<folder of beatmap folders>"

For each beatmap folder it picks the busiest difficulty, splits it into our
three, levels the audio into public/beat/, and appends an entry to
dungeons.json using the song title as a placeholder name.
"""
import sys, os, io, json, re, subprocess, glob

T = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(T)
sys.path.insert(0, T)
from osu2chart import convert
from osu_difficulties import split, report

FF = (r"C:/Users/krist/AppData/Local/Microsoft/WinGet/Packages/"
      r"Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/"
      r"ffmpeg-8.1.1-full_build/bin/ffmpeg.exe")


def slug(s, n=4):
    words = re.findall(r"[A-Za-z0-9]+", s)
    if len(words) == 1:
        return words[0][:n].upper()
    return "".join(w[0] for w in words)[:n].upper()


def duration(path):
    out = subprocess.run([FF, "-hide_banner", "-i", path],
                         capture_output=True, text=True).stderr
    m = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", out)
    if not m:
        return None
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))


def encode(src, dst):
    subprocess.run([FF, "-v", "error", "-i", src,
                    "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
                    "-c:a", "libmp3lame", "-b:a", "128k",
                    "-ar", "44100", "-ac", "2", dst, "-y"], check=True)


def main(root):
    cfg = json.load(io.open(T + "/dungeons.json", encoding="utf-8"))
    taken = {d["key"] for d in cfg}
    used_short = {d["short"] for d in cfg}

    folders = sorted(d for d in glob.glob(os.path.join(root, "*")) if os.path.isdir(d))
    for folder in folders:
        r = convert(folder)
        title = r["title"]
        short = slug(title)
        base = short.lower()
        key, i = base, 2
        while key in taken:
            key = base + str(i); i += 1
        while short in used_short:
            short = short + "2"
        taken.add(key); used_short.add(short)

        # the audio the map was timed against
        audio = None
        for c in glob.glob(os.path.join(folder, "**", r["audio"]), recursive=True):
            audio = c; break
        if not audio:
            print("!! no audio for", title, "(" + r["audio"] + ")"); continue

        out_name = key + ".mp3"
        encode(audio, os.path.join(ROOT, "public", "beat", out_name))
        dur = duration(os.path.join(ROOT, "public", "beat", out_name)) or 0

        n, h, m = split(r["notes"], r["tp"])
        for nm, arr in (("normal", n), ("heroic", h), ("mythic", m)):
            io.open(os.path.join(T, "charts", "%s_%s.txt" % (short, nm[0].upper())),
                    "w", encoding="utf-8").write(
                ",".join("[%g,%d]" % (t, l) for t, l in arr))

        last = max(t for t, _ in r["notes"])
        end = round(min(dur - 0.3, last + 5.0), 1)

        print("%-16s %-5s %6.2f BPM  %d sections  notes %d/%d/%d  last %.0fs  audio %.0fs"
              % (title[:16], short, r["bpm"], len(r["tp"]), len(n), len(h), len(m), last, dur))

        cfg.append({
            "key": key,
            "name": title, "short": short,
            "track": out_name, "song": r["artist"] + " - " + title,
            "bpm": round(r["bpm"], 2), "beat": round(r["beat"], 6),
            "zero": round(r["zero"], 3), "end": end, "len": round(dur, 2),
            "charts": {"normal": short + "_N", "heroic": short + "_H", "mythic": short + "_M"},
            "pulls": [{"b": 0, "mob": title, "spell": "Interrupt"}],
        })

    io.open(T + "/dungeons.json", "w", encoding="utf-8", newline="").write(
        json.dumps(cfg, indent=2))
    print("dungeons.json now has", len(cfg), "dungeons")


if __name__ == "__main__":
    main(sys.argv[1])
