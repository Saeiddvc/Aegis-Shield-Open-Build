from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_107.py <android-project-root>")

root = Path(sys.argv[1])
java = root / "app/src/main/java/com/varasecurity/alpha031/MainActivity.java"
gradle = root / "app/build.gradle"
s = java.read_text(encoding="utf-8")

required = [
    'currentWebViewIdentity()',
    'last_webview_identity',
    'safePayReadinessWebViewChanged()',
    'safePayReadinessEnvironmentChanged()',
    '0.10.6 ALPHA',
]
for marker in required:
    if marker not in s:
        raise SystemExit(f"missing validated 0.10.6 prerequisite: {marker}")

old_identity = r'''    private String currentWebViewIdentity() {
        try {
            android.content.pm.PackageInfo pi = android.webkit.WebView.getCurrentWebViewPackage();
            if (pi == null || pi.packageName == null) return "unavailable";
            String version = pi.versionName == null ? "unknown" : pi.versionName;
            return pi.packageName + "@" + version;
        } catch (Exception ignored) {
            return "unavailable";
        }
    }

'''
if s.count(old_identity) != 1:
    raise SystemExit(f"patch failed [platform identity anchor]: found {s.count(old_identity)}")

new_identity = old_identity + r'''    private String currentPlatformIdentity() {
        String patch = android.os.Build.VERSION.SECURITY_PATCH == null ? "unknown" : android.os.Build.VERSION.SECURITY_PATCH;
        String fingerprint = android.os.Build.FINGERPRINT == null ? "unknown" : android.os.Build.FINGERPRINT;
        return android.os.Build.VERSION.SDK_INT + "|" + patch + "|" + fingerprint;
    }

'''
s = s.replace(old_identity, new_identity, 1)

old_persist = '''                .putInt("last_prerequisite_mask", currentSafePayPrerequisiteMask())\n                .putString("last_webview_identity", currentWebViewIdentity())\n                .apply();'''
if s.count(old_persist) != 1:
    raise SystemExit(f"patch failed [persist platform identity]: found {s.count(old_persist)}")
new_persist = '''                .putInt("last_prerequisite_mask", currentSafePayPrerequisiteMask())\n                .putString("last_webview_identity", currentWebViewIdentity())\n                .putString("last_platform_identity", currentPlatformIdentity())\n                .apply();'''
s = s.replace(old_persist, new_persist, 1)

old_changed = r'''    private boolean safePayReadinessWebViewChanged() {
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
if s.count(old_changed) != 1:
    raise SystemExit(f"patch failed [platform change helper]: found {s.count(old_changed)}")

new_changed = r'''    private boolean safePayReadinessWebViewChanged() {
        android.content.SharedPreferences p = readinessPrefs();
        if (!p.contains("last_webview_identity")) return true;
        String previous = p.getString("last_webview_identity", "");
        return !currentWebViewIdentity().equals(previous);
    }

    private boolean safePayReadinessPlatformChanged() {
        android.content.SharedPreferences p = readinessPrefs();
        if (!p.contains("last_platform_identity")) return true;
        String previous = p.getString("last_platform_identity", "");
        return !currentPlatformIdentity().equals(previous);
    }

    private boolean safePayReadinessEnvironmentChanged() {
        android.content.SharedPreferences p = readinessPrefs();
        if (!p.contains("last_prerequisite_mask")) return true;
        return p.getInt("last_prerequisite_mask", -1) != currentSafePayPrerequisiteMask()
                || safePayReadinessWebViewChanged()
                || safePayReadinessPlatformChanged();
    }

'''
s = s.replace(old_changed, new_changed, 1)

compat_anchor = '''        if (safePayReadinessWebViewChanged()) {\n            protectedReady.addView(tv(t("The Android System WebView provider or version changed since the last readiness test. Retest before starting a protected session.", "ارائه‌دهنده یا نسخه Android System WebView از آخرین آزمون آمادگی تغییر کرده است. پیش از شروع نشست محافظت‌شده، آزمون را دوباره اجرا کنید."), 12, WARN, true));\n        }'''
if s.count(compat_anchor) != 1:
    raise SystemExit(f"patch failed [platform compatibility disclosure]: found {s.count(compat_anchor)}")
compat_new = compat_anchor + '''\n        if (safePayReadinessPlatformChanged()) {\n            protectedReady.addView(tv(t("Android build or security-patch identity changed since the last readiness test. Retest SafePay readiness after system updates.", "شناسه نسخه Android یا وصله امنیتی از آخرین آزمون آمادگی تغییر کرده است. پس از به‌روزرسانی سیستم، آمادگی SafePay را دوباره بررسی کنید."), 12, WARN, true));\n        }'''
s = s.replace(compat_anchor, compat_new, 1)

s = s.replace('0.10.6 ALPHA', '0.10.7 ALPHA')
s = s.replace('0.10.6 Alpha • versionCode 1006', '0.10.7 Alpha • versionCode 1007')
s = s.replace('0.10.6 Alpha', '0.10.7 Alpha')
s = s.replace('VARA 0.10.6 requires Android 8.0 / API 26 or newer.', 'VARA 0.10.7 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+1006\b', 'versionCode 1007', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.10\.6-alpha['\"]", "versionName '0.10.7-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'currentPlatformIdentity()',
    'Build.VERSION.SECURITY_PATCH',
    'Build.FINGERPRINT',
    'last_platform_identity',
    'safePayReadinessPlatformChanged()',
    'Android build or security-patch identity changed',
    '0.10.7 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.10.7 platform-aware readiness patch applied")
