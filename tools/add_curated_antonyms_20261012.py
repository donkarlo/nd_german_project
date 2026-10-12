#!/usr/bin/env python3
"""Add verified new German vocabulary with explicit antonyms and valency; transaction-safe."""
import sqlite3, shutil, datetime, re, unicodedata
from pathlib import Path

DB=Path('/home/donkarlo/Dropbox/repo/data/nd_german_project/dictionary.sqlite3')
# word | english | persian | penglish | antonym | meaning | synonym | example-de | example-en | example-de | example-en | valency
DATA = """
abmildern|mitigate; soften|تخفیف دادن؛ ملایم کردن|takhfif dadan; molayem kardan|verschärfen|die Stärke oder Schwere von etwas vermindern|abschwächen|Die Maßnahmen mildern die Folgen ab.|The measures mitigate the consequences.|Der Regen milderte die Hitze ab.|The rain softened the heat.|etwas [Akk.]
verschärfen|intensify; aggravate|تشدید کردن؛ سخت‌تر کردن|tashdid kardan; sakht-tar kardan|abmildern|eine Situation oder Regel strenger oder schlimmer machen|zuspitzen|Die Krise verschärft die Spannungen.|The crisis aggravates tensions.|Die Behörde verschärft die Regeln.|The authority tightens the rules.|etwas [Akk.]
entkräften|refute; invalidate|رد کردن؛ بی‌اعتبار کردن|rad kardan; bi-etebar kardan|bekräftigen|ein Argument durch Gegenbeweise widerlegen|widerlegen|Neue Belege entkräften den Verdacht.|New evidence refutes the suspicion.|Sie konnte den Einwand entkräften.|She was able to invalidate the objection.|etwas [Akk.]
bekräftigen|reaffirm; reinforce|تأکید دوباره کردن؛ تقویت کردن|taakid-e dobareh kardan; taghviat kardan|entkräften|eine Aussage ausdrücklich bestätigen|bestätigen|Er bekräftigt seine Zusage.|He reaffirms his promise.|Die Ergebnisse bekräftigen unsere Vermutung.|The findings reinforce our assumption.|etwas [Akk.]
aufwiegeln|incite; stir up|تحریک کردن؛ شوراندن|tahrik kardan; shoorandan|beschwichtigen|Menschen zu Unruhe oder Widerstand anstacheln|anstacheln|Der Redner wiegelt die Menge auf.|The speaker incites the crowd.|Falsche Gerüchte wiegelten die Menschen auf.|False rumors stirred people up.|jemanden [Akk.]
deeskalieren|de-escalate|تنش‌زدایی کردن|tanesh-zodaii kardan|eskalieren|eine angespannte Lage weniger gefährlich machen|entschärfen|Die Vermittlerin versucht den Konflikt zu deeskalieren.|The mediator tries to de-escalate the conflict.|Beide Seiten konnten die Lage deeskalieren.|Both sides managed to de-escalate the situation.|etwas [Akk.]
verharmlosen|downplay; trivialize|کوچک جلوه دادن؛ کم‌اهمیت شمردن|koochak jelveh dadan; kam-ahammiyat shemordan|dramatisieren|eine Gefahr als weniger ernst darstellen|bagatellisieren|Man darf diese Risiken nicht verharmlosen.|We must not downplay these risks.|Er verharmlost das Problem.|He trivializes the problem.|etwas [Akk.]
abschwächen|weaken; attenuate|تضعیف کردن؛ کاهش دادن|tazif kardan; kahesh dadan|verstärken|etwas weniger stark oder intensiv machen|mindern|Das Material schwächt den Schall ab.|The material attenuates sound.|Die Aussage wurde später abgeschwächt.|The statement was later softened.|etwas [Akk.]
verstärken|strengthen; amplify|تقویت کردن؛ شدت دادن|taghviat kardan; sheddat dadan|abschwächen|die Stärke oder Intensität erhöhen|steigern|Das Mikrofon verstärkt die Stimme.|The microphone amplifies the voice.|Die Nachricht verstärkte ihre Sorge.|The news increased her concern.|etwas [Akk.]
befrieden|pacify; bring peace to|آرام کردن؛ صلح برقرار کردن|aram kardan; solh bargharaar kardan|aufwiegeln|einen Konflikt durch friedliche Einigung beenden|versöhnen|Die Gespräche sollen die Region befrieden.|The talks aim to bring peace to the region.|Ein Vertrag konnte den Streit befrieden.|An agreement was able to settle the dispute.|etwas [Akk.]
begünstigen|favor; facilitate|مساعد کردن؛ به نفع کسی عمل کردن|mosaed kardan; be nafe kasi amal kardan|benachteiligen|jemandem einen Vorteil verschaffen oder etwas fördern|fördern|Die Regel begünstigt große Unternehmen.|The rule favors large companies.|Warmes Wetter begünstigt das Wachstum.|Warm weather facilitates growth.|jemanden/etwas [Akk.]
missbilligen|disapprove of|نپسندیدن؛ مخالفت نشان دادن|napasandidan; mokhalefat neshan dadan|billigen|ein Verhalten ausdrücklich ablehnen|ablehnen|Sie missbilligt sein Verhalten.|She disapproves of his behavior.|Der Ausschuss missbilligte die Entscheidung.|The committee disapproved of the decision.|etwas [Akk.]
vernachlässigen|neglect|غفلت کردن از؛ نادیده گرفتن|gheflat kardan az; nadideh gereftan|pflegen|sich nicht ausreichend um jemanden oder etwas kümmern|ignorieren|Er vernachlässigt seine Gesundheit.|He neglects his health.|Die Firma hat die Wartung vernachlässigt.|The company neglected maintenance.|jemanden/etwas [Akk.]
beschönigen|gloss over; sugarcoat|بهتر از واقعیت نشان دادن|behtar az vagheiyat neshan dadan|bloßstellen|Mängel weniger schlimm darstellen als sie sind|verharmlosen|Der Bericht beschönigt die Lage.|The report sugarcoats the situation.|Wir sollten die Fehler nicht beschönigen.|We should not gloss over the mistakes.|etwas [Akk.]
bloßstellen|humiliate; expose|رسوا کردن؛ خجالت‌زده کردن|rosva kardan; khejalat-zadeh kardan|beschützen|jemanden öffentlich in eine peinliche Lage bringen|demütigen|Er wollte sie vor allen bloßstellen.|He wanted to humiliate her in front of everyone.|Die Frage stellte den Gast bloß.|The question embarrassed the guest.|jemanden [Akk.]
drosseln|throttle; reduce|کاهش دادن؛ محدود کردن|kahesh dadan; mahdood kardan|ankurbeln|Tempo oder Leistung gezielt verringern|reduzieren|Die Firma drosselt die Produktion.|The company reduces production.|Das Gerät drosselt die Geschwindigkeit.|The device throttles the speed.|etwas [Akk.]
präzisieren|specify; clarify|دقیق‌تر کردن؛ روشن‌تر بیان کردن|daghigh-tar kardan; roshan-tar bayan kardan|verallgemeinern|eine Aussage genauer formulieren|konkretisieren|Bitte präzisieren Sie Ihre Frage.|Please clarify your question.|Die Forscherin präzisiert ihre Hypothese.|The researcher specifies her hypothesis.|etwas [Akk.]
entschärfen|defuse; alleviate|خنثی کردن؛ از شدت کاستن|khonsa kardan; az sheddat kastan|zuspitzen|eine gefährliche Situation weniger gefährlich machen|deeskalieren|Das Gespräch entschärfte den Konflikt.|The conversation defused the conflict.|Fachleute entschärften die Bombe.|Experts defused the bomb.|etwas [Akk.]
zuspitzen|intensify; bring to a head|حادتر کردن؛ به اوج رساندن|had-tar kardan; be ouj resandan|entschärfen|eine Lage oder Frage schärfer herausarbeiten|verschärfen|Die Debatte spitzt den Konflikt zu.|The debate brings the conflict to a head.|Er spitzte seine These bewusst zu.|He deliberately sharpened his thesis.|etwas [Akk.]
""".strip()

def norm(s):
    t=unicodedata.normalize('NFKD',s).lower()
    return ''.join(c for c in t if not unicodedata.combining(c)).replace('ß','ss')
def textnorm(s):
    return re.sub(r'[^\w\s]+',' ',norm(s)).strip()
records=[line.split('|') for line in DATA.splitlines()]
assert all(len(r)==12 for r in records), [(r[0],len(r)) for r in records]
assert len(set(r[0] for r in records))==len(records)
backup=DB.with_name('dictionary.before_curated_antonyms_20261012.sqlite3')
if not backup.exists():
    source=sqlite3.connect(str(DB)); dest=sqlite3.connect(str(backup));source.backup(dest);dest.close();source.close()
c=sqlite3.connect(str(DB));c.execute('PRAGMA foreign_keys=ON')
roles={row[1]:row[0] for row in c.execute('select * from verb_argument_roles')}
cases={row[1]:row[0] for row in c.execute('select * from grammatical_cases')}
start=c.execute('select coalesce(max(entry_index),0) from entries').fetchone()[0]
added=[];skipped=[]
try:
 c.execute('BEGIN IMMEDIATE')
 for w,en,fa,peng,ant,meaning,syn,de1,eng1,de2,eng2,val in records:
    if c.execute('select 1 from entries where headword_norm=?',(norm(w),)).fetchone():
        skipped.append(w);continue
    start+=1
    first=f'{w} (Verb): {en}'
    raw='\n'.join([first,f'English: {en}',f'Persian: {fa}',f'Penglish: {peng}',f'Bedeutung: {meaning}',f'Gebrauch: {val}; häufig in der Standardsprache',f'Synonyme: {syn}',f'Gegenteile: {ant}',f'Rektion: {val}',f'ex: {de1}: {eng1}',f'ex: {de2}: {eng2}'])
    c.execute('insert into entries values(?,?,?,?,?,?,?,?,?,?)',(start,raw,first,w,'verb',en,norm(w),norm(w),textnorm(en),textnorm(raw)))
    c.execute('insert into entries_fts(rowid,headword_norm,lexeme_norm,translation_norm,search_norm) values(?,?,?,?,?)',(start,norm(w),norm(w),textnorm(en),textnorm(raw)))
    key='verb|'+norm(w)
    c.execute('insert into verb_valency_entries values(?,?,?,?,?,?)',(key,norm(w),w,'verb',start,0))
    pid=c.execute('insert into verb_valency_patterns(entry_key,pattern_order,sense_label,display_text,source,confidence) values(?,?,?,?,?,?)',(key,0,None,val,'explicit',1.0)).lastrowid
    argtype='dative_object' if '[Dat.]' in val else 'direct_object'
    case='DAT' if '[Dat.]' in val else 'AKK'
    c.execute('insert into verb_valency_arguments(pattern_id,argument_order,role_id,case_id,preposition_id,placeholder,required,reflexive,complementizer,infinitive_marker) values(?,?,?,?,?,?,?,?,?,?)',(pid,0,roles[argtype],cases[case],None,val.split(' [')[0],1,0,None,None))
    added.append(w)
 c.commit()
except:
 c.rollback();raise
print('ADDED:',len(added),', '.join(added))
print('SKIPPED:',len(skipped),', '.join(skipped))
print('TOTAL:',c.execute('select count(*) from entries').fetchone()[0])
print('INTEGRITY:',c.execute('pragma integrity_check').fetchone()[0])
print('FOREIGN_KEYS:',c.execute('pragma foreign_key_check').fetchall()[:5])
print('BACKUP:',backup)
c.close()
