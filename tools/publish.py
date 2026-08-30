# -*- coding: utf-8 -*-
"""Read blacklist.xlsx -> write public/blacklist.json -> commit + push.

Cloudflare Pages redeploys on push, so the site updates on its own.
Handles both inline strings (how we write the file) and shared strings
(how Excel rewrites it once you save).
"""
import io, json, os, re, subprocess, sys, zipfile
import xml.etree.ElementTree as ET

NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
XLSX = os.path.join(ROOT, 'blacklist.xlsx')
OUT  = os.path.join(ROOT, 'public', 'blacklist.json')


def col_of(ref):
    m = re.match(r'([A-Z]+)', ref or '')
    if not m:
        return 0
    n = 0
    for ch in m.group(1):
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def read_sheet(z, path, shared):
    try:
        root = ET.fromstring(z.read(path))
    except KeyError:
        return []
    rows = []
    for row in root.iter(NS + 'row'):
        cells = {}
        for c in row.iter(NS + 'c'):
            t = c.get('t')
            val = ''
            if t == 'inlineStr':
                node = c.find(NS + 'is')
                if node is not None:
                    val = ''.join(x.text or '' for x in node.iter(NS + 't'))
            else:
                v = c.find(NS + 'v')
                if v is not None and v.text is not None:
                    if t == 's':
                        try:
                            val = shared[int(v.text)]
                        except (ValueError, IndexError):
                            val = ''
                    else:
                        val = v.text
            cells[col_of(c.get('r'))] = (val or '').strip()
        if cells:
            width = max(cells) + 1
            rows.append([cells.get(i, '') for i in range(width)])
    return rows


def sheet_paths(z):
    """Map sheet name -> part path, so sheet order can't bite us."""
    wb = ET.fromstring(z.read('xl/workbook.xml'))
    rels = ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
    RNS = '{http://schemas.openxmlformats.org/package/2006/relationships}'
    target = {r.get('Id'): r.get('Target') for r in rels.iter(RNS + 'Relationship')}
    RID = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'
    out = {}
    for s in wb.iter(NS + 'sheet'):
        t = target.get(s.get(RID), '')
        if t and not t.startswith('xl/'):
            t = 'xl/' + t.lstrip('/')
        out[(s.get('name') or '').strip().lower()] = t
    return out


def main():
    if not os.path.exists(XLSX):
        print('ERROR: %s not found' % XLSX)
        return 1

    z = zipfile.ZipFile(XLSX)
    shared = []
    if 'xl/sharedStrings.xml' in z.namelist():
        ss = ET.fromstring(z.read('xl/sharedStrings.xml'))
        for si in ss.iter(NS + 'si'):
            shared.append(''.join(t.text or '' for t in si.iter(NS + 't')))

    paths = sheet_paths(z)
    bl_rows = read_sheet(z, paths.get('blacklist', 'xl/worksheets/sheet1.xml'), shared)
    st_rows = read_sheet(z, paths.get('stats', 'xl/worksheets/sheet2.xml'), shared)

    entries = []
    for r in bl_rows[1:]:                       # skip the header row
        g = lambda i: (r[i] if i < len(r) else '').strip()
        if not g(0):
            continue
        link = g(2)
        if not re.match(r'^https?://', link):
            link = ''
        entries.append({'name': g(0), 'realm': g(1), 'link': link, 'note': g(3)})

    depleted = 0
    for r in st_rows[1:]:
        if len(r) >= 2 and 'deplet' in r[0].lower():
            m = re.search(r'-?\d+', r[1])
            if m:
                depleted = int(m.group(0))

    data = {'depleted': depleted, 'entries': entries}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, 'w', encoding='utf-8').write(
        json.dumps(data, ensure_ascii=False, indent=1))

    print('blacklist entries : %d' % len(entries))
    for e in entries:
        print('   - %s%s' % (e['name'], (' (%s)' % e['realm']) if e['realm'] else ''))
    print('depleted keys     : %d' % depleted)

    def git(*a):
        return subprocess.run(('git',) + a, cwd=ROOT,
                              capture_output=True, text=True)

    git('add', 'public/blacklist.json', 'blacklist.xlsx')
    status = git('status', '--porcelain', 'public/blacklist.json', 'blacklist.xlsx').stdout.strip()
    if not status:
        print('\nNothing changed since last publish.')
        return 0

    c = git('commit', '-m', 'Blacklist: %d entries, %d depleted' % (len(entries), depleted))
    if c.returncode != 0:
        print('commit failed:\n' + (c.stderr or c.stdout))
        return 1
    p = git('push', 'origin', 'main')
    if p.returncode != 0:
        print('push failed:\n' + (p.stderr or p.stdout))
        return 1

    print('\nPushed. The site updates in about half a minute.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
