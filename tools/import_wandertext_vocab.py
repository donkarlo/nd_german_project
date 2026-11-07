"""Add missing vocabulary from the hiking-tourism passage to the canonical SQLite dictionary.
Re-runnable, inserts only absent normalized lexemes, preserves all prior entries.
"""
from pathlib import Path
import sqlite3
import sys

ROOT = Path("/home/donkarlo/Dropbox/repo/nd_german_project")
sys.path.insert(0, str(ROOT / "src" / "nd_german"))
import dictionary_core
import verb_valency

DB = Path("/home/donkarlo/Dropbox/repo/data/nd_german_project/dictionary.sqlite3")

ENTRIES = [
"""die Wanderroute [ˈvandɐˌʁuːtə]: hiking trail; hiking route
English: hiking trail; hiking route
Persian: مسیر پیاده‌روی در طبیعت؛ مسیر طبیعت‌گردی
Penglish: masire piyadeh-ravi dar tabiat; masire tabiatgardi
Grammatical role: Nomen (feminin)
Bedeutung: Eine festgelegte oder empfohlene Strecke, auf der Menschen wandern.
Genitiv: der Wanderroute
Plural: die Wanderrouten
Kollokation: eine beliebte Wanderroute; einer Wanderroute folgen
Synonyme: Wanderweg, Wanderstrecke
ex: Unser Dorf liegt an einer beliebten Wanderroute.: Our village lies along a popular hiking trail.
ex: Die Wanderroute führt durch die Berge.: The hiking route runs through the mountains.""",
"""das Inland [ˈɪnlant]: one's own country; domestic territory
English: one's own country; domestic territory
Persian: داخل کشور؛ محدودهٔ داخلی یک کشور
Penglish: dakhele keshvar; mahdood-ye dakheliye yek keshvar
Grammatical role: Nomen (neutral)
Bedeutung: Das Gebiet innerhalb der Grenzen des eigenen oder eines betrachteten Staates, im Gegensatz zum Ausland.
Genitiv: des Inlands
Plural: normalerweise kein Plural
Kollokation: im Inland; aus dem Inland; In- und Ausland
Synonyme: eigenes Staatsgebiet
ex: Viele Gäste kommen aus dem Inland.: Many guests come from within the country.
ex: Die Nachfrage im Inland ist gestiegen.: Domestic demand has increased.""",
"""In- und Ausland (Phrase): home and abroad; domestic and foreign countries
English: home and abroad; domestic and foreign countries
Persian: داخل و خارج کشور؛ در کشور و خارج از کشور
Penglish: dakhel va khareje keshvar; dar keshvar va kharej az keshvar
Grammatical role: Feste Wortverbindung
Bedeutung: Verkürzte Verbindung von Inland und Ausland, die beide Bereiche zusammen bezeichnet.
Verwendung: im In- und Ausland; aus dem In- und Ausland
ex: Touristen aus dem In- und Ausland besuchen die Stadt.: Tourists from home and abroad visit the city.
ex: Das Unternehmen ist im In- und Ausland tätig.: The company operates at home and abroad.""",
"""zum Glück [t͡sʊm ɡlʏk] (Adverbiale Wendung): fortunately; luckily
English: fortunately; luckily
Persian: خوشبختانه؛ از خوش‌شانسی
Penglish: khoshbakhtaneh; az khosh-shansi
Grammatical role: Adverbiale Wendung
Bedeutung: Drückt Erleichterung darüber aus, dass etwas Gutes geschehen oder etwas Schlechtes ausgeblieben ist.
Synonyme: glücklicherweise, erfreulicherweise
ex: Zum Glück gibt es hier einen Campingplatz.: Fortunately, there is a campsite here.
ex: Zum Glück haben wir den letzten Bus erreicht.: Luckily, we caught the last bus.""",
"""der Campingplatz [ˈkɛmpɪŋˌplat͡s]: campsite; campground
English: campsite; campground
Persian: محل کمپینگ؛ محل چادر زدن
Penglish: mahale kamping; mahale chador zadan
Grammatical role: Nomen (maskulin)
Bedeutung: Ein Gelände, auf dem Reisende mit Zelten, Wohnwagen oder Wohnmobilen übernachten können.
Genitiv: des Campingplatzes
Plural: die Campingplätze
Kollokation: auf dem Campingplatz übernachten; einen Campingplatz buchen
Synonyme: Zeltplatz
ex: Wir übernachten auf einem Campingplatz am See.: We are staying at a campsite by the lake.
ex: Der Campingplatz ist im Sommer oft voll.: The campsite is often full in summer.""",
"""Pause machen [ˈpaʊ̯zə ˈmaxn̩] (Phrase, Verb): to take a break
English: to take a break; to pause
Persian: استراحت کردن؛ وقفه‌ای در کار ایجاد کردن
Penglish: esterahat kardan; vaghfe-i dar kar ijad kardan
Grammatical role: Verb (feste Wendung)
Verwendung: eine Pause machen; kurz Pause machen; ein paar Tage Pause machen
Bedeutung: Eine Tätigkeit für eine begrenzte Zeit unterbrechen, um sich auszuruhen oder später weiterzumachen.
Synonyme: pausieren, sich ausruhen, eine Rast einlegen
ex: Die Wanderer machen im Dorf ein paar Tage Pause.: The hikers take a break in the village for a few days.
ex: Nach zwei Stunden Arbeit machen wir eine Pause.: After two hours of work, we take a break.
Imperativ: mach Pause!; macht Pause!; machen Sie Pause!
Präsens: ich mache Pause
Präteritum: ich machte Pause
Perfekt: ich habe Pause gemacht
Futur I: ich werde Pause machen
Konjunktiv II: ich würde Pause machen
Konjunktiv I: ich mache Pause""",
"""der Reiseleiter [ˈʁaɪ̯zəˌlaɪ̯tɐ]: tour guide
English: tour guide
Persian: راهنمای تور؛ راهنمای گردشگری
Penglish: rahnamaye toor; rahnamaye gardeshgari
Grammatical role: Nomen (maskulin)
Bedeutung: Eine Person, die Reisende oder Touristengruppen betreut, begleitet und über besuchte Orte informiert.
Genitiv: des Reiseleiters
Plural: die Reiseleiter
Kollokation: als Reiseleiter arbeiten; ein erfahrener Reiseleiter
Synonyme: Fremdenführer, Tourguide
ex: Mein Onkel arbeitet als Reiseleiter.: My uncle works as a tour guide.
ex: Der Reiseleiter zeigt uns die Altstadt.: The tour guide shows us the old town.""",
"""die Touristengruppe: tourist group; group of tourists
English: tourist group; group of tourists
Persian: گروه گردشگران؛ گروه توریست‌ها
Penglish: gorohe gardeshgaran; gorohe tooristha
Grammatical role: Nomen (feminin)
Bedeutung: Eine Gruppe von Menschen, die gemeinsam als Touristen reisen oder eine Sehenswürdigkeit besuchen.
Genitiv: der Touristengruppe
Plural: die Touristengruppen
Kollokation: eine Touristengruppe führen; eine Touristengruppe begleiten
ex: Der Reiseleiter führt eine Touristengruppe durch die Stadt.: The tour guide leads a group of tourists through the city.
ex: Zwei Touristengruppen warten vor dem Schloss.: Two tourist groups are waiting in front of the palace.""",
"""die Touristeninformation: tourist information office; visitor information center
English: tourist information office; visitor information center
Persian: دفتر اطلاعات گردشگری؛ مرکز اطلاع‌رسانی گردشگران
Penglish: daftare ettelaate gardeshgari; markaze ettelaresaniye gardeshgaran
Grammatical role: Nomen (feminin)
Bedeutung: Eine Stelle oder Einrichtung, die Besucher über Unterkünfte, Sehenswürdigkeiten, Wege und Veranstaltungen informiert.
Genitiv: der Touristeninformation
Plural: die Touristeninformationen (bei mehreren Stellen)
Kollokation: zur Touristeninformation gehen; bei der Touristeninformation fragen
Synonyme: Touristinformation, Fremdenverkehrsbüro
ex: Die Führung beginnt an der Touristeninformation.: The guided tour begins at the tourist information office.
ex: Bei der Touristeninformation bekommt man einen Stadtplan.: You can get a city map at the tourist information office.""",
"""die Ansichtskarte [ˈanˌzɪçt͡sˌkaʁtə]: picture postcard
English: picture postcard; postcard showing a place
Persian: کارت‌پستال تصویری؛ کارت‌پستال
Penglish: karte postale tasviri; karte postal
Grammatical role: Nomen (feminin)
Bedeutung: Eine Postkarte mit einem Bild, meist einer Landschaft, Stadt oder Sehenswürdigkeit.
Genitiv: der Ansichtskarte
Plural: die Ansichtskarten
Kollokation: eine Ansichtskarte kaufen; eine Ansichtskarte verschicken
Synonyme: Postkarte, Bildpostkarte
ex: Ich kaufe eine Ansichtskarte vom Schloss.: I buy a picture postcard of the castle.
ex: Sie schickt ihrer Freundin eine Ansichtskarte.: She sends her friend a postcard.""",
"""der Stadtkern [ˈʃtatˌkɛʁn]: city center; urban core
English: city center; urban core
Persian: هستهٔ مرکزی شهر؛ مرکز شهر
Penglish: hasteye markaziye shahr; markaze shahr
Grammatical role: Nomen (maskulin)
Bedeutung: Der zentrale Teil einer Stadt, häufig mit älteren Gebäuden und wichtigen Einrichtungen.
Genitiv: des Stadtkerns
Plural: die Stadtkerne
Kollokation: der historische Stadtkern; der mittelalterliche Stadtkern
Synonyme: Stadtzentrum, Innenstadt (je nach Zusammenhang)
ex: Wir gehen durch den mittelalterlichen Stadtkern.: We walk through the medieval town center.
ex: Der alte Stadtkern ist gut erhalten.: The old town center is well preserved.""",
"""an ... vorbei (Präpositionale Wendung, an + Dat.): past; by
English: past; by
Persian: از کنار چیزی یا کسی گذشتن؛ از کنار عبور کردن
Penglish: az kenare chizi ya kasi gozashtan; az kenar oboor kardan
Grammatical role: Präpositionale Wendung (an + Dativ)
Verwendung: an jemandem/etwas (Dativ) vorbei; an einem Denkmal vorbei
Bedeutung: Bezeichnet eine Bewegung, bei der man sich an einer Person oder Sache entlang oder neben ihr vorüberbewegt.
Gebrauch: an verlangt hier den Dativ; vorbei steht gewöhnlich nach der Ergänzung.
ex: Wir gehen an einigen Denkmälern vorbei.: We walk past several monuments.
ex: Der Bus fährt an unserem Haus vorbei.: The bus passes by our house.""",
"""bis hin zu (Präpositionale Wendung, zu + Dat.): all the way to; up to and including
English: all the way to; up to and including
Persian: تا خودِ؛ حتی تا؛ تا حدِ
Penglish: ta khode; hatta ta; ta hadde
Grammatical role: Präpositionale Wendung (mit Dativ)
Verwendung: bis hin zu jemandem/etwas (Dativ)
Bedeutung: Betont den Endpunkt einer Strecke, einer Aufzählung oder einer Entwicklung.
Gebrauch: Die Präposition zu regiert den Dativ.
ex: Wir gehen durch die Altstadt bis hin zum Schloss.: We walk through the old town all the way to the castle.
ex: Die Temperaturen steigen bis hin zu 35 Grad.: Temperatures rise to as much as 35 degrees.""",
"""das Fernglas [ˈfɛʁnˌɡlaːs]: binoculars
English: binoculars; field glasses
Persian: دوربین دوچشمی
Penglish: doorbine docheshmi
Grammatical role: Nomen (neutral)
Bedeutung: Ein optisches Gerät mit zwei Okularen, mit dem man entfernte Gegenstände vergrößert betrachten kann.
Genitiv: des Fernglases
Plural: die Ferngläser
Kollokation: durch ein Fernglas schauen; mit dem Fernglas beobachten
ex: Durch das Fernglas kann man die Burgruine sehen.: You can see the castle ruins through the binoculars.
ex: Er beobachtet die Vögel mit einem Fernglas.: He watches the birds with binoculars.""",
"""der Wegweiser [ˈveːkˌvaɪ̯zɐ]: signpost; direction sign
English: signpost; direction sign
Persian: تابلوی راهنما؛ نشانگر مسیر
Penglish: tabloye rahnama; neshangare masir
Grammatical role: Nomen (maskulin)
Bedeutung: Ein Schild oder Zeichen, das die Richtung zu einem Ort oder das Weitergehen auf einem Weg anzeigt.
Genitiv: des Wegweisers
Plural: die Wegweiser
Kollokation: den Wegweisern folgen; ein Wegweiser zum Schloss
Synonyme: Richtungsschild, Hinweisschild
ex: Folge einfach den Wegweisern zur Burg.: Just follow the signposts to the castle.
ex: Am Wegweiser biegen wir rechts ab.: We turn right at the signpost.""",
"""ein paar [aɪ̯n paːɐ̯] (Indefinitpronomen): a few; several
English: a few; several
Persian: چند؛ تعدادی
Penglish: chand; tedadi
Grammatical role: Indefinitpronomen (unveränderlich)
Bedeutung: Eine kleine, nicht genau festgelegte Anzahl von Personen oder Dingen.
Gebrauch: paar wird hier kleingeschrieben; anders als das Nomen Paar für zwei zusammengehörige Personen oder Dinge.
ex: Wir bleiben ein paar Tage in diesem Ort.: We are staying in this town for a few days.
ex: Ich habe ein paar Fotos gemacht.: I took a few photos."""
]

def run():
    connection = sqlite3.connect(str(DB), timeout=15)
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA busy_timeout=15000")
    initial_count = connection.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
    existing = set(row[0] for row in connection.execute("SELECT lexeme_norm FROM entries"))
    existing_heads = set(row[0] for row in connection.execute("SELECT headword_norm FROM entries"))
    added = []
    skipped = []
    try:
        connection.execute("BEGIN IMMEDIATE")
        next_index = connection.execute("SELECT COALESCE(MAX(entry_index),0)+1 FROM entries").fetchone()[0]
        for raw in ENTRIES:
            entry = dictionary_core.parse_entry(raw)
            key = entry.lexeme_norm
            if (key in existing and entry.headword != 'ein paar') or entry.headword_norm in existing_heads:
                skipped.append(entry.headword)
                continue
            connection.execute(
                "INSERT INTO entries (entry_index,raw,first_line,headword,role,translation,headword_norm,lexeme_norm,translation_norm,search_norm) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (next_index,entry.raw,entry.first_line,entry.headword,entry.role,entry.translation,entry.headword_norm,entry.lexeme_norm,entry.translation_norm,entry.search_norm)
            )
            connection.execute(
                "INSERT INTO entries_fts (rowid,headword_norm,lexeme_norm,translation_norm,search_norm) VALUES (?,?,?,?,?)",
                (next_index,entry.headword_norm,entry.lexeme_norm,entry.translation_norm,entry.search_norm)
            )
            if verb_valency._is_verbish(entry.role, entry.headword, entry.raw, entry.first_line):
                patterns = verb_valency._patterns_for_entry(entry.raw, entry.first_line, entry.headword)
                verb_valency._replace_valency(
                    connection,entry_index=next_index,headword=entry.headword,
                    headword_norm=entry.headword_norm,role=entry.role,patterns=patterns
                )
            existing.add(key)
            added.append((next_index,entry.headword,entry.role))
            next_index += 1
        # Every inserted verbish entry has been indexed in the valency tables.
        connection.execute("INSERT OR REPLACE INTO meta(key,value) VALUES ('verb_rektion_dirty','0')")
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    c = sqlite3.connect(str(DB))
    c.execute("PRAGMA foreign_keys=ON")
    final_count = c.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
    fts_count = c.execute("SELECT COUNT(*) FROM entries_fts").fetchone()[0]
    errors = c.execute("PRAGMA foreign_key_check").fetchall()
    check = c.execute("PRAGMA integrity_check").fetchone()[0]
    print("INITIAL_ENTRIES:",initial_count)
    print("INSERTED:",len(added))
    for index,headword,role in added:
        print("ADDED:",index,headword,role)
    print("SKIPPED:",len(skipped),", ".join(skipped))
    print("FINAL_ENTRIES:",final_count)
    print("FTS_ENTRIES:",fts_count)
    print("VALENCY_ROWS_FOR_PAUSE:",c.execute("SELECT count(*) FROM verb_valency_entries WHERE headword_norm=?", (dictionary_core.normalize_text("Pause machen"),)).fetchone()[0])
    print("FOREIGN_KEY_ERRORS:",len(errors))
    print("INTEGRITY:",check)
    assert final_count-initial_count==len(added)
    assert final_count==fts_count
    assert not errors and check=="ok"
    c.close()

if __name__=="__main__":
    run()
