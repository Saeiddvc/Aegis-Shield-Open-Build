from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_097.py <android-project-root>")

root = Path(sys.argv[1])
java = root / "app/src/main/java/com/varasecurity/alpha031/MainActivity.java"
gradle = root / "app/build.gradle"
s = java.read_text(encoding="utf-8")

required = [
    'protectedSessionPreflightReady()',
    'protectedSessionReadinessText()',
    'Protected session readiness',
    '0.9.6 ALPHA',
]
for marker in required:
    if marker not in s:
        raise SystemExit(f"missing validated 0.9.6 prerequisite: {marker}")

# 0.9.7: make SafePay readiness remediation direct and explicit.
# Scan remains independent: these prerequisites gate only Protected Session launch.
helper_anchor = '    private String protectedSessionReadinessText() {'
if s.count(helper_anchor) != 1:
    raise SystemExit(f"patch failed [readiness remediation helper anchor]: found {s.count(helper_anchor)}")
helper = r'''    private void fixProtectedSessionRequirement() {
        if (!webViewRuntimeReady()) {
            try { openSettings("android.settings.WEBVIEW_SETTINGS"); }
            catch (Exception ignored) { openSettings(Settings.ACTION_APPLICATION_SETTINGS); }
            return;
        }
        if (!isDeviceLockSecure()) {
            openSettings(Settings.ACTION_SECURITY_SETTINGS);
            return;
        }
        if (adbEnabled()) {
            try { openSettings(Settings.ACTION_APPLICATION_DEVELOPMENT_SETTINGS); }
            catch (Exception ignored) { openSettings(Settings.ACTION_SETTINGS); }
            return;
        }
        renderBrowserStart();
    }

    private String protectedSessionRequirementActionText() {
        if (!webViewRuntimeReady()) return t("Open WebView settings", "باز کردن تنظیمات WebView");
        if (!isDeviceLockSecure()) return t("Set secure screen lock", "تنظیم قفل امن صفحه");
        if (adbEnabled()) return t("Turn off USB debugging", "خاموش کردن اشکال‌زدایی USB");
        return t("Open SafePay", "باز کردن SafePay");
    }

'''
s = s.replace(helper_anchor, helper + helper_anchor, 1)

old_action = 'Button readinessAction = secondary(protectedReady ? t("Open SafePay", "باز کردن SafePay") : t("Review requirements", "بررسی پیش‌نیازها"));'
if s.count(old_action) != 1:
    raise SystemExit(f"patch failed [home readiness CTA]: found {s.count(old_action)}")
s = s.replace(old_action,
              'Button readinessAction = secondary(protectedReady ? t("Open SafePay", "باز کردن SafePay") : protectedSessionRequirementActionText());', 1)

old_listener = 'readinessAction.setOnClickListener(v -> { if (protectedSessionPreflightReady()) renderBrowserStart(); else renderCompatibility(); });'
if s.count(old_listener) != 1:
    raise SystemExit(f"patch failed [home readiness direct remediation]: found {s.count(old_listener)}")
s = s.replace(old_listener,
              'readinessAction.setOnClickListener(v -> { if (protectedSessionPreflightReady()) renderBrowserStart(); else fixProtectedSessionRequirement(); });', 1)

old_detail = 'Review the blocking prerequisite before starting a sensitive payment or browser session.'
if s.count(old_detail) != 1:
    raise SystemExit(f"patch failed [home scan independence disclosure]: found {s.count(old_detail)}")
s = s.replace(old_detail,
              'Fix the blocking prerequisite before SafePay. Device Scan still works independently and is never blocked by these SafePay requirements.', 1)

# Add a direct remediation button to Compatibility immediately after the prerequisite breakdown.
compat_anchor = '''        protectedReady.addView(tv((!adbEnabled() ? "✓ " : "• ") + t("USB debugging disabled", "اشکال‌زدایی USB غیرفعال"), 12, !adbEnabled() ? GOOD : WARN, true));
        content.addView(protectedReady);'''
if s.count(compat_anchor) != 1:
    raise SystemExit(f"patch failed [compatibility direct remediation]: found {s.count(compat_anchor)}")
compat_new = '''        protectedReady.addView(tv((!adbEnabled() ? "✓ " : "• ") + t("USB debugging disabled", "اشکال‌زدایی USB غیرفعال"), 12, !adbEnabled() ? GOOD : WARN, true));
        if (!protectedSessionReady) {
            Button fixRequirement = secondary(protectedSessionRequirementActionText());
            LinearLayout.LayoutParams fixParams = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(46));
            fixParams.setMargins(0, dp(10), 0, 0);
            protectedReady.addView(fixRequirement, fixParams);
            fixRequirement.setOnClickListener(v -> fixProtectedSessionRequirement());
        }
        content.addView(protectedReady);'''
s = s.replace(compat_anchor, compat_new, 1)

# Version metadata.
s = s.replace('0.9.6 ALPHA', '0.9.7 ALPHA')
s = s.replace('0.9.6 Alpha • versionCode 906', '0.9.7 Alpha • versionCode 907')
s = s.replace('0.9.6 Alpha', '0.9.7 Alpha')
s = s.replace('VARA 0.9.6 requires Android 8.0 / API 26 or newer.', 'VARA 0.9.7 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+906\b', 'versionCode 907', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.9\.6-alpha['\"]", "versionName '0.9.7-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'fixProtectedSessionRequirement()',
    'protectedSessionRequirementActionText()',
    'android.settings.WEBVIEW_SETTINGS',
    'Set secure screen lock',
    'Turn off USB debugging',
    'Device Scan still works independently',
    'Button fixRequirement',
    '0.9.7 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.9.7 direct SafePay readiness remediation patch applied")
