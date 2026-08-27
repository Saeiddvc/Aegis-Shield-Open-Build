from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_061.py <android-project-root>")

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

# Secure Browser / SafePay: never silently fall back to a generic site when the requested
# destination fails validation. An invalid initial target must fail closed and return the user
# to the protected-browser start screen.
rep(
    '        String safe = normalizeHttps(initialUrl);\n        final String launchUrl = safe == null ? "https://www.google.com" : safe;',
    '''        String safe = normalizeHttps(initialUrl);
        if (safe == null) {
            String event = t("Protected browser blocked: invalid HTTPS destination", "مرورگر محافظت‌شده مسدود شد: مقصد HTTPS نامعتبر است");
            recordActivity(event);
            try { web.stopLoading(); web.destroy(); } catch (Exception ignored) {}
            Toast.makeText(MainActivity.this, t("Enter a valid HTTPS destination", "یک مقصد HTTPS معتبر وارد کنید"), Toast.LENGTH_LONG).show();
            renderBrowserStart();
            return;
        }
        final String launchUrl = safe;''',
    "fail closed invalid launch destination",
)

# High-assurance payment/browser sessions should not start while ADB is exposed. Developer
# Options alone remain a review signal, but active USB debugging is treated as a blocking
# preflight condition because it materially increases the local attack surface.
secure_lock_block = '''        if (!isDeviceLockSecure()) {
            String event = t("Protected browser blocked: secure screen lock required", "مرورگر محافظت‌شده مسدود شد: قفل امن صفحه لازم است");
            recordActivity(event);
            try { web.stopLoading(); web.destroy(); } catch (Exception ignored) {}
            Toast.makeText(MainActivity.this, t("Enable a secure screen lock before SafePay or protected browsing", "پیش از SafePay یا مرور محافظت‌شده، قفل امن صفحه را فعال کنید"), Toast.LENGTH_LONG).show();
            openSettings(Settings.ACTION_SECURITY_SETTINGS);
            renderBrowserStart();
            return;
        }
        WebView.startSafeBrowsing(this, value -> {'''
secure_lock_and_adb = '''        if (!isDeviceLockSecure()) {
            String event = t("Protected browser blocked: secure screen lock required", "مرورگر محافظت‌شده مسدود شد: قفل امن صفحه لازم است");
            recordActivity(event);
            try { web.stopLoading(); web.destroy(); } catch (Exception ignored) {}
            Toast.makeText(MainActivity.this, t("Enable a secure screen lock before SafePay or protected browsing", "پیش از SafePay یا مرور محافظت‌شده، قفل امن صفحه را فعال کنید"), Toast.LENGTH_LONG).show();
            openSettings(Settings.ACTION_SECURITY_SETTINGS);
            renderBrowserStart();
            return;
        }
        if (adbEnabled()) {
            String event = t("Protected browser blocked: USB debugging is enabled", "مرورگر محافظت‌شده مسدود شد: اشکال‌زدایی USB فعال است");
            recordActivity(event);
            try { web.stopLoading(); web.destroy(); } catch (Exception ignored) {}
            Toast.makeText(MainActivity.this, t("Disable USB debugging before SafePay or protected browsing", "پیش از SafePay یا مرور محافظت‌شده، اشکال‌زدایی USB را غیرفعال کنید"), Toast.LENGTH_LONG).show();
            openSettings(Settings.ACTION_APPLICATION_DEVELOPMENT_SETTINGS);
            renderBrowserStart();
            return;
        }
        WebView.startSafeBrowsing(this, value -> {'''
rep(secure_lock_block, secure_lock_and_adb, "protected session adb gate")

# Compatibility contract now reflects all blocking prerequisites. Developer Options remains
# visible as a posture warning but does not block a session by itself.
rep(
    '        boolean protectedSessionReady = webViewRuntimeReady() && secureLockReady;',
    '        boolean protectedSessionReady = webViewRuntimeReady() && secureLockReady && !adbEnabled();',
    "protected readiness includes adb",
)
rep(
    '                ? t("Ready • WebView available and secure screen lock enabled", "آماده • WebView در دسترس و قفل امن صفحه فعال است")\n                : t("Needs review • SafePay requires WebView and a secure screen lock", "نیازمند بررسی • SafePay به WebView و قفل امن صفحه نیاز دارد"),',
    '                ? t("Ready • WebView available, secure screen lock enabled and USB debugging off", "آماده • WebView در دسترس، قفل امن فعال و اشکال‌زدایی USB خاموش است")\n                : t("Needs review • SafePay requires WebView, a secure screen lock and USB debugging disabled", "نیازمند بررسی • SafePay به WebView، قفل امن صفحه و غیرفعال بودن اشکال‌زدایی USB نیاز دارد"),',
    "protected readiness explanation",
)

# Add a concise compatibility detail for CPU/runtime transparency. VARA currently ships no
# native libraries, so this is informational and not a compatibility blocker.
rep(
    '        LinearLayout web = card();',
    '''        LinearLayout deviceRuntime = card();
        deviceRuntime.addView(tv(t("Runtime architecture", "معماری اجرا"), 16, NAVY, true));
        String abi = (android.os.Build.SUPPORTED_ABIS != null && android.os.Build.SUPPORTED_ABIS.length > 0)
                ? android.os.Build.SUPPORTED_ABIS[0] : t("Unknown", "نامشخص");
        deviceRuntime.addView(tv(abi, 13, TEXT, true));
        deviceRuntime.addView(tv(t("VARA uses the Android runtime only and currently includes no native ABI-specific libraries.", "VARA در حال حاضر فقط از محیط اجرای Android استفاده می‌کند و کتابخانه Native وابسته به ABI ندارد."), 12, MUTED, false));
        content.addView(deviceRuntime);

        LinearLayout web = card();''',
    "runtime architecture compatibility card",
)

# Version metadata.
s = s.replace('0.6.0 ALPHA', '0.6.1 ALPHA')
s = s.replace('0.6.0 Alpha • versionCode 600', '0.6.1 Alpha • versionCode 601')
s = s.replace('0.6.0 Alpha', '0.6.1 Alpha')
s = s.replace('VARA 0.6.0 requires Android 8.0 / API 26 or newer.', 'VARA 0.6.1 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+600\b', 'versionCode 601', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.6\.0-alpha['\"]", "versionName '0.6.1-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'Protected browser blocked: invalid HTTPS destination',
    'Protected browser blocked: USB debugging is enabled',
    'protectedSessionReady = webViewRuntimeReady() && secureLockReady && !adbEnabled()',
    'Runtime architecture',
    'SUPPORTED_ABIS',
    '0.6.1 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.6.1 protected-session preflight and compatibility patch applied")
