"""Fetch public research candidates; retain metadata and links for human curation."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]

def fetch(row):
    out = dict(row)
    try:
        r = requests.get(row['url'], timeout=25, headers={'User-Agent': 'Mozilla/5.0'})
        out.update(status=r.status_code, final_url=r.url, sha256=hashlib.sha256(r.content).hexdigest())
        s = BeautifulSoup(r.content, 'html.parser')
        out['page_title'] = s.title.get_text(' ', strip=True) if s.title else ''
        out['meta'] = {m.get('property') or m.get('name'): m.get('content') for m in s.select('meta[content]') if any(t in (m.get('property') or m.get('name') or '') for t in ['title','date','time','description','author'])}
        out['links'] = [{'text': a.get_text(' ',strip=True), 'url': a['href']} for a in s.select('a[href]') if any(t in a.get_text(' ',strip=True) for t in ['منبع','متن خبر','ادامه خبر','ماندگان']) or any(t in a['href'] for t in ['tn.ai','wif4','pdf'])][:100]
        for el in s(['script','style','nav','footer','header']):
            el.decompose()
        lines = [line.strip() for line in s.get_text('\n',strip=True).splitlines()]
        out['context'] = '\n'.join(lines)[:55000]
    except Exception as e:
        out['error'] = str(e)
    return out

if __name__ == '__main__':
    rows = json.loads((ROOT/'reports/mandegan_candidates.json').read_text(encoding='utf-8'))
    rows = [r for r in rows if not any(t in r['url'] for t in ['vista.ir/t/','t.me/','telegram.me/','wikipedia','blogfa','reddit','khabarfarsi.com/ua/'])]
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(fetch, rows))
    # Working evidence stays outside the committed report: reports contain curated summaries.
    temp = ROOT/'reports/_tmp_mandegan_fetch.json'
    temp.write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    for i,r in enumerate(results):
        print(i,r.get('status',r.get('error')),r['title'])
        for link in r.get('links',[]):
            if any(t in link['text'] for t in ['منبع','متن خبر','ادامه خبر']):
                print(' ORIGINAL',link['url'])
