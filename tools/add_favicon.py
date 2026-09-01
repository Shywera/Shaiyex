import io, glob, os
LINK = ('<link rel="icon" href="/favicon.svg" type="image/svg+xml">\n'
        '<link rel="apple-touch-icon" href="/favicon.svg">')
targets = sorted(glob.glob(r'C:/Users/krist/shaiyex/public/**/*.html', recursive=True))
targets.append(r'C:/Users/krist/shaiyex/tools/beat_template.html')
for p in targets:
    s = io.open(p, encoding='utf-8').read()
    if 'rel="icon"' in s:
        print("has one already:", os.path.basename(os.path.dirname(p)) or "root"); continue
    anchor = '<link rel="preconnect" href="https://fonts.googleapis.com">'
    if anchor in s:
        s = s.replace(anchor, LINK + "\n" + anchor, 1)
    elif '</title>' in s:
        s = s.replace('</title>', '</title>\n' + LINK, 1)
    else:
        print("no anchor:", p); continue
    io.open(p, 'w', encoding='utf-8', newline='').write(s)
    who = p.replace('C:/Users/krist/shaiyex/', '')
    print("added to", who)
