from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_116.py <android-project-root>")

root = Path(sys.argv[1])
java = root / "app/src/main/java/com/varasecurity/alpha031/MainActivity.java"
gradle = root / "app/build.gradle"
s = java.read_text(encoding="utf-8")

for marker in [
    '0.11.5 ALPHA',
    'setAcceptThirdPartyCookies(web, false)',
    'Protected cookie isolation',
    'web.clearCache(true)',
    'web.clearSslPreferences()',
    'clearProtectedSessionState()',
]:
    if marker not in s:
        raise SystemExit(f"missing validated 0.11.5 prerequisite: {marker}")

# 0.11.6: explicitly erase in-WebView navigation and form residue before destroying a
# protected session. Save-form-data is already disabled, but clearing the live history/form
# state is a defense-in-depth guarantee for user-driven exit, background fail-close,
# security failure and lifetime expiry paths that converge on clearProtectedSessionState().
# Match the semantic statement rather than indentation so this patch remains stable after
# formatting-only changes in earlier patches.
pattern = re.compile(r'(?P<indent>^[ \t]*)web\.clearSslPreferences\(\);', re.MULTILINE)
matches = list(pattern.finditer(s))
if not matches:
    raise SystemExit("patch failed [protected residue cleanup anchor]: clearSslPreferences not found")
if len(matches) > 1:
    # Prefer the occurrence inside clearProtectedSessionState().
    method_pos = s.find('clearProtectedSessionState()')
    chosen = None
    if method_pos >= 0:
        for m in matches:
            if m.start() > method_pos and m.start() - method_pos < 5000:
                chosen = m
                break
    if chosen is None:
        raise SystemExit(f"patch failed [protected residue cleanup anchor]: ambiguous count {len(matches)}")
else:
    chosen = matches[0]
indent = chosen.group('indent')
cleanup = (
    f"{indent}web.clearSslPreferences();\n"
    f"{indent}web.clearHistory();\n"
    f"{indent}web.clearFormData();"
)
s = s[:chosen.start()] + cleanup + s[chosen.end():]

# Surface the cleanup contract in Compatibility so field testing can distinguish browser
# compatibility behavior from expected protected-session residue removal.
anchor = '        content.addView(cookieIsolationCard);'
if s.count(anchor) != 1:
    raise SystemExit(f"patch failed [compatibility residue cleanup anchor]: found {s.count(anchor)}")
card = '''        content.addView(cookieIsolationCard);

        LinearLayout residueCleanupCard = card();
        residueCleanupCard.addView(tv(t("Protected navigation cleanup", "پاک‌سازی پیمایش محافظت‌شده"), 16, NAVY, true));
        residueCleanupCard.addView(tv(t("History cleared • form state cleared on every protected-session close",
                "تاریخچه پاک می‌شود • وضعیت فرم در هر پایان نشست محافظت‌شده پاک می‌شود"), 13, GOOD, true));
        residueCleanupCard.addView(tv(t("SafePay and Secure Browser discard in-session navigation and form residue before the WebView is destroyed.",
                "SafePay و مرورگر امن پیش از حذف WebView، تاریخچه پیمایش و وضعیت فرم همان نشست را پاک می‌کنند."), 12, MUTED, false));
        content.addView(residueCleanupCard);'''
s = s.replace(anchor, card, 1)

s = s.replace('0.11.5 ALPHA', '0.11.6 ALPHA')
s = s.replace('0.11.5 Alpha • versionCode 1105', '0.11.6 Alpha • versionCode 1106')
s = s.replace('0.11.5 Alpha', '0.11.6 Alpha')
s = s.replace('VARA 0.11.5 requires Android 8.0 / API 26 or newer.', 'VARA 0.11.6 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+1105\b', 'versionCode 1106', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.11\.5-alpha['\"]", "versionName '0.11.6-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

for marker in [
    'web.clearHistory()',
    'web.clearFormData()',
    'Protected navigation cleanup',
    'History cleared',
    '0.11.6 ALPHA',
]:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.11.6 protected navigation and form-state cleanup patch applied")
