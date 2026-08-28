from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_117.py <android-project-root>")

root = Path(sys.argv[1])
java = root / "app/src/main/java/com/varasecurity/alpha031/MainActivity.java"
gradle = root / "app/build.gradle"
s = java.read_text(encoding="utf-8")

for marker in [
    '0.11.6 ALPHA',
    'setAllowFileAccessFromFileURLs(false)',
    'setAcceptThirdPartyCookies(web, false)',
    'Protected WebView isolation',
    'Protected navigation cleanup',
]:
    if marker not in s:
        raise SystemExit(f"missing validated 0.11.6 prerequisite: {marker}")

# 0.11.7: reduce protected WebView data/sensor surface without disabling JavaScript or
# DOM storage required by many banking/payment flows. Geolocation and the legacy Web SQL
# database surface are not required by VARA protected browsing and are explicitly disabled.
anchor = '        ws.setMediaPlaybackRequiresUserGesture(true);'
if s.count(anchor) != 1:
    raise SystemExit(f"patch failed [protected data-surface anchor]: found {s.count(anchor)}")

hardening = '''        ws.setMediaPlaybackRequiresUserGesture(true);\n        ws.setGeolocationEnabled(false);\n        ws.setDatabaseEnabled(false);'''
s = s.replace(anchor, hardening, 1)

compat_anchor = '        content.addView(webViewIsolationCard);'
if s.count(compat_anchor) != 1:
    raise SystemExit(f"patch failed [compatibility data-surface anchor]: found {s.count(compat_anchor)}")
card = '''        content.addView(webViewIsolationCard);\n\n        LinearLayout protectedDataSurfaceCard = card();\n        protectedDataSurfaceCard.addView(tv(t("Protected data-surface boundary", "مرزبندی سطح داده در نشست محافظت‌شده"), 16, NAVY, true));\n        protectedDataSurfaceCard.addView(tv(t("Geolocation disabled • legacy Web SQL database disabled",\n                "موقعیت مکانی غیرفعال • پایگاه داده قدیمی Web SQL غیرفعال"), 13, GOOD, true));\n        protectedDataSurfaceCard.addView(tv(t("JavaScript and DOM storage remain available for banking compatibility, while unnecessary location and legacy database surfaces stay unavailable in SafePay and Secure Browser.",\n                "JavaScript و DOM Storage برای سازگاری بانکی فعال می‌مانند، اما دسترسی غیرضروری به موقعیت مکانی و پایگاه داده قدیمی در SafePay و مرورگر امن غیرفعال است."), 12, MUTED, false));\n        content.addView(protectedDataSurfaceCard);'''
s = s.replace(compat_anchor, card, 1)

s = s.replace('0.11.6 ALPHA', '0.11.7 ALPHA')
s = s.replace('0.11.6 Alpha • versionCode 1106', '0.11.7 Alpha • versionCode 1107')
s = s.replace('0.11.6 Alpha', '0.11.7 Alpha')
s = s.replace('VARA 0.11.6 requires Android 8.0 / API 26 or newer.', 'VARA 0.11.7 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+1106\b', 'versionCode 1107', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.11\.6-alpha['\"]", "versionName '0.11.7-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

for marker in [
    'setGeolocationEnabled(false)',
    'setDatabaseEnabled(false)',
    'Protected data-surface boundary',
    'Geolocation disabled',
    '0.11.7 ALPHA',
]:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.11.7 protected data-surface hardening patch applied")
