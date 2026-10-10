import json,pathlib,re,unicodedata,difflib,sys
sys.stdout.reconfigure(encoding='utf-8')
R=pathlib.Path(__file__).resolve().parents[1];O=R/'reports/deep_round2_2026_10_10'
b=[('master',s) for s in json.loads((R/'data.json').read_text('utf-8-sig'))['sources']]
for f in ['research_refresh_2026_10_03_candidates.json','news_refresh_2026_10_03.json','four_categories_2026_10_03/candidates.json','refresh_2026_10_10/candidates.json']:
 d=json.loads((R/'reports'/f).read_text('utf-8-sig'));b += [(f,s) for s in d.get('Candidates',d.get('candidates',[]))]
def n(t):return re.sub(r'[^\w]','',unicodedata.normalize('NFKC',str(t or '')).lower().replace('ي','ی').replace('ك','ک'))
a=json.loads((O/'registry_unmatched.json').read_text('utf-8'));out=[]
ids=[1,6,7,8,10,11,12,16,23,30,37,38,39,41,45,47,51,52,53,57,63,70,71,72,73,74,76,84,85,86,87,88,89,90,92,94,95,104,105,106,107,108,109,110,111,112,113,115,117,121,122,124,127,134,135,148]
for i in ids:
 w=a[i];matches=[]
 for origin,s in b:
  ts=[s.get(k,'') for k in ['Title','Title_EN','title']]
  score=max(difflib.SequenceMatcher(None,n(w['title']),n(t)).ratio() for t in ts)
  if score>.4:matches.append({'score':round(score,3),'origin':origin,'id':s.get('Source_ID',s.get('ID',s.get('Candidate_ID'))),'title':s.get('Title',s.get('title')),'url':s.get('URL')})
 out.append({'row':i,'title':w['title'],'doi':w.get('doi'),'closest':sorted(matches,key=lambda x:x['score'],reverse=True)[:3]})
(O/'registry_fuzzy_audit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf-8')
for x in out:print(json.dumps(x,ensure_ascii=False))
