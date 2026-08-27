from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_109.py <android-project-root>")

root = Path(sys.argv[1])
java = root / "app/src/main/java/com/varasecurity/alpha031/MainActivity.java"
gradle = root / "app/build.gradle"
s = java.read_text(encoding="utf-8")

required = [
    '0.10.8 ALPHA',
    'deviceIntegrityIndicators()',
    'configuredSystemProxy()',
    'Protected script-dialog policy',
]
for marker in required:
    if marker not in s:
        raise SystemExit(f"missing validated 0.10.8 prerequisite: {marker}")

helpers = r'''
    private int deviceEncryptionStatus() {
        try {
            android.app.admin.DevicePolicyManager dpm =
                    (android.app.admin.DevicePolicyManager) getSystemService(android.content.Context.DEVICE_POLICY_SERVICE);
            return dpm == null ? android.app.admin.DevicePolicyManager.ENCRYPTION_STATUS_UNSUPPORTED
                    : dpm.getStorageEncryptionStatus();
        } catch (Exception ignored) {
            return android.app.admin.DevicePolicyManager.ENCRYPTION_STATUS_UNSUPPORTED;
        }
    }

    private boolean deviceEncryptionSecure() {
        int status = deviceEncryptionStatus();
        return status == android.app.admin.DevicePolicyManager.ENCRYPTION_STATUS_ACTIVE
                || status == android.app.admin.DevicePolicyManager.ENCRYPTION_STATUS_ACTIVE_DEFAULT_KEY
                || status == android.app.admin.DevicePolicyManager.ENCRYPTION_STATUS_ACTIVE_PER_USER;
    }

    private String deviceEncryptionDetail() {
        int status = deviceEncryptionStatus();
        if (status == android.app.admin.DevicePolicyManager.ENCRYPTION_STATUS_ACTIVE_PER_USER) {
            return t("File-based encryption is active for the current user", "رمزگذاری مبتنی بر فایل برای کاربر فعلی فعال است");
        }
        if (status == android.app.admin.DevicePolicyManager.ENCRYPTION_STATUS_ACTIVE
                || status == android.app.admin.DevicePolicyManager.ENCRYPTION_STATUS_ACTIVE_DEFAULT_KEY) {
            return t("Device storage encryption is active", "رمزگذاری فضای ذخیره‌سازی دستگاه فعال است");
        }
        if (status == android.app.admin.DevicePolicyManager.ENCRYPTION_STATUS_ACTIVATING) {
            return t("Storage encryption is still activating; review device security before sensitive use",
                    "رمزگذاری فضای ذخیره‌سازی هنوز در حال فعال‌شدن است؛ پیش از استفاده حساس، امنیت دستگاه را بررسی کنید");
        }
        if (status == android.app.admin.DevicePolicyManager.ENCRYPTION_STATUS_INACTIVE) {
            return t("Device storage encryption is not active", "رمزگذاری فضای ذخیره‌سازی دستگاه فعال نیست");
        }
        return t("Storage encryption status could not be verified on this device",
                "وضعیت رمزگذاری فضای ذخیره‌سازی در این دستگاه قابل تأیید نیست");
    }

'''
anchor = '    private String configuredSystemProxy() {'
if s.count(anchor) != 1:
    raise SystemExit(f"patch failed [encryption helper anchor]: found {s.count(anchor)}")
s = s.replace(anchor, helpers + anchor, 1)

count_anchor = '''        if (deviceIntegrityIndicators() != null) n++;
        return n;'''
if s.count(count_anchor) != 1:
    raise SystemExit(f"patch failed [audit count anchor]: found {s.count(count_anchor)}")
s = s.replace(count_anchor, '''        if (deviceIntegrityIndicators() != null) n++;
        if (!deviceEncryptionSecure()) n++;
        return n;''', 1)

row_anchor = '''        String integrityIndicators = deviceIntegrityIndicators();
        content.addView(auditRow(
                t("Device integrity indicators", "نشانه‌های یکپارچگی دستگاه"),
                deviceIntegrityDetail(integrityIndicators),
                integrityIndicators == null,
                () -> openSettings(Settings.ACTION_SECURITY_SETTINGS)));

        LinearLayout summary = card();'''
if s.count(row_anchor) != 1:
    raise SystemExit(f"patch failed [audit row anchor]: found {s.count(row_anchor)}")
s = s.replace(row_anchor, '''        String integrityIndicators = deviceIntegrityIndicators();
        content.addView(auditRow(
                t("Device integrity indicators", "نشانه‌های یکپارچگی دستگاه"),
                deviceIntegrityDetail(integrityIndicators),
                integrityIndicators == null,
                () -> openSettings(Settings.ACTION_SECURITY_SETTINGS)));

        content.addView(auditRow(
                t("Storage encryption", "رمزگذاری فضای ذخیره‌سازی"),
                deviceEncryptionDetail(),
                deviceEncryptionSecure(),
                () -> openSettings(Settings.ACTION_SECURITY_SETTINGS)));

        LinearLayout summary = card();''', 1)

compat_anchor = '        LinearLayout backgroundIsolation = card();'
if s.count(compat_anchor) != 1:
    raise SystemExit(f"patch failed [compatibility anchor]: found {s.count(compat_anchor)}")
compat_card = '''        LinearLayout encryptionCard = card();
        boolean storageEncrypted = deviceEncryptionSecure();
        encryptionCard.addView(tv(t("Storage encryption", "رمزگذاری فضای ذخیره‌سازی"), 16, NAVY, true));
        encryptionCard.addView(tv(deviceEncryptionDetail(), 13,
                storageEncrypted ? GOOD : WARN, !storageEncrypted));
        encryptionCard.addView(tv(t("This check uses Android's device encryption status and adds a review finding when encryption cannot be verified as active.",
                "این بررسی از وضعیت رمزگذاری Android استفاده می‌کند و اگر فعال‌بودن رمزگذاری قابل تأیید نباشد، یک مورد برای بازبینی اضافه می‌کند."), 12, MUTED, false));
        content.addView(encryptionCard);

'''
s = s.replace(compat_anchor, compat_card + compat_anchor, 1)

s = s.replace('0.10.8 ALPHA', '0.10.9 ALPHA')
s = s.replace('0.10.8 Alpha • versionCode 1008', '0.10.9 Alpha • versionCode 1009')
s = s.replace('0.10.8 Alpha', '0.10.9 Alpha')
s = s.replace('VARA 0.10.8 requires Android 8.0 / API 26 or newer.', 'VARA 0.10.9 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+1008\b', 'versionCode 1009', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.10\.8-alpha['\"]", "versionName '0.10.9-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'deviceEncryptionStatus()',
    'deviceEncryptionSecure()',
    'deviceEncryptionDetail()',
    'Storage encryption',
    'ENCRYPTION_STATUS_ACTIVE_PER_USER',
    '0.10.9 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.10.9 storage encryption audit patch applied")
