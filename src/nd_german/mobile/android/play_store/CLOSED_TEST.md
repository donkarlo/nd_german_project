# Closed testing — NoonDreams German Learning

For a new Google Play personal developer account: 12 testers opted in continuously for at least 14 days before applying for production access. Invite 15–20 willing people to cover opt-outs. The clock begins with actual opt-ins, not with preparation.

## After identity and phone verification
1. Create the app as com.ndgerman.android.play; use Play App Signing.
2. Upload current signed Play AAB to Closed testing.
3. Complete Store listing, App content, and Data safety declarations.
4. Add consenting testers' emails or a Google Group.
5. Obtain the official closed-test opt-in link from Play Console.
6. Collect useful feedback and fix reported issues.
7. Check 12 continuous opt-ins for 14 days, then apply for production access.

## English invitation draft
Subject: Invitation to test NoonDreams German Learning on Android

Hello,
I'm preparing a new offline German dictionary and grammar app for Android. Would you be willing to join a closed Google Play test? Please try searching words and using the grammar tools, and tell me if anything doesn't work. Google asks that testers remain opted in for at least 14 days. Participation is voluntary; you can leave at any time.
Link: [ADD OFFICIAL GOOGLE PLAY TEST LINK]
Feedback: contact@noondreams.com
Thank you!

## Deutsche Einladung
Betreff: Einladung zum Test der Android-App German Learning

Hallo,
ich bereite eine neue Offline-App mit einem deutschen Wörterbuch und Grammatikhilfen vor. Hättest du Interesse, an einem geschlossenen Google-Play-Test teilzunehmen? Du kannst die Suche und Grammatikfunktionen ausprobieren und mir Fehler melden. Google verlangt mindestens 14 Tage Anmeldung für Testpersonen. Die Teilnahme ist freiwillig.
Link: [LINK AUS DER GOOGLE PLAY CONSOLE]
Feedback: contact@noondreams.com
Vielen Dank!

## Real-device QA checklist
- Install public Play APK, confirm first-launch DB load and search.
- Test German, English, Persian, Penglish; special characters; examples and conjugations.
- Check offline mode, app restart, navigation and large datasets.
- Check RTL, text-to-speech, font display and accessibility.
- Confirm no Dropbox OAuth, no edit functions, no unintended network upload.
- Confirm ads and paid removal are inactive without production setup.
- Capture at least two unedited actual Android screenshots from the shipping build.
- Check privacy policy via HTTPS without authentication.
- Safely back up upload key and signing config to offline encrypted storage.
