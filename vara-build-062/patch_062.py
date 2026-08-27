from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_062.py <android-project-root>")

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

# Device clock integrity is relevant to TLS validation, token expiry and payment flows.
# Treat disabled automatic time/time-zone as review signals, not compromise indicators.
rep(
    '''    private boolean adbEnabled() {
        try { return Settings.Global.getInt(getContentResolver(), Settings.Global.ADB_ENABLED, 0) == 1; }
        catch (Exception ignored) { return false; }
    }

    private int deviceTrustIssueCount() {''',
    '''    private boolean adbEnabled() {
        try { return Settings.Global.getInt(getContentResolver(), Settings.Global.ADB_ENABLED, 0) == 1; }
        catch (Exception ignored) { return false; }
    }

    private boolean automaticTimeEnabled() {
        try { return Settings.Global.getInt(getContentResolver(), Settings.Global.AUTO_TIME, 0) == 1; }
        catch (Exception ignored) { return false; }
    }

    private boolean automaticTimeZoneEnabled() {
        try { return Settings.Global.getInt(getContentResolver(), Settings.Global.AUTO_TIME_ZONE, 0) == 1; }
        catch (Exception ignored) { return false; }
    }

    private int deviceTrustIssueCount() {''',
    "clock integrity helpers",
)

rep(
    '''        if (!isDeviceLockSecure()) n++;
        if (developerOptionsEnabled()) n++;
        if (adbEnabled()) n++;
        return n;''',
    '''        if (!isDeviceLockSecure()) n++;
        if (developerOptionsEnabled()) n++;
        if (adbEnabled()) n++;
        if (!automaticTimeEnabled()) n++;
        if (!automaticTimeZoneEnabled()) n++;
        return n;''',
    "clock signals in device trust score",
)

# Add actionable clock-integrity rows to the device audit.
rep(
    '''        boolean usbDebug = adbEnabled();
        content.addView(auditRow(
                t("USB debugging", "اشکال‌زدایی USB"),
                usbDebug ? t("ADB is enabled — disable before sensitive sessions unless explicitly required", "ADB فعال است — مگر در صورت نیاز صریح، پیش از نشست حساس غیرفعال شود")
                        : t("Disabled", "غیرفعال"),
                !usbDebug,
                () -> openSettings(Settings.ACTION_APPLICATION_DEVELOPMENT_SETTINGS)));

        LinearLayout summary = card();''',
    '''        boolean usbDebug = adbEnabled();
        content.addView(auditRow(
                t("USB debugging", "اشکال‌زدایی USB"),
                usbDebug ? t("ADB is enabled — disable before sensitive sessions unless explicitly required", "ADB فعال است — مگر در صورت نیاز صریح، پیش از نشست حساس غیرفعال شود")
                        : t("Disabled", "غیرفعال"),
                !usbDebug,
                () -> openSettings(Settings.ACTION_APPLICATION_DEVELOPMENT_SETTINGS)));

        boolean autoTime = automaticTimeEnabled();
        content.addView(auditRow(
                t("Automatic date & time", "تاریخ و زمان خودکار"),
                autoTime ? t("Enabled — device clock follows the network time source", "فعال است — ساعت دستگاه از منبع زمان شبکه پیروی می‌کند")
                        : t("Disabled — review before payment or certificate-sensitive use", "غیرفعال است — پیش از پرداخت یا استفاده حساس به گواهی بررسی شود"),
                autoTime,
                () -> openSettings(Settings.ACTION_DATE_SETTINGS)));

        boolean autoZone = automaticTimeZoneEnabled();
        content.addView(auditRow(
                t("Automatic time zone", "منطقه زمانی خودکار"),
                autoZone ? t("Enabled", "فعال")
                        : t("Disabled — verify the device time zone", "غیرفعال است — منطقه زمانی دستگاه را بررسی کنید"),
                autoZone,
                () -> openSettings(Settings.ACTION_DATE_SETTINGS)));

        LinearLayout summary = card();''',
    "actionable clock audit rows",
)

# Compatibility page now surfaces clock integrity separately from blocking protected-session prerequisites.
rep(
    '''        Button recheck = secondary(t("Recheck compatibility", "بررسی مجدد سازگاری"));''',
    '''        LinearLayout clock = card();
        boolean clockReady = automaticTimeEnabled() && automaticTimeZoneEnabled();
        clock.addView(tv(t("Clock integrity", "یکپارچگی ساعت"), 16, NAVY, true));
        clock.addView(tv(clockReady
                ? t("Automatic date/time and time zone are enabled", "تاریخ/زمان و منطقه زمانی خودکار فعال هستند")
                : t("Review date/time settings before certificate-sensitive transactions", "پیش از تراکنش‌های حساس به گواهی، تنظیمات تاریخ و زمان را بررسی کنید"),
                13, clockReady ? GOOD : WARN, true));
        clock.addView(tv(t("Clock posture is an audit signal and does not by itself indicate compromise.", "وضعیت ساعت یک سیگنال ممیزی است و به‌تنهایی نشانه نفوذ نیست."), 12, MUTED, false));
        content.addView(clock);

        Button recheck = secondary(t("Recheck compatibility", "بررسی مجدد سازگاری"));''',
    "compatibility clock card",
)

# Secure Browser: explicitly reject HTTP Basic/Digest auth challenges and client-certificate
# requests so protected sessions cannot expose credentials or device certificates through
# browser-level authentication prompts. This is fail-closed and auditable.
rep(
    '''            @Override public boolean onRenderProcessGone(WebView view, android.webkit.RenderProcessGoneDetail detail) {''',
    '''            @Override public void onReceivedHttpAuthRequest(WebView view, android.webkit.HttpAuthHandler handler, String host, String realm) {
                if (handler != null) handler.cancel();
                String safeHost = host == null ? "unknown" : host;
                recordActivity(t("Protected browser blocked a web authentication challenge for " + safeHost,
                        "مرورگر محافظت‌شده درخواست احراز هویت وب برای " + safeHost + " را مسدود کرد"));
                Toast.makeText(MainActivity.this, t("Web authentication challenge blocked", "درخواست احراز هویت وب مسدود شد"), Toast.LENGTH_LONG).show();
            }
            @Override public void onReceivedClientCertRequest(WebView view, android.webkit.ClientCertRequest request) {
                if (request != null) request.cancel();
                recordActivity(t("Protected browser blocked a client-certificate request",
                        "مرورگر محافظت‌شده درخواست گواهی کاربر را مسدود کرد"));
                Toast.makeText(MainActivity.this, t("Client certificate request blocked", "درخواست گواهی کاربر مسدود شد"), Toast.LENGTH_LONG).show();
            }
            @Override public boolean onRenderProcessGone(WebView view, android.webkit.RenderProcessGoneDetail detail) {''',
    "web authentication and client certificate fail-closed handling",
)

# Keep the protected-session disclosure aligned with the new authentication policy.
rep(
    '• TLS and renderer failures close the session safely", "• فقط پیمایش HTTPS\\n• خطای TLS باعث توقف اتصال می‌شود\\n• ترافیک بدون رمزنگاری غیرفعال است\\n• دسترسی فایل و محتوا بسته است\\n• محتوای ترکیبی مسدود است\\n• درخواست دوربین، میکروفن و موقعیت وب رد می‌شود\\n• تهدیدهای Safe Browsing به‌صورت مسدودشونده مدیریت می‌شوند\\n• دانلود در نشست‌های محافظت‌شده مسدود است\\n• خطای TLS یا فرآیند مرورگر نشست را به‌صورت امن می‌بندد")',
    '• TLS and renderer failures close the session safely\\n• Web-auth and client-certificate prompts are blocked", "• فقط پیمایش HTTPS\\n• خطای TLS باعث توقف اتصال می‌شود\\n• ترافیک بدون رمزنگاری غیرفعال است\\n• دسترسی فایل و محتوا بسته است\\n• محتوای ترکیبی مسدود است\\n• درخواست دوربین، میکروفن و موقعیت وب رد می‌شود\\n• تهدیدهای Safe Browsing به‌صورت مسدودشونده مدیریت می‌شوند\\n• دانلود در نشست‌های محافظت‌شده مسدود است\\n• خطای TLS یا فرآیند مرورگر نشست را به‌صورت امن می‌بندد\\n• درخواست‌های احراز هویت وب و گواهی کاربر مسدود می‌شوند")',
    "protected-session auth disclosure",
)

# Version metadata.
s = s.replace('0.6.1 ALPHA', '0.6.2 ALPHA')
s = s.replace('0.6.1 Alpha • versionCode 601', '0.6.2 Alpha • versionCode 602')
s = s.replace('0.6.1 Alpha', '0.6.2 Alpha')
s = s.replace('VARA 0.6.1 requires Android 8.0 / API 26 or newer.', 'VARA 0.6.2 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+601\b', 'versionCode 602', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.6\.1-alpha['\"]", "versionName '0.6.2-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'automaticTimeEnabled()',
    'automaticTimeZoneEnabled()',
    'Automatic date & time',
    'Clock integrity',
    'onReceivedHttpAuthRequest',
    'handler.cancel()',
    'onReceivedClientCertRequest',
    'request.cancel()',
    '0.6.2 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.6.2 clock-integrity audit and protected-auth hardening patch applied")
