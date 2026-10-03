"""Produce news candidates and audit them against the current master."""
import csv,json
from pathlib import Path
from difflib import SequenceMatcher
from research_refresh_20261003 import norm
root=Path(__file__).resolve().parents[1]
items=[
('توزیع۴۲۰میلیون مترمکعب آب از سد زاینده‌رود؛ ماندگان پیشرفت مطلوبی دارد','https://www.mehrnews.com/news/6939772/','مهر','خبر/نشست خبری','verified_primary','گزارش حسن ساسانی درباره رهاسازی آب و پیشرفت ماندگان؛ همپوشانی رویداد با خبر ایمنا باید حفظ شود.'),
('گذار از تنش‌های آبی اصفهان با تکمیل ابرپروژه‌های آبرسانی و جایگزینی پساب صنعتی','https://www.imna.ir/news/1002326/','ایمنا','خبر/نشست خبری','verified_primary','۱۶ شهریور ۱۴۰۵؛ اظهارات حسن ساسانی درباره ماندگان، سامانه دوم و پساب. پوشش همان نشست خبر مهر؛ رویداد مستقل محسوب نشود.'),
('خوزستان نبایدبه بیابان تبدیل شود؛ مخالفت با هرگونه انتقال آب ازبالادست','https://www.mehrnews.com/news/6595600/','مهر','خبر/موضع مقام رسمی','verified_primary','استاندار خوزستان درباره فقدان مجوز انتقال آب ماندگان و مخالفت با انتقال بالادست؛ ۲۹ شهریور ۱۴۰۴ در نمایه.'),
('نقشه نجات زاینده‌ رود روی میز محیط زیست | شفاف ‌سازی مسیرهای گمشده آب تا گاوخونی','https://www.hamshahrionline.ir/news/1047749/','همشهری آنلاین','خبر/گزارش محیط زیستی','verified_primary','مطالعه کریدورهای آبی بوم‌شناختی از سرشاخه تا گاوخونی؛ بررسی منابع و مصارف.'),
('واگذاری تملک اراضی و تعهدات تونل سوم کوهرنگ به استان چهارمحال و بختیاری تکذیب شد','https://www.sarpoosh.com/economy/oil-energy/oil-energy1402101031.html','سرپوش؛ بازنشر ایراسین','خبر/تکذیبیه','verified_republication','تفکیک تسهیل خرید اراضی از انتقال مدیریت و تعهدات تونل؛ لینک ناشر اصلی باید بازیابی شود.'),
('انتقال آب کارون باوجود سدهای فراوان توجیهی ندارد','https://www.tasnimnews.ir/fa/news/1393/06/01/470584/','تسنیم','مصاحبه','indexed_primary','مصاحبه احمدرضا لاهیجان‌زاده؛ موضع سازمان بازرسی و مرکز پژوهش‌ها. متن در نمایه دیده شد؛ صفحه مستقیم هنوز بررسی نشده.'),
('پروژه مردمی نجات ماهی‌های زاینده‌رود - اصفهان','https://www.tasnimnews.ir/fa/media/1394/05/19/825122/','تسنیم','گزارش تصویری','indexed_primary','۱۹ مرداد ۱۳۹۴؛ مستند مشارکت مردمی در پیامد خشکی رودخانه؛ تصاویر مستقیم نیازمند بررسی.'),
('مخزن آب پاک تصفیه‌خانه بن-بروجن به بهره‌برداری رسید','https://www.cm8.ir/2608/227/mwm35/','ایرنا؛ نمایه در سی‌ام۸','خبر','needs_original','ظرفیت ۱۵ هزار مترمکعب و اعتبار ۱۵۰ میلیارد تومان؛ لینک ایرنا و تاریخ انتشار اصلی نیازمند بازیابی.'),
('امسال 2.1 میلیون مترمکعب آب وارد تالاب گاوخونی شد','https://khabarfarsi.com/u/252736002','مهر؛ نمایه در خبر فارسی','خبر','needs_original','تاریخ خبر نمایه: ۱۴۰۵/۰۵/۰۱؛ ورود آب در سال آبی ۱۴۰۴–۱۴۰۵؛ لینک و متن اصلی بازیابی شود.'),
('تشکیل زنجیره انسانی برای حمایت از رود کارون در اهواز','https://www.radiofarda.com/a/f6_iran_ahwaz_chain_karoon/26568562.html','رادیو فردا','خبر/کنش اجتماعی','indexed_primary','کنش اجتماعی علیه انتقال آب؛ منبع قدیمی تازه‌یافته، نه خبر تازه‌منتشرشده.'),
]
sources=json.loads((root/'data.json').read_text(encoding='utf-8'))['sources']
rows=[]
for title,url,publisher,kind,status,notes in items:
    matches=[]
    for s in sources:
        text=' '.join(str(s.get(k) or '') for k in ['URL','Canonical_URL'])
        sim=max(SequenceMatcher(None,norm(title),norm(s.get(k))).ratio() for k in ['Title','Title_EN'])
        if url.rstrip('/') in text or sim>.82:matches.append({'Source_ID':s['Source_ID'],'title':s['Title'],'similarity':round(sim,3)})
    rows.append(dict(Title=title,URL=url,Publisher=publisher,Source_Type=kind,Verification=status,Notes=notes,Existing_Matches=matches))
out={'Checked_Date':'2026-10-03','Master_Modified':False,'Baseline':985,'Candidates':rows}
(root/'reports/news_refresh_2026_10_03.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
with (root/'reports/news_refresh_2026_10_03.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
lines=['# تکمیل جست‌وجوی خبری — ۳ اکتبر ۲۰۲۶','','۱۰ یافته خبری/مصاحبه/تصویری منتخب؛ هر یافته با ۹۸۵ رکورد بانک از نظر نشانی و شباهت عنوان تطبیق داده شد. فایل اصلی بانک تغییر نکرده است. جدید بودن برای بانک با تازه بودن تاریخ انتشار متفاوت است.','','وضعیت‌ها: verified_primary=متن منبع اصلی بررسی شد؛ verified_republication=بازنشر بررسی شد؛ indexed_primary=شاهد نمایه موجود اما متن مستقیم نیازمند بررسی؛ needs_original=فقط نمایه/تجمیع‌گر. خبر مهر و ایمنا درباره ماندگان پوشش یک نشست‌اند و نباید دو رویداد مستقل شمارش شوند. تاریخ سربرگ سایت تاریخ انتشار تلقی نشده است.','','| عنوان | ناشر | وضعیت | تطبیق با بانک | یادداشت |','|---|---|---|---|---|']
for r in rows:lines.append(f"| [{r['Title']}]({r['URL']}) | {r['Publisher']} | {r['Verification']} | {', '.join(x['Source_ID'] for x in r['Existing_Matches']) or 'یافت نشد'} | {r['Notes']} |")
(root/'reports/news_refresh_2026_10_03_report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
for r in rows:print(r['Verification'],r['Title'],r['Existing_Matches'])
