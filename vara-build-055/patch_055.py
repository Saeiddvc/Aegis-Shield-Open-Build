from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_055.py <android-project-root>")

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

# Treat an old or unavailable Android security patch level as an actionable device finding.
rep(
    '''    private int auditIssueCount() {
        int n = 0;
        KeyguardManager km = (KeyguardManager) getSystemService(KEYGUARD_SERVICE);
        if (km == null || !km.isDeviceSecure()) n++;
        if (Settings.Global.getInt(getContentResolver(), Settings.Global.DEVELOPMENT_SETTINGS_ENABLED, 0) != 0) n++;
        if (Settings.Global.getInt(getContentResolver(), Settings.Global.ADB_ENABLED, 0) != 0) n++;
        return n;
    }''',
    '''    private boolean isSecurityPatchCurrent() {
        try {
            String patch = android.os.Build.VERSION.SECURITY_PATCH;
            if (patch == null || patch.trim().isEmpty()) return false;
            java.time.LocalDate patchDate = java.time.LocalDate.parse(patch);
            long ageDays = java.time.temporal.ChronoUnit.DAYS.between(patchDate, java.time.LocalDate.now());
            return ageDays >= 0 && ageDays <= 180;
        } catch (Exception ignored) {
            return false;
        }
    }

    private String securityPatchLabel() {
        String patch = android.os.Build.VERSION.SECURITY_PATCH;
        return (patch == null || patch.trim().isEmpty()) ? t("Unavailable", "نامشخص") : patch;
    }

    private int auditIssueCount() {
        int n = 0;
        KeyguardManager km = (KeyguardManager) getSystemService(KEYGUARD_SERVICE);
        if (km == null || !km.isDeviceSecure()) n++;
        if (Settings.Global.getInt(getContentResolver(), Settings.Global.DEVELOPMENT_SETTINGS_ENABLED, 0) != 0) n++;
        if (Settings.Global.getInt(getContentResolver(), Settings.Global.ADB_ENABLED, 0) != 0) n++;
        if (!isSecurityPatchCurrent()) n++;
        return n;
    }''',
    "security patch posture check",
)

# Add a visible remediation row that deep-links to Android system update settings.
rep(
    '''        content.addView(auditRow(t("USB debugging", "اشکال‌زدایی USB"), adb ? t("Enabled — increases attack surface", "فعال است — سطح حمله را افزایش می‌دهد") : t("Disabled", "غیرفعال"), !adb, () -> openSettings(Settings.ACTION_APPLICATION_DEVELOPMENT_SETTINGS)));

        LinearLayout summary = card();''',
    '''        content.addView(auditRow(t("USB debugging", "اشکال‌زدایی USB"), adb ? t("Enabled — increases attack surface", "فعال است — سطح حمله را افزایش می‌دهد") : t("Disabled", "غیرفعال"), !adb, () -> openSettings(Settings.ACTION_APPLICATION_DEVELOPMENT_SETTINGS)));
        boolean patchCurrent = isSecurityPatchCurrent();
        String patchLevel = securityPatchLabel();
        content.addView(auditRow(
                t("Android security patch", "وصله امنیتی Android"),
                patchCurrent ? t("Patch level " + patchLevel + " is within the 180-day review window", "سطح وصله " + patchLevel + " در بازه بررسی ۱۸۰ روزه است")
                        : t("Patch level " + patchLevel + " should be reviewed for a system update", "سطح وصله " + patchLevel + " برای به‌روزرسانی سیستم نیاز به بررسی دارد"),
                patchCurrent,
                () -> openSettings(Settings.ACTION_SYSTEM_UPDATE_SETTINGS)));

        LinearLayout summary = card();''',
    "actionable security patch audit row",
)

# Explain the policy threshold so the finding is transparent and not presented as a malware verdict.
rep(
    '''        summary.addView(tv(t("VARA does not change sensitive system settings automatically. Use the action buttons to review them in Android Settings.", "VARA تنظیمات حساس سیستم را خودکار تغییر نمی‌دهد. برای اصلاح، از دکمه‌های اقدام و تنظیمات Android استفاده کنید."), 13, MUTED, false));''',
    '''        summary.addView(tv(t("VARA does not change sensitive system settings automatically. Use the action buttons to review them in Android Settings. Security patches older than 180 days are flagged for review.", "VARA تنظیمات حساس سیستم را خودکار تغییر نمی‌دهد. برای اصلاح، از دکمه‌های اقدام و تنظیمات Android استفاده کنید. وصله امنیتی قدیمی‌تر از ۱۸۰ روز برای بررسی علامت‌گذاری می‌شود."), 13, MUTED, false));''',
    "audit policy disclosure",
)

# Version metadata.
s = s.replace('0.5.4 ALPHA', '0.5.5 ALPHA')
s = s.replace('0.5.4 Alpha • versionCode 504', '0.5.5 Alpha • versionCode 505')
s = s.replace('0.5.4 Alpha', '0.5.5 Alpha')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+504\b', 'versionCode 505', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.5\.4-alpha['\"]", "versionName '0.5.5-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'isSecurityPatchCurrent()',
    'VERSION.SECURITY_PATCH',
    'ACTION_SYSTEM_UPDATE_SETTINGS',
    'older than 180 days',
    '0.5.5 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.5.5 Android security-patch audit patch applied")
