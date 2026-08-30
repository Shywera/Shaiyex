# -*- coding: utf-8 -*-
"""Create blacklist.xlsx from scratch (no third-party libraries).

Two sheets:
  Blacklist -> Name | Realm | Link | Reason
  Stats     -> Depleted keys | <number>
"""
import zipfile, io, os, sys

def esc(t):
    return (str(t).replace('&', '&amp;').replace('<', '&lt;')
            .replace('>', '&gt;').replace('"', '&quot;'))

def col(i):
    s = ''
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s

def sheet(rows, widths):
    cols = ''.join(
        '<col min="%d" max="%d" width="%d" customWidth="1"/>' % (i + 1, i + 1, w)
        for i, w in enumerate(widths))
    body = []
    for r, row in enumerate(rows, start=1):
        cells = []
        for c, val in enumerate(row):
            ref = '%s%d' % (col(c), r)
            if isinstance(val, int):
                cells.append('<c r="%s"><v>%d</v></c>' % (ref, val))
            else:
                cells.append(
                    '<c r="%s" t="inlineStr"><is><t xml:space="preserve">%s</t></is></c>'
                    % (ref, esc(val)))
        body.append('<row r="%d">%s</row>' % (r, ''.join(cells)))
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<cols>%s</cols><sheetData>%s</sheetData></worksheet>' % (cols, ''.join(body)))

BL = [
    ['Name', 'Realm', 'Link', 'Reason'],
    ['Wannatotem', 'Twisting Nether (EU)',
     'https://raider.io/characters/eu/twisting-nether/Wannatotem', ''],
]
ST = [
    ['Setting', 'Value'],
    ['Depleted keys', 1],
]

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

out = sys.argv[1] if len(sys.argv) > 1 else 'blacklist.xlsx'
if os.path.exists(out):
    print('refusing to overwrite existing %s' % out)
    raise SystemExit(1)

with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
    z.writestr('[Content_Types].xml', CT)
    z.writestr('_rels/.rels', RELS)
    z.writestr('xl/workbook.xml', WB)
    z.writestr('xl/_rels/workbook.xml.rels', WBR)
    z.writestr('xl/worksheets/sheet1.xml', sheet(BL, [22, 26, 62, 46]))
    z.writestr('xl/worksheets/sheet2.xml', sheet(ST, [22, 12]))

print('wrote %s (%d bytes)' % (out, os.path.getsize(out)))
