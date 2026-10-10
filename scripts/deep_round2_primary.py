import json,pathlib,requests,concurrent.futures,re,sys,hashlib,html
sys.stdout.reconfigure(encoding='utf-8')
O=pathlib.Path(__file__).resolve().parents[1]/'reports/deep_round2_2026_10_10';A=json.loads((O/'registry_unmatched.json').read_text('utf-8'))
ids=[1,8,12,45,52,57,73,76,86,87,89,92,95,108,110,111,112,113,121,122,124,135]
jobs=[(str(i),'https://doi.org/'+A[i]['doi'] if A[i].get('doi') else A[i]['url']) for i in ids]
jobs += [('court_appendix','https://1drv.ms/w/c/7a8d2f97b29d57fc/Ea2LzatMbz5LstxLNYdSXkkBY2uVc9DWDMlD71cgDdtLLA?e=bSBBh9')]
def run(item):
 key,url=item
 try:
  r=requests.get(url,timeout=35);raw=r.content;ispdf=raw.startswith(b'%PDF');ext='pdf' if ispdf else 'html';f=f'files/primary_{key}.{ext}';(O/f).write_bytes(raw)
  txt=html.unescape(re.sub('<[^>]+>',' ',r.text)) if not ispdf else ''
  txt=re.sub(r'\s+',' ',txt)
  if txt:(O/f'files/primary_{key}.txt').write_text(txt,'utf-8')
  meta=re.findall(r'<meta[^>]+(?:citation_|dc\.|DC\.|og:)[^>]+>',r.text)
  links=re.findall(r'href=[\"\x27]([^\"\x27]+)',r.text)
  return dict(key=key,url=url,final_url=r.url,status=r.status_code,bytes=len(raw),file=f,is_pdf=ispdf,sha256=hashlib.sha256(raw).hexdigest(),metadata=meta,download_links=[html.unescape(x) for x in links if any(w in x for w in ['.pdf','download','article/view'])],text_start=txt[:800])
 except Exception as e:return dict(key=key,url=url,error=str(e))
out=list(concurrent.futures.ThreadPoolExecutor(max_workers=4).map(run,jobs))
(O/'primary_access.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf-8')
for x in out:print(json.dumps(x,ensure_ascii=False))
