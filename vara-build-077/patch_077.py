from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_077.py <android-project-root>")

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

# Fail closed on main-frame WebView transport failures so a protected session
# cannot remain on a partially loaded or stale sensitive page.
rep(
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
            @Override public boolean onRenderProcessGone(WebView view, android.webkit.RenderProcessGoneDetail detail) {''',
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
            @Override public void onReceivedError(WebView view, android.webkit.WebResourceRequest request, android.webkit.WebResourceError error) {
                if (request == null || !request.isForMainFrame()) return;
                try { if (view != null) view.stopLoading(); } catch (Exception ignored) {}
                String host = "unknown";
                try {
                    Uri failed = request.getUrl();
                    if (failed != null && failed.getHost() != null) host = failed.getHost();
                } catch (Exception ignored) {}
                String event = t("Protected session closed after a network failure for " + host,
                        "نشست محافظت‌شده پس از خطای شبکه برای " + host + " بسته شد");
                prefs.edit().putString("last_activity", event)
                        .putString("last_activity_time", DateFormat.getDateTimeInstance(DateFormat.SHORT, DateFormat.SHORT).format(new Date())).apply();
                Toast.makeText(MainActivity.this,
                        t("Network error — protected session closed", "خطای شبکه — نشست محافظت‌شده بسته شد"),
                        Toast.LENGTH_LONG).show();
                renderHome();
            }
            @Override public boolean onRenderProcessGone(WebView view, android.webkit.RenderProcessGoneDetail detail) {''',
    "main-frame network failure fail-closed handling",
)

# Keep compatibility/disclosure copy aligned with the new runtime behavior.
rep(
    'TLS and renderer failures close the session safely", "• فقط پیمایش HTTPS',
    'TLS, renderer and main-frame network failures close the session safely", "• فقط پیمایش HTTPS',
    "english protected-session failure disclosure",
)
rep(
    '• خطای TLS یا فرآیند مرورگر نشست را به‌صورت امن می‌بندد")',
    '• خطای TLS، فرآیند مرورگر یا خطای شبکه صفحه اصلی نشست را به‌صورت امن می‌بندد")',
    "persian protected-session failure disclosure",
)

# Version metadata.
s = s.replace('0.7.6 ALPHA', '0.7.7 ALPHA')
s = s.replace('0.7.6 Alpha • versionCode 706', '0.7.7 Alpha • versionCode 707')
s = s.replace('0.7.6 Alpha', '0.7.7 Alpha')
s = s.replace('VARA 0.7.6 requires Android 8.0 / API 26 or newer.', 'VARA 0.7.7 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+706\b', 'versionCode 707', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.7\.6-alpha['\"]", "versionName '0.7.7-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'onReceivedError(WebView view, android.webkit.WebResourceRequest request, android.webkit.WebResourceError error)',
    'request.isForMainFrame()',
    'Network error — protected session closed',
    'Protected session closed after a network failure for',
    'TLS, renderer and main-frame network failures close the session safely',
    '0.7.7 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.7.7 protected-session network-failure hardening patch applied")
