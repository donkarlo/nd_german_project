# Android public Play build — verified

Built: 15 October 2026, on owner's Ubuntu laptop
Gradle `./gradlew :app:bundlePlay :app:assemblePlay :app:assembleDebug --offline` — **SUCCESS**

- Signed Play AAB: `/home/donkarlo/Dropbox/repo/nd_german_project/src/nd_german/mobile/android/app/build/outputs/bundle/play/app-play.aab` — **35.2 MiB**, signature verified.
- Test Play APK: `/home/donkarlo/Dropbox/repo/nd_german_project/src/nd_german/mobile/android/app/build/outputs/apk/play/app-play.apk` — **38.0 MiB**, signature verified.
- Copies in Downloads: `/home/donkarlo/Downloads/NoonDreams-German-Learning-v0.1.0-play.aab` and `/home/donkarlo/Downloads/NoonDreams-German-Learning-v0.1.0-test.apk`.
- Application ID: `com.ndgerman.android.play` (permanent after Play submission).
- Version: 0.1.0; versionCode 1; min SDK 26; target SDK 37.
- No debug flag; Play APK not debuggable.
- Play bundle contains no Dropbox artifacts / OAuth component.
- Bundled SQLite dictionary size, uncompressed: 72978432 bytes.
- AdMob real IDs **NOT configured**; ad requests disabled.
- Play in-app product `remove_ads` **not yet created/verified**; purchase action disabled until product has price.
- AAB SHA256: `2fad237d3c5c359157878a3db48b0c63e99ebdc405e27f97f29b54d7f42320f6`.
- Upload key cert SHA256: `e45b34b7c6dc8c7973c4a2d242f8227dd6e3c7e6f46f83a8a06c89eed7c0a633`.
- Upload key and password files are locally under `~/.config/nd_german_play/`, not in git; make a secure offline backup.

**Key note:** self-signed upload certificates are normal for Google Play App Signing. `jarsigner -verify` succeeded; `-strict` would warn about its lack of a CA chain.

**Pending before production:** Google developer identity approval; real AdMob IDs + consent message; live privacy page on noondreams.com; Play listing images; completed Data Safety/Ads declarations; optional paid `remove_ads` product; real-device QA; closed testing 12 opted-in testers for at least 14 consecutive days; approval for production access.
