from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_106.py <android-project-root>")

root = Path(sys.argv[1])
java = root / "app/src/main/java/com/varasecurity/alpha031/MainActivity.java"
gradle = root / "app/build.gradle"
s = java.read_text(encoding="utf-8")

required = [
    'currentSafePayPrerequisiteMask()',
    'last_prerequisite_mask',
    'safePayReadinessEnvironmentChanged()',
    'CHANGED • retest required',
    '0.10.5 ALPHA',
]
for marker in required:
    if marker not in s:
        raise SystemExit(f"missing validated 0.10.5 prerequisite: {marker}")

old_mask = r'''    private int currentSafePayPrerequisiteMask() {
        int mask = 0;
        if (!webViewRuntimeReady()) mask |= 1;
        if (!isDeviceLockSecure()) mask |= 2;
        if (adbEnabled()) mask |= 4;
        return mask;
    }

'''
if s.count(old_mask) != 1:
    raise SystemExit(f"patch failed [WebView identity helper anchor]: found {s.count(old_mask)}")

new_mask = r'''    private String currentWebViewIdentity() {
        try {
            android.content.pm.PackageInfo pi = android.webkit.WebView.getCurrentWebViewPackage();
            if (pi == null || pi.packageName == null) return "unavailable";
            String version = pi.versionName == null ? "unknown" : pi.versionName;
            return pi.packageName + "@" + version;
        } catch (Exception ignored) {
            return "unavailable";
        }
    }

    private int currentSafePayPrerequisiteMask() {
        int mask = 0;
        if (!webViewRuntimeReady()) mask |= 1;
        if (!isDeviceLockSecure()) mask |= 2;
        if (adbEnabled()) mask |= 4;
        return mask;
    }

'''
s = s.replace(old_mask, new_mask, 1)

old_persist = '''                .putInt("last_blockers", blockers)\n                .putInt("last_prerequisite_mask", currentSafePayPrerequisiteMask())\n                .apply();'''
if s.count(old_persist) != 1:
    raise SystemExit(f"patch failed [persist WebView identity]: found {s.count(old_persist)}")
new_persist = '''                .putInt("last_blockers", blockers)\n                .putInt("last_prerequisite_mask", currentSafePayPrerequisiteMask())\n                .putString("last_webview_identity", currentWebViewIdentity())\n                .apply();'''
s = s.replace(old_persist, new_persist, 1)

old_changed = r'''    private boolean safePayReadinessEnvironmentChanged() {
        android.content.SharedPreferences p = readinessPrefs();
        if (!p.contains("last_prerequisite_mask")) return true;
        return p.getInt("last_prerequisite_mask", -1) != currentSafePayPrerequisiteMask();
    }

'''
if s.count(old_changed) != 1:
    raise SystemExit(f"patch failed [environment changed helper]: found {s.count(old_changed)}")
new_changed = r'''    private boolean safePayReadinessWebViewChanged() {
        android.content.SharedPreferences p = readinessPrefs();
        if (!p.contains("last_webview_identity")) return true;
        String previous = p.getString("last_webview_identity", "");
        return !currentWebViewIdentity().equals(previous);
    }

    private boolean safePayReadinessEnvironmentChanged() {
        android.content.SharedPreferences p = readinessPrefs();
        if (!p.contains("last_prerequisite_mask")) return true;
        return p.getInt("last_prerequisite_mask", -1) != currentSafePayPrerequisiteMask()
                || safePayReadinessWebViewChanged();
    }

'''
s = s.replace(old_changed, new_changed, 1)

compat_anchor = '''        if (safePayReadinessEnvironmentChanged()) {\n            protectedReady.addView(tv(t("Device prerequisites changed since the last readiness test. Run the test again before relying on the displayed result.", "پیش‌نیازهای دستگاه از آخرین آزمون آمادگی تغییر کرده‌اند. پیش از اتکا به نتیجه نمایش‌داده‌شده، آزمون را دوباره اجرا کنید."), 12, WARN, true));\n        }'''
if s.count(compat_anchor) != 1:
    raise SystemExit(f"patch failed [WebView-change compatibility disclosure]: found {s.count(compat_anchor)}")
compat_new = compat_anchor + '''\n        if (safePayReadinessWebViewChanged()) {\n            protectedReady.addView(tv(t("The Android System WebView provider or version changed since the last readiness test. Retest before starting a protected session.", "ارائه‌دهنده یا نسخه Android System WebView از آخرین آزمون آمادگی تغییر کرده است. پیش از شروع نشست محافظت‌شده، آزمون را دوباره اجرا کنید."), 12, WARN, true));\n        }'''
s = s.replace(compat_anchor, compat_new, 1)

s = s.replace('0.10.5 ALPHA', '0.10.6 ALPHA')
s = s.replace('0.10.5 Alpha • versionCode 1005', '0.10.6 Alpha • versionCode 1006')
s = s.replace('0.10.5 Alpha', '0.10.6 Alpha')
s = s.replace('VARA 0.10.5 requires Android 8.0 / API 26 or newer.', 'VARA 0.10.6 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+1005\b', 'versionCode 1006', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.10\.5-alpha['\"]", "versionName '0.10.6-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'currentWebViewIdentity()',
    'WebView.getCurrentWebViewPackage()',
    'last_webview_identity',
    'safePayReadinessWebViewChanged()',
    'System WebView provider or version changed',
    '0.10.6 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.10.6 WebView identity-aware readiness patch applied")
