#!/usr/bin/env bash
# Take a genuine screenshot of the public Android Play app after it is installed.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$HERE/assets/screenshots"
mkdir -p "$OUT"
command -v adb >/dev/null || { echo "adb is not installed."; exit 1; }
if ! adb get-state 2>/dev/null | grep -qx device; then
    echo "Connect and authorize an Android device using USB or wireless ADB."
    echo "Only actual screenshots from the public Play app are acceptable."
    exit 2
fi
if ! adb shell pm path com.ndgerman.android.play | grep -q '^package:'; then
    echo "Install app/build/outputs/apk/play/app-play.apk first (the public Play build)."
    exit 3
fi
adb shell am start -n com.ndgerman.android.play/com.ndgerman.android.MainActivity
echo "Put the public app on a clean, representative screen, then press Enter."
read -r _
for N in 1 2; do
    printf 'Capture real screenshot %s: prepare device and press Enter...' "$N"
    read -r _
    adb exec-out screencap -p > "$OUT/android_screenshot_$N.png"
    file "$OUT/android_screenshot_$N.png"
    echo "Saved $OUT/android_screenshot_$N.png"
done
echo "Check images for personal data and verify they reflect the shipping version."
