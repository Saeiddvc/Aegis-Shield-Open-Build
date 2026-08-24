from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_076.py <android-project-root>")

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

# Security-patch freshness is a device hygiene signal. Treat devices with an unknown,
# unparsable, or older-than-180-day patch level as needing review, not as malware proof.
rep(
    '''    private int enabledThirdPartyInputMethodCount() {''',
    '''    private int securityPatchAgeDays() {
        try {
            String patch = android.os.Build.VERSION.SECURITY_PATCH;
            if (patch == null || patch.trim().isEmpty()) return Integer.MAX_VALUE;
            java.time.LocalDate patchDate = java.time.LocalDate.parse(patch.trim());
            long days = java.time.temporal.ChronoUnit.DAYS.between(patchDate, java.time.LocalDate.now());
            if (days < 0) return 0;
            return days > Integer.MAX_VALUE ? Integer.MAX_VALUE : (int) days;
        } catch (Exception ignored) {
            return Integer.MAX_VALUE;
        }
    }

    private boolean securityPatchCurrent() {
        return securityPatchAgeDays() <= 180;
    }

    private int enabledThirdPartyInputMethodCount() {''',
    "security patch freshness helpers",
)

rep(
    '''        if (enabledThirdPartyNotificationListenerCount() > 0) n++;
        if (enabledThirdPartyOverlayCount() > 0) n++;
        if (enabledThirdPartyInputMethodCount() > 0) n++;
        return n;''',
    '''        if (enabledThirdPartyNotificationListenerCount() > 0) n++;
        if (enabledThirdPartyOverlayCount() > 0) n++;
        if (enabledThirdPartyInputMethodCount() > 0) n++;
        if (!securityPatchCurrent()) n++;
        return n;''',
    "security patch freshness in device trust score",
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

        int patchAge = securityPatchAgeDays();
        boolean patchCurrent = securityPatchCurrent();
        String patchLevel = android.os.Build.VERSION.SECURITY_PATCH == null || android.os.Build.VERSION.SECURITY_PATCH.trim().isEmpty()
                ? t("Unknown", "نامشخص") : android.os.Build.VERSION.SECURITY_PATCH;
        content.addView(auditRow(
                t("Android security patch", "وصله امنیتی اندروید"),
                patchCurrent
                        ? t("Patch level " + patchLevel + " • " + patchAge + " day(s) old", "سطح وصله " + patchLevel + " • " + patchAge + " روز از آن گذشته است")
                        : t("Patch level " + patchLevel + " is older than 180 days or cannot be verified — check for a system update",
                                "سطح وصله " + patchLevel + " بیش از ۱۸۰ روز قدیمی است یا قابل تأیید نیست — به‌روزرسانی سیستم را بررسی کنید"),
                patchCurrent,
                () -> openSettings(Settings.ACTION_SYSTEM_UPDATE_SETTINGS)));

        LinearLayout summary = card();''',
    "actionable Android security patch audit row",
)

rep(
    '''        content.addView(keyboards);''',
    '''        content.addView(keyboards);

        LinearLayout securityPatch = card();
        int patchAgeDays = securityPatchAgeDays();
        boolean currentPatch = securityPatchCurrent();
        String devicePatch = android.os.Build.VERSION.SECURITY_PATCH == null || android.os.Build.VERSION.SECURITY_PATCH.trim().isEmpty()
                ? t("Unknown", "نامشخص") : android.os.Build.VERSION.SECURITY_PATCH;
        securityPatch.addView(tv(t("Android security patch", "وصله امنیتی اندروید"), 16, NAVY, true));
        securityPatch.addView(tv(currentPatch
                ? t("Patch level " + devicePatch + " • " + patchAgeDays + " day(s) old", "سطح وصله " + devicePatch + " • " + patchAgeDays + " روز از آن گذشته است")
                : t("Patch level " + devicePatch + " needs review because it is older than 180 days or unavailable",
                        "سطح وصله " + devicePatch + " نیاز به بررسی دارد چون بیش از ۱۸۰ روز قدیمی است یا در دسترس نیست"),
                13, currentPatch ? GOOD : WARN, !currentPatch));
        securityPatch.addView(tv(t("VARA uses patch age as a device-hygiene signal only. Update availability depends on the device manufacturer and carrier.",
                "VARA سن وصله را فقط به‌عنوان شاخص بهداشت امنیتی دستگاه در نظر می‌گیرد. دسترسی به به‌روزرسانی به سازنده دستگاه و اپراتور بستگی دارد."), 12, MUTED, false));
        content.addView(securityPatch);''',
    "compatibility security patch card",
)

# Version metadata.
s = s.replace('0.7.5 ALPHA', '0.7.6 ALPHA')
s = s.replace('0.7.5 Alpha • versionCode 705', '0.7.6 Alpha • versionCode 706')
s = s.replace('0.7.5 Alpha', '0.7.6 Alpha')
s = s.replace('VARA 0.7.5 requires Android 8.0 / API 26 or newer.', 'VARA 0.7.6 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+705\b', 'versionCode 706', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.7\.5-alpha['\"]", "versionName '0.7.6-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'securityPatchAgeDays()',
    'securityPatchCurrent()',
    'android.os.Build.VERSION.SECURITY_PATCH',
    'java.time.temporal.ChronoUnit.DAYS.between',
    'Android security patch',
    'Settings.ACTION_SYSTEM_UPDATE_SETTINGS',
    'older than 180 days',
    '0.7.6 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.7.6 Android security-patch freshness audit patch applied")
