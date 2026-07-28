# Deutsch Dictionary + Verb Conjugation

A Linux desktop application built with Python and Qt (PySide6).

The original dictionary search/add interface remains in the **Dictionary** tab. A separate **Conjugation** tab was added for German verbs.

## Dictionary tab

- Searches German headwords, English translations, Penglish text and Persian text.
- Finds partial matches anywhere in an entry.
- Uses typo-tolerant fuzzy matching with a pre-indexed trigram candidate filter.
- Shows the first 20 matches by default; change `max_results` in `settings.yaml`.
- Adds complete multiline entries through a dialog.
- Rejects a new entry when the same word spelling and grammatical role already exists.
- Reads and writes UTF-8 and preserves the blank-line-separated database format.
- Shows a small speaker button before every headword. A web request is made
  only after that button is clicked, so normal dictionary searching remains
  local and keeps the same search path.
- Downloads pronunciation audio in a background worker through Python's HTTPS
  stack rather than Qt Network. This avoids Qt/OpenSSL runtime mismatches such
  as `TLS initialization failed` while keeping the GUI responsive.
- Initializes Qt Multimedia only after a valid local MP3 file has been
  downloaded.

## Conjugation tab

- Searches irregular verbs with fast autocomplete and typo-tolerant suggestions.
- Generates regular verbs directly with built-in German conjugation rules.
- Loads irregular and mixed verbs from `irregular_verbs.yaml`.
- The bundled database contains 164 common irregular/mixed base verbs and auxiliary overrides.
- Common prefixed compounds can inherit the base verb automatically, for example:
  - `aufstehen` from `stehen`
  - `anfangen` from `fangen`
  - `verstehen` from `stehen`
  - `einladen` from `laden`
- Displays:
  - Indikativ: Präsens, Präteritum, Futur I, Perfekt, Plusquamperfekt, Futur II
  - Konjunktiv I: Präsens, Futur I, Perfekt
  - Konjunktiv II: Präteritum, Futur I, Plusquamperfekt, Futur II
  - Imperativ Präsens: **du, ihr, Sie**
  - Partizip Präsens and Partizip II
  - Infinitiv Präsens, Infinitiv Perfekt, `zu + Infinitiv`, and perfect infinitive with `zu`
- Supports separable verbs such as `aufmachen` and `aufstehen`.
- Supports reflexive input such as `sich erinnern`.
- Accepts common keyboard spellings without German characters. For example,
  `mussen` and `muessen` are interpreted as `müssen`, and `zuruckkommen` as
  `zurückkommen`, when the spelling maps unambiguously.
- Handles common variable prefixes such as `um-`, `unter-`, `über-` and
  `durch-`, including `umsteigen`, `untergehen`, `übernehmen` and
  `durchlesen`.
- Corrects Partizip II/Partizip I edge cases such as `übernachtet`, `seiend`,
  `tuend` and `antuend`.

## Install and run on Linux

```bash
cd app
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
./run.sh
```

`run.sh` calls `configure.py`, which writes the bundled irregular-verb path and,
when a local `woerterbuch.txt` exists, its path into `settings.yaml`. If the
dictionary is stored elsewhere, the already configured path is preserved.

You can also override either database temporarily:

```bash
python3 app.py \
  --database /absolute/path/to/woerterbuch.txt \
  --irregular-verbs /absolute/path/to/irregular_verbs.yaml
```

## YAML settings

```yaml
database_path: /absolute/path/to/woerterbuch.txt
irregular_verbs_path: /absolute/path/to/irregular_verbs.yaml
max_results: 20
fuzzy_threshold: 58
search_debounce_ms: 80
conjugation_search_debounce_ms: 60
conjugation_suggestion_count: 14
pronunciation_enabled: true
pronunciation_api_url: https://translate.google.com/translate_tts
pronunciation_language: de
pronunciation_timeout_ms: 12000
pronunciation_max_download_bytes: 5000000
window_title: Deutsch–English–Persian Dictionary
```

The irregular-verb database path is therefore fully configurable without changing Python code.
The pronunciation service is contacted only after a speaker button is clicked.
The clicked headword is sent to the configured URL. The HTTPS download uses
Python's standard library in a worker thread; Qt Network and its TLS backend are
not used. A working Qt Multimedia audio output is still required to play the
already-downloaded local MP3. The URL can be replaced in `settings.yaml`
without changing the Python code.

## Pronunciation troubleshooting on Linux

Messages about `cert-only`, `QSslSocket`, or `TLS initialization failed` came
from Qt Network in the older build. This build no longer uses Qt Network for
pronunciation downloads. Messages about optional PipeWire or VA-API symbols can
still be printed when Qt Multimedia starts; they do not by themselves mean that
the HTTPS download failed. The status line at the bottom of the Dictionary tab
now reports download errors and playback errors separately.

## Keyboard shortcuts

- `Ctrl+F`: focus the search box of the active tab
- `Ctrl+N`: open the dictionary add-entry dialog

## Tests

```bash
python -m unittest discover -s tests -v
```

## Grammar lookup tabs
The application now contains three additional tabs:
- **Artikel**: filters article type, case, and gender/number.
- **Pronomen**: filters personal, reflexive, demonstrative, relative, interrogative, and possessive forms. Possessive forms distinguish the owner/person from the gender/number and case of the referenced noun.
- **Adjektivendungen**: generates strong, weak, and mixed adjective forms from an adjective search field plus case and gender/number filters. Orthographically special stems are documented in `irregular_adjectives.yaml`.
