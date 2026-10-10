"""Build reviewed research candidates without changing the master dataset."""
import json,pathlib,re,html,unicodedata,difflib,urllib.parse,hashlib,collections,sys
sys.stdout.reconfigure(encoding='utf-8')
R=pathlib.Path(__file__).resolve().parents[1]; O=R/'reports/deep_round2_2026_10_10'
def read(f):return json.loads(f.read_text('utf-8-sig'))
A=read(O/'registry_unmatched.json'); P={int(x['key']):x for x in read(O/'primary_access.json') if x['key'].isdigit()}; D={x['key']:x for x in read(O/'downloads.json')}
def meta(i,name):
 out=[]
 for m in P.get(i,{}).get('metadata',[]):
  if re.search(r'''name=["']'''+re.escape(name)+r'''["']''',m):
   found=re.search(r'''content=["'](.*?)["']\s*/?>''',m,re.S)
   if found:out.append(html.unescape(found[1]))
 return out
def first(i,name,fallback=''):return next(iter(meta(i,name)),fallback)
rows=[]
specs={
1:('بهشت‌آباد','انتخاب مناسب‌ترین روش حفاری تونل انتقال آب بهشت‌آباد','مقایسه روش‌های حفاری در ۱۷ کیلومتر نخست مسیر با معیارهای فنی، اقتصادی و محیطی.','متن اصلی فارسی است؛ عنوان انگلیسی نمایه، انتشار جداگانه نیست.'),
8:('بهشت‌آباد','پیش‌بینی ورود آب زیرزمینی به تونل بهشت‌آباد با منطق فازی','مطالعه داده‌های اکتشافی مسیر برای برآورد شرایط ورود آب؛ برای بخش ریسک هیدروژئولوژی مفید است.','نام نویسندگان از PDF اصلاح شد؛ انتساب کامل نام‌ها در OpenAlex قابل اتکا نبود.'),
12:('بهشت‌آباد','انتخاب سیستم نگهداری تونل بهشت‌آباد با FAHP','مقایسه گزینه‌های نگهداری با تحلیل عددی و معیارهای تصمیم‌گیری.','با وجود Naien در عنوان، مقدمه PDF به تونل ۶۵ کیلومتری نزدیک اردل اشاره دارد. با پایان‌نامه S158 و مقاله تاکسونومی S681 پیوند موضوعی دارد؛ سه شاهد مستقل فرض نشوند.'),
45:('بهشت‌آباد','طراحی ظرفیت انتقال آب با شبیه‌سازی–بهینه‌سازی و تصمیم‌گیری چندمعیاره','طراحی ظرفیت سامانه بهشت‌آباد و بررسی حساسیت گزینه‌ها به دوره خشکسالی.','چکیده ناشر بررسی شد؛ متن کامل در دسترس نبود. با مقاله فارسی S094 و نویسندگان آن همپوشانی پژوهشی احتمالی دارد؛ انتشار مستقل ولی استقلال داده‌ها احراز نشده است.'),
52:('کوهرنگ ۳','طراحی پوشش انعطاف‌پذیر تونل کوهرنگ ۳ در پهنه گسل فعال','مدل‌سازی تغییرشکل طولی و طراحی اتصال‌ها در بخش‌های گسلی مسیر.','چکیده و بخش‌های نمونه ناشر؛ ۲۰۰۵ سال انتشار است، نه ۲۰۰۴ موجود در DOI.'),
57:('زاینده‌رود؛ انتقال بین‌حوضه‌ای','تفکیک اثر سد و انتقال آب بر خشکسالی هیدرولوژیک زاینده‌رود','چارچوبی برای جداکردن اثرات منفرد و مشترک مداخله‌های انسانی.','چکیده دامنه ناشر و فهرست انتشارات نهاد نویسنده بررسی شد؛ دانلود مستقیم با محدودیت روبه‌رو بود.'),
76:('خرسان ۳','بررسی باستان‌شناختی محدوده سد خرسان ۳','پژوهش نجات‌بخشی باستان‌شناسی محدوده مخزن؛ پوشش میراث فرهنگی را تقویت می‌کند.','مقاله پژوهشی است، نه مجوز میراث فرهنگی یا گزارش ارزیابی رسمی. DOI صحیح ANES.51 است؛ یک نمایه ثانویه آن را SI نوشته بود.'),
86:('گلاب ۱','پارامترهای عملکرد TBM در سنگ‌های شیستی تونل گلاب','تحلیل داده‌های عملکرد دستگاه و مقایسه با مدل‌های پیش‌بینی حفاری.','صفحه KoreaScience که DOI به آن هدایت می‌شود، چکیده معتبر دارد؛ متن کامل دریافت نشد.'),
87:('گلاب','شرایط مچاله‌شوندگی سنگ در تونل گلاب','ارزیابی تغییرشکل و آسیب احتمالی پوشش در بخش فیلیت–اسلیت.','اصلاحیه ترتیب نام نویسندگان در خود صفحه ناشر ثبت شده؛ اصلاحیه یک مطالعه مستقل شمرده نشده است. فقط چکیده در دسترس بود.'),
89:('گلاب ۲','رابطه هندسه خرده‌سنگ و عملکرد TBM در تونل گلاب ۲','داده‌های آزمایش میدانی حفاری برای پیوند تنظیمات دستگاه، انرژی و هندسه خرده‌سنگ.','چکیده و بخش‌های نمونه ناشر بررسی شد؛ ۲۰۱۹ سال انتشار جلد است و ۲۰۱۸ بخشی از DOI.'),
92:('گلاب؛ سبزکوه؛ قمرود','پیش‌بینی نرخ نفوذ TBM در چند تونل انتقال آب ایران','مدل‌های آماری و یادگیری ماشین بر داده‌های چند تونل، شامل گلاب و سبزکوه.','صفحه ناشر تایید شد؛ دریافت PDF ناقص ماند و متن کامل محلی محسوب نشد. با مقاله بعدی نویسندگان مشترک دارد.'),
95:('سبزکوه','پیش‌بینی نرخ حفاری تونل سبزکوه با الگوریتم‌های بهینه‌سازی','مقایسه سه روش بر مبنای داده‌های سنگ، توده‌سنگ و عملکرد دستگاه.','چکیده کامل ناشر بررسی شد؛ با مطالعه چندتونلی همین نویسندگان پیوند داده شود.'),
108:('سبزکوه','اختلاف رفتار پیش‌بینی‌شده و مشاهده‌شده تونل سبزکوه','بررسی ریزش‌های دهانه و بازنگری روش حفاری و نگهداری بر اساس مشاهدات اجرایی.','انتشار آنلاین ۲۰۱۶، جلد چاپی ۲۰۱۷. با مقالات IAST، ADECO و ناپایداری دهانه در یک خوشه رخداد/پروژه است.'),
110:('سبزکوه','بررسی اثرات تسلیح با تکنیک تیرآهن‌رانی؛ بررسی موردی تونل سبزکوه','تحلیل عددی روش تسلیح برای عبور از بخش ریزشی تونل.','ترتیب نویسندگان در PDF با فراداده صفحه متفاوت است؛ PDF مبنا قرار گرفت. همپوشانی رخداد با سایر مطالعات دهانه سبزکوه.'),
111:('سبزکوه','طراحی و ساخت تونل در زمین دشوار با رویکرد ADECO','بازنگری طراحی پس از ریزش و کاربرد روش کنترل تغییرشکل در تونل سبزکوه.','PDF چهار نویسنده دارد، در حالی که صفحه ناشر فقط دو نویسنده و برچسب نامناسب نوع مقاله نشان می‌دهد؛ مشخصات PDF مبناست.'),
112:('سبزکوه','شناسایی مخاطرات تونل‌زنی با تلفیق زمین‌شناسی و ژئوفیزیک','مطالعات تکمیلی برای شناسایی گسل‌های آبدار و سطح لغزش در مسیر تونل.','متن کامل فارسی دریافت شد؛ همان رخداد ریزش دهانه در چند مقاله بررسی شده است.'),
113:('سبزکوه','ناپایداری دهانه تونل در زمین لغزشی و راهکار اصلاح','بررسی انتخاب محل، پایش و مشکلات زمین‌شناختی دهانه تونل سبزکوه.','صفحه ناشر و چکیده تایید شد؛ PDF ناقص دریافت شد. با مطالعات دیگر دهانه خوشه‌بندی شود.'),
122:('کارون به فلات مرکزی','ارزیابی پایداری اقتصادی انتقال بین‌حوضه‌ای با چارچوب GWP','ارزیابی هزینه کامل انتقال، از جمله آثار تولید برق و کشاورزی مبدأ، در برابر ارزش آب در مقصد.','مجموعه‌مقالات همایش ۲۰۰۹؛ صفحه ناشر تاریخ آنلاین ۲۰۱۲-۰۴-۲۶ دارد. نام دقیق طرح در چکیده مشخص نیست و به بهشت‌آباد یا ونک نسبت داده نشد.'),
}
for i,(project,fa,summary,notes) in specs.items():
 w=A[i];p=P.get(i,{});dl=D.get(str(i),{});full=dl.get('is_pdf',False)
 rows.append(dict(ID=f'A{i:03}',Category='articles',Status='candidate_verified',Title=first(i,'citation_title',w['title']),Title_FA=fa,DOI=w.get('doi',''),URL=p.get('final_url') or w.get('url') or 'https://doi.org/'+w['doi'],Authors=meta(i,'citation_author') or w.get('authors'),Publisher=first(i,'citation_journal_title',w.get('publisher')),Date=first(i,'citation_date',w.get('date')),Project=project,Relation='direct',Summary=summary,Notes=notes,Access='PDF کامل دریافت و صفحه اول دیده شد' if full else 'صفحه یا چکیده ناشر بررسی شد؛ متن کامل محلی موجود نیست',Local_File=dl.get('file') if full else None,PDF_URL=dl.get('url'),Registry_Row=i))
by={r['ID']:r for r in rows}
by['A001'].update(Title='انتخاب مناسب‌ترین روش حفاری تونل انتقال آب بهشت‌آباد',Title_EN=A[1]['title'],Authors=['مهدی نیک‌منش','مهدی حسینی','صفر فضلی'],Date='۱۳۹۱؛ بهار و تابستان',Language='fa')
by['A008']['Authors']=['M. Doust Mohammadi','A. Jafari','O. Asghari']
by['A045'].update(URL='https://ascelibrary.org/doi/abs/10.1061/%28ASCE%29WR.1943-5452.0000818',Date='2017-06-30')
by['A052'].update(URL='https://www.sciencedirect.com/science/article/pii/S0886779804003256',Date='2005-05')
by['A057']['URL']='https://iwaponline.com/jwcc/article/13/9/3473/90280/Quantitative-analysis-of-the-human-intervention'
by['A076'].update(Date='2014',Authors=['Parsa Ghasemi','Greg Watson'])
by['A086'].update(Date='2018-08-25',Authors=['Abbas Eftekhari','Ali Aalianvari','Jamal Rostami'])
by['A087'].update(Date='2017-11-11',Authors=['Asghar Rahmati','Lohrasb Faramarzi','Mohammad Darbor'])
by['A089'].update(URL='https://www.sciencedirect.com/science/article/pii/S0886779818301238',Date='2019-06')
by['A095']['Authors']=['Alireza Afradi','Arash Ebrahimabadi','Tahereh Hallajian']
by['A095']['Date']='2020؛ جلد 14، شماره 2؛ روز دقیق احراز نشد'
by['A110']['Authors']=['عباس افتخاری','مجید طارمی','مهدی سعیدی']
by['A111'].update(Title='Tunnel designing and construction process in difficult ground conditions using Controlled Deformations (ADECO) approach; a Case Study',Authors=['Majid Taromi','Abbas Eftekhari','Jafar Khademi Hamidi','Amirhossein Eghbali'])
by['A122'].update(URL='https://ascelibrary.org/doi/10.1061/41036%28342%29385',Date='2009؛ online 2012-04-26')
def add(id,cat,title,url,date,project,publisher,summary,notes,**kw):
 rows.append(dict(ID=id,Category=cat,Status='candidate_verified',Title=title,URL=url,Date=date,Project=project,Publisher=publisher,Summary=summary,Notes=notes,Relation='direct',Access='متن منبع بررسی شد',**kw))
add('A063','articles','From Contract to Constitution: Judicial Innovation in the Iran’s Khersan 3 Dam Environmental Case','https://www.dpceonline.it/index.php/dpceonline/article/view/2480','2026-01-22؛ شماره 4/2025','خرسان ۳','DPCE Online','تحلیل حقوقی پرونده قرارداد سد و الزامات ارزیابی محیطی؛ دارای شماره آرای بدوی و تجدیدنظر و ارجاع به پیوست.','این مقاله جای اصل دادنامه نیست. شماره‌ها نقل از مقاله‌اند؛ پیوند پیوست دسترسی نداد.',DOI='10.57660/dpceonline.2025.2480',Authors=['Hossein Mardi'],Local_File='files/khersan_legal.pdf')
add('N01','news','نگاه مثبت کلانتری به پروژه سبزکوه/انتقال آب بنام شرب به کام فولاد','https://www.iranboom.ir/didehban/zistboom/17032-khabar-970712-008.html','۱۳۹۷/۰۷/۱۳، تاریخ بازنشر','سبزکوه–چغاخور','مهر / بازنشر ایران‌بوم','گزارش درباره مخالفت‌ها، پیگیری مجوز و نامه توقف وزارت نیرو.','نویسنده مسعود بربر. نسخه مهر و بازنشر یک منبع هستند؛ نامه نقل‌شده، اصل نامه بازیابی‌شده محسوب نمی‌شود.',Local_HTML='files/sabzkuh_news.html')
add('N02','news','نگاه مسئولان به ورزشگاه نقش جهان اصفهان سیاسی است','https://www.tasnimnews.ir/fa/news/1393/03/24/400751/','۱۳۹۳/۰۳/۲۴','کوهرنگ ۳؛ بهشت‌آباد','تسنیم','در بخش آبی گزارش، حسن کامران درباره اعتبار اوراق مشارکت سد کوهرنگ ۳ و اصلاح طرح بهشت‌آباد اظهارنظر می‌کند.','عنوان خبر ورزشی است؛ ارتباط در متن احراز شد. خبر اظهارات نماینده است، نه سند تصویب بودجه.',Local_HTML='files/news400751.html')
add('I01','interviews','مرگ حوضه مبدأ با حفر تونل آبرسانی در شاهان‌کوه فریدون‌شهر','https://www.tasnimnews.ir/fa/news/1393/03/13/389844/','۱۳۹۳/۰۳/۱۳','پشندگان؛ گوکان؛ چشمه لنگان','تسنیم','گفت‌وگو با حسین گوگونانی، رئیس شورای شهر فریدون‌شهر، درباره نگرانی‌های حوضه مبدأ و آثار حفر تونل.','آمار خسارت و انتساب علت به گوینده نسبت داده شود؛ گزارش اندازه‌گیری مستقل نیست.',Person='حسین گوگونانی',Local_HTML='files/interview389844.html')
add('I02','interviews','جولان سد سازان با چراغ سبز کلانتری','https://www.pishkhan.com/news/105243','۱۳۹۷/۰۶/۱۲','خرسان؛ سبزکوه','روزنامه قانون / آرشیو پیشخوان','گزارش مصاحبه‌محور با محمد درویش و هژیر کیانی درباره بازگشایی طرح‌ها، آثار پایین‌دست و لزوم بازنگری مطالعات.','اظهارات در تاریخ انتشار ثبت شوند؛ وضعیت مجوز در سال ۱۳۹۷ به وضعیت امروز تعمیم داده نشود.',Person='محمد درویش؛ هژیر کیانی')
add('R01','official_reports','IWRM Zayandeh Rud Iran – Phase 2: Hydrogeological structural model for the upstream part of the Zayandeh Rud River basin','https://edocs.tib.eu/files/e01fb19/1685135072.pdf','جلد: May 2016؛ شناسنامه: 2016-06-01','بالادست سد زاینده‌رود','DHI-WASY برای وزارت نیرو / آب منطقه‌ای اصفهان؛ مخزن TIB','مدل ساختاری آب زیرزمینی و داده‌های گمانه‌های چادگان، داران، چهل‌خانه و دامنه.','گزارش فنی نهادی با برچسب Draft در شناسنامه؛ منبع زمینه‌ای آبخوان‌هاست، نه گزارش EIA یا تایید طرح انتقال.',Authors=['Sebastian Sklorz'],Local_File='files/upstream_hsm.pdf')
rows[-1]['Relation']='context'
add('R02','official_reports','برنامه مدیریت جامع تالاب گندمان','https://rsis.ramsar.org/RISapp/files/47382230/documents/IR2558_mgt240312.pdf','زمستان ۱۳۹۹','گندمان؛ چغاخور','اداره کل حفاظت محیط زیست چهارمحال و بختیاری؛ مخزن Ramsar','برنامه مدیریت تالاب با اقدام مشخص تامین حقابه از چغاخور پس از رعایت نیاز محیطی آن؛ برای بررسی سامانه مقصد و تعهدات حقابه مفید است.','منبع زمینه‌ای مرتبط با چغاخور؛ گزارش ارزیابی تونل سبزکوه نیست. تاریخ مسیر URL تاریخ انتشار گزارش نیست.',Local_File='files/download_gandoman.pdf')
rows[-1]['Relation']='context'
add('D01','documents','فراخوان تجدید مناقصه بهره‌برداری و تعمیرات تأسیسات پمپاژ آب بیرگان، نوبت دوم','https://static2.esfahanemrooz.ir/servev2/LKA3SQ9XN7gT/Kl4CadDoeE4bRz50Hlni6LGql1ADMwHQ4Wu5Wxs5ff4%2C/esfahanemrooz4977.pdf','۱۴۰۳/۰۶/۰۷ / 2024-08-28','پمپاژ بیرگان؛ شهرستان کوهرنگ','شرکت سهامی آب منطقه‌ای اصفهان / اصفهان امروز ۴۹۷۷، صفحه ۸','آگهی رسمی دارای موضوع قرارداد، محل اجرا، مدت، مبلغ برآورد و شماره فراخوان.','اصل آگهی در صفحه روزنامه مشاهده شد. آگهی دلالت بر انعقاد قرارداد یا اجرای موفق ندارد؛ ارتباط آن با اجزای کوهرنگ ۳ فراتر از متن آگهی فرض نشده است.',Local_File='files/download_tender4977.pdf',Document_ID='2003001205000034')
add('D02','documents','درخواست استانداران، فرمانداران، نمایندگان مجلس و شوراهای اصفهان از جهانگیری','https://www.tasnimnews.ir/fa/news/1393/02/30/376197/','۱۳۹۳/۰۲/۳۰','بهشت‌آباد؛ کوهرنگ ۳؛ بن–بروجن؛ سبزکوه','تسنیم؛ متن بازنشرشده نامه مدیران ادوار اصفهان','نامه به معاون اول و رئیس شورای عالی آب درباره تامین آب و پیشنهاد جایگزینی سبزکوه برای بن–بروجن.','متن نامه در رسانه است؛ تصویر امضاها و اصل ثبت اداری احراز نشده. با نامه دیگری در مرداد ۱۳۹۳، S381، تاریخ و مخاطب متفاوت دارد.',Local_HTML='files/letter376197.html')
for i in [73,121,124,135]:
 w=A[i];p=P.get(i,{})
 reason={73:'صفحه ناشر timeout داد؛ فقط نمایه و شناسه موجود است.',121:'ناشر به Emerald منتقل شده و دسترسی مسدود بود؛ چکیده اولیه از نمایه است.',124:'DOI اعلام‌شده در resolve پاسخ 404 داد؛ ثبت DOI و اصل مقاله نیازمند تکمیل است.',135:'DOI به PII ناشر هدایت شد ولی متن علمی ناشر دریافت نشد؛ خبر ScienceMag و چکیده OpenAlex برای تایید نهایی کافی شمرده نشد.'}[i]
 rows.append(dict(ID=f'P{i:03}',Category='articles',Status='needs_verification',Title=w['title'],DOI=w.get('doi'),URL=w.get('url'),Date=w.get('date'),Project='کارون/خرسان یا انتقال آب مرتبط',Publisher=w.get('publisher'),Summary='سرنخ علمی مرتبط؛ خارج از شمار نامزدهای تاییدشده.',Notes=reason,Access=reason,Relation='needs_review',Registry_Row=i))
add('Pdoc','documents','پیوست دوزبانه آرای بدوی و تجدیدنظر خرسان ۳، ارجاع‌شده در مقاله Mardi','https://1drv.ms/w/c/7a8d2f97b29d57fc/Ea2LzatMbz5LstxLNYdSXkkBY2uVc9DWDMlD71cgDdtLLA?e=bSBBh9','تاریخ‌های نقل‌شده در مقاله: 2024-01-18 و 2025-01-18','خرسان ۳','پیوست به‌اشتراک‌گذاشته‌شده توسط نویسنده مقاله','پیوند مستقیم از annotationهای PDF استخراج شد.','OneDrive اعلام کرد دسترسی به سند ممکن نیست. فایل دادنامه دریافت نشده؛ شماره‌های 140241390002417255 و 140341390002837117 صرفاً نقل از مقاله‌اند.')
rows[-1].update(Status='needs_verification',Access='صفحه خطای عدم دسترسی؛ HTTP 200 به معنای دریافت سند نبود')
add('Pint','interviews','مصاحبه محمد بهرامی با کبنا؛ بخش مربوط به سد ماندگان','https://khabarfarsi.com/u/252227087','تیر ۱۴۰۵؛ روز دقیق احراز نشد','ماندگان','کبنا / نمایه خبرفارسی','مصاحبه دارای عبارت چوب لای چرخ سد ماندگان گذاشتیم در عنوان.','فقط خبرخوان در دسترس بود؛ اصل مصاحبه و تاریخ دقیق بازیابی نشد.')
rows[-1].update(Status='needs_verification',Access='نمایه خبرخوان؛ متن اصلی احراز نشد')
# Baseline includes all prior candidate packages, including the first October 10 round.
prev=['research_refresh_2026_10_03_candidates.json','news_refresh_2026_10_03.json','four_categories_2026_10_03/candidates.json','refresh_2026_10_10/candidates.json']
main=read(R/'data.json');base=[('master',s) for s in main['sources']]
for f in prev:
 d=read(R/'reports'/f);base.extend((f,s) for s in d.get('Candidates',d.get('candidates',[])))
def norm(t):return re.sub(r'[^\w]','',unicodedata.normalize('NFKC',str(t or '')).lower().replace('ي','ی').replace('ك','ک'))
def strings(x):
 if isinstance(x,dict):
  for v in x.values():yield from strings(v)
 elif isinstance(x,list):
  for v in x:yield from strings(v)
 elif isinstance(x,str):yield x
def urlkey(u):
 p=urllib.parse.urlsplit(urllib.parse.unquote(u));host=p.netloc.lower().removeprefix('www.').replace('tasnimnews.com','tasnimnews.ir');path=p.path.rstrip('/')
 m=re.search(r'/news/(?:\d{4}/\d{2}/\d{2}/)?(\d+)',path)
 if m:return host+'/news/'+m[1]
 return host+path+('?'+'&'.join(sorted(k+'='+v for k,v in urllib.parse.parse_qsl(p.query) if k not in ['lang','utm_source','utm_medium'])) if p.query else '')
audit=[]
for row in rows:
 own={urlkey(row[k]) for k in ['URL','PDF_URL'] if row.get(k)};exact=[];near=[]
 for origin,s in base:
  flat=list(strings(s));urls={urlkey(v) for v in flat if v.startswith(('http://','https://'))};title=s.get('Title',s.get('title',''));titles=[title,s.get('Title_EN','')];doi=(row.get('DOI') or '').lower()
  if (doi and doi in ' '.join(flat).lower()) or own&urls or norm(row['Title']) in [norm(t) for t in titles if t]:exact.append(dict(origin=origin,id=s.get('Source_ID',s.get('ID',s.get('Candidate_ID'))),title=title))
  pairs=[(norm(rt),norm(t)) for rt in [row['Title'],row.get('Title_FA',''),row.get('Title_EN','')] if rt for t in titles if t]
  score=0
  for rt,bt in pairs:
   sm=difflib.SequenceMatcher(None,rt,bt)
   if sm.quick_ratio()>.5:score=max(score,sm.ratio())
  if score>.5:near.append(dict(score=round(score,3),origin=origin,id=s.get('Source_ID',s.get('ID')),title=title))
 row['Exact_Duplicate_Matches']=exact
 if exact:row['Status']='duplicate_review'
 if row.get('Local_File'):row['SHA256']=hashlib.sha256((O/row['Local_File']).read_bytes()).hexdigest()
 audit.append(dict(ID=row['ID'],exact=exact,similar=sorted(near,key=lambda x:x['score'],reverse=True)[:3]))
(O/'dedup_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),'utf-8')
(O/'candidates.json').write_text(json.dumps(dict(Search_Date='2026-10-10',Baseline_Count=len(main['sources']),Previous_Files=prev,Master_Modified=False,Candidates=rows),ensure_ascii=False,indent=2),'utf-8')
labels={'articles':'مقاله‌ها','news':'خبرها','interviews':'مصاحبه‌ها','official_reports':'گزارش‌های رسمی نهادی','documents':'اسناد و نامه‌ها'}
def describe(r):
 ls=[f"### {r['ID']} — {r.get('Title_FA',r['Title'])}",'',f"- وضعیت: {r['Status']}",f"- عنوان منبع: {r['Title']}",f"- تاریخ: {r.get('Date','نامشخص')}",f"- ناشر: {r.get('Publisher','نامشخص')}",f"- پروژه/حوضه: {r['Project']}",f"- پیوند: [{r['Title']}]({r['URL']})"]
 if r.get('DOI'):ls.append(f"- DOI: {r['DOI']}")
 if r.get('Authors'):ls.append('- نویسندگان: '+'؛ '.join(r['Authors']))
 if r.get('Local_File'):ls.append(f"- نسخه محلی: [{r['Local_File']}]({r['Local_File']})")
 ls.extend([f"- دسترسی: {r['Access']}",f"- کاربرد: {r['Summary']}",f"- ملاحظات: {r['Notes']}",''])
 return '\n'.join(ls)
for cat,label in labels.items():(O/(cat+'.md')).write_text('# '+label+'\n\n'+'\n'.join(describe(r) for r in rows if r['Category']==cat),'utf-8')
counts=collections.Counter(r['Category'] for r in rows if r['Status']=='candidate_verified');pending=sum(r['Status']=='needs_verification' for r in rows)
print('COUNTS',dict(counts),'pending',pending)
for a in audit:
 if a['exact'] or a['similar']:print(json.dumps(a,ensure_ascii=False))
assert len(main['sources'])==985
assert not any(r['Exact_Duplicate_Matches'] for r in rows)
