import json,pathlib,re,unicodedata,difflib,urllib.parse,sys,collections,hashlib
sys.stdout.reconfigure(encoding='utf-8')
ROOT=pathlib.Path(__file__).resolve().parents[1]; OUT=ROOT/'reports/refresh_2026_10_10'
main=json.loads((ROOT/'data.json').read_text('utf-8-sig'))
rows=json.loads((OUT/'candidates_draft.json').read_text('utf-8'))
prevfiles=['reports/research_refresh_2026_10_03_candidates.json','reports/news_refresh_2026_10_03.json','reports/four_categories_2026_10_03/candidates.json']
baseline=[('master',s) for s in main['sources']]
for filename in prevfiles:
 d=json.loads((ROOT/filename).read_text('utf-8-sig'))
 baseline.extend((filename,s) for s in d.get('candidates',d.get('Candidates',[])))
def norm(t):
 t=unicodedata.normalize('NFKC',str(t or '')).lower().translate(str.maketrans('يك','یک'))
 return re.sub(r'[^\w]','',t)
def strings(d):
 if isinstance(d,dict):
  for v in d.values():yield from strings(v)
 elif isinstance(d,list):
  for v in d:yield from strings(v)
 elif isinstance(d,str):yield d
def urlkey(u):
 try:
  x=urllib.parse.urlsplit(urllib.parse.unquote(u));host=x.netloc.lower().removeprefix('www.').replace('tasnimnews.com','tasnimnews.ir')
  path=x.path.rstrip('/').removesuffix('/amp').rstrip('/')
  m=re.search(r'/news/(?:\d{4}/\d{2}/\d{2}/)?(\d+)',path)
  if m:path='/news/'+m[1]
  return host+path
 except:return u
audit=[]
for row in rows:
 exact=[]; fuzzy=[]
 ownurls={urlkey(row[k]) for k in ['URL','Original_URL','PDF_URL'] if row.get(k)}
 ownnorm=norm(row['Title']);doi=str(row.get('DOI','')).lower()
 for origin,s in baseline:
  flat=list(strings(s));alltext=' '.join(flat).lower()
  su={urlkey(v) for v in flat if v.startswith(('http://','https://'))}
  st=s.get('Title',s.get('title',''));ste=s.get('Title_EN','')
  if (doi and doi in alltext) or ownurls&su or ownnorm in [norm(st),norm(ste)]:exact.append({'Origin':origin,'ID':s.get('Source_ID',s.get('Candidate_ID')),'Title':st})
  score=max(difflib.SequenceMatcher(None,ownnorm,norm(st)).ratio(),difflib.SequenceMatcher(None,ownnorm,norm(ste)).ratio())
  if score>0.48:fuzzy.append({'score':round(score,3),'Origin':origin,'ID':s.get('Source_ID',s.get('Candidate_ID')),'Title':st})
 row['Exact_Duplicate_Matches']=exact
 if exact:row['Status']='duplicate_review'
 if row.get('Local_File'):
  file=OUT/row['Local_File'];row['SHA256']=hashlib.sha256(file.read_bytes()).hexdigest()
 audit.append({'ID':row['ID'],'exact':exact,'closest':sorted(fuzzy,key=lambda s:s['score'],reverse=True)[:3]})
(OUT/'dedup_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),'utf-8')
(OUT/'candidates.json').write_text(json.dumps({'Search_Date':'2026-10-10','Baseline_Count':len(main['sources']),'Previous_Candidate_Files':prevfiles,'Master_Modified':False,'Candidates':rows},ensure_ascii=False,indent=2),'utf-8')
for a in audit:print(json.dumps(a,ensure_ascii=False))
labels={'articles':'مقاله‌ها','news':'خبرها','interviews':'مصاحبه‌ها','official_reports':'گزارش‌های رسمی نهادی و پژوهشی','documents':'اسناد و بیانیه‌ها'}
rows_by={k:[r for r in rows if r['Category']==k] for k in labels}
def describe(r):
 lines=[f"### {r['ID']} — {r['Title']}", '', f"- وضعیت: {'نامزد تاییدشده برای ورود' if r['Status']=='candidate_verified' else 'نیازمند تکمیل اعتبارسنجی'}",f"- ناشر: {r.get('Publisher','نامشخص')}", f"- تاریخ: {r.get('Date_Persian',r.get('Date','نامشخص'))}", f"- پروژه/حوضه: {r['Project']}", f"- ارتباط: {'زمینه‌ای؛ مدیریت تقاضا و اقتصاد آب' if r['Relation']=='context' else 'مستقیم یا دارای بخش مشخص درباره طرح انتقال'}", f"- منبع: [{r['Title']}]({r['URL']})"]
 if r.get('DOI'):lines.append(f"- DOI: {r['DOI']}")
 if r.get('Authors'):lines.append(f"- نویسنده/نویسندگان: {r['Authors']}")
 if r.get('Person'):lines.append(f"- گوینده: {r['Person']}")
 if r.get('Local_File'):lines.append(f"- نسخه محلی: [{r['Local_File']}]({r['Local_File']})")
 lines += [f"- دسترسی و بررسی: {r['Access']}",f"- ارزش برای بانک: {r['Summary']}",f"- ملاحظات: {r['Notes']}",'']
 return '\n'.join(lines)
for category,rs in rows_by.items():
 (OUT/(category+'.md')).write_text('# '+labels[category]+'\n\n'+'\n'.join(describe(r) for r in rs),'utf-8')
counts=collections.Counter(r['Category'] for r in rows if r['Status']=='candidate_verified')
report=['# بازبینی منابع انتقال آب — ۱۰ اکتبر ۲۰۲۶','', 'جست‌وجوی تازه با کلیدواژه‌های فارسی و انگلیسی پروژه‌های بهشت‌آباد، خرسان، کوهرنگ، گلاب، چشمه لنگان، خدنگستان، ماندگان، بن–بروجن، انتقال آب دریا و شاخه‌های مرتبط انجام شد. دامنه شامل حوضه‌های کارون و زاینده‌رود و آثار مرتبط است. منابع جهانی بدون مطالعه موردی مرتبط کنار گذاشته شدند.','',
 'نتیجه: **۱۱ نامزد تازه نسبت به ۹۸۵ رکورد بانک و سه فهرست نامزد ۳ اکتبر**، به‌علاوه **۳ سرنخ نیازمند تکمیل**. تازه بودن به معنای نبودن در بانک و فهرست‌های قبلی است، نه الزاماً انتشار در هفته اخیر. دیتاست اصلی، فایل اکسل و داشبورد تغییر نکرده‌اند.','',
 '| دسته | نامزد تاییدشده | نیازمند تکمیل | فهرست تفصیلی |','|---|---:|---:|---|']
for k in labels:report.append(f"| {labels[k]} | {counts[k]} | {sum(r['Status']=='needs_primary' for r in rows_by[k])} | [{labels[k]}]({k}.md) |")
report += ['', '## یافته‌های مهم و نحوه استفاده','',
 '- N01 مستقیماً طراحی و اقتصاد انتقال خرسان به کرمان را بررسی می‌کند؛ عنوان آن نام پروژه را ندارد و به همین دلیل جست‌وجو در متن اهمیت داشت.',
 '- N02 و N03 دو انتشار با DOI مجزا ولی نویسندگان، سناریوها و نتایج بسیار نزدیک هستند؛ برای مرور نظام‌مند یک خوشه مطالعاتی با پیوند متقابل ثبت شوند، نه دو تایید مستقل.',
 '- N07 پرسش‌وپاسخ درباره ارزیابی ماندگان را در مصاحبه‌ای با عنوان عمومی محیط‌زیست ثبت می‌کند. این اظهارات جای گزارش اصلی ارزیابی را نمی‌گیرند.',
 '- N08 نسخه کامل روزنامه‌ای از مصاحبه مهران زینلیان است. تاریخ ثبت‌شده تاریخ بازنشر روزنامه است؛ نشانی ایرنا یک نسخه دیگر همان مصاحبه است.',
 '- N09 و N10 گزارش‌های رسمی خروجی پروژه‌های پژوهشی نهادها هستند و ارتباط زمینه‌ای دارند. هیچ‌یک گزارش ارزیابی اثرات محیط‌زیستی ماندگان یا خرسان نیستند.',
 '- N11 متن بازنشرشده بیانیه مدنی است؛ ادعاها به صادرکنندگان نسبت داده شوند و در رده اسناد دولتی قرار نگیرد.','',
 '## روش تطبیق و اعتبارسنجی','',
 'DOI، نشانی اصلی و PDF، شناسه خبر مستقل از اسلاگ و دامنه‌های com/ir، عنوان فارسی و انگلیسی پس از یکسان‌سازی ی/ک و فاصله‌ها با بانک و فهرست‌های قبلی تطبیق داده شد. موارد مشابه نیز از نظر ناشر، نویسنده، زمان و نوع سند بازبینی شدند. چهار PDF دریافت شد؛ جلد/صفحه اول و صفحه کامل مصاحبه مشاهده شد. متن کامل انگلیسی COPRAS در دسترس نبود؛ اعتبار کتابشناختی آن از Crossref و چکیده دامنه ناشر کنترل شد.','',
 'نمونه منابع حذف‌شده به علت وجود در بانک: S251 (مقاله مدل‌سازی و مناقشه آب)، S273 (اثر انتقال بر زیستگاه ماهیان چشمه لنگان)، S303 (تجمع اعتراض به تونل‌ها)، S379 (خبر مجوز گلاب)، S390 (آب دریا و صنایع)، S965/S967 (وضعیت مجوز ماندگان)، S979 (اعتراض یاسوج). گزارش inter3 سال ۲۰۱۸ نیز یافته قبلی بود و دوباره شمرده نشد.','',
 'تفاوت‌های بررسی‌شده: S506 نویسندگان و انتشار دیگری نسبت به مقالات COPRAS دارد؛ S332 فصل کتاب است و با گزارش IEEM تفاوت دارد؛ S074 نامه سال ۲۰۱۷ است و با بیانیه ۲۰۲۱ N11 یک سند نیست. N09 با S351 و گزارش inter3 در یک برنامه پژوهشی قرار دارد ولی گزارش مجزایی است.','',
 '## خلأهای باقی‌مانده','',
 'در جست‌وجوی این نوبت اصل قابل احراز مصوبه شورای عالی آب برای ماندگان/گلاب، مجوز ماده ۲۳ ماندگان، متن کامل گزارش رسمی ارزیابی محیط‌زیستی ماندگان/خرسان و دادنامه بهشت‌آباد با مشخصات ثبتی پیدا نشد. یافت نشدن در وب اثبات نبودن سند نیست. خبر یا نقل اظهارات مسئول به عنوان اصل این اسناد ثبت نشده است.','',
 'P01 مقاله فارسی جدیدی است که فعلاً فقط نمایه آن قابل مشاهده بود؛ P02 گزارش ATB سال ۲۰۱۹ فقط از ارجاع نهادی شناسایی شد؛ P03 نامه به نهاد ریاست جمهوری فقط از خبرخوان به دست آمد. این سه مورد وارد شمار ۱۱ منبع نشدند.','',
 '## فایل‌های پژوهش','',
 '- [فراداده نامزدها و موارد در انتظار](candidates.json)',
 '- [ممیزی حذف تکراری‌ها](dedup_audit.json)',
 '- [کلیدواژه‌ها و عبارت‌های اجراشده](search_log.json)',
 '- [وضعیت دریافت فایل‌ها و هش](access_checks.json)',
 '', 'وضعیت HTTP به‌تنهایی معیار دسترسی نبود: صفحه مسدود مگیران و صفحه بدون محتوای ایرنا با وجود پاسخ ۲۰۰، متن معتبر محسوب نشدند.']
(OUT/'report.md').write_text('\n'.join(report)+'\n','utf-8')
assert len(main['sources'])==985
assert len([r for r in rows if r['Status']=='candidate_verified'])==11
assert len({r['ID'] for r in rows})==len(rows)
assert not any(r['Exact_Duplicate_Matches'] for r in rows)
print('FINAL: 11 verified candidates; 3 pending; main unchanged; reports generated.')
