# NoonDreams Android release status — 2026-10-18

## Prepared locally
- Public package: com.ndgerman.android.play; separate from the personal Dropbox build.
- Dedicated signed AAB and test APK configured; upload key outside repository.
- Listing text in STORE_LISTING.md (English/German).
- Privacy Policy in PRIVACY_POLICY.md and publishable privacy_policy.html.
- Store icon PNG: assets/store_icon_512.png (512×512).
- Feature graphic PNG: assets/feature_graphic_1024x500.png (1024×500).
- Graphics generator: generate_assets.py.
- SDK/privacy declaration worksheet: DATA_SAFETY_REVIEW.md.
- Closed test invitations/QA: CLOSED_TEST.md.

## Remaining, not done
1. Google Play identity verification pending on 2026-10-18.
2. Contact phone verification after identity approval.
3. Publish privacy_policy.html on noondreams.com. Current /privacy-policy/ returns 404.
4. In Play Console create app, complete required App content and store metadata, upload AAB.
5. Obtain 2+ actual Android screenshots. No connected ADB device or emulator AVD available.
6. Run the required 12-tester/14-day closed test; apply for production access.
7. For paid/advertising update only: configure real AdMob IDs/UMP, remove_ads product, purchase/restore validation.

## Cautions
- Keep signing key and password outside Git and Dropbox; encrypted offline backup.
- SDKs remain packaged even in no-ad build; check Data safety claims carefully.
- Preserve permanent application ID and increment versionCode for later Play uploads.
- This is a readiness record, not a claim of Google Play approval.
