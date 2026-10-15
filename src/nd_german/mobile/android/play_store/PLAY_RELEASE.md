# Android Play release checklist

## Current architecture
- Personal (owner-only) build: `app-debug.apk`, unchanged package `com.ndgerman.android`, Dropbox synchronization supported, no runtime advertisements.
- Public Play build: `com.ndgerman.android.play`, read-only dictionary, local-only synchronization, no Dropbox OAuth component, signed with a dedicated **upload key**. Not debuggable.
- Google Play account: owner `contact@noondreams.com`, developer `NoonDreams`.

## Signed bundle location
`app/build/outputs/bundle/play/app-play.aab`

## Key management
Signing secrets are never committed to the repo. Local files on owner's Ubuntu:
- `~/.config/nd_german_play/nd-german-upload.p12` — upload private key.
- `~/.config/nd_german_play/upload-signing.properties` — signing passwords, excluded from source control.

**Important:** Keep an offline encrypted backup of both files. Never share or paste their contents in chat; do not delete. Once Google Play App Signing is enabled, this is the **upload key**, distinct from the Google-managed distribution signing key. If lost, request a reset through Play Console; do not create a new key and silently replace it.

## Build commands
```sh
cd /home/donkarlo/Dropbox/repo/nd_german_project/src/nd_german/mobile/android
./gradlew :app:bundlePlay :app:assemblePlay --offline
```
Never upload `app-debug.apk` or an unsigned bundle to Play Console.

## Missing before ad-supported production
1. Create/register this exact public app in Google AdMob.
2. Copy its **real** AdMob App ID and banner Ad Unit ID into gitignored `local.properties`:
```properties
ND_GERMAN_ADMOB_APP_ID=ca-app-pub-XXXXXXXXXXXXXXXX~YYYYYYYYYY
ND_GERMAN_ADMOB_BANNER_ID=ca-app-pub-XXXXXXXXXXXXXXXX/ZZZZZZZZZZ
```
3. Build again. The public app deliberately does not load **any ads** when both real IDs are absent. Sample IDs in the manifest are placeholders solely for configuration; never publish a monetized version without checking AdMob setup.
4. In AdMob Privacy & messaging configure relevant consent messages (EEA/UK/Switzerland, etc.) and test Google UMP flow.
5. In Google Play Console create the optional **one-time in-app product** with Product ID `remove_ads` (only if shipping paid ad removal). Test purchase, restore, cancel, refunds. Do not make it available to buyers without testing and entitlement verification.
6. Review third-party SDK data collection and sharing, configure Google Play **Data safety**, advertising declaration and content rating honestly.
7. Publish `play_store/privacy_policy.html` at a public HTTPS URL under noondreams.com; link it in Play Console. The app also has a built-in privacy dialog.

## Play Store
- Use `play_store/STORE_LISTING.md` as draft, update screenshots from this signed Android build.
- New personal developer accounts must run a closed test with **12 opted-in testers continuously for at least 14 days**, then request production access (per current Play policy).
- Google account identity, Android phone and contact phone verifications must be approved.
- Use Google Play App Signing (Google manages distribution signing key). Retain the upload keystore.
- Application ID becomes permanent once the first bundle is uploaded; check `com.ndgerman.android.play` before uploading.
- Increase `versionCode` for every subsequent uploaded bundle.

## Acceptance before production
- Verify the bundled SQLite opens, search results include expected German, English, Persian/Penglish fields, and grammar/conjugations work.
- Confirm no Dropbox data/permissions in the Play manifest.
- Test offline operation, font rendering, RTL/Persian text, navigation, accessibility, text-to-speech, back behavior, and large/slow device performance.
- Test consent flow, ad visibility, ad-free purchase and restoration on real devices **after** creating live AdMob and Play Billing resources.
- Confirm publication/privacy pages do not imply features absent from the build.
- Check policy rules for any third-party dictionary sources or lexical datasets.
