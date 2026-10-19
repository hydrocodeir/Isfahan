import json,pathlib,re,sys,html
sys.stdout.reconfigure(encoding='utf-8')
R=pathlib.Path(__file__).resolve().parents[1];P=R/'reports/deep_refresh_2026_10_19'
a=json.loads((P/'access_checks.json').read_text('utf-8'))
for x in a:
 if x['key'].startswith('A'):
  ms=[m for m in x.get('metadata',[]) if 'citation_reference' not in m and any(t in m for t in ['citation_title','citation_author','citation_doi','citation_date','citation_publication','citation_pdf','dc.creator'])]
  print(x['key'],ms[:18])
for k in ['C01','C02','C03','C04','C05','C06','C07']:
 txt=(P/f'files/{k}.txt').read_text('utf-8'); start=txt.rfind('مطالعه',0,txt.index('کارفرما:'))
 print(k,txt[start:txt.index('تلفن:',start)])
b=json.loads((R/'data.json').read_text('utf-8'))
print('POSSIBLE MASTER OVERLAPS')
for s in b['sources']:
 if any(t in json.dumps(s,ensure_ascii=False).lower() for t in ['شلمزار','6027','egu25','khersan dam-to','subsurface exploration','مهندسي ارزش','مهندسی ارزش','concrete segments damages','consumed disc cutters','hishinuma']):print(s['Source_ID'],s['Title'],s['DOI'],s['URL'])
print('DOI_LANDING_A14', (P/'files/A14.txt').read_text('utf-8')[:1200])
print('PAPER_A06', (P/'files/A06.txt').read_text('utf-8')[:800])
print('ARCHAEOLOGY', (P/'files/D01.txt').read_text('utf-8')[2000:7000])
