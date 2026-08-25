from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_088.py <android-project-root>")

root = Path(sys.argv[1])
java = root / "app/src/main/java/com/varasecurity/alpha031/MainActivity.java"
gradle = root / "app/build.gradle"
manifest = root / "app/src/main/AndroidManifest.xml"
s = java.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str):
    global s
    count = s.count(old)
    if count != 1:
        raise SystemExit(f"patch failed [{label}]: expected 1 match, found {count}")
    s = s.replace(old, new, 1)

# 0.8.8 fixes the misleading scan/posture UX observed on a real Samsung device.
# Low-confidence app review findings must not drive the global score to zero, and
# a scan must always complete independently of remediation or SafePay prerequisites.
replace_once(
    '        int flaggedAppCount() { return findings.size(); }',
    '''        int flaggedAppCount() { return findings.size(); }

        int mediumRiskCount() {
            int count = 0;
            for (AppRiskItem item : findings) if (item.reviewScore >= 25 && item.reviewScore < 60) count++;
            return count;
        }

        int lowRiskCount() {
            int count = 0;
            for (AppRiskItem item : findings) if (item.reviewScore > 0 && item.reviewScore < 25) count++;
            return count;
        }''',
    "risk category counters",
)

score_pattern = re.compile(r'''    private int securityPostureScore\(AppRiskSummary risk\) \{.*?\n    \}\n''', re.S)
score_replacement = '''    private int remediationActionCount(AppRiskSummary risk) {
        int device = auditIssueCount();
        int appGroup = (risk != null && risk.flaggedAppCount() > 0) ? 1 : 0;
        return device + appGroup;
    }

    private int securityPostureScore(AppRiskSummary risk) {
        int deviceIssues = auditIssueCount();
        int high = risk == null ? 0 : risk.highRiskCount();
        int medium = risk == null ? 0 : risk.mediumRiskCount();
        int low = risk == null ? 0 : risk.lowRiskCount();

        // Bounded penalties: repeated low-confidence app signals are grouped instead of
        // being counted linearly. The score is posture guidance, never a malware probability.
        int devicePenalty = Math.min(45, deviceIssues * 8);
        int highPenalty = Math.min(30, high * 6);
        int mediumPenalty = Math.min(15, medium * 2);
        int lowPenalty = low > 0 ? 5 : 0;
        int score = 100 - devicePenalty - highPenalty - mediumPenalty - lowPenalty;
        return Math.max(0, Math.min(100, score));
    }
'''
s, n = score_pattern.subn(score_replacement, s, count=1)
if n != 1:
    raise SystemExit(f"patch failed [balanced posture score]: found {n}")

# Group app review into one remediation destination instead of presenting every flagged
# application as a separate top-level action on Home/Drawer/Action Center.
s = s.replace('int homeActions = homeIssues + homePosture.flaggedAppCount();',
              'int homeActions = remediationActionCount(homePosture);')
s = s.replace('int drawerActions = drawerIssues + drawerRisk.flaggedAppCount();',
              'int drawerActions = remediationActionCount(drawerRisk);')
s = s.replace('int total = deviceIssues + appFindings;',
              'int total = deviceIssues + (appFindings > 0 ? 1 : 0);')

# Scan completion is independent of remediation and protected-session prerequisites.
scan_pattern = re.compile(r'''    private void runQuickScan\(\) \{.*?\n    \}\n''', re.S)
scan_replacement = '''    private void runQuickScan() {
        AppRiskSummary risk = analyzeAppRisk();
        int issues = auditIssueCount();
        int score = securityPostureScore(risk);
        String event = t("Device scan completed • " + risk.visible + " apps checked • " + issues + " device finding(s) • " + risk.flaggedAppCount() + " app review signal(s)",
                "اسکن دستگاه کامل شد • " + risk.visible + " برنامه بررسی شد • " + issues + " یافته دستگاه • " + risk.flaggedAppCount() + " سیگنال بررسی برنامه");
        recordActivity(event);
        Toast.makeText(this,
                t("Scan completed • posture " + score + "/100. Findings are recommendations and do not block scanning.",
                  "اسکن کامل شد • امتیاز وضعیت " + score + "/100. یافته‌ها پیشنهاد بررسی هستند و مانع اسکن نمی‌شوند."),
                Toast.LENGTH_LONG).show();
        renderHome();
    }
'''
s, n = scan_pattern.subn(scan_replacement, s, count=1)
if n != 1:
    raise SystemExit(f"patch failed [scan completion UX]: found {n}")

# Make the scan CTA explicit. Protected-session gating remains isolated to SafePay/browser startup.
s = s.replace('t("Review device", "بررسی دستگاه")', 't("Scan device", "اسکن دستگاه")')
s = s.replace('t("Recheck security posture", "بررسی مجدد وضعیت امنیتی")', 't("Scan again", "اسکن مجدد")')

# Version metadata.
s = s.replace('0.8.7 ALPHA', '0.8.8 ALPHA')
s = s.replace('0.8.7 Alpha • versionCode 807', '0.8.8 Alpha • versionCode 808')
s = s.replace('0.8.7 Alpha', '0.8.8 Alpha')
s = s.replace('VARA 0.8.7 requires Android 8.0 / API 26 or newer.', 'VARA 0.8.8 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+807\b', 'versionCode 808', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.8\.7-alpha['\"]", "versionName '0.8.8-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

# Replace the Android fallback icon with a real VARA adaptive launcher icon.
m = manifest.read_text(encoding="utf-8")
if 'android:icon="@mipmap/ic_vara_launcher"' not in m:
    m = m.replace('android:label="VARA Security"',
                  'android:label="VARA Security"\n        android:icon="@mipmap/ic_vara_launcher"\n        android:roundIcon="@mipmap/ic_vara_launcher"')
manifest.write_text(m, encoding="utf-8")

values = root / "app/src/main/res/values"
drawable = root / "app/src/main/res/drawable"
mipmap = root / "app/src/main/res/mipmap-anydpi-v26"
values.mkdir(parents=True, exist_ok=True)
drawable.mkdir(parents=True, exist_ok=True)
mipmap.mkdir(parents=True, exist_ok=True)

(values / "vara_launcher_colors.xml").write_text('''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <color name="vara_launcher_bg">#10354A</color>
</resources>
''', encoding="utf-8")

(drawable / "ic_vara_launcher_foreground.xml").write_text('''<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp" android:height="108dp"
    android:viewportWidth="108" android:viewportHeight="108">
    <path android:fillColor="#18A6A6"
        android:pathData="M54,20 L82,31 L79,59 C77,75 67,85 54,91 C41,85 31,75 29,59 L26,31 Z"/>
    <path android:fillColor="#FFFFFFFF"
        android:pathData="M43,55 L51,63 L67,43 L72,47 L52,72 L38,59 Z"/>
</vector>
''', encoding="utf-8")

(mipmap / "ic_vara_launcher.xml").write_text('''<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@color/vara_launcher_bg" />
    <foreground android:drawable="@drawable/ic_vara_launcher_foreground" />
</adaptive-icon>
''', encoding="utf-8")

checks = [
    'remediationActionCount(AppRiskSummary risk)',
    'mediumRiskCount()',
    'lowRiskCount()',
    'Scan completed • posture ',
    'findings are recommendations and do not block scanning',
    '0.8.8 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")
if 'android:icon="@mipmap/ic_vara_launcher"' not in m:
    raise SystemExit("launcher icon not wired in manifest")
print("VARA Security 0.8.8 scan UX, bounded posture score and branded launcher icon patch applied")
