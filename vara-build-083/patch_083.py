from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_083.py <android-project-root>")

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

# 0.8.3: a protected SafePay/Secure Browser session must not survive when
# VARA leaves the foreground. Destroy the active WebView and clear its transient
# session state on pause, then return to Home when the app resumes. This avoids
# resuming a stale payment/authentication page after app switching or screen-off.
rep(
    '    private String lastSecureUrl = "https://www.google.com";',
    '''    private String lastSecureUrl = "https://www.google.com";
    private WebView activeProtectedWebView;
    private boolean protectedSessionActive = false;
    private boolean protectedSessionLaunchAllowed = false;
    private boolean returnHomeAfterProtectedPause = false;''',
    "protected session lifecycle state",
)

lifecycle_helpers = r'''
    private void clearProtectedSessionRuntime() {
        WebView web = activeProtectedWebView;
        activeProtectedWebView = null;
        protectedSessionActive = false;
        protectedSessionLaunchAllowed = false;
        if (web != null) {
            try { web.stopLoading(); } catch (Exception ignored) {}
            try { web.clearHistory(); } catch (Exception ignored) {}
            try { web.clearFormData(); } catch (Exception ignored) {}
            try { web.destroy(); } catch (Exception ignored) {}
        }
        try {
            android.webkit.CookieManager cm = android.webkit.CookieManager.getInstance();
            cm.removeSessionCookies(null);
            cm.flush();
        } catch (Exception ignored) {}
        try { android.webkit.WebStorage.getInstance().deleteAllData(); } catch (Exception ignored) {}
    }

    @Override
    protected void onPause() {
        if (protectedSessionActive && !isChangingConfigurations()) {
            String event = t("Protected session closed when VARA left the foreground",
                    "نشست محافظت‌شده با خروج VARA از حالت فعال بسته شد");
            recordActivity(event);
            returnHomeAfterProtectedPause = true;
            clearProtectedSessionRuntime();
        }
        super.onPause();
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (returnHomeAfterProtectedPause) {
            returnHomeAfterProtectedPause = false;
            renderHome();
            Toast.makeText(this,
                    t("Protected session was closed for safety", "نشست محافظت‌شده برای حفظ ایمنی بسته شد"),
                    Toast.LENGTH_LONG).show();
        }
    }

'''
rep(
    '    private String t(String en, String faText) { return fa ? faText : en; }',
    lifecycle_helpers + '    private String t(String en, String faText) { return fa ? faText : en; }',
    "protected session lifecycle helpers",
)

# Register the WebView before Safe Browsing initialization. The callback checks
# that the same launch is still authorized so an asynchronous callback cannot
# resurrect a session that was already closed while the app went to background.
rep(
    '        WebView.startSafeBrowsing(this, value -> {\n            if (!value) {',
    '''        activeProtectedWebView = web;
        protectedSessionActive = true;
        protectedSessionLaunchAllowed = true;
        WebView.startSafeBrowsing(this, value -> {
            if (!protectedSessionLaunchAllowed || activeProtectedWebView != web) {
                try { web.stopLoading(); web.destroy(); } catch (Exception ignored) {}
                return;
            }
            if (!value) {''',
    "protected session async launch guard",
)

# Ensure ordinary navigation to Home also destroys any surviving protected
# runtime instead of merely detaching its view hierarchy.
rep(
    '    private void renderHome() {\n        currentPage = "home";',
    '''    private void renderHome() {
        if (protectedSessionActive || activeProtectedWebView != null) clearProtectedSessionRuntime();
        currentPage = "home";''',
    "home protected session cleanup",
)

# Make the lifecycle contract visible in Device Compatibility.
rep(
    '        content.addView(autofillExposure);',
    '''        content.addView(autofillExposure);

        LinearLayout backgroundIsolation = card();
        backgroundIsolation.addView(tv(t("Protected-session background policy", "سیاست پس‌زمینه نشست محافظت‌شده"), 16, NAVY, true));
        backgroundIsolation.addView(tv(t("Fail-closed • leaving VARA closes the active SafePay/Secure Browser session", "بسته‌شدن امن • خروج از VARA نشست فعال SafePay/Secure Browser را می‌بندد"), 13, GOOD, true));
        backgroundIsolation.addView(tv(t("The active WebView is destroyed and transient cookie/WebStorage state is cleared before a new protected session can start.",
                "WebView فعال از بین می‌رود و وضعیت موقت Cookie/WebStorage پیش از شروع نشست محافظت‌شده جدید پاک می‌شود."), 12, MUTED, false));
        content.addView(backgroundIsolation);''',
    "compatibility background isolation card",
)

# Version metadata.
s = s.replace('0.8.2 ALPHA', '0.8.3 ALPHA')
s = s.replace('0.8.2 Alpha • versionCode 802', '0.8.3 Alpha • versionCode 803')
s = s.replace('0.8.2 Alpha', '0.8.3 Alpha')
s = s.replace('VARA 0.8.2 requires Android 8.0 / API 26 or newer.', 'VARA 0.8.3 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+802\b', 'versionCode 803', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.8\.2-alpha['\"]", "versionName '0.8.3-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'protectedSessionLaunchAllowed',
    'Protected session closed when VARA left the foreground',
    'clearProtectedSessionRuntime()',
    'activeProtectedWebView != web',
    'Protected-session background policy',
    '0.8.3 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.8.3 protected-session background fail-closed patch applied")
