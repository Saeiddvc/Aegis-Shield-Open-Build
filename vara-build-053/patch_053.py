from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_053.py <android-project-root>")

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

# Fail closed when Android WebView Safe Browsing identifies a malicious or unwanted destination.
rep(
    '''            @Override public void onReceivedSslError(WebView view, SslErrorHandler handler, SslError error) {
                handler.cancel(); Toast.makeText(MainActivity.this, t("TLS certificate error — connection blocked", "خطای گواهی TLS — اتصال مسدود شد"), Toast.LENGTH_LONG).show();
            }
        });
        if (android.os.Build.VERSION.SDK_INT >= 26) WebView.startSafeBrowsing(this, value -> {});''',
    '''            @Override public void onSafeBrowsingHit(WebView view, WebResourceRequest request, int threatType, android.webkit.SafeBrowsingResponse response) {
                response.backToSafety(true);
                String event = t("Secure Browser blocked a Safe Browsing threat", "مرورگر امن یک تهدید Safe Browsing را مسدود کرد");
                prefs.edit().putString("last_activity", event)
                        .putString("last_activity_time", DateFormat.getDateTimeInstance(DateFormat.SHORT, DateFormat.SHORT).format(new Date())).apply();
                Toast.makeText(MainActivity.this, t("Unsafe page blocked", "صفحه ناامن مسدود شد"), Toast.LENGTH_LONG).show();
            }
            @Override public void onReceivedSslError(WebView view, SslErrorHandler handler, SslError error) {
                handler.cancel(); Toast.makeText(MainActivity.this, t("TLS certificate error — connection blocked", "خطای گواهی TLS — اتصال مسدود شد"), Toast.LENGTH_LONG).show();
            }
        });
        web.setWebChromeClient(new android.webkit.WebChromeClient() {
            @Override public void onPermissionRequest(android.webkit.PermissionRequest request) {
                if (request != null) request.deny();
            }
            @Override public void onGeolocationPermissionsShowPrompt(String origin, android.webkit.GeolocationPermissions.Callback callback) {
                if (callback != null) callback.invoke(origin, false, false);
            }
        });
        if (android.os.Build.VERSION.SDK_INT >= 26) WebView.startSafeBrowsing(this, value -> {
            if (!value) Toast.makeText(MainActivity.this, t("Safe Browsing service unavailable", "سرویس Safe Browsing در دسترس نیست"), Toast.LENGTH_SHORT).show();
        });''',
    "fail-closed safe browsing and web permission policy",
)

# Make the protected-session explanation match the enforced permission policy.
rep(
    '• Mixed content blocked", "• فقط پیمایش HTTPS\\n• خطای TLS باعث توقف اتصال می‌شود\\n• ترافیک بدون رمزنگاری غیرفعال است\\n• دسترسی فایل و محتوا بسته است\\n• محتوای ترکیبی مسدود است")',
    '• Mixed content blocked\\n• Web camera, microphone and location requests denied\\n• Safe Browsing threats fail closed", "• فقط پیمایش HTTPS\\n• خطای TLS باعث توقف اتصال می‌شود\\n• ترافیک بدون رمزنگاری غیرفعال است\\n• دسترسی فایل و محتوا بسته است\\n• محتوای ترکیبی مسدود است\\n• درخواست دوربین، میکروفن و موقعیت وب رد می‌شود\\n• تهدیدهای Safe Browsing به‌صورت مسدودشونده مدیریت می‌شوند")',
    "safepay protection disclosure",
)

# Version metadata.
s = s.replace('0.5.2 ALPHA', '0.5.3 ALPHA')
s = s.replace('0.5.2 Alpha • versionCode 502', '0.5.3 Alpha • versionCode 503')
s = s.replace('0.5.2 Alpha', '0.5.3 Alpha')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+502\b', 'versionCode 503', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.5\.2-alpha['\"]", "versionName '0.5.3-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'onSafeBrowsingHit',
    'response.backToSafety(true)',
    'onPermissionRequest',
    'request.deny()',
    'onGeolocationPermissionsShowPrompt',
    'callback.invoke(origin, false, false)',
    'Safe Browsing threats fail closed',
    '0.5.3 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.5.3 Safe Browsing and web-permission hardening patch applied")
