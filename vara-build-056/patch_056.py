from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_056.py <android-project-root>")

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

# Make TLS failures auditable and handle a WebView renderer crash as a fail-closed protected-session event.
rep(
    '''            @Override public void onReceivedSslError(WebView view, SslErrorHandler handler, SslError error) {
                handler.cancel(); Toast.makeText(MainActivity.this, t("TLS certificate error — connection blocked", "خطای گواهی TLS — اتصال مسدود شد"), Toast.LENGTH_LONG).show();
            }''',
    '''            @Override public void onReceivedSslError(WebView view, SslErrorHandler handler, SslError error) {
                handler.cancel();
                String host = "unknown";
                try {
                    Uri failed = error == null ? null : Uri.parse(error.getUrl());
                    if (failed != null && failed.getHost() != null) host = failed.getHost();
                } catch (Exception ignored) {}
                String event = t("Secure Browser blocked a TLS certificate error for " + host, "مرورگر امن خطای گواهی TLS برای " + host + " را مسدود کرد");
                prefs.edit().putString("last_activity", event)
                        .putString("last_activity_time", DateFormat.getDateTimeInstance(DateFormat.SHORT, DateFormat.SHORT).format(new Date())).apply();
                Toast.makeText(MainActivity.this, t("TLS certificate error — connection blocked", "خطای گواهی TLS — اتصال مسدود شد"), Toast.LENGTH_LONG).show();
            }
            @Override public boolean onRenderProcessGone(WebView view, android.webkit.RenderProcessGoneDetail detail) {
                String event = t("Protected browser process ended — session closed", "فرآیند مرورگر محافظت‌شده متوقف شد — نشست بسته شد");
                prefs.edit().putString("last_activity", event)
                        .putString("last_activity_time", DateFormat.getDateTimeInstance(DateFormat.SHORT, DateFormat.SHORT).format(new Date())).apply();
                try {
                    if (view != null) {
                        android.view.ViewParent parent = view.getParent();
                        if (parent instanceof ViewGroup) ((ViewGroup) parent).removeView(view);
                        view.destroy();
                    }
                } catch (Exception ignored) {}
                Toast.makeText(MainActivity.this, t("Protected session closed safely", "نشست محافظت‌شده با ایمنی بسته شد"), Toast.LENGTH_LONG).show();
                renderHome();
                return true;
            }''',
    "tls audit and renderer fail-closed handling",
)

# Keep the protected-session disclosure aligned with renderer/TLS behavior.
rep(
    '• Downloads blocked in protected sessions", "• فقط پیمایش HTTPS\\n• خطای TLS باعث توقف اتصال می‌شود\\n• ترافیک بدون رمزنگاری غیرفعال است\\n• دسترسی فایل و محتوا بسته است\\n• محتوای ترکیبی مسدود است\\n• درخواست دوربین، میکروفن و موقعیت وب رد می‌شود\\n• تهدیدهای Safe Browsing به‌صورت مسدودشونده مدیریت می‌شوند\\n• دانلود در نشست‌های محافظت‌شده مسدود است")',
    '• Downloads blocked in protected sessions\\n• TLS and renderer failures close the session safely", "• فقط پیمایش HTTPS\\n• خطای TLS باعث توقف اتصال می‌شود\\n• ترافیک بدون رمزنگاری غیرفعال است\\n• دسترسی فایل و محتوا بسته است\\n• محتوای ترکیبی مسدود است\\n• درخواست دوربین، میکروفن و موقعیت وب رد می‌شود\\n• تهدیدهای Safe Browsing به‌صورت مسدودشونده مدیریت می‌شوند\\n• دانلود در نشست‌های محافظت‌شده مسدود است\\n• خطای TLS یا فرآیند مرورگر نشست را به‌صورت امن می‌بندد")',
    "protected-session failure disclosure",
)

# Version metadata.
s = s.replace('0.5.5 ALPHA', '0.5.6 ALPHA')
s = s.replace('0.5.5 Alpha • versionCode 505', '0.5.6 Alpha • versionCode 506')
s = s.replace('0.5.5 Alpha', '0.5.6 Alpha')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+505\b', 'versionCode 506', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.5\.5-alpha['\"]", "versionName '0.5.6-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'onRenderProcessGone',
    'Protected browser process ended',
    'Secure Browser blocked a TLS certificate error',
    'renderHome();',
    '0.5.6 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.5.6 TLS/renderer fail-closed patch applied")
