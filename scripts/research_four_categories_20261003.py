"""Separate discovery, primary evidence, duplicates and documentary gaps."""
import csv,hashlib,io,json,re,html,subprocess
from concurrent.futures import ThreadPoolExecutor
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urlparse,unquote
import requests
from research_refresh_20261003 import norm

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/four_categories_2026_10_03'
ITEMS=[
('خبر','عملیات اجرایی فاز دوم انتقال آب بن-بروجن آغاز شد','https://www.tasnimnews.ir/fa/news/1394/11/20/995911/','بن–بروجن','خبر اجرای پروژه؛ ۲۰ بهمن ۱۳۹۴'),
('خبر','پروژه انتقال آب بن-بروجن سال ۹۶ به بهره‌برداری می‌رسد','https://www.tasnimnews.ir/fa/news/1394/11/20/995983/','بن–بروجن','وعده زمان بهره‌برداری؛ رویداد مشترک با خبر 995911'),
('خبر','۵۵ میلیارد تومان از اوراق مشارکت طرح انتقال آب بن-بروجن جذب نشده است','https://www.tasnimnews.ir/fa/news/1396/06/20/1515979/','بن–بروجن','تأمین مالی پروژه؛ ۲۰ شهریور ۱۳۹۶'),
('خبر','طرح انتقال آب زاینده‌رود از بن به بروجن تا برطرف شدن ابهامات اساسی متوقف شود','https://www.tasnimnews.ir/fa/news/1396/06/25/1520441/','بن–بروجن','موضع مخالف اجرای طرح؛ ۲۵ شهریور ۱۳۹۶'),
('خبر','وزارت‌های نیرو و کشور مقصران اجرایی نشدن پروژه انتقال آب بن-بروجن هستند','https://www.tasnimnews.ir/fa/news/1400/06/24/2572080/','بن–بروجن','موضع احمد راستینه درباره تأمین مالی و آبگیر؛ ۲۴ شهریور ۱۴۰۰'),
('خبر','وزارت نیرو چرا در واگذاری زمین برای پروژه بن-بروجن تعلل می‌کند؟','https://www.tasnimnews.ir/fa/news/1400/01/28/2486452/','بن–بروجن','خبر استناد به مصوبات شورای امنیت؛ اصل مصوبات بازیابی نشده'),
('خبر','نگران تأمین آب شرب نیستیم؛ تکمیل طرح آبرسانی اصفهان با ۲۰ همت اعتبار','https://www.tasnimnews.ir/fa/news/1405/06/16/3691073/','کوهرنگ ۳ / ماندگان','کنترل تکراری؛ همین نشست در اخبار مهر و ایمنا قبلی نیز پوشش دارد'),
('مصاحبه','ارزان‌ترین راه برای انتقال آب به اصفهان، احداث تونل است','https://www.tasnimnews.ir/fa/news/1393/02/31/377073/','بهشت‌آباد','گفت‌وگو درباره گزینه تونل؛ موضع گوینده، نه نتیجه مستقل پژوهشی'),
('مصاحبه','انتقال آب کارون باوجود سدهای فراوان توجیهی ندارد','https://www.tasnimnews.ir/fa/news/1393/06/01/470584/','کارون / بهشت‌آباد','احمدرضا لاهیجان‌زاده؛ در فهرست نامزدهای دور قبلی هم دیده شد'),
('مصاحبه','مناقشه بر سر احداث تونل گلاب ۲ و برداشت آب از زاینده‌رود؛ زاینده‌رود توان بارگذاری جدید ندارد','https://www.iranboom.ir/didehban/zistboom/11056-------2-----------.html','گلاب','بازنشر گزارش/گفت‌وگو؛ هویت ناشر اصلی بررسی شود'),
('مصاحبه','عضو کمپین حمایت از زاگرس: اعتراض به رأی دیوان درباره بهشت‌آباد','https://www.didbaniran.ir/بخش-دسته-بندی-نشده-1/146504-عضو-کمپین-مردمی-حمایت-از-زاگرس-مهربان-رای-دیوان-عدالت-اداری-در-خصوص-اجرای-پروژه-بهشت-آباد-وجاهت-قانونی-ندارد-سازمان-محیط-زیست-به-این-رای-اعتراض-کند','بهشت‌آباد','گفت‌وگوی رسانه‌ای درباره رأی؛ متن خود رأی محسوب نمی‌شود'),
('مصاحبه','محمد درویش: کسب‌وکارهایی سودشان در اجرای طرح‌های انتقال آب است','https://abdimedia.net/mohammad-darwish/water-transfer-plans','انتقال آب / زاینده‌رود','نیازمند مشاهده محتوای اصلی و احراز ارتباط مستقیم؛ صفحه وب چالش ربات دارد'),
('گزارش رسمی/فنی','Adaptation to Climate Change to enhance Food Security and Environmental Quality: Zayandeh Rud Basin, Iran','https://archive.iwmi.org/assessment/files/word/ProjectDocuments/Zayandeh%20Rud/ADAPT%20Final%20Report.pdf','زاینده‌رود / کوهرنگ','گزارش پروژه ADAPT، سعید مرید و همکاران؛ آرشیو IWMI، نه سند مجوز دولت ایران'),
('گزارش رسمی/فنی','Agricultural Transformation in the Zayandeh Rud Catchment','https://www.iwrm-zayandehrud.com/wp-content/uploads/2019/07/inter-3-Agricultural-Transformation.pdf','زاینده‌رود','گزارش پروژه IWRM/inter 3؛ دیدگاه ذی‌نفعان و کشاورزان؛ منبع زمینه‌ای'),
('گزارش رسمی/فنی','2011 – Seismic Network for Khersan 3 Dam and Power Plant Project','https://geopersian.com/en/projects','خرسان ۳','صفحه رسمی مجری پایش لرزه‌ای؛ سابقه پروژه، نه گزارش کامل ارزیابی اثرات محیط زیست'),
('سند','400MW Khersan 3 Hydro Power Plant — CDM Prior Consideration notification','https://cdm.unfccc.int/Projects/PriorCDM/notifications/index_html?s=5440','خرسان ۳','اعلام اولیه دریافت‌شده در ۲۰ اوت ۲۰۱۱؛ نه ثبت نهایی CDM، مجوز محیط‌زیست یا تخصیص آب'),
('سند','نامه سرگشاده سد خرسان ۳ روی میز رییس‌جمهور','https://arw.ir/نامه-سرگشاده-سد-خِرسان-۳-روی-میز-رییس/','خرسان ۳ / کارون','۹ دی ۱۳۹۳؛ متن نامه سازمان‌های غیردولتی؛ امضاهای تصویری/اصل نامه اداری احراز نشده'),
('سند','بیانیه کمیته صیانت از آب استان چارمحال و بختیاری','https://waterresources.blogfa.com/post/708','گلاب ۲ / بهشت‌آباد','متن بیانیه مدنی درباره ماده ۲۱۵ و شورای عالی آب؛ خودِ مصوبه شورا نیست'),
]

def urlkey(url):
    p=urlparse(url or '');path=unquote(p.path)
    m=re.search(r'/(?:news|media)/(?:\d+/\d+/\d+/)?(\d+)',path)
    host=p.netloc.lower().removeprefix('www.')
    if m:return host+'/'+m.group(1)
    return host+path.rstrip('/')+'?'+p.query

def verify(item):
    cat,title,url,project,notes=item
    row=dict(Category=cat,Title=title,URL=url,Project=project,Notes=notes,Checked_Date='2026-10-03')
    key=hashlib.sha256(url.encode()).hexdigest()[:12]
    try:
        r=requests.get(url,timeout=(8,25),headers={'User-Agent':'Mozilla/5.0'})
        row.update(HTTP_Status=r.status_code,Resolved_URL=r.url)
        if r.ok and r.content.startswith(b'%PDF'):
            pdf=OUT/(key+'.pdf');pdf.write_bytes(r.content)
            poppler=Path('C:/Users/psh2610/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin')
            evidence=ROOT/'reports/research_four_categories_2026_10_03_primary_checks.json'
            text=evidence.read_text(encoding='utf-8') if evidence.exists() else ''
            row['Text_Provenance']='Web PDF extraction evidence, retained separately; not local full-text extraction'
            row.update(Local_File=str(pdf.relative_to(ROOT)),SHA256=hashlib.sha256(r.content).hexdigest(),Access='PDF full text')
            subprocess.run([str(poppler/'pdftoppm.exe'),'-f','1','-singlefile','-scale-to','1100','-png',str(pdf),str(OUT/(key+'_cover'))],check=True,capture_output=True)
        elif r.ok:
            title_match=re.search(r'<title[^>]*>(.*?)</title>',r.text,re.S|re.I)
            row['Page_Title']=html.unescape(title_match.group(1)) if title_match else None
            row['Meta_Dates']=re.findall(r'<meta[^>]*(?:article:published_time|DC.Date)[^>]*>',r.text,re.I)
            clean=re.sub(r'<(script|style)[^>]*>.*?</\1>','',r.text,flags=re.S|re.I)
            text=html.unescape(re.sub(r'<[^>]+>',' ',clean));text=' '.join(text.split())
            row['Access']='HTML retrieved; inspect body'
        else:text='';row['Access']='Unavailable'
        p=OUT/(key+'.txt');p.write_text(text,encoding='utf-8');row['Text_File']=str(p.relative_to(ROOT))
        row['Body_Length']=len(text)
        row['Target_Hits']=list(dict.fromkeys(re.findall(r'زاینده.?رود|بهشت.?آباد|کوهرنگ|گلاب|خرسان|ماندگان|بن.?بروجن|کارون|Zayandeh|Khersan|Kuhrang|transfer',text,re.I)))
        if re.search(r'verifying that you are not|bot verification|access denied',text,re.I):row['Access']='Bot/access challenge'
    except (requests.RequestException,ValueError) as e:row.update(Access='Fetch error',Error=type(e).__name__)
    return row

if __name__=='__main__':
    OUT.mkdir(exist_ok=True)
    master=json.loads((ROOT/'data.json').read_text(encoding='utf-8'))['sources']
    keys={};titles=[]
    for s in master:
        for f in ['URL','Canonical_URL','PDF_URL']:
            if s.get(f):keys.setdefault(urlkey(s[f]),[]).append(s['Source_ID'])
        titles.append((s['Source_ID'],norm(s.get('Title')),norm(s.get('Title_EN'))))
    with ThreadPoolExecutor(max_workers=8) as pool:rows=list(pool.map(verify,ITEMS))
    previous=[]
    for fname in ['news_refresh_2026_10_03.json']:
        previous+=json.loads((ROOT/'reports'/fname).read_text(encoding='utf-8'))['Candidates']
    for r in rows:
        r['Existing_Matches']=sorted(set(keys.get(urlkey(r['URL']),[])))
        t=norm(r['Title']);r['Similar_Titles']=[sid for sid,a,b in titles if max(SequenceMatcher(None,t,a).ratio(),SequenceMatcher(None,t,b).ratio())>.88]
        r['Previously_Discovered']=any(urlkey(r['URL'])==urlkey(p['URL']) for p in previous)
        r['Disposition']='duplicate' if r['Existing_Matches'] or r['Similar_Titles'] else ('needs_review' if r['Access'] in ['Unavailable','Fetch error','Bot/access challenge'] or not r.get('Target_Hits') else 'candidate')
        print(r['Category'],r['Disposition'],r['HTTP_Status'] if 'HTTP_Status' in r else None,r['Title'],r['Existing_Matches'],r.get('Target_Hits'))
    data={'Checked_Date':'2026-10-03','Baseline':len(master),'Master_Modified':False,'Queries':40,'Candidates':rows,'Documentary_Gaps':[
        'اصل رأی قضایی بهشت‌آباد با شماره دادنامه و متن کامل مستقل پیدا نشد؛ مصاحبه درباره رأی جایگزین آن نیست.',
        'اصل مصوبه شورای عالی آب درباره گلاب با امضا و شماره مصوبه پیدا نشد؛ بیانیه مدنی فقط سرنخ است.',
        'اصل مجوز ماده ۲۳ ماندگان/خرسان در این دور بازیابی نشد؛ ادعای کانال تلگرام احراز اصالت نشده است.',
        'گزارش کامل EIA خرسان ۳ یا ماندگان از ناشر رسمی بازیابی نشد؛ خبر ارزیابی با خودِ گزارش تفاوت دارد.'
    ]}
    (OUT/'candidates.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    fields=['Category','Disposition','Title','URL','Project','Access','Existing_Matches','Similar_Titles','Previously_Discovered','Notes']
    with (OUT/'candidates.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
