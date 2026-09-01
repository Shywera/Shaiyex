"""One time: charts move from beat positions to seconds."""
import io, json, re, os
T = os.path.dirname(os.path.abspath(__file__))
cfg = json.load(io.open(T + "/dungeons.json", encoding="utf-8"))
for d in cfg:
    beat, zero = float(d["beat"]), float(d["zero"])
    for diff in ("normal", "heroic", "mythic"):
        p = T + "/charts/" + d["charts"][diff] + ".txt"
        raw = io.open(p, encoding="utf-8").read()
        pairs = re.findall(r"\[([\d.]+),(\d)\]", raw)
        secs = [(zero + float(b) * beat, int(l)) for b, l in pairs]
        io.open(p, "w", encoding="utf-8").write(
            ",".join("[%g,%d]" % (t, l) for t, l in secs))
    print("%-4s %-16s beat %.5f zero %.3f -> seconds" % (d["key"], d["name"], beat, zero))
