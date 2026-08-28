from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_118.py <android-project-root>")

root = Path(sys.argv[1])
java = root / "app/src/main/java/com/varasecurity/alpha031/MainActivity.java"
gradle = root / "app/build.gradle"
s = java.read_text(encoding="utf-8")

for marker in [
    '0.11.7 ALPHA',
    'setGeolocationEnabled(false)',
    'setDatabaseEnabled(false)',
    'Protected data-surface boundary',
    'Protected WebView isolation',
]:
    if marker not in s:
        raise SystemExit(f"missing validated 0.11.7 prerequisite: {marker}")

# 0.11.8: explicitly reject HTTP subresources inside every protected WebView.
# Android 8+ is the project minimum, so MIXED_CONTENT_NEVER_ALLOW is uniformly available.
anchor = '        ws.setDatabaseEnabled(false);'
anchor_count = s.count(anchor)
if anchor_count < 1:
    raise SystemExit("patch failed [mixed-content anchor]: no protected WebView settings blocks found")

hardening = '''        ws.setDatabaseEnabled(false);\n        ws.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);'''
s = s.replace(anchor, hardening)
if s.count('setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW)') != anchor_count:
    raise SystemExit("patch failed [mixed-content coverage]: not all protected settings blocks were hardened")

compat_anchor = '        content.addView(protectedDataSurfaceCard);'
if s.count(compat_anchor) != 1:
    raise SystemExit(f"patch failed [compatibility mixed-content anchor]: found {s.count(compat_anchor)}")
card = '''        content.addView(protectedDataSurfaceCard);\n\n        LinearLayout mixedContentCard = card();\n        mixedContentCard.addView(tv(t("HTTPS mixed-content protection", "محافظت Mixed Content در HTTPS"), 16, NAVY, true));\n        mixedContentCard.addView(tv(t("HTTP subresources blocked inside protected HTTPS sessions",\n                "منابع HTTP داخل نشست محافظت‌شده HTTPS مسدود می‌شوند"), 13, GOOD, true));\n        mixedContentCard.addView(tv(t("SafePay and Secure Browser reject insecure HTTP images, scripts, frames and other subresources loaded by an HTTPS page. This reduces downgrade and injection exposure while preserving normal HTTPS banking flows.",\n                "SafePay و مرورگر امن، تصویر، اسکریپت، فریم و سایر منابع ناامن HTTP را در صفحات HTTPS رد می‌کنند. این کنترل ریسک downgrade و تزریق محتوا را کاهش می‌دهد و جریان عادی بانکی HTTPS را حفظ می‌کند."), 12, MUTED, false));\n        content.addView(mixedContentCard);'''
s = s.replace(compat_anchor, card, 1)

s = s.replace('0.11.7 ALPHA', '0.11.8 ALPHA')
s = s.replace('0.11.7 Alpha • versionCode 1107', '0.11.8 Alpha • versionCode 1108')
s = s.replace('0.11.7 Alpha', '0.11.8 Alpha')
s = s.replace('VARA 0.11.7 requires Android 8.0 / API 26 or newer.', 'VARA 0.11.8 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+1107\b', 'versionCode 1108', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.11\.7-alpha['\"]", "versionName '0.11.8-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

for marker in [
    'setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW)',
    'HTTPS mixed-content protection',
    'HTTP subresources blocked',
    '0.11.8 ALPHA',
]:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print(f"VARA Security 0.11.8 mixed-content hardening patch applied to {anchor_count} protected settings blocks")
