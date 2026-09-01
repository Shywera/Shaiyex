import sys, io
sys.path.insert(0, r'C:/Users/krist/shaiyex/tools')
from osu2chart import convert, as_chart
r = convert(sys.argv[1])
ch = as_chart(r)
BEAT = r["beat"]
times = sorted(set(b for b,_ in ch))
print("song grid : %.3f BPM, beat %.5f s, offset %.3f s" % (r["bpm"], BEAT, r["zero"]))
print("notes     : %d over %.1f s" % (len(ch), (times[-1]-times[0])*BEAT))
# where do the notes sit relative to the beat?
from collections import Counter
sub = Counter()
for b,_ in ch:
    frac = round((b % 1) * 8) % 8      # eighth-of-a-beat buckets
    sub[frac] += 1
print("position within the beat (32nd buckets of an 8th):")
for k in range(8):
    print("   %s : %4d  %s" % (["on beat","1/8","1/4","3/8","1/2","5/8","3/4","7/8"][k],
                               sub[k], "#"*int(sub[k]/25)))
gaps=[(times[i+1]-times[i])*BEAT*1000 for i in range(len(times)-1)]
gaps.sort()
print("gaps ms   : min %.0f  p10 %.0f  median %.0f" % (gaps[0], gaps[len(gaps)//10], gaps[len(gaps)//2]))
peak=0
for t in times:
    c=sum(1 for b,_ in ch if t<=b<t+1/BEAT)
    peak=max(peak,c)
print("peak      : %d notes in one second" % peak)
