from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_074.py <android-project-root>")

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

# Overlay permission can place content over other apps and can be abused for deceptive UI.
# Report granted third-party overlay access as a review signal, not as proof of malware and
# not as an automatic Protected Session blocker because legitimate apps may require it.
rep(
    '''    private int deviceTrustIssueCount() {''',
    '''    private int enabledThirdPartyOverlayCount() {
        try {
            android.content.pm.PackageManager pm = getPackageManager();
            int count = 0;
            for (android.content.pm.ApplicationInfo app : pm.getInstalledApplications(0)) {
                if (app == null || app.packageName == null || getPackageName().equals(app.packageName)) continue;
                boolean systemApp = (app.flags & android.content.pm.ApplicationInfo.FLAG_SYSTEM) != 0
                        || (app.flags & android.content.pm.ApplicationInfo.FLAG_UPDATED_SYSTEM_APP) != 0;
                if (systemApp) continue;
                if (pm.checkPermission(android.Manifest.permission.SYSTEM_ALERT_WINDOW, app.packageName)
                        == android.content.pm.PackageManager.PERMISSION_GRANTED) count++;
            }
            return count;
        } catch (Exception ignored) { return 0; }
    }

    private int deviceTrustIssueCount() {''',
    "third-party overlay helper",
)

rep(
    '''        if (enabledThirdPartyNotificationListenerCount() > 0) n++;
        return n;''',
    '''        if (enabledThirdPartyNotificationListenerCount() > 0) n++;
        if (enabledThirdPartyOverlayCount() > 0) n++;
        return n;''',
    "overlay exposure in device trust score",
)

rep(
    '''        int listenerCount = enabledThirdPartyNotificationListenerCount();
        content.addView(auditRow(
                t("Notification listener exposure", "دسترسی خواندن اعلان‌ها"),
                listenerCount == 0
                        ? t("No enabled third-party notification listener detected", "برنامه شخص ثالثی با دسترسی خواندن اعلان‌ها شناسایی نشد")
                        : t(listenerCount + " third-party listener app(s) can read notifications — verify every app before using OTP or payment flows",
                                listenerCount + " برنامه شخص ثالث می‌تواند اعلان‌ها را بخواند — پیش از استفاده از رمز یک‌بارمصرف یا پرداخت، همه موارد را بررسی کنید"),
                listenerCount == 0,
                () -> openSettings(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS)));

        LinearLayout summary = card();''',
    '''        int listenerCount = enabledThirdPartyNotificationListenerCount();
        content.addView(auditRow(
                t("Notification listener exposure", "دسترسی خواندن اعلان‌ها"),
                listenerCount == 0
                        ? t("No enabled third-party notification listener detected", "برنامه شخص ثالثی با دسترسی خواندن اعلان‌ها شناسایی نشد")
                        : t(listenerCount + " third-party listener app(s) can read notifications — verify every app before using OTP or payment flows",
                                listenerCount + " برنامه شخص ثالث می‌تواند اعلان‌ها را بخواند — پیش از استفاده از رمز یک‌بارمصرف یا پرداخت، همه موارد را بررسی کنید"),
                listenerCount == 0,
                () -> openSettings(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS)));

        int overlayCount = enabledThirdPartyOverlayCount();
        content.addView(auditRow(
                t("Display-over-other-apps exposure", "دسترسی نمایش روی سایر برنامه‌ها"),
                overlayCount == 0
                        ? t("No third-party app with granted overlay permission detected", "برنامه شخص ثالثی با مجوز فعال نمایش روی سایر برنامه‌ها شناسایی نشد")
                        : t(overlayCount + " third-party app(s) can draw over other apps — verify every app before sensitive use",
                                overlayCount + " برنامه شخص ثالث می‌تواند روی سایر برنامه‌ها نمایش داده شود — پیش از استفاده حساس، همه موارد را بررسی کنید"),
                overlayCount == 0,
                () -> openSettings(Settings.ACTION_MANAGE_OVERLAY_PERMISSION)));

        LinearLayout summary = card();''',
    "actionable overlay audit row",
)

rep(
    '''        content.addView(notifications);''',
    '''        content.addView(notifications);

        LinearLayout overlays = card();
        int enabledOverlays = enabledThirdPartyOverlayCount();
        overlays.addView(tv(t("Display-over-other-apps exposure", "دسترسی نمایش روی سایر برنامه‌ها"), 16, NAVY, true));
        overlays.addView(tv(enabledOverlays == 0
                ? t("No granted third-party overlay permission detected", "مجوز فعال Overlay برای برنامه شخص ثالث شناسایی نشد")
                : t(enabledOverlays + " third-party app(s) with overlay access should be reviewed before sensitive use",
                        enabledOverlays + " برنامه شخص ثالث دارای دسترسی Overlay است و پیش از استفاده حساس باید بررسی شود"),
                13, enabledOverlays == 0 ? GOOD : WARN, enabledOverlays != 0));
        overlays.addView(tv(t("Overlay access can obscure or imitate interface elements. VARA reports this as a review signal; protected mode also rejects obscured touches.",
                "دسترسی Overlay می‌تواند عناصر رابط را بپوشاند یا تقلید کند. VARA این مورد را سیگنال بررسی می‌داند و حالت محافظت‌شده لمس‌های پوشانده‌شده را نیز رد می‌کند."), 12, MUTED, false));
        content.addView(overlays);''',
    "compatibility overlay card",
)

# Version metadata.
s = s.replace('0.7.3 ALPHA', '0.7.4 ALPHA')
s = s.replace('0.7.3 Alpha • versionCode 703', '0.7.4 Alpha • versionCode 704')
s = s.replace('0.7.3 Alpha', '0.7.4 Alpha')
s = s.replace('VARA 0.7.3 requires Android 8.0 / API 26 or newer.', 'VARA 0.7.4 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+703\b', 'versionCode 704', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.7\.3-alpha['\"]", "versionName '0.7.4-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'enabledThirdPartyOverlayCount()',
    'SYSTEM_ALERT_WINDOW',
    'Display-over-other-apps exposure',
    'Settings.ACTION_MANAGE_OVERLAY_PERMISSION',
    'protected mode also rejects obscured touches',
    '0.7.4 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.7.4 overlay-exposure audit patch applied")
