from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_113.py <android-project-root>")

root = Path(sys.argv[1])
java = root / "app/src/main/java/com/varasecurity/alpha031/MainActivity.java"
gradle = root / "app/build.gradle"
s = java.read_text(encoding="utf-8")

required = [
    '0.11.2 ALPHA',
    'activeNetworkValidated()',
    'WebSettings.MIXED_CONTENT_NEVER_ALLOW',
    'ws.setAllowFileAccess(false)',
    'ws.setAllowContentAccess(false)',
    'protectedSessionPreflightReady()',
]
for marker in required:
    if marker not in s:
        raise SystemExit(f"missing validated 0.11.2 prerequisite: {marker}")

# 0.11.3: tighten the protected WebView's local-origin and window-creation surface.
# Banking/payment pages retain JavaScript and DOM storage compatibility, while
# file-origin cross-origin access, automatic JS windows, background media autoplay and
# reusable HTTP cache state are explicitly disabled for every protected session.
pattern = re.compile(
    r"\s*ws\.setJavaScriptEnabled\(true\);\s*"
    r"ws\.setDomStorageEnabled\(true\);\s*"
    r"ws\.setAllowFileAccess\(false\);\s*"
    r"ws\.setAllowContentAccess\(false\);\s*"
    r"ws\.setMixedContentMode\(WebSettings\.MIXED_CONTENT_NEVER_ALLOW\);\s*"
    r"ws\.setSaveFormData\(false\);\s*"
    r"ws\.setDatabaseEnabled\(false\);"
)
matches = list(pattern.finditer(s))
if len(matches) != 1:
    raise SystemExit(f"patch failed [protected WebSettings baseline]: found {len(matches)}")
new = '''
        ws.setJavaScriptEnabled(true);
        ws.setDomStorageEnabled(true);
        ws.setAllowFileAccess(false);
        ws.setAllowContentAccess(false);
        ws.setAllowFileAccessFromFileURLs(false);
        ws.setAllowUniversalAccessFromFileURLs(false);
        ws.setJavaScriptCanOpenWindowsAutomatically(false);
        ws.setSupportMultipleWindows(false);
        ws.setMediaPlaybackRequiresUserGesture(true);
        ws.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        ws.setSaveFormData(false);
        ws.setDatabaseEnabled(false);
        ws.setCacheMode(WebSettings.LOAD_NO_CACHE);'''
s = pattern.sub(new, s, count=1)

# Document the hardened WebView contract in Compatibility so runtime behavior is visible.
anchor = '        LinearLayout validatedNetworkCard = card();'
if s.count(anchor) != 1:
    raise SystemExit(f"patch failed [compatibility webview policy anchor]: found {s.count(anchor)}")
card = '''        LinearLayout webViewIsolationCard = card();
        webViewIsolationCard.addView(tv(t("Protected WebView isolation", "جداسازی WebView محافظت‌شده"), 16, NAVY, true));
        webViewIsolationCard.addView(tv(t("File-origin access blocked • automatic JavaScript windows blocked • multiple windows disabled • media requires user gesture • no reusable HTTP cache",
                "دسترسی مبدأ فایل مسدود • پنجره خودکار JavaScript مسدود • چندپنجره‌ای غیرفعال • پخش رسانه نیازمند اقدام کاربر • بدون کش HTTP قابل استفاده مجدد"), 13, GOOD, true));
        webViewIsolationCard.addView(tv(t("JavaScript remains enabled for banking compatibility, but protected sessions keep local-origin bridging and background window creation disabled.",
                "JavaScript برای سازگاری بانکی فعال می‌ماند، اما اتصال مبدأ محلی و ایجاد پنجره در پس‌زمینه در نشست محافظت‌شده غیرفعال است."), 12, MUTED, false));
        content.addView(webViewIsolationCard);

'''
s = s.replace(anchor, card + anchor, 1)

s = s.replace('0.11.2 ALPHA', '0.11.3 ALPHA')
s = s.replace('0.11.2 Alpha • versionCode 1102', '0.11.3 Alpha • versionCode 1103')
s = s.replace('0.11.2 Alpha', '0.11.3 Alpha')
s = s.replace('VARA 0.11.2 requires Android 8.0 / API 26 or newer.', 'VARA 0.11.3 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+1102\b', 'versionCode 1103', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.11\.2-alpha['\"]", "versionName '0.11.3-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'setAllowFileAccessFromFileURLs(false)',
    'setAllowUniversalAccessFromFileURLs(false)',
    'setJavaScriptCanOpenWindowsAutomatically(false)',
    'setSupportMultipleWindows(false)',
    'setMediaPlaybackRequiresUserGesture(true)',
    'setCacheMode(WebSettings.LOAD_NO_CACHE)',
    'Protected WebView isolation',
    'JavaScript remains enabled for banking compatibility',
    '0.11.3 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.11.3 protected WebView isolation patch applied")
