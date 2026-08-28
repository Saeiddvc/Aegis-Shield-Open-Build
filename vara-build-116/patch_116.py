from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_116.py <android-project-root>")

root = Path(sys.argv[1])
java = root / "app/src/main/java/com/varasecurity/alpha031/MainActivity.java"
gradle = root / "app/build.gradle"
s = java.read_text(encoding="utf-8")

# 0.11.4 already introduced history/form/cache/SSL cleanup on the protected WebView
# destruction path. 0.11.6 promotes that behavior to an explicitly validated contract
# rather than mutating the same cleanup block a second time.
for marker in [
    '0.11.5 ALPHA',
    'setAcceptThirdPartyCookies(web, false)',
    'Protected cookie isolation',
    'web.clearHistory()',
    'web.clearFormData()',
    'web.clearCache(true)',
    'web.clearSslPreferences()',
    'clearProtectedSessionRuntime()',
]:
    if marker not in s:
        raise SystemExit(f"missing validated 0.11.5 prerequisite: {marker}")

# Require all residue-removal calls to coexist on the protected WebView teardown path.
# The validated 0.11.4 source uses guarded try/catch calls before web.destroy().
teardown = re.compile(
    r'try\s*\{\s*web\.stopLoading\(\);\s*\}\s*catch\s*\(Exception ignored\)\s*\{\s*\}\s*'
    r'try\s*\{\s*web\.clearHistory\(\);\s*\}\s*catch\s*\(Exception ignored\)\s*\{\s*\}\s*'
    r'try\s*\{\s*web\.clearFormData\(\);\s*\}\s*catch\s*\(Exception ignored\)\s*\{\s*\}\s*'
    r'try\s*\{\s*web\.clearCache\(true\);\s*\}\s*catch\s*\(Exception ignored\)\s*\{\s*\}\s*'
    r'try\s*\{\s*web\.clearSslPreferences\(\);\s*\}\s*catch\s*\(Exception ignored\)\s*\{\s*\}\s*'
    r'try\s*\{\s*web\.destroy\(\);\s*\}\s*catch\s*\(Exception ignored\)\s*\{\s*\}'
)
if len(list(teardown.finditer(s))) != 1:
    raise SystemExit("patch failed [protected teardown contract]: expected exactly one validated cleanup chain")

anchor = '        content.addView(cookieIsolationCard);'
if s.count(anchor) != 1:
    raise SystemExit(f"patch failed [compatibility residue cleanup anchor]: found {s.count(anchor)}")
card = '''        content.addView(cookieIsolationCard);

        LinearLayout residueCleanupCard = card();
        residueCleanupCard.addView(tv(t("Protected navigation cleanup", "پاک‌سازی پیمایش محافظت‌شده"), 16, NAVY, true));
        residueCleanupCard.addView(tv(t("History cleared • form state cleared • HTTP cache cleared • SSL preferences cleared",
                "تاریخچه پاک می‌شود • وضعیت فرم پاک می‌شود • کش HTTP پاک می‌شود • تنظیمات SSL پاک می‌شود"), 13, GOOD, true));
        residueCleanupCard.addView(tv(t("SafePay and Secure Browser validate the full protected WebView teardown chain before release builds are accepted.",
                "SafePay و مرورگر امن در نسخه‌های انتشار، زنجیره کامل پاک‌سازی WebView محافظت‌شده را پیش از پذیرش ساخت اعتبارسنجی می‌کنند."), 12, MUTED, false));
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
    'web.clearCache(true)',
    'web.clearSslPreferences()',
    'Protected navigation cleanup',
    'History cleared',
    '0.11.6 ALPHA',
]:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.11.6 protected teardown contract validated")
