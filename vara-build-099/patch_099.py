from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_099.py <android-project-root>")

root = Path(sys.argv[1])
java = root / "app/src/main/java/com/varasecurity/alpha031/MainActivity.java"
gradle = root / "app/build.gradle"
s = java.read_text(encoding="utf-8")

required = [
    'protectedRequirementFixPending',
    'SafePay prerequisite fixed',
    'readiness is rechecked automatically',
    '0.9.8 ALPHA',
]
for marker in required:
    if marker not in s:
        raise SystemExit(f"missing validated 0.9.8 prerequisite: {marker}")

# 0.9.9: make SafePay remediation-return state resilient to Android process/activity recreation.
# The previous in-memory boolean could be lost while the user was in Android Settings.
old_field = '    private boolean protectedRequirementFixPending = false;\n'
if s.count(old_field) != 1:
    raise SystemExit(f"patch failed [pending state field]: found {s.count(old_field)}")
helpers = '''    private static final String RUNTIME_PREFS = "vara_runtime_state";\n    private static final String KEY_PROTECTED_FIX_PENDING = "protected_fix_pending";\n\n    private boolean protectedRequirementFixPending() {\n        return getSharedPreferences(RUNTIME_PREFS, MODE_PRIVATE).getBoolean(KEY_PROTECTED_FIX_PENDING, false);\n    }\n\n    private void setProtectedRequirementFixPending(boolean pending) {\n        getSharedPreferences(RUNTIME_PREFS, MODE_PRIVATE).edit().putBoolean(KEY_PROTECTED_FIX_PENDING, pending).apply();\n    }\n'''
s = s.replace(old_field, helpers, 1)

count = s.count('protectedRequirementFixPending = true;')
if count != 3:
    raise SystemExit(f"patch failed [persist remediation pending writes]: found {count}")
s = s.replace('protectedRequirementFixPending = true;', 'setProtectedRequirementFixPending(true);')

old_resume = '        if (protectedRequirementFixPending) {\n            protectedRequirementFixPending = false;'
if s.count(old_resume) != 1:
    raise SystemExit(f"patch failed [persist remediation pending read]: found {s.count(old_resume)}")
s = s.replace(old_resume,
              '        if (protectedRequirementFixPending()) {\n            setProtectedRequirementFixPending(false);', 1)

# Compatibility disclosure now explains that the pending recheck survives recreation.
old_text = 'Return to VARA after changing the setting; readiness is rechecked automatically.'
new_text = 'Return to VARA after changing the setting; readiness is rechecked automatically even if Android recreates the app while Settings is open.'
if s.count(old_text) != 1:
    raise SystemExit(f"patch failed [compatibility persistence disclosure]: found {s.count(old_text)}")
s = s.replace(old_text, new_text, 1)

s = s.replace('0.9.8 ALPHA', '0.9.9 ALPHA')
s = s.replace('0.9.8 Alpha • versionCode 908', '0.9.9 Alpha • versionCode 909')
s = s.replace('0.9.8 Alpha', '0.9.9 Alpha')
s = s.replace('VARA 0.9.8 requires Android 8.0 / API 26 or newer.', 'VARA 0.9.9 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+908\b', 'versionCode 909', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.9\.8-alpha['\"]", "versionName '0.9.9-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'RUNTIME_PREFS',
    'KEY_PROTECTED_FIX_PENDING',
    'protectedRequirementFixPending()',
    'setProtectedRequirementFixPending(true)',
    'setProtectedRequirementFixPending(false)',
    'even if Android recreates the app while Settings is open',
    '0.9.9 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.9.9 persistent SafePay remediation-state patch applied")
