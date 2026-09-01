"""Rebuild public/beat/index.html from tools/dungeons.json + tools/charts/.
Adding a dungeon means adding a chart file and a json entry, then running this."""
import io, json, os, re, sys

ROOT  = r"C:/Users/krist/shaiyex"
TOOLS = ROOT + "/tools"

def wrap(path, indent="    ", width=94):
    raw = io.open(path, encoding="utf-8").read().strip()
    toks = [x.strip("[]") for x in raw.split("],[")]
    lines, line = [], indent
    for tk in toks:
        piece = "[" + tk + "],"
        if len(line) + len(piece) > width:
            lines.append(line.rstrip()); line = indent
        line += piece
    lines.append(line.rstrip().rstrip(","))
    return "\n".join(lines)

def build():
    cfg = json.load(io.open(TOOLS + "/dungeons.json", encoding="utf-8"))
    out, names = [], []
    for d in cfg:
        for diff in ("normal", "heroic", "mythic"):
            var = d["charts"][diff]
            path = TOOLS + "/charts/" + var + ".txt"
            if not os.path.exists(path):
                raise SystemExit("missing chart: " + path)
            out.append("  var %s = [\n%s\n  ];" % (var, wrap(path)))
            names.append(var)

    out.append("")
    out.append("  /* route order, and every cast here is genuinely interruptible */")
    out.append("  var DUNGEONS = {")
    blocks = []
    for d in cfg:
        pulls = ",\n".join(
            '        { b: %-3s mob: "%s",%s spell: "%s" }'
            % (str(p["b"]) + ",", p["mob"], " " * max(1, 24 - len(p["mob"])), p["spell"])
            for p in d["pulls"])
        blocks.append(
            '    %s: {\n'
            '      name: "%s", short: "%s",\n'
            '      track: "%s", song: "%s",\n'
            '      bpm: %s, beat: %s, zero: %s, end: %s,\n'
            '      charts: { normal: %s, heroic: %s, mythic: %s },\n'
            '      pulls: [\n%s\n      ]\n'
            '    }'
            % (d["key"], d["name"], d["short"], d["track"], d["song"],
               (repr(int(d["bpm"])) if float(d["bpm"]).is_integer() else repr(d["bpm"])), repr(d["beat"]), repr(d["zero"]), repr(d["end"]),
               d["charts"]["normal"], d["charts"]["heroic"], d["charts"]["mythic"],
               pulls))
    out.append(",\n".join(blocks))
    out.append("  };")

    tpl = io.open(TOOLS + "/beat_template.html", encoding="utf-8").read()
    page = tpl.replace("__DUNGEONS__", "\n".join(out))

    # the dungeon buttons on the gate are generated too
    btns = "\n".join(
        '      <button class="dung" data-g="%s" type="button">\n'
        '        <span class="dung-n">%s</span>\n'
        '        <span class="dung-d">%g BPM &middot; %d:%02d</span>\n'
        '      </button>' % (d["key"], d["name"], d["bpm"],
                             int(d.get("len", d["end"])) // 60, int(d.get("len", d["end"])) % 60)
        for d in cfg)
    page = re.sub(r'(<div class="dungs">\n).*?(\n    </div>)',
                  lambda m: m.group(1) + btns + m.group(2), page, count=1, flags=re.S)
    cols = min(3, len(cfg))
    page = re.sub(r'(\.dungs\{\n\s*display:grid;grid-template-columns:)repeat\(\d+,1fr\)',
                  lambda m: m.group(1) + "repeat(%d,1fr)" % cols, page, count=1)

    io.open(ROOT + "/public/beat/index.html", "w", encoding="utf-8", newline="").write(page)
    return cfg, names, len(page)

if __name__ == "__main__":
    cfg, names, size = build()
    print("built public/beat/index.html  %d bytes" % size)
    for d in cfg:
        print("  %-4s %-18s %-22s %g BPM  %d pulls" %
              (d["key"], d["name"], d["track"], d["bpm"], len(d["pulls"])))
