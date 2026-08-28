from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_105.py <android-project-root>")

root = Path(sys.argv[1])
java = root / "app/src/main/java/com/varasecurity/alpha031/MainActivity.java"
gradle = root / "app/build.gradle"
s = java.read_text(encoding="utf-8")

required = [
    'SAFEPAY_READINESS_FRESH_MS',
    'safePayReadinessTestFresh()',
    'persistSafePayReadinessTest(',
    'protectedSessionBlockingCount()',
    'webViewRuntimeReady()',
    'isDeviceLockSecure()',
    'adbEnabled()',
    '0.10.4 ALPHA',
]
for marker in required:
    if marker not in s:
        raise SystemExit(f"missing validated 0.10.4 prerequisite: {marker}")

old_persist = r'''    private void persistSafePayReadinessTest(boolean ready, int blockers) {
        readinessPrefs().edit()
                .putLong("last_test_ms", System.currentTimeMillis())
                .putBoolean("last_ready", ready)
                .putInt("last_blockers", blockers)
                .apply();
    }

'''
if s.count(old_persist) != 1:
    raise SystemExit(f"patch failed [persist readiness snapshot]: found {s.count(old_persist)}")

new_persist = r'''    private int currentSafePayPrerequisiteMask() {
        int mask = 0;
        if (!webViewRuntimeReady()) mask |= 1;
        if (!isDeviceLockSecure()) mask |= 2;
        if (adbEnabled()) mask |= 4;
        return mask;
    }

    private void persistSafePayReadinessTest(boolean ready, int blockers) {
        readinessPrefs().edit()
                .putLong("last_test_ms", System.currentTimeMillis())
                .putBoolean("last_ready", ready)
                .putInt("last_blockers", blockers)
                .putInt("last_prerequisite_mask", currentSafePayPrerequisiteMask())
                .apply();
    }

    private boolean safePayReadinessEnvironmentChanged() {
        android.content.SharedPreferences p = readinessPrefs();
        if (!p.contains("last_prerequisite_mask")) return true;
        return p.getInt("last_prerequisite_mask", -1) != currentSafePayPrerequisiteMask();
    }

'''
s = s.replace(old_persist, new_persist, 1)

old_fresh = r'''    private boolean safePayReadinessTestFresh() {
        long when = readinessPrefs().getLong("last_test_ms", 0L);
        return when > 0L && System.currentTimeMillis() - when <= SAFEPAY_READINESS_FRESH_MS;
    }

'''
if s.count(old_fresh) != 1:
    raise SystemExit(f"patch failed [freshness helper]: found {s.count(old_fresh)}")
new_fresh = r'''    private boolean safePayReadinessTestFresh() {
        long when = readinessPrefs().getLong("last_test_ms", 0L);
        return when > 0L
                && System.currentTimeMillis() - when <= SAFEPAY_READINESS_FRESH_MS
                && !safePayReadinessEnvironmentChanged();
    }

'''
s = s.replace(old_fresh, new_fresh, 1)

old_summary_fragment = '        String freshness = fresh ? t("CURRENT", "معتبر") : t("STALE • retest recommended", "قدیمی • آزمون مجدد پیشنهاد می‌شود");'
if s.count(old_summary_fragment) != 1:
    raise SystemExit(f"patch failed [summary freshness]: found {s.count(old_summary_fragment)}")
new_summary_fragment = '''        boolean changed = safePayReadinessEnvironmentChanged();
        String freshness = changed
                ? t("CHANGED • retest required", "تغییر کرده • آزمون مجدد لازم است")
                : (fresh ? t("CURRENT", "معتبر") : t("STALE • retest recommended", "قدیمی • آزمون مجدد پیشنهاد می‌شود"));'''
s = s.replace(old_summary_fragment, new_summary_fragment, 1)

compat_anchor = '        TextView readinessTestHistory = tv(safePayReadinessTestSummary(), 12, safePayReadinessTestFresh() ? MUTED : WARN, false);'
if s.count(compat_anchor) != 1:
    raise SystemExit(f"patch failed [compat changed-state disclosure]: found {s.count(compat_anchor)}")

s = s.replace(
    compat_anchor,
    compat_anchor + '\n        if (safePayReadinessEnvironmentChanged()) {\n            protectedReady.addView(tv(t("Device prerequisites changed since the last readiness test. Run the test again before relying on the displayed result.", "پیش‌نیازهای دستگاه از آخرین آزمون آمادگی تغییر کرده‌اند. پیش از اتکا به نتیجه نمایش‌داده‌شده، آزمون را دوباره اجرا کنید."), 12, WARN, true));\n        }',
    1,
)

s = s.replace('0.10.4 ALPHA', '0.10.5 ALPHA')
s = s.replace('0.10.4 Alpha • versionCode 1004', '0.10.5 Alpha • versionCode 1005')
s = s.replace('0.10.4 Alpha', '0.10.5 Alpha')
s = s.replace('VARA 0.10.4 requires Android 8.0 / API 26 or newer.', 'VARA 0.10.5 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+1004\b', 'versionCode 1005', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.10\.4-alpha['\"]", "versionName '0.10.5-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'currentSafePayPrerequisiteMask()',
    'last_prerequisite_mask',
    'safePayReadinessEnvironmentChanged()',
    'CHANGED • retest required',
    'Device prerequisites changed since the last readiness test',
    '0.10.5 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.10.5 readiness environment-change patch applied")
