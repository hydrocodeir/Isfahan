import json, pathlib, requests, hashlib, concurrent.futures, sys, re, subprocess
sys.stdout.reconfigure(encoding='utf-8')
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/'reports'/'refresh_2026_10_10'
OUT.mkdir(exist_ok=True)
targets={
 'atb2021':'https://www.atb-potsdam.de/fileadmin/generell/BABs/BAB_104_Transformation_Strategies_in_Agriculture.pdf',
 'ieem2015':'https://edocs.tib.eu/files/e01fb15/842152709.pdf',
 'zeynalian':'https://static2.esfahanemrooz.ir/servev2/dSp9dQgzq5a4/eYFLnMzXdX4%2C/06.pdf',
 'copras_fa':'https://jsw.um.ac.ir/article_38803_d79d9307e8bb326d877b5b8facdf979e.pdf',
 'copras_crossref':'https://api.crossref.org/works/10.1016/j.scitotenv.2020.138499',
 'tib2019':'https://doi.org/10.2314/KXP:1671692810',
 'kebna':'https://khabarfarsi.com/u/234343667',
 'magiran_legal':'https://www.magiran.com/paper/3032415',
}
def get(item):
 key,url=item
 try:
  r=requests.get(url,timeout=25)
  pdf=r.content.startswith(b'%PDF')
  ext='.pdf' if pdf else '.json' if 'json' in r.headers.get('Content-Type','') else '.html'
  path=OUT/(key+ext)
  path.write_bytes(r.content)
  result=dict(Key=key,URL=url,Final_URL=r.url,Status=r.status_code,PDF=pdf,Bytes=len(r.content),File=str(path.relative_to(ROOT)),SHA256=hashlib.sha256(r.content).hexdigest())
  if key=='kebna': result['Primary_Links']=list(set(re.findall(r'https?[^\s\"<>]+(?:kebnanews|aftonews)[^\s\"<>]*',r.text)))[:10]
  if key=='copras_crossref' and r.status_code==200:
   m=r.json()['message'];result['Metadata']={x:m.get(x) for x in ['title','author','published','published-online','published-print','DOI','link']}
  return result
 except Exception as e:return dict(Key=key,URL=url,Error=str(e))
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool: results=list(pool.map(get,targets.items()))
(OUT/'access_checks.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps(results,ensure_ascii=False,indent=2))
