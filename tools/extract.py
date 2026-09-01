import re, io, json, os
src = io.open(r'C:/Users/krist/shaiyex/public/beat/index.html', encoding='utf-8').read()
js  = re.search(r'<script>(.*?)</script>', src, re.S).group(1)
out = r'C:/Users/krist/shaiyex/tools/charts/'
os.makedirs(out, exist_ok=True)
for nm in ['KR_N','KR_H','KR_M','RLP_N','RLP_H','RLP_M','VSA_N','VSA_H','VSA_M']:
    blk = re.search(r'var '+nm+r' = \[(.*?)\n  \];', js, re.S).group(1)
    pairs = re.findall(r'\[([\d.]+),(\d)\]', blk)
    io.open(out+nm+'.txt','w',encoding='utf-8').write(
        ",".join("[%g,%d]"%(float(a),int(b)) for a,b in pairs))
    print(nm, len(pairs))
# and the dungeon config, straight out of the page so nothing is retyped
blk = re.search(r'var DUNGEONS = \{(.*?)\n  \};', js, re.S).group(1)
cfg=[]
for key in ['kr','rlp','vsa']:
    m = re.search(key+r': \{(.*?)\n    \}', blk, re.S).group(1)
    def g(field, cast=str):
        mm = re.search(field+r':\s*"?([^,"\n]+)"?', m)
        return cast(mm.group(1).strip()) if mm else None
    pulls=[]
    for pb, mob, sp in re.findall(r'\{ b: (\d+),\s*mob: "([^"]+)",\s*spell: "([^"]+)" \}', m):
        pulls.append({"b":int(pb),"mob":mob,"spell":sp})
    cfg.append({
        "key": key,
        "name": g('name'), "short": g('short'),
        "track": g('track'), "song": g('song'),
        "bpm": g('bpm', float), "beat": g('beat', float),
        "zero": g('zero', float), "end": g('end', float),
        "charts": {"normal": key.upper()+"_N", "heroic": key.upper()+"_H", "mythic": key.upper()+"_M"},
        "pulls": pulls
    })
io.open(r'C:/Users/krist/shaiyex/tools/dungeons.json','w',encoding='utf-8').write(
    json.dumps(cfg, indent=2))
print("wrote dungeons.json with", len(cfg), "dungeons")
