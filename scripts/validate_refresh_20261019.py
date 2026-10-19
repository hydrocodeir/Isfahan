"""Validate all allowed edits, native feature preservation, and source references."""
import collections,copy,json,pathlib,re,shutil,sys,zipfile,xml.etree.ElementTree as E
from openpyxl import load_workbook
from merge_refresh_20261019 import ROOT,OUT,read,save,sha
def validate():
 data=read(OUT/'staged/data.json');before=read(OUT/'backup/data.json');m=read(OUT/'manifest.json');ops=read(OUT/'workbook_changes.json');curated=read(OUT/'curated.json')
 ids={s['Source_ID'] for s in data['sources']};by={s['Source_ID']:s for s in data['sources']};n=len(before['sources'])
 assert len(ids)==len(data['sources'])==1067
 assert [s['Source_ID'] for s in data['sources']]==[f'S{i:03}' for i in range(1,1068)]
 assert data['meta']['totalSources']==1067 and data['meta']['lastSourceId']=='S1067'
 allowed_src={e['source_id']:e['fields'] for e in m['enriched_sources']}
 for s in before['sources']:assert by[s['Source_ID']]==dict(s,**allowed_src.get(s['Source_ID'],{})),s['Source_ID']
 for k,values in data['collections'].items():assert len(values)==len(set(values)) and set(values)<=ids,k
 assert len(data['transferResearch']['studies'])==49 and len(data['transferProjects'])==25
 pids={p['id'] for p in data['transferProjects']};sids=set()
 for s in data['transferResearch']['studies']:
  assert s['id'] not in sids;sids.add(s['id']);assert set(s['project_ids'])<=pids and set(s['source_ids'])<=ids
 for p in data['transferProjects']:assert set(p['source_ids'])<=ids
 for s in data['sources'][n:]:
  for f in ['Title','URL','Publisher','Project','Source_Type','Notes']:assert s[f],(s['Source_ID'],f)
  if s['Local_PDF']:
   p=ROOT/s['Local_PDF'];assert p.read_bytes().startswith(b'%PDF') and sha(p)==s['SHA256']
  if s['Date_Gregorian']:assert s['Date_Gregorian']<='2026-10-19'
 # The online DOI deposit is separated from its future December print issue.
 ecology=by[m['source_mapping']['A06']];assert ecology['Date_Gregorian'] is None and '2026-12' in next(s['period'] for s in data['transferResearch']['studies'] if s['source_ids']==[ecology['Source_ID']])
 assert len([s for s in data['sources'][n:] if s['Local_PDF']])==6
 app=(OUT/'staged/app.js').read_text('utf-8');mark='const OFFLINE_FALLBACK = ';start=app.index(mark)+len(mark);end=app.index(';\n\nconst $',start)
 assert json.loads(app[start:end])==data
 wb=load_workbook(OUT/'staged/Data.xlsx');old=load_workbook(OUT/'backup/Data.xlsx');assert old.sheetnames==wb.sheetnames
 allowed={(e['sheet'],e['cell']):e['value'] for e in ops['cells']};checked=0
 def blank(v):return None if v=='' else v
 for ws in old:
  new=wb[ws.title]
  for row in ws:
   for c in row:
    nc=new[c.coordinate];expected=allowed.get((ws.title,c.coordinate),c.value)
    assert nc.value==blank(expected),(ws.title,c.coordinate,'value',nc.value,expected)
    assert nc._style==c._style,(ws.title,c.coordinate,'style')
    assert (nc.hyperlink.target if nc.hyperlink else None)==(c.hyperlink.target if c.hyperlink else None),(ws.title,c.coordinate,'hyperlink')
    assert (nc.comment.text if nc.comment else None)==(c.comment.text if c.comment else None),(ws.title,c.coordinate,'comment')
    checked+=1
  assert ws.freeze_panes==new.freeze_panes and set(ws.tables)==set(new.tables)
  assert list(ws.merged_cells.ranges)==list(new.merged_cells.ranges)
  assert str(ws.protection)==str(new.protection) and ws.data_validations==new.data_validations
  assert {k:dict(v) for k,v in ws.column_dimensions.items()}=={k:dict(v) for k,v in new.column_dimensions.items()}
  for k,v in ws.row_dimensions.items():assert dict(v)==dict(new.row_dimensions[k]),(ws.title,k,'row dimensions')
 for sheet,op in ops['append'].items():
  expected=[[blank(v) for v in row] for row in op['rows']]
  actual=[[wb[sheet].cell(r,c).value for c in range(1,op['columns']+1)] for r in range(op['start_row'],op['start_row']+len(op['rows']))]
  assert actual==expected,('appended rows',sheet)
 for e in ops['cells']:assert wb[e['sheet']][e['cell']].value==blank(e['value'])
 assert wb['ALL_SOURCES'].tables['AllSourcesClean'].ref=='A1:AK1068'
 assert wb['TRANSFER_STUDIES'].tables['TransferStudies'].ref=='A1:L50'
 assert wb['TRANSFER_PROJECTS'].tables['TransferProjects'].ref=='A1:K26'
 rows=list(wb['ALL_SOURCES'].values);heads=rows[0]
 assert [list(r) for r in rows[n+1:]]==[[blank(s.get(k)) for k in heads] for s in data['sources'][n:]]
 baseline_differences=collections.Counter(k for row,s in zip(list(old['ALL_SOURCES'].values)[1:],before['sources']) for k,v in zip(heads,row) if v!=s.get(k))
 after_differences=collections.Counter(k for row,s in zip(rows[1:n+1],data['sources'][:n]) for k,v in zip(heads,row) if v!=s.get(k))
 assert baseline_differences==after_differences
 # Cell edits preserve every pre-existing style, relationship and native feature.
 wb.close();old.close()
 result={'status':'PASS','date':'2026-10-19','before_sources':n,'after_sources':1067,'added_sources':25,'enriched_source_ids':['S097'],
  'new_study_records':19,'updated_study_records':2,'total_study_records':49,'new_project_profiles':8,'total_project_profiles':25,
  'primary_pdfs_added':6,'existing_excel_cells_checked':checked,'existing_style_changes':0,'json_offline_equal':True,'new_excel_json_rows_equal':True,
  'legacy_excel_json_differences_preserved':dict(baseline_differences),'doi_date_conflicts_documented':True}
 save(OUT/'validation.json',result);print(json.dumps(result,ensure_ascii=False,indent=2))
def apply():
 assert read(OUT/'validation.json')['status']=='PASS' and read(OUT/'browser_validation.json')['status']=='PASS'
 m=read(OUT/'manifest.json')
 for name,digest in m['baseline_sha256'].items():assert sha(ROOT/name)==digest,'Main file changed during staging: '+name
 for name in ['Data.xlsx','data.json','app.js']:shutil.copy2(OUT/'staged'/name,ROOT/name)
 print('Applied validated refresh to master files.')
if __name__=='__main__':(apply if '--apply' in sys.argv else validate)()
