from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_054.py <android-project-root>")

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

# Keep the protected-session chrome synchronized with the actually committed host after redirects/navigation.
rep(
    '''            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                if (!request.isForMainFrame()) return false;
                Uri u = request.getUrl();
                String validated = normalizeHttps(u == null ? null : u.toString());
                if (validated == null) {
                    Toast.makeText(MainActivity.this, t("Blocked unsafe browser destination", "مقصد ناامن مرورگر مسدود شد"), Toast.LENGTH_SHORT).show();
                    return true;
                }
                return false;
            }''',
    '''            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                if (!request.isForMainFrame()) return false;
                Uri u = request.getUrl();
                String validated = normalizeHttps(u == null ? null : u.toString());
                if (validated == null) {
                    Toast.makeText(MainActivity.this, t("Blocked unsafe browser destination", "مقصد ناامن مرورگر مسدود شد"), Toast.LENGTH_SHORT).show();
                    return true;
                }
                return false;
            }
            @Override public void onPageCommitVisible(WebView view, String url) {
                try {
                    Uri committed = Uri.parse(url);
                    String host = committed.getHost();
                    title.setText(host == null ? t("Protected HTTPS session", "نشست محافظت‌شده HTTPS") : t("Protected • " + host, "محافظت‌شده • " + host));
                } catch (Exception ignored) {
                    title.setText(t("Protected HTTPS session", "نشست محافظت‌شده HTTPS"));
                }
            }''',
    "dynamic committed-host indicator",
)

# Protected sessions are navigation-only: downloads are intentionally blocked to avoid handing content
# to external apps or persistent storage without an explicit, separately reviewed flow.
rep(
    '''        if (android.os.Build.VERSION.SDK_INT >= 26) WebView.startSafeBrowsing(this, value -> {
            if (!value) Toast.makeText(MainActivity.this, t("Safe Browsing service unavailable", "سرویس Safe Browsing در دسترس نیست"), Toast.LENGTH_SHORT).show();
        });''',
    '''        web.setDownloadListener((url, userAgent, contentDisposition, mimeType, contentLength) -> {
            String event = t("Secure Browser blocked a download request", "مرورگر امن یک درخواست دانلود را مسدود کرد");
            prefs.edit().putString("last_activity", event)
                    .putString("last_activity_time", DateFormat.getDateTimeInstance(DateFormat.SHORT, DateFormat.SHORT).format(new Date())).apply();
            Toast.makeText(MainActivity.this, t("Downloads are disabled in protected sessions", "دانلود در نشست‌های محافظت‌شده غیرفعال است"), Toast.LENGTH_LONG).show();
        });
        if (android.os.Build.VERSION.SDK_INT >= 26) WebView.startSafeBrowsing(this, value -> {
            if (!value) Toast.makeText(MainActivity.this, t("Safe Browsing service unavailable", "سرویس Safe Browsing در دسترس نیست"), Toast.LENGTH_SHORT).show();
        });''',
    "protected-session download blocking",
)

# Make Safe Browsing enforcement explicit in WebSettings on supported Android versions.
rep(
    '        ws.setCacheMode(WebSettings.LOAD_NO_CACHE);',
    '        ws.setCacheMode(WebSettings.LOAD_NO_CACHE);\n        if (android.os.Build.VERSION.SDK_INT >= 26) ws.setSafeBrowsingEnabled(true);',
    "explicit safe browsing setting",
)

# Keep the protection disclosure aligned with the enforced download policy.
rep(
    '• Safe Browsing threats fail closed", "• فقط پیمایش HTTPS\\n• خطای TLS باعث توقف اتصال می‌شود\\n• ترافیک بدون رمزنگاری غیرفعال است\\n• دسترسی فایل و محتوا بسته است\\n• محتوای ترکیبی مسدود است\\n• درخواست دوربین، میکروفن و موقعیت وب رد می‌شود\\n• تهدیدهای Safe Browsing به‌صورت مسدودشونده مدیریت می‌شوند")',
    '• Safe Browsing threats fail closed\\n• Downloads blocked in protected sessions", "• فقط پیمایش HTTPS\\n• خطای TLS باعث توقف اتصال می‌شود\\n• ترافیک بدون رمزنگاری غیرفعال است\\n• دسترسی فایل و محتوا بسته است\\n• محتوای ترکیبی مسدود است\\n• درخواست دوربین، میکروفن و موقعیت وب رد می‌شود\\n• تهدیدهای Safe Browsing به‌صورت مسدودشونده مدیریت می‌شوند\\n• دانلود در نشست‌های محافظت‌شده مسدود است")',
    "download policy disclosure",
)

# Version metadata.
s = s.replace('0.5.3 ALPHA', '0.5.4 ALPHA')
s = s.replace('0.5.3 Alpha • versionCode 503', '0.5.4 Alpha • versionCode 504')
s = s.replace('0.5.3 Alpha', '0.5.4 Alpha')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+503\b', 'versionCode 504', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.5\.3-alpha['\"]", "versionName '0.5.4-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'onPageCommitVisible',
    'title.setText(host == null',
    'setDownloadListener',
    'Downloads are disabled in protected sessions',
    'setSafeBrowsingEnabled(true)',
    'Downloads blocked in protected sessions',
    '0.5.4 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.5.4 committed-host and protected-download hardening patch applied")
