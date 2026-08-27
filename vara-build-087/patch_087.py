from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_087.py <android-project-root>")

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

# 0.8.7: add a conservative, review-only device integrity indicator audit.
# This intentionally avoids claiming root/malware detection. It only reports a
# small set of high-signal build/file indicators that warrant manual review.
integrity_helpers = r'''
    private String deviceIntegrityIndicators() {
        java.util.ArrayList<String> hits = new java.util.ArrayList<>();
        try {
            String tags = android.os.Build.TAGS;
            if (tags != null && tags.contains("test-keys")) hits.add("build:test-keys");
        } catch (Exception ignored) {}

        String[] paths = new String[] {
                "/system/bin/su",
                "/system/xbin/su",
                "/sbin/su",
                "/system/app/Superuser.apk",
                "/system/app/Magisk.apk",
                "/data/adb/magisk"
        };
        for (String p : paths) {
            try {
                if (new java.io.File(p).exists()) hits.add(p);
            } catch (Exception ignored) {}
        }
        if (hits.isEmpty()) return null;
        return android.text.TextUtils.join(", ", hits);
    }

    private String deviceIntegrityDetail(String indicators) {
        if (indicators == null || indicators.isEmpty()) {
            return t("No common root/modified-system indicators were observed by this lightweight check",
                    "در این بررسی سبک، نشانه متداولی از روت یا تغییر سیستم مشاهده نشد");
        }
        return t("Review device integrity indicators: " + indicators + ". This is a heuristic signal, not proof of root, compromise or malware.",
                "نشانه‌های یکپارچگی دستگاه را بررسی کنید: " + indicators + ". این فقط یک سیگنال اکتشافی است و اثبات روت، نفوذ یا بدافزار نیست.");
    }

'''
rep(
    '    private String configuredSystemProxy() {',
    integrity_helpers + '    private String configuredSystemProxy() {',
    "device integrity helper methods",
)

rep(
    '''        if (!thirdPartySmsAccessApps().isEmpty()) n++;
        if (enabledThirdPartyAutofillService() != null) n++;
        if (configuredSystemProxy() != null) n++;
        return n;''',
    '''        if (!thirdPartySmsAccessApps().isEmpty()) n++;
        if (enabledThirdPartyAutofillService() != null) n++;
        if (configuredSystemProxy() != null) n++;
        if (deviceIntegrityIndicators() != null) n++;
        return n;''',
    "device integrity signal in device trust score",
)

rep(
    '''        String configuredProxy = configuredSystemProxy();
        content.addView(auditRow(
                t("System proxy exposure", "پراکسی سیستمی"),
                proxyExposureDetail(configuredProxy),
                configuredProxy == null,
                () -> openSettings(Settings.ACTION_WIFI_SETTINGS)));

        LinearLayout summary = card();''',
    '''        String configuredProxy = configuredSystemProxy();
        content.addView(auditRow(
                t("System proxy exposure", "پراکسی سیستمی"),
                proxyExposureDetail(configuredProxy),
                configuredProxy == null,
                () -> openSettings(Settings.ACTION_WIFI_SETTINGS)));

        String integrityIndicators = deviceIntegrityIndicators();
        content.addView(auditRow(
                t("Device integrity indicators", "نشانه‌های یکپارچگی دستگاه"),
                deviceIntegrityDetail(integrityIndicators),
                integrityIndicators == null,
                () -> openSettings(Settings.ACTION_SECURITY_SETTINGS)));

        LinearLayout summary = card();''',
    "actionable device integrity audit row",
)

rep(
    '''        content.addView(proxyExposure);

        LinearLayout backgroundIsolation = card();''',
    '''        content.addView(proxyExposure);

        LinearLayout integrityExposure = card();
        String compatibilityIntegrity = deviceIntegrityIndicators();
        integrityExposure.addView(tv(t("Device integrity indicators", "نشانه‌های یکپارچگی دستگاه"), 16, NAVY, true));
        integrityExposure.addView(tv(deviceIntegrityDetail(compatibilityIntegrity), 13,
                compatibilityIntegrity == null ? GOOD : WARN, compatibilityIntegrity != null));
        integrityExposure.addView(tv(t("This is a lightweight heuristic review signal only. It does not prove root, compromise or malware, and it does not independently block SafePay.",
                "این فقط یک سیگنال سبک و اکتشافی برای بازبینی است؛ روت، نفوذ یا بدافزار را اثبات نمی‌کند و به‌تنهایی SafePay را مسدود نمی‌کند."), 12, MUTED, false));
        content.addView(integrityExposure);

        LinearLayout backgroundIsolation = card();''',
    "compatibility device integrity card",
)

# Version metadata.
s = s.replace('0.8.6 ALPHA', '0.8.7 ALPHA')
s = s.replace('0.8.6 Alpha • versionCode 806', '0.8.7 Alpha • versionCode 807')
s = s.replace('0.8.6 Alpha', '0.8.7 Alpha')
s = s.replace('VARA 0.8.6 requires Android 8.0 / API 26 or newer.', 'VARA 0.8.7 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+806\b', 'versionCode 807', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.8\.6-alpha['\"]", "versionName '0.8.7-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'deviceIntegrityIndicators()',
    'deviceIntegrityDetail(',
    'build:test-keys',
    '/system/xbin/su',
    '/data/adb/magisk',
    'Device integrity indicators',
    'heuristic signal, not proof',
    'android.os.Build.TAGS',
    '0.8.7 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.8.7 device integrity indicator audit patch applied")
