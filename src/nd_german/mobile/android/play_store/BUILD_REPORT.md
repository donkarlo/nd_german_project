# Android public Play build — verified 18 October 2026

Public app: German Learning v0.1.0, application ID com.ndgerman.android.play, versionCode 1, Android minSdk 26 / targetSdk 37.

## Final signed build
- AAB: /home/donkarlo/Downloads/NoonDreams-German-Learning-v0.1.0-play.aab
- Public Play APK for local QA: /home/donkarlo/Downloads/NoonDreams-German-Learning-v0.1.0-test.apk
- Preserved previous October 15 AAB: /home/donkarlo/Downloads/NoonDreams-German-Learning-v0.1.0-play-20261015.aab
- Release bundle SHA256: f5acaa6ed39a07d3e45fbe6a8a0b0302fe43d5af89002e8a288fe68655c039ae
- Signature: jarsigner -verify succeeded (expected self-signed upload certificate).
- Build command: ./gradlew :app:lintPlay :app:assembleDebug :app:bundlePlay :app:assemblePlay --offline
- Build: SUCCESS; Android Lint: 0 errors, 4 warnings, 1 hint.

## Database / privacy validation
- Bundled dictionary database: 15,145 entries; SQLite integrity_check: ok.
- Database SHA256 inside the AAB exactly equals 2026-10-18 shared source: 61757ebf7bbb7847c1138081117f78da7eeb97f75480eec85a0184d539378eae
- Manifest: public Play build contains no Dropbox OAuth activity/package visibility; private debug build retains Dropbox authorization.
- No real AdMob IDs configured, so actual ad requests disabled by app logic.
- Live remove_ads product remains unconfigured; paid purchase action disabled.
- Review Google SDK manifest permissions and behavior before filing Play Console Data Safety answers.

## Creative and metadata
- assets/store_icon_512.png: 512x512 RGBA, 13,219 bytes.
- assets/feature_graphic_1024x500.png: 1024x500 RGB, 77,573 bytes.
- Store descriptions: STORE_LISTING.md
- Publishable privacy policy: privacy_policy.html; WordPress page body: privacy_policy_wordpress.html
- Tester invite and QA: CLOSED_TEST.md

## Remaining before upload and launch
- Developer identity and phone approval, then Create app in Play Console.
- Public HTTPS privacy policy (candidate /privacy-policy/ currently returns 404).
- 2+ **real** Android screenshots from public app; no connected ADB device or emulator AVD at build time. Use capture_store_screenshots.sh once authorized phone is connected.
- Complete ads/Data Safety and all other App content questionnaires; install and manually test the public Play APK.
- Closed test: 12 opted-in testers for 14 days, then request production access.
- Python pytest suite was not executed; system Python reports 'No module named pytest'. This does not affect the successful Gradle build but remains an independent QA gap.
