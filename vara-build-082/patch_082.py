from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_082.py <android-project-root>")

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

# 0.8.2: expose an enabled third-party Autofill Service as a review signal.
# Autofill providers can receive form structure/data by design. VARA treats this
# as a transparency/remediation finding only; it is not malware evidence and
# does not independently block SafePay. Protected WebView autofill remains off.
autofill_helpers = r'''
    private String enabledThirdPartyAutofillService() {
        try {
            String flat = android.provider.Settings.Secure.getString(
                    getContentResolver(), "autofill_service");
            if (flat == null || flat.trim().isEmpty()) return null;
            android.content.ComponentName component = android.content.ComponentName.unflattenFromString(flat);
            String pkg = component != null ? component.getPackageName() : flat.split("/", 2)[0];
            if (pkg == null || pkg.isEmpty() || getPackageName().equals(pkg)) return null;
            android.content.pm.PackageManager pm = getPackageManager();
            android.content.pm.ApplicationInfo app = pm.getApplicationInfo(pkg, 0);
            boolean systemApp = (app.flags & android.content.pm.ApplicationInfo.FLAG_SYSTEM) != 0
                    || (app.flags & android.content.pm.ApplicationInfo.FLAG_UPDATED_SYSTEM_APP) != 0;
            if (systemApp) return null;
            String label;
            try { label = String.valueOf(pm.getApplicationLabel(app)); }
            catch (Exception ignored) { label = pkg; }
            return label + " (" + pkg + ")";
        } catch (Exception ignored) {
            return null;
        }
    }

    private String autofillExposureDetail(String provider) {
        if (provider == null || provider.isEmpty()) {
            return t("No enabled third-party Autofill Service was detected",
                    "هیچ سرویس تکمیل خودکار شخص ثالث فعالی شناسایی نشد");
        }
        return t("A third-party Autofill Service is enabled and may receive form structure/data by design — verify that you trust and still need it: " + provider,
                "یک سرویس تکمیل خودکار شخص ثالث فعال است و طبق طراحی می‌تواند ساختار/داده فرم را دریافت کند — مطمئن شوید به آن اعتماد دارید و هنوز به آن نیاز دارید: " + provider);
    }

'''
rep(
    '    private String recommendedActionTitle(int deviceIssues, int appFindings) {',
    autofill_helpers + '    private String recommendedActionTitle(int deviceIssues, int appFindings) {',
    "Autofill exposure helpers",
)

rep(
    '''        if (activeThirdPartyDeviceAdminCount() > 0) n++;
        if (allowedThirdPartyUnknownSourceInstallerCount() > 0) n++;
        if (!thirdPartySmsAccessApps().isEmpty()) n++;
        return n;''',
    '''        if (activeThirdPartyDeviceAdminCount() > 0) n++;
        if (allowedThirdPartyUnknownSourceInstallerCount() > 0) n++;
        if (!thirdPartySmsAccessApps().isEmpty()) n++;
        if (enabledThirdPartyAutofillService() != null) n++;
        return n;''',
    "Autofill exposure in device trust score",
)

rep(
    '''        java.util.List<String> smsAccessApps = thirdPartySmsAccessApps();
        content.addView(auditRow(
                t("SMS / OTP access exposure", "دسترسی به پیامک / رمز یکبارمصرف"),
                smsAccessExposureDetail(smsAccessApps),
                smsAccessApps.isEmpty(),
                () -> openSettings(Settings.ACTION_APPLICATION_SETTINGS)));

        LinearLayout summary = card();''',
    '''        java.util.List<String> smsAccessApps = thirdPartySmsAccessApps();
        content.addView(auditRow(
                t("SMS / OTP access exposure", "دسترسی به پیامک / رمز یکبارمصرف"),
                smsAccessExposureDetail(smsAccessApps),
                smsAccessApps.isEmpty(),
                () -> openSettings(Settings.ACTION_APPLICATION_SETTINGS)));

        String autofillProvider = enabledThirdPartyAutofillService();
        content.addView(auditRow(
                t("Autofill service exposure", "دسترسی سرویس تکمیل خودکار"),
                autofillExposureDetail(autofillProvider),
                autofillProvider == null,
                () -> openSettings(Settings.ACTION_SETTINGS)));

        LinearLayout summary = card();''',
    "actionable Autofill exposure audit row",
)

rep(
    '''        content.addView(smsExposure);''',
    '''        content.addView(smsExposure);

        LinearLayout autofillExposure = card();
        String compatibilityAutofillProvider = enabledThirdPartyAutofillService();
        autofillExposure.addView(tv(t("Autofill service exposure", "دسترسی سرویس تکمیل خودکار"), 16, NAVY, true));
        autofillExposure.addView(tv(autofillExposureDetail(compatibilityAutofillProvider), 13,
                compatibilityAutofillProvider == null ? GOOD : WARN, compatibilityAutofillProvider != null));
        autofillExposure.addView(tv(t("VARA reports only an enabled non-system Autofill Service. Password managers can be legitimate; review this signal rather than treating it as malware evidence. Protected sessions keep Android Autofill excluded.",
                "VARA فقط سرویس تکمیل خودکار فعال و غیرسیستمی را گزارش می‌کند. مدیرهای رمز عبور می‌توانند کاملاً معتبر باشند؛ این مورد را برای بازبینی در نظر بگیرید، نه نشانه بدافزار. تکمیل خودکار اندروید در نشست‌های محافظت‌شده VARA غیرفعال می‌ماند."), 12, MUTED, false));
        content.addView(autofillExposure);''',
    "compatibility Autofill exposure card",
)

# Version metadata.
s = s.replace('0.8.1 ALPHA', '0.8.2 ALPHA')
s = s.replace('0.8.1 Alpha • versionCode 801', '0.8.2 Alpha • versionCode 802')
s = s.replace('0.8.1 Alpha', '0.8.2 Alpha')
s = s.replace('VARA 0.8.1 requires Android 8.0 / API 26 or newer.', 'VARA 0.8.2 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+801\b', 'versionCode 802', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.8\.1-alpha['\"]", "versionName '0.8.2-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'enabledThirdPartyAutofillService()',
    'autofillExposureDetail(',
    '"autofill_service"',
    'Autofill service exposure',
    'Settings.ACTION_SETTINGS',
    'Protected sessions keep Android Autofill excluded',
    '0.8.2 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.8.2 Autofill exposure audit patch applied")
