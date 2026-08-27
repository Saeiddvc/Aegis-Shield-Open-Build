from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_058.py <android-project-root>")

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

# Device trust signals: secure lock screen, Developer Options and USB debugging.
trust_helpers = r'''
    private boolean isDeviceLockSecure() {
        try {
            android.app.KeyguardManager km = (android.app.KeyguardManager) getSystemService(KEYGUARD_SERVICE);
            return km != null && km.isDeviceSecure();
        } catch (Exception ignored) { return false; }
    }

    private boolean developerOptionsEnabled() {
        try { return Settings.Global.getInt(getContentResolver(), Settings.Global.DEVELOPMENT_SETTINGS_ENABLED, 0) == 1; }
        catch (Exception ignored) { return false; }
    }

    private boolean adbEnabled() {
        try { return Settings.Global.getInt(getContentResolver(), Settings.Global.ADB_ENABLED, 0) == 1; }
        catch (Exception ignored) { return false; }
    }

    private int deviceTrustIssueCount() {
        int n = 0;
        if (!isDeviceLockSecure()) n++;
        if (developerOptionsEnabled()) n++;
        if (adbEnabled()) n++;
        return n;
    }

'''
rep(
    '    private boolean isSecurityPatchCurrent() {',
    trust_helpers + '    private boolean isSecurityPatchCurrent() {',
    "device trust helpers",
)

rep(
    '        if (!isSecurityPatchCurrent()) n++;\n        if (!webViewRuntimeReady()) n++;\n        return n;',
    '        if (!isSecurityPatchCurrent()) n++;\n        if (!webViewRuntimeReady()) n++;\n        n += deviceTrustIssueCount();\n        return n;',
    "trust issues in audit count",
)

# Make each trust signal actionable in Device Security Audit.
anchor = '''        content.addView(auditRow(
                t("Secure WebView runtime", "موتور WebView امن"),
                webViewReady ? t("Available • " + webViewRuntimeLabel(), "در دسترس • " + webViewRuntimeLabel())
                        : t("No usable system WebView provider detected — SafePay cannot start safely", "موتور WebView قابل استفاده شناسایی نشد — SafePay نمی‌تواند با ایمنی اجرا شود"),
                webViewReady,
                () -> openSettings(Settings.ACTION_SETTINGS)));

        LinearLayout summary = card();'''
replacement = '''        content.addView(auditRow(
                t("Secure WebView runtime", "موتور WebView امن"),
                webViewReady ? t("Available • " + webViewRuntimeLabel(), "در دسترس • " + webViewRuntimeLabel())
                        : t("No usable system WebView provider detected — SafePay cannot start safely", "موتور WebView قابل استفاده شناسایی نشد — SafePay نمی‌تواند با ایمنی اجرا شود"),
                webViewReady,
                () -> openSettings(Settings.ACTION_SETTINGS)));

        boolean lockSecure = isDeviceLockSecure();
        content.addView(auditRow(
                t("Secure screen lock", "قفل امن صفحه"),
                lockSecure ? t("PIN, password or biometric-backed device credential is configured", "PIN، رمز عبور یا اعتبار دستگاه پشتیبان‌شده با بیومتریک تنظیم شده است")
                        : t("No secure device credential detected — configure a screen lock before sensitive use", "اعتبار امن دستگاه شناسایی نشد — پیش از استفاده حساس قفل صفحه تنظیم کنید"),
                lockSecure,
                () -> openSettings(Settings.ACTION_SECURITY_SETTINGS)));

        boolean devEnabled = developerOptionsEnabled();
        content.addView(auditRow(
                t("Developer Options", "گزینه‌های توسعه‌دهنده"),
                devEnabled ? t("Enabled — review and disable when not actively needed", "فعال است — در صورت عدم نیاز فعال، بررسی و غیرفعال شود")
                        : t("Disabled", "غیرفعال"),
                !devEnabled,
                () -> openSettings(Settings.ACTION_APPLICATION_DEVELOPMENT_SETTINGS)));

        boolean usbDebug = adbEnabled();
        content.addView(auditRow(
                t("USB debugging", "اشکال‌زدایی USB"),
                usbDebug ? t("ADB is enabled — disable before sensitive sessions unless explicitly required", "ADB فعال است — مگر در صورت نیاز صریح، پیش از نشست حساس غیرفعال شود")
                        : t("Disabled", "غیرفعال"),
                !usbDebug,
                () -> openSettings(Settings.ACTION_APPLICATION_DEVELOPMENT_SETTINGS)));

        LinearLayout summary = card();'''
rep(anchor, replacement, "actionable trust audit rows")

# Surface trust posture in Device Compatibility so compatibility and security context are separated but visible together.
rep(
    '''        Button recheck = secondary(t("Recheck compatibility", "بررسی مجدد سازگاری"));''',
    '''        LinearLayout trust = card();
        trust.addView(tv(t("Device trust signals", "سیگنال‌های اعتماد دستگاه"), 16, NAVY, true));
        int trustIssues = deviceTrustIssueCount();
        trust.addView(tv(trustIssues == 0 ? t("Secure lock is configured and developer/ADB exposure is not detected.", "قفل امن تنظیم شده و فعال بودن Developer/ADB شناسایی نشد.")
                : t(trustIssues + " trust signal(s) need review before sensitive use.", trustIssues + " سیگنال اعتماد پیش از استفاده حساس نیازمند بررسی است."), 13, trustIssues == 0 ? GOOD : WARN, trustIssues != 0));
        trust.addView(tv(t("These signals influence VARA's local posture score; they do not by themselves indicate compromise.", "این سیگنال‌ها بر وضعیت محلی VARA اثر می‌گذارند و به‌تنهایی نشانه نفوذ نیستند."), 12, MUTED, false));
        content.addView(trust);

        Button recheck = secondary(t("Recheck compatibility", "بررسی مجدد سازگاری"));''',
    "compatibility trust card",
)

# Version metadata.
s = s.replace('0.5.7 ALPHA', '0.5.8 ALPHA')
s = s.replace('0.5.7 Alpha • versionCode 507', '0.5.8 Alpha • versionCode 508')
s = s.replace('0.5.7 Alpha', '0.5.8 Alpha')
s = s.replace('VARA 0.5.7 requires Android 8.0 / API 26 or newer.', 'VARA 0.5.8 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+507\b', 'versionCode 508', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.5\.7-alpha['\"]", "versionName '0.5.8-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'isDeviceLockSecure()',
    'developerOptionsEnabled()',
    'adbEnabled()',
    'deviceTrustIssueCount()',
    'Secure screen lock',
    'Developer Options',
    'USB debugging',
    'Device trust signals',
    '0.5.8 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.5.8 device-trust posture patch applied")
