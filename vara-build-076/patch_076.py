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

# Security-patch freshness already exists in the validated 0.6.4 chain.
# 0.7.6 makes that signal easier to interpret and surfaces it in Device Compatibility
# without duplicating helpers or changing the 180-day posture threshold.
rep(
    '''        long patchAge = securityPatchAgeDays();
        boolean patchFresh = securityPatchFresh();
        String freshnessPatchLevel = android.os.Build.VERSION.SECURITY_PATCH;
        String patchDetail;
        if (freshnessPatchLevel == null || freshnessPatchLevel.trim().isEmpty() || patchAge == Long.MAX_VALUE) {
            patchDetail = t("Security patch level unavailable — review system updates",
                    "سطح وصله امنیتی در دسترس نیست — به‌روزرسانی‌های سیستم را بررسی کنید");
        } else if (patchFresh) {
            patchDetail = t("Patch " + freshnessPatchLevel + " — " + patchAge + " days old",
                    "وصله " + freshnessPatchLevel + " — مربوط به " + patchAge + " روز قبل");
        } else {
            patchDetail = t("Patch " + freshnessPatchLevel + " — older than 180 days; review system updates",
                    "وصله " + freshnessPatchLevel + " — قدیمی‌تر از ۱۸۰ روز؛ به‌روزرسانی سیستم را بررسی کنید");
        }
        content.addView(auditRow(
                t("Android security patch", "وصله امنیتی اندروید"),
                patchDetail,
                patchFresh,
                () -> openSettings(Settings.ACTION_SECURITY_SETTINGS)));''',
    '''        long patchAge = securityPatchAgeDays();
        boolean patchFresh = securityPatchFresh();
        String freshnessPatchLevel = android.os.Build.VERSION.SECURITY_PATCH;
        String patchDetail;
        if (freshnessPatchLevel == null || freshnessPatchLevel.trim().isEmpty() || patchAge == Long.MAX_VALUE) {
            patchDetail = t("Patch level unavailable — review Android security and system updates",
                    "سطح وصله در دسترس نیست — امنیت و به‌روزرسانی سیستم اندروید را بررسی کنید");
        } else if (patchFresh) {
            patchDetail = t("Patch " + freshnessPatchLevel + " • " + patchAge + " day(s) old • within VARA's 180-day review window",
                    "وصله " + freshnessPatchLevel + " • مربوط به " + patchAge + " روز قبل • در محدوده بررسی ۱۸۰ روزه VARA");
        } else {
            patchDetail = t("Patch " + freshnessPatchLevel + " • older than 180 days — check for a manufacturer or carrier system update",
                    "وصله " + freshnessPatchLevel + " • قدیمی‌تر از ۱۸۰ روز — به‌روزرسانی سازنده یا اپراتور را بررسی کنید");
        }
        content.addView(auditRow(
                t("Android security patch", "وصله امنیتی اندروید"),
                patchDetail,
                patchFresh,
                () -> openSettings(Settings.ACTION_SECURITY_SETTINGS)));''',
    "security patch audit interpretation",
)

rep(
    '''        content.addView(keyboards);''',
    '''        content.addView(keyboards);

        LinearLayout securityPatch = card();
        long patchAgeDays = securityPatchAgeDays();
        boolean currentPatch = securityPatchFresh();
        String devicePatch = android.os.Build.VERSION.SECURITY_PATCH == null || android.os.Build.VERSION.SECURITY_PATCH.trim().isEmpty()
                ? t("Unknown", "نامشخص") : android.os.Build.VERSION.SECURITY_PATCH;
        securityPatch.addView(tv(t("Android security patch", "وصله امنیتی اندروید"), 16, NAVY, true));
        securityPatch.addView(tv(currentPatch
                ? t("Patch " + devicePatch + " • " + patchAgeDays + " day(s) old", "وصله " + devicePatch + " • مربوط به " + patchAgeDays + " روز قبل")
                : t("Patch " + devicePatch + " needs review because it is older than 180 days or unavailable",
                        "وصله " + devicePatch + " نیاز به بررسی دارد چون بیش از ۱۸۰ روز قدیمی است یا در دسترس نیست"),
                13, currentPatch ? GOOD : WARN, !currentPatch));
        securityPatch.addView(tv(t("Patch age is a device-hygiene signal only; it is not evidence of malware or compromise. Update availability depends on the manufacturer and carrier.",
                "سن وصله فقط یک شاخص بهداشت امنیتی دستگاه است و نشانه بدافزار یا نفوذ نیست. دسترسی به به‌روزرسانی به سازنده دستگاه و اپراتور بستگی دارد."), 12, MUTED, false));
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
    'securityPatchFresh()',
    'android.os.Build.VERSION.SECURITY_PATCH',
    'Android security patch',
    "VARA's 180-day review window",
    'Patch age is a device-hygiene signal only',
    '0.7.6 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.7.6 security-patch freshness UX patch applied")
