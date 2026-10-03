"""Verify fresh discovery candidates without mutating the master dataset."""
import csv, json, re, unicodedata
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from difflib import SequenceMatcher
import requests

ROOT = Path(__file__).resolve().parents[1]
ITEMS = [
('10.1038/s41598-025-14332-1', 'Application of the metaheuristic algorithms to quantify the GSI based on the RMR classification', 'https://www.nature.com/articles/s41598-025-14332-1', 'مطالعه موردی مستقیم تونل بهشت‌آباد؛ زمین‌شناسی مهندسی'),
('10.1038/s41598-026-55296-0', 'A hybrid NSGA II-CNN-LSTM model for optimal operation of hydropower reservoirs based on the day-ahead electricity price forecast', 'https://www.nature.com/articles/s41598-026-55296-0', 'بهره‌برداری مخزن کارون ۴؛ منبع زمینه‌ای حوضه مبدأ'),
('10.1038/s41598-025-90728-3', 'Water agriculture nexus a system dynamics approach for the next three decades', 'https://www.nature.com/articles/s41598-025-90728-3', 'مدیریت آب و کشاورزی در زاینده‌رود'),
('10.1038/s41598-025-32376-1', 'Application of machine learning algorithms for groundwater level prediction in the Najafabad plain', 'https://www.nature.com/articles/s41598-025-32376-1', 'آبخوان نجف‌آباد و اثر جریان زاینده‌رود'),
('10.1038/s41598-026-70501-w', 'Integrating QUAL2KW nitrate modeling with ambient grey-water dilution pressure and wheat-pathway exposure screening in a semi-arid basin', 'https://www.nature.com/articles/s41598-026-70501-w', 'کیفیت آب زاینده‌رود؛ نیترات و استفاده مجدد در کشاورزی'),
('10.1038/s41598-025-18838-6', 'A disaggregated system dynamics and agent-based modeling of the water-energy-food nexus for optimizing water allocation', 'https://www.nature.com/articles/s41598-025-18838-6', 'تخصیص آب و پیوند آب، انرژی و غذا در حوضه زاینده‌رود'),
('10.5281/zenodo.15221274', 'Temporal changes in diversity and abundance of wintering birds in the Gavkhuni international wetland, Isfahan Province, Iran', 'https://www.wildlife-biodiversity.org/index.php/jwb/article/view/847', 'تنوع زیستی و جریان محیط‌زیستی گاوخونی'),
('10.1007/s11069-025-07943-4', 'Implementing groundwater management strategies to mitigate human-induced subsidence through numerical simulation', 'https://link.springer.com/article/10.1007/s11069-025-07943-4', 'آب زیرزمینی و فرونشست دشت اصفهان'),
('10.1007/s41742-026-01228-9', 'Assessing the Biophysical and Economic Impacts of Water Scarcity on Agriculture and Industry: A Case Study of the Zayandehroud Basin, Iran', 'https://link.springer.com/article/10.1007/s41742-026-01228-9', 'پیامد اقتصادی کم‌آبی بر کشاورزی و صنعت'),
('10.1175/WCAS-D-25-0101.1', 'Evaluating the Effects of Vegetation, Zayandeh Rud River, and Urban Development on the Formation of Heat Islands in Isfahan Using Spatial Statistical Analyses', 'https://journals.ametsoc.org/abstract/journals/wcas/18/3/WCAS-D-25-0101.1.xml', 'اثر رودخانه و پوشش گیاهی بر جزیره حرارتی اصفهان'),
('10.1126/science.aed9259', "Iran’s largest river in crisis", 'https://www.science.org/doi/10.1126/science.aed9259', 'بحران جریان آب کارون؛ نامه/دیدگاه علمی، نوع مقاله باید کنترل شود'),
('10.1038/s41598-026-41014-3', 'Integrating geospatial intelligence and machine learning for flood susceptibility mapping', 'https://www.nature.com/articles/s41598-026-41014-3', 'سیلاب در حوضه کارون بزرگ'),
('', 'Water Crisis: From Management to Social Conflicts', 'https://www.iwii.ir/news/17?lang=en', 'گزارش نشست با مطالعه موردی زاینده‌رود؛ انتشار ۲۰۲۶/۰۹/۰۲، رویداد ۲۰۲۶/۰۷/۲۹'),
('', 'Winners of Environmental Photographer Of The Year 2025 announced', 'https://www.ciwem.org/news/winners-of-environmental-photographer-of-the-year-2025-announced', 'مستند تصویری کنش جمعی برای احیای گاوخونی؛ فقط بخش مرتبط با تالاب'),
]

def norm(x):
    x = unicodedata.normalize('NFKC', x or '').lower().replace('ي','ی').replace('ك','ک').replace('\u200c',' ')
    return ' '.join(re.sub(r'[^\w]+',' ',x).split())

def run(item):
    doi,title,url,relevance=item
    row=dict(DOI=doi or None, Title_EN=title, URL=url, Relevance=relevance, Checked_Date='2026-10-03')
    row['registry']={}
    if doi and not doi.startswith('10.5281/'):
        try:
            r=requests.get('https://api.crossref.org/works/'+doi,timeout=25)
            row['registry']['status']=r.status_code
            if r.ok:
                m=r.json()['message']; row['registry'].update(title=m.get('title'),authors=m.get('author'),published=m.get('published'),publisher=m.get('publisher'),container=m.get('container-title'),type=m.get('type'),links=m.get('link'))
                row['Title_EN']=(m.get('title') or [title])[0]
        except requests.RequestException as e: row['registry']['error']=type(e).__name__
    try:
        r=requests.get(url,timeout=25,headers={'User-Agent':'Mozilla/5.0'})
        row['access']={'status':r.status_code,'resolved_url':r.url,'bytes':len(r.content)}
    except requests.RequestException as e: row['access']={'error':type(e).__name__}
    return row

if __name__=='__main__':
    sources=json.loads((ROOT/'data.json').read_text(encoding='utf-8'))['sources']
    with ThreadPoolExecutor(max_workers=8) as pool: rows=list(pool.map(run,ITEMS))
    for row in rows:
        matches=[];near=[]
        for s in sources:
            text=' '.join(str(s.get(k) or '') for k in ['DOI','URL','Canonical_URL'])
            if (row['DOI'] and row['DOI'].lower() in text.lower()) or row['URL'].rstrip('/') in text:
                matches.append(s['Source_ID'])
            sim=max(SequenceMatcher(None,norm(row['Title_EN']),norm(s.get(k))).ratio() for k in ['Title','Title_EN'])
            if sim>.82: near.append({'Source_ID':s['Source_ID'],'similarity':round(sim,3),'title':s['Title']})
        row['existing_exact_matches']=matches;row['existing_similar_titles']=near
        row['status']='duplicate_or_review' if matches or near else 'new_candidate'
    output={'search_date':'2026-10-03','baseline_sources':len(sources),'master_modified':False,'candidates':rows}
    p=ROOT/'reports/research_refresh_2026_10_03_candidates.json';p.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for row in rows:
        if row['status']=='new_candidate':
            row['status']='needs_primary_access' if row['DOI']=='10.1126/science.aed9259' else 'verified_new'
        row['Full_Text']='Abstract only' if (row['DOI'] or '').startswith('10.1007/') else ('Unverified' if row['status']=='needs_primary_access' else 'Publisher page checked')
        if row['DOI']=='10.5281/zenodo.15221274': row['Publication_Date']='2025-02-15';row['Date_Note']='PDF gives 2025-02-17; publisher landing page gives 2025-02-15.'
        if row['DOI']=='10.1038/s41598-025-18838-6':row['Publication_Date']='2025-10-07'
        if row['URL'].startswith('https://www.iwii.ir'):row['Publication_Date']='2026-09-02';row['Event_Date']='2026-07-29'
    p.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with (ROOT/'reports/research_refresh_2026_10_03_candidates.csv').open('w',encoding='utf-8-sig',newline='') as f:
        fields=['status','Title_EN','DOI','URL','Relevance','Full_Text'];w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
    lines=['# جست‌وجوی تازه منابع — ۳ اکتبر ۲۰۲۶','', 'بانک پایه: ۹۸۵ منبع. فایل‌های اصلی بانک تغییر نکرده‌اند؛ این خروجی بسته نامزدهای افزودن است.', '', '۱۴ نامزد بررسی شد: ۱۲ منبع جدید با صفحه ناشر/سازمان و ارتباط موضوعی بررسی‌شده، یک مورد نیازمند دسترسی به منبع اصلی، و یک مورد تکراری (S719). این اعداد مربوط به فهرست منتخب‌اند، نه همه نتایج موتور جست‌وجو.', '', '## روش', '', 'جست‌وجوی فارسی و انگلیسی با نام‌های زاینده‌رود، کارون، گاوخونی، کوهرنگ، بهشت‌آباد، گلاب، چشمه لنگان، خدنگستان، ماندگان، خرسان و بن–بروجن؛ همراه کلیدواژه‌های انتقال آب، حقابه، حکمرانی، تعارض، فرونشست، کیفیت آب و تنوع زیستی. ۳۴ عبارت جست‌وجوی وب و بررسی صفحه‌های منتخب انجام شد. نتایج خام بخشی از جست‌وجو در فایل‌های search_2026_10_03_*.json ذخیره شده‌اند. DOI، URL و شباهت عنوان با تمام ۹۸۵ رکورد کنترل شد؛ Crossref و صفحه ناشر برای metadata/access بررسی شدند. HTTP 200 به‌تنهایی به معنی دسترسی به متن کامل نیست.', '', '## فهرست منتخب', '', '| وضعیت | عنوان و منبع | دلیل ارتباط | دسترسی |','|---|---|---|---|']
    labels={'verified_new':'جدید؛ قابل افزودن','needs_primary_access':'نیازمند بررسی بیشتر','duplicate_or_review':'تکراری/بازبینی'}
    for row in rows:lines.append(f"| {labels[row['status']]} | [{row['Title_EN']}]({row['URL']}) | {row['Relevance']} | {row['Full_Text']} |")
    lines+=['', '## اولویت و محدودیت‌ها', '', 'اولویت بالا: مقاله مستقیم تونل بهشت‌آباد (14332-1)، پیامد اقتصادی کم‌آبی (01228-9)، کیفیت آب زاینده‌رود (70501-w)، مدل تخصیص آب (18838-6)، فرونشست برخوار (07943-4) و پایش پرندگان گاوخونی (15221274). منابع کارون ۴ و نقشه سیلاب کارون، زمینه‌ای‌اند و نباید به‌عنوان شاهد مستقیم آثار انتقال آب معرفی شوند. گزارش CIWEM برای مجموعه اسناد تصویری/کنش اجتماعی مناسب است؛ مقاله پژوهشی نیست. گزارش مؤسسه زنان خلاصه یک نشست است، نه متن کامل سخنرانی.', '', 'دو مقاله Springer تنها چکیده عمومی دارند. خطاهای 429 در Crossref برای برخی DOIها رخ داده است؛ صفحه ناشر مستقلاً بررسی شده و خطا در JSON باقی مانده است. نامه Science تا بررسی متن اصلی/نوع سند در فهرست انتظار است. تاریخ گزارش مؤسسه زنان از تاریخ برگزاری جدا ثبت شده است. تاریخ مقاله پرندگان میان صفحه و PDF دو روز اختلاف دارد و باید هنگام ادغام در Notes حفظ شود.', '', 'مقاله‌های چشمه لنگان (10.1016/j.ejrh.2026.103359)، چرخه عرضه–تقاضا (10.2166/wp.2026.137)، حکمرانی پایدار اصفهان و پاسخ پوشش گیاهی (10.1186/s12862-026-02575-z) از قبل در بانک‌اند. PDF کنفرانس احیای گاوخونی نیز در S962 ارجاع شده و منبع جدید مستقل شمارش نشد. نتایج خبری تجمیع‌گر و تاریخ سربرگ سایت برای افزودن کافی تلقی نشدند.', '']
    (ROOT/'reports/research_refresh_2026_10_03_report.md').write_text('\n'.join(lines).replace('۳۴ عبارت','۳۸ عبارت'),encoding='utf-8')
    for r in rows: print(r['status'],r['DOI'],r['registry'].get('status'),r['access'].get('status'),r['existing_similar_titles'])
