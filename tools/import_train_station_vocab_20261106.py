"""Import missing vocabulary from the train-station passage into the SQLite primary dictionary.
Idempotent: only inserts absent normalized headwords; never writes to deprecated text dictionary.
Populates entries, FTS and verb-Rektion tables in a single transaction.
"""
from __future__ import annotations
from pathlib import Path
import sys
import sqlite3

ROOT = Path("/home/donkarlo/Dropbox/repo/nd_german_project")
DB = Path("/home/donkarlo/Dropbox/repo/data/nd_german_project/dictionary.sqlite3")
sys.path.insert(0, str(ROOT / "src" / "nd_german"))
import dictionary_core
import verb_valency

ENTRIES = [
    "die Anzeigetafel: display board; information board\nEnglish: display board; information board\nPersian: تابلوی اطلاعات؛ تابلو نمایش زمان حرکت قطارها\nPenglish: tabloye ettelaat; tabloye neshayesh-e zamane harekate ghatarha\nGrammatical role: Nomen (Femininum)\nBedeutung: Tafel oder elektronische Anzeige, auf der beispielsweise Abfahrtszeiten, Ziele und Gleise von Zügen stehen.\nGenitiv: der Anzeigetafel\nPlural: die Anzeigetafeln\nKollokation: auf die Anzeigetafel schauen; die Anzeigetafel am Bahnhof\nSynonyme: Informationstafel, Displaytafel\nex: Auf der Anzeigetafel steht, dass unser Zug von Gleis acht abfährt.: The information board says that our train departs from platform eight.\nex: Wir prüfen die Abfahrtszeit auf der Anzeigetafel.: We check the departure time on the display board.",
    "der Fahrkartenautomat: ticket vending machine; ticket machine\nEnglish: ticket vending machine; ticket machine\nPersian: دستگاه خودکار فروش بلیت؛ دستگاه بلیت‌فروشی\nPenglish: dastgahe khodkare forooshe belit; dastgahe belitforooshi\nGrammatical role: Nomen (Maskulinum)\nBedeutung: Automat, an dem man Fahrkarten für Bus, Bahn oder andere Verkehrsmittel selbst kaufen kann.\nGenitiv: des Fahrkartenautomaten\nPlural: die Fahrkartenautomaten\nKollokation: eine Fahrkarte am Fahrkartenautomaten kaufen; den Fahrkartenautomaten benutzen\nSynonyme: Ticketautomat, Fahrscheinautomat\nex: Wir kaufen unsere Fahrkarten am Fahrkartenautomaten.: We buy our tickets from the ticket machine.\nex: Der Fahrkartenautomat nimmt keine Münzen an.: The ticket machine does not accept coins.",
    "die Platzkarte [ˈplat͡sˌkaʁtə]: seat reservation ticket; reserved-seat ticket\nEnglish: seat reservation ticket; reserved-seat ticket\nPersian: بلیت رزرو صندلی؛ برگهٔ رزرو جای نشستن\nPenglish: belite rezerv-e sandali; bargeye rezerv-e jaye neshastan\nGrammatical role: Nomen (Femininum)\nBedeutung: Karte oder Nachweis, mit dem ein bestimmter Sitzplatz, besonders in einem Zug, reserviert ist.\nGenitiv: der Platzkarte\nPlural: die Platzkarten\nKollokation: eine Platzkarte kaufen; eine Platzkarte für einen Wagen haben\nSynonyme: Sitzplatzreservierung, Reservierungsnachweis\nex: Wir haben zwei Fahrkarten und zwei Platzkarten gekauft.: We bought two travel tickets and two seat reservations.\nex: Ohne Platzkarte ist dieser Sitzplatz nicht für uns reserviert.: Without a reservation ticket, this seat is not reserved for us.",
    "die Lokomotive [lokomoˈtiːvə]: locomotive; railway engine\nEnglish: locomotive; railway engine\nPersian: لوکوموتیو؛ ماشین کشندهٔ قطار\nPenglish: lokomotiv; mashine keshandeye ghatar\nGrammatical role: Nomen (Femininum)\nBedeutung: Schienenfahrzeug mit eigenem Antrieb, das andere Eisenbahnwagen ziehen oder schieben kann.\nGenitiv: der Lokomotive\nPlural: die Lokomotiven\nKollokation: eine Lokomotive steuern; die Lokomotive zieht Wagen\nSynonyme: Lok, Triebfahrzeug\nex: Der Lokführer schaut aus der Lokomotive heraus.: The train driver looks out of the locomotive.\nex: Eine elektrische Lokomotive zieht den Güterzug.: An electric locomotive pulls the freight train.",
    "der Lokführer [ˈlɔkˌfyːʁɐ]: train driver; locomotive engineer\nEnglish: train driver; locomotive engineer\nPersian: رانندهٔ قطار؛ لوکوموتیوران\nPenglish: ranandeye ghatar; lokomotivran\nGrammatical role: Nomen (Maskulinum)\nBedeutung: Person, die eine Lokomotive oder einen Zug führt und dessen Fahrt steuert.\nGenitiv: des Lokführers\nPlural: die Lokführer\nKollokation: als Lokführer arbeiten; der Lokführer fährt den Zug\nSynonyme: Triebfahrzeugführer, Zugführer (nicht immer bedeutungsgleich)\nex: Der Lokführer wollte gerade abfahren.: The train driver was just about to depart.\nex: Der Lokführer wartet auf das Abfahrtsignal.: The locomotive driver is waiting for the departure signal.",
    "der Schaffner [ˈʃafnɐ]: train conductor; ticket inspector\nEnglish: train conductor; ticket inspector\nPersian: مأمور قطار؛ مأمور کنترل بلیت\nPenglish: mamure ghatar; mamure kontrol-e belit\nGrammatical role: Nomen (Maskulinum)\nBedeutung: Person, die in einem Zug Fahrgäste betreut oder Fahrkarten kontrolliert; traditionelle Bezeichnung, die je nach Bahnunternehmen durch andere Berufsbezeichnungen ersetzt ist.\nGenitiv: des Schaffners\nPlural: die Schaffner\nKollokation: der Schaffner kontrolliert die Fahrkarten; den Schaffner fragen\nSynonyme: Zugbegleiter, Fahrkartenkontrolleur (je nach Aufgabe)\nex: Der Schaffner war freundlich und wartete auf uns.: The conductor was friendly and waited for us.\nex: Der Schaffner kontrolliert die Fahrkarten der Passagiere.: The conductor checks the passengers' tickets.",
    "herausschauen [hɛˈʁaʊ̯sˌʃaʊ̯ən] (Verb, trennbar, intransitiv): to look out; to peer out\nEnglish: to look out; to peer out\nPersian: از داخل چیزی به بیرون نگاه کردن؛ سرک کشیدن\nPenglish: az dakhele chizi be biroon negah kardan; sarak keshidan\nGrammatical role: Verb (trennbar, intransitiv)\nGebrauch: Typisch: aus dem Fenster, aus der Lokomotive oder durch eine Öffnung herausschauen. Die Ortsangabe ist nicht zwingend ein fest regiertes Objekt.\nBedeutung: Von einem Innenraum oder einem geschützten Ort aus nach draußen schauen.\nSynonyme: hinausschauen, nach draußen schauen\nex: Der Lokführer schaute aus der Lokomotive heraus.: The driver looked out of the locomotive.\nex: Sie schaut aus dem Fenster heraus, um den Zug zu sehen.: She looks out of the window to see the train.\nImperativ: schau heraus!; schaut heraus!; schauen Sie heraus!\nPräsens: ich schaue heraus\nPräteritum: ich schaute heraus\nPerfekt: ich habe herausgeschaut\nFutur I: ich werde herausschauen\nKonjunktiv II: ich würde herausschauen\nKonjunktiv I: ich schaue heraus",
    "oje [oˈjeː] (Interjektion): oh dear!; oh no!\nEnglish: oh dear!; oh no!\nPersian: ای وای!؛ وای!؛ اوه نه!\nPenglish: ey vay!; vay!; oh na!\nGrammatical role: Interjektion (Ausruf)\nGebrauch: Meist am Anfang einer Äußerung; auch als oh je geschrieben.\nBedeutung: Ausruf des Erschreckens, Bedauerns oder der Besorgnis über eine unangenehme Situation.\nSynonyme: ach du meine Güte, oh nein\nex: Oje! Wir haben nur noch zwei Minuten bis zur Abfahrt.: Oh no! We have only two minutes left before departure.\nex: Oje, ich habe meine Fahrkarte vergessen!: Oh dear, I forgot my ticket!",
    "nur noch [nuːɐ̯ nɔx] (Adverbiale Wendung): only ... left; just ... remaining\nEnglish: only ... left; just ... remaining\nPersian: فقط ... دیگر؛ تنها ... باقی مانده\nPenglish: faghat ... digeh; tanha ... baghi mandeh\nGrammatical role: Adverbiale Wendung\nGebrauch: Häufig vor Zahlen, Zeitangaben oder Personen. Im Gegensatz zu nur deutet noch auf einen verbleibenden Rest hin.\nBedeutung: Drückt aus, dass von einer Menge, einer Frist oder einer Möglichkeit lediglich ein geringer Rest verbleibt.\nSynonyme: lediglich noch, bloß noch\nex: Wir haben nur noch zwei Minuten bis zur Abfahrt.: We have only two minutes left until departure.\nex: Es sind nur noch drei Plätze frei.: Only three seats are still available.",
    "noch einmal gut gehen (Verb, feste Wendung): to turn out all right after a close call\nEnglish: to turn out all right after a close call\nPersian: به خیر گذشتن؛ با وجود خطر یا مشکل بدون آسیب جدی تمام شدن\nPenglish: be kheyr gozashtan; ba vojood-e khatar ya moshkel bedoone asibe jeddi tamoom shodan\nGrammatical role: Verb (feste Wendung, unpersönlich)\nGebrauch: Typisch mit es oder das als Subjekt: Das ist (ja gerade) noch einmal gut gegangen! Vergleiche gutgehen.\nBedeutung: Eine gefährliche oder problematische Situation endet ohne größeren Schaden, obwohl es fast anders gekommen wäre.\nSynonyme: glimpflich ausgehen, mit einem Schrecken davonkommen\nex: Das ist ja gerade noch einmal gut gegangen!: That was a close call, but it turned out all right!\nex: Wir hätten beinahe den Zug verpasst, aber es ist noch einmal gut gegangen.: We almost missed the train, but luckily everything turned out fine.\nPräsens: es geht noch einmal gut\nPräteritum: es ging noch einmal gut\nPerfekt: es ist noch einmal gut gegangen\nFutur I: es wird noch einmal gut gehen\nKonjunktiv II: es würde noch einmal gut gehen\nKonjunktiv I: es gehe noch einmal gut",
    "Das kann doch nicht sein! (Redewendung): That can't be!; You must be kidding!\nEnglish: That can't be!; You must be kidding!\nPersian: امکان ندارد!؛ مگه می‌شه!؛ باورکردنی نیست!\nPenglish: emkan nadare!; mage misheh!; bavar kardani nist!\nGrammatical role: Feste Redewendung (Ausruf)\nGebrauch: Das Modalpartikel doch verstärkt hier die Überraschung oder den Widerspruch.\nBedeutung: Ausruf des Unglaubens, der Überraschung oder der Empörung, wenn etwas den Erwartungen stark widerspricht.\nSynonyme: Das ist doch unmöglich!; Das gibt's doch nicht!\nex: Das kann doch nicht sein! Auf unserem Bahnsteig steht ein Güterzug.: That can't be! There is a freight train at our platform.\nex: Das kann doch nicht sein! Meine Platzkarte ist verschwunden.: You must be kidding! My seat reservation ticket has disappeared.",
    "so schnell man kann (Adverbiale Wendung): as fast as one can; as quickly as possible\nEnglish: as fast as one can; as quickly as possible\nPersian: تا جایی که می‌شود سریع؛ با بیشترین سرعت ممکن\nPenglish: ta jaee ke misheh sari; ba bishtarin sorate momken\nGrammatical role: Adverbiale Wendung (Vergleichskonstruktion)\nGebrauch: Mit wechselndem Subjekt und Tempus: so schnell ich kann, so schnell wir konnten. Auch: so schnell, wie man kann.\nBedeutung: Bezeichnet die höchstmögliche Geschwindigkeit einer Handlung unter den gegebenen Umständen.\nSynonyme: so rasch wie möglich, mit höchstmöglicher Geschwindigkeit\nex: So schnell wir konnten, rannten wir zum richtigen Gleis.: As fast as we could, we ran to the correct platform.\nex: Bitte komm so schnell du kannst!: Please come as quickly as you can!",
    "quer über (Präpositionale Wendung, über + Akk.): across; from one side to the other\nEnglish: across; from one side to the other\nPersian: از عرضِ چیزی؛ از یک طرف به طرف دیگرِ چیزی\nPenglish: az arze chizi; az yek taraf be tarafe digare chizi\nGrammatical role: Präpositionale Wendung (über + Akkusativ)\nGebrauch: Typisch: quer über den Platz, quer über den Bahnhof; über steht bei der Richtungsangabe mit Akkusativ.\nBedeutung: Bezeichnet eine Bewegung quer durch oder über eine Fläche von einer Seite zur anderen.\nSynonyme: quer durch, über die ganze Breite\nex: Wir rannten quer über den Bahnhof.: We ran across the station.\nex: Die Kinder liefen quer über den Platz.: The children ran across the square."
]

def run():
    assert DB.is_file(), f"Missing primary SQLite dictionary: {DB}"
    con = sqlite3.connect(DB, timeout=20)
    con.execute("PRAGMA foreign_keys=ON")
    con.execute("PRAGMA busy_timeout=20000")
    before = con.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
    fts_before = con.execute("SELECT COUNT(*) FROM entries_fts").fetchone()[0]
    known_heads = {x[0] for x in con.execute("SELECT headword_norm FROM entries")}
    known_lexemes = {x[0] for x in con.execute("SELECT lexeme_norm FROM entries")}
    added = []
    skipped = []
    try:
        con.execute("BEGIN IMMEDIATE")
        idx = con.execute("SELECT COALESCE(MAX(entry_index),0)+1 FROM entries").fetchone()[0]
        for raw in ENTRIES:
            parsed = dictionary_core.parse_entry(raw)
            lines = raw.splitlines()
            required = ("English:", "Persian:", "Penglish:", "Grammatical role:", "Bedeutung:")
            assert all(any(l.startswith(k) for l in lines) for k in required), parsed.headword
            assert sum(l.startswith("ex:") for l in lines) >= 2, parsed.headword
            if parsed.role == "noun":
                assert any(l.startswith("Genitiv:") for l in lines), parsed.headword
                assert any(l.startswith("Plural:") for l in lines), parsed.headword
            if parsed.role == "verb":
                assert all(any(l.startswith(k) for l in lines)
                           for k in ("Präsens:", "Präteritum:", "Perfekt:",
                                     "Futur I:", "Konjunktiv II:", "Konjunktiv I:")),parsed.headword
            if parsed.headword_norm in known_heads or parsed.lexeme_norm in known_lexemes:
                skipped.append(parsed.headword)
                continue
            con.execute("INSERT INTO entries"
                        " (entry_index,raw,first_line,headword,role,translation,"
                        " headword_norm,lexeme_norm,translation_norm,search_norm)"
                        " VALUES (?,?,?,?,?,?,?,?,?,?)",
                        (idx,parsed.raw,parsed.first_line,parsed.headword,
                         parsed.role,parsed.translation,parsed.headword_norm,
                         parsed.lexeme_norm,parsed.translation_norm,parsed.search_norm))
            con.execute("INSERT INTO entries_fts"
                        " (rowid,headword_norm,lexeme_norm,translation_norm,search_norm)"
                        " VALUES (?,?,?,?,?)",
                        (idx,parsed.headword_norm,parsed.lexeme_norm,
                         parsed.translation_norm,parsed.search_norm))
            if verb_valency._is_verbish(parsed.role,parsed.headword,parsed.raw,parsed.first_line):
                verb_valency._replace_valency(con,entry_index=idx,headword=parsed.headword,
                                             headword_norm=parsed.headword_norm,role=parsed.role,
                                             patterns=verb_valency._patterns_for_entry(
                                                 parsed.raw,parsed.first_line,parsed.headword))
            known_heads.add(parsed.headword_norm)
            known_lexemes.add(parsed.lexeme_norm)
            added.append((idx,parsed.headword,parsed.role))
            idx+=1
        con.execute("INSERT OR REPLACE INTO meta(key,value) VALUES ('verb_rektion_dirty','0')")
        con.commit()
    except Exception:
        con.rollback()
        raise
    after=con.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
    fts_after=con.execute("SELECT COUNT(*) FROM entries_fts").fetchone()[0]
    validity=con.execute("PRAGMA integrity_check").fetchone()[0]
    foreign=con.execute("PRAGMA foreign_key_check").fetchall()
    rowless=con.execute("SELECT COUNT(*) FROM entries e LEFT JOIN entries_fts f ON f.rowid=e.entry_index WHERE f.rowid IS NULL").fetchone()[0]
    print("ENTRIES_BEFORE:",before,"FTS_BEFORE:",fts_before)
    print("INSERTED:",len(added),"SKIPPED_EXISTING:",len(skipped))
    for i,h,r in added: print("ADDED:",i,h,"("+r+")")
    for h in skipped: print("SKIPPED:",h)
    print("ENTRIES_AFTER:",after,"FTS_AFTER:",fts_after)
    print("UNINDEXED_ENTRIES:",rowless,"FOREIGN_KEY_ERRORS:",len(foreign),"INTEGRITY:",validity)
    assert after-before == len(added)
    assert fts_after-fts_before == len(added)
    assert after == fts_after and rowless == 0
    assert validity == "ok" and len(foreign) == 0
    con.close()

if __name__ == "__main__":
    run()
