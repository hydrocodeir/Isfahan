import requests,pathlib,json,hashlib,re,concurrent.futures,sys,subprocess
sys.stdout.reconfigure(encoding='utf-8')
O=pathlib.Path(__file__).resolve().parents[1]/'reports/deep_round2_2026_10_10';(O/'files').mkdir(exist_ok=True)
jobs={
 'khersan_legal.pdf':'https://www.dpceonline.it/index.php/dpceonline/article/download/2480/2838',
 'upstream_hsm.pdf':'https://edocs.tib.eu/files/e01fb19/1685135072.pdf',
 'court_news.html':'https://faslino.ir/49417',
 'kebna_interview_aggregator.html':'https://khabarfarsi.com/u/252227087',
 'sabzkuh_news.html':'https://www.iranboom.ir/didehban/zistboom/17032-khabar-970712-008.html',
 'khersan_info.html':'https://iwpco.ir/cs/ProjectsMgmt/188/11',
}
def run(item):
 name,url=item
 try:
  r=requests.get(url,timeout=40);r.raise_for_status();p=O/'files'/name;p.write_bytes(r.content)
  links=re.findall(rb'/URI\s*\((.*?)\)',r.content) if r.content.startswith(b'%PDF') else re.findall(rb'href=[\"\x27]([^\"\x27]+)',r.content)
  wanted=[x.decode('utf-8','replace') for x in links if any(s in x.lower() for s in [b'appendix',b'share',b'docs',b'mehrnews',b'kebna',b'pdf'])]
  return dict(file=name,url=url,final_url=r.url,status=r.status_code,bytes=len(r.content),is_pdf=r.content.startswith(b'%PDF'),sha256=hashlib.sha256(r.content).hexdigest(),interesting_links=wanted)
 except Exception as e:return dict(file=name,url=url,error=str(e))
out=list(concurrent.futures.ThreadPoolExecutor(max_workers=4).map(run,jobs.items()))
(O/'fetch_checks.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf-8')
for x in out:print(json.dumps(x,ensure_ascii=False))
bp=pathlib.Path('C:/Users/psh2610/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin')
for name in ['khersan_legal.pdf','upstream_hsm.pdf']:
 if (O/'files'/name).exists():subprocess.run([str(bp/'pdftoppm.exe'),'-f','1','-singlefile','-scale-to','1400','-png',str(O/'files'/name),str(O/'files'/name.removesuffix('.pdf'))],capture_output=True)
