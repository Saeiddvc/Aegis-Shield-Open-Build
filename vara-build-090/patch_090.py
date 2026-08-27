from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_090.py <android-project-root>")

root = Path(sys.argv[1])
java = root / "app/src/main/java/com/varasecurity/alpha031/MainActivity.java"
gradle = root / "app/build.gradle"
s = java.read_text(encoding="utf-8")

required = [
    'renderScanResults(int apps, int deviceFindings, int appFindings, int postureScore)',
    'Scan and remediation are separate',
    'int priorityDeviceIssues = auditIssueCount();',
    'protectedSessionReadinessText()',
]
for marker in required:
    if marker not in s:
        raise SystemExit(f"missing validated 0.8.9 prerequisite: {marker}")

# 0.9.0: make scan freshness persistent and visible on the main command surfaces.
# This gives the user an explicit answer to "when was this posture last measured?"
# without conflating scan freshness with SafePay prerequisites.
helpers = r'''
    private long lastCompletedScanAt() {
        return getSharedPreferences("vara_security_state", MODE_PRIVATE).getLong("last_completed_scan_at", 0L);
    }

    private void markScanCompletedNow() {
        getSharedPreferences("vara_security_state", MODE_PRIVATE)
                .edit().putLong("last_completed_scan_at", System.currentTimeMillis()).apply();
    }

    private String scanFreshnessText() {
        long ts = lastCompletedScanAt();
        if (ts <= 0L) return t("Never scanned on this install", "در این نصب هنوز اسکن انجام نشده است");
        long ageMs = Math.max(0L, System.currentTimeMillis() - ts);
        long minutes = ageMs / 60000L;
        if (minutes < 1L) return t("Scanned just now", "همین حالا اسکن شد");
        if (minutes < 60L) return t("Last scan " + minutes + " min ago", "آخرین اسکن " + minutes + " دقیقه قبل");
        long hours = minutes / 60L;
        if (hours < 24L) return t("Last scan " + hours + " h ago", "آخرین اسکن " + hours + " ساعت قبل");
        long days = hours / 24L;
        return t("Last scan " + days + " day(s) ago", "آخرین اسکن " + days + " روز قبل");
    }

'''
anchor = '    private void renderScanResults(int apps, int deviceFindings, int appFindings, int postureScore) {'
if s.count(anchor) != 1:
    raise SystemExit(f"patch failed [scan freshness helper anchor]: found {s.count(anchor)}")
s = s.replace(anchor, helpers + anchor, 1)

# Home: add a compact branded scan-status card before the remediation recommendation.
home_anchor = '        int priorityDeviceIssues = auditIssueCount();'
if s.count(home_anchor) != 1:
    raise SystemExit(f"patch failed [home scan card anchor]: found {s.count(home_anchor)}")
home_card = r'''        LinearLayout scanStatus = card();
        scanStatus.setBackground(gradient(Color.rgb(239,248,249), Color.rgb(250,253,253), 22));
        scanStatus.addView(tv(t("Protection scan", "اسکن حفاظتی"), 13, MUTED, true));
        scanStatus.addView(tv(scanFreshnessText(), 17, NAVY, true));
        scanStatus.addView(tv(t("Scanning measures the current device and app posture. Findings remain review guidance and do not prevent future scans.",
                "اسکن، وضعیت فعلی دستگاه و برنامه‌ها را اندازه‌گیری می‌کند. یافته‌ها صرفاً راهنمای بررسی هستند و مانع اسکن‌های بعدی نمی‌شوند."), 12, MUTED, false));
        Button scanNow = secondary(lastCompletedScanAt() <= 0L ? t("Scan device", "اسکن دستگاه") : t("Scan again", "اسکن مجدد"));
        LinearLayout.LayoutParams snp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(46));
        snp.setMargins(0, dp(10), 0, 0);
        scanStatus.addView(scanNow, snp);
        scanNow.setOnClickListener(v -> runQuickScan());
        content.addView(scanStatus);

'''
s = s.replace(home_anchor, home_card + home_anchor, 1)

# Drawer header: carry the same scan freshness signal so Home and navigation agree.
drawer_anchor = '        head.addView(tv(t("SafePay: ", "SafePay: ") + protectedSessionReadinessText(), 11, Color.rgb(196,221,225), false));'
if s.count(drawer_anchor) != 1:
    raise SystemExit(f"patch failed [drawer scan freshness anchor]: found {s.count(drawer_anchor)}")
s = s.replace(drawer_anchor,
              drawer_anchor + '\n        head.addView(tv(scanFreshnessText(), 11, Color.rgb(196,221,225), false));', 1)

# Persist completion only after the scan analysis has completed successfully.
scan_record_anchor = '        recordActivity(event);\n        renderScanResults(risk.visible, issues, risk.flaggedAppCount(), score);'
if s.count(scan_record_anchor) != 1:
    raise SystemExit(f"patch failed [persist scan completion]: found {s.count(scan_record_anchor)}")
s = s.replace(scan_record_anchor,
              '        markScanCompletedNow();\n        recordActivity(event);\n        renderScanResults(risk.visible, issues, risk.flaggedAppCount(), score);', 1)

# Back from Scan Results returns Home explicitly as a first-level result screen.
nav_anchor = '        if ("actions".equals(currentPage) || "report".equals(currentPage) || "activity".equals(currentPage)) {'
if s.count(nav_anchor) == 1:
    s = s.replace(nav_anchor,
                  '        if ("scanresult".equals(currentPage)) {\n            renderHome();\n            return;\n        }\n' + nav_anchor, 1)

# Version metadata.
s = s.replace('0.8.9 ALPHA', '0.9.0 ALPHA')
s = s.replace('0.8.9 Alpha • versionCode 809', '0.9.0 Alpha • versionCode 900')
s = s.replace('0.8.9 Alpha', '0.9.0 Alpha')
s = s.replace('VARA 0.8.9 requires Android 8.0 / API 26 or newer.', 'VARA 0.9.0 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+809\b', 'versionCode 900', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.8\.9-alpha['\"]", "versionName '0.9.0-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'lastCompletedScanAt()',
    'markScanCompletedNow()',
    'scanFreshnessText()',
    'Protection scan',
    'Never scanned on this install',
    'markScanCompletedNow();',
    '0.9.0 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.9.0 persistent scan freshness and command-surface UX patch applied")
