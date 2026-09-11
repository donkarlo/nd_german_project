# ND German · Android

Native Android companion for the ND German desktop dictionary/grammar application.

## What is included

- Dictionary search over the same SQLite schema used by the desktop application.
- German / English / Penglish / Persian results, IPA/details/examples and Android TTS.
- Add, edit and delete dictionary entries on Android.
- Search history and direct navigation from a dictionary result to grammar tools.
- Verb conjugation: Indikativ, Konjunktiv I, Konjunktiv II, imperative, participles, infinitives and Vorgangspassiv.
- Artikel tables for all four cases and genders.
- Personal-, Possessiv-, Reflexiv-, Demonstrativ-, Relativ- and Fragepronomen.
- Adjektivendungen with strong/weak/mixed declension and automatic determiner detection.
- Nomenendungen including dictionary Genitiv/Plural data, n-Deklination and irregular noun exceptions.
- Material 3 / Jetpack Compose phone UI.
- Bidirectional Dropbox synchronization of `dictionary.sqlite3` with conflict-safe revision checks.

## Shared dictionary

The desktop application already treats this file as authoritative:

`/repo/data/nd_german_project/dictionary.sqlite3`

The Android application downloads a local working copy for fast/offline access. Android edits are written to the same SQLite schema (including the FTS5 table) and can then be pushed back to the Dropbox file. Pull/push operations use Dropbox revisions so an Android device never silently overwrites a newer desktop revision.

The desktop application continues to read the SQLite file through the normal Dropbox filesystem at:

`/home/donkarlo/Dropbox/repo/data/nd_german_project/dictionary.sqlite3`

## Build-time data

`app/build.gradle.kts` copies the latest desktop assets into the APK before each build:

- `dictionary.sqlite3`
- `irregular_verbs.yaml`
- `irregular_adjectives.yaml`
- `irregular_nouns.yaml`

This makes the APK useful immediately even before Dropbox is connected. After installation, Dropbox Sync keeps the working database current.

## Dropbox setup

Create a separate Dropbox API app for ND German. Use **Full Dropbox** access (not App Folder), because the shared database already lives under `/repo/data/nd_german_project/`.

Enable these scoped permissions:

- `account_info.read`
- `files.metadata.read`
- `files.content.read`
- `files.content.write`

Only the **App key** is needed on Android. Do not put the App secret in the application.

Create `local.properties` from the example and set:

```properties
sdk.dir=/home/donkarlo/Android/Sdk
ND_GERMAN_DROPBOX_APP_KEY=YOUR_DROPBOX_APP_KEY
```

A separate app key is recommended so the OAuth redirect scheme does not collide with another installed ND Android application.

## Build and install

From the project directory:

```bash
cd /home/donkarlo/Dropbox/repo/nd_german_project/src/nd_german/mobile/android
./gradlew :app:assembleDebug
```

Then install:

```bash
~/Android/Sdk/platform-tools/adb install -r app/build/outputs/apk/debug/app-debug.apk
```

If more than one Android device is connected, add `-s <device-id>` to the adb command.

## Sync rules

- **Pull**: replaces the local Android copy with the current Dropbox revision.
- **Push**: uploads only if the Dropbox revision still matches the revision Android last read.
- **Pending local edits**: a normal pull is blocked to prevent accidental loss.
- **Revision conflict**: the app keeps the local edits and reports the conflict; pull the new remote state only after intentionally discarding the pending Android changes.
- Add/edit/delete operations automatically try to push when Dropbox is connected. If offline, they remain pending locally.

## Source layout

- `data/DictionaryDatabase.kt` — SQLite/FTS5 search and CRUD compatible with desktop schema.
- `grammar/GermanGrammar.kt` — Android port of article/pronoun/adjective/noun/conjugation rules.
- `sync/DropboxSync.kt` — OAuth + revision-safe database synchronization.
- `ui/GermanViewModel.kt` — app state and operations.
- `ui/GermanApp.kt` — Material 3 Compose interface.

