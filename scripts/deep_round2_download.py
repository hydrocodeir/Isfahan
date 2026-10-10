import json,pathlib,requests,re,concurrent.futures,sys,subprocess,hashlib,urllib.parse
sys.stdout.reconfigure(encoding='utf-8')
O=pathlib.Path(__file__).resolve().parents[1]/'reports/deep_round2_2026_10_10';a=json.loads((O/'primary_access.json').read_text('utf-8'))
jobs=[]
for x in a:
 for m in x.get('metadata',[]):
  if 'citation_pdf_url' in m:
   url=re.search(r'''content=["']([^"']+)["']''',m)[1];jobs.append((x['key'],url))
jobs += [('tender4977','https://static2.esfahanemrooz.ir/servev2/LKA3SQ9XN7gT/Kl4CadDoeE4bRz50Hlni6LGql1ADMwHQ4Wu5Wxs5ff4%2C/esfahanemrooz4977.pdf'),('gandoman','https://rsis.ramsar.org/RISapp/files/47382230/documents/IR2558_mgt240312.pdf'),('choghakhor','https://rsis.ramsar.org/RISapp/files/RISrep/IR1939RIS.pdf')]
def run(item):
 key,url=item
 try:
  r=requests.get(url,timeout=35);r.raise_for_status();is_pdf=r.content.startswith(b'%PDF')
  f=f'files/download_{key}.pdf' if is_pdf else f'files/download_{key}.html';(O/f).write_bytes(r.content)
  return dict(key=key,url=url,status=r.status_code,is_pdf=is_pdf,file=f,bytes=len(r.content),sha256=hashlib.sha256(r.content).hexdigest())
 except Exception as e:return dict(key=key,url=url,error=str(e))
out=list(concurrent.futures.ThreadPoolExecutor(max_workers=4).map(run,jobs))
(O/'downloads.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf-8')
bp=pathlib.Path('C:/Users/psh2610/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin')
for x in out:
 print(json.dumps(x,ensure_ascii=False),flush=True)
 if x.get('is_pdf'):
  args=[str(bp/'pdftoppm.exe'),'-f','1','-l','8','-scale-to','1700','-png'] if x['key']=='tender4977' else [str(bp/'pdftoppm.exe'),'-f','1','-singlefile','-scale-to','1300','-png']
  subprocess.run(args+[str(O/x['file']),str(O/'files'/('cover_'+x['key']))],capture_output=True)
