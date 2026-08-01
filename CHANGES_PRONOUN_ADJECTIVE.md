# Pronoun and adjective corrections

## Pronomen

- `sie (Singular, feminin)`, `sie (Plural)`, and `Sie (Höflichkeitsform)` now have unique selector labels.
- Dative lookup now correctly distinguishes `ihr`, `ihnen`, and `Ihnen`.
- Possessive articles and standalone possessive pronouns are separate tables.
- Demonstrative `der/die/das` now uses `denen` in dative plural and `dessen/deren` in genitive.

## Adjektivendungen

- Added an optional `Begleiter/Artikel` field.
- Automatic mode detects:
  - weak declension after definite/der-type determiners,
  - mixed declension after ein/kein/possessive determiners,
  - strong declension without an article and after common strong quantifiers.
- Unknown determiners show all three paradigms rather than making an unsafe guess.
- Manual selection remains available.
- `irregular_adjectives_path` is now read from `settings.yaml`; the configured YAML mapping is loaded at startup and used for adjective stem formation.

## Verification

- Added grammar regression tests.
- All 34 unit tests pass.
