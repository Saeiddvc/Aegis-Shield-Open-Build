from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_079.py <android-project-root>")

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

# Review-only audit for third-party apps that both declare REQUEST_INSTALL_PACKAGES
# and currently have Android's install-unknown-apps AppOp allowed. This is an
# exposure signal, not malware evidence, and does not automatically block SafePay.
rep(
    '''    private int activeThirdPartyDeviceAdminCount() {''',
    '''    private int allowedThirdPartyUnknownSourceInstallerCount() {
        try {
            android.content.pm.PackageManager pm = getPackageManager();
            android.app.AppOpsManager appOps =
                    (android.app.AppOpsManager) getSystemService(APP_OPS_SERVICE);
            if (appOps == null) return 0;
            java.util.List<android.content.pm.PackageInfo> packages =
                    pm.getInstalledPackages(android.content.pm.PackageManager.GET_PERMISSIONS);
            if (packages == null || packages.isEmpty()) return 0;
            int count = 0;
            java.util.HashSet<String> seen = new java.util.HashSet<>();
            for (android.content.pm.PackageInfo pi : packages) {
                if (pi == null || pi.packageName == null || pi.applicationInfo == null) continue;
                String pkg = pi.packageName;
                if (getPackageName().equals(pkg) || !seen.add(pkg)) continue;
                android.content.pm.ApplicationInfo app = pi.applicationInfo;
                boolean systemApp = (app.flags & android.content.pm.ApplicationInfo.FLAG_SYSTEM) != 0
                        || (app.flags & android.content.pm.ApplicationInfo.FLAG_UPDATED_SYSTEM_APP) != 0;
                if (systemApp) continue;
                boolean requestsInstallPackages = false;
                if (pi.requestedPermissions != null) {
                    for (String permission : pi.requestedPermissions) {
                        if (android.Manifest.permission.REQUEST_INSTALL_PACKAGES.equals(permission)) {
                            requestsInstallPackages = true;
                            break;
                        }
                    }
                }
                if (!requestsInstallPackages) continue;
                int mode = appOps.checkOpNoThrow(
                        "android:request_install_packages",
                        app.uid,
                        pkg);
                if (mode == android.app.AppOpsManager.MODE_ALLOWED) count++;
            }
            return count;
        } catch (Exception ignored) { return 0; }
    }

    private int activeThirdPartyDeviceAdminCount() {''',
    "unknown-source installer exposure helper",
)

rep(
    '''        if (enabledThirdPartyInputMethodCount() > 0) n++;
        if (activeThirdPartyDeviceAdminCount() > 0) n++;
        return n;''',
    '''        if (enabledThirdPartyInputMethodCount() > 0) n++;
        if (activeThirdPartyDeviceAdminCount() > 0) n++;
        if (allowedThirdPartyUnknownSourceInstallerCount() > 0) n++;
        return n;''',
    "unknown-source installer exposure in device trust score",
)

rep(
    '''        int deviceAdminCount = activeThirdPartyDeviceAdminCount();
        content.addView(auditRow(
                t("Device administrator exposure", "دسترسی مدیر دستگاه"),
                deviceAdminCount == 0
                        ? t("No active third-party device administrator detected", "مدیر دستگاه شخص ثالث فعالی شناسایی نشد")
                        : t(deviceAdminCount + " third-party app(s) have active device-administrator authority — verify each app and remove authority you no longer need",
                                deviceAdminCount + " برنامه شخص ثالث دارای اختیار فعال مدیر دستگاه است — هر مورد را بررسی و دسترسی غیرضروری را حذف کنید"),
                deviceAdminCount == 0,
                () -> openSettings(Settings.ACTION_SECURITY_SETTINGS)));

        LinearLayout summary = card();''',
    '''        int deviceAdminCount = activeThirdPartyDeviceAdminCount();
        content.addView(auditRow(
                t("Device administrator exposure", "دسترسی مدیر دستگاه"),
                deviceAdminCount == 0
                        ? t("No active third-party device administrator detected", "مدیر دستگاه شخص ثالث فعالی شناسایی نشد")
                        : t(deviceAdminCount + " third-party app(s) have active device-administrator authority — verify each app and remove authority you no longer need",
                                deviceAdminCount + " برنامه شخص ثالث دارای اختیار فعال مدیر دستگاه است — هر مورد را بررسی و دسترسی غیرضروری را حذف کنید"),
                deviceAdminCount == 0,
                () -> openSettings(Settings.ACTION_SECURITY_SETTINGS)));

        int unknownInstallerCount = allowedThirdPartyUnknownSourceInstallerCount();
        content.addView(auditRow(
                t("Unknown-source installer exposure", "دسترسی نصب از منابع ناشناس"),
                unknownInstallerCount == 0
                        ? t("No third-party app is currently allowed to install unknown apps", "هیچ برنامه شخص ثالثی در حال حاضر مجاز به نصب برنامه از منابع ناشناس نیست")
                        : t(unknownInstallerCount + " third-party app(s) can install packages from outside trusted app stores — verify every allowed installer and revoke access you do not need",
                                unknownInstallerCount + " برنامه شخص ثالث می‌تواند بسته‌های خارج از فروشگاه‌های مورداعتماد را نصب کند — همه موارد را بررسی و دسترسی غیرضروری را لغو کنید"),
                unknownInstallerCount == 0,
                () -> openSettings(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES)));

        LinearLayout summary = card();''',
    "actionable unknown-source installer audit row",
)

rep(
    '''        content.addView(deviceAdmins);''',
    '''        content.addView(deviceAdmins);

        LinearLayout unknownInstallers = card();
        int allowedUnknownInstallers = allowedThirdPartyUnknownSourceInstallerCount();
        unknownInstallers.addView(tv(t("Unknown-source installer exposure", "دسترسی نصب از منابع ناشناس"), 16, NAVY, true));
        unknownInstallers.addView(tv(allowedUnknownInstallers == 0
                ? t("No third-party app is currently allowed to install unknown apps", "هیچ برنامه شخص ثالثی در حال حاضر مجاز به نصب برنامه از منابع ناشناس نیست")
                : t(allowedUnknownInstallers + " third-party app(s) currently have install-unknown-apps access and should be reviewed",
                        allowedUnknownInstallers + " برنامه شخص ثالث در حال حاضر دسترسی نصب از منابع ناشناس دارد و باید بررسی شود"),
                13, allowedUnknownInstallers == 0 ? GOOD : WARN, allowedUnknownInstallers != 0));
        unknownInstallers.addView(tv(t("This access can be legitimate for enterprise deployment or trusted alternative stores. VARA reports it as a review signal only and does not classify the app as malicious or block SafePay automatically.",
                "این دسترسی می‌تواند برای استقرار سازمانی یا فروشگاه جایگزین مورداعتماد کاملاً مجاز باشد. VARA آن را فقط سیگنال بررسی می‌داند و برنامه را بدافزار تلقی یا SafePay را خودکار مسدود نمی‌کند."), 12, MUTED, false));
        content.addView(unknownInstallers);''',
    "compatibility unknown-source installer card",
)

# Version metadata.
s = s.replace('0.7.8 ALPHA', '0.7.9 ALPHA')
s = s.replace('0.7.8 Alpha • versionCode 708', '0.7.9 Alpha • versionCode 709')
s = s.replace('0.7.8 Alpha', '0.7.9 Alpha')
s = s.replace('VARA 0.7.8 requires Android 8.0 / API 26 or newer.', 'VARA 0.7.9 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+708\b', 'versionCode 709', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.7\.8-alpha['\"]", "versionName '0.7.9-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'allowedThirdPartyUnknownSourceInstallerCount()',
    'android:request_install_packages',
    'android.Manifest.permission.REQUEST_INSTALL_PACKAGES',
    'Unknown-source installer exposure',
    'Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES',
    'does not classify the app as malicious or block SafePay automatically',
    '0.7.9 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.7.9 unknown-source installer exposure audit patch applied")
