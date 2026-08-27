from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_075.py <android-project-root>")

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

# Third-party enabled input methods can observe text entered through them. Report this as a
# review-only exposure signal, not as proof of malware and not as an automatic SafePay blocker.
rep(
    '''    private int enabledThirdPartyOverlayCount() {''',
    '''    private int enabledThirdPartyInputMethodCount() {
        try {
            android.view.inputmethod.InputMethodManager imm =
                    (android.view.inputmethod.InputMethodManager) getSystemService(INPUT_METHOD_SERVICE);
            if (imm == null) return 0;
            android.content.pm.PackageManager pm = getPackageManager();
            int count = 0;
            java.util.HashSet<String> seen = new java.util.HashSet<>();
            for (android.view.inputmethod.InputMethodInfo info : imm.getEnabledInputMethodList()) {
                if (info == null || info.getPackageName() == null) continue;
                String pkg = info.getPackageName();
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

    private int enabledThirdPartyOverlayCount() {''',
    "third-party input method helper",
)

rep(
    '''        if (enabledThirdPartyNotificationListenerCount() > 0) n++;
        if (enabledThirdPartyOverlayCount() > 0) n++;
        return n;''',
    '''        if (enabledThirdPartyNotificationListenerCount() > 0) n++;
        if (enabledThirdPartyOverlayCount() > 0) n++;
        if (enabledThirdPartyInputMethodCount() > 0) n++;
        return n;''',
    "input method exposure in device trust score",
)

rep(
    '''        int overlayCount = enabledThirdPartyOverlayCount();
        content.addView(auditRow(
                t("Display-over-other-apps exposure", "دسترسی نمایش روی سایر برنامه‌ها"),
                overlayCount == 0
                        ? t("No third-party app with granted overlay permission detected", "برنامه شخص ثالثی با مجوز فعال نمایش روی سایر برنامه‌ها شناسایی نشد")
                        : t(overlayCount + " third-party app(s) can draw over other apps — verify every app before sensitive use",
                                overlayCount + " برنامه شخص ثالث می‌تواند روی سایر برنامه‌ها نمایش داده شود — پیش از استفاده حساس، همه موارد را بررسی کنید"),
                overlayCount == 0,
                () -> openSettings(Settings.ACTION_MANAGE_OVERLAY_PERMISSION)));

        LinearLayout summary = card();''',
    '''        int overlayCount = enabledThirdPartyOverlayCount();
        content.addView(auditRow(
                t("Display-over-other-apps exposure", "دسترسی نمایش روی سایر برنامه‌ها"),
                overlayCount == 0
                        ? t("No third-party app with granted overlay permission detected", "برنامه شخص ثالثی با مجوز فعال نمایش روی سایر برنامه‌ها شناسایی نشد")
                        : t(overlayCount + " third-party app(s) can draw over other apps — verify every app before sensitive use",
                                overlayCount + " برنامه شخص ثالث می‌تواند روی سایر برنامه‌ها نمایش داده شود — پیش از استفاده حساس، همه موارد را بررسی کنید"),
                overlayCount == 0,
                () -> openSettings(Settings.ACTION_MANAGE_OVERLAY_PERMISSION)));

        int inputMethodCount = enabledThirdPartyInputMethodCount();
        content.addView(auditRow(
                t("Third-party keyboard exposure", "دسترسی صفحه‌کلید شخص ثالث"),
                inputMethodCount == 0
                        ? t("No enabled third-party input method detected", "روش ورودی شخص ثالث فعالی شناسایی نشد")
                        : t(inputMethodCount + " third-party input method app(s) are enabled — verify every keyboard before entering passwords, OTPs or payment data",
                                inputMethodCount + " برنامه روش ورودی شخص ثالث فعال است — پیش از ورود رمز، رمز یک‌بارمصرف یا اطلاعات پرداخت همه موارد را بررسی کنید"),
                inputMethodCount == 0,
                () -> openSettings(Settings.ACTION_INPUT_METHOD_SETTINGS)));

        LinearLayout summary = card();''',
    "actionable input method audit row",
)

rep(
    '''        content.addView(overlays);''',
    '''        content.addView(overlays);

        LinearLayout keyboards = card();
        int enabledKeyboards = enabledThirdPartyInputMethodCount();
        keyboards.addView(tv(t("Third-party keyboard exposure", "دسترسی صفحه‌کلید شخص ثالث"), 16, NAVY, true));
        keyboards.addView(tv(enabledKeyboards == 0
                ? t("No enabled third-party input method detected", "روش ورودی شخص ثالث فعالی شناسایی نشد")
                : t(enabledKeyboards + " third-party input method app(s) are enabled and should be reviewed before sensitive typing",
                        enabledKeyboards + " برنامه روش ورودی شخص ثالث فعال است و پیش از تایپ اطلاعات حساس باید بررسی شود"),
                13, enabledKeyboards == 0 ? GOOD : WARN, enabledKeyboards != 0));
        keyboards.addView(tv(t("Enabled keyboards can receive text typed through them. VARA reports this as a review signal and does not classify the keyboard as malicious.",
                "صفحه‌کلیدهای فعال می‌توانند متن تایپ‌شده از طریق خود را دریافت کنند. VARA این مورد را سیگنال بررسی می‌داند و صفحه‌کلید را بدافزار تلقی نمی‌کند."), 12, MUTED, false));
        content.addView(keyboards);''',
    "compatibility input method card",
)

# Version metadata.
s = s.replace('0.7.4 ALPHA', '0.7.5 ALPHA')
s = s.replace('0.7.4 Alpha • versionCode 704', '0.7.5 Alpha • versionCode 705')
s = s.replace('0.7.4 Alpha', '0.7.5 Alpha')
s = s.replace('VARA 0.7.4 requires Android 8.0 / API 26 or newer.', 'VARA 0.7.5 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+704\b', 'versionCode 705', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.7\.4-alpha['\"]", "versionName '0.7.5-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'enabledThirdPartyInputMethodCount()',
    'getEnabledInputMethodList()',
    'Third-party keyboard exposure',
    'Settings.ACTION_INPUT_METHOD_SETTINGS',
    'passwords, OTPs or payment data',
    '0.7.5 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.7.5 third-party input-method exposure audit patch applied")
