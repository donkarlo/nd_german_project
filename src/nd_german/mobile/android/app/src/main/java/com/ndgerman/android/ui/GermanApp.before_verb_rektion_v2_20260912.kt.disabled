package com.ndgerman.android.ui

import android.speech.tts.TextToSpeech
import androidx.compose.foundation.background
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.ArrowForward
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Clear
import androidx.compose.material.icons.filled.Cloud
import androidx.compose.material.icons.filled.CloudOff
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Sync
import androidx.compose.material.icons.filled.VolumeUp
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExtendedFloatingActionButton
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.FilterChip
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedCard
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.ndgerman.android.data.DictionaryEntry
import com.ndgerman.android.grammar.AdjectiveRow
import com.ndgerman.android.grammar.GrammarTables
import com.ndgerman.android.grammar.NounResult
import com.ndgerman.android.grammar.TenseCard
import java.util.Locale

private data class AppTab(val title: String, val short: String)
private val tabs = listOf(
    AppTab("Dictionary", "Wörter"),
    AppTab("Conjugation", "Verben"),
    AppTab("Artikel", "Artikel"),
    AppTab("Pronomen", "Pronomen"),
    AppTab("Adjektivendungen", "Adjektiv"),
    AppTab("Nomenendungen", "Nomen"),
)

@Composable
fun GermanApp(viewModel: GermanViewModel) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val context = LocalContext.current
    var selectedTab by remember { mutableStateOf(0) }
    var adjectivePrefill by remember { mutableStateOf("") }
    var syncDialog by remember { mutableStateOf(false) }
    var addDialog by remember { mutableStateOf(false) }
    var editing by remember { mutableStateOf<DictionaryEntry?>(null) }
    var deleting by remember { mutableStateOf<DictionaryEntry?>(null) }
    var discardPullConfirm by remember { mutableStateOf(false) }
    var ttsReady by remember { mutableStateOf(false) }
    val tts = remember {
        TextToSpeech(context) { status ->
            if (status == TextToSpeech.SUCCESS) ttsReady = true
        }
    }
    LaunchedEffect(ttsReady) {
        if (ttsReady) tts.language = Locale.GERMANY
    }
    DisposableEffect(Unit) { onDispose { tts.stop(); tts.shutdown() } }

    fun speak(text: String) {
        if (ttsReady) tts.speak(text, TextToSpeech.QUEUE_FLUSH, null, "nd-german-$text")
    }

    state.error?.let { error ->
        AlertDialog(
            onDismissRequest = viewModel::clearError,
            title = { Text("ND Deutsch") },
            text = { Text(error) },
            confirmButton = { TextButton(onClick = viewModel::clearError) { Text("OK") } },
        )
    }

    if (syncDialog) {
        SyncDialog(
            state = state.sync,
            configured = viewModel.dropboxConfigured,
            onDismiss = { syncDialog = false },
            onConnect = viewModel::startDropboxAuthentication,
            onPull = {
                if (state.sync.pendingLocalChanges) discardPullConfirm = true
                else viewModel.pullRemote(false)
            },
            onPush = viewModel::pushRemote,
            onDisconnect = viewModel::disconnectDropbox,
        )
    }
    if (discardPullConfirm) {
        AlertDialog(
            onDismissRequest = { discardPullConfirm = false },
            title = { Text("Discard local edits?") },
            text = { Text("Pulling now will replace the Android database with the current desktop/Dropbox database. Pending Android-only edits will be lost.") },
            confirmButton = {
                TextButton(onClick = { discardPullConfirm = false; viewModel.pullRemote(true) }) { Text("Discard & Pull") }
            },
            dismissButton = { TextButton(onClick = { discardPullConfirm = false }) { Text("Cancel") } },
        )
    }
    if (addDialog) {
        EntryEditorDialog(
            title = "Add dictionary entry",
            initial = "",
            busy = state.busy,
            onDismiss = { addDialog = false },
            onSave = { raw -> viewModel.saveEntry(null, raw) { addDialog = false } },
        )
    }
    editing?.let { entry ->
        EntryEditorDialog(
            title = "Edit ${entry.headword}",
            initial = entry.raw,
            busy = state.busy,
            onDismiss = { editing = null },
            onSave = { raw -> viewModel.saveEntry(entry.index, raw) { editing = null } },
        )
    }
    deleting?.let { entry ->
        AlertDialog(
            onDismissRequest = { deleting = null },
            title = { Text("Delete ${entry.headword}?") },
            text = { Text("This removes the entry from the shared SQLite dictionary. If Dropbox is connected, the change is synced to the desktop database too.") },
            confirmButton = {
                TextButton(onClick = { viewModel.deleteEntry(entry.index) { deleting = null } }) { Text("Delete") }
            },
            dismissButton = { TextButton(onClick = { deleting = null }) { Text("Cancel") } },
        )
    }

    Scaffold(
        topBar = {
            Column {
                Surface(tonalElevation = 2.dp) {
                    Row(
                        Modifier.fillMaxWidth().padding(horizontal = 14.dp, vertical = 8.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Surface(shape = RoundedCornerShape(12.dp), color = MaterialTheme.colorScheme.primaryContainer) {
                            Text("DE", modifier = Modifier.padding(horizontal = 10.dp, vertical = 7.dp), fontWeight = FontWeight.Black, color = MaterialTheme.colorScheme.onPrimaryContainer)
                        }
                        Spacer(Modifier.width(10.dp))
                        Column(Modifier.weight(1f)) {
                            Text("ND Deutsch", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                            Text(
                                if (state.ready) "${state.databaseCount} entries · ${state.sync.message}" else state.status,
                                style = MaterialTheme.typography.labelSmall,
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                        }
                        IconButton(onClick = { syncDialog = true }) {
                            Icon(if (state.sync.connected) Icons.Default.Cloud else Icons.Default.CloudOff, contentDescription = "Dictionary sync")
                        }
                    }
                }
                if (state.busy || state.sync.busy || !state.ready) LinearProgressIndicator(Modifier.fillMaxWidth())
                LazyRow(
                    contentPadding = PaddingValues(horizontal = 10.dp, vertical = 7.dp),
                    horizontalArrangement = Arrangement.spacedBy(7.dp),
                ) {
                    items(tabs.indices.toList()) { index ->
                        FilterChip(
                            selected = selectedTab == index,
                            onClick = { selectedTab = index },
                            label = { Text(tabs[index].short) },
                        )
                    }
                }
                HorizontalDivider()
            }
        },
        floatingActionButton = {
            if (selectedTab == 0) {
                ExtendedFloatingActionButton(onClick = { addDialog = true }, icon = { Icon(Icons.Default.Add, null) }, text = { Text("Add entry") })
            }
        },
    ) { padding ->
        Box(Modifier.fillMaxSize().padding(padding)) {
            when (selectedTab) {
                0 -> DictionaryScreen(
                    state = state,
                    onQuery = viewModel::setQuery,
                    onSearch = { viewModel.performSearch(true) },
                    onHistory = viewModel::chooseHistory,
                    onSpeak = ::speak,
                    onEdit = { editing = it },
                    onDelete = { deleting = it },
                    onConjugate = { entry -> selectedTab = 1; viewModel.openVerbFromDictionary(entry.headword) },
                    onAdjective = { entry ->
                        adjectivePrefill = entry.headword
                        selectedTab = 4
                    },
                    onNoun = { entry -> selectedTab = 5; viewModel.setNounQuery(entry.headword); viewModel.declineNoun(entry.headword) },
                )
                1 -> ConjugationScreen(state, viewModel::setVerbQuery, viewModel::conjugate)
                2 -> ArticleScreen()
                3 -> PronounScreen()
                4 -> AdjectiveScreen(viewModel, adjectivePrefill)
                5 -> NounScreen(state, viewModel::setNounQuery, viewModel::declineNoun)
            }
        }
    }
}

@Composable
private fun DictionaryScreen(
    state: GermanUiState,
    onQuery: (String) -> Unit,
    onSearch: () -> Unit,
    onHistory: (String) -> Unit,
    onSpeak: (String) -> Unit,
    onEdit: (DictionaryEntry) -> Unit,
    onDelete: (DictionaryEntry) -> Unit,
    onConjugate: (DictionaryEntry) -> Unit,
    onAdjective: (DictionaryEntry) -> Unit,
    onNoun: (DictionaryEntry) -> Unit,
) {
    Column(Modifier.fillMaxSize()) {
        OutlinedTextField(
            value = state.query,
            onValueChange = onQuery,
            modifier = Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 10.dp),
            singleLine = true,
            label = { Text("German · English · Penglish · Persian") },
            leadingIcon = { Icon(Icons.Default.Search, null) },
            trailingIcon = {
                Row {
                    if (state.query.isNotEmpty()) IconButton(onClick = { onQuery("") }) { Icon(Icons.Default.Clear, "Clear") }
                    IconButton(onClick = onSearch) { Icon(Icons.Default.ArrowForward, "Search") }
                }
            },
        )
        if (state.searchHistory.isNotEmpty()) {
            LazyRow(contentPadding = PaddingValues(horizontal = 12.dp), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                items(state.searchHistory) { item -> AssistChip(onClick = { onHistory(item) }, label = { Text(item, maxLines = 1) }) }
            }
        }
        Text(state.status, modifier = Modifier.padding(horizontal = 14.dp, vertical = 6.dp), style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(start = 12.dp, end = 12.dp, bottom = 96.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            items(state.results, key = { it.index }) { entry ->
                DictionaryCard(entry, onSpeak, onEdit, onDelete, onConjugate, onAdjective, onNoun)
            }
            if (state.results.isEmpty() && state.ready) {
                item { EmptyHint("No matching entry found. Try fewer characters or another spelling.") }
            }
        }
    }
}

@Composable
private fun DictionaryCard(
    entry: DictionaryEntry,
    onSpeak: (String) -> Unit,
    onEdit: (DictionaryEntry) -> Unit,
    onDelete: (DictionaryEntry) -> Unit,
    onConjugate: (DictionaryEntry) -> Unit,
    onAdjective: (DictionaryEntry) -> Unit,
    onNoun: (DictionaryEntry) -> Unit,
) {
    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerLow)) {
        Column(Modifier.fillMaxWidth().padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                IconButton(onClick = { onSpeak(entry.headword) }, modifier = Modifier.size(38.dp)) { Icon(Icons.Default.VolumeUp, "Pronounce") }
                Spacer(Modifier.width(4.dp))
                Text(entry.headword, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold, modifier = Modifier.weight(1f))
                Text(entry.role, style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.primary)
            }
            MeaningBox("English", entry.english)
            MeaningBox("Persian", entry.persian, rtl = true)
            MeaningBox("Penglish", entry.penglish)
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Text("Pronunciation: ${if (entry.ipa.isBlank()) "—" else "[${entry.ipa}]"}", style = MaterialTheme.typography.bodySmall)
            }
            entry.detailLines().take(14).forEach { line ->
                val isExample = line.lowercase(Locale.ROOT).startsWith("ex:")
                Surface(
                    shape = RoundedCornerShape(7.dp),
                    color = if (isExample) MaterialTheme.colorScheme.secondaryContainer.copy(alpha = .55f) else MaterialTheme.colorScheme.surface,
                ) { Text(line, modifier = Modifier.padding(horizontal = 9.dp, vertical = 6.dp), style = MaterialTheme.typography.bodyMedium) }
            }
            HorizontalDivider()
            Row(
                modifier = Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                when (entry.role) {
                    "verb" -> FilledTonalButton(onClick = { onConjugate(entry) }) { Text("Conjugate") }
                    "adjective" -> FilledTonalButton(onClick = { onAdjective(entry) }) { Text("Endungen") }
                    "noun" -> FilledTonalButton(onClick = { onNoun(entry) }) { Text("Endungen") }
                }
                OutlinedButton(onClick = { onEdit(entry) }) { Icon(Icons.Default.Edit, null, Modifier.size(18.dp)); Spacer(Modifier.width(5.dp)); Text("Edit") }
                OutlinedButton(onClick = { onDelete(entry) }) { Icon(Icons.Default.Delete, null, Modifier.size(18.dp)); Spacer(Modifier.width(5.dp)); Text("Delete") }
            }
        }
    }
}

@Composable
private fun MeaningBox(label: String, value: String, rtl: Boolean = false) {
    Surface(shape = RoundedCornerShape(8.dp), color = MaterialTheme.colorScheme.tertiaryContainer.copy(alpha = .45f)) {
        Row(Modifier.fillMaxWidth().padding(horizontal = 10.dp, vertical = 8.dp)) {
            Text("$label: ", fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.tertiary)
            Text(value.ifBlank { "—" }, modifier = Modifier.weight(1f))
        }
    }
}

@Composable
private fun ConjugationScreen(state: GermanUiState, onQuery: (String) -> Unit, onConjugate: (String) -> Unit) {
    Column(Modifier.fillMaxSize()) {
        OutlinedTextField(
            value = state.verbQuery,
            onValueChange = onQuery,
            modifier = Modifier.fillMaxWidth().padding(12.dp),
            label = { Text("German infinitive · e.g. gehen, aufstehen, sich freuen") },
            singleLine = true,
            trailingIcon = { IconButton(onClick = { onConjugate(state.verbQuery) }) { Icon(Icons.Default.ArrowForward, "Conjugate") } },
        )
        state.conjugationError?.let { Text(it, color = MaterialTheme.colorScheme.error, modifier = Modifier.padding(horizontal = 14.dp)) }
        val result = state.conjugation
        if (result == null) {
            EmptyHint("Enter an infinitive. The Android engine uses the same irregular-verb YAML, separable-prefix logic and Passive section as the desktop app.")
            return
        }
        LazyColumn(
            contentPadding = PaddingValues(horizontal = 12.dp, vertical = 4.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            item {
                Card {
                    Column(Modifier.padding(14.dp)) {
                        Text(result.infinitive, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
                        Text("Partizip II: ${result.participle} · Hilfsverb: ${result.auxiliary}")
                        Text("Source: ${result.source}", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        if (result.note.isNotBlank()) Text(result.note, style = MaterialTheme.typography.bodySmall)
                    }
                }
            }
            result.sections.forEach { (title, cards) ->
                item { SectionTitle(title) }
                items(cards) { card -> TenseCardView(card) }
            }
            item { SectionTitle("IMPERATIV PRÄSENS") }
            item { TenseCardView(TenseCard("du · ihr · Sie", result.imperatives)) }
            item { SectionTitle("PARTIZIPIEN") }
            item { SimplePairCard(result.participles) }
            item { SectionTitle("INFINITIVE") }
            item { SimplePairCard(result.infinitives) }
            item { Spacer(Modifier.height(24.dp)) }
        }
    }
}

@Composable
private fun TenseCardView(card: TenseCard) {
    OutlinedCard {
        Column(Modifier.fillMaxWidth().padding(12.dp), verticalArrangement = Arrangement.spacedBy(5.dp)) {
            Text(card.title, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary)
            card.lines.forEach { Text(it, style = MaterialTheme.typography.bodyMedium) }
        }
    }
}

@Composable
private fun SimplePairCard(items: List<Pair<String, String>>) {
    OutlinedCard { Column(Modifier.fillMaxWidth().padding(12.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
        items.forEach { (label, form) -> Row { Text("$label: ", fontWeight = FontWeight.Bold); Text(form) } }
    } }
}

@Composable
private fun ArticleScreen() {
    var type by remember { mutableStateOf("Alle") }
    var case by remember { mutableStateOf("Alle") }
    var gender by remember { mutableStateOf("Alle") }
    val types = listOf("Alle") + GrammarTables.articles.keys
    val cases = listOf("Alle") + GrammarTables.cases
    val genders = listOf("Alle") + GrammarTables.genders
    val rows = buildList {
        GrammarTables.articles.forEach { (t, table) ->
            if (type != "Alle" && type != t) return@forEach
            GrammarTables.cases.forEach { c ->
                if (case != "Alle" && case != c) return@forEach
                GrammarTables.genders.forEachIndexed { i, g ->
                    if (gender == "Alle" || gender == g) add(listOf(t, c, g, table.getValue(c)[i]))
                }
            }
        }
    }
    GrammarTableScreen(
        title = "Artikel in den vier Kasus",
        hint = "Leere/Alle Filter zeigen alle passenden Formen.",
        selectors = listOf(
            Triple("Artikeltyp", type, types) to { type = it },
            Triple("Kasus", case, cases) to { case = it },
            Triple("Genus", gender, genders) to { gender = it },
        ),
        rows = rows,
    )
}

@Composable
private fun PronounScreen() {
    val types = listOf("Personalpronomen", "Possessivartikel", "Possessivpronomen", "Reflexivpronomen") + GrammarTables.pronounDeclensions.keys
    var type by remember { mutableStateOf(types.first()) }
    var case by remember { mutableStateOf("Alle") }
    var gender by remember { mutableStateOf("Alle") }
    var owner by remember { mutableStateOf("Alle") }
    val rows = buildList<List<String>> {
        when (type) {
            "Personalpronomen" -> GrammarTables.personal.forEach { (c, forms) ->
                if (case == "Alle" || case == c) forms.forEachIndexed { i, form -> add(listOf(c, GrammarTables.persons[i], form)) }
            }
            "Reflexivpronomen" -> GrammarTables.reflexive.forEach { (c, forms) ->
                if (case == "Alle" || case == c) forms.forEachIndexed { i, form -> add(listOf(c, GrammarTables.persons[i], form)) }
            }
            "Possessivartikel", "Possessivpronomen" -> {
                val owners = if (owner == "Alle") GrammarTables.persons else listOf(owner)
                val cs = if (case == "Alle") GrammarTables.cases else listOf(case)
                val gs = if (gender == "Alle") GrammarTables.genders else listOf(gender)
                owners.forEach { o -> cs.forEach { c -> gs.forEach { g ->
                    val form = if (type == "Possessivartikel") GrammarTables.possessiveArticle(o, c, g) else GrammarTables.possessivePronoun(o, c, g)
                    add(listOf(o, c, g, form))
                } } }
            }
            else -> GrammarTables.pronounDeclensions[type].orEmpty().forEach { (c, forms) ->
                if (case == "Alle" || case == c) GrammarTables.genders.forEachIndexed { i, g ->
                    if (gender == "Alle" || gender == g) add(listOf(c, g, forms[i]))
                }
            }
        }
    }
    val selectorPairs = mutableListOf<Pair<Triple<String, String, List<String>>, (String) -> Unit>>()
    selectorPairs += Triple("Typ", type, types) to { type = it }
    selectorPairs += Triple("Kasus", case, listOf("Alle") + GrammarTables.cases) to { case = it }
    if (type !in setOf("Personalpronomen", "Reflexivpronomen")) selectorPairs += Triple("Genus", gender, listOf("Alle") + GrammarTables.genders) to { gender = it }
    if (type in setOf("Possessivartikel", "Possessivpronomen")) selectorPairs += Triple("Besitzer", owner, listOf("Alle") + GrammarTables.persons) to { owner = it }
    GrammarTableScreen("Pronomen", "Alle Filter sind optional. Nicht anwendbare Kasus werden ausgelassen.", selectorPairs, rows)
}

@Composable
private fun AdjectiveScreen(viewModel: GermanViewModel, prefill: String) {
    var word by remember { mutableStateOf("") }
    LaunchedEffect(prefill) {
        if (prefill.isNotBlank()) word = prefill
    }
    var determiner by remember { mutableStateOf("") }
    var type by remember { mutableStateOf("Automatisch (nach Begleiter)") }
    var case by remember { mutableStateOf("Alle") }
    var gender by remember { mutableStateOf("Alle") }
    val allRows = remember(word, determiner, type) { viewModel.adjectiveRows(word, determiner, type) }
    val rows = allRows.filter { (case == "Alle" || it.case == case) && (gender == "Alle" || it.gender == gender) }
    val detected = viewModel.detectedAdjectiveType(determiner)
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(12.dp),
        verticalArrangement = Arrangement.spacedBy(9.dp),
    ) {
        item {
            OutlinedTextField(word, { word = it }, Modifier.fillMaxWidth(), label = { Text("Adjektiv · z. B. traurig, hoch") }, singleLine = true)
        }
        item {
            OutlinedTextField(determiner, { determiner = it }, Modifier.fillMaxWidth(), label = { Text("Begleiter/Artikel · z. B. der, ein, mein, ohne") }, singleLine = true)
        }
        item {
            Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Selector("Deklination", type, listOf("Automatisch (nach Begleiter)") + GrammarTables.adjectiveEndings.keys) { type = it }
                Selector("Kasus", case, listOf("Alle") + GrammarTables.cases) { case = it }
                Selector("Genus", gender, listOf("Alle") + GrammarTables.genders) { gender = it }
            }
        }
        if (type == "Automatisch (nach Begleiter)") item {
            Text("Detected: ${detected ?: "unknown determiner — showing all three declensions"}", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        if (word.isBlank()) item { EmptyHint("Enter an adjective. The app supports strong, weak, mixed and automatic declension, including irregular adjective stems.") }
        items(rows) { row -> AdjectiveRowCard(row) }
        item { Spacer(Modifier.height(20.dp)) }
    }
}

@Composable
private fun AdjectiveRowCard(row: AdjectiveRow) {
    OutlinedCard { Row(Modifier.fillMaxWidth().padding(11.dp), verticalAlignment = Alignment.CenterVertically) {
        Column(Modifier.weight(1f)) { Text(row.declension, style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.primary); Text("${row.case} · ${row.gender}", style = MaterialTheme.typography.bodySmall) }
        Text(row.form, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
    } }
}

@Composable
private fun NounScreen(state: GermanUiState, onQuery: (String) -> Unit, onDecline: (String) -> Unit) {
    Column(Modifier.fillMaxSize()) {
        OutlinedTextField(
            state.nounQuery,
            onQuery,
            Modifier.fillMaxWidth().padding(12.dp),
            label = { Text("Nomen · z. B. der Hund, die Gelegenheit, das Herz") },
            singleLine = true,
            trailingIcon = { IconButton(onClick = { onDecline(state.nounQuery) }) { Icon(Icons.Default.ArrowForward, "Decline") } },
        )
        val result = state.nounResult
        if (result == null) {
            EmptyHint("Dictionary Genitiv/Plural forms are preferred; then n-declension rules and irregular_nouns.yaml are applied.")
        } else {
            NounResultView(result)
        }
    }
}

@Composable
private fun NounResultView(result: NounResult) {
    LazyColumn(contentPadding = PaddingValues(horizontal = 12.dp, vertical = 4.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        item {
            Card { Column(Modifier.padding(14.dp)) {
                Text("${result.base} — ${result.gender}", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
                Text("Source: ${result.source}", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                if (result.note.isNotBlank()) Text(result.note, style = MaterialTheme.typography.bodySmall)
            } }
        }
        items(result.rows) { row ->
            OutlinedCard { Column(Modifier.padding(12.dp)) {
                Text(row.case, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary)
                Row(Modifier.fillMaxWidth()) { Text("Singular", Modifier.width(90.dp), fontWeight = FontWeight.SemiBold); Text(row.singular, Modifier.weight(1f)); Text(row.singularEnding) }
                Row(Modifier.fillMaxWidth()) { Text("Plural", Modifier.width(90.dp), fontWeight = FontWeight.SemiBold); Text(row.plural, Modifier.weight(1f)); Text(row.pluralEnding) }
            } }
        }
    }
}

@Composable
private fun GrammarTableScreen(
    title: String,
    hint: String,
    selectors: List<Pair<Triple<String, String, List<String>>, (String) -> Unit>>,
    rows: List<List<String>>,
) {
    LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        item { Text(title, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold) }
        item { Text(hint, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant) }
        item {
            Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                selectors.forEach { (spec, callback) -> Selector(spec.first, spec.second, spec.third, callback) }
            }
        }
        items(rows) { row ->
            OutlinedCard { Row(Modifier.fillMaxWidth().padding(11.dp), verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) { row.dropLast(1).forEachIndexed { i, value -> Text(value, style = if (i == 0) MaterialTheme.typography.labelMedium else MaterialTheme.typography.bodySmall, color = if (i == 0) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurface) } }
                Text(row.lastOrNull().orEmpty(), style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            } }
        }
        item { Spacer(Modifier.height(16.dp)) }
    }
}

@Composable
private fun Selector(label: String, value: String, options: List<String>, onChange: (String) -> Unit) {
    var expanded by remember { mutableStateOf(false) }
    Box {
        OutlinedButton(onClick = { expanded = true }) { Text("$label: $value", maxLines = 1) }
        DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            options.forEach { option ->
                DropdownMenuItem(
                    text = { Text(option) },
                    onClick = { expanded = false; onChange(option) },
                    leadingIcon = { if (option == value) Icon(Icons.Default.Check, null) },
                )
            }
        }
    }
}

@Composable
private fun SectionTitle(title: String) {
    Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Black, color = MaterialTheme.colorScheme.primary, modifier = Modifier.padding(top = 5.dp))
}

@Composable
private fun EmptyHint(text: String) {
    Surface(
        modifier = Modifier.fillMaxWidth().padding(14.dp),
        shape = RoundedCornerShape(12.dp),
        color = MaterialTheme.colorScheme.surfaceContainer,
    ) { Text(text, Modifier.padding(16.dp), color = MaterialTheme.colorScheme.onSurfaceVariant) }
}

@Composable
private fun EntryEditorDialog(
    title: String,
    initial: String,
    busy: Boolean,
    onDismiss: () -> Unit,
    onSave: (String) -> Unit,
) {
    var text by remember(initial) { mutableStateOf(initial) }
    AlertDialog(
        onDismissRequest = { if (!busy) onDismiss() },
        title = { Text(title) },
        text = {
            Column {
                Text("Paste or edit the complete entry. The first line determines the headword and grammatical role.", style = MaterialTheme.typography.bodySmall)
                Spacer(Modifier.height(8.dp))
                OutlinedTextField(
                    value = text,
                    onValueChange = { text = it },
                    modifier = Modifier.fillMaxWidth().height(330.dp),
                    label = { Text("Complete dictionary entry") },
                )
            }
        },
        confirmButton = { Button(onClick = { onSave(text.trim()) }, enabled = text.isNotBlank() && !busy) { Text("Save") } },
        dismissButton = { TextButton(onClick = onDismiss, enabled = !busy) { Text("Cancel") } },
    )
}

@Composable
private fun SyncDialog(
    state: com.ndgerman.android.data.SyncState,
    configured: Boolean,
    onDismiss: () -> Unit,
    onConnect: () -> Unit,
    onPull: () -> Unit,
    onPush: () -> Unit,
    onDisconnect: () -> Unit,
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Shared dictionary sync") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(if (state.connected) Icons.Default.Cloud else Icons.Default.CloudOff, null)
                    Spacer(Modifier.width(8.dp))
                    Text(if (state.connected) "Dropbox connected" else "Dropbox not connected", fontWeight = FontWeight.Bold)
                }
                Text(state.message)
                Text("Remote: /repo/data/nd_german_project/dictionary.sqlite3", style = MaterialTheme.typography.bodySmall)
                if (state.lastRemoteRevision != null) Text("Revision: ${state.lastRemoteRevision}", style = MaterialTheme.typography.bodySmall)
                if (state.pendingLocalChanges) Text("Android has local edits waiting to sync.", color = MaterialTheme.colorScheme.error, fontWeight = FontWeight.SemiBold)
                if (!configured) {
                    Text("Add ND_GERMAN_DROPBOX_APP_KEY to local.properties to enable OAuth sync. Offline dictionary and all grammar tools still work.", color = MaterialTheme.colorScheme.error)
                }
                if (state.connected) {
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        FilledTonalButton(onClick = onPull, enabled = !state.busy) { Icon(Icons.Default.Refresh, null); Spacer(Modifier.width(5.dp)); Text("Pull") }
                        FilledTonalButton(onClick = onPush, enabled = !state.busy) { Icon(Icons.Default.Sync, null); Spacer(Modifier.width(5.dp)); Text("Push") }
                    }
                    OutlinedButton(onClick = onDisconnect, enabled = !state.busy) { Text("Disconnect Dropbox") }
                } else {
                    Button(onClick = onConnect, enabled = configured && !state.busy) { Text("Connect Dropbox") }
                }
            }
        },
        confirmButton = { TextButton(onClick = onDismiss) { Text("Close") } },
    )
}
