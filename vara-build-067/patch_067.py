from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_067.py <android-project-root>")

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

# Notification-listener access can expose OTPs and transaction notifications. Report enabled
# third-party listeners as a review signal, without calling them malicious and without turning
# legitimate notification-management apps into an automatic SafePay block.
rep(
    '''    private int enabledThirdPartyAccessibilityServiceCount() {
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
    '''    private int enabledThirdPartyAccessibilityServiceCount() {
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

    private int enabledThirdPartyNotificationListenerCount() {
        try {
            String raw = android.provider.Settings.Secure.getString(
                    getContentResolver(), "enabled_notification_listeners");
            if (raw == null || raw.trim().isEmpty()) return 0;
            java.util.HashSet<String> packages = new java.util.HashSet<>();
            for (String flattened : raw.split(":")) {
                android.content.ComponentName component = android.content.ComponentName.unflattenFromString(flattened);
                if (component == null) continue;
                String pkg = component.getPackageName();
                if (pkg == null || pkg.isEmpty() || getPackageName().equals(pkg)) continue;
                try {
                    android.content.pm.ApplicationInfo app = getPackageManager().getApplicationInfo(pkg, 0);
                    boolean systemApp = (app.flags & android.content.pm.ApplicationInfo.FLAG_SYSTEM) != 0
                            || (app.flags & android.content.pm.ApplicationInfo.FLAG_UPDATED_SYSTEM_APP) != 0;
                    if (!systemApp) packages.add(pkg);
                } catch (android.content.pm.PackageManager.NameNotFoundException ignored) {
                    packages.add(pkg);
                }
            }
            return packages.size();
        } catch (Exception ignored) { return 0; }
    }

    private int deviceTrustIssueCount() {''',
    "third-party notification listener helper",
)

rep(
    '''        if (!securityPatchFresh()) n++;
        if (enabledThirdPartyAccessibilityServiceCount() > 0) n++;
        return n;''',
    '''        if (!securityPatchFresh()) n++;
        if (enabledThirdPartyAccessibilityServiceCount() > 0) n++;
        if (enabledThirdPartyNotificationListenerCount() > 0) n++;
        return n;''',
    "notification listener exposure in device trust score",
)

# Add an actionable row to Device Security Audit. This remains review-only because many
# notification listeners are legitimate, but they can read OTP and payment notifications.
rep(
    '''        int accessibilityCount = enabledThirdPartyAccessibilityServiceCount();
        content.addView(auditRow(
                t("Accessibility service exposure", "دسترسی سرویس‌های دسترس‌پذیری"),
                accessibilityCount == 0
                        ? t("No enabled third-party accessibility service detected", "سرویس دسترس‌پذیری شخص ثالث فعالی شناسایی نشد")
                        : t(accessibilityCount + " enabled third-party service(s) — verify each one is expected before sensitive use",
                                accessibilityCount + " سرویس شخص ثالث فعال است — پیش از استفاده حساس، مورد انتظار بودن هرکدام را بررسی کنید"),
                accessibilityCount == 0,
                () -> openSettings(Settings.ACTION_ACCESSIBILITY_SETTINGS)));

        LinearLayout summary = card();''',
    '''        int accessibilityCount = enabledThirdPartyAccessibilityServiceCount();
        content.addView(auditRow(
                t("Accessibility service exposure", "دسترسی سرویس‌های دسترس‌پذیری"),
                accessibilityCount == 0
                        ? t("No enabled third-party accessibility service detected", "سرویس دسترس‌پذیری شخص ثالث فعالی شناسایی نشد")
                        : t(accessibilityCount + " enabled third-party service(s) — verify each one is expected before sensitive use",
                                accessibilityCount + " سرویس شخص ثالث فعال است — پیش از استفاده حساس، مورد انتظار بودن هرکدام را بررسی کنید"),
                accessibilityCount == 0,
                () -> openSettings(Settings.ACTION_ACCESSIBILITY_SETTINGS)));

        int listenerCount = enabledThirdPartyNotificationListenerCount();
        content.addView(auditRow(
                t("Notification listener exposure", "دسترسی خواندن اعلان‌ها"),
                listenerCount == 0
                        ? t("No enabled third-party notification listener detected", "برنامه شخص ثالثی با دسترسی خواندن اعلان‌ها شناسایی نشد")
                        : t(listenerCount + " third-party listener app(s) can read notifications — verify every app before using OTP or payment flows",
                                listenerCount + " برنامه شخص ثالث می‌تواند اعلان‌ها را بخواند — پیش از استفاده از رمز یک‌بارمصرف یا پرداخت، همه موارد را بررسی کنید"),
                listenerCount == 0,
                () -> openSettings(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS)));

        LinearLayout summary = card();''',
    "actionable notification listener audit row",
)

# Device Compatibility mirrors the review state while keeping it separate from hard Protected
# Session prerequisites, so expected listener apps do not unnecessarily block banking flows.
rep(
    '''        content.addView(accessibility);

        Button recheck = secondary(t("Recheck compatibility", "بررسی مجدد سازگاری"));''',
    '''        content.addView(accessibility);

        LinearLayout notifications = card();
        int enabledListeners = enabledThirdPartyNotificationListenerCount();
        notifications.addView(tv(t("Notification listener exposure", "دسترسی خواندن اعلان‌ها"), 16, NAVY, true));
        notifications.addView(tv(enabledListeners == 0
                ? t("No enabled third-party notification listener detected", "برنامه شخص ثالثی با دسترسی خواندن اعلان‌ها شناسایی نشد")
                : t(enabledListeners + " third-party listener app(s) should be reviewed before OTP or payment use",
                        enabledListeners + " برنامه شخص ثالث دارای دسترسی اعلان است و پیش از رمز یک‌بارمصرف یا پرداخت باید بررسی شود"),
                13, enabledListeners == 0 ? GOOD : WARN, enabledListeners != 0));
        notifications.addView(tv(t("Notification access can expose OTP and transaction messages. VARA reports this as a review signal, not proof of compromise.",
                "دسترسی اعلان می‌تواند محتوای رمز یک‌بارمصرف و پیام‌های تراکنش را در اختیار برنامه بگذارد. VARA این مورد را فقط سیگنال بررسی می‌داند و آن را اثبات نفوذ تلقی نمی‌کند."), 12, MUTED, false));
        content.addView(notifications);

        Button recheck = secondary(t("Recheck compatibility", "بررسی مجدد سازگاری"));''',
    "compatibility notification listener card",
)

# Version metadata.
s = s.replace('0.6.6 ALPHA', '0.6.7 ALPHA')
s = s.replace('0.6.6 Alpha • versionCode 606', '0.6.7 Alpha • versionCode 607')
s = s.replace('0.6.6 Alpha', '0.6.7 Alpha')
s = s.replace('VARA 0.6.6 requires Android 8.0 / API 26 or newer.', 'VARA 0.6.7 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+606\b', 'versionCode 607', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.6\.6-alpha['\"]", "versionName '0.6.7-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'enabledThirdPartyNotificationListenerCount()',
    'enabled_notification_listeners',
    'Notification listener exposure',
    'Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS',
    'OTP and transaction messages',
    '0.6.7 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.6.7 notification-listener exposure audit patch applied")
