"""Discovery only: registry searches and citation chasing; never edits master."""
import requests,json,re,pathlib,unicodedata,concurrent.futures,sys,time
sys.stdout.reconfigure(encoding='utf-8')
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=ROOT/'reports/deep_round2_2026_10_10';OUT.mkdir(exist_ok=True)
baseline=json.loads((ROOT/'data.json').read_text('utf-8-sig'))['sources']
for f in ['research_refresh_2026_10_03_candidates.json','news_refresh_2026_10_03.json','four_categories_2026_10_03/candidates.json','refresh_2026_10_10/candidates.json']:
 d=json.loads((ROOT/'reports'/f).read_text('utf-8-sig'));baseline+=d.get('Candidates',d.get('candidates',[]))
def norm(t):return re.sub(r'[^\w]','',unicodedata.normalize('NFKC',str(t or '')).lower().replace('ي','ی').replace('ك','ک'))
base_text=json.dumps(baseline,ensure_ascii=False).lower();titles={norm(s.get(k)) for s in baseline for k in ['Title','Title_EN'] if s.get(k)}
def inv(x):return ' '.join(w for _,w in sorted((p,w) for w,ps in (x or {}).items() for p in ps))
queries=['Beheshtabad','Behesht Abad','Koohrang tunnel','Kouhrang water transfer','Kuhrang water transfer','Khersan water transfer','Khersan dam','Golab tunnel','Cheshmeh Langan','Cheshme Langan','Khadangestan','Khodangestan','Sabzkooh tunnel','Sabzkuh water','Zayandeh interbasin transfer','Karoon interbasin transfer','Vanak Rafsanjan','Gukan water','Mandegan dam','Ben Borujen','Zayandeh water conflict','Karun water transfer environmental']
seeds=['10.1038/s41598-026-49232-5','10.1016/j.scitotenv.2020.138499','10.1016/j.ejrh.2026.103359','10.22067/jwsd.v11i3.2410-1375','10.1007/s00704-024-05126-y']
jobs=[('openalex',q) for q in queries]+[('crossref',q) for q in queries[:14]]+[('references',q) for q in seeds]
def run(job):
 source,q=job
 try:
  if source=='openalex':
   r=requests.get('https://api.openalex.org/works',params={'search':q,'per-page':100},timeout=30);r.raise_for_status();d=r.json();items=[]
   for w in d.get('results',[]):
    loc=w.get('primary_location') or {};items.append(dict(title=w.get('title'),doi=(w.get('doi') or '').removeprefix('https://doi.org/'),date=w.get('publication_date'),abstract=inv(w.get('abstract_inverted_index')),url=loc.get('landing_page_url'),pdf=loc.get('pdf_url'),type=w.get('type'),authors=[a['author']['display_name'] for a in w.get('authorships',[])],publisher=(loc.get('source') or {}).get('display_name')))
  else:
   u='https://api.crossref.org/works'+('/'+q if source=='references' else '')
   r=requests.get(u,params=None if source=='references' else {'query.bibliographic':q,'rows':100},timeout=30);r.raise_for_status();d=r.json()['message']
   if source=='references':return dict(source=source,query=q,status=r.status_code,references=d.get('reference',[]))
   items=[dict(title=(w.get('title') or [''])[0],doi=w.get('DOI'),date=w.get('published',{}),abstract=w.get('abstract',''),url=w.get('URL'),type=w.get('type'),authors=w.get('author'),publisher=w.get('container-title')) for w in d.get('items',[])]
  return dict(source=source,query=q,status=r.status_code,items=items)
 except Exception as e:return dict(source=source,query=q,error=str(e))
results=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
 for result in pool.map(run,jobs):results.append(result);print(result['source'],result['query'],len(result.get('items',result.get('references',[]))),result.get('error',''),flush=True)
(OUT/'registry_search.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),'utf-8')
strong=re.compile(r'behesht.?abad|k[oau]+hrang|kh[eo]rsan|golab|cheshm.{0,5}langan|kh[ao]d[ae]ngestan|sabz.?k[oau]+h|zayand|kar[ou]+n|gavkh|ماندگان|خرسان|کوهرنگ|بهشت|گلاب|زاینده',re.I)
new={}
for res in results:
 for w in res.get('items',[]):
  doi=(w.get('doi') or '').lower();title=w.get('title','') or ''
  if doi and doi in base_text or norm(title) in titles:continue
  if not strong.search(title+' '+(w.get('abstract') or '')):continue
  key=doi or norm(title)
  if key not in new:new[key]=w|{'queries':[]}
  new[key]['queries'].append(res['query'])
(OUT/'registry_unmatched.json').write_text(json.dumps(list(new.values()),ensure_ascii=False,indent=2),'utf-8')
print('UNMATCHED',len(new))
for i,w in enumerate(new.values()):print(i,w.get('doi'),w['title'],(w.get('abstract') or '')[:120])
