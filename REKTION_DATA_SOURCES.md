# Sources and verification for German verb Rektion data

The SQLite dictionary at `/home/donkarlo/Dropbox/repo/data/nd_german_project/dictionary.sqlite3` is the authoritative dictionary. Verb-Rektion entries added in October 2026 were prepared from a combination of existing in-dictionary grammatical descriptions, manually checked standard verb constructions, and the following open resources.

- **VerbframesDE** — bflowtoolbox, [source and license](https://github.com/bflowtoolbox/VerbframesDE), Mozilla Public License 2.0 (MPL-2.0). Only general matching verb patterns were extracted; idiom-specific fixed expressions were excluded from automatic transfer.
- **German Prepositions Anki Deck Suite** — Yuhou Zhou, [source](https://github.com/yuhouzhou/german-prepositions-anki), [MIT license](https://github.com/yuhouzhou/german-prepositions-anki/blob/main/LICENSE). Selected cases and prepositions were checked against the existing dictionary meaning before inclusion.

The initial bulk backfill preserved existing meanings and examples; a later focused quality-control pass repaired demonstrable category errors, the misleading explanation of `überlegen`, and an example of `anfragen`. Patterns are indexed in SQLite and in the derived verb-valency tables. All remaining entries without a verified construction are recorded separately for review.

Audit: `/home/donkarlo/Dropbox/repo/data/nd_german_project/backups/rektion_audit_20261011.json`.

Backups:
- `dictionary.before_rektion_backfill_20261011.sqlite3`
- `dictionary.before_rektion_supplement_20261012.sqlite3`

**Important:** Some entries have no governed complement, others contain incorrect verb tagging or lack sufficient evidence to determine every construction. These were not filled with guesses. All remaining unannotated entries require a separate review for completeness.
