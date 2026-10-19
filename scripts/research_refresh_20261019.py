"""Read-only discovery and deduplication against the current master."""
import concurrent.futures, difflib, json, pathlib, re, sys, unicodedata
import requests
sys.stdout.reconfigure(encoding='utf-8')
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/deep_refresh_2026_10_19';OUT.mkdir(exist_ok=True)
BASE=json.loads((ROOT/'data.json').read_text('utf-8-sig'))['sources']
def norm(t):return re.sub(r'[^\w]','',unicodedata.normalize('NFKC',str(t or '')).lower().replace('ي','ی').replace('ك','ک'))
def save(name,v):(OUT/name).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n','utf-8')
queries=['Beheshtabad water transfer','Karun interbasin water transfer','Koohrang water tunnel','Golab water conveyance tunnel',
 'Sabzkooh water tunnel','Zayandeh Rud seawater transfer','Ghadir water transmission Khuzestan','Khersan water transfer',
 'Kohgiluyeh Boyer Ahmad water transfer','Chaharmahal Bakhtiari interbasin water transfer',
 'Tang Sorkh Bashar water transfer','Marun Jarahi water transfer','Kowsar regional water supply Iran','Dez Qomrud water transfer',
 'Ben Borujen water supply','Mandegan Vanak Rafsanjan water transfer','Isfahan Oman Sea desalinated water transfer',
 'Khuzestan water transfer environmental justice','Karun transfer decision conflict','Khadangestan tunnel',
 'Cheshmeh Langan water transfer','Gukan water transfer','Solegan Rafsanjan transfer','Kouhrang tunnel groundwater',
 'انتقال آب خرسان','انتقال آب کارون','انتقال آب غدیر','انتقال آب سبزکوه','انتقال آب بشار','انتقال آب کوثر']
jobs=[('crossref',q) for q in queries]+[('openalex',q) for q in queries[:18]]
def run(job):
 source,q=job
 try:
  if source=='crossref':
   r=requests.get('https://api.crossref.org/works',params={'query.bibliographic':q,'rows':80},timeout=35);r.raise_for_status()
   items=[]
   for w in r.json()['message']['items']:
    parts=(w.get('published') or w.get('issued') or {}).get('date-parts',[[]])[0]
    date='-'.join(str(v).zfill(2) if i else str(v) for i,v in enumerate(parts))
    items.append({'title':(w.get('title') or [''])[0],'doi':w.get('DOI'),'date':date,'abstract':w.get('abstract',''),
     'url':w.get('resource',{}).get('primary',{}).get('URL') or w.get('URL'),'type':w.get('type'),
     'authors':[' '.join([a.get('given',''),a.get('family','')]).strip() for a in w.get('author',[])],
     'publisher':'; '.join(w.get('container-title',[])),'links':w.get('link',[])})
  else:
   r=requests.get('https://api.openalex.org/works',params={'search':q,'per-page':80},timeout=35);r.raise_for_status();items=[]
   for w in r.json().get('results',[]):
    loc=w.get('primary_location') or {};inv=w.get('abstract_inverted_index') or {}
    abstract=' '.join(t for i,t in sorted((i,t) for t,ii in inv.items() for i in ii))
    items.append({'title':w.get('title'),'doi':(w.get('doi') or '').removeprefix('https://doi.org/'),'date':w.get('publication_date'),
     'abstract':abstract,'url':loc.get('landing_page_url'),'pdf':loc.get('pdf_url'),'type':w.get('type'),
     'authors':[a['author']['display_name'] for a in w.get('authorships',[])],'publisher':(loc.get('source') or {}).get('display_name')})
  return {'engine':source,'query':q,'status':r.status_code,'items':items}
 except Exception as e:return {'engine':source,'query':q,'error':str(e)}
results=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
 for r in pool.map(run,jobs):
  results.append(r);print(r['engine'],r['query'],len(r.get('items',[])),r.get('error',''),flush=True)
save('registry_search.json',results)
known_dois={norm(s.get('DOI')) for s in BASE if s.get('DOI')}
known_titles={norm(s.get(k)) for s in BASE for k in ['Title','Title_EN'] if s.get(k)}
base_blob=json.dumps(BASE).lower();new={}
basin=re.compile(r'behesht.?abad|k[oau]+hrang|kh[eo]rsan|golab|cheshm.{0,6}langan|kh[ao]d[ae]ngestan|sabz.?k[oau]+h|zayand|kar[ou]+n|ghadir|k[ou]wsar|qomr[ou]d|borujen|jar[ar]hi|b[ao]shar|mar[ou]n|khuzestan|خوزستان|زاینده|کارون|بشار|غدیر|بهشت|کوهرنگ|سبزکوه|خرسان',re.I)
transfer=re.compile(r'transfer|tunnel|conveyance|transmission|inter.?basin|انتقال|تونل',re.I)
for result in results:
 for w in result.get('items',[]):
  title=w.get('title') or '';abstract=w.get('abstract') or '';doi=w.get('doi') or ''
  if norm(doi) in known_dois or norm(title) in known_titles or doi and doi.lower() in base_blob:continue
  text=title+' '+abstract
  if not basin.search(text) or not transfer.search(text):continue
  key=norm(doi or title)
  if key not in new:new[key]=w|{'queries':[]}
  new[key]['queries'].append(result['query'])
rows=list(new.values())
for w in rows:
 matches=[]
 for old in BASE:
  score=max(difflib.SequenceMatcher(None,norm(w['title']),norm(old.get(k))).ratio() for k in ['Title','Title_EN'])
  if score>.5:matches.append({'id':old['Source_ID'],'score':round(score,3),'title':old['Title'],'url':old['URL']})
 w['closest']=sorted(matches,key=lambda s:-s['score'])[:3]
save('registry_unmatched.json',rows)
print('UNMATCHED',len(rows))
for i,w in enumerate(rows):print(i,w['date'],w.get('doi'),w['title'],'CLOSEST',w['closest'][:1])
