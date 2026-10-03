import csv,json
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/four_categories_2026_10_03'
p=OUT/'candidates.json';d=json.loads(p.read_text(encoding='utf-8'))
for r in d['Candidates']:
    if 'Prior Consideration' in r['Title']:
        r.update(Disposition='candidate',Access='Official record verified via web; direct HTTP returned access challenge',Evidence_File='reports/four_categories_2026_10_03/unfccc_web_evidence.json',Date_Gregorian='2011-08-20')
    if 'Agricultural Transformation' in r['Title']:
        r.update(Title='Agricultural Transformation: Experts’ Recommendations for the Zayandeh Rud Catchment',Date_Gregorian='2018-12',Author='Lena Horlemann; Mohammad Naser Reyhani; Ali Asghar Besalatpour; Shahrooz Mohajeri',Publisher='inter 3 / IWRM Zayandeh Rud; BMBF-funded project')
    if r.get('Local_File'):
        r['Text_File']=None;r['Evidence_File']='reports/research_four_categories_2026_10_03_primary_checks.json';r['Notes']+=' PDF دریافت و جلد آن مشاهده شد؛ متن مرتبط در نمایه PDF بررسی شده، استخراج کامل محلی متن انجام نشده است.'
    if 'ارزان' in r['Title']:r.update(Interviewee='رسول زرگرپور',Date_Persian='1393/02/31')
    if 'توجیهی ندارد' in r['Title']:r.update(Interviewee='احمدرضا لاهیجان‌زاده',Date_Persian='1393/06/01')
    if 'کمپین' in r['Title']:r['Interviewee']='یوسف فرهادی بابادی'
    if 'ابهامات اساسی' in r['Title']:r['Interviewee']='حمیدرضا فولادگر'
    if 'نامه سرگشاده' in r['Title']:r['Date_Persian']='1393/10/09'
    if 'کمیته صیانت' in r['Title']:r['Date_Persian']='1395/11/10'
d['Summary']=dict(Counter(r['Disposition'] for r in d['Candidates']))
p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
fields=['Category','Disposition','Title','URL','Project','Access','Existing_Matches','Similar_Titles','Previously_Discovered','Notes']
with (OUT/'candidates.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(d['Candidates'])
names={'خبر':'news','مصاحبه':'interviews','گزارش رسمی/فنی':'reports','سند':'documents'}
labels={'candidate':'قابل بررسی برای افزودن؛ تطبیق با بانک یافت نشد','duplicate':'تکراری در بانک','needs_review':'نیازمند دسترسی/بررسی بیشتر'}
for category,name in names.items():
    rows=[r for r in d['Candidates'] if r['Category']==category]
    lines=[f'# {category} — بررسی ۳ اکتبر ۲۰۲۶','', '| عنوان | پروژه | نتیجه | نوع دسترسی | یادداشت |','|---|---|---|---|---|']
    for r in rows:lines.append(f"| [{r['Title']}]({r['URL']}) | {r['Project']} | {labels[r['Disposition']]} {', '.join(r['Existing_Matches'])} | {r['Access']} | {r['Notes']} |")
    if category=='سند':lines+=['','## شکاف‌های سندی','']+['- '+s for s in d['Documentary_Gaps']]
    (OUT/(name+'.md')).write_text('\n'.join(lines)+'\n',encoding='utf-8')
lines=['# بررسی دوباره خبر، مصاحبه، گزارش رسمی و سند','', 'تاریخ: ۳ اکتبر ۲۰۲۶ / ۱۱ مهر ۱۴۰۵. بانک مبنا: ۹۸۵ رکورد. فایل اصلی بانک تغییر نکرده است.', '', '۴۰ عبارت جست‌وجوی تازه به‌همراه کنترل صفحات منتخب انجام شد. جست‌وجوی اولیه، دامنه رسمی، آرشیو فنی و پیگیری اسناد جدا ثبت شده‌اند. ۱۸ یافته منتخب با URL استاندارد، شناسه خبر، عنوان فارسی/انگلیسی و نشانی PDF با بانک تطبیق داده شد. خروجی: ۱۶ نامزد فاقد تطبیق با بانک، یک منبع تکراری S959، و یک مورد نیازمند دسترسی بیشتر. از ۱۶ نامزد، مصاحبه 470584 در گزارش دور قبل هم معرفی شده بود؛ بنابراین ۱۵ یافته نسبت به آن فهرست تازه‌اند.', '', '| دسته | نامزد فاقد تطبیق | تکراری | نیازمند بررسی بیشتر | گزارش |','|---|---:|---:|---:|---|']
for category,name in names.items():
    c=Counter(r['Disposition'] for r in d['Candidates'] if r['Category']==category)
    lines.append(f"| {category} | {c['candidate']} | {c['duplicate']} | {c['needs_review']} | [{category}]({name}.md) |")
lines+=['', '## یافته‌های مهم و نحوه استفاده', '', 'خبرهای بن–بروجن، زنجیره آغاز اجرا، وعده افتتاح، جذب اوراق، اختلاف بر سر آبگیر و درخواست توقف را تکمیل می‌کنند؛ دو خبر 995911 و 995983 پوشش یک مراسم‌اند و نباید دو رویداد مستقل شمرده شوند. خبر 3691073 از قبل در S959 موجود بود و حذف شد.', '', 'مصاحبه رسول زرگرپور گزینه تونل بهشت‌آباد را از دید مقام اجرایی شرح می‌دهد؛ مصاحبه لاهیجان‌زاده دیدگاه مخالف را ثبت می‌کند. گزارش گلاب در ایران‌بوم، بازنشر رسانه‌ای است. گفت‌وگوی یوسف فرهادی درباره رأی دیوان سند قضایی محسوب نمی‌شود. کلیپ عبدی‌مدیا به علت مشکل دسترسی و احراز نشدن متن کامل در انتظار باقی ماند.', '', 'گزارش ADAPT در آرشیو IWMI مستقیماً سناریوی بهشت‌آباد و عرضه و تقاضای زاینده‌رود را بررسی می‌کند. گزارش توصیه کارشناسان تحول کشاورزی، دسامبر ۲۰۱۸، گزارش رسمی پروژه IWRM با تأمین مالی BMBF است و منبع زمینه‌ای برای مدیریت تقاضاست. صفحه Geopersian سابقه اجرای شبکه لرزه‌نگاری خرسان را ثبت می‌کند؛ این صفحه گزارش کامل طراحی یا EIA نیست.', '', 'در دسته اسناد، اعلام اولیه 400MW Khersan 3 در سامانه UNFCCC/CDM به تاریخ ۲۰ اوت ۲۰۱۱ پیدا شد. این اعلام اولیه نه ثبت نهایی CDM است، نه مجوز محیط‌زیست و نه مجوز انتقال آب. نامه سرگشاده خرسان و بیانیه کمیته صیانت متن مدنی‌اند؛ ادعاهایشان باید به نویسندگان منتسب شوند. هیچ‌یک جایگزین متن مصوبه، مجوز اداری یا دادنامه نیست.', '', '## محدودیت‌ها', '', 'جدید به معنی تازه‌یافته برای بانک است، نه لزوماً تازه‌منتشرشده. رکوردهای انتخاب‌شده عمدتاً تاریخی‌اند و برای تکمیل سیر پروژه مفیدند. جست‌وجوی مستقیم دامنه‌های rc.majlis.ir، doe.ir، esrw.ir، iwpco.ir و chbwater.ir نتیجه نمایه‌شده نداد؛ این به معنی نبود سند در سازمان نیست. HTTP 200 به‌تنهایی معیار پذیرش نبود؛ صفحه UNFCCC در درخواست مستقیم چالش دسترسی داشت ولی رکورد از ابزار وب قابل مشاهده بود. PDFهای ADAPT و IWRM به همراه SHA-256 نگهداری شده‌اند. تطبیق عنوان خودکار جایگزین کنترل انسانی هنگام ادغام نهایی نیست.', '', '## اسناد رسمی همچنان بازیابی‌نشده','']+['- '+s for s in d['Documentary_Gaps']]
(OUT/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
assert len(d['Candidates'])==18
assert d['Summary']=={'candidate':16,'duplicate':1,'needs_review':1}
assert len(json.loads((ROOT/'data.json').read_text(encoding='utf-8'))['sources'])==985
print(d['Summary'])
