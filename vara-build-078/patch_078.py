from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_078.py <android-project-root>")

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

# Active third-party Device Administrators can enforce policies or retain elevated
# device-management authority. Treat them as review-only exposure signals: legitimate
# enterprise/MDM deployments are common, so this is not malware evidence and does not
# automatically block SafePay.
rep(
    '''    private int enabledThirdPartyInputMethodCount() {''',
    '''    private int activeThirdPartyDeviceAdminCount() {
        try {
            android.app.admin.DevicePolicyManager dpm =
                    (android.app.admin.DevicePolicyManager) getSystemService(DEVICE_POLICY_SERVICE);
            if (dpm == null) return 0;
            java.util.List<android.content.ComponentName> admins = dpm.getActiveAdmins();
            if (admins == null || admins.isEmpty()) return 0;
            android.content.pm.PackageManager pm = getPackageManager();
            java.util.HashSet<String> seen = new java.util.HashSet<>();
            int count = 0;
            for (android.content.ComponentName admin : admins) {
                if (admin == null || admin.getPackageName() == null) continue;
                String pkg = admin.getPackageName();
                if (getPackageName().equals(pkg) || !seen.add(pkg)) continue;
                try {
                    android.content.pm.ApplicationInfo app = pm.getApplicationInfo(pkg, 0);
                    boolean systemApp = (app.flags & android.content.pm.ApplicationInfo.FLAG_SYSTEM) != 0
                            || (app.flags & android.content.pm.ApplicationInfo.FLAG_UPDATED_SYSTEM_APP) != 0;
                    if (!systemApp) count++;
                } catch (android.content.pm.PackageManager.NameNotFoundException ignored) { }
            }
            return count;
        } catch (Exception ignored) { return 0; }
    }

    private int enabledThirdPartyInputMethodCount() {''',
    "third-party active device admin helper",
)

rep(
    '''        if (enabledThirdPartyOverlayCount() > 0) n++;
        if (enabledThirdPartyInputMethodCount() > 0) n++;
        return n;''',
    '''        if (enabledThirdPartyOverlayCount() > 0) n++;
        if (enabledThirdPartyInputMethodCount() > 0) n++;
        if (activeThirdPartyDeviceAdminCount() > 0) n++;
        return n;''',
    "device admin exposure in device trust score",
)

rep(
    '''        int inputMethodCount = enabledThirdPartyInputMethodCount();
        content.addView(auditRow(
                t("Third-party keyboard exposure", "دسترسی صفحه‌کلید شخص ثالث"),
                inputMethodCount == 0
                        ? t("No enabled third-party input method detected", "روش ورودی شخص ثالث فعالی شناسایی نشد")
                        : t(inputMethodCount + " third-party input method app(s) are enabled — verify every keyboard before entering passwords, OTPs or payment data",
                                inputMethodCount + " برنامه روش ورودی شخص ثالث فعال است — پیش از ورود رمز، رمز یک‌بارمصرف یا اطلاعات پرداخت همه موارد را بررسی کنید"),
                inputMethodCount == 0,
                () -> openSettings(Settings.ACTION_INPUT_METHOD_SETTINGS)));

        LinearLayout summary = card();''',
    '''        int inputMethodCount = enabledThirdPartyInputMethodCount();
        content.addView(auditRow(
                t("Third-party keyboard exposure", "دسترسی صفحه‌کلید شخص ثالث"),
                inputMethodCount == 0
                        ? t("No enabled third-party input method detected", "روش ورودی شخص ثالث فعالی شناسایی نشد")
                        : t(inputMethodCount + " third-party input method app(s) are enabled — verify every keyboard before entering passwords, OTPs or payment data",
                                inputMethodCount + " برنامه روش ورودی شخص ثالث فعال است — پیش از ورود رمز، رمز یک‌بارمصرف یا اطلاعات پرداخت همه موارد را بررسی کنید"),
                inputMethodCount == 0,
                () -> openSettings(Settings.ACTION_INPUT_METHOD_SETTINGS)));

        int deviceAdminCount = activeThirdPartyDeviceAdminCount();
        content.addView(auditRow(
                t("Device administrator exposure", "دسترسی مدیر دستگاه"),
                deviceAdminCount == 0
                        ? t("No active third-party device administrator detected", "مدیر دستگاه شخص ثالث فعالی شناسایی نشد")
                        : t(deviceAdminCount + " third-party app(s) have active device-administrator authority — verify each app and remove authority you no longer need",
                                deviceAdminCount + " برنامه شخص ثالث دارای اختیار فعال مدیر دستگاه است — هر مورد را بررسی و دسترسی غیرضروری را حذف کنید"),
                deviceAdminCount == 0,
                () -> openSettings(Settings.ACTION_DEVICE_ADMIN_SETTINGS)));

        LinearLayout summary = card();''',
    "actionable device administrator audit row",
)

rep(
    '''        content.addView(securityPatch);''',
    '''        content.addView(securityPatch);

        LinearLayout deviceAdmins = card();
        int activeAdmins = activeThirdPartyDeviceAdminCount();
        deviceAdmins.addView(tv(t("Device administrator exposure", "دسترسی مدیر دستگاه"), 16, NAVY, true));
        deviceAdmins.addView(tv(activeAdmins == 0
                ? t("No active third-party device administrator detected", "مدیر دستگاه شخص ثالث فعالی شناسایی نشد")
                : t(activeAdmins + " third-party app(s) currently hold device-administrator authority and should be reviewed",
                        activeAdmins + " برنامه شخص ثالث در حال حاضر اختیار مدیر دستگاه دارد و باید بررسی شود"),
                13, activeAdmins == 0 ? GOOD : WARN, activeAdmins != 0));
        deviceAdmins.addView(tv(t("Device-administrator authority can be legitimate for enterprise or device-management apps. VARA reports it as a review signal only and does not classify the app as malicious or block SafePay automatically.",
                "اختیار مدیر دستگاه می‌تواند برای برنامه‌های سازمانی یا مدیریت دستگاه کاملاً مجاز باشد. VARA آن را فقط سیگنال بررسی می‌داند و برنامه را بدافزار تلقی یا SafePay را خودکار مسدود نمی‌کند."), 12, MUTED, false));
        content.addView(deviceAdmins);''',
    "compatibility device administrator card",
)

# Version metadata.
s = s.replace('0.7.7 ALPHA', '0.7.8 ALPHA')
s = s.replace('0.7.7 Alpha • versionCode 707', '0.7.8 Alpha • versionCode 708')
s = s.replace('0.7.7 Alpha', '0.7.8 Alpha')
s = s.replace('VARA 0.7.7 requires Android 8.0 / API 26 or newer.', 'VARA 0.7.8 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+707\b', 'versionCode 708', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.7\.7-alpha['\"]", "versionName '0.7.8-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'activeThirdPartyDeviceAdminCount()',
    'DevicePolicyManager',
    'getActiveAdmins()',
    'Device administrator exposure',
    'Settings.ACTION_DEVICE_ADMIN_SETTINGS',
    'does not classify the app as malicious or block SafePay automatically',
    '0.7.8 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.7.8 active third-party device-administrator exposure audit patch applied")
