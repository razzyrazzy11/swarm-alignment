"""Opt-in complete-ledger tables over the unchanged official-template builder.

Only manuscript table layout changes. No results are loaded or generated here.
"""
from copy import deepcopy
import json
from pathlib import Path
from lxml import etree as E

try:
    from . import build as legacy
except ImportError:
    import build as legacy

W, NS, require = legacy.W, legacy.NS, legacy.require
WIDTHS = {'table2': (2600, 1500, 5260), 'table3': (3360, 2000, 2000, 2000)}
SLOTS = {key: '__SWARM_LEDGER_' + key.upper() + '_SLOT__' for key in WIDTHS}


def _shape(rows, columns, name):
    require(type(rows) is list and len(rows) > 0, name + ' requires rows')
    require(all(type(row) is list and len(row) == columns for row in rows),
            name + ' must be rectangular with ' + str(columns) + ' columns')
    require(all(type(value) is str and value for row in rows for value in row),
            name + ' requires nonempty text cells')


def _table(source, rows, widths):
    """Clone the legacy TABLE1 styles; enumerate cells without truncating zip."""
    require(sum(widths) == 9360, 'Table exceeds template text width')
    table = deepcopy(source)
    source_rows = source.findall(W + 'tr')
    header = source_rows[0].find(W + 'tc').find(W + 'p')
    normal = source_rows[min(1, len(source_rows) - 1)].find(W + 'tc').find(W + 'p')
    for row in table.findall(W + 'tr'):
        table.remove(row)
    grid = table.find(W + 'tblGrid')
    for column in list(grid):
        grid.remove(column)
    for width in widths:
        E.SubElement(grid, W + 'gridCol').set(W + 'w', str(width))
    for index, values in enumerate(rows):
        row = E.SubElement(table, W + 'tr')
        props = E.SubElement(row, W + 'trPr')
        E.SubElement(props, W + 'cantSplit')
        if index == 0:
            E.SubElement(props, W + 'tblHeader')
        for column in range(len(widths)):
            cell = E.SubElement(row, W + 'tc')
            cp = E.SubElement(cell, W + 'tcPr')
            width = E.SubElement(cp, W + 'tcW')
            width.set(W + 'w', str(widths[column]))
            width.set(W + 'type', 'dxa')
            paragraph = deepcopy(header if index == 0 else normal)
            legacy.replace(paragraph, values[column])
            if index and len(source_rows) == 1:
                for bold in paragraph.xpath('.//w:b | .//w:bCs', namespaces=NS):
                    bold.getparent().remove(bold)
            pp = paragraph.find(W + 'pPr')
            if pp is None:
                pp = E.Element(W + 'pPr')
                paragraph.insert(0, pp)
            for keep in pp.findall(W + 'keepNext'):
                pp.remove(keep)
            if index < len(rows) - 1:
                pp.insert(sum(v.tag == W + 'pStyle' for v in pp), E.Element(W + 'keepNext'))
            cell.append(paragraph)
    require([legacy.text(c) for r in table.findall(W + 'tr') for c in r.findall(W + 'tc')]
            == [value for row in rows for value in row], 'Table cell text changed')
    return table


def assemble(content, template):
    require(content.get('table2_source') == 'swarm_ledger_complete', 'Complete-ledger layout requires explicit source')
    _shape(content.get('table1'), 3, 'table1')
    _shape(content.get('table2'), 3, 'table2')
    _shape(content.get('table3'), 4, 'table3')
    require(sum(value == 'TABLE1' for _, ps in content['sections'] for value in ps) == 1,
            'TABLE1 must occur once in sections')
    require(all(slot not in json.dumps(content) for slot in SLOTS.values()), 'Ledger sentinel collision')
    edited = deepcopy(content)
    for key, slot in SLOTS.items():
        marker = key.upper()
        require(sum(value == marker for _, ps in content['sections'] for value in ps) == 1,
                marker + ' must occur once in sections')
        caption = content.get(key + '_caption')
        require(type(caption) is str and caption.startswith('Table ' + key[-1] + '.'), 'Missing ledger table caption')
        edited['sections'] = [[name, [slot if value == marker else value for value in ps]]
                              for name, ps in edited['sections']]
    # Legal dummy shapes only satisfy unchanged legacy prevalidation. Their
    # markers are absent, so no dummy cell enters the document.
    edited['table2'] = [['unused'] * 4]
    edited['table3'] = [['unused'] * 3]
    parts = legacy.assemble(edited, Path(template))
    doc = E.fromstring(parts['word/document.xml'])
    body = doc.find(W + 'body')
    section = E.tostring(body.find(W + 'sectPr'))
    tables = body.findall(W + 'tbl')
    require(len(tables) >= 2, 'Source-generated TABLE1 required for ledger styles')
    source = tables[1]
    require([legacy.text(c) for r in source.findall(W + 'tr') for c in r.findall(W + 'tc')]
            == [value for row in content['table1'] for value in row], 'TABLE1 style source differs')
    for key, slot in SLOTS.items():
        matches = [p for p in body.findall(W + 'p') if legacy.text(p) == slot]
        require(len(matches) == 1, 'Ledger slot not unique')
        paragraph = matches[0]
        legacy.replace(paragraph, content[key + '_caption'])
        pp = paragraph.find(W + 'pPr')
        if pp is None:
            pp = E.Element(W + 'pPr')
            paragraph.insert(0, pp)
        if pp.find(W + 'keepNext') is None:
            pp.insert(sum(v.tag == W + 'pStyle' for v in pp), E.Element(W + 'keepNext'))
        paragraph.addnext(_table(source, content[key], WIDTHS[key]))
    require(all(slot not in legacy.text(doc) for slot in SLOTS.values()), 'Unresolved ledger table slot')
    require(E.tostring(body.find(W + 'sectPr')) == section, 'Ledger layout changed template geometry')
    parts['word/document.xml'] = E.tostring(doc, xml_declaration=True, encoding='UTF-8', standalone=True)
    return parts
