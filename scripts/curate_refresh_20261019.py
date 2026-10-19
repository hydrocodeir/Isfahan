"""Curated primary-source decisions, with uncertainty and duplicate evidence retained."""
import copy, difflib, hashlib, html, json, pathlib, re, sys, unicodedata
from urllib.parse import urlsplit, unquote
sys.stdout.reconfigure(encoding='utf-8')
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=ROOT/'reports/deep_refresh_2026_10_19';TODAY='2026-10-19'
def read(p):return json.loads(p.read_text('utf-8-sig'))
def save(name,v):(OUT/name).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n','utf-8')
def norm(v):return re.sub(r'[^\w]','',unicodedata.normalize('NFKC',str(v or '')).casefold().replace('ي','ی').replace('ك','ک'))
def urlkey(v):
 u=urlsplit(unquote(v or ''));host=u.netloc.casefold().removeprefix('www.')
 m=re.search(r'/news/(?:\d{4}/\d{2}/\d{2}/)?(\d+)',u.path)
 if m:return host+'/news/'+m[1]
 return host+u.path.rstrip('/')
base=read(ROOT/'data.json'); reg=read(OUT/'registry_unmatched.json'); access={x['key']:x for x in read(OUT/'access_checks.json')}
sources=[];studies=[];projects=[];source_updates=[];study_updates=[]
def source(key,title,summary,pids,**kw):
 a=access[key];r=dict.fromkeys(base['sources'][0]);url=a.get('final_url') or a['url']
 r.update(Title=title,Summary=summary,URL=url,Canonical_URL=url,Language='فارسی',Reliability='B',Primary_or_Secondary='Primary',
          Source_Type='معرفی رسمی مطالعه / خدمات مشاوره',Full_Text='Yes',PDF_Status='Landing Page Only',
          Position_Stance='تحلیلی / خنثی',Topic='مطالعات و تحقیقات انتقال آب',Publisher=urlsplit(url).netloc)
 r.update(kw);date=r.get('Date_Gregorian') or r.get('Date_Persian')
 if date and not r.get('Year'):r['Year']=int(date[:4])
 if not r['PDF_URL'] and a.get('is_pdf'):r['PDF_URL']=url
 if r['PDF_URL']:r['PDF_Status']='Direct Link Available'
 pdfkey=kw.pop('_pdfkey',None)
 if pdfkey:
  p=access[pdfkey];assert p.get('is_pdf') and p['status']==200
  r['PDF_URL']=p['final_url'];r['PDF_Status']='Direct Link Available';r['Local_PDF']=(OUT/p['file']).relative_to(ROOT).as_posix();r['SHA256']=p['sha256']
 r.pop('_pdfkey',None)
 notes=r.get('Notes') or ''
 r['Notes']=f'مرور عمیق {TODAY}؛ شاهد {key}. '+notes
 sources.append({'key':key,'record':r,'project_ids':pids,'retrieval_key':key})
 return key
def study(key,title,category,pids,performer,client,period,scope,cooperation='داخلی',cooperation_type='domestic',evidence='صفحه اولیه بررسی شد'):
 studies.append(dict(title_fa=title,subcategory=category,project_ids=pids,performer=performer,commissioner_or_funder=client,
  period=period,scope=scope,cooperation=cooperation,cooperation_type=cooperation_type,evidence=evidence,source_keys=[key]))
def project(i,name,origin,destination,provinces,kind,keys,status,date=None,downstream=None):
 projects.append(dict(id=f'WT-T{i:02}',research_id=f'T{i:02}',name_fa=name,name_en=None,project_tag=name,origin=origin,destination=destination,
  provinces=provinces,downstream_or_shared=downstream or [],transfer_type=kind,status_evidence=status,status_as_of=date,source_keys=keys,annual_volume_mcm=None))

# Consultancy records: a study year is not represented as the publication date of an undated web page.
consult=[('C01','مهندسی ارزش سد تنگ‌سرخ و سامانه انتقال','WT-T14',1397,'شرکت آب منطقه‌ای کهگیلویه و بویراحمد','کهگیلویه و بویراحمد؛ فارس'),
 ('C02','مهندسی ارزش آبرسانی به شهرها و روستاهای غرب اصفهان','WT-T19',1399,'شرکت آب منطقه‌ای اصفهان','اصفهان'),
 ('C03','مهندسی ارزش بهره‌برداری کانال‌های انتقال سیلاب کارون به کانون‌های ریزگرد','WT-T20',1399,'سازمان آب و برق خوزستان','خوزستان'),
 ('C04','مهندسی ارزش آبرسانی شرب و صنعت باشت','WT-T21',1398,'شرکت آب منطقه‌ای کهگیلویه و بویراحمد','کهگیلویه و بویراحمد'),
 ('C05','مهندسی ارزش تصفیه‌خانه طرح غدیر','WT-T11',1394,'سازمان آب و برق خوزستان','خوزستان'),
 ('C06','مهندسی ارزش آبرسانی شهرهای شمال‌شرق خوزستان','WT-T22',1394,'سازمان آب و برق خوزستان','خوزستان'),
 ('C07','مهندسی ارزش آبرسانی شهرهای جنوب‌شرق خوزستان','WT-T23',1394,'سازمان آب و برق خوزستان','خوزستان'),
 ('C10','پیشنهاد تغییر به روش مهندسی ارزش تأمین و انتقال آب و شبکه آبیاری دهدشت غربی','WT-T24',1390,'شرکت آب منطقه‌ای کهگیلویه و بویراحمد','کهگیلویه و بویراحمد'),
 ('C11','مهندسی ارزش تأمین و انتقال آب کشاورزی و شرب دشت ایذه','WT-T25',1390,'سازمان آب و برق خوزستان','خوزستان')]
for key,title,pid,year,client,province in consult:
 summary=f'وبگاه رسمی کریت‌کارا این مطالعه را با کارفرمای {client} و سال پروژه {year} ثبت کرده است. اصل قرارداد، مبلغ و گزارش نهایی در این صفحه ارائه نشده است.'
 if key=='C01':summary+=' خبر کارگاه شرکت، حضور آبدان‌فراز به عنوان مشاور طرح و آب منطقه‌ای فارس را نیز ثبت می‌کند؛ رکورد سد و سامانه انتقال، اثبات وضعیت اجرایی کنونی خط انتقال به شیراز نیست.'
 source(key,title,summary,[pid],Publisher='مهندسان مشاور کریت‌کارا',Organization=client,Author='مهندسان مشاور کریت‌کارا',Province=province,
        Notes=f'سال {year} سال انجام مطالعه است؛ تاریخ انتشار صفحه نامشخص. '+('خبر تکمیلی کارگاه: '+access['C09']['url'] if key=='C01' else ''))
 if key in ['C06','C07']:
  study_updates.append({'id':'WT-R11' if key=='C06' else 'WT-R10','patch':dict(commissioner_or_funder=client,period=str(year),project_ids=[pid],evidence='صفحه مستقل رسمی مشاور با سال و کارفرما؛ متن قرارداد در دسترس نیست'),'source_keys':[key]})
 else:study(key,title,'مهندسی ارزش',[pid],'مهندسان مشاور کریت‌کارا',client,str(year),summary,evidence='صفحه مستقل پروژه در وبگاه مشاور؛ خدمات و کارفرما مستند، قرارداد کامل مشاهده نشده')

# Academic studies: primary publication metadata and content; keep related case studies separate from contracts.
def academic(i,summary,pids,date,**kw):
 w=reg[i];key='A'+str(i).zfill(2)
 opts=dict(Title_EN=w['title'].lstrip('• '),Language='English',Source_Type='مقاله علمی',Publisher=w['publisher'],Author='؛ '.join(w['authors']),DOI=w['doi'],Date_Gregorian=date)
 opts.update(kw)
 return source(key,w['title'].lstrip('• '),summary,pids,**opts)
academic(1,'مدل بهینه‌سازی اقتصادی–هیدرولیکی انتقال خرسان به کرمان با ترکیب تحلیل انرژی–داده‌ستانده و طراحی خط انتقال. مقاله از داده و پشتیبانی غیرمالی وزارت نیرو و شرکت مهندسی آب و فاضلاب کشور قدردانی کرده و نبود گرنت اختصاصی را تصریح می‌کند.',['WT-T07'],'2026-04-25',Reliability='A',_pdfkey='P01',Organization='دانشگاه صنعتی امیرکبیر؛ دانشگاه صنعتی شریف',Notes='متن ناشر و PDF بازیابی شد. حمایت داده‌ای وزارت نیرو با تأمین مالی یا سفارش رسمی برابر نیست.')
study('A01','طراحی اقتصادی و هیدرولیکی انتقال خرسان به کرمان','امکان‌سنجی',['WT-T07'],'حامد حمزه‌خانی؛ س. جمشید موسوی؛ محمد وصال — دانشگاه صنعتی امیرکبیر و صنعتی شریف','وزارت نیرو و شرکت مهندسی آب و فاضلاب کشور: داده و پشتیبانی غیرمالی؛ گرنت اختصاصی ندارد','2026','بهینه‌سازی ظرفیت و تخصیص اقتصادی خط انتقال خرسان–کرمان؛ پژوهش دانشگاهی، نه قرارداد مصوب اجرای خط.',evidence='مقاله و بخش قدردانی و Funding ناشر؛ PDF محلی')
academic(10,'بررسی روش‌های مقابله با فشردگی زمین در حفاری مکانیزه تونل گلاب؛ مطالعه موردی رفتار سنگ ضعیف و راهکارهای عملی حفاری.',['WT-T08'],'2019',Full_Text='Partial',Notes='چکیده و متادیتای KoreaScience بررسی شد؛ PDF دریافت نشده است.')
study('A10','راهکارهای مقابله با فشردگی زمین در تونل مکانیزه گلاب','مهندسی و طراحی',['WT-T08'],'عباس افتخاری؛ علی عالیانواری','کارفرما یا حامی اختصاصی احراز نشد','2019','تحلیل عددی و تحلیلی فشردگی و شرح راهکارهای حفاری تونل گلاب؛ از قرارداد مشاوره تفکیک شود.',evidence='متادیتا و چکیده در KoreaScience؛ DOI ناشر')
academic(11,'طبقه‌بندی آسیب سگمنت‌های بتنی در تولید و حمل؛ گلاب اصفهان یکی از تونل‌های مورد بررسی است. بخش آماری مقاله بر نمونه‌های متروی تهران متکی است و نتایج آن نباید اندازه‌گیری مختص گلاب معرفی شود.',['WT-T08'],'2017-06-30',Reliability='A',_pdfkey='P11',Organization='دانشگاه علم و صنعت ایران؛ دانشگاه تهران')
study('A11','آسیب سگمنت‌های پیش‌ساخته؛ گلاب در میان نمونه‌های تونل ایران','مهندسی و طراحی',['WT-T08'],'محسن علی شایانفر؛ پیمان مهیار؛ احمد جعفری؛ محمد مهتدی‌نیا — دانشگاه علم و صنعت و دانشگاه تهران','حامی اختصاصی احراز نشد','2017','پژوهش چندموردی شامل گلاب؛ آمار تفصیلی ارائه‌شده مربوط به نمونه‌های متروی تهران است.',evidence='متن کامل ناشر و PDF')
academic(12,'اولویت‌بندی روش‌های اکتشاف زیرسطحی برای تونل انتقال آب سبزکوه؛ هویت، نویسندگان، DOI و تاریخ با صفحه ناشر کنترل شد.',['WT-T10'],'2018-07-23',Title='اولویت‌بندی و انتخاب بهترین روش بررسی زیرسطحی تونل انتقال آب سبزکوه در کوه‌های زاگرس',Language='فارسی',DOI='10.18869/acadpub.jeg.12.2.293',Publisher='نشریه زمین‌شناسی مهندسی — دانشگاه خوارزمی',Reliability='A',_pdfkey='P12',Notes='تاریخ 2018-07-23 از متادیتای ناشر است؛ تاریخ OpenAlex متفاوت بود.')
study('A12','انتخاب روش بررسی زیرسطحی تونل انتقال آب سبزکوه','مهندسی و طراحی',['WT-T10'],'مسعود زارع نقدهی؛ سید داود محمدی؛ مصطفی کریمی — دانشگاه صنعتی همدان و بوعلی سینا','کارفرما یا حامی اختصاصی احراز نشد','2018','ارزیابی و اولویت‌بندی شیوه‌های بررسی زیرسطحی تونل؛ از قرارداد اجرا جداست.',evidence='صفحه و PDF ناشر؛ DOI 10.18869/acadpub.jeg.12.2.293')
academic(13,'پیش‌بینی تعداد دیسک‌کاتر مصرفی TBM در تونل انتقال سبزکوه با روش‌های رگرسیون، برنامه‌نویسی بیان ژن و ماشین بردار پشتیبان.',['WT-T10'],'2021-12-24',Reliability='A',_pdfkey='P13',Organization='دانشگاه آزاد اسلامی، واحدهای قائم‌شهر و تهران مرکزی',Notes='تاریخ انتشار آنلاین 24 December 2021 روی PDF؛ تاریخ ماهانه پایگاه استنادی مبنا قرار نگرفت.')
study('A13','پیش‌بینی مصرف دیسک‌کاتر TBM در تونل سبزکوه','مهندسی و طراحی',['WT-T10'],'علیرضا افرادی؛ آرش ابراهیم‌آبادی؛ طاهره حلاجیان — دانشگاه آزاد قائم‌شهر و تهران مرکزی','حامی اختصاصی احراز نشد','2021','مدل‌های پیش‌بینی مصرف ابزار حفاری بر پایه شرایط ماشین و زمین؛ داده‌های موردی سبزکوه.',evidence='مقاله و PDF در وبگاه نشریه Mining of Mineral Deposits')
academic(14,'بررسی خرابی، نشت، نگهداری و کارایی خطوط طرح غدیر خوزستان. هویت و تاریخ Available با ثبت رسمی DataCite و نسخه بارگذاری‌شده نویسنده تطبیق شد.',['WT-T11'],'2025-10-26',Publisher='Islamic Azad University Press — نشریه مهندسی آب',Full_Text='Partial',Notes='تاریخ 2025-09-18 تاریخ Submitted است؛ تاریخ Available برابر 2025-10-26. Crossref این DOI را ندارد، اما DataCite آن را ثبت کرده است. صفحه ناشر با مانع JavaScript مواجه شد؛ نسخه نویسنده در ResearchGate مشاهده شد.')
study('A14','خرابی و نشت خطوط انتقال آب غدیر خوزستان','مهندسی و طراحی',['WT-T11'],'روزبه آقامجیدی — دانشگاه آزاد اسلامی واحد سپیدان','کارفرما یا حامی اختصاصی احراز نشد','2025','مرور خرابی و نشت و راهکارهای بهره‌برداری خطوط غدیر؛ قرارداد مطالعات سامانه را اثبات نمی‌کند.',evidence='ثبت رسمی DataCite و متن نسخه بارگذاری‌شده نویسنده؛ صفحه اصلی ناشر با مانع دسترسی')
academic(18,'تحلیل عددی اندرکنش درزه‌های پوشش سگمنتی با مشخصات تونل انتقال قمرود، از سرشاخه دز به فلات مرکزی.',['WT-T17'],'2016-07-30',Reliability='A',_pdfkey='P18',Organization='دانشگاه صنعتی امیرکبیر؛ دانشگاه صنعتی سهند')
study('A18','اندرکنش درزه‌های پوشش سگمنتی تونل قمرود','مهندسی و طراحی',['WT-T17'],'محمدحسین احمدی؛ علی مرتضوی؛ سید مرتضی داورپناه؛ حمید زارعی — امیرکبیر و سهند','حامی اختصاصی احراز نشد','2016','تحلیل UDEC پوشش تونل با پارامترهای قمرود؛ طرح مرتبط در حوضه دز است.',evidence='صفحه ناشر و PDF')
eco=read(OUT/'files/A06D.html')['message']
source('A06',eco['title'][0],'پژوهش زیستگاه ماهیان بومی رودخانه کوهرنگ در بالادست و پایین‌دست سازه انتقال بین‌حوضه‌ای. این مرور به چکیده و ثبت DOI دسترسی داشت؛ متن کامل ناشر بازیابی نشد.',[],Title_EN=eco['title'][0],Language='English',Source_Type='مقاله علمی / رکورد پیش‌انتشار',Publisher='Journal of Hydro-environment Research',Author='؛ '.join(' '.join([a.get('given',''),a.get('family','')]) for a in eco['author']),DOI=eco['DOI'],Year=2026,Full_Text='Partial',URL='https://doi.org/'+eco['DOI'],Canonical_URL='https://doi.org/'+eco['DOI'],Project='کوهرنگ (شماره تونل نامشخص)',Province='چهارمحال و بختیاری',Notes='ثبت DOI در 2026-10-13 موجود است؛ شماره چاپی دسامبر 2026 در آینده است و تاریخ انتشار آنلاین قطعی از ثبت جداست. تونل مشخص از میان کوهرنگ ۱،۲،۳ در چکیده تعیین نشده؛ انتساب به تونل مشخص انجام نشده است.')
study('A06','تغییر زیستگاه ماهیان کوهرنگ بر اثر سازه انتقال بین‌حوضه‌ای','ریسک و محیط‌زیست',[], 'Jaber Aazami و همکاران؛ هویت نویسندگان در Crossref','حامی و وابستگی سازمانی از رکورد DOI احراز نشد','ثبت DOI: 2026-10-13؛ شماره چاپی: 2026-12','مطالعه رودخانه کوهرنگ؛ چکیده شماره تونل را مشخص نمی‌کند، بنابراین به یک تونل خاص منتسب نشده است. متن کامل ناشر بازیابی نشد.',cooperation='وابستگی‌های سازمانی در ثبت DOI درج نشده؛ همکاری خارجی احراز نشد',cooperation_type='unconfirmed',evidence='ثبت رسمی Crossref و چکیده نمایه‌شده؛ دسترسی محدود')
source('A20','Seawater Transfer and Sustainability challenges: Insights from Central Iran','چکیده کنفرانس EGU درباره ردپای آب، انرژی و کربن انتقال آب دریا به صنایع ایران مرکزی. نمونه‌های اصلی چکیده عمدتاً کرمان و یزد هستند؛ منبع زمینه‌ای برای ارزیابی انتقال آب دریا به اصفهان محسوب می‌شود.',[],Title_EN='Seawater Transfer and Sustainability challenges: Insights from Central Iran',Language='English',Source_Type='چکیده کنفرانس علمی',Publisher='EGU General Assembly 2025 — Copernicus',Author='Alireza Gohari؛ Mahshid Ghanbarian؛ Ghazal Akhavan Saraf',Organization='University of Oulu؛ دانشگاه صنعتی اصفهان',DOI='10.5194/egusphere-egu25-1824',Date_Gregorian='2025-03-14',Full_Text='Partial',Notes='فقط چکیده عمومی؛ ارائه کنفرانس نیازمند ثبت‌نام است. وابستگی نویسنده به اصفهان با محل نمونه‌های مطالعه یکسان نیست. ارتباط زمینه‌ای.')
study('A20','پایداری انتقال آب دریا به صنایع ایران مرکزی؛ چکیده EGU','همکاری بین‌المللی',[],'علیرضا گوهری؛ مهشید قنبریان؛ غزل اخوان صراف — دانشگاه اولو و صنعتی اصفهان','حامی اختصاصی احراز نشد','2025','چکیده مقایسه آب، انرژی و کربن در نمونه‌های ایران مرکزی؛ زمینه‌ای و فاقد نتیجه اندازه‌گیری مختص اصفهان.',cooperation='ایران–فنلاند؛ همکاری دانشگاهی',cooperation_type='international',evidence='چکیده رسمی کنفرانس و وابستگی‌های درج‌شده')
source('J02','Challenges of Hydrological Analysis for Water Resources Development in Semi-Arid Mountainous Regions: A Case Study in Iran','رساله دکتری GRIPS درباره چالش مدل‌سازی حوضه کارون برای توسعه منابع آب و سامانه‌های انتقال. متن از حمایت مالی Nippon Koei و ارائه داده هیدرولوژی و GIS از شرکت توسعه منابع آب و نیروی ایران قدردانی می‌کند.',[],Title_EN='Challenges of Hydrological Analysis for Water Resources Development in Semi-Arid Mountainous Regions: A Case Study in Iran',Language='English',Source_Type='رساله دکتری',Publisher='National Graduate Institute for Policy Studies (GRIPS)',Author='Shiro Hishinuma',Organization='GRIPS؛ ICHARM؛ Nippon Koei؛ شرکت توسعه منابع آب و نیروی ایران',Date_Gregorian='2013-09-04',Reliability='A',_pdfkey='J02',DOI='10.24545/00000582',Notes='تاریخ اعطای مدرک از صفحه دانشگاه: https://www.grips.ac.jp/en/dtds3/shiro_hishinuma/ . حمایت مالی رساله با قرارداد طراحی یک خط انتقال در ایران برابر نیست؛ پژوهش زمینه‌ای حوضه کارون.')
study('J02','تحلیل هیدرولوژیک کارون برای توسعه منابع آب؛ رساله GRIPS','همکاری بین‌المللی',[],'Shiro Hishinuma؛ GRIPS و ICHARM ژاپن','Nippon Koei: حمایت مالی؛ شرکت توسعه منابع آب و نیروی ایران: داده و پشتیبانی کارشناسی','2013','پژوهش زمینه‌ای هیدرولوژی کارون و محدودیت داده و اقلیم برای طرح‌های توسعه و انتقال؛ قرارداد طراحی انتقال خاص نیست.',cooperation='ژاپن؛ حمایت داده‌ای و کارشناسی ایران',cooperation_type='international',evidence='جلد، چکیده، قدردانی رساله و صفحه رسمی اعطای مدرک')

# An alternate-language record already exists. Enrich it instead of creating a second source.
source('A00P','مدل‌سازی اثرات انتقال آب بین‌حوضه‌ای بر سطح و حجم آبخوان مبدأ؛ آبخوان شلمزار','مدل WEAP اثرات سناریویی انتقال بهشت‌آباد بر سطح و حجم آبخوان شلمزار را بررسی می‌کند؛ نتیجه مدل پیش‌بینی شرطی است، نه افت اندازه‌گیری‌شده پس از اجرا.',['WT-T06'],Source_Type='مقاله علمی',Publisher='جغرافیا و توسعه — دانشگاه سیستان و بلوچستان',Author='شاهین سلیم‌پور ناغانی؛ سید آرمان هاشمی منفرد؛ مهدی اژدری مقدم',DOI='10.22111/gdij.2021.6027',Date_Gregorian='2021-03-21',Full_Text='Partial',Notes='رکورد موجود S097 با عنوان کوتاه انگلیسی همین اثر است؛ DOI و منبع اولیه تکمیل می‌شوند.')
sources[-1]['reuse_source_id']='S097'
study('A00P','اثر سناریوی انتقال بهشت‌آباد بر آبخوان شلمزار','هیدرولوژی و آبخوان',['WT-T06'],'شاهین سلیم‌پور ناغانی؛ سید آرمان هاشمی منفرد؛ مهدی اژدری مقدم','حامی یا کارفرمای اختصاصی احراز نشد','2021','مدل‌سازی ۳۰ ساله WEAP با سناریوهای انتقال و توسعه حوضه؛ شرط‌های مدل در تفسیر نتیجه حفظ شود.',evidence='صفحه ناشر و تطبیق عنوان فارسی با رکورد موجود S097')

# Dated official reports and attributed statements, not independent proof of every claim.
news=[('N01','جانباز: انتقال آب دیگر مسئله حوضه زاینده‌رود را رفع نمی‌کند','2026-10-10','1405/07/18','خبرگزاری مهر','حمیدرضا جانباز','معاون آب و آبفای وزارت نیرو',[], 'اظهارات معاون وزارت نیرو در نشست روز زاینده‌رود درباره حکمرانی و مدیریت مصرف و محدودیت اتکا به انتقال آب. خبر همچنین پیگیری طرح‌های شرب را نقل می‌کند؛ اظهارات سیاستی با مجوز یا نتیجه فنی قطعی یکسان نیست.'),
 ('N02','جوکار: چرا انتقال آب خرسان به یزد هنوز به سرانجام نرسیده است؟','2026-09-06','1405/06/15','آفتاب اقتصاد؛ نقل خبر از تسنیم','محمدصالح جوکار','نماینده یزد، اشکذر، زارچ و ندوشن',['WT-T07'],'اظهارات نماینده درباره مسیرهای پیشنهادی انتقال خرسان و درخواست مطالعات تکمیلی دانشگاه تهران. اصل نامه یا قرارداد مطالعات تکمیلی مشاهده نشده است و ادعای تأیید مجوزها به گوینده منتسب می‌ماند.'),
 ('N03','در شرایط فقر حفظ محیط زیست دشوارتر می‌شود','2026-06-07','1405/03/17','روزنامه اعتماد؛ آرشیو مگیران','شینا انصاری','رئیس سازمان حفاظت محیط زیست',['WT-T18'],'گفت‌وگو با رئیس سازمان حفاظت محیط زیست؛ بخش ماندگان، تأیید نشدن گزارش ارائه‌شده به دلایل فنی، محیط‌زیستی و اجتماعی و کاستی بررسی آثار تجمعی را بیان می‌کند. این اظهارنظرِ تاریخ‌دار جای متن مجوز و وضعیت اجرایی امروز را نمی‌گیرد.'),
 ('N04','بازدید مدیرعامل سازمان آب و برق و استاندار خوزستان از پروژه‌های انتقال و تصفیه آب در شادگان','2025-05-05','1404/02/15','سازمان آب و برق خوزستان','عباس صدریان‌فر','مدیرعامل سازمان آب و برق خوزستان',['WT-T12'],'خبر رسمی سازمان، طرح کارون به جراحی را در این تاریخ «مطالعاتی» معرفی و بازدید از آن و تصفیه‌خانه دارخوین را گزارش می‌کند؛ شواهد متأخرتر نسبت به خبر مرحله دوم ۱۴۰۱.'),
 ('N05','ایذه و باغملک در مسیر توسعه پایدار با محوریت کشاورزی','2017-01-17',None,'سازمان آب و برق خوزستان','خدابخشی','مقام سازمان آب و برق خوزستان',['WT-T25'],'خبر رسمی از انجام مطالعات سامانه مشترک تأمین و انتقال آب شرب و کشاورزی از سد کارون ۳ به محدوده ایذه و باغملک؛ همراه ملاحظات اجتماعی، اقتصادی و محیط‌زیستی. خبر تاریخی است.'),
 ('N06','بهره‌گیری از سیلاب برای مهار کانون‌های ریزگرد و احیای تالاب‌های خوزستان','2019-02-13',None,'سازمان آب و برق خوزستان',None,'معاون حفاظت و بهره‌برداری منابع آب سازمان',['WT-T20','WT-T12'],'گزارش رسمی تاریخی از استفاده از ایستگاه‌های پمپاژ کارون برای انتقال آب به شادگان و بررسی هدایت آب به کانون‌های ریزگرد؛ اهداف و مسیرهای مطالعه از بهره‌برداری دائمی جدا خوانده شوند.')]
for key,title,dg,dp,publisher,person,position,pids,summary in news:
 source(key,title,summary,pids,Source_Type='مصاحبه / موضع رسمی' if key in ['N01','N02','N03'] else 'خبر رسمی سازمان',Publisher=publisher,
   Date_Gregorian=dg,Date_Persian=dp,Person=person,Interviewee=person,Position=position,Organization='وزارت نیرو' if key=='N01' else 'مجلس شورای اسلامی' if key=='N02' else 'سازمان حفاظت محیط زیست' if key=='N03' else 'سازمان آب و برق خوزستان',
   Province='اصفهان' if key=='N01' else 'کهگیلویه و بویراحمد؛ چهارمحال و بختیاری؛ یزد' if key=='N02' else 'اصفهان؛ کهگیلویه و بویراحمد؛ خوزستان' if key=='N03' else 'خوزستان',
   Primary_or_Secondary='Secondary' if key=='N02' else 'Primary',Reliability='A' if key in ['N04','N05','N06'] else 'B')
study('N05','مطالعات سامانه مشترک انتقال آب شرب و کشاورزی ایذه و باغملک','امکان‌سنجی',['WT-T25'],'واحد مطالعات سازمان آب و برق خوزستان؛ مشاور مشخص در متن نام برده نشده','سازمان آب و برق خوزستان','اعلام انجام مطالعات: 2017-01-17','مطالعات انتقال از سد کارون ۳ به محدوده ایذه و باغملک؛ ممکن است با مطالعات مهندسی ارزش هم‌پوشان باشد، شمار قرارداد مستقل محسوب نمی‌شود.',evidence='خبر رسمی سازمان؛ اصل گزارش مطالعه و قرارداد مشاهده نشده')

project(18,'ماندگان','رودخانه ماربر؛ سرشاخه کارون در محدوده سمیرم / دنا','شرب اصفهان؛ مسیر مصوب نهایی این مرور احراز نشده',['اصفهان'],'انتقال بین‌حوضه‌ای',['N03'],'رئیس سازمان محیط زیست در مصاحبه ۱۴۰۵ از تأیید نشدن گزارش ارائه‌شده خبر داده؛ اصل تصمیم اداری و وضعیت اجرای کنونی جداگانه احراز نشده.','2026-06-07',['کهگیلویه و بویراحمد','خوزستان'])
project(19,'آبرسانی غرب اصفهان','منبع و مسیر در صفحه مطالعه مشخص نشده','شهرها و روستاهای غرب اصفهان',['اصفهان'],'سامانه آبرسانی؛ بین‌حوضه‌ای بودن احراز نشده',['C02'],'صفحه رسمی، انجام مطالعه مهندسی ارزش در ۱۳۹۹ را ثبت می‌کند؛ شاهد بهره‌برداری کنونی نیست.','1399')
project(20,'انتقال سیلاب کارون به کانون‌های ریزگرد','کارون؛ مسیرهای پمپاژ و کانال‌های خوزستان','کانون‌های ریزگرد و تالاب‌های خوزستان',['خوزستان'],'انتقال / هدایت سیلاب درون استان',['C03','N06'],'مطالعه مهندسی ارزش ۱۳۹۹ و گزارش تاریخی انتقال و بررسی گزینه‌ها موجود است؛ اجزای مختلف یک وضعیت اجرایی واحد ندارند.','1399')
project(21,'آبرسانی شرب و صنعت باشت','در صفحه مطالعه معرفی نشده','باشت',['کهگیلویه و بویراحمد'],'آبرسانی؛ مبدأ و نوع بین‌حوضه‌ای احراز نشده',['C04'],'صفحه مشاور اتمام مطالعه مهندسی ارزش سال ۱۳۹۸ را ثبت می‌کند؛ مشخصات اجرا و منبع آب در این شاهد نیست.','1398')
project(22,'آبرسانی شمال‌شرق خوزستان','منبع دقیق در صفحه مطالعه درج نشده','شهرهای شمال‌شرق خوزستان',['خوزستان'],'سامانه منطقه‌ای آبرسانی',['C06'],'مطالعه مهندسی ارزش با کارفرمای سازمان آب و برق خوزستان در ۱۳۹۴ مستند است.','1394')
project(23,'آبرسانی جنوب‌شرق خوزستان','منبع دقیق در صفحه مطالعه درج نشده','شهرهای جنوب‌شرق خوزستان',['خوزستان'],'سامانه منطقه‌ای آبرسانی',['C07'],'مطالعه مهندسی ارزش با کارفرمای سازمان آب و برق خوزستان در ۱۳۹۴ مستند است.','1394')
project(24,'تأمین و انتقال آب دهدشت غربی','در صفحه مستقل مطالعه معرفی نشده','اراضی و شبکه آبیاری دهدشت غربی',['کهگیلویه و بویراحمد'],'انتقال و آبیاری؛ مبدأ نیازمند سند تکمیلی',['C10'],'پیشنهاد تغییر به روش مهندسی ارزش سال ۱۳۹۰ ثبت شده است؛ اجرای امروز از آن نتیجه نمی‌شود.','1390')
project(25,'انتقال آب به ایذه و باغملک','سد کارون ۳؛ طبق گزارش سازمان آب و برق','ایذه و باغملک؛ شرب و کشاورزی',['خوزستان'],'انتقال منطقه‌ای درون استان',['C11','N05'],'مهندسی ارزش ۱۳۹۰ و اعلام مطالعات مشترک در ۲۰۱۷ مستند است؛ تأیید نهایی مجوز و بهره‌برداری امروز جداگانه لازم است.','2017-01-17')

# Explicit exclusions prevent vague searches and alternate URLs inflating the bank.
decisions=[{'key':'A02','decision':'pending','reason':'رکورد پایان‌نامه احمدشهر؛ منبع اولیه تایم‌اوت و اطلاعات کافی برای ورود احراز نشد'},
 {'key':'A03','decision':'pending','reason':'رتبه‌بندی فازی انتقال‌های کارون؛ صفحه ناشر 403، متن اولیه کافی بازیابی نشد'},
 {'key':'A04','decision':'duplicate','source_id':'S099','reason':'همان مقاله ریسک بیزی؛ عنوان کامل در برابر عنوان کوتاه'},
 {'key':'A05','decision':'duplicate','source_id':'S106','reason':'اختلاف جزئی عنوان و پیوند ResearchGate؛ همان مقاله کوهرنگ ۳'},
 {'key':'A07','decision':'excluded','reason':'نیترات و کیفیت آب زاینده‌رود؛ ارزیابی مستقیم انتقال آب ندارد'},
 {'key':'A08','decision':'excluded','reason':'پایش عمومی مسیر کارون؛ ارتباط مستقیم کافی با انتقال احراز نشد'},
 {'key':'A09','decision':'excluded','reason':'Erratum مقاله موجود S994؛ پژوهش مستقل جدید نیست'},
 {'key':'A15','decision':'excluded','reason':'مدل عمومی مدول سنگ؛ ارتباط مستقیم و مشخص کافی با سامانه هدف احراز نشد'},
 {'key':'A16','decision':'excluded','reason':'پیش‌بینی کیفیت مارون؛ موضوع مستقیم انتقال نیست'},
 {'key':'A17','decision':'excluded','reason':'دامپزشکی؛ واژه transfer ربطی به انتقال آب ندارد'},
 {'key':'D01','decision':'duplicate','source_id':'S216','reason':'نامه ۱۷ پرسش ماندگان در بانک موجود است'},
 {'key':'A19','decision':'alternate','replacement_key':'J02','reason':'مخزن قدیمی تایم‌اوت؛ همان رساله از PDF رسمی GRIPS دریافت شد'},
 {'key':'C08','decision':'discovery_only','reason':'فهرست مادر مشاور؛ صفحات مستقل هر مطالعه به جای شمارش دوباره فهرست استفاده شدند'},
 {'key':'C09','decision':'supporting_only','reason':'خبر کارگاه، مکمل همان مطالعه C01 است و مطالعه/منبع مستقل تازه شمرده نشد'},
 {'key':'J04','decision':'pending','reason':'مقاله مشتق از رساله ژاپن؛ ناشر 403 و مطالعه مستقل از رساله احراز نشد'},
 {'key':'X01','decision':'unavailable','reason':'Google پاسخ 200 با صفحه هدایت و بدون نتایج قابل خواندن داد؛ مرور مستقیم نتایج ادعا نمی‌شود'}]
for s in sources:
 r=s['record'];matches=[]
 for old in base['sources']:
  score=max(difflib.SequenceMatcher(None,norm(r['Title']),norm(old.get(k))).ratio() for k in ['Title','Title_EN'])
  if score>.55:matches.append({'id':old['Source_ID'],'title':old['Title'],'score':round(score,3)})
 s['closest']=sorted(matches,key=lambda x:-x['score'])[:3]
 if s.get('reuse_source_id'):continue
 for old in base['sources']:
  if r['DOI'] and norm(r['DOI'])==norm(old.get('DOI')) or urlkey(r['URL']) in {urlkey(old.get(k)) for k in ['URL','Canonical_URL','PDF_URL']} or norm(r['Title']) in {norm(old.get(k)) for k in ['Title','Title_EN']}:
   s['reuse_source_id']=old['Source_ID'];break
save('curated.json',{'date':TODAY,'sources':sources,'new_studies':studies,'study_updates':study_updates,'new_projects':projects,'decisions':decisions,
 'limitations':['فهرست بر اساس منابع عمومی و قابل بازیابی است؛ قراردادهای غیرعمومی پوشش داده نمی‌شوند.','Google بدون نتیجه قابل خواندن بود؛ ابزار جست‌وجوی وب، OpenAlex و ثبت DOI استفاده شد.','Crossref در جست‌وجوی گسترده محدودیت 429 داشت؛ برای DOI منتخب به‌صورت مستقیم بررسی انجام شد.','شماره چاپی آینده با تاریخ ایجاد DOI یا دسترسی آنلاین یکسان نیست.']})
for s in sources:print(s['key'],s.get('reuse_source_id','NEW'),s['record']['Title'],s['closest'][:1])
print('COUNTS',len(sources),len(studies),len(projects),len(study_updates))
