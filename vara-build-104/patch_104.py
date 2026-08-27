from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_104.py <android-project-root>")

root = Path(sys.argv[1])
java = root / "app/src/main/java/com/varasecurity/alpha031/MainActivity.java"
gradle = root / "app/build.gradle"
s = java.read_text(encoding="utf-8")

required = [
    'safePayReadinessTestSummary()',
    'vara_safepay_readiness',
    'last_test_ms',
    '0.10.3 ALPHA',
]
for marker in required:
    if marker not in s:
        raise SystemExit(f"missing validated 0.10.3 prerequisite: {marker}")

old_method = r'''    private String safePayReadinessTestSummary() {
        android.content.SharedPreferences p = readinessPrefs();
        long when = p.getLong("last_test_ms", 0L);
        if (when <= 0L) {
            return t("Readiness has not been tested yet", "آمادگی SafePay هنوز آزمون نشده است");
        }
        boolean ready = p.getBoolean("last_ready", false);
        int blockers = p.getInt("last_blockers", 0);
        String stamp = android.text.format.DateFormat.format("yyyy-MM-dd HH:mm", when).toString();
        if (ready) {
            return t("Last test " + stamp + " • READY", "آخرین آزمون " + stamp + " • آماده");
        }
        return t("Last test " + stamp + " • BLOCKED • " + blockers + " prerequisite(s)",
                "آخرین آزمون " + stamp + " • مسدود • " + blockers + " پیش‌نیاز");
    }

'''
if s.count(old_method) != 1:
    raise SystemExit(f"patch failed [readiness summary]: found {s.count(old_method)}")

new_method = r'''    private static final long SAFEPAY_READINESS_FRESH_MS = 15L * 60L * 1000L;

    private boolean safePayReadinessTestFresh() {
        long when = readinessPrefs().getLong("last_test_ms", 0L);
        return when > 0L && System.currentTimeMillis() - when <= SAFEPAY_READINESS_FRESH_MS;
    }

    private String safePayReadinessTestSummary() {
        android.content.SharedPreferences p = readinessPrefs();
        long when = p.getLong("last_test_ms", 0L);
        if (when <= 0L) {
            return t("Readiness has not been tested yet", "آمادگی SafePay هنوز آزمون نشده است");
        }
        boolean ready = p.getBoolean("last_ready", false);
        int blockers = p.getInt("last_blockers", 0);
        boolean fresh = safePayReadinessTestFresh();
        String stamp = android.text.format.DateFormat.format("yyyy-MM-dd HH:mm", when).toString();
        String freshness = fresh ? t("CURRENT", "معتبر") : t("STALE • retest recommended", "قدیمی • آزمون مجدد پیشنهاد می‌شود");
        if (ready) {
            return t("Last test " + stamp + " • READY • " + freshness,
                    "آخرین آزمون " + stamp + " • آماده • " + freshness);
        }
        return t("Last test " + stamp + " • BLOCKED • " + blockers + " prerequisite(s) • " + freshness,
                "آخرین آزمون " + stamp + " • مسدود • " + blockers + " پیش‌نیاز • " + freshness);
    }

'''
s = s.replace(old_method, new_method, 1)

# Persisted readiness is informational only. Add an explicit disclosure where the
# result is shown so stale state can never be mistaken for a launch authorization.
anchor = '        TextView lastSafePayTest = tv(safePayReadinessTestSummary(), 12, MUTED, false);'
if s.count(anchor) != 1:
    raise SystemExit(f"patch failed [home readiness disclosure anchor]: found {s.count(anchor)}")
s = s.replace(anchor,
    '        TextView lastSafePayTest = tv(safePayReadinessTestSummary(), 12, safePayReadinessTestFresh() ? MUTED : WARN, false);', 1)

anchor2 = '        TextView readinessTestHistory = tv(safePayReadinessTestSummary(), 12, MUTED, false);'
if s.count(anchor2) != 1:
    raise SystemExit(f"patch failed [compat readiness disclosure anchor]: found {s.count(anchor2)}")
s = s.replace(anchor2,
    '        TextView readinessTestHistory = tv(safePayReadinessTestSummary(), 12, safePayReadinessTestFresh() ? MUTED : WARN, false);', 1)

# Version metadata.
s = s.replace('0.10.3 ALPHA', '0.10.4 ALPHA')
s = s.replace('0.10.3 Alpha • versionCode 1003', '0.10.4 Alpha • versionCode 1004')
s = s.replace('0.10.3 Alpha', '0.10.4 Alpha')
s = s.replace('VARA 0.10.3 requires Android 8.0 / API 26 or newer.', 'VARA 0.10.4 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+1003\b', 'versionCode 1004', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.10\.3-alpha['\"]", "versionName '0.10.4-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'SAFEPAY_READINESS_FRESH_MS',
    'safePayReadinessTestFresh()',
    'STALE • retest recommended',
    'CURRENT',
    'safePayReadinessTestFresh() ? MUTED : WARN',
    '0.10.4 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.10.4 SafePay readiness freshness patch applied")
