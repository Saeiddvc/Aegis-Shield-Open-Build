from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_101.py <android-project-root>")

root = Path(sys.argv[1])
java = root / "app/src/main/java/com/varasecurity/alpha031/MainActivity.java"
gradle = root / "app/build.gradle"
s = java.read_text(encoding="utf-8")

required = [
    'protectedSessionBlockingCount()',
    'protectedSessionCompactStatus()',
    'SafePay readiness',
    'Device Scan still works independently',
    '0.10.0 ALPHA',
]
for marker in required:
    if marker not in s:
        raise SystemExit(f"missing validated 0.10.0 prerequisite: {marker}")

# 0.10.1: make SafePay prerequisites explicit instead of presenting one opaque
# readiness state. This is presentation/remediation UX only; the fail-closed
# launch contract remains unchanged and Device Scan stays independent.
anchor = '    private String protectedSessionReadinessText() {'
if s.count(anchor) != 1:
    raise SystemExit(f"patch failed [prerequisite checklist helper anchor]: found {s.count(anchor)}")

helpers = r'''    private String protectedSessionPrerequisiteChecklist() {
        String webViewState = webViewRuntimeReady() ? t("OK", "تأیید") : t("ACTION", "اقدام");
        String lockState = isDeviceLockSecure() ? t("OK", "تأیید") : t("ACTION", "اقدام");
        String adbState = !adbEnabled() ? t("OK", "تأیید") : t("ACTION", "اقدام");
        return webViewState + " • " + t("System WebView", "WebView سیستم") + "\n"
                + lockState + " • " + t("Secure screen lock", "قفل امن صفحه") + "\n"
                + adbState + " • " + t("USB debugging off", "USB debugging خاموش");
    }

'''
s = s.replace(anchor, helpers + anchor, 1)

home_anchor = '        readyCard.addView(tv(protectedSessionReadinessText(), 12, MUTED, false));'
if s.count(home_anchor) != 1:
    raise SystemExit(f"patch failed [home SafePay separation note]: found {s.count(home_anchor)}")
home_new = '''        readyCard.addView(tv(protectedSessionReadinessText(), 12, MUTED, false));
        readyCard.addView(tv(t("SafePay prerequisites are separate from Device Scan findings.",
                "پیش‌نیازهای SafePay از یافته‌های اسکن دستگاه مستقل هستند."), 11, MUTED, false));'''
s = s.replace(home_anchor, home_new, 1)

compat_anchor = '        protectedReady.addView(tv(t("Safe Browsing initialization is also verified at session start and fails closed if unavailable.", "راه‌اندازی Safe Browsing نیز هنگام شروع نشست بررسی می‌شود و در صورت عدم دسترسی، نشست به‌صورت امن متوقف می‌شود."), 12, MUTED, false));'
if s.count(compat_anchor) != 1:
    raise SystemExit(f"patch failed [compatibility prerequisite checklist]: found {s.count(compat_anchor)}")
compat_new = '''        protectedReady.addView(tv(t("SafePay prerequisites", "پیش‌نیازهای SafePay"), 13, NAVY, true));
        protectedReady.addView(tv(protectedSessionPrerequisiteChecklist(), 12,
                protectedSessionBlockingCount() == 0 ? GOOD : WARN, false));
        protectedReady.addView(tv(t("Device Scan still works independently of these SafePay launch requirements.",
                "اسکن دستگاه مستقل از این پیش‌نیازهای اجرای SafePay کار می‌کند."), 11, MUTED, false));
''' + compat_anchor
s = s.replace(compat_anchor, compat_new, 1)

# Version metadata.
s = s.replace('0.10.0 ALPHA', '0.10.1 ALPHA')
s = s.replace('0.10.0 Alpha • versionCode 1000', '0.10.1 Alpha • versionCode 1001')
s = s.replace('0.10.0 Alpha', '0.10.1 Alpha')
s = s.replace('VARA 0.10.0 requires Android 8.0 / API 26 or newer.', 'VARA 0.10.1 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+1000\b', 'versionCode 1001', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.10\.0-alpha['\"]", "versionName '0.10.1-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'protectedSessionPrerequisiteChecklist()',
    'System WebView',
    'Secure screen lock',
    'USB debugging off',
    'SafePay prerequisites',
    'SafePay prerequisites are separate from Device Scan findings.',
    'Device Scan still works independently of these SafePay launch requirements.',
    '0.10.1 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.10.1 SafePay prerequisite checklist patch applied")
