"""Conservative dictionary entry repair and validation.

Only deterministic grammatical mistakes and manually reviewed entries are
changed. Unknown translations are reported, never guessed.
"""
from __future__ import annotations

import re
from collections import Counter


class DictionaryQuality:
    _BAD_AUXILIARY = re.compile(r"(?m)^(Perfekt:\s*)ich (haben|sein)(?:}})?(?=\s)")
    _BAD_PERSIAN_VERB = re.compile(r"(?m)^Persian:\s*(?:شوخی|تلفن|برگرد)\s*$")
    _BAD_PERFECT = re.compile(r"(?m)^Perfekt:\s*ich (?:haben|sein)\s")

    # Manually checked: original entries included wrong meanings, examples,
    # Persian part of speech or impossible conjugation.
    CURATED = {
        "der Spaß": """der Spaß [ʃpaːs]: fun; enjoyment; joke; prank
English: fun; enjoyment; joke; prank
Persian: تفریح؛ سرگرمی؛ لذت؛ شوخی
Penglish: tafrih; sargarmi; lezzat; shookhi
Bedeutung: 1. Freude oder Vergnügen (meist unzählbar). 2. Scherz oder lustige Handlung (zählbar).
Genitiv: des Spaßes
Plural: die Späße
Kollokation: Spaß haben; Spaß machen; Spaß verstehen; aus Spaß; jemandem den Spaß verderben; Viel Spaß!
Synonyme: Vergnügen, Freude, Scherz, Amüsement
ex: Deutschlernen macht mir viel Spaß.: Learning German is a lot of fun for me.
ex: Ich wünsche dir viel Spaß bei der Feier!: I hope you have lots of fun at the party.
ex: Das war doch nur ein Spaß!: That was just a joke!""",
        "spaßen": """spaßen [ˈʃpaːsn̩] (Verb, intransitiv): to joke; to jest; to kid
English: to joke; to jest; to kid
Persian: شوخی کردن؛ مزاح کردن
Penglish: shookhi kardan; mozaah kardan
Bedeutung: etwas scherzhaft sagen oder tun; nicht ernst meinen.
Gebrauch: häufig in den Wendungen „Du spaßt wohl!“ und „mit jemandem ist nicht zu spaßen“; sonst eher scherzen.
Synonyme: scherzen, witzeln, einen Scherz machen
ex: Du spaßt doch nur, oder?: You're just joking, aren't you?
ex: Mit diesem Chef ist nicht zu spaßen.: This boss is not someone to mess with.
Präsens: ich spaße
Präteritum: ich spaßte
Perfekt: ich habe gespaßt
Futur I: ich werde spaßen
Konjunktiv II: ich würde spaßen
Konjunktiv I: ich spaße""",
        "spaßig": """spaßig [ˈʃpaːsɪç] (Adjektiv, Komparativ: spaßiger, Superlativ: am spaßigsten): funny; amusing; fun
English: funny; amusing; fun
Persian: بامزه؛ سرگرم‌کننده؛ خنده‌دار
Penglish: bamazeh; sargarm-konandeh; khandedar
Bedeutung: humorvoll, lustig oder unterhaltsam.
Synonyme: lustig, witzig, unterhaltsam, amüsant
Attributiv und prädikativ verwendbar
ex: Das war eine spaßige Idee.: That was a funny idea.
ex: Wir hatten einen spaßigen Abend.: We had a fun evening.
ex: Dieses Spiel ist spaßiger als das andere.: This game is more fun than the other one.""",
        "rieseln": """rieseln [ˈʁiːzl̩n] (Verb, intransitiv): to trickle; to sift down; to fall gently
English: to trickle; to sift down; to fall gently
Persian: آرام فرو ریختن؛ به نرمی سرازیر شدن؛ چکه‌چکه جاری شدن
Penglish: aram foro rikhtan; be narmi sarazir shodan; chek-cheke jari shodan
Bedeutung: in kleinen Teilchen leise herabfallen oder in einer dünnen Strömung fließen.
Gebrauch: häufig für Schnee, Sand und Wasser; Hilfsverb sein bei Bewegung, haben bei der Bedeutung „ein rieselndes Geräusch machen“.
Synonyme: herabrieseln, herunterrieseln, leise fließen
ex: Leise rieselt der Schnee.: Snow is falling gently.
ex: Der feine Sand rieselte durch meine Finger.: The fine sand trickled through my fingers.
Präsens: es rieselt
Präteritum: es rieselte
Perfekt: der Sand ist gerieselt; das Wasser hat gerieselt
Futur I: es wird rieseln
Konjunktiv II: es würde rieseln
Konjunktiv I: es riesele""",
        "weitererzählen": """weitererzählen [ˈvaɪ̯tɐʔɛɐ̯ˌt͡sɛːlən] (Verb, trennbar): to pass on; to continue telling
English: to pass on (a story); to continue telling
Persian: برای دیگران تعریف کردن؛ نقل کردن؛ ادامه دادن روایت
Penglish: baraye digaran tarif kardan; naghl kardan; edameh dadane revayat
Bedeutung: 1. etwas Gehörtes anderen erzählen. 2. nach einer Unterbrechung mit dem Erzählen fortfahren.
Rektion: etwas [Akk.] + jemandem [Dat.]
Rektion 2: etwas [Akk.]
Synonyme: weitersagen, weitererichten, fortfahren zu erzählen
ex: Bitte erzähl das Geheimnis nicht weiter!: Please don't pass on the secret!
ex: Nach der Pause erzählte sie ihre Geschichte weiter.: After the break, she continued telling her story.
Präsens: ich erzähle weiter
Präteritum: ich erzählte weiter
Perfekt: ich habe weitererzählt
Futur I: ich werde weitererzählen
Konjunktiv II: ich würde weitererzählen
Konjunktiv I: ich erzähle weiter""",
        "telefonieren": """telefonieren [teləfoˈniːʁən] (Verb, intransitiv): to phone; to talk on the phone
English: to phone; to talk on the phone
Persian: تلفن زدن؛ تلفنی صحبت کردن
Penglish: telefon zadan; telefoni sohbat kardan
Bedeutung: über ein Telefon mit jemandem sprechen.
Rektion: mit jemandem [Dat.] telefonieren
Gebrauch: Auch „jemandem telefonieren“ ist regional, besonders in der Schweiz, üblich.
Synonyme: anrufen, ein Telefongespräch führen
ex: Ich telefoniere gerade mit meiner Schwester.: I'm talking on the phone with my sister.
ex: Können wir morgen telefonieren?: Can we talk on the phone tomorrow?
Präsens: ich telefoniere
Präteritum: ich telefonierte
Perfekt: ich habe telefoniert
Futur I: ich werde telefonieren
Konjunktiv II: ich würde telefonieren
Konjunktiv I: ich telefoniere""",
        "auslachen": """auslachen [ˈaʊ̯sˌlaxn̩] (Verb, trennbar, transitiv): to laugh at; to mock
English: to laugh at; to mock
Persian: کسی را مسخره کردن؛ به کسی خندیدن
Penglish: kasi ra maskhareh kardan; be kasi khandidan
Bedeutung: 1. jemanden durch Lachen verspotten. 2. (selten) zu Ende lachen, aufhören zu lachen.
Rektion: jemanden [Akk.]
Synonyme: verspotten, verhöhnen, verlachen
ex: Die anderen Kinder lachten ihn wegen seines Akzents aus.: The other children laughed at him because of his accent.
ex: Niemand sollte wegen eines Fehlers ausgelacht werden.: No one should be mocked for making a mistake.
Präsens: ich lache aus
Präteritum: ich lachte aus
Perfekt: ich habe ausgelacht
Futur I: ich werde auslachen
Konjunktiv II: ich würde auslachen
Konjunktiv I: ich lache aus""",
        "zurückwollen": """zurückwollen [t͡suˈʁʏkˌvɔlən] (Verb, trennbar): to want to go back; to want back
English: to want to go back; to want something back
Persian: خواستن که برگردد؛ چیزی را پس خواستن
Penglish: khastan ke bargardad; chizi ra pas khastan
Bedeutung: 1. an einen früheren Ort zurückkehren wollen. 2. etwas wiederhaben wollen.
Rektion: etwas [Akk.] zurückwollen (im Sinn von zurückhaben wollen)
Synonyme: zurückkehren wollen, zurückhaben wollen
ex: Nach einer Stunde wollte sie wieder nach Hause zurück.: After an hour, she wanted to go back home.
ex: Ich will mein Buch zurück!: I want my book back!
Präsens: ich will zurück
Präteritum: ich wollte zurück
Perfekt: ich habe zurückgewollt
Futur I: ich werde zurückwollen
Konjunktiv II: ich würde zurückwollen
Konjunktiv I: ich wolle zurück""",
        "geraten": """geraten [ɡəˈʁaːtn̩] (Verb, intransitiv): to get into; to end up; to turn out
English: to get into; to end up; to turn out
Persian: در موقعیتی قرار گرفتن؛ به جایی افتادن؛ از آب درآمدن
Penglish: dar mogheiyati gharar gereftan; be jaei oftadan; az ab dar amadan
Bedeutung: 1. unbeabsichtigt in eine Situation oder an einen Ort gelangen. 2. sich auf bestimmte Weise entwickeln oder gelingen.
Rektion: in etwas [Akk.] geraten
Gebrauch: in Schwierigkeiten geraten; außer Kontrolle geraten; gut/schlecht geraten
Synonyme: hineingeraten, gelangen, werden, gelingen
ex: Er geriet in Schwierigkeiten.: He got into trouble.
ex: Der Kuchen ist gut geraten.: The cake turned out well.
Präsens: ich gerate
Präteritum: ich geriet
Perfekt: ich bin geraten
Futur I: ich werde geraten
Konjunktiv II: ich würde geraten
Konjunktiv I: ich gerate""",
        "verladen": """verladen [fɛɐ̯ˈlaːdn̩] (Verb, transitiv): to load; to trick (colloquial)
English: to load; to trick (colloquial)
Persian: بار زدن؛ بارگیری کردن؛ گول زدن (عامیانه)
Penglish: bar zadan; bargiri kardan; gool zadan (amiyaneh)
Bedeutung: 1. Güter oder Tiere auf ein Transportmittel laden. 2. (umgangssprachlich) jemanden täuschen.
Rektion: jemanden/etwas [Akk.]
Synonyme: aufladen, einladen, betrügen
ex: Die Arbeiter verladen die Möbel auf den Lkw.: The workers load the furniture onto the truck.
ex: Der Händler hat mich ganz schön verladen.: The dealer really tricked me.
Präsens: ich verlade
Präteritum: ich verlud
Perfekt: ich habe verladen
Futur I: ich werde verladen
Konjunktiv II: ich würde verladen
Konjunktiv I: ich verlade""",
        "abrichten": """abrichten [ˈapˌʁɪçtn̩] (Verb, trennbar, transitiv): to train; to condition
English: to train (an animal); to condition
Persian: تربیت کردن (حیوان)؛ شرطی کردن
Penglish: tarbiat kardan (heyvan); sharti kardan
Bedeutung: einem Tier durch wiederholtes Training bestimmtes Verhalten beibringen; übertragen: jemanden zum mechanischen Gehorsam erziehen.
Rektion: jemanden/etwas [Akk.] auf etwas [Akk.] abrichten
Synonyme: dressieren, trainieren, konditionieren
ex: Sie richtet den Hund darauf ab, auf Kommando zu sitzen.: She trains the dog to sit on command.
ex: Der Hund wurde zum Aufspüren von Drogen abgerichtet.: The dog was trained to detect drugs.
Präsens: ich richte ab
Präteritum: ich richtete ab
Perfekt: ich habe abgerichtet
Futur I: ich werde abrichten
Konjunktiv II: ich würde abrichten
Konjunktiv I: ich richte ab""",
        "zusammengehören": """zusammengehören [t͡suˈzamənɡəˌhøːʁən] (Verb, trennbar, intransitiv): to belong together
English: to belong together
Persian: به هم تعلق داشتن؛ متعلق به یک مجموعه بودن
Penglish: be ham taallogh dashtan; motaallegh be yek majmooeh boodan
Bedeutung: in einem engen Zusammenhang stehen oder gemeinsam eine Einheit bilden.
Synonyme: zusammenpassen, verbunden sein
ex: Diese beiden Teile gehören zusammen.: These two parts belong together.
ex: Die beiden Freunde gehören einfach zusammen.: The two friends simply belong together.
Präsens: wir gehören zusammen
Präteritum: wir gehörten zusammen
Perfekt: wir haben zusammengehört
Futur I: wir werden zusammengehören
Konjunktiv II: wir würden zusammengehören
Konjunktiv I: wir gehören zusammen""",
        "inwieweit": """inwieweit [ɪnˈviːvaɪ̯t] (Interrogativadverb): to what extent; to what degree
English: to what extent; to what degree
Persian: تا چه حد؛ تا چه اندازه
Penglish: ta che had; ta che andazeh
Bedeutung: fragt nach Grad oder Ausmaß einer Sache.
Gebrauch: in direkten und indirekten Fragen; nicht flektierbar.
Synonyme: in welchem Maße, bis zu welchem Grad
ex: Inwieweit bist du damit einverstanden?: To what extent do you agree with that?
ex: Ich weiß nicht, inwieweit das möglich ist.: I don't know to what extent that is possible.""",
        "Regen": """der Regen [ˈʁeːɡn̩]: rain
English: rain
Persian: باران
Penglish: baran
Bedeutung: Niederschlag in Form von Wassertropfen.
Genitiv: des Regens
Plural: kein Plural (gewöhnlich)
Kollokation: starker Regen; im Regen stehen; der Regen lässt nach
Synonyme: Niederschlag
ex: Der Regen hört langsam auf.: The rain is gradually stopping.
ex: Trotz des Regens fahren wir mit dem Fahrrad.: Despite the rain, we are cycling.""",
        "der Kommentar": """der Kommentar [kɔmɛnˈtaːɐ̯]: comment; commentary; annotation
English: comment; commentary; annotation
Persian: نظر؛ توضیح؛ یادداشت تفسیری
Penglish: nazar; tozih; yaddasht-e tafsiri
Bedeutung: 1. Anmerkung oder bewertende Stellungnahme. 2. erläuternder Text, etwa in einem Programm oder Fachbuch.
Genitiv: des Kommentars
Plural: die Kommentare
Kollokation: einen Kommentar schreiben; einen Kommentar hinterlassen; einen Kommentar im Quellcode hinzufügen
Synonyme: Anmerkung, Stellungnahme, Erläuterung
ex: Sie hat einen Kommentar zu meinem Artikel geschrieben.: She wrote a comment on my article.
ex: Die Kommentare im Code erklären die Funktion.: The comments in the code explain the function.""",
        "der Gehorsam": """der Gehorsam [ɡeˈhoːɐ̯zaːm]: obedience; compliance
English: obedience; compliance
Persian: اطاعت؛ فرمان‌برداری
Penglish: etaat; farman-bardari
Bedeutung: das Befolgen von Anweisungen oder Befehlen einer Autorität.
Genitiv: des Gehorsams
Plural: kein Plural
Kollokation: blinder Gehorsam; bedingungsloser Gehorsam; Gehorsam verlangen
Synonyme: Folgsamkeit, Fügsamkeit
ex: Blinder Gehorsam kann gefährlich sein.: Blind obedience can be dangerous.
ex: Der Offizier verlangt Gehorsam von seinen Soldaten.: The officer demands obedience from his soldiers.""",
        "sich etwas bewusst sein": """sich etwas bewusst sein (Verb, reflexiv mit Dat.; häufig Genitiv): to be aware of something; to realize
English: to be aware of something; to realize
Persian: از چیزی آگاه بودن؛ به چیزی واقف بودن
Penglish: az chizi agah boodan; be chizi vaghef boodan
Bedeutung: etwas klar erkennen oder wissen.
Rektion: sich [Dat.] + einer Sache [Gen.] bewusst sein
Rektion 2: sich [Dat.] + bewusst sein, dass ...
Gebrauch: Ich bin mir dessen bewusst; ich bin mir bewusst, dass ...; seltenere Form „sich etwas [Akk.] bewusst machen“ gehört zum Verb „bewusst machen“.
Synonyme: wissen, erkennen, sich im Klaren sein
ex: Ich bin mir des Problems bewusst.: I am aware of the problem.
ex: Sie ist sich bewusst, dass die Entscheidung Folgen hat.: She realizes that the decision has consequences.
Präsens: ich bin mir bewusst
Präteritum: ich war mir bewusst
Perfekt: ich bin mir bewusst gewesen
Futur I: ich werde mir bewusst sein
Konjunktiv II: ich wäre mir bewusst
Konjunktiv I: ich sei mir bewusst""",
        "zu einem Ergebnis kommen": """zu einem Ergebnis kommen (Redewendung): to reach a conclusion; to arrive at a result
English: to reach a conclusion; to arrive at a result
Persian: به نتیجه رسیدن؛ نتیجه گرفتن
Penglish: be natijeh residan; natijeh gereftan
Bedeutung: nach Prüfung oder Beratung ein Resultat erreichen.
Gebrauch: zu einem Ergebnis kommen; zu keinem Ergebnis kommen
Synonyme: ein Ergebnis erzielen, zu einer Schlussfolgerung gelangen
ex: Nach langer Diskussion sind wir zu einem Ergebnis gekommen.: After a long discussion, we reached a conclusion.
ex: Die Untersuchung kam zu keinem eindeutigen Ergebnis.: The investigation did not yield a clear result.""",
        "die Teekanne": """die Teekanne [ˈteːˌkanə]: teapot
English: teapot
Persian: قوری
Penglish: ghoori
Bedeutung: Gefäß zum Aufbrühen oder Servieren von Tee.
Genitiv: der Teekanne
Plural: die Teekannen
Kollokation: eine Teekanne füllen; Tee in einer Teekanne zubereiten
Synonyme: Teekrug
ex: Die Teekanne steht auf dem Tisch.: The teapot is on the table.
ex: Sie gießt heißes Wasser in die Teekanne.: She pours hot water into the teapot.""",
        "das Tagebuch": """das Tagebuch [ˈtaːɡəˌbuːx]: diary; personal journal
English: diary; personal journal
Persian: دفتر خاطرات؛ یادداشت‌های روزانه
Penglish: daftar-e khaterat; yaddasht-haye roozaneh
Bedeutung: Buch oder Datei, in dem oder der man persönliche Erlebnisse regelmäßig festhält.
Genitiv: des Tagebuchs
Plural: die Tagebücher
Kollokation: ein Tagebuch führen; in ein Tagebuch schreiben
Synonyme: persönliches Journal
ex: Ich schreibe jeden Abend in mein Tagebuch.: I write in my diary every evening.
ex: Sie hat ein altes Tagebuch aus ihrer Jugend gefunden.: She found an old diary from her youth.""",
        "kleinste": """kleinste [ˈklaɪ̯nstə] (Adjektiv, flektierte Superlativform von klein): smallest; least
English: smallest; least
Persian: کوچک‌ترین؛ کمترین
Penglish: koochak-tarin; kamtarin
Bedeutung: flektierte Form des Superlativs von klein; bezeichnet die geringste Größe oder Menge.
Gebrauch: die kleinste Zahl; das kleinste Kind; der kleinste Fehler
Synonyme: geringste, minimalste (umgangssprachlich)
ex: Das ist das kleinste Zimmer im Haus.: This is the smallest room in the house.
ex: Selbst der kleinste Fehler kann wichtig sein.: Even the smallest mistake can be important.""",
        "folgsam": """folgsam [ˈfɔlkzaːm] (Adjektiv, Komparativ: folgsamer, Superlativ: am folgsamsten): obedient; compliant; docile
English: obedient; compliant; docile
Persian: مطیع؛ فرمان‌بردار؛ حرف‌گوش‌کن
Penglish: motie; farman-bardar; harf-goosh-kon
Bedeutung: bereit, Anweisungen oder Wünsche anderer zu befolgen.
Synonyme: gehorsam, fügsam, brav
Attributiv und prädikativ verwendbar
ex: Der Hund ist sehr folgsam.: The dog is very obedient.
ex: Das folgsame Kind hört auf seine Eltern.: The obedient child listens to its parents.""",
        "ausholen": """ausholen [ˈaʊ̯sˌhoːlən] (Verb, trennbar, intransitiv): to draw back; to wind up; to elaborate
English: to draw back (for a strike); to wind up; to elaborate
Persian: دست را برای ضربه عقب بردن؛ مفصل توضیح دادن
Penglish: dast ra baraye zarbe aghab bordan; mofassal tozih dadan
Bedeutung: 1. Arm oder Bein zum Schlagen, Werfen oder Treten zurückbewegen. 2. beim Erzählen weit ins Detail gehen.
Rektion: zu etwas [Dat.] ausholen
Gebrauch: zu einem Schlag ausholen; weit ausholen
Synonyme: zurückschwingen, ausführlich erklären
ex: Er holte aus und schlug gegen die Tür.: He drew his arm back and struck the door.
ex: Bevor sie die Frage beantwortete, holte sie weit aus.: Before answering the question, she went into a long explanation.
Präsens: ich hole aus
Präteritum: ich holte aus
Perfekt: ich habe ausgeholt
Futur I: ich werde ausholen
Konjunktiv II: ich würde ausholen
Konjunktiv I: ich hole aus""",
        "besonders": """besonders [bəˈzɔndɐs] (Adverb): especially; particularly
English: especially; particularly
Persian: به‌ویژه؛ خصوصاً؛ به‌طور خاص
Penglish: be vizheh; khosoosan; be tor-e khas
Bedeutung: in besonderem Maße; mehr als gewöhnlich; vor allem.
Gebrauch: adverbiale Verwendung; nicht flektierbar; für „special“ als Adjektiv: besonders → besonderer, besondere, besonderes.
Synonyme: insbesondere, vor allem, speziell
ex: Ich finde dieses Buch besonders interessant.: I find this book particularly interesting.
ex: Besonders im Winter ist es hier sehr kalt.: It is very cold here, especially in winter.""",
    }

    # Older import created the same nouns with an incorrect "verb" role.
    # Verified the correctly classified noun exists independently.
    DUPLICATE_HEADWORDS = frozenset({"das", "Mittagessen", "Abendessen", "Eltern"})

    # Field-level repairs where the old importer copied inflection metadata
    # into Persian and Penglish instead of the actual translation.
    FIELD_REPAIRS = {
        "falsch": ("غلط؛ نادرست؛ اشتباه", "ghalat; nadorost; eshtebah"),
        "fällig": ("سررسیدشده؛ موعدش رسیده؛ قابل پرداخت", "sarresid-shodeh; moedes resideh; ghabel-e pardakht"),
        "hoch": ("بلند؛ مرتفع؛ بالا", "boland; mortafe; bala"),
        "störend": ("آزاردهنده؛ مزاحم", "azar-dahandeh; mozahem"),
        "übertrieben": ("اغراق‌آمیز؛ بیش از حد", "eghragh-amiz; bish az had"),
        "böse": ("شرور؛ بدجنس؛ عصبانی", "sharoor; badjens; asabani"),
        "sorgfältig": ("دقیق؛ با دقت؛ موشکافانه", "daghigh; ba deghat; mooshkafaneh"),
        "gründlich": ("کامل؛ دقیق؛ به‌طور کامل", "kamel; daghigh; be tor-e kamel"),
        "pünktlich": ("وقت‌شناس؛ به‌موقع", "vaght-shenas; be moghe"),
        "nützlich": ("مفید؛ سودمند", "mofid; soodmand"),
        "lächerlich": ("مضحک؛ مسخره؛ خنده‌دار", "mozhak; maskhareh; khandedar"),
        "fern": ("دور؛ دوردست", "door; doordast"),
        "weit": ("دور؛ وسیع؛ گسترده", "door; vasie; gostardeh"),
        "blass": ("رنگ‌پریده؛ کم‌رنگ", "rang-parideh; kamrang"),
        "besonders": ("به‌ویژه؛ خصوصاً؛ به‌طور خاص", "be vizheh; khosoosan; be tor-e khas"),
        "banal": ("پیش‌پاافتاده؛ مبتذل؛ معمولی", "pish-pa-oftadeh; mobtazal; mamooli"),
        "original": ("اصلی؛ اصیل", "asli; asil"),
        "leicht": ("سبک؛ آسان", "sabok; asan"),
        "rostig": ("زنگ‌زده", "zang-zadeh"),
        "kritisch": ("انتقادی؛ بحرانی؛ حساس", "enteghadi; bohrani; hassas"),
        "rational": ("منطقی؛ عقلانی", "manteghi; aghlani"),
        "problematisch": ("مشکل‌ساز؛ مسئله‌دار", "moshkel-saz; masaleh-dar"),
        "tot": ("مرده؛ بی‌جان", "mordeh; bijan"),
        "technisch": ("فنی؛ تکنیکی", "fani; tekniki"),
        "ernst": ("جدی", "jeddi"),
        "neugierig": ("کنجکاو", "konjkav"),
        "verantwortlich": ("مسئول؛ پاسخ‌گو", "masool; pasokhgoo"),
        "restriktiv": ("محدودکننده؛ سخت‌گیرانه", "mahdood-konandeh; sakht-giraneh"),
        "unwohl": ("ناخوش؛ ناراحت؛ معذب", "nakhosh; narahat; moazzab"),
        "formell": ("رسمی", "rasmi"),
        "sinnvoll": ("معنادار؛ مفید؛ معقول", "manadar; mofid; maghool"),
        "teuer": ("گران", "geran"),
        "selbstbewusst": ("بااعتمادبه‌نفس", "ba etemad be nafs"),
        "unverzichtbar": ("ضروری؛ غیرقابل چشم‌پوشی", "zaroori; gheyr-e ghabel-e cheshm-pooshi"),
        "spontan": ("خودجوش؛ بی‌مقدمه", "khodjoosh; bi-moghaddameh"),
        "aufmerksam": ("حواس‌جمع؛ باتوجه؛ دقیق", "havas-jam; ba tavajoh; daghigh"),
        "spektakulär": ("تماشایی؛ خیره‌کننده", "tamashaee; khireh-konandeh"),
        "eitel": ("خودپسند؛ مغرور؛ بیهوده", "khodpasand; maghroor; bihoodeh"),
        "selbstsicher": ("مطمئن به خود؛ بااعتمادبه‌نفس", "motmaen be khod; ba etemad be nafs"),
        "verantwortungsvoll": ("مسئولانه؛ مسئولیت‌پذیر", "masoolaneh; masooliat-pazir"),
        "dienstlich": ("کاری؛ اداری؛ مربوط به وظیفه", "kari; edari; marboot be vazifeh"),
        "grell": ("تند و زننده؛ خیره‌کننده", "tond va zanandeh; khireh-konandeh"),
        "unbehaglich": ("ناراحت؛ معذب؛ ناخوشایند", "narahat; moazzab; nakhoshayand"),
        "leblos": ("بی‌جان؛ بی‌روح", "bijan; birooh"),
        "verantwortungsbewusst": ("مسئولیت‌پذیر", "masooliat-pazir"),
        "ungläubig": ("ناباور؛ بی‌ایمان", "nabavar; bi-iman"),
        "kostspielig": ("پرهزینه؛ گران", "porhazineh; geran"),
        "umsichtig": ("دوراندیش؛ محتاط", "doorandish; mohtat"),
        "unentbehrlich": ("ضروری؛ بی‌جایگزین", "zaroori; bijaygozin"),
        "unerlässlich": ("ضروری؛ اجتناب‌ناپذیر", "zaroori; ejtenab-napazir"),
        "gehässig": ("کینه‌توز؛ بدخواه", "kineh-tooz; badkhah"),
        "fettarm": ("کم‌چرب", "kam-charb"),
        "ausholen": ("دست را برای ضربه عقب بردن؛ مفصل توضیح دادن", "dast ra baraye zarbe aghab bordan; mofassal tozih dadan"),
        "sorgsam": ("مراقب؛ بادقت", "moragheb; ba deghat"),
        "unwahr": ("خلاف واقع؛ نادرست", "khelaf-e vaghe; nadorost"),
        "kurios": ("عجیب؛ غریب؛ غیرمعمول", "ajib; gharib; gheyr-e mamool"),
        "fahl": ("رنگ‌پریده؛ بی‌روح؛ کم‌رنگ", "rang-parideh; birooh; kamrang"),
        "exzessiv": ("افراطی؛ بیش از حد", "efrati; bish az had"),
        "achtsam": ("باتوجه؛ مراقب؛ هوشیار", "ba tavajoh; moragheb; hooshyar"),
        "förderlich": ("سودمند؛ کمک‌کننده", "soodmand; komak-konandeh"),
        "ernstlich": ("جدی؛ به‌طور جدی", "jeddi; be tor-e jeddi"),
    }

    ENGLISH_REPAIRS = {
        "besonders": "especially; particularly",
        "dienstlich": "official; work-related",
        "unerlässlich": "essential; indispensable",
        "ernstlich": "serious; earnest",
        "fahl": "pale; sallow; wan",
        "kurios": "strange; odd; curious",
        "tot": "dead; lifeless",
    }

    PERFECT_REPAIRS = {
        "hinfliegen": "ich bin hingeflogen",
        "abstumpfen": "ich bin abgestumpft; ich habe etwas abgestumpft",
        "vernarren": "ich habe mich vernarrt",
    }

    EXAMPLE_REPAIRS = {
        "die Haut": (
            "Die Haut schützt unseren Körper.: The skin protects our body.",
            "Die Haut an den Händen ist trocken.: The skin on my hands is dry."),
        "eingeben": (
            "Gib bitte dein Passwort ein.: Please enter your password.",
            "Sie gibt ihre Adresse in das Formular ein.: She enters her address in the form."),
        "rechten": (
            "Die beiden Parteien rechten um das Erbe.: The two parties are disputing the inheritance.",
            "Sie haben jahrelang miteinander gerechtet.: They argued with each other for years."),
        "das Amt": (
            "Er hat ein öffentliches Amt übernommen.: He took on a public office.",
            "Sie tritt ihr Amt im Herbst an.: She takes office in the autumn."),
        "die Portion": (
            "Ich nehme eine kleine Portion Reis.: I'll have a small portion of rice.",
            "Die Portion ist für mich zu groß.: The portion is too large for me."),
        "verständlich": (
            "Ihre Sorge ist verständlich.: Her concern is understandable.",
            "Kannst du das bitte verständlich erklären?: Could you explain that clearly?"),
        "blamieren": (
            "Er hat sich vor allen Kollegen blamiert.: He embarrassed himself in front of all his colleagues.",
            "Ich möchte mich bei der Präsentation nicht blamieren.: I don't want to embarrass myself during the presentation."),
        "komischerweise": (
            "Komischerweise hat niemand etwas bemerkt.: Strangely enough, nobody noticed anything.",
            "Komischerweise kam er diesmal pünktlich.: Oddly enough, he arrived on time this time."),
        "routinemäßig": (
            "Die Geräte werden routinemäßig überprüft.: The devices are checked routinely.",
            "Wir kontrollieren routinemäßig alle Messwerte.: We routinely check all measurements."),
        "fairerweise": (
            "Fairerweise muss ich sagen, dass sie recht hatte.: To be fair, I must say that she was right.",
            "Fairerweise sollte man beide Seiten anhören.: To be fair, one should hear both sides."),
    }

    def normalize(self, raw: str, headword: str | None = None) -> tuple[str, tuple[str, ...]]:
        raw = raw.strip()
        if headword in self.CURATED:
            replacement = self.CURATED[headword]
            if raw != replacement:
                return replacement, ("curated",)
            return raw, ()
        repaired, count = self._BAD_AUXILIARY.subn(
            lambda m: m.group(1) + ("ich habe" if m.group(2) == "haben" else "ich bin"),
            raw,
        )
        reasons = ["perfect_auxiliary"] if count else []
        if headword in self.PERFECT_REPAIRS:
            expected = "Perfekt: " + self.PERFECT_REPAIRS[headword]
            updated = re.sub(r"(?m)^Perfekt:.*$", lambda m: expected, repaired)
            if updated != repaired:
                repaired = updated
                reasons.append("curated_perfect")
        if headword in ("selbständig", "fanatisch") and "}}" in repaired:
            repaired = repaired.replace("}}", "")
            if headword == "selbständig":
                repaired = repaired.replace("indepndent", "independent")
            reasons.append("malformed_grammar")
        if headword in self.EXAMPLE_REPAIRS and "{{" in repaired:
            keep = [line for line in repaired.splitlines() if not line.startswith("ex:")]
            keep.extend("ex: " + ex for ex in self.EXAMPLE_REPAIRS[headword])
            repaired = "\n".join(keep)
            reasons.append("malformed_examples")
        if headword in self.FIELD_REPAIRS:
            persian, penglish = self.FIELD_REPAIRS[headword]
            lines = repaired.splitlines()
            for index, line in enumerate(lines):
                if line.startswith("Persian:"):
                    lines[index] = "Persian: " + persian
                elif line.startswith("Penglish:"):
                    lines[index] = "Penglish: " + penglish
                elif headword == "fällig" and line.startswith("English:"):
                    lines[index] = "English: due; payable"
                elif headword == "fällig" and line.endswith(": due; payable; overdue"):
                    lines[index] = line.replace(": due; payable; overdue", ": due; payable")
                elif headword in self.ENGLISH_REPAIRS and line.startswith("English:"):
                    lines[index] = "English: " + self.ENGLISH_REPAIRS[headword]
                elif headword in self.ENGLISH_REPAIRS and index == 0 and ": " in line:
                    lines[index] = line.rsplit(": ", 1)[0] + ": " + self.ENGLISH_REPAIRS[headword]
                    if headword == "besonders":
                        lines[index] = lines[index].replace("(Adjektiv)", "(Adverb)")
                    elif headword == "tot":
                        lines[index] = re.sub(r"\(Adjektiv, Komparativ:.*?\)", "(Adjektiv, nicht steigerbar)", lines[index])
                elif "verwpersendbar" in line:
                    lines[index] = line.replace("verwpersendbar", "verwendbar")
            field_repaired = "\n".join(lines)
            if field_repaired != repaired:
                repaired = field_repaired
                reasons.append("translation_fields")
        return repaired, tuple(reasons)

    def issues(self, raw: str, role: str) -> tuple[str, ...]:
        problems = []
        if self._BAD_PERFECT.search(raw):
            problems.append("perfect_auxiliary")
        if role == "verb" and self._BAD_PERSIAN_VERB.search(raw):
            problems.append("persian_infinitive")
        if role == "unknown":
            problems.append("unknown_part_of_speech")
        if re.search(r"(?m)^(?:English|Persian|Penglish):.*(?:Superlativ:|Komparativ:)", raw):
            problems.append("grammar_in_translation")
        if re.search(r"(?m)^(?:English|Persian|Penglish):.*\bex:\s", raw):
            problems.append("examples_in_translation_field")
        if sum(line.startswith("ex:") for line in raw.splitlines()) < 2:
            problems.append("too_few_examples")
        return tuple(problems)
