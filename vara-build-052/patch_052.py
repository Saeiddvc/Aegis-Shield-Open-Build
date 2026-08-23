from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_052.py <android-project-root>")

root = Path(sys.argv[1])
java = root / "app/src/main/java/com/varasecurity/alpha031/MainActivity.java"
gradle = root / "app/build.gradle"
s = java.read_text(encoding="utf-8")


def rep(old: str, new: str, label: str):
    global s
    count = s.count(old)
    if count != 1:
        raise SystemExit(f"patch failed [{label}]: expected 1 match, found {count}")
    s = s.replace(old, new, 1)

# Secure Browser: align the in-session navigation control with the cleaner app navigation.
rep(
    '        TextView back = tv(fa ? "›" : "‹", 34, NAVY, false); back.setGravity(Gravity.CENTER); back.setOnClickListener(v -> renderBrowserStart()); bar.addView(back, new LinearLayout.LayoutParams(dp(48), dp(48)));',
    '        TextView back = tv(fa ? "→" : "←", 22, NAVY, true); back.setGravity(Gravity.CENTER); back.setBackground(rounded(Color.rgb(245,248,250), 16)); back.setContentDescription(t("Back", "بازگشت")); back.setOnClickListener(v -> renderBrowserStart()); bar.addView(back, new LinearLayout.LayoutParams(dp(48), dp(48)));',
    "secure browser navigation polish",
)

# Defense in depth for the payment/browser WebView. Keep JavaScript for banking-site compatibility,
# but prevent script-created windows, geolocation, file-origin escalation, caching and remote debugging.
rep(
    '        ws.setJavaScriptEnabled(true); ws.setDomStorageEnabled(true); ws.setAllowFileAccess(false); ws.setAllowContentAccess(false); ws.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW); ws.setSaveFormData(false); ws.setDatabaseEnabled(false);',
    '''        WebView.setWebContentsDebuggingEnabled(false);
        ws.setJavaScriptEnabled(true);
        ws.setJavaScriptCanOpenWindowsAutomatically(false);
        ws.setSupportMultipleWindows(false);
        ws.setDomStorageEnabled(true);
        ws.setAllowFileAccess(false);
        ws.setAllowContentAccess(false);
        ws.setAllowFileAccessFromFileURLs(false);
        ws.setAllowUniversalAccessFromFileURLs(false);
        ws.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        ws.setSaveFormData(false);
        ws.setDatabaseEnabled(false);
        ws.setGeolocationEnabled(false);
        ws.setMediaPlaybackRequiresUserGesture(true);
        ws.setCacheMode(WebSettings.LOAD_NO_CACHE);''',
    "secure webview settings",
)

# Clear SSL decision state as part of every protected session, in addition to history/cache/form data.
rep(
    '        web.clearFormData(); web.clearHistory(); web.clearCache(false);',
    '        web.clearFormData(); web.clearHistory(); web.clearCache(true); web.clearSslPreferences();',
    "secure session state reset",
)

# Make the on-screen protection disclosure match the controls that are actually enforced.
rep(
    '• Mixed content blocked", "• فقط پیمایش HTTPS\\n• خطاهای TLS به‌صورت بسته مدیریت می‌شوند\\n• ترافیک بدون رمزنگاری غیرفعال است\\n• دسترسی فایل و محتوا بسته است\\n• محتوای ترکیبی مسدود است")',
    '• Mixed content blocked\\n• Browser debugging, geolocation and pop-up windows disabled", "• فقط پیمایش HTTPS\\n• خطاهای TLS به‌صورت بسته مدیریت می‌شوند\\n• ترافیک بدون رمزنگاری غیرفعال است\\n• دسترسی فایل و محتوا بسته است\\n• محتوای ترکیبی مسدود است\\n• دیباگ مرورگر، موقعیت مکانی و پنجره‌های بازشونده غیرفعال است")',
    "protection disclosure",
)

# Version metadata.
s = s.replace('0.5.1 ALPHA', '0.5.2 ALPHA')
s = s.replace('0.5.1 Alpha • versionCode 501', '0.5.2 Alpha • versionCode 502')
s = s.replace('0.5.1 Alpha', '0.5.2 Alpha')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+501\b', 'versionCode 502', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.5\.1-alpha['\"]", "versionName '0.5.2-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'WebView.setWebContentsDebuggingEnabled(false)',
    'setJavaScriptCanOpenWindowsAutomatically(false)',
    'setAllowUniversalAccessFromFileURLs(false)',
    'setGeolocationEnabled(false)',
    'setCacheMode(WebSettings.LOAD_NO_CACHE)',
    'clearSslPreferences()',
    '0.5.2 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.5.2 secure-session hardening patch applied")
