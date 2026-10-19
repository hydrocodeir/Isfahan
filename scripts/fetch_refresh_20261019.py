"""Retrieve bounded primary evidence; log real access status and fingerprints."""
import concurrent.futures, hashlib, html, json, pathlib, re, sys
from urllib.parse import urljoin
import requests
sys.stdout.reconfigure(encoding='utf-8')
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=ROOT/'reports/deep_refresh_2026_10_19'
(OUT/'files').mkdir(exist_ok=True)
registry=json.loads((OUT/'registry_unmatched.json').read_text('utf-8'))
jobs=[('A'+str(i).zfill(2),w.get('url') or 'https://doi.org/'+w['doi']) for i,w in enumerate(registry) if i in [0,1,2,3,6,10,11,12,13,14,18,19]]
jobs+=[('A20','https://meetingorganizer.copernicus.org/EGU25/EGU25-1824.html'),
 ('C01','https://kuriteng.com/project/ve-of-tangesorkh-dam-and-transfer-systems.html'),
 ('C02','https://kuriteng.com/project/ve-esfahan-water.html'),
 ('C03','https://kuriteng.com/project/ve-rizgard.html'),
 ('C04','https://kuriteng.com/project/ve-of-supplying-domestic-water-for-basht-region.html'),
 ('C05','https://kuriteng.com/project/value-engineering-ghadir.html'),
 ('C06','https://kuriteng.com/project/value-engineering-north-east-khozestan.html'),
 ('C07','https://kuriteng.com/project/value-engineering-south-east-of-khozestan.html'),
 ('C08','https://kuriteng.com/projects/value-engineering-projects.html'),
 ('C09','https://kuriteng.com/news/tang-e-sork-dam-value-engineering-study-and-transmission-system.html'),
 ('D01','https://iranianarchaeology.org/headline/6124/1404/09/01'),
 ('X01','https://www.google.com/search?q=water+transfer+Khuzestan+Isfahan+studies')]
extra=[('C10','https://kuriteng.com/project/value-engineering-west-dehdasht.html'),
 ('C11','https://kuriteng.com/project/value-engineering-izeh-plain.html'),
 ('N01','https://www.mehrnews.com/news/6973681'),
 ('N02','https://aftabeghtesad.com/جوکار-چرا-انتقال-آب-خِرسان-به-یزد-هنوز/'),
 ('N03','https://www.magiran.com/article/4685527'),
 ('P01','https://www.nature.com/articles/s41598-026-49232-5.pdf'),
 ('P11','https://civilejournal.org/index.php/cej/article/download/352/pdf'),
 ('P12','https://jeg.khu.ac.ir/article_10849_3c2e55b31641e3d4cfd7867dd501c5d9.pdf'),
 ('P13','http://mining.in.ua/articles/volume15_4/08.pdf'),
 ('P18','https://civilejournal.org/index.php/cej/article/download/128/pdf'),
 ('A06P','https://www.sciencedirect.com/science/article/pii/S1570644326000468'),
 ('A00P','https://gdij.usb.ac.ir/article_6027.html'),
 ('A19P','https://grips.repo.nii.ac.jp/record/582/files/k92_fulltext.pdf'),
 ('A06D','https://api.crossref.org/works/10.1016/j.jher.2026.100739'),
 ('A14D','https://api.crossref.org/works/10.82476/jwe.2025.1207089')]
last=[('J01','https://www.grips.ac.jp/en/dtds3/shiro_hishinuma/'),
 ('J02','https://www.grips.ac.jp/cms/wp-content/uploads/2014/08/Thesis_shiro_submitted20130830.pdf'),
 ('J03','https://api.datacite.org/dois/10.82476/jwe.2025.1207089'),
 ('J04','https://www.tandfonline.com/doi/pdf/10.1080/02626667.2013.853879'),
 ('J05','https://kuriteng.com/news/tang-e-sork-dam-value-engineering-study-and-transmission-system.html')]
if '--extra' in sys.argv:jobs=extra
if '--last' in sys.argv:jobs=last
if '--news' in sys.argv:jobs=json.loads((OUT/'extra_news_jobs.json').read_text('utf-8'))
def run(job):
 key,url=job
 try:
  r=requests.get(url,headers={'User-Agent':'ResearchSourceReview/1.0 (public academic metadata)'},timeout=28)
  if 'charset' not in r.headers.get('Content-Type','').lower():r.encoding='utf-8'
  content=r.content;pdf=content.startswith(b'%PDF');name=f'files/{key}'+('.pdf' if pdf else '.html');(OUT/name).write_bytes(content)
  body=re.sub(r'<(script|style)\b.*?</\1>',' ',r.text,flags=re.S|re.I)
  txt=html.unescape(re.sub('<[^>]+>',' ',body));txt=re.sub(r'\s+',' ',txt)
  if not pdf:(OUT/f'files/{key}.txt').write_text(txt,'utf-8')
  links=[{'text':re.sub('<[^>]+>',' ',html.unescape(t)).strip(),'url':urljoin(r.url,html.unescape(u))} for u,t in re.findall(r'<a[^>]+href=["\x27]([^"\x27]+)["\x27][^>]*>(.*?)</a>',r.text,re.I|re.S)] if not pdf else []
  return {'key':key,'url':url,'final_url':r.url,'status':r.status_code,'bytes':len(content),'file':name,'is_pdf':pdf,
    'sha256':hashlib.sha256(content).hexdigest(),'metadata':re.findall(r'<meta[^>]+(?:citation_|dc\.|DC\.|og:)[^>]+>',r.text) if not pdf else [],
    'links':links,'text_start':txt[:600] if not pdf else ''}
 except Exception as e:return {'key':key,'url':url,'error':str(e)}
old=json.loads((OUT/'access_checks.json').read_text('utf-8')) if any(x in sys.argv for x in ['--extra','--last','--news']) else []
out=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
 for r in pool.map(run,jobs):out.append(r);print(r['key'],r.get('status'),r.get('bytes'),r.get('final_url'),r.get('error',''),flush=True)
(OUT/'access_checks.json').write_text(json.dumps(old+out,ensure_ascii=False,indent=2),'utf-8')
print('RETRIEVAL COMPLETE')
