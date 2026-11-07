from pathlib import Path
import sqlite3, unicodedata
p=Path("/home/donkarlo/Dropbox/repo/data/nd_german_project/dictionary.sqlite3")
words="""ich|wohnen|in|ein|klein|Ort|der|an|beliebt|Wanderroute|liegen|Sommer|kommen|Tourist|aus|Inland|Ausland|In- und Ausland|hierher|oft|sein|sie|sehr|müde|weil|so|viel|Kilometer|mit|Rucksack|wandern|zum Glück|Glück|haben|wir|Campingplatz|oder|mehrere|mehrere|Hotel|wo|man|übernachten|können|unser|schön|machen|Wanderer|hier|paar|Tag|Pause|Pause machen|sich umsehen|umsehen|immer|ganz|begeistert|Kamera|unzählig|Foto|mein|Onkel|Reiseleiter|führen|Touristengruppe|durch|Tour|beginnen|Touristeninformation|auch|Ansichtskarte|und|Stadtplan|kaufen|Besucher|mittelalterlich|Stadtkern|einige|Denkmal|vorbei|an ... vorbei|bis hin zu|bis|hin|Schloss|Fernglas|zeigen|Ruine|alt|Burg|Berg|wenn|dorthin|wollen|folgen|einfach|Wegweiser""".split("|")
def norm(s):
    return ''.join(x for x in unicodedata.normalize("NFKD", s.casefold()) if not unicodedata.combining(x))
c=sqlite3.connect(str(p))
rows=c.execute("select headword,lexeme_norm from entries").fetchall()
index={}
for h,n in rows:
    index.setdefault(n,[]).append(h)
missing=[]
for w in dict.fromkeys(words):
    k=norm(w)
    matches=index.get(k,[])
    if not matches and w.startswith('sich '):
        matches=index.get(norm(w[5:]),[])
    if not matches:
        missing.append(w)
    print(("MISSING" if not matches else "EXISTS "),w,"->",'; '.join(matches[:4]))
print("MISSING COUNT",len(missing))
print("MISSING WORDS","|".join(missing))
