from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_102.py <android-project-root>")

root = Path(sys.argv[1])
java = root / "app/src/main/java/com/varasecurity/alpha031/MainActivity.java"
gradle = root / "app/build.gradle"
s = java.read_text(encoding="utf-8")

required = [
    'protectedSessionPrerequisiteChecklist()',
    'protectedSessionBlockingCount()',
    'fixProtectedSessionRequirement()',
    'SafePay prerequisites are separate from Device Scan findings.',
    '0.10.1 ALPHA',
]
for marker in required:
    if marker not in s:
        raise SystemExit(f"missing validated 0.10.1 prerequisite: {marker}")

# 0.10.2: add an explicit preflight test that does not launch WebView or start a
# Protected Session. This gives the user a deterministic way to verify readiness
# after changing Android settings, while Device Scan remains fully independent.
helper_anchor = '    private String protectedSessionReadinessText() {'
if s.count(helper_anchor) != 1:
    raise SystemExit(f"patch failed [SafePay readiness test helper anchor]: found {s.count(helper_anchor)}")

helper = r'''    private void testProtectedSessionReadiness() {
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
s = s.replace(helper_anchor, helper + helper_anchor, 1)

# Home: add a non-launching readiness test immediately after the branded SafePay card.
home_anchor = '        content.addView(readyCard);'
if s.count(home_anchor) != 1:
    raise SystemExit(f"patch failed [home readiness test button]: found {s.count(home_anchor)}")
home_new = '''        content.addView(readyCard);

        Button testSafePayReadiness = secondary(t("Test SafePay readiness", "آزمون آمادگی SafePay"));
        LinearLayout.LayoutParams testReadyParams = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(46));
        testReadyParams.setMargins(0, dp(8), 0, 0);
        content.addView(testSafePayReadiness, testReadyParams);
        testSafePayReadiness.setOnClickListener(v -> testProtectedSessionReadiness());'''
s = s.replace(home_anchor, home_new, 1)

# Compatibility: add the same deterministic preflight test below the prerequisite
# checklist/direct remediation controls and before the next compatibility section.
compat_anchor = '        content.addView(protectedReady);'
if s.count(compat_anchor) != 1:
    raise SystemExit(f"patch failed [compatibility readiness test button]: found {s.count(compat_anchor)}")
compat_new = '''        content.addView(protectedReady);

        Button testProtectedReadiness = secondary(t("Test SafePay readiness", "آزمون آمادگی SafePay"));
        LinearLayout.LayoutParams testProtectedParams = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(46));
        testProtectedParams.setMargins(0, dp(8), 0, 0);
        content.addView(testProtectedReadiness, testProtectedParams);
        testProtectedReadiness.setOnClickListener(v -> testProtectedSessionReadiness());'''
s = s.replace(compat_anchor, compat_new, 1)

# Version metadata.
s = s.replace('0.10.1 ALPHA', '0.10.2 ALPHA')
s = s.replace('0.10.1 Alpha • versionCode 1001', '0.10.2 Alpha • versionCode 1002')
s = s.replace('0.10.1 Alpha', '0.10.2 Alpha')
s = s.replace('VARA 0.10.1 requires Android 8.0 / API 26 or newer.', 'VARA 0.10.2 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+1001\b', 'versionCode 1002', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.10\.1-alpha['\"]", "versionName '0.10.2-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'testProtectedSessionReadiness()',
    'SafePay readiness test passed',
    'No protected session was started.',
    'Test SafePay readiness',
    'testSafePayReadiness.setOnClickListener',
    'testProtectedReadiness.setOnClickListener',
    '0.10.2 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.10.2 explicit SafePay readiness test patch applied")
