import io, difflib
a=io.open(r'C:/Users/krist/shaiyex/tools/_prev.html',encoding='utf-8').read()
b=io.open(r'C:/Users/krist/shaiyex/public/beat/index.html',encoding='utf-8').read()
def outside(s):
    i=s.index("  var KR_N = ["); j=s.index("  var dung = 'kr', G = DUNGEONS.kr;")
    return (s[:i]+s[j:]).splitlines()
d=[l for l in difflib.unified_diff(outside(a),outside(b),lineterm='',n=0)
   if l.startswith(('+','-')) and not l.startswith(('+++','---'))]
print("differences outside the generated block:", len(d))
for l in d: print("  ",l)
