# Google Play App content / Data safety — working review

App: German Learning — Dictionary
Package: com.ndgerman.android.play
First closed test: use the existing no-ad configuration until real AdMob and UMP services are ready.

## Observed in source and compiled Android Play build
- Public app has an offline SQLite vocabulary database bundled inside.
- No Dropbox login/OAuth component in the public Play build.
- Local user preferences, dictionary state and searches can be stored on device.
- Android Backup enabled, so OS-level backup may be possible.
- Bundled libraries include Google Mobile Ads SDK, UMP and Google Play Billing, even without real AdMob IDs or a Play Billing product.
- **Important:** merged manifest contains AD_ID, AdServices ID/Attribution/Topics, BILLING, WAKE_LOCK and FOREGROUND_SERVICE permissions from SDKs. Do not automatically answer "no advertising ID" or "no data collection" just because ad banners are disabled. Verify actual SDK/network behavior before submitting.
- Android text-to-speech provider may process speech requests.

## Fields to fill in Play Console — verify first
- Category: Education.
- Ads declaration: answer based on exact release behavior and policies; don't guess.
- App access: no login for public offline dictionary.
- Target audience: choose actual age groups; review rules for children if applicable.
- Data safety: inspect SDK data collection, backup, optional TTS and Play Billing. Verify data type, sharing, purpose, encryption in transit, user deletion and optionality.
- Privacy Policy: public HTTPS page. Candidate https://noondreams.com/privacy-policy/ returned HTTP 404 on 2026-10-18; HTML ready as privacy_policy.html.
- Content rating: fill official IARC questionnaire truthfully.
- Confirm final manifest permissions and rights for third-party dictionary sources.

## Do not do automatically
- Do not declare data handling properties without evidence.
- Do not use sample AdMob IDs as production IDs.
- Do not activate remove_ads purchases until live product and purchase/restore/refund tests exist.
- Do not use simulated app UI instead of actual screenshot captures.
