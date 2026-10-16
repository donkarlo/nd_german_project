#!/usr/bin/env python3
import sqlite3, sys, shutil, datetime
from pathlib import Path
ROOT=Path('/home/donkarlo/Dropbox/repo/nd_german_project/src/nd_german')
sys.path.insert(0,str(ROOT))
import dictionary_core as dc

DB=Path('/home/donkarlo/Dropbox/repo/data/nd_german_project/dictionary.sqlite3')
# category|article|German|English|Persian
ROWS = """
hardware|die|Hauptplatine|motherboard|مادربرد
hardware|der|Arbeitsspeicher|random-access memory|حافظه موقت
hardware|die|Festplattenpartition|disk partition|پارتیشن دیسک
hardware|der|Prozessorkern|CPU core|هسته پردازنده
hardware|die|Grafikschnittstelle|graphics interface|رابط گرافیکی
hardware|der|Kühlkörper|heat sink|گرماگیر
hardware|die|Wärmeleitpaste|thermal paste|خمیر حرارتی
hardware|der|Lüfteranschluss|fan connector|اتصال فن
hardware|das|Netzteilgehäuse|power supply housing|محفظه منبع تغذیه
hardware|der|Speichercontroller|memory controller|کنترلگر حافظه
hardware|der|Datenbus|data bus|گذرگاه داده
hardware|die|Taktfrequenz|clock frequency|فرکانس ساعت
hardware|die|Rechenleistung|computing power|توان پردازشی
hardware|der|Steckplatz|expansion slot|شکاف توسعه
hardware|das|Erweiterungsmodul|expansion module|ماژول توسعه
hardware|der|Gerätetreiber|device driver|راه‌انداز دستگاه
hardware|die|Bildwiederholrate|refresh rate|نرخ نوسازی تصویر
hardware|die|Bildschirmauflösung|screen resolution|وضوح نمایشگر
hardware|der|Berührungssensor|touch sensor|حسگر لمسی
hardware|die|Speicherkapazität|storage capacity|ظرفیت ذخیره‌سازی
hardware|die|Anschlussbuchse|connector socket|سوکت اتصال
hardware|der|Kabeladapter|cable adapter|تبدیل کابل
hardware|das|Eingabegerät|input device|دستگاه ورودی
hardware|das|Ausgabegerät|output device|دستگاه خروجی
network|die|Netzwerkschnittstelle|network interface|رابط شبکه
network|die|Netzwerkadresse|network address|نشانی شبکه
network|das|Netzwerkprotokoll|network protocol|پروتکل شبکه
network|der|Paketverlust|packet loss|از دست رفتن بسته
network|die|Paketvermittlung|packet switching|سوئیچینگ بسته
network|die|Übertragungsrate|transfer rate|نرخ انتقال
network|die|Netzwerklatenz|network latency|تأخیر شبکه
network|die|Netzwerkmaske|subnet mask|ماسک زیرشبکه
network|das|Standardgateway|default gateway|دروازه پیش‌فرض
network|die|Namensauflösung|name resolution|تبدیل نام به نشانی
network|die|Portweiterleitung|port forwarding|هدایت درگاه
network|die|Verbindungsanfrage|connection request|درخواست اتصال
network|der|Verbindungsabbruch|connection drop|قطع اتصال
network|die|Netzwerktopologie|network topology|توپولوژی شبکه
network|der|Datenverkehr|network traffic|ترافیک داده
network|die|Paketfilterung|packet filtering|فیلتر کردن بسته‌ها
network|die|Bandbreitenbegrenzung|bandwidth throttling|محدودسازی پهنای باند
network|die|Zugriffsverzögerung|access latency|تأخیر دسترسی
network|die|Funkverbindung|wireless connection|اتصال بی‌سیم
network|der|Verbindungsaufbau|connection establishment|برقراری اتصال
network|der|Adressbereich|address range|محدوده نشانی
security|die|Zugriffsberechtigung|access permission|مجوز دسترسی
security|die|Zugriffskontrolle|access control|کنترل دسترسی
security|die|Benutzerauthentifizierung|user authentication|احراز هویت کاربر
security|die|Mehrfaktorauthentifizierung|multi-factor authentication|احراز هویت چندعاملی
security|die|Datenverschlüsselung|data encryption|رمزگذاری داده‌ها
security|der|Verschlüsselungsschlüssel|encryption key|کلید رمزگذاری
security|die|Schlüsselverwaltung|key management|مدیریت کلید
security|die|Sicherheitslücke|security vulnerability|آسیب‌پذیری امنیتی
security|das|Sicherheitsupdate|security update|به‌روزرسانی امنیتی
security|die|Schadsoftware|malware|بدافزار
security|die|Angriffserkennung|intrusion detection|شناسایی نفوذ
security|die|Anmeldebestätigung|login confirmation|تأیید ورود
security|der|Sitzungsschlüssel|session key|کلید نشست
security|die|Kennwortverwaltung|password management|مدیریت گذرواژه
security|die|Rechteverwaltung|permission management|مدیریت مجوزها
security|der|Sicherheitsvorfall|security incident|رخداد امنیتی
security|die|Vertrauensstellung|trust relationship|رابطه اعتماد
security|der|Prüfwert|checksum|مقدار وارسی
security|die|Integritätsprüfung|integrity check|بررسی یکپارچگی
security|das|Sicherheitszertifikat|security certificate|گواهی امنیتی
data|die|Datenbankabfrage|database query|پرس‌وجوی پایگاه داده
data|der|Datenbankindex|database index|نمایه پایگاه داده
data|die|Tabellenverknüpfung|table join|پیوند جدول‌ها
data|der|Primärschlüssel|primary key|کلید اصلی
data|der|Fremdschlüssel|foreign key|کلید خارجی
data|die|Datenkonsistenz|data consistency|سازگاری داده‌ها
data|die|Datenintegrität|data integrity|یکپارچگی داده‌ها
data|die|Datenredundanz|data redundancy|افزونگی داده‌ها
data|die|Datensicherung|data backup|پشتیبان‌گیری داده‌ها
data|die|Datenwiederherstellung|data recovery|بازیابی داده‌ها
data|der|Speicherbedarf|storage requirement|نیاز به فضای ذخیره‌سازی
data|die|Dateiberechtigung|file permission|مجوز فایل
data|die|Dateiendung|file extension|پسوند فایل
data|der|Dateipfad|file path|مسیر فایل
data|das|Dateisystemformat|filesystem format|قالب سامانه فایل
data|die|Verzeichnisstruktur|directory structure|ساختار پوشه‌ها
data|die|Speicherbelegung|disk usage|میزان استفاده از حافظه
data|die|Datenkomprimierung|data compression|فشرده‌سازی داده‌ها
data|das|Datenformat|data format|قالب داده
data|der|Datensatztyp|record type|نوع رکورد
software|die|Programmierschnittstelle|application programming interface|رابط برنامه‌نویسی
software|die|Laufzeitumgebung|runtime environment|محیط زمان اجرا
software|die|Versionsverwaltung|version control|مدیریت نسخه‌ها
software|der|Quellcodeeditor|source code editor|ویرایشگر کد منبع
software|der|Paketmanager|package manager|مدیر بسته‌ها
software|die|Abhängigkeitsverwaltung|dependency management|مدیریت وابستگی‌ها
software|der|Kompilierungsvorgang|compilation process|فرایند کامپایل
software|die|Fehlerbehandlung|error handling|مدیریت خطا
software|die|Ausnahmebehandlung|exception handling|مدیریت استثنا
software|die|Speicherfreigabe|memory release|آزادسازی حافظه
software|die|Speicherzuweisung|memory allocation|تخصیص حافظه
software|der|Programmabsturz|application crash|از کار افتادن برنامه
software|die|Prozessverwaltung|process management|مدیریت فرایندها
software|die|Threadverwaltung|thread management|مدیریت رشته‌ها
software|die|Hintergrundverarbeitung|background processing|پردازش پس‌زمینه
software|die|Warteschlangenverwaltung|queue management|مدیریت صف‌ها
software|die|Aufgabenplanung|task scheduling|زمان‌بندی وظایف
software|der|Startparameter|startup parameter|پارامتر راه‌اندازی
software|die|Konfigurationsdatei|configuration file|فایل پیکربندی
software|die|Protokolldatei|log file|فایل گزارش
software|die|Benutzeroberfläche|user interface|رابط کاربری
software|die|Befehlseingabe|command input|ورود فرمان
software|die|Eingabeaufforderung|command prompt|اعلان فرمان
software|die|Zwischenablage|clipboard|حافظه موقت کپی
software|die|Tastenkombination|keyboard shortcut|میانبر صفحه‌کلید
software|die|Bildschirmfreigabe|screen sharing|اشتراک‌گذاری صفحه
software|die|Fernwartung|remote maintenance|نگهداری از راه دور
software|der|Installationsassistent|installation wizard|دستیار نصب
software|die|Fehlermeldung|error message|پیام خطا
software|der|Fehlerbericht|bug report|گزارش خطا
dev|der|Testfall|test case|مورد آزمون
dev|die|Testabdeckung|test coverage|پوشش آزمون
dev|der|Integrationstest|integration test|آزمون یکپارچه‌سازی
dev|der|Komponententest|component test|آزمون مؤلفه
dev|die|Versionsnummer|version number|شماره نسخه
dev|die|Codeüberprüfung|code review|بازبینی کد
dev|die|Fehlersuche|debugging|اشکال‌زدایی
dev|der|Haltepunkt|breakpoint|نقطه توقف
dev|die|Ausführungszeit|execution time|زمان اجرا
dev|die|Ressourcennutzung|resource usage|مصرف منابع
dev|die|Leistungsüberwachung|performance monitoring|پایش عملکرد
dev|die|Bereitstellungspipeline|deployment pipeline|خط استقرار
dev|die|Entwicklungsumgebung|development environment|محیط توسعه
dev|die|Produktionsumgebung|production environment|محیط عملیاتی
dev|die|Versionsfreigabe|release approval|تأیید انتشار نسخه
dev|der|Änderungsverlauf|change history|تاریخچه تغییرات
dev|die|Rückwärtskompatibilität|backward compatibility|سازگاری با نسخه‌های پیشین
dev|die|Fehlerreproduktion|bug reproduction|بازآفرینی خطا
dev|die|Codebasis|codebase|پایگاه کد
dev|die|Anwendungsarchitektur|application architecture|معماری نرم‌افزار
""".strip()

CAT = {
'hardware': ('Computerhardware', 'technischen Aufbau von Computern', 'Geräte und Komponenten'),
'network': ('Computernetzwerke', 'Datenaustausch zwischen Geräten', 'Netzwerkverbindungen'),
'security': ('IT-Sicherheit', 'Schutz von Systemen und Daten', 'Sicherheitsmaßnahmen'),
'data': ('Datenverarbeitung', 'Organisation und Speicherung von Informationen', 'Datenbestände'),
'software': ('Softwareentwicklung und Systembetrieb', 'Ausführung und Bedienung von Programmen', 'Softwareanwendungen'),
'dev': ('Softwareentwicklung', 'Testen und Bereitstellen von Programmen', 'Entwicklungsprozesse'),
}
PERSIAN_ROMAN={'ا':'a','آ':'â','ب':'b','پ':'p','ت':'t','ث':'s','ج':'j','چ':'ch','ح':'h','خ':'kh','د':'d','ذ':'z','ر':'r','ز':'z','ژ':'zh','س':'s','ش':'sh','ص':'s','ض':'z','ط':'t','ظ':'z','ع':'','غ':'gh','ف':'f','ق':'gh','ک':'k','گ':'g','ل':'l','م':'m','ن':'n','و':'v','ه':'h','ی':'y','ئ':'y','ء':'','‌':' ',' ':' '}
def roman(x): return ''.join(PERSIAN_ROMAN.get(c,c) for c in x)
c=sqlite3.connect(DB)
existing={str(r[0]).strip().casefold() for r in c.execute('select headword from entries')}
def clean(x):
    import re
    x=re.sub(r'^\s*(?:der|die|das)\s+','',x,flags=re.I)
    return x.casefold().strip()
existing={clean(x) for x in existing}
fresh=[]
for line in ROWS.splitlines():
    cat,article,word,en,fa=line.split('|')
    if clean(word) not in existing:
        fresh.append((cat,article,word,en,fa))
    if len(fresh)==100:break
if len(fresh)!=100:raise RuntimeError('Only '+str(len(fresh))+' unique candidates available')
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
backup=DB.with_name('dictionary.backup_before_100_computer_'+stamp+'.sqlite3')
dst=sqlite3.connect(backup);c.backup(dst);dst.close()
maxidx=c.execute('select coalesce(max(entry_index),-1) from entries').fetchone()[0]
has_fts=c.execute("select count(*) from sqlite_master where name='entries_fts'").fetchone()[0]>0
created=[]
try:
 c.execute('BEGIN IMMEDIATE')
 for cat,article,word,en,fa in fresh:
    scope,func,objects=CAT[cat]
    upper=article.capitalize()
    # Meaningful contexts that are category-specific and use correct nominative articles
    s1={'hardware':f'{upper} {word} gehört zur Hardware des Computers.',
        'network':f'{upper} {word} ist für die Kommunikation im Netzwerk relevant.',
        'security':f'{upper} {word} verbessert die Sicherheit des IT-Systems.',
        'data':f'{upper} {word} ist bei der Verwaltung großer Datenmengen wichtig.',
        'software':f'{upper} {word} wird in modernen Softwareprojekten verwendet.',
        'dev':f'{upper} {word} spielt in der Softwareentwicklung eine wichtige Rolle.'}[cat]
    s2=f'Im Fachgespräch erklären wir, wofür {article} {word} benötigt wird.'
    raw=(f'{article} {word} (Substantiv): {en}\n'
         f'English: {en}\nPersian: {fa}\nPenglish: {roman(fa)}\n'
         f'Grammatical role: Substantiv, {"Maskulinum" if article=="der" else "Femininum" if article=="die" else "Neutrum"}\n'
         f'Bedeutung: Fachbegriff aus dem Bereich {scope}; bezeichnet {en} im Zusammenhang mit {func}.\n'
         f'Gebrauch: Fachsprache der Informatik; häufig in technischen Dokumentationen.\n'
         f'Synonyme: {en} (englischer Fachausdruck)\n'
         f'Kollokation: {article} {word} in einem IT-System\n'
         f'ex: {s1}: The term {en} is relevant to {scope.lower()}.\n'
         f'ex: {s2}: In a technical discussion, we explain what {en} is needed for.')
    e=dc.parse_entry(raw)
    maxidx+=1
    vals=(maxidx,e.raw,e.first_line,e.headword,e.role,e.translation,e.headword_norm,e.lexeme_norm,e.translation_norm,e.search_norm)
    c.execute('INSERT INTO entries(entry_index,raw,first_line,headword,role,translation,headword_norm,lexeme_norm,translation_norm,search_norm) VALUES (?,?,?,?,?,?,?,?,?,?)', vals)
    if has_fts:
      c.execute('INSERT INTO entries_fts(rowid,headword_norm,lexeme_norm,translation_norm,search_norm) VALUES (?,?,?,?,?)',(maxidx,e.headword_norm,e.lexeme_norm,e.translation_norm,e.search_norm))
    created.append(word)
 c.commit()
except: c.rollback();raise
print('ADDED',len(created),'TOTAL',c.execute('select count(*) from entries').fetchone()[0])
print('BACKUP',backup)
print('FTS',has_fts)
print('FIRST',created[:10]);print('LAST',created[-10:])
print('INTEGRITY',c.execute('pragma integrity_check').fetchone()[0])
