import re, io, sys
a = io.open(r'C:/Users/krist/shaiyex/tools/_prev.html', encoding='utf-8').read()
b = io.open(r'C:/Users/krist/shaiyex/public/beat/index.html', encoding='utf-8').read()
def charts(s):
    js = re.search(r'<script>(.*?)</script>', s, re.S).group(1)
    d = {}
    for nm in re.findall(r'var ([A-Z]+_[NHM]) = \[', js):
        blk = re.search(r'var '+nm+r' = \[(.*?)\n  \];', js, re.S).group(1)
        d[nm] = re.findall(r'\[([\d.]+),(\d)\]', blk)
    return d
ca, cb = charts(a), charts(b)
print("chart sets identical:", ca == cb, "| arrays:", len(cb))
def cfgblock(s):
    js = re.search(r'<script>(.*?)</script>', s, re.S).group(1)
    m = re.search(r'var DUNGEONS = \{(.*?)\n  \};', js, re.S).group(1)
    return re.findall(r'(name|short|track|song|bpm|beat|zero|end):\s*("?[^,\n]+"?)', m), \
           re.findall(r'\{ b: (\d+),\s*mob: "([^"]+)",\s*spell: "([^"]+)" \}', m)
fa, pa = cfgblock(a); fb, pb = cfgblock(b)
print("dungeon fields identical:", fa == fb)
print("pull lists identical:", pa == pb, "| pulls:", len(pb))
if fa != fb:
    for x, y in zip(fa, fb):
        if x != y: print("   ", x, "->", y)
# everything outside the generated block must be untouched
def outside(s):
    i = s.index("  var KR_N = [")
    j = s.index("  var dung = 'kr', G = DUNGEONS.kr;")
    return s[:i] + s[j:]
print("rest of the page byte identical:", outside(a) == outside(b))
