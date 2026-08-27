from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_103.py <android-project-root>")

root = Path(sys.argv[1])
java = root / "app/src/main/java/com/varasecurity/alpha031/MainActivity.java"
gradle = root / "app/build.gradle"
s = java.read_text(encoding="utf-8")

required = [
    'testProtectedSessionReadiness()',
    'SafePay readiness test passed',
    'Test SafePay readiness',
    '0.10.2 ALPHA',
]
for marker in required:
    if marker not in s:
        raise SystemExit(f"missing validated 0.10.2 prerequisite: {marker}")

old_method = r'''    private void testProtectedSessionReadiness() {
        int blockers = protectedSessionBlockingCount();
        boolean ready = blockers == 0;
        String event = ready
                ? t("SafePay readiness test passed", "آزمون آمادگی SafePay موفق بود")
                : t("SafePay readiness test: " + blockers + " prerequisite(s) need action",
                    "آزمون آمادگی SafePay: " + blockers + " پیش‌نیاز نیازمند اقدام است");
        recordActivity(event);
        Toast.makeText(this,
                ready
                        ? t("SafePay is ready. No protected session was started.",
                            "SafePay آماده است. هیچ نشست محافظت‌شده‌ای شروع نشد.")
                        : t("SafePay is not ready yet. Review the prerequisite checklist.",
                            "SafePay هنوز آماده نیست. فهرست پیش‌نیازها را بررسی کنید."),
                Toast.LENGTH_LONG).show();
        if ("compatibility".equals(currentPage)) renderCompatibility();
        else renderHome();
    }

'''
if s.count(old_method) != 1:
    raise SystemExit(f"patch failed [readiness method]: found {s.count(old_method)}")

new_method = r'''    private android.content.SharedPreferences readinessPrefs() {
        return getSharedPreferences("vara_safepay_readiness", MODE_PRIVATE);
    }

    private void persistSafePayReadinessTest(boolean ready, int blockers) {
        readinessPrefs().edit()
                .putLong("last_test_ms", System.currentTimeMillis())
                .putBoolean("last_ready", ready)
                .putInt("last_blockers", blockers)
                .apply();
    }

    private String safePayReadinessTestSummary() {
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

    private void testProtectedSessionReadiness() {
        int blockers = protectedSessionBlockingCount();
        boolean ready = blockers == 0;
        persistSafePayReadinessTest(ready, blockers);
        String event = ready
                ? t("SafePay readiness test passed", "آزمون آمادگی SafePay موفق بود")
                : t("SafePay readiness test: " + blockers + " prerequisite(s) need action",
                    "آزمون آمادگی SafePay: " + blockers + " پیش‌نیاز نیازمند اقدام است");
        recordActivity(event);
        Toast.makeText(this,
                ready
                        ? t("SafePay is ready. No protected session was started.",
                            "SafePay آماده است. هیچ نشست محافظت‌شده‌ای شروع نشد.")
                        : t("SafePay is not ready yet. Review the prerequisite checklist.",
                            "SafePay هنوز آماده نیست. فهرست پیش‌نیازها را بررسی کنید."),
                Toast.LENGTH_LONG).show();
        if ("compatibility".equals(currentPage)) renderCompatibility();
        else renderHome();
    }

'''
s = s.replace(old_method, new_method, 1)

home_anchor = '''        content.addView(testSafePayReadiness, testReadyParams);
        testSafePayReadiness.setOnClickListener(v -> testProtectedSessionReadiness());'''
if s.count(home_anchor) != 1:
    raise SystemExit(f"patch failed [home test summary]: found {s.count(home_anchor)}")
home_new = '''        content.addView(testSafePayReadiness, testReadyParams);
        testSafePayReadiness.setOnClickListener(v -> testProtectedSessionReadiness());
        TextView lastSafePayTest = tv(safePayReadinessTestSummary(), 12, MUTED, false);
        LinearLayout.LayoutParams lastSafePayTestParams = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        lastSafePayTestParams.setMargins(0, dp(6), 0, 0);
        content.addView(lastSafePayTest, lastSafePayTestParams);'''
s = s.replace(home_anchor, home_new, 1)

compat_anchor = '''        content.addView(testProtectedReadiness, testProtectedParams);
        testProtectedReadiness.setOnClickListener(v -> testProtectedSessionReadiness());'''
if s.count(compat_anchor) != 1:
    raise SystemExit(f"patch failed [compatibility test summary]: found {s.count(compat_anchor)}")
compat_new = '''        content.addView(testProtectedReadiness, testProtectedParams);
        testProtectedReadiness.setOnClickListener(v -> testProtectedSessionReadiness());
        TextView readinessTestHistory = tv(safePayReadinessTestSummary(), 12, MUTED, false);
        LinearLayout.LayoutParams readinessTestHistoryParams = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        readinessTestHistoryParams.setMargins(0, dp(6), 0, 0);
        content.addView(readinessTestHistory, readinessTestHistoryParams);'''
s = s.replace(compat_anchor, compat_new, 1)

s = s.replace('0.10.2 ALPHA', '0.10.3 ALPHA')
s = s.replace('0.10.2 Alpha • versionCode 1002', '0.10.3 Alpha • versionCode 1003')
s = s.replace('0.10.2 Alpha', '0.10.3 Alpha')
s = s.replace('VARA 0.10.2 requires Android 8.0 / API 26 or newer.', 'VARA 0.10.3 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+1002\b', 'versionCode 1003', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.10\.2-alpha['\"]", "versionName '0.10.3-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'readinessPrefs()',
    'persistSafePayReadinessTest(',
    'safePayReadinessTestSummary()',
    'vara_safepay_readiness',
    'last_test_ms',
    'Last test ',
    'Readiness has not been tested yet',
    '0.10.3 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.10.3 persisted SafePay readiness result patch applied")
