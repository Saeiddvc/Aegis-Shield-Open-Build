from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_081.py <android-project-root>")

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

# 0.8.1: expose non-system, non-default-SMS apps that currently hold a granted
# READ_SMS or RECEIVE_SMS permission. This is a review signal for OTP/message
# confidentiality; it is not malware evidence and does not independently block SafePay.
sms_helpers = r'''
    private java.util.List<String> thirdPartySmsAccessApps() {
        java.util.ArrayList<String> exposed = new java.util.ArrayList<>();
        try {
            android.content.pm.PackageManager pm = getPackageManager();
            String defaultSms = null;
            try { defaultSms = android.provider.Telephony.Sms.getDefaultSmsPackage(this); }
            catch (Exception ignored) { }
            java.util.List<android.content.pm.PackageInfo> packages =
                    pm.getInstalledPackages(android.content.pm.PackageManager.GET_PERMISSIONS);
            if (packages == null) return exposed;
            java.util.HashSet<String> seen = new java.util.HashSet<>();
            for (android.content.pm.PackageInfo pi : packages) {
                if (pi == null || pi.packageName == null || pi.applicationInfo == null) continue;
                String pkg = pi.packageName;
                if (getPackageName().equals(pkg) || pkg.equals(defaultSms) || !seen.add(pkg)) continue;
                android.content.pm.ApplicationInfo app = pi.applicationInfo;
                boolean systemApp = (app.flags & android.content.pm.ApplicationInfo.FLAG_SYSTEM) != 0
                        || (app.flags & android.content.pm.ApplicationInfo.FLAG_UPDATED_SYSTEM_APP) != 0;
                if (systemApp || pi.requestedPermissions == null || pi.requestedPermissionsFlags == null) continue;
                boolean grantedSensitiveSms = false;
                int lim = Math.min(pi.requestedPermissions.length, pi.requestedPermissionsFlags.length);
                for (int i = 0; i < lim; i++) {
                    String permission = pi.requestedPermissions[i];
                    boolean sensitiveSms = android.Manifest.permission.READ_SMS.equals(permission)
                            || android.Manifest.permission.RECEIVE_SMS.equals(permission);
                    boolean granted = (pi.requestedPermissionsFlags[i]
                            & android.content.pm.PackageInfo.REQUESTED_PERMISSION_GRANTED) != 0;
                    if (sensitiveSms && granted) {
                        grantedSensitiveSms = true;
                        break;
                    }
                }
                if (!grantedSensitiveSms) continue;
                String label;
                try { label = String.valueOf(pm.getApplicationLabel(app)); }
                catch (Exception ignored) { label = pkg; }
                exposed.add(label + " (" + pkg + ")");
            }
            java.util.Collections.sort(exposed, String.CASE_INSENSITIVE_ORDER);
        } catch (Exception ignored) { }
        return exposed;
    }

    private String smsAccessExposureDetail(java.util.List<String> apps) {
        if (apps == null || apps.isEmpty()) {
            return t("No non-system, non-default SMS app currently has granted SMS-reading or SMS-receiving access",
                    "هیچ برنامه غیرسیستمی و غیرپیش‌فرض پیامک، در حال حاضر دسترسی فعال خواندن یا دریافت پیامک ندارد");
        }
        int visible = Math.min(3, apps.size());
        String names = android.text.TextUtils.join(", ", apps.subList(0, visible));
        if (apps.size() > visible) names += " +" + (apps.size() - visible);
        return t(apps.size() + " third-party app(s) can access SMS/OTP content — review and revoke access that is not essential: " + names,
                apps.size() + " برنامه شخص ثالث می‌تواند به محتوای پیامک/رمز یکبارمصرف دسترسی داشته باشد — موارد غیرضروری را بررسی و لغو کنید: " + names);
    }

'''
rep(
    '    private String recommendedActionTitle(int deviceIssues, int appFindings) {',
    sms_helpers + '    private String recommendedActionTitle(int deviceIssues, int appFindings) {',
    "SMS/OTP exposure helpers",
)

rep(
    '''        if (activeThirdPartyDeviceAdminCount() > 0) n++;
        if (allowedThirdPartyUnknownSourceInstallerCount() > 0) n++;
        return n;''',
    '''        if (activeThirdPartyDeviceAdminCount() > 0) n++;
        if (allowedThirdPartyUnknownSourceInstallerCount() > 0) n++;
        if (!thirdPartySmsAccessApps().isEmpty()) n++;
        return n;''',
    "SMS/OTP exposure in device trust score",
)

rep(
    '''        int unknownInstallerCount = allowedThirdPartyUnknownSourceInstallerCount();
        content.addView(auditRow(
                t("Unknown-source installer exposure", "دسترسی نصب از منابع ناشناس"),
                unknownInstallerCount == 0
                        ? t("No third-party app is currently allowed to install unknown apps", "هیچ برنامه شخص ثالثی در حال حاضر مجاز به نصب برنامه از منابع ناشناس نیست")
                        : t(unknownInstallerCount + " third-party app(s) can install packages from outside trusted app stores — verify every allowed installer and revoke access you do not need",
                                unknownInstallerCount + " برنامه شخص ثالث می‌تواند بسته‌های خارج از فروشگاه‌های مورداعتماد را نصب کند — همه موارد را بررسی و دسترسی غیرضروری را لغو کنید"),
                unknownInstallerCount == 0,
                () -> openSettings(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES)));

        LinearLayout summary = card();''',
    '''        int unknownInstallerCount = allowedThirdPartyUnknownSourceInstallerCount();
        content.addView(auditRow(
                t("Unknown-source installer exposure", "دسترسی نصب از منابع ناشناس"),
                unknownInstallerCount == 0
                        ? t("No third-party app is currently allowed to install unknown apps", "هیچ برنامه شخص ثالثی در حال حاضر مجاز به نصب برنامه از منابع ناشناس نیست")
                        : t(unknownInstallerCount + " third-party app(s) can install packages from outside trusted app stores — verify every allowed installer and revoke access you do not need",
                                unknownInstallerCount + " برنامه شخص ثالث می‌تواند بسته‌های خارج از فروشگاه‌های مورداعتماد را نصب کند — همه موارد را بررسی و دسترسی غیرضروری را لغو کنید"),
                unknownInstallerCount == 0,
                () -> openSettings(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES)));

        java.util.List<String> smsAccessApps = thirdPartySmsAccessApps();
        content.addView(auditRow(
                t("SMS / OTP access exposure", "دسترسی به پیامک / رمز یکبارمصرف"),
                smsAccessExposureDetail(smsAccessApps),
                smsAccessApps.isEmpty(),
                () -> openSettings(Settings.ACTION_APPLICATION_SETTINGS)));

        LinearLayout summary = card();''',
    "actionable SMS/OTP exposure audit row",
)

rep(
    '''        content.addView(unknownInstallers);''',
    '''        content.addView(unknownInstallers);

        LinearLayout smsExposure = card();
        java.util.List<String> compatibilitySmsApps = thirdPartySmsAccessApps();
        smsExposure.addView(tv(t("SMS / OTP access exposure", "دسترسی به پیامک / رمز یکبارمصرف"), 16, NAVY, true));
        smsExposure.addView(tv(smsAccessExposureDetail(compatibilitySmsApps), 13,
                compatibilitySmsApps.isEmpty() ? GOOD : WARN, !compatibilitySmsApps.isEmpty()));
        smsExposure.addView(tv(t("VARA excludes system apps and the current default SMS app. This is a confidentiality review signal only; it does not classify an app as malicious or automatically block SafePay.",
                "VARA برنامه‌های سیستمی و برنامه پیش‌فرض فعلی پیامک را از این بررسی کنار می‌گذارد. این مورد فقط سیگنال بازبینی محرمانگی است و برنامه را بدافزار تلقی یا SafePay را خودکار مسدود نمی‌کند."), 12, MUTED, false));
        content.addView(smsExposure);''',
    "compatibility SMS/OTP exposure card",
)

# Version metadata.
s = s.replace('0.8.0 ALPHA', '0.8.1 ALPHA')
s = s.replace('0.8.0 Alpha • versionCode 800', '0.8.1 Alpha • versionCode 801')
s = s.replace('0.8.0 Alpha', '0.8.1 Alpha')
s = s.replace('VARA 0.8.0 requires Android 8.0 / API 26 or newer.', 'VARA 0.8.1 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+800\b', 'versionCode 801', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.8\.0-alpha['\"]", "versionName '0.8.1-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'thirdPartySmsAccessApps()',
    'smsAccessExposureDetail(',
    'android.Manifest.permission.READ_SMS',
    'android.Manifest.permission.RECEIVE_SMS',
    'REQUESTED_PERMISSION_GRANTED',
    'Telephony.Sms.getDefaultSmsPackage',
    'SMS / OTP access exposure',
    'Settings.ACTION_APPLICATION_SETTINGS',
    'does not classify an app as malicious or automatically block SafePay',
    '0.8.1 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.8.1 SMS/OTP access exposure audit patch applied")
