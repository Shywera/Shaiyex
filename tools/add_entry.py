# -*- coding: utf-8 -*-
"""Append an entry and rebuild blacklist.xlsx from the current list.

Usage:  python tools/add_entry.py "Name" "Realm" "https://link" "Reason"
Keeps the spreadsheet as the source of truth so the next publish
does not drop anything.
"""
import io, json, os, re, sys, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON = os.path.join(ROOT, 'public', 'blacklist.json')
XLSX = os.path.join(ROOT, 'blacklist.xlsx')

sys.path.insert(0, os.path.join(ROOT, 'tools'))


def esc(t):
    return (str(t).replace('&', '&amp;').replace('<', '&lt;')
            .replace('>', '&gt;').replace('"', '&quot;'))


def colref(i):
    s, i = '', i + 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def sheet(rows, widths):
    cols = ''.join('<col min="%d" max="%d" width="%d" customWidth="1"/>'
                   % (i + 1, i + 1, w) for i, w in enumerate(widths))
    body = []
    for r, row in enumerate(rows, start=1):
        cells = []
        for c, val in enumerate(row):
            ref = '%s%d' % (colref(c), r)
            if isinstance(val, int):
                cells.append('<c r="%s"><v>%d</v></c>' % (ref, val))
            else:
                cells.append('<c r="%s" t="inlineStr"><is><t xml:space="preserve">%s</t></is></c>'
                             % (ref, esc(val)))
        body.append('<row r="%d">%s</row>' % (r, ''.join(cells)))
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<cols>%s</cols><sheetData>%s</sheetData></worksheet>' % (cols, ''.join(body)))


CT = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
      '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
      '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
      '<Default Extension="xml" ContentType="application/xml"/>'
      '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
      '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
      '<Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
      '</Types>')
RELS = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        '</Relationships>')
WB = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
      '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
      '<sheets><sheet name="Blacklist" sheetId="1" r:id="rId1"/>'
      '<sheet name="Stats" sheetId="2" r:id="rId2"/></sheets></workbook>')
WBR = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
       '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
       '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
       '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/>'
       '</Relationships>')


def clean_link(u):
    u = (u or '').strip()
    if not re.match(r'^https?://', u):
        return ''
    return u.split('?')[0]          # drop utm_source and friends


def main():
    if len(sys.argv) < 2:
        print('need at least a name')
        return 1
    name  = sys.argv[1].strip()
    realm = sys.argv[2].strip() if len(sys.argv) > 2 else ''
    link  = clean_link(sys.argv[3] if len(sys.argv) > 3 else '')
    note  = sys.argv[4].strip() if len(sys.argv) > 4 else ''

    data = {'depleted': 0, 'entries': []}
    if os.path.exists(JSON):
        data = json.loads(io.open(JSON, encoding='utf-8').read())

    entries = data.get('entries', [])
    if any((e.get('name', '').lower() == name.lower()) for e in entries):
        print('%s is already on the list' % name)
        return 0
    entries.append({'name': name, 'realm': realm, 'link': link, 'note': note})

    rows = [['Name', 'Realm', 'Link', 'Reason']]
    for e in entries:
        rows.append([e.get('name', ''), e.get('realm', ''), e.get('link', ''), e.get('note', '')])
    stats = [['Setting', 'Value'], ['Depleted keys', int(data.get('depleted', 0))]]

    with zipfile.ZipFile(XLSX, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', CT)
        z.writestr('_rels/.rels', RELS)
        z.writestr('xl/workbook.xml', WB)
        z.writestr('xl/_rels/workbook.xml.rels', WBR)
        z.writestr('xl/worksheets/sheet1.xml', sheet(rows, [22, 26, 62, 46]))
        z.writestr('xl/worksheets/sheet2.xml', sheet(stats, [22, 12]))

    print('added %s — workbook now has %d entries' % (name, len(entries)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
