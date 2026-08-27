from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_091.py <android-project-root>")

root = Path(sys.argv[1])
java = root / "app/src/main/java/com/varasecurity/alpha031/MainActivity.java"
gradle = root / "app/build.gradle"
s = java.read_text(encoding="utf-8")

required = [
    'scanFreshnessText()',
    'renderScanResults(int apps, int deviceFindings, int appFindings, int postureScore)',
    'markScanCompletedNow();',
    'Protection scan',
]
for marker in required:
    if marker not in s:
        raise SystemExit(f"missing validated 0.9.0 prerequisite: {marker}")

# 0.9.1: persist a compact previous-scan snapshot and surface change over time.
# This turns repeated scans into a useful trend signal without claiming malware detection.
helpers = r'''
    private int lastScanPostureScore() {
        return getSharedPreferences("vara_security_state", MODE_PRIVATE).getInt("last_scan_posture_score", -1);
    }

    private int lastScanDeviceFindings() {
        return getSharedPreferences("vara_security_state", MODE_PRIVATE).getInt("last_scan_device_findings", -1);
    }

    private int lastScanAppFindings() {
        return getSharedPreferences("vara_security_state", MODE_PRIVATE).getInt("last_scan_app_findings", -1);
    }

    private void saveScanSnapshot(int postureScore, int deviceFindings, int appFindings) {
        getSharedPreferences("vara_security_state", MODE_PRIVATE).edit()
                .putInt("last_scan_posture_score", postureScore)
                .putInt("last_scan_device_findings", deviceFindings)
                .putInt("last_scan_app_findings", appFindings)
                .apply();
    }

    private String scanTrendText(int currentScore, int previousScore) {
        if (previousScore < 0) return t("Baseline created from this scan", "این اسکن به‌عنوان خط مبنا ثبت شد");
        int delta = currentScore - previousScore;
        if (delta > 0) return t("Posture improved by " + delta + " point(s) since the previous scan",
                "امتیاز وضعیت نسبت به اسکن قبلی " + delta + " امتیاز بهتر شده است");
        if (delta < 0) return t("Posture decreased by " + Math.abs(delta) + " point(s) since the previous scan",
                "امتیاز وضعیت نسبت به اسکن قبلی " + Math.abs(delta) + " امتیاز کاهش یافته است");
        return t("Posture score is unchanged since the previous scan", "امتیاز وضعیت نسبت به اسکن قبلی تغییری نکرده است");
    }

'''
anchor = '    private void renderScanResults(int apps, int deviceFindings, int appFindings, int postureScore) {'
if s.count(anchor) != 1:
    raise SystemExit(f"patch failed [scan trend helpers]: found {s.count(anchor)}")
s = s.replace(anchor, helpers + anchor, 1)

# Scan Results: add an explicit comparison card before remediation guidance.
results_anchor = '''        summary.addView(metrics);
        content.addView(summary);

        LinearLayout guidance = card();'''
if s.count(results_anchor) != 1:
    raise SystemExit(f"patch failed [scan trend result card]: found {s.count(results_anchor)}")
trend_card = r'''        summary.addView(metrics);
        content.addView(summary);

        int previousScore = lastScanPostureScore();
        int previousDevice = lastScanDeviceFindings();
        int previousApps = lastScanAppFindings();
        LinearLayout trend = card();
        trend.addView(tv(t("Change since previous scan", "تغییر نسبت به اسکن قبلی"), 16, NAVY, true));
        trend.addView(tv(scanTrendText(postureScore, previousScore), 14,
                previousScore >= 0 && postureScore < previousScore ? WARN : TEAL_DARK, true));
        if (previousScore >= 0) {
            trend.addView(tv(t("Previous: posture " + previousScore + "/100 • " + previousDevice + " device finding(s) • " + previousApps + " app signal(s)",
                    "قبلی: امتیاز " + previousScore + "/100 • " + previousDevice + " یافته دستگاه • " + previousApps + " سیگنال برنامه"), 12, MUTED, false));
        } else {
            trend.addView(tv(t("Future scans will be compared with this baseline so changes are easier to see.",
                    "اسکن‌های بعدی با این خط مبنا مقایسه می‌شوند تا تغییرات واضح‌تر دیده شوند."), 12, MUTED, false));
        }
        content.addView(trend);

        LinearLayout guidance = card();'''
s = s.replace(results_anchor, trend_card, 1)

# Home: include the most recent posture score beside scan freshness when available.
home_anchor = '        scanStatus.addView(tv(scanFreshnessText(), 17, NAVY, true));'
if s.count(home_anchor) != 1:
    raise SystemExit(f"patch failed [home previous score]: found {s.count(home_anchor)}")
s = s.replace(home_anchor,
              home_anchor + '\n        if (lastScanPostureScore() >= 0) scanStatus.addView(tv(t("Last posture " + lastScanPostureScore() + "/100", "آخرین امتیاز وضعیت " + lastScanPostureScore() + "/100"), 13, TEAL_DARK, true));', 1)

# Persist the snapshot only after the result screen has been constructed from the previous baseline.
scan_anchor = '        renderScanResults(risk.visible, issues, risk.flaggedAppCount(), score);'
if s.count(scan_anchor) != 1:
    raise SystemExit(f"patch failed [save scan snapshot]: found {s.count(scan_anchor)}")
s = s.replace(scan_anchor,
              scan_anchor + '\n        saveScanSnapshot(score, issues, risk.flaggedAppCount());', 1)

# Version metadata.
s = s.replace('0.9.0 ALPHA', '0.9.1 ALPHA')
s = s.replace('0.9.0 Alpha • versionCode 900', '0.9.1 Alpha • versionCode 901')
s = s.replace('0.9.0 Alpha', '0.9.1 Alpha')
s = s.replace('VARA 0.9.0 requires Android 8.0 / API 26 or newer.', 'VARA 0.9.1 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+900\b', 'versionCode 901', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.9\.0-alpha['\"]", "versionName '0.9.1-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'lastScanPostureScore()',
    'lastScanDeviceFindings()',
    'lastScanAppFindings()',
    'saveScanSnapshot(',
    'scanTrendText(',
    'Change since previous scan',
    'Last posture ',
    '0.9.1 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.9.1 scan trend and persistent baseline patch applied")
