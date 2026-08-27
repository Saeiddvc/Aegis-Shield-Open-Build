from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_098.py <android-project-root>")

root = Path(sys.argv[1])
java = root / "app/src/main/java/com/varasecurity/alpha031/MainActivity.java"
gradle = root / "app/build.gradle"
s = java.read_text(encoding="utf-8")

required = [
    'fixProtectedSessionRequirement()',
    'protectedSessionRequirementActionText()',
    'Device Scan still works independently',
    'protected void onResume()',
    '0.9.7 ALPHA',
]
for marker in required:
    if marker not in s:
        raise SystemExit(f"missing validated 0.9.7 prerequisite: {marker}")

# 0.9.8: close the remediation loop after Android Settings returns to VARA.
# The app remembers that a SafePay prerequisite fix was requested, re-evaluates
# readiness on resume, refreshes the relevant surface, and reports the result.
helper_anchor = '    private void fixProtectedSessionRequirement() {'
if s.count(helper_anchor) != 1:
    raise SystemExit(f"patch failed [pending remediation state anchor]: found {s.count(helper_anchor)}")
s = s.replace(helper_anchor,
              '    private boolean protectedRequirementFixPending = false;\n\n' + helper_anchor, 1)

# Mark only branches that actually leave VARA for Android settings.
replacements = [
    (
        '        if (!webViewRuntimeReady()) {\n            try { openSettings("android.settings.WEBVIEW_SETTINGS"); }',
        '        if (!webViewRuntimeReady()) {\n            protectedRequirementFixPending = true;\n            try { openSettings("android.settings.WEBVIEW_SETTINGS"); }',
        'webview remediation pending state',
    ),
    (
        '        if (!isDeviceLockSecure()) {\n            openSettings(Settings.ACTION_SECURITY_SETTINGS);',
        '        if (!isDeviceLockSecure()) {\n            protectedRequirementFixPending = true;\n            openSettings(Settings.ACTION_SECURITY_SETTINGS);',
        'screen lock remediation pending state',
    ),
    (
        '        if (adbEnabled()) {\n            try { openSettings(Settings.ACTION_APPLICATION_DEVELOPMENT_SETTINGS); }',
        '        if (adbEnabled()) {\n            protectedRequirementFixPending = true;\n            try { openSettings(Settings.ACTION_APPLICATION_DEVELOPMENT_SETTINGS); }',
        'adb remediation pending state',
    ),
]
for old, new, label in replacements:
    if s.count(old) != 1:
        raise SystemExit(f"patch failed [{label}]: found {s.count(old)}")
    s = s.replace(old, new, 1)

resume_anchor = '''        if (root == null || currentPage == null) return;
        if ("audit".equals(currentPage)) renderAudit();'''
if s.count(resume_anchor) != 1:
    raise SystemExit(f"patch failed [resume remediation loop]: found {s.count(resume_anchor)}")
resume_replacement = '''        if (root == null || currentPage == null) return;
        if (protectedRequirementFixPending) {
            protectedRequirementFixPending = false;
            boolean readyNow = protectedSessionPreflightReady();
            String event = readyNow
                    ? t("SafePay prerequisite fixed • protected session ready", "پیش‌نیاز SafePay رفع شد • نشست محافظت‌شده آماده است")
                    : t("SafePay prerequisite rechecked • another requirement still needs attention", "پیش‌نیاز SafePay دوباره بررسی شد • یک مورد دیگر هنوز نیاز به رسیدگی دارد");
            recordActivity(event);
            if ("compatibility".equals(currentPage)) renderCompatibility();
            else renderHome();
            Toast.makeText(this,
                    readyNow ? t("SafePay is ready", "SafePay آماده است")
                            : t("Another SafePay requirement still needs attention", "یک پیش‌نیاز دیگر SafePay هنوز نیاز به رسیدگی دارد"),
                    Toast.LENGTH_LONG).show();
            return;
        }
        if ("compatibility".equals(currentPage)) { renderCompatibility(); return; }
        if ("audit".equals(currentPage)) renderAudit();'''
s = s.replace(resume_anchor, resume_replacement, 1)

# Make the remediation loop explicit on Compatibility so the user knows returning
# from Android settings triggers an automatic re-check.
compat_anchor = '            fixRequirement.setOnClickListener(v -> fixProtectedSessionRequirement());\n        }'
if s.count(compat_anchor) != 1:
    raise SystemExit(f"patch failed [compatibility remediation disclosure]: found {s.count(compat_anchor)}")
s = s.replace(compat_anchor,
              '            fixRequirement.setOnClickListener(v -> fixProtectedSessionRequirement());\n'
              '            protectedReady.addView(tv(t("Return to VARA after changing the setting; readiness is rechecked automatically.", "پس از تغییر تنظیمات به VARA برگردید؛ آمادگی به‌صورت خودکار دوباره بررسی می‌شود."), 11, MUTED, false));\n'
              '        }', 1)

# Version metadata.
s = s.replace('0.9.7 ALPHA', '0.9.8 ALPHA')
s = s.replace('0.9.7 Alpha • versionCode 907', '0.9.8 Alpha • versionCode 908')
s = s.replace('0.9.7 Alpha', '0.9.8 Alpha')
s = s.replace('VARA 0.9.7 requires Android 8.0 / API 26 or newer.', 'VARA 0.9.8 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+907\b', 'versionCode 908', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.9\.7-alpha['\"]", "versionName '0.9.8-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'protectedRequirementFixPending',
    'SafePay prerequisite fixed',
    'SafePay is ready',
    'readiness is rechecked automatically',
    'if ("compatibility".equals(currentPage)) { renderCompatibility(); return; }',
    '0.9.8 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

if s.count('protected void onResume()') != 1:
    raise SystemExit(f"lifecycle validation failed: expected exactly one onResume override, found {s.count('protected void onResume()')}")

print("VARA Security 0.9.8 SafePay remediation return-loop patch applied")
