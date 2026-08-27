from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_065.py <android-project-root>")

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

# Protected-session privacy: clear session cookies when entering and leaving the hardened browser.
# Persistent cookies are intentionally left untouched; this avoids breaking deliberate remembered-login
# behavior while preventing one protected payment session from leaking session state into the next.
helper = r'''
    private void clearProtectedSessionState() {
        try {
            CookieManager cookies = CookieManager.getInstance();
            cookies.removeSessionCookies(null);
            cookies.flush();
        } catch (Exception ignored) {}
    }

'''
rep(
    '    private void navigateBack() {',
    helper + '    private void navigateBack() {',
    'protected session cookie cleanup helper',
)

rep(
    '''        if ("browser".equals(currentPage)) {
            renderBrowserStart();
            return;
        }''',
    '''        if ("browser".equals(currentPage)) {
            clearProtectedSessionState();
            renderBrowserStart();
            return;
        }''',
    'clear protected session state on exit',
)

rep(
    '''    private void openSecureBrowser(String initialUrl) {
        currentPage = "browser";
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_SECURE);''',
    '''    private void openSecureBrowser(String initialUrl) {
        currentPage = "browser";
        clearProtectedSessionState();
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_SECURE);''',
    'clear stale session cookies before protected launch',
)

# Defense in depth: a committed top-level URL must still satisfy the same protected-destination policy.
# shouldOverrideUrlLoading already blocks unsafe main-frame navigations; this second check covers
# unexpected WebView commit paths and ensures the visible host is derived only from a validated URL.
rep(
    '''            @Override public void onPageCommitVisible(WebView view, String url) {
                try {
                    Uri committed = Uri.parse(url);
                    String host = committed.getHost();
                    title.setText(host == null ? t("Protected HTTPS session", "نشست محافظت‌شده HTTPS") : t("Protected • " + host, "محافظت‌شده • " + host));
                } catch (Exception ignored) {
                    title.setText(t("Protected HTTPS session", "نشست محافظت‌شده HTTPS"));
                }
            }''',
    '''            @Override public void onPageCommitVisible(WebView view, String url) {
                String validated = normalizeHttps(url);
                if (validated == null) {
                    String event = t("Protected browser blocked an invalid committed destination",
                            "مرورگر محافظت‌شده یک مقصد نهایی نامعتبر را مسدود کرد");
                    recordActivity(event);
                    try { view.stopLoading(); view.setVisibility(View.GONE); } catch (Exception ignored) {}
                    Toast.makeText(MainActivity.this,
                            t("Unsafe destination blocked — session closed", "مقصد ناامن مسدود شد — نشست بسته شد"),
                            Toast.LENGTH_LONG).show();
                    clearProtectedSessionState();
                    renderBrowserStart();
                    return;
                }
                try {
                    Uri committed = Uri.parse(validated);
                    String host = committed.getHost();
                    title.setText(host == null ? t("Protected HTTPS session", "نشست محافظت‌شده HTTPS") : t("Protected • " + host, "محافظت‌شده • " + host));
                } catch (Exception ignored) {
                    title.setText(t("Protected HTTPS session", "نشست محافظت‌شده HTTPS"));
                }
            }''',
    'validate committed protected destination',
)

rep(
    '• Form resubmission is blocked to reduce accidental duplicate payment posts',
    '• Form resubmission is blocked to reduce accidental duplicate payment posts\\n• Session cookies are cleared between protected sessions',
    'english session isolation disclosure',
)
rep(
    '• ارسال مجدد فرم برای کاهش خطر ثبت تکراری پرداخت مسدود می‌شود',
    '• ارسال مجدد فرم برای کاهش خطر ثبت تکراری پرداخت مسدود می‌شود\\n• کوکی‌های نشست بین نشست‌های محافظت‌شده پاک می‌شوند',
    'persian session isolation disclosure',
)

# Version metadata.
s = s.replace('0.6.4 ALPHA', '0.6.5 ALPHA')
s = s.replace('0.6.4 Alpha • versionCode 604', '0.6.5 Alpha • versionCode 605')
s = s.replace('0.6.4 Alpha', '0.6.5 Alpha')
s = s.replace('VARA 0.6.4 requires Android 8.0 / API 26 or newer.', 'VARA 0.6.5 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+604\b', 'versionCode 605', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.6\.4-alpha['\"]", "versionName '0.6.5-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'clearProtectedSessionState()',
    'removeSessionCookies(null)',
    'Protected browser blocked an invalid committed destination',
    'Unsafe destination blocked — session closed',
    'Session cookies are cleared between protected sessions',
    '0.6.5 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.6.5 protected-session isolation and committed-destination validation patch applied")
