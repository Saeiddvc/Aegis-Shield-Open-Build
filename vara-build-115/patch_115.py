from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_115.py <android-project-root>")

root = Path(sys.argv[1])
java = root / "app/src/main/java/com/varasecurity/alpha031/MainActivity.java"
gradle = root / "app/build.gradle"
s = java.read_text(encoding="utf-8")

for marker in [
    '0.11.4 ALPHA',
    'setCacheMode(WebSettings.LOAD_NO_CACHE)',
    'Protected session cleanup',
    'CookieManager',
    'clearProtectedSessionState()',
]:
    if marker not in s:
        raise SystemExit(f"missing validated 0.11.4 prerequisite: {marker}")

# 0.11.5: keep first-party cookies available for normal banking authentication while
# blocking third-party cookie state inside every protected WebView. This reduces
# cross-site session/tracking state without weakening the existing per-session cleanup.
anchor = '        ws.setCacheMode(WebSettings.LOAD_NO_CACHE);'
if s.count(anchor) != 1:
    raise SystemExit(f"patch failed [protected cookie policy anchor]: found {s.count(anchor)}")
cookie_policy = '''        ws.setCacheMode(WebSettings.LOAD_NO_CACHE);\n        try {\n            CookieManager protectedCookies = CookieManager.getInstance();\n            protectedCookies.setAcceptCookie(true);\n            protectedCookies.setAcceptThirdPartyCookies(web, false);\n        } catch (Exception ignored) {}'''
s = s.replace(anchor, cookie_policy, 1)

# Make the policy visible so a compatibility issue can be distinguished from a network
# or device-readiness failure during field testing.
anchor = '        content.addView(sessionCleanupCard);'
if s.count(anchor) != 1:
    raise SystemExit(f"patch failed [compatibility cookie policy anchor]: found {s.count(anchor)}")
card = '''        content.addView(sessionCleanupCard);\n\n        LinearLayout cookieIsolationCard = card();\n        cookieIsolationCard.addView(tv(t("Protected cookie isolation", "جداسازی کوکی در نشست محافظت‌شده"), 16, NAVY, true));\n        cookieIsolationCard.addView(tv(t("First-party cookies allowed • third-party cookies blocked",\n                "کوکی‌های دامنه اصلی مجاز • کوکی‌های شخص ثالث مسدود"), 13, GOOD, true));\n        cookieIsolationCard.addView(tv(t("Bank sign-in state can work on the committed destination while cross-site cookie state is not accepted by the protected WebView.",\n                "وضعیت ورود بانکی روی مقصد تأییدشده قابل استفاده است، اما WebView محافظت‌شده کوکی شخص ثالث را نمی‌پذیرد."), 12, MUTED, false));\n        content.addView(cookieIsolationCard);'''
s = s.replace(anchor, card, 1)

s = s.replace('0.11.4 ALPHA', '0.11.5 ALPHA')
s = s.replace('0.11.4 Alpha • versionCode 1104', '0.11.5 Alpha • versionCode 1105')
s = s.replace('0.11.4 Alpha', '0.11.5 Alpha')
s = s.replace('VARA 0.11.4 requires Android 8.0 / API 26 or newer.', 'VARA 0.11.5 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+1104\b', 'versionCode 1105', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.11\.4-alpha['\"]", "versionName '0.11.5-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

for marker in [
    'setAcceptCookie(true)',
    'setAcceptThirdPartyCookies(web, false)',
    'Protected cookie isolation',
    'First-party cookies allowed',
    '0.11.5 ALPHA',
]:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.11.5 protected first-party cookie isolation patch applied")
