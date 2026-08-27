from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_073.py <android-project-root>")

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

# Strengthen protected-session isolation. Session cookies were already cleared between sessions;
# also clear WebStorage (localStorage/sessionStorage/IndexedDB) so sensitive browser state does not
# persist from one protected session into the next.
rep(
    '''    private void clearProtectedSessionState() {
        try {
            CookieManager cookies = CookieManager.getInstance();
            cookies.removeSessionCookies(null);
            cookies.flush();
        } catch (Exception ignored) {}
    }
''',
    '''    private void clearProtectedSessionState() {
        try {
            CookieManager cookies = CookieManager.getInstance();
            cookies.removeSessionCookies(null);
            cookies.flush();
        } catch (Exception ignored) {}
        try {
            android.webkit.WebStorage.getInstance().deleteAllData();
        } catch (Exception ignored) {}
    }
''',
    "protected web storage isolation",
)

# Make the isolation contract visible in Compatibility so users understand what protected mode
# deliberately forgets between launches.
rep(
    '''        protectedReady.addView(tv((!adbEnabled() ? "✓ " : "• ") + t("USB debugging disabled", "اشکال‌زدایی USB غیرفعال"), 12, !adbEnabled() ? GOOD : WARN, true));
        content.addView(protectedReady);''',
    '''        protectedReady.addView(tv((!adbEnabled() ? "✓ " : "• ") + t("USB debugging disabled", "اشکال‌زدایی USB غیرفعال"), 12, !adbEnabled() ? GOOD : WARN, true));
        protectedReady.addView(tv(t("Protected storage isolation", "جداسازی فضای ذخیره‌سازی محافظت‌شده"), 13, NAVY, true));
        protectedReady.addView(tv(t("Session cookies and WebView site storage are cleared between protected sessions.",
                "کوکی‌های نشست و فضای ذخیره‌سازی سایت در WebView بین نشست‌های محافظت‌شده پاک می‌شوند."), 12, MUTED, false));
        content.addView(protectedReady);''',
    "compatibility storage isolation disclosure",
)

# Keep the SafePay disclosure aligned with the actual cleanup behavior.
rep(
    '• Session cookies are cleared between protected sessions',
    '• Session cookies and WebView site storage are cleared between protected sessions',
    "english protected storage disclosure",
)
rep(
    '• کوکی‌های نشست بین نشست‌های محافظت‌شده پاک می‌شوند',
    '• کوکی‌های نشست و فضای ذخیره‌سازی سایت در WebView بین نشست‌های محافظت‌شده پاک می‌شوند',
    "persian protected storage disclosure",
)

# Version metadata.
s = s.replace('0.7.2 ALPHA', '0.7.3 ALPHA')
s = s.replace('0.7.2 Alpha • versionCode 702', '0.7.3 Alpha • versionCode 703')
s = s.replace('0.7.2 Alpha', '0.7.3 Alpha')
s = s.replace('VARA 0.7.2 requires Android 8.0 / API 26 or newer.', 'VARA 0.7.3 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+702\b', 'versionCode 703', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.7\.2-alpha['\"]", "versionName '0.7.3-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'WebStorage.getInstance().deleteAllData()',
    'Protected storage isolation',
    'Session cookies and WebView site storage are cleared between protected sessions',
    '0.7.3 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.7.3 protected WebStorage isolation patch applied")
