"""Preserve original XLSX parts around artifact-authored edits.

The artifact exporter rewrites legacy hyperlinks and styles. Overlay only the
authorized authored cells/rows onto the original OOXML package, remapping new
styles and shared strings, and create new hyperlink relationships explicitly.
No workbook content is regenerated with a second spreadsheet authoring library.
"""
import copy,json,pathlib,posixpath,re,sys,zipfile
import xml.etree.ElementTree as E

R=pathlib.Path(__file__).resolve().parents[1]
P=R/(sys.argv[1] if len(sys.argv)>1 else 'reports/merge_deep_round2_2026_10_10')
M='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
REL='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
PKG='http://schemas.openxmlformats.org/package/2006/relationships'
E.register_namespace('',M);E.register_namespace('r',REL)
def tag(s):return '{'+M+'}'+s
def unpack(path):
    with zipfile.ZipFile(path) as z:return {n:z.read(n) for n in z.namelist()}
def xml(b):return E.fromstring(b)
def dump(e):return E.tostring(e,encoding='utf-8',xml_declaration=True)
def target(base,t):return t.lstrip('/') if t.startswith('/') else posixpath.normpath(posixpath.join(base,t))
def sheetmap(z):
    rels={e.get('Id'):target('xl',e.get('Target')) for e in xml(z['xl/_rels/workbook.xml.rels'])}
    return {e.get('name'):rels[e.get('{'+REL+'}id')] for e in xml(z['xl/workbook.xml']).find(tag('sheets'))}
old=unpack(P/'backup/Data.xlsx');new=unpack(P/'staged/Data.xlsx');out=dict(old)
osheets,nsheets=sheetmap(old),sheetmap(new)
changes=json.loads((P/'workbook_changes.json').read_text('utf-8'))
oldstyles,newstyles=xml(old['xl/styles.xml']),xml(new['xl/styles.xml'])
stylemap={};componentmap={}
def comp(kind,index):
    key=(kind,index)
    if key in componentmap:return componentmap[key]
    collection=oldstyles.find(tag(kind));source=newstyles.find(tag(kind))[index]
    serial=E.tostring(source)
    idx=next((i for i,c in enumerate(collection) if E.tostring(c)==serial),None)
    if idx is None:idx=len(collection);collection.append(copy.deepcopy(source));collection.set('count',str(len(collection)))
    componentmap[key]=idx;return idx
def numfmt(index):
    if index<164:return index
    source=next(e for e in newstyles.find(tag('numFmts')) if int(e.get('numFmtId'))==index)
    dest=oldstyles.find(tag('numFmts'))
    if dest is None:dest=E.Element(tag('numFmts'),{'count':'0'});oldstyles.insert(0,dest)
    match=next((e for e in dest if e.get('formatCode')==source.get('formatCode')),None)
    if match is not None:return int(match.get('numFmtId'))
    i=max([163]+[int(e.get('numFmtId')) for e in dest])+1
    e=copy.deepcopy(source);e.set('numFmtId',str(i));dest.append(e);dest.set('count',str(len(dest)));return i
def style(index):
    if index in stylemap:return stylemap[index]
    xf=copy.deepcopy(newstyles.find(tag('cellXfs'))[index])
    for attr,kind in [('fontId','fonts'),('fillId','fills'),('borderId','borders')]:
        if attr in xf.attrib:xf.set(attr,str(comp(kind,int(xf.get(attr)))))
    if 'numFmtId' in xf.attrib:xf.set('numFmtId',str(numfmt(int(xf.get('numFmtId')))))
    # The imported workbook uses the existing Normal cell style; keep that base.
    xf.set('xfId','0')
    coll=oldstyles.find(tag('cellXfs'));s=E.tostring(xf)
    idx=next((i for i,c in enumerate(coll) if E.tostring(c)==s),None)
    if idx is None:idx=len(coll);coll.append(xf);coll.set('count',str(len(coll)))
    stylemap[index]=idx;return idx
sst=xml(new['xl/sharedStrings.xml']) if 'xl/sharedStrings.xml' in new else []
def cell(source,keep_style=None):
    c=copy.deepcopy(source)
    if c.get('t')=='s':
        si=sst[int(c.find(tag('v')).text)];c.remove(c.find(tag('v')));c.set('t','inlineStr')
        inline=E.SubElement(c,tag('is'))
        for e in si:inline.append(copy.deepcopy(e))
    if keep_style is not None:
        if keep_style:c.set('s',keep_style)
        else:c.attrib.pop('s',None)
    elif 's' in c.attrib:c.set('s',str(style(int(c.get('s')))))
    return c
def relpath(path):return posixpath.join(posixpath.dirname(path),'_rels',posixpath.basename(path)+'.rels')
changed_sheets=set(changes['append'])|{e['sheet'] for e in changes['cells']}
for name in changed_sheets:
    path=osheets[name];original=xml(old[path]);authored=xml(new[nsheets[name]])
    data=original.find(tag('sheetData'));nd=authored.find(tag('sheetData'))
    rows={int(e.get('r')):e for e in data};nr={int(e.get('r')):e for e in nd}
    nc={e.get('r'):e for row in nd for e in row}
    op=changes['append'].get(name)
    if op:
        for n in range(op['start_row'],op['start_row']+len(op['rows'])):
            ar=nr[n];row=E.Element(tag('row'),dict(ar.attrib))
            for c in ar:row.append(cell(c))
            data.append(row);rows[n]=row
    for edit in [e for e in changes['cells'] if e['sheet']==name]:
        addr=edit['cell'];n=int(re.search(r'\d+',addr)[0])
        if n not in rows:
            row=E.Element(tag('row'),{'r':str(n)});data.append(row);rows[n]=row
        row=rows[n];existing=next((c for c in row if c.get('r')==addr),None)
        if existing is not None:
            i=list(row).index(existing);replacement=cell(nc[addr],existing.get('s',''));row.remove(existing);row.insert(i,replacement)
        else:row.append(cell(nc[addr]))
    dimension=original.find(tag('dimension'))
    if dimension is None:
        dimension=E.Element(tag('dimension'))
        original.insert(1 if original.find(tag('sheetPr')) is not None else 0,dimension)
        columns=[re.match(r'[A-Z]+',c.get('r'))[0] for row in data for c in row]
        dimension.set('ref','A1:'+max(columns,key=lambda c:(len(c),c))+str(max(rows)))
    dimension.set('ref',re.sub(r'\d+$',str(max(rows)),dimension.get('ref')))
    if op:
        last=op['start_row']+len(op['rows'])-1
        af=original.find(tag('autoFilter'))
        if af is not None:af.set('ref',re.sub(r'\d+$',str(last),af.get('ref')))
        rp=relpath(path);relationships=xml(old[rp]) if rp in old else E.Element('{'+PKG+'}Relationships')
        links=original.find(tag('hyperlinks'))
        if links is None:
            links=E.Element(tag('hyperlinks'))
            # OOXML order: hyperlinks before print/page/drawing/table sections.
            after={'printOptions','pageMargins','pageSetup','headerFooter','drawing','legacyDrawing','tableParts','extLst'}
            i=next((i for i,e in enumerate(original) if e.tag.split('}')[-1] in after),len(original));original.insert(i,links)
        max_id=max([0]+[int(re.search(r'\d+$',e.get('Id'))[0]) for e in relationships if re.search(r'\d+$',e.get('Id',''))])
        for offset,values in enumerate(op['rows']):
            rownum=op['start_row']+offset
            for col,value in enumerate(values,1):
                if not isinstance(value,str) or not value.startswith(('https://','http://')) or '\n' in value or '\r' in value:continue
                colname='';v=col
                while v:v,r=divmod(v-1,26);colname=chr(65+r)+colname
                max_id+=1;rid=f'rId{max_id}'
                E.SubElement(relationships,'{'+PKG+'}Relationship',{'Id':rid,'Type':REL+'/hyperlink','Target':value,'TargetMode':'External'})
                E.SubElement(links,tag('hyperlink'),{'ref':f'{colname}{rownum}','{'+REL+'}id':rid})
        if len(relationships):out[rp]=dump(relationships)
        if not len(links):original.remove(links)
        for tablepart in original.findall(tag('tableParts')+'/'+tag('tablePart')):
            rel=next(e for e in relationships if e.get('Id')==tablepart.get('{'+REL+'}id'))
            tp=target(posixpath.dirname(path),rel.get('Target'));table=xml(old[tp])
            table.set('ref',re.sub(r'\d+$',str(last),table.get('ref')))
            af=table.find(tag('autoFilter'))
            if af is not None:af.set('ref',table.get('ref'))
            out[tp]=dump(table)
    out[path]=dump(original)
# Copy explicitly requested new registry sheets, remapping styles and package
# relationships while preserving every unrelated part of the original file.
if changes.get('new_sheets'):
    owb=xml(old['xl/workbook.xml']); nwb=xml(new['xl/workbook.xml'])
    wr=xml(old['xl/_rels/workbook.xml.rels']); ct=xml(old['[Content_Types].xml'])
    nwr={e.get('Id'):e for e in xml(new['xl/_rels/workbook.xml.rels'])}
    sheets=owb.find(tag('sheets'))
    sheet_id=max(int(e.get('sheetId')) for e in sheets)
    rel_id=max([0]+[int(re.search(r'\d+$',e.get('Id'))[0]) for e in wr if re.search(r'\d+$',e.get('Id',''))])
    sheet_file=max(int(re.search(r'sheet(\d+)\.xml$',p)[1]) for p in old if re.search(r'worksheets/sheet\d+\.xml$',p))
    table_id=max([0]+[int(xml(b).get('id')) for p,b in old.items() if re.search(r'^xl/tables/table\d+\.xml$',p)])
    content_ns='http://schemas.openxmlformats.org/package/2006/content-types'
    for name in changes['new_sheets']:
        source=next(e for e in nwb.find(tag('sheets')) if e.get('name')==name)
        sheet_id+=1; sheet_file+=1; rel_id+=1
        path=f'xl/worksheets/sheet{sheet_file}.xml'
        sr=copy.deepcopy(source);sr.set('sheetId',str(sheet_id));sr.set('{'+REL+'}id',f'rId{rel_id}');sheets.append(sr)
        E.SubElement(wr,'{'+PKG+'}Relationship',{'Id':f'rId{rel_id}','Type':REL+'/worksheet','Target':f'worksheets/sheet{sheet_file}.xml'})
        E.SubElement(ct,'{'+content_ns+'}Override',{'PartName':'/'+path,'ContentType':'application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml'})
        document=xml(new[nsheets[name]])
        for row in document.find(tag('sheetData')):
            for i,c in enumerate(list(row)):row.remove(c);row.insert(i,cell(c))
        source_rel=relpath(nsheets[name])
        if source_rel in new:
            relationships=xml(new[source_rel])
            for rel in relationships:
                if rel.get('Type')!=REL+'/table':
                    assert rel.get('TargetMode')=='External', ('unsupported new sheet relationship',rel.attrib)
                    continue
                tp=target(posixpath.dirname(nsheets[name]),rel.get('Target'))
                table_id+=1;dest=f'xl/tables/table{table_id}.xml';document_table=xml(new[tp]);document_table.set('id',str(table_id))
                out[dest]=dump(document_table);rel.set('Target',f'../tables/table{table_id}.xml')
                E.SubElement(ct,'{'+content_ns+'}Override',{'PartName':'/'+dest,'ContentType':'application/vnd.openxmlformats-officedocument.spreadsheetml.table+xml'})
            out[relpath(path)]=dump(relationships)
        out[path]=dump(document)
    out['xl/workbook.xml']=dump(owb);out['xl/_rels/workbook.xml.rels']=dump(wr);out['[Content_Types].xml']=dump(ct)
out['xl/styles.xml']=dump(oldstyles)
content_types=xml(out['[Content_Types].xml'])
E.register_namespace('','http://schemas.openxmlformats.org/package/2006/content-types')
out['[Content_Types].xml']=dump(content_types)
temporary=P/'staged/preserved.xlsx'
with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED) as z:
    for name,blob in out.items():z.writestr(name,blob)
temporary.replace(P/'staged/Data.xlsx')
print('Preserved original workbook parts; applied artifact-authored edits to',len(changed_sheets),'sheets.')
