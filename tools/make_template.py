import re, io
src = io.open(r'C:/Users/krist/shaiyex/public/beat/index.html', encoding='utf-8').read()
# everything from the first chart array to the end of DUNGEONS becomes one slot
start = src.index("  var KR_N = [")
end   = src.index("  var dung = 'kr', G = DUNGEONS.kr;")
tpl = src[:start] + "__DUNGEONS__\n" + src[end:]
io.open(r'C:/Users/krist/shaiyex/tools/beat_template.html','w',encoding='utf-8',newline='').write(tpl)
print("template written, slot replaces", end-start, "bytes")
