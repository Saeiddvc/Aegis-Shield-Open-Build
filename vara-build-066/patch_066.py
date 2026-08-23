from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_066.py <android-project-root>")

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

# Accessibility services can legitimately assist users, but third-party enabled services can
# observe UI content and gestures. Surface this as a review signal without labeling it malware
# and without blocking accessibility-dependent users from Protected Browser/SafePay.
rep(
    '''    private boolean securityPatchFresh() {
        long age = securityPatchAgeDays();
        return age >= 0 && age <= 180;
    }

    private int deviceTrustIssueCount() {''',
    '''    private boolean securityPatchFresh() {
        long age = securityPatchAgeDays();
        return age >= 0 && age <= 180;
    }

    private int enabledThirdPartyAccessibilityServiceCount() {
        try {
            android.view.accessibility.AccessibilityManager manager =
                    (android.view.accessibility.AccessibilityManager) getSystemService(ACCESSIBILITY_SERVICE);
            if (manager == null) return 0;
            java.util.List<android.accessibilityservice.AccessibilityServiceInfo> enabled =
                    manager.getEnabledAccessibilityServiceList(android.accessibilityservice.AccessibilityServiceInfo.FEEDBACK_ALL_MASK);
            int count = 0;
            for (android.accessibilityservice.AccessibilityServiceInfo info : enabled) {
                if (info == null || info.getResolveInfo() == null || info.getResolveInfo().serviceInfo == null) continue;
                android.content.pm.ServiceInfo service = info.getResolveInfo().serviceInfo;
                android.content.pm.ApplicationInfo app = service.applicationInfo;
                if (app == null || getPackageName().equals(service.packageName)) continue;
                boolean systemApp = (app.flags & android.content.pm.ApplicationInfo.FLAG_SYSTEM) != 0
                        || (app.flags & android.content.pm.ApplicationInfo.FLAG_UPDATED_SYSTEM_APP) != 0;
                if (!systemApp) count++;
            }
            return count;
        } catch (Exception ignored) { return 0; }
    }

    private int deviceTrustIssueCount() {''',
    "third-party accessibility helper",
)

rep(
    '''        if (!automaticTimeEnabled()) n++;
        if (!automaticTimeZoneEnabled()) n++;
        if (!securityPatchFresh()) n++;
        return n;''',
    '''        if (!automaticTimeEnabled()) n++;
        if (!automaticTimeZoneEnabled()) n++;
        if (!securityPatchFresh()) n++;
        if (enabledThirdPartyAccessibilityServiceCount() > 0) n++;
        return n;''',
    "accessibility exposure in device trust score",
)

# Add an actionable row to Device Security Audit. The row deliberately avoids asserting that an
# enabled accessibility service is malicious; it asks the user to review only services they expect.
rep(
    '''        content.addView(auditRow(
                t("Android security patch", "وصله امنیتی اندروید"),
                patchDetail,
                patchFresh,
                () -> openSettings(Settings.ACTION_SECURITY_SETTINGS)));

        LinearLayout summary = card();''',
    '''        content.addView(auditRow(
                t("Android security patch", "وصله امنیتی اندروید"),
                patchDetail,
                patchFresh,
                () -> openSettings(Settings.ACTION_SECURITY_SETTINGS)));

        int accessibilityCount = enabledThirdPartyAccessibilityServiceCount();
        content.addView(auditRow(
                t("Accessibility service exposure", "دسترسی سرویس‌های دسترس‌پذیری"),
                accessibilityCount == 0
                        ? t("No enabled third-party accessibility service detected", "سرویس دسترس‌پذیری شخص ثالث فعالی شناسایی نشد")
                        : t(accessibilityCount + " enabled third-party service(s) — verify each one is expected before sensitive use",
                                accessibilityCount + " سرویس شخص ثالث فعال است — پیش از استفاده حساس، مورد انتظار بودن هرکدام را بررسی کنید"),
                accessibilityCount == 0,
                () -> openSettings(Settings.ACTION_ACCESSIBILITY_SETTINGS)));

        LinearLayout summary = card();''',
    "actionable accessibility audit row",
)

# Compatibility view surfaces the same state separately from hard blocking prerequisites.
rep(
    '''        Button recheck = secondary(t("Recheck compatibility", "بررسی مجدد سازگاری"));''',
    '''        LinearLayout accessibility = card();
        int enabledAccessibility = enabledThirdPartyAccessibilityServiceCount();
        accessibility.addView(tv(t("Accessibility exposure", "وضعیت دسترس‌پذیری"), 16, NAVY, true));
        accessibility.addView(tv(enabledAccessibility == 0
                ? t("No enabled third-party accessibility service detected", "سرویس دسترس‌پذیری شخص ثالث فعالی شناسایی نشد")
                : t(enabledAccessibility + " enabled third-party service(s) need review before sensitive use",
                        enabledAccessibility + " سرویس شخص ثالث فعال پیش از استفاده حساس نیازمند بررسی است"),
                13, enabledAccessibility == 0 ? GOOD : WARN, enabledAccessibility != 0));
        accessibility.addView(tv(t("Accessibility services may be legitimate. VARA reports this as a review signal and does not treat it as proof of compromise.",
                "سرویس‌های دسترس‌پذیری می‌توانند کاملاً مجاز باشند. VARA این مورد را فقط سیگنال بررسی می‌داند و آن را اثبات نفوذ تلقی نمی‌کند."), 12, MUTED, false));
        content.addView(accessibility);

        Button recheck = secondary(t("Recheck compatibility", "بررسی مجدد سازگاری"));''',
    "compatibility accessibility card",
)

# Version metadata.
s = s.replace('0.6.5 ALPHA', '0.6.6 ALPHA')
s = s.replace('0.6.5 Alpha • versionCode 605', '0.6.6 Alpha • versionCode 606')
s = s.replace('0.6.5 Alpha', '0.6.6 Alpha')
s = s.replace('VARA 0.6.5 requires Android 8.0 / API 26 or newer.', 'VARA 0.6.6 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+605\b', 'versionCode 606', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.6\.5-alpha['\"]", "versionName '0.6.6-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'enabledThirdPartyAccessibilityServiceCount()',
    'AccessibilityServiceInfo.FEEDBACK_ALL_MASK',
    'Accessibility service exposure',
    'Settings.ACTION_ACCESSIBILITY_SETTINGS',
    'Accessibility services may be legitimate',
    '0.6.6 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.6.6 accessibility exposure audit patch applied")
