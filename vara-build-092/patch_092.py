from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_092.py <android-project-root>")

root = Path(sys.argv[1])
java = root / "app/src/main/java/com/varasecurity/alpha031/MainActivity.java"
gradle = root / "app/build.gradle"
s = java.read_text(encoding="utf-8")

required = [
    'lastScanPostureScore()',
    'saveScanSnapshot(',
    'scanTrendText(',
    'renderScanResults(int apps, int deviceFindings, int appFindings, int postureScore)',
    'Protection scan',
]
for marker in required:
    if marker not in s:
        raise SystemExit(f"missing validated 0.9.1 prerequisite: {marker}")

# 0.9.2: keep a small local scan history so repeated scans are useful beyond one baseline delta.
helpers = r'''
    private java.util.List<String> scanHistoryEntries() {
        String raw = getSharedPreferences("vara_security_state", MODE_PRIVATE).getString("scan_history", "");
        java.util.ArrayList<String> out = new java.util.ArrayList<>();
        if (raw == null || raw.trim().isEmpty()) return out;
        for (String row : raw.split(";")) {
            if (row != null && !row.trim().isEmpty()) out.add(row);
        }
        return out;
    }

    private void appendScanHistory(long timestamp, int postureScore, int deviceFindings, int appFindings) {
        java.util.ArrayList<String> rows = new java.util.ArrayList<>();
        rows.add(timestamp + "," + postureScore + "," + deviceFindings + "," + appFindings);
        for (String row : scanHistoryEntries()) {
            if (rows.size() >= 5) break;
            rows.add(row);
        }
        getSharedPreferences("vara_security_state", MODE_PRIVATE).edit()
                .putString("scan_history", android.text.TextUtils.join(";", rows)).apply();
    }

    private String scanHistoryTime(long timestamp) {
        try {
            return android.text.format.DateFormat.format("yyyy-MM-dd HH:mm", new java.util.Date(timestamp)).toString();
        } catch (Exception ignored) {
            return t("Recorded scan", "اسکن ثبت‌شده");
        }
    }

    private void renderScanHistory() {
        currentPage = "scanhistory";
        basePage(); addTopBar(t("Scan History", "تاریخچه اسکن"), true);
        java.util.List<String> rows = scanHistoryEntries();

        LinearLayout hero = card();
        hero.setBackground(gradient(NAVY, NAVY_2, 24));
        hero.addView(tv(t("Recent protection scans", "اسکن‌های حفاظتی اخیر"), 20, Color.WHITE, true));
        hero.addView(tv(t("VARA keeps only the five most recent scan summaries on this device. History is local and is not a malware verdict.",
                "VARA فقط خلاصه پنج اسکن اخیر را روی همین دستگاه نگه می‌دارد. این تاریخچه محلی است و تشخیص بدافزار محسوب نمی‌شود."), 13, Color.rgb(236,244,246), false));
        content.addView(hero);

        if (rows.isEmpty()) {
            LinearLayout empty = card();
            empty.addView(tv(t("No scan history yet", "هنوز تاریخچه اسکن وجود ندارد"), 17, NAVY, true));
            empty.addView(tv(t("Run a protection scan to create the first history entry.", "برای ایجاد اولین سابقه، اسکن حفاظتی را اجرا کنید."), 13, MUTED, false));
            content.addView(empty);
        } else {
            int index = 0;
            for (String row : rows) {
                String[] p = row.split(",");
                if (p.length != 4) continue;
                try {
                    long ts = Long.parseLong(p[0]);
                    int score = Integer.parseInt(p[1]);
                    int device = Integer.parseInt(p[2]);
                    int apps = Integer.parseInt(p[3]);
                    LinearLayout item = card();
                    item.addView(tv(index == 0 ? t("Latest scan", "آخرین اسکن") : scanHistoryTime(ts), 15, NAVY, true));
                    if (index == 0) item.addView(tv(scanHistoryTime(ts), 12, MUTED, false));
                    item.addView(tv(t("Posture " + score + "/100", "امتیاز وضعیت " + score + "/100"), 18,
                            score >= 90 ? GOOD : (score >= 70 ? TEAL_DARK : WARN), true));
                    item.addView(tv(t(device + " device finding(s) • " + apps + " app review signal(s)",
                            device + " یافته دستگاه • " + apps + " سیگنال بررسی برنامه"), 12, MUTED, false));
                    content.addView(item);
                    index++;
                } catch (Exception ignored) {}
            }
        }

        Button scanAgain = primary(t("Scan device now", "اسکن دستگاه"));
        LinearLayout.LayoutParams sp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(52));
        sp.setMargins(0, dp(8), 0, 0); content.addView(scanAgain, sp);
        scanAgain.setOnClickListener(v -> runQuickScan());
    }

'''
anchor = '    private void renderScanResults(int apps, int deviceFindings, int appFindings, int postureScore) {'
if s.count(anchor) != 1:
    raise SystemExit(f"patch failed [scan history helpers]: found {s.count(anchor)}")
s = s.replace(anchor, helpers + anchor, 1)

# Add a scan-history action to the Home protection-scan card.
home_anchor = '''        scanNow.setOnClickListener(v -> runQuickScan());
        content.addView(scanStatus);'''
if s.count(home_anchor) != 1:
    raise SystemExit(f"patch failed [home scan history action]: found {s.count(home_anchor)}")
home_new = '''        scanNow.setOnClickListener(v -> runQuickScan());
        Button scanHistory = secondary(t("View scan history", "مشاهده تاریخچه اسکن"));
        LinearLayout.LayoutParams shp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(44));
        shp.setMargins(0, dp(8), 0, 0);
        scanStatus.addView(scanHistory, shp);
        scanHistory.setOnClickListener(v -> renderScanHistory());
        content.addView(scanStatus);'''
s = s.replace(home_anchor, home_new, 1)

# Persist the compact history entry after a successful scan snapshot is saved.
scan_anchor = '        saveScanSnapshot(score, issues, risk.flaggedAppCount());'
if s.count(scan_anchor) != 1:
    raise SystemExit(f"patch failed [append scan history]: found {s.count(scan_anchor)}")
s = s.replace(scan_anchor, scan_anchor + '\n        appendScanHistory(lastCompletedScanAt(), score, issues, risk.flaggedAppCount());', 1)

# Scan Results offers direct history navigation.
results_anchor = '''        Button home = secondary(t("Back to Home", "بازگشت به خانه"));'''
if s.count(results_anchor) != 1:
    raise SystemExit(f"patch failed [scan results history button]: found {s.count(results_anchor)}")
results_new = '''        Button history = secondary(t("View scan history", "مشاهده تاریخچه اسکن"));
        LinearLayout.LayoutParams hp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(48));
        hp.setMargins(0, dp(8), 0, 0); content.addView(history, hp);
        history.setOnClickListener(v -> renderScanHistory());

        Button home = secondary(t("Back to Home", "بازگشت به خانه"));'''
s = s.replace(results_anchor, results_new, 1)

# Scan history is a first-level destination; Back returns Home.
nav_anchor = '        if ("scanresult".equals(currentPage)) {'
if s.count(nav_anchor) != 1:
    raise SystemExit(f"patch failed [scan history navigation]: found {s.count(nav_anchor)}")
s = s.replace(nav_anchor, '        if ("scanhistory".equals(currentPage)) {\n            renderHome();\n            return;\n        }\n' + nav_anchor, 1)

# Version metadata.
s = s.replace('0.9.1 ALPHA', '0.9.2 ALPHA')
s = s.replace('0.9.1 Alpha • versionCode 901', '0.9.2 Alpha • versionCode 902')
s = s.replace('0.9.1 Alpha', '0.9.2 Alpha')
s = s.replace('VARA 0.9.1 requires Android 8.0 / API 26 or newer.', 'VARA 0.9.2 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+901\b', 'versionCode 902', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.9\.1-alpha['\"]", "versionName '0.9.2-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'scanHistoryEntries()',
    'appendScanHistory(',
    'renderScanHistory()',
    'Recent protection scans',
    'View scan history',
    'scan_history',
    '0.9.2 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.9.2 local scan history patch applied")
