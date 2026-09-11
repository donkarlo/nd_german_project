package com.ndgerman.android.grammar

import android.content.Context
import com.ndgerman.android.data.DictionaryEntry
import org.yaml.snakeyaml.Yaml
import java.util.Locale

object GrammarTables {
    val cases = listOf("Nominativ", "Akkusativ", "Dativ", "Genitiv")
    val genders = listOf("Maskulin", "Feminin", "Neutrum", "Plural")

    val articles: LinkedHashMap<String, LinkedHashMap<String, List<String>>> = linkedMapOf(
        "Bestimmter Artikel" to table(
            "Nominativ", "der", "die", "das", "die",
            "Akkusativ", "den", "die", "das", "die",
            "Dativ", "dem", "der", "dem", "den",
            "Genitiv", "des", "der", "des", "der",
        ),
        "Unbestimmter Artikel" to table(
            "Nominativ", "ein", "eine", "ein", "—",
            "Akkusativ", "einen", "eine", "ein", "—",
            "Dativ", "einem", "einer", "einem", "—",
            "Genitiv", "eines", "einer", "eines", "—",
        ),
        "Negativartikel (kein)" to table(
            "Nominativ", "kein", "keine", "kein", "keine",
            "Akkusativ", "keinen", "keine", "kein", "keine",
            "Dativ", "keinem", "keiner", "keinem", "keinen",
            "Genitiv", "keines", "keiner", "keines", "keiner",
        ),
        "dieser" to table(
            "Nominativ", "dieser", "diese", "dieses", "diese",
            "Akkusativ", "diesen", "diese", "dieses", "diese",
            "Dativ", "diesem", "dieser", "diesem", "diesen",
            "Genitiv", "dieses", "dieser", "dieses", "dieser",
        ),
        "jener" to table(
            "Nominativ", "jener", "jene", "jenes", "jene",
            "Akkusativ", "jenen", "jene", "jenes", "jene",
            "Dativ", "jenem", "jener", "jenem", "jenen",
            "Genitiv", "jenes", "jener", "jenes", "jener",
        ),
        "jeder" to table(
            "Nominativ", "jeder", "jede", "jedes", "—",
            "Akkusativ", "jeden", "jede", "jedes", "—",
            "Dativ", "jedem", "jeder", "jedem", "—",
            "Genitiv", "jedes", "jeder", "jedes", "—",
        ),
        "welcher" to table(
            "Nominativ", "welcher", "welche", "welches", "welche",
            "Akkusativ", "welchen", "welche", "welches", "welche",
            "Dativ", "welchem", "welcher", "welchem", "welchen",
            "Genitiv", "welches", "welcher", "welches", "welcher",
        ),
    )

    val persons = listOf("ich", "du", "er", "sie (Singular, feminin)", "es", "wir", "ihr", "sie (Plural)", "Sie (Höflichkeitsform)")
    val personal = linkedMapOf(
        "Nominativ" to listOf("ich", "du", "er", "sie", "es", "wir", "ihr", "sie", "Sie"),
        "Akkusativ" to listOf("mich", "dich", "ihn", "sie", "es", "uns", "euch", "sie", "Sie"),
        "Dativ" to listOf("mir", "dir", "ihm", "ihr", "ihm", "uns", "euch", "ihnen", "Ihnen"),
        "Genitiv" to listOf("meiner", "deiner", "seiner", "ihrer", "seiner", "unser", "euer", "ihrer", "Ihrer"),
    )
    val reflexive = linkedMapOf(
        "Akkusativ" to listOf("mich", "dich", "sich", "sich", "sich", "uns", "euch", "sich", "sich"),
        "Dativ" to listOf("mir", "dir", "sich", "sich", "sich", "uns", "euch", "sich", "sich"),
    )
    val possessiveStems = linkedMapOf(
        "ich" to "mein", "du" to "dein", "er" to "sein", "sie (Singular, feminin)" to "ihr", "es" to "sein",
        "wir" to "unser", "ihr" to "euer", "sie (Plural)" to "ihr", "Sie (Höflichkeitsform)" to "Ihr",
    )
    private val possessiveArticleEndings = linkedMapOf(
        "Nominativ" to listOf("", "e", "", "e"), "Akkusativ" to listOf("en", "e", "", "e"),
        "Dativ" to listOf("em", "er", "em", "en"), "Genitiv" to listOf("es", "er", "es", "er"),
    )
    private val possessivePronounEndings = linkedMapOf(
        "Nominativ" to listOf("er", "e", "es", "e"), "Akkusativ" to listOf("en", "e", "es", "e"),
        "Dativ" to listOf("em", "er", "em", "en"), "Genitiv" to listOf("es", "er", "es", "er"),
    )

    val pronounDeclensions = linkedMapOf(
        "Demonstrativpronomen: der/die/das" to table(
            "Nominativ", "der", "die", "das", "die", "Akkusativ", "den", "die", "das", "die",
            "Dativ", "dem", "der", "dem", "denen", "Genitiv", "dessen", "deren", "dessen", "deren",
        ),
        "Demonstrativpronomen: dieser" to articles.getValue("dieser"),
        "Demonstrativpronomen: jener" to articles.getValue("jener"),
        "Relativpronomen" to table(
            "Nominativ", "der", "die", "das", "die", "Akkusativ", "den", "die", "das", "die",
            "Dativ", "dem", "der", "dem", "denen", "Genitiv", "dessen", "deren", "dessen", "deren",
        ),
        "Fragepronomen: welcher" to articles.getValue("welcher"),
    )

    val adjectiveEndings = linkedMapOf(
        "Stark (ohne Artikel)" to table(
            "Nominativ", "er", "e", "es", "e", "Akkusativ", "en", "e", "es", "e",
            "Dativ", "em", "er", "em", "en", "Genitiv", "en", "er", "en", "er",
        ),
        "Schwach (der/die/das …)" to table(
            "Nominativ", "e", "e", "e", "en", "Akkusativ", "en", "e", "e", "en",
            "Dativ", "en", "en", "en", "en", "Genitiv", "en", "en", "en", "en",
        ),
        "Gemischt (ein/kein/mein …)" to table(
            "Nominativ", "er", "e", "es", "en", "Akkusativ", "en", "e", "es", "en",
            "Dativ", "en", "en", "en", "en", "Genitiv", "en", "en", "en", "en",
        ),
    )

    fun possessiveArticle(owner: String, case: String, gender: String): String = attach(
        possessiveStems.getValue(owner), possessiveArticleEndings.getValue(case)[genders.indexOf(gender)]
    )

    fun possessivePronoun(owner: String, case: String, gender: String): String {
        val stem = possessiveStems.getValue(owner)
        if ((case == "Nominativ" || case == "Akkusativ") && gender == "Neutrum" && stem.lowercase() in setOf("mein", "dein", "sein")) {
            return "${stem}s / ${stem}es"
        }
        return attach(stem, possessivePronounEndings.getValue(case)[genders.indexOf(gender)])
    }

    private fun attach(stem: String, ending: String): String {
        val s = if (stem.lowercase() == "euer" && ending.isNotEmpty()) {
            if (stem.first().isUpperCase()) "Eur" else "eur"
        } else stem
        return s + ending
    }

    private fun table(vararg values: String): LinkedHashMap<String, List<String>> {
        val out = linkedMapOf<String, List<String>>()
        var i = 0
        while (i < values.size) {
            out[values[i]] = listOf(values[i + 1], values[i + 2], values[i + 3], values[i + 4])
            i += 5
        }
        return out
    }
}

data class TenseCard(val title: String, val lines: List<String>)
data class ConjugationResult(
    val infinitive: String,
    val source: String,
    val auxiliary: String,
    val participle: String,
    val note: String,
    val sections: LinkedHashMap<String, List<TenseCard>>,
    val imperatives: List<String>,
    val participles: List<Pair<String, String>>,
    val infinitives: List<Pair<String, String>>,
)

data class AdjectiveRow(val declension: String, val case: String, val gender: String, val form: String)
data class NounRow(val case: String, val singular: String, val singularEnding: String, val plural: String, val pluralEnding: String)
data class NounResult(val base: String, val gender: String, val rows: List<NounRow>, val note: String, val source: String)

class GermanGrammar(private val context: Context) {
    private val yaml = Yaml()
    private val irregularVerbs: Map<String, Map<String, Any?>> by lazy { loadVerbData() }
    private val auxiliaryOverrides: Map<String, String> by lazy { loadAuxOverrides() }
    private val irregularAdjectiveStems: Map<String, String> by lazy { loadSimpleStringMap("irregular_adjectives.yaml") }
    private val irregularNouns: Map<String, Map<String, String>> by lazy { loadNouns() }

    fun adjectiveRows(word: String, determiner: String, requestedType: String): List<AdjectiveRow> {
        val base = word.trim()
        if (base.isBlank()) return emptyList()
        val types = if (requestedType == "Automatisch (nach Begleiter)") {
            detectAdjectiveType(determiner)?.let(::listOf) ?: GrammarTables.adjectiveEndings.keys.toList()
        } else listOf(requestedType)
        val stem = adjectiveStem(base)
        return buildList {
            types.forEach { type ->
                GrammarTables.cases.forEach { case ->
                    GrammarTables.genders.forEachIndexed { genderIndex, gender ->
                        add(AdjectiveRow(type, case, gender, stem + GrammarTables.adjectiveEndings.getValue(type).getValue(case)[genderIndex]))
                    }
                }
            }
        }
    }

    fun detectAdjectiveType(determinerText: String): String? {
        val normalized = determinerText.trim().lowercase(Locale.ROOT).replace("—", "-")
        if (normalized.isBlank() || normalized in setOf("-", "ohne", "ohne artikel", "kein artikel")) return "Stark (ohne Artikel)"
        val tokens = Regex("[a-zäöüß]+", RegexOption.IGNORE_CASE).findAll(normalized).map { it.value }.toList()
        val weak = mutableSetOf("der", "die", "das", "den", "dem", "des", "alle", "aller", "allen", "allem", "beide", "beider", "beiden", "beidem")
        listOf("dies", "jen", "jed", "welch", "solch", "manch", "jeglich").forEach { s ->
            listOf("er", "e", "es", "en", "em").forEach { weak += s + it }
        }
        val mixed = mutableSetOf<String>()
        listOf("ein", "kein", "mein", "dein", "sein", "ihr", "unser", "irgendein").forEach { s ->
            listOf("", "e", "en", "em", "er", "es").forEach { mixed += s + it }
        }
        mixed += setOf("euer", "eure", "euren", "eurem", "eurer", "eures")
        val strong = setOf("viel", "viele", "vieler", "vielen", "vielem", "vieles", "wenig", "wenige", "weniger", "wenigen", "wenigem", "weniges", "einige", "einiger", "einigen", "einigem", "einiges", "mehrere", "mehrerer", "mehreren", "etwas", "nichts", "genug")
        return when {
            tokens.any { it in weak } -> "Schwach (der/die/das …)"
            tokens.any { it in mixed } -> "Gemischt (ein/kein/mein …)"
            tokens.any { it in strong } -> "Stark (ohne Artikel)"
            else -> null
        }
    }

    private fun adjectiveStem(word: String): String {
        val clean = word.trim()
        irregularAdjectiveStems[clean.lowercase(Locale.ROOT)]?.let { replacement ->
            return if (clean.firstOrNull()?.isUpperCase() == true) replacement.replaceFirstChar { it.uppercase() } else replacement
        }
        val low = clean.lowercase(Locale.ROOT)
        return when {
            low.endsWith("el") && clean.length > 3 -> clean.dropLast(2) + "l"
            low.endsWith("er") && clean.length > 3 -> clean.dropLast(2) + "r"
            else -> clean
        }
    }

    fun declineNoun(input: String, dictionaryEntry: DictionaryEntry? = null): NounResult {
        val raw = dictionaryEntry?.raw.orEmpty()
        val (queryBase, queryGender) = nounAndGender(input)
        val (rawBase, rawGender) = if (raw.isNotBlank()) nounAndGender(raw) else "" to null
        val base = rawBase.ifBlank { queryBase }
        var gender = rawGender ?: queryGender
        val genitiveField = field(raw, "Genitiv")
        val pluralField = field(raw, "Plural")
        var genitive = stripArticle(genitiveField)
        var noPlural = pluralField.isNotBlank() && isNoPlural(pluralField)
        var plural = if (noPlural) "" else stripArticle(pluralField)
        val singular = linkedMapOf(
            "Nominativ" to base, "Akkusativ" to base, "Dativ" to base,
            "Genitiv" to if (genitive.isNotBlank()) genitive else regularGenitive(base, gender),
        )
        val sources = mutableListOf<String>()
        if (genitiveField.isNotBlank()) sources += "Genitiv aus Dictionary"
        if (pluralField.isNotBlank()) sources += "Plural aus Dictionary"
        if (looksWeakMasculine(base, gender)) {
            val oblique = if (base.lowercase().endsWith("e")) base + "n" else base + "en"
            singular["Akkusativ"] = oblique; singular["Dativ"] = oblique
            if (genitiveField.isBlank()) singular["Genitiv"] = oblique
            sources += "n-Deklination per Regel"
        }
        var pluralForms = linkedMapOf(
            "Nominativ" to plural, "Akkusativ" to plural,
            "Dativ" to dativePlural(plural), "Genitiv" to plural,
        )
        val irregular = irregularNouns[base.lowercase(Locale.ROOT)]
        if (irregular != null) {
            gender = irregular["gender"]?.takeIf { it.isNotBlank() } ?: gender
            singular["Nominativ"] = irregular["nominative_singular"] ?: singular.getValue("Nominativ")
            singular["Akkusativ"] = irregular["accusative_singular"] ?: singular.getValue("Akkusativ")
            singular["Dativ"] = irregular["dative_singular"] ?: singular.getValue("Dativ")
            singular["Genitiv"] = irregular["genitive_singular"] ?: singular.getValue("Genitiv")
            irregular["plural"]?.let { p ->
                noPlural = isNoPlural(p)
                plural = if (noPlural) "" else p
                pluralForms = linkedMapOf(
                    "Nominativ" to plural, "Akkusativ" to plural,
                    "Dativ" to (irregular["dative_plural"] ?: dativePlural(plural)), "Genitiv" to plural,
                )
            }
            sources += "irregular_nouns.yaml"
        }
        val definite = mapOf(
            "Maskulin" to mapOf("Nominativ" to "der", "Akkusativ" to "den", "Dativ" to "dem", "Genitiv" to "des"),
            "Feminin" to mapOf("Nominativ" to "die", "Akkusativ" to "die", "Dativ" to "der", "Genitiv" to "der"),
            "Neutrum" to mapOf("Nominativ" to "das", "Akkusativ" to "das", "Dativ" to "dem", "Genitiv" to "des"),
        )
        val pluralArticles = mapOf("Nominativ" to "die", "Akkusativ" to "die", "Dativ" to "den", "Genitiv" to "der")
        val rows = GrammarTables.cases.map { case ->
            val sf = singular[case].orEmpty().ifBlank { "—" }
            val pf = pluralForms[case].orEmpty().ifBlank { if (noPlural) "kein Plural" else "—" }
            val sa = definite[gender]?.get(case).orEmpty()
            val pa = if (pf != "—" && pf != "kein Plural") pluralArticles[case].orEmpty() else ""
            NounRow(case, listOf(sa, sf).filter(String::isNotBlank).joinToString(" "), ending(base, sf),
                listOf(pa, pf).filter(String::isNotBlank).joinToString(" "), if (pf in setOf("—", "kein Plural")) "—" else ending(base, pf))
        }
        return NounResult(base, gender ?: "Unbekannt", rows, irregular?.get("note").orEmpty(), sources.distinct().joinToString("; ").ifBlank { "Regelbasierte Form" })
    }

    fun conjugate(rawInput: String): ConjugationResult {
        var input = rawInput.trim().lowercase(Locale.ROOT).trimEnd('.', '!', '?', ',', ';', ':')
        var reflexive = false
        if (input.startsWith("sich ")) { reflexive = true; input = input.removePrefix("sich ").trim() }
        if (input.startsWith("zu ")) input = input.removePrefix("zu ").trim()
        require(Regex("^[a-zäöüß]+(?:eln|ern|en|n)$", RegexOption.IGNORE_CASE).matches(input)) {
            "Enter a German infinitive ending in -en or -n, for example: haben, gehen, arbeiten."
        }

        val canonical = canonicalVerb(input)
        val analysis = analyzePrefix(canonical)
        val directRecord = irregularVerbs[canonical]
        val baseRecord = if (directRecord == null && analysis.base.isNotBlank()) irregularVerbs[analysis.base] else null
        val record = directRecord ?: baseRecord
        val source = when {
            directRecord != null -> "irregular_verbs.yaml"
            baseRecord != null -> "Inherited from ${analysis.base}"
            else -> "Regular-rule engine"
        }

        val usePrefixInheritance = directRecord == null && analysis.prefix.isNotBlank()
        val finiteInfinitive = if (usePrefixInheritance) analysis.base else canonical
        var present = record?.list("present") ?: regularPresent(finiteInfinitive)
        if (record?.string("present_du") != null) present = present.toMutableList().also { it[1] = record.string("present_du")!! }
        if (record?.string("present_er") != null) present = present.toMutableList().also { it[2] = record.string("present_er")!! }
        var preterite = record?.list("preterite") ?: record?.string("preterite_ich")?.let(::strongPreterite) ?: regularPreterite(finiteInfinitive)
        var k1 = record?.list("konjunktiv_i") ?: regularK1(finiteInfinitive)
        var k2 = record?.list("konjunktiv_ii") ?: record?.string("konjunktiv_ii_ich")?.let(::konjunktivFromFirst)
            ?: record?.string("preterite_ich")?.let(::konjunktivFromFirst) ?: regularK2(finiteInfinitive)

        if (usePrefixInheritance) {
            present = applyPrefix(present, analysis)
            preterite = applyPrefix(preterite, analysis)
            k1 = applyPrefix(k1, analysis)
            k2 = applyPrefix(k2, analysis)
        }

        val participle = when {
            directRecord != null -> directRecord.string("participle") ?: regularParticiple(canonical)
            baseRecord != null -> applyPrefixToParticiple(baseRecord.string("participle") ?: regularParticiple(analysis.base), analysis)
            else -> regularParticiple(canonical)
        }
        val auxiliary = directRecord?.string("auxiliary") ?: baseRecord?.string("auxiliary") ?: auxiliaryOverrides[canonical]
            ?: auxiliaryOverrides[analysis.base] ?: inferAuxiliary(canonical)
        val note = record?.string("note").orEmpty()
        val infinitivePhrase = if (reflexive) "sich $canonical" else canonical

        val indicative = listOf(
            TenseCard("Präsens", simpleLines(present, reflexive)),
            TenseCard("Präteritum", simpleLines(preterite, reflexive)),
            TenseCard("Futur I", compoundLines(werdenPresent, infinitivePhrase, reflexive)),
            TenseCard("Perfekt", compoundLines(auxPresent.getValue(auxiliary), participle, reflexive)),
            TenseCard("Plusquamperfekt", compoundLines(auxPreterite.getValue(auxiliary), participle, reflexive)),
            TenseCard("Futur II", compoundLines(werdenPresent, "$participle $auxiliary", reflexive)),
        )
        val conjI = listOf(
            TenseCard("Präsens", simpleLines(k1, reflexive)),
            TenseCard("Futur I", compoundLines(werdenK1, infinitivePhrase, reflexive)),
            TenseCard("Perfekt", compoundLines(auxK1.getValue(auxiliary), participle, reflexive)),
        )
        val conjII = listOf(
            TenseCard("Präteritum", simpleLines(k2, reflexive)),
            TenseCard("Futur I", compoundLines(werdenK2, infinitivePhrase, reflexive)),
            TenseCard("Plusquamperfekt", compoundLines(auxK2.getValue(auxiliary), participle, reflexive)),
            TenseCard("Futur II", compoundLines(werdenK2, "$participle $auxiliary", reflexive)),
        )
        val sections = linkedMapOf("INDIKATIV" to indicative, "KONJUNKTIV I" to conjI, "KONJUNKTIV II" to conjII)
        if (!reflexive) sections["PASSIV (VORGANGSPASSIV · falls möglich)"] = passiveCards(participle)

        val baseImperativeDu = record?.string("imperative_du") ?: regularImperativeDu(finiteInfinitive)
        val baseImperativeIhr = record?.string("imperative_ihr") ?: regularPresent(finiteInfinitive)[4]
        val imperativeDuBase = if (usePrefixInheritance) applyImperativePrefix(baseImperativeDu, analysis) else baseImperativeDu
        val imperativeIhrBase = if (usePrefixInheritance) applyImperativePrefix(baseImperativeIhr, analysis) else baseImperativeIhr
        val imperatives = listOf(
            "${imperativeDuBase}${if (reflexive) " dich" else ""}!",
            "${imperativeIhrBase}${if (reflexive) " euch" else ""}!",
            "${if (reflexive) "${present[5].substringBefore(' ')} Sie sich" else "${present[5].substringBefore(' ')} Sie"}!",
        )
        return ConjugationResult(
            infinitive = infinitivePhrase,
            source = source,
            auxiliary = auxiliary,
            participle = participle,
            note = note,
            sections = sections,
            imperatives = imperatives,
            participles = listOf("Präsens" to presentParticiple(canonical), "Perfekt" to participle),
            infinitives = listOf("Präsens" to infinitivePhrase, "Perfekt" to "${if (reflexive) "sich " else ""}$participle $auxiliary"),
        )
    }

    private fun passiveCards(participle: String): List<TenseCard> {
        val agents = listOf("mir", "dir", "ihm/ihr/ihm", "uns", "euch", "Ihnen")
        fun lines(finite: List<String>, tail: String) = finite.indices.map { i -> "${finite[i]} $tail von ${agents[i]}" }
        return listOf(
            TenseCard("Präsens", lines(werdenPresent, participle)),
            TenseCard("Präteritum", lines(werdenPreterite, participle)),
            TenseCard("Perfekt", lines(auxPresent.getValue("sein"), "$participle worden")),
            TenseCard("Plusquamperfekt", lines(auxPreterite.getValue("sein"), "$participle worden")),
            TenseCard("Futur I", lines(werdenPresent, "$participle werden")),
            TenseCard("Futur II", lines(werdenPresent, "$participle worden sein")),
        )
    }

    private fun simpleLines(forms: List<String>, reflexive: Boolean): List<String> = pronouns.indices.map { i ->
        if (reflexive) "${pronouns[i]} ${forms[i]} ${reflexivePronouns[i]}" else "${pronouns[i]} ${forms[i]}"
    }
    private fun compoundLines(finite: List<String>, tail: String, reflexive: Boolean): List<String> = pronouns.indices.map { i ->
        if (reflexive) "${pronouns[i]} ${finite[i]} ${reflexivePronouns[i]} $tail" else "${pronouns[i]} ${finite[i]} $tail"
    }

    private data class Prefix(val prefix: String = "", val base: String = "", val separable: Boolean = false)
    private fun analyzePrefix(infinitive: String): Prefix {
        if (infinitive in nonSeparableExceptions) return Prefix(base = infinitive)
        separablePrefixes.firstOrNull { infinitive.startsWith(it) && infinitive.length - it.length >= 3 }?.let {
            return Prefix(it, infinitive.removePrefix(it), true)
        }
        inseparablePrefixes.firstOrNull { infinitive.startsWith(it) && infinitive.length - it.length >= 3 }?.let {
            return Prefix(it, infinitive.removePrefix(it), false)
        }
        return Prefix(base = infinitive)
    }

    private fun applyPrefix(forms: List<String>, p: Prefix): List<String> = if (p.prefix.isBlank()) forms else forms.map { form ->
        if (p.separable) "$form ${p.prefix}" else p.prefix + form
    }
    private fun applyImperativePrefix(form: String, p: Prefix): String = if (p.prefix.isBlank()) form else if (p.separable) "$form ${p.prefix}" else p.prefix + form
    private fun applyPrefixToParticiple(baseParticiple: String, p: Prefix): String = if (p.prefix.isBlank()) baseParticiple else if (p.separable) p.prefix + baseParticiple else p.prefix + baseParticiple.removePrefix("ge")

    private fun canonicalVerb(input: String): String {
        if (input in irregularVerbs) return input
        val aliases = irregularVerbs.keys.groupBy { keyboard(it) }
        aliases[keyboard(input)]?.singleOrNull()?.let { return it }
        return input
    }
    private fun keyboard(s: String) = s.lowercase(Locale.ROOT).replace("ä", "a").replace("ö", "o").replace("ü", "u").replace("ß", "ss")

    private fun regularPresent(infinitive: String): List<String> {
        val stem = stem(infinitive)
        val ich = if (infinitive.endsWith("eln") && stem.endsWith("el")) stem.dropLast(2) + "le" else stem + "e"
        val insertE = needsE(stem)
        val du = when { insertE -> stem + "est"; stem.endsWithAny("s", "ß", "x", "z", "tz") -> stem + "t"; else -> stem + "st" }
        val er = if (insertE) stem + "et" else stem + "t"
        val ihr = if (insertE) stem + "et" else stem + "t"
        return listOf(ich, du, er, infinitive, ihr, infinitive)
    }
    private fun regularPreterite(infinitive: String): List<String> {
        val s = stem(infinitive); val first = s + if (needsE(s)) "ete" else "te"
        return listOf(first, first + "st", first, first + "n", first + "t", first + "n")
    }
    private fun regularK1(infinitive: String): List<String> { val s = stem(infinitive); return listOf("e", "est", "e", "en", "et", "en").map { s + it } }
    private fun regularK2(infinitive: String) = regularPreterite(infinitive)
    private fun strongPreterite(first: String): List<String> {
        if (first.endsWith("e")) { val b = first.dropLast(1); return listOf(first, first + "st", first, b + "en", b + "et", b + "en") }
        val du = if (first.endsWithAny("d", "t", "s", "ß", "z", "x")) first + "est" else first + "st"
        val ihr = if (first.endsWithAny("d", "t")) first + "et" else first + "t"
        return listOf(first, du, first, first + "en", ihr, first + "en")
    }
    private fun konjunktivFromFirst(firstRaw: String): List<String> {
        val first = if (firstRaw.endsWith("e")) firstRaw else firstRaw + "e"; val b = first.dropLast(1)
        return listOf(first, b + "est", first, b + "en", b + "et", b + "en")
    }
    private fun regularParticiple(infinitive: String): String {
        val p = analyzePrefix(infinitive)
        val base = if (p.prefix.isNotBlank()) p.base else infinitive
        val s = stem(base)
        val end = if (needsE(s)) "et" else "t"
        return when {
            p.prefix.isBlank() -> if (inseparablePrefixes.any(base::startsWith) || base.endsWith("ieren")) s + end else "ge" + s + end
            p.separable -> p.prefix + "ge" + s + end
            else -> p.prefix + s + end
        }
    }
    private fun regularImperativeDu(infinitive: String): String {
        val s = stem(infinitive)
        return if (s.endsWith("el")) s.dropLast(1) + "le" else s
    }
    private fun presentParticiple(infinitive: String): String = when {
        infinitive.endsWith("sein") -> infinitive.removeSuffix("sein") + "seiend"
        infinitive.endsWith("tun") -> infinitive.removeSuffix("tun") + "tuend"
        else -> infinitive + "d"
    }
    private fun stem(infinitive: String) = when { infinitive.endsWith("en") -> infinitive.dropLast(2); infinitive.endsWith("n") -> infinitive.dropLast(1); else -> infinitive }
    private fun needsE(s: String) = s.endsWith("d") || s.endsWith("t") || Regex("[^aeiouäöüyrlmn][mn]$").containsMatchIn(s)
    private fun String.endsWithAny(vararg suffixes: String) = suffixes.any(::endsWith)
    private fun inferAuxiliary(infinitive: String): String = if (infinitive in setOf("gehen", "kommen", "fahren", "fliegen", "fallen", "steigen", "bleiben", "werden", "sein")) "sein" else "haben"

    @Suppress("UNCHECKED_CAST")
    private fun loadRoot(name: String): Map<Any?, Any?> = context.assets.open(name).bufferedReader().use { reader ->
        (yaml.load<Any?>(reader) as? Map<Any?, Any?>).orEmpty()
    }
    private fun loadVerbData(): Map<String, Map<String, Any?>> {
        val raw = loadRoot("irregular_verbs.yaml")["verbs"] as? Map<*, *> ?: emptyMap<Any?, Any?>()
        return raw.entries.associate { (k, v) -> k.toString().lowercase(Locale.ROOT) to ((v as? Map<*, *>)?.entries?.associate { it.key.toString() to it.value }.orEmpty()) }
    }
    private fun loadAuxOverrides(): Map<String, String> {
        val raw = loadRoot("irregular_verbs.yaml")["auxiliary_overrides"] as? Map<*, *> ?: return emptyMap()
        return raw.entries.associate { it.key.toString().lowercase(Locale.ROOT) to it.value.toString() }
    }
    private fun loadSimpleStringMap(name: String): Map<String, String> = loadRoot(name).entries.associate { it.key.toString().lowercase(Locale.ROOT) to it.value.toString().trim() }
    private fun loadNouns(): Map<String, Map<String, String>> = loadRoot("irregular_nouns.yaml").entries.associate { (k, v) ->
        k.toString().lowercase(Locale.ROOT) to ((v as? Map<*, *>)?.entries?.filter { it.value != null }?.associate { it.key.toString() to it.value.toString().trim() }.orEmpty())
    }
    private fun Map<String, Any?>.string(key: String): String? = this[key]?.toString()?.takeIf { it.isNotBlank() }
    private fun Map<String, Any?>.list(key: String): List<String>? = (this[key] as? List<*>)?.map { it.toString() }?.takeIf { it.size == 6 }

    private fun nounAndGender(text: String): Pair<String, String?> {
        var left = text.lineSequence().firstOrNull().orEmpty().trim().substringBefore(':').trim()
        left = left.replace(Regex("\\s*\\[[^]]*].*$"), "").replace(Regex("\\s*\\([^)]*\\).*$"), "").trim()
        val m = Regex("^(der|die|das|ein|eine)\\s+(.+)$", RegexOption.IGNORE_CASE).find(left) ?: return left to null
        val gender = when (m.groupValues[1].lowercase(Locale.ROOT)) { "der", "ein" -> "Maskulin"; "die", "eine" -> "Feminin"; "das" -> "Neutrum"; else -> null }
        return m.groupValues[2].trim() to gender
    }
    private fun field(raw: String, label: String): String = raw.lineSequence().drop(1).mapNotNull { line ->
        val p = line.indexOf(':'); if (p <= 0) null else line.substring(0, p).trim() to line.substring(p + 1).trim()
    }.firstOrNull { it.first.equals(label, true) }?.second.orEmpty()
    private fun stripArticle(v: String) = v.trim().replace(Regex("^(?:des|der|dem|den|die|das|ein(?:es|em|en|er|e)?|kein(?:es|em|en|er|e)?)\\s+", RegexOption.IGNORE_CASE), "").trim()
    private fun isNoPlural(v: String) = v.lowercase(Locale.ROOT).replace("—", "-") in setOf("kein plural", "keine pluralform", "kein pl.", "singular", "nur singular", "-")
    private fun regularGenitive(base: String, gender: String?): String {
        if (gender == "Feminin") return base
        val low = base.lowercase(Locale.ROOT)
        if (low.endsWithAny("s", "ß", "x", "z", "tz", "tsch")) return base + "es"
        return base + if (Regex("[aeiouyäöü]+").findAll(low).count() <= 1) "es" else "s"
    }
    private fun dativePlural(p: String) = if (p.isBlank() || p.lowercase().endsWithAny("n", "s")) p else p + "n"
    private fun looksWeakMasculine(base: String, gender: String?) = gender == "Maskulin" && base.lowercase(Locale.ROOT).endsWithAny("ant", "ent", "ist", "oge", "at", "nom", "graf", "graph", "arch", "soph", "ot")
    private fun ending(base: String, form: String): String = when {
        form.isBlank() || form == "—" || form == base -> "—"
        form.lowercase(Locale.ROOT).startsWith(base.lowercase(Locale.ROOT)) -> "-" + form.drop(base.length)
        else -> "→ $form"
    }

    companion object {
        private val pronouns = listOf("ich", "du", "er/sie/es", "wir", "ihr", "Sie")
        private val reflexivePronouns = listOf("mich", "dich", "sich", "uns", "euch", "sich")
        private val werdenPresent = listOf("werde", "wirst", "wird", "werden", "werdet", "werden")
        private val werdenPreterite = listOf("wurde", "wurdest", "wurde", "wurden", "wurdet", "wurden")
        private val werdenK1 = listOf("werde", "werdest", "werde", "werden", "werdet", "werden")
        private val werdenK2 = listOf("würde", "würdest", "würde", "würden", "würdet", "würden")
        private val auxPresent = mapOf(
            "haben" to listOf("habe", "hast", "hat", "haben", "habt", "haben"),
            "sein" to listOf("bin", "bist", "ist", "sind", "seid", "sind"),
        )
        private val auxPreterite = mapOf(
            "haben" to listOf("hatte", "hattest", "hatte", "hatten", "hattet", "hatten"),
            "sein" to listOf("war", "warst", "war", "waren", "wart", "waren"),
        )
        private val auxK1 = mapOf(
            "haben" to listOf("habe", "habest", "habe", "haben", "habet", "haben"),
            "sein" to listOf("sei", "seiest", "sei", "seien", "seiet", "seien"),
        )
        private val auxK2 = mapOf(
            "haben" to listOf("hätte", "hättest", "hätte", "hätten", "hättet", "hätten"),
            "sein" to listOf("wäre", "wärest", "wäre", "wären", "wäret", "wären"),
        )
        private val separablePrefixes = setOf("auseinander", "durcheinander", "gegenüber", "hinterher", "nebeneinander", "vorwärts", "zusammen", "zurecht", "zurück", "dazwischen", "entgegen", "entlang", "herunter", "hinunter", "voraus", "vorbei", "weiter", "wieder", "heraus", "herein", "hinaus", "hinein", "herauf", "hinauf", "herab", "hinab", "heran", "voran", "empor", "fort", "frei", "heim", "nieder", "preis", "statt", "teil", "umher", "durch", "unter", "über", "um", "ab", "an", "auf", "aus", "bei", "ein", "fest", "her", "hin", "los", "mit", "nach", "vor", "weg", "zu").sortedByDescending { it.length }
        private val inseparablePrefixes = listOf("hinter", "wider", "miss", "emp", "ent", "ver", "zer", "be", "er", "ge")
        private val nonSeparableExceptions = setOf("antworten", "arbeiten", "beobachten", "beurteilen", "hinterfragen", "durchdringen", "durchqueren", "durchschauen", "durchsuchen", "überarbeiten", "überblicken", "überfordern", "überleben", "überlegen", "übergeben", "übermitteln", "übernachten", "übernehmen", "überprüfen", "überqueren", "überraschen", "übersehen", "übersetzen", "übertragen", "übertreffen", "überwachen", "überweisen", "überzeugen", "umarmen", "umgeben", "unterbrechen", "unterdrücken", "unterhalten", "unterrichten", "unterstützen", "unterlassen", "unternehmen", "unterscheiden", "unterstehen", "untersuchen", "unterzeichnen", "unterziehen", "wiederholen", "widerlegen", "widerrufen", "widersprechen", "widerstehen")
    }
}
