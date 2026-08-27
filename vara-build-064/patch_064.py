from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_064.py <android-project-root>")

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

# Security patch freshness is a useful device-posture signal. It does not imply compromise;
# it simply tells the user when the platform patch level deserves review.
rep(
    '''    private boolean automaticTimeZoneEnabled() {
        try { return Settings.Global.getInt(getContentResolver(), Settings.Global.AUTO_TIME_ZONE, 0) == 1; }
        catch (Exception ignored) { return false; }
    }

    private int deviceTrustIssueCount() {''',
    '''    private boolean automaticTimeZoneEnabled() {
        try { return Settings.Global.getInt(getContentResolver(), Settings.Global.AUTO_TIME_ZONE, 0) == 1; }
        catch (Exception ignored) { return false; }
    }

    private long securityPatchAgeDays() {
        String patch = android.os.Build.VERSION.SECURITY_PATCH;
        if (patch == null || patch.trim().isEmpty()) return Long.MAX_VALUE;
        try {
            java.time.LocalDate patchDate = java.time.LocalDate.parse(patch.trim());
            return java.time.temporal.ChronoUnit.DAYS.between(patchDate, java.time.LocalDate.now());
        } catch (Exception ignored) {
            return Long.MAX_VALUE;
        }
    }

    private boolean securityPatchFresh() {
        long age = securityPatchAgeDays();
        return age >= 0 && age <= 180;
    }

    private int deviceTrustIssueCount() {''',
    "security patch freshness helpers",
)

rep(
    '''        if (!automaticTimeEnabled()) n++;
        if (!automaticTimeZoneEnabled()) n++;
        return n;''',
    '''        if (!automaticTimeEnabled()) n++;
        if (!automaticTimeZoneEnabled()) n++;
        if (!securityPatchFresh()) n++;
        return n;''',
    "security patch freshness in device trust score",
)

rep(
    '''        boolean autoZone = automaticTimeZoneEnabled();
        content.addView(auditRow(
                t("Automatic time zone", "منطقه زمانی خودکار"),
                autoZone ? t("Enabled", "فعال")
                        : t("Disabled — verify the device time zone", "غیرفعال است — منطقه زمانی دستگاه را بررسی کنید"),
                autoZone,
                () -> openSettings(Settings.ACTION_DATE_SETTINGS)));

        LinearLayout summary = card();''',
    '''        boolean autoZone = automaticTimeZoneEnabled();
        content.addView(auditRow(
                t("Automatic time zone", "منطقه زمانی خودکار"),
                autoZone ? t("Enabled", "فعال")
                        : t("Disabled — verify the device time zone", "غیرفعال است — منطقه زمانی دستگاه را بررسی کنید"),
                autoZone,
                () -> openSettings(Settings.ACTION_DATE_SETTINGS)));

        long patchAge = securityPatchAgeDays();
        boolean patchFresh = securityPatchFresh();
        String patchLevel = android.os.Build.VERSION.SECURITY_PATCH;
        String patchDetail;
        if (patchLevel == null || patchLevel.trim().isEmpty() || patchAge == Long.MAX_VALUE) {
            patchDetail = t("Security patch level unavailable — review system updates",
                    "سطح وصله امنیتی در دسترس نیست — به‌روزرسانی‌های سیستم را بررسی کنید");
        } else if (patchFresh) {
            patchDetail = t("Patch " + patchLevel + " — " + patchAge + " days old",
                    "وصله " + patchLevel + " — مربوط به " + patchAge + " روز قبل");
        } else {
            patchDetail = t("Patch " + patchLevel + " — older than 180 days; review system updates",
                    "وصله " + patchLevel + " — قدیمی‌تر از ۱۸۰ روز؛ به‌روزرسانی سیستم را بررسی کنید");
        }
        content.addView(auditRow(
                t("Android security patch", "وصله امنیتی اندروید"),
                patchDetail,
                patchFresh,
                () -> openSettings(Settings.ACTION_SECURITY_SETTINGS)));

        LinearLayout summary = card();''',
    "actionable security patch audit row",
)

# Payment protection: WebView can ask to resubmit a POST after refresh/back navigation.
# In a protected payment session, fail closed and choose dontResend to reduce accidental
# duplicate payment submissions.
rep(
    '''            @Override public void onReceivedHttpAuthRequest(WebView view, android.webkit.HttpAuthHandler handler, String host, String realm) {''',
    '''            @Override public void onFormResubmission(WebView view, android.os.Message dontResend, android.os.Message resend) {
                if (dontResend != null) dontResend.sendToTarget();
                recordActivity(t("Protected browser blocked a form resubmission",
                        "مرورگر محافظت‌شده ارسال مجدد فرم را مسدود کرد"));
                Toast.makeText(MainActivity.this,
                        t("Form resubmission blocked to prevent duplicate submission", "ارسال مجدد فرم برای جلوگیری از ثبت تکراری مسدود شد"),
                        Toast.LENGTH_LONG).show();
            }
            @Override public void onReceivedHttpAuthRequest(WebView view, android.webkit.HttpAuthHandler handler, String host, String realm) {''',
    "protected form resubmission fail-closed handling",
)

rep(
    '• Popups, secondary windows and web file uploads are blocked',
    '• Popups, secondary windows and web file uploads are blocked\\n• Form resubmission is blocked to reduce accidental duplicate payment posts',
    "english protected-session form disclosure",
)
rep(
    '• پنجره‌های بازشو، پنجره‌های ثانویه و بارگذاری فایل وب مسدود می‌شوند',
    '• پنجره‌های بازشو، پنجره‌های ثانویه و بارگذاری فایل وب مسدود می‌شوند\\n• ارسال مجدد فرم برای کاهش خطر ثبت تکراری پرداخت مسدود می‌شود',
    "persian protected-session form disclosure",
)

# Version metadata.
s = s.replace('0.6.3 ALPHA', '0.6.4 ALPHA')
s = s.replace('0.6.3 Alpha • versionCode 603', '0.6.4 Alpha • versionCode 604')
s = s.replace('0.6.3 Alpha', '0.6.4 Alpha')
s = s.replace('VARA 0.6.3 requires Android 8.0 / API 26 or newer.', 'VARA 0.6.4 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+603\b', 'versionCode 604', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.6\.3-alpha['\"]", "versionName '0.6.4-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'securityPatchAgeDays()',
    'securityPatchFresh()',
    'Android security patch',
    'older than 180 days',
    'onFormResubmission',
    'dontResend.sendToTarget()',
    'Form resubmission blocked to prevent duplicate submission',
    '0.6.4 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.6.4 security-patch audit and payment form-resubmission hardening patch applied")
