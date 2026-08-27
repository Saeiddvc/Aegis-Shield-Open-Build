from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_089.py <android-project-root>")

root = Path(sys.argv[1])
java = root / "app/src/main/java/com/varasecurity/alpha031/MainActivity.java"
gradle = root / "app/build.gradle"
s = java.read_text(encoding="utf-8")

# 0.8.9: make scan completion a first-class, non-blocking result flow. The scan
# always finishes, shows what was checked, and clearly separates findings from
# remediation and SafePay prerequisites.
if 'Scan completed • posture ' not in s:
    raise SystemExit('validated 0.8.8 scan UX prerequisite missing')

scan_results = r'''
    private void renderScanResults(int apps, int deviceFindings, int appFindings, int postureScore) {
        currentPage = "scanresult";
        basePage();
        addTopBar(t("Scan results", "نتیجه اسکن"), true);

        LinearLayout hero = card();
        boolean clear = deviceFindings == 0 && appFindings == 0;
        hero.setBackground(gradient(clear ? TEAL_DARK : NAVY, clear ? Color.rgb(17,142,134) : NAVY_2, 24));
        hero.addView(tv(t("Scan completed", "اسکن کامل شد"), 22, Color.WHITE, true));
        hero.addView(tv(t("Posture " + postureScore + "/100", "امتیاز وضعیت " + postureScore + "/100"), 17, Color.WHITE, true));
        hero.addView(tv(clear
                ? t("No current device or app review findings were observed.", "در بررسی فعلی، یافته‌ای برای دستگاه یا برنامه‌ها مشاهده نشد.")
                : t("Scanning completed successfully. Findings below are review recommendations and did not block the scan.", "اسکن با موفقیت کامل شد. موارد زیر پیشنهاد بررسی هستند و مانع اجرای اسکن نشده‌اند."),
                13, Color.rgb(236,244,246), false));
        content.addView(hero);

        LinearLayout summary = card();
        summary.addView(tv(t("What was checked", "خلاصه بررسی"), 17, NAVY, true));
        LinearLayout metrics = new LinearLayout(this);
        metrics.setOrientation(LinearLayout.HORIZONTAL);
        metrics.setPadding(0, dp(14), 0, 0);
        metrics.addView(metric(String.valueOf(apps), t("Apps", "برنامه")), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        metrics.addView(metric(String.valueOf(deviceFindings), t("Device findings", "موارد دستگاه")), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        metrics.addView(metric(String.valueOf(appFindings), t("App signals", "سیگنال برنامه")), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        summary.addView(metrics);
        content.addView(summary);

        LinearLayout guidance = card();
        guidance.addView(tv(t("Scan and remediation are separate", "اسکن و اصلاح تنظیمات از هم جدا هستند"), 16, NAVY, true));
        guidance.addView(tv(t("You can scan at any time. Device settings and app-review signals are shown afterward so you can decide what to review. Only SafePay and protected browsing apply their own security prerequisites at session start.",
                "اسکن در هر زمان قابل اجراست. تنظیمات دستگاه و سیگنال‌های برنامه پس از اسکن نمایش داده می‌شوند تا خودتان موارد لازم را بررسی کنید. فقط SafePay و مرور محافظت‌شده هنگام شروع نشست، پیش‌نیازهای امنیتی مستقل خود را کنترل می‌کنند."), 13, MUTED, false));
        content.addView(guidance);

        if (deviceFindings > 0) {
            Button reviewDevice = secondary(t("Review device findings", "بررسی موارد دستگاه"));
            LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(50));
            p.setMargins(0, dp(8), 0, 0);
            content.addView(reviewDevice, p);
            reviewDevice.setOnClickListener(v -> renderAudit());
        }
        if (appFindings > 0) {
            Button reviewApps = secondary(t("Review app findings", "بررسی موارد برنامه‌ها"));
            LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(50));
            p.setMargins(0, dp(8), 0, 0);
            content.addView(reviewApps, p);
            reviewApps.setOnClickListener(v -> renderAppReview());
        }

        Button scanAgain = secondary(t("Scan again", "اسکن مجدد"));
        LinearLayout.LayoutParams sp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(50));
        sp.setMargins(0, dp(8), 0, 0);
        content.addView(scanAgain, sp);
        scanAgain.setOnClickListener(v -> runQuickScan());

        Button done = secondary(t("Done", "بازگشت به خانه"));
        LinearLayout.LayoutParams dpv = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(50));
        dpv.setMargins(0, dp(8), 0, 0);
        content.addView(done, dpv);
        done.setOnClickListener(v -> renderHome());
    }

'''

anchor = '    private void runQuickScan() {'
if s.count(anchor) != 1:
    raise SystemExit(f'patch failed [scan result insertion]: found {s.count(anchor)}')
s = s.replace(anchor, scan_results + anchor, 1)

scan_pattern = re.compile(r'''    private void runQuickScan\(\) \{.*?\n    \}\n''', re.S)
scan_replacement = '''    private void runQuickScan() {
        AppRiskSummary risk = analyzeAppRisk();
        int issues = auditIssueCount();
        int score = securityPostureScore(risk);
        String event = t("Device scan completed • " + risk.visible + " apps checked • " + issues + " device finding(s) • " + risk.flaggedAppCount() + " app review signal(s)",
                "اسکن دستگاه کامل شد • " + risk.visible + " برنامه بررسی شد • " + issues + " یافته دستگاه • " + risk.flaggedAppCount() + " سیگنال بررسی برنامه");
        recordActivity(event);
        renderScanResults(risk.visible, issues, risk.flaggedAppCount(), score);
    }
'''
s, n = scan_pattern.subn(scan_replacement, s, count=1)
if n != 1:
    raise SystemExit(f"patch failed [scan result routing]: found {n}")

# Version metadata.
s = s.replace('0.8.8 ALPHA', '0.8.9 ALPHA')
s = s.replace('0.8.8 Alpha • versionCode 808', '0.8.9 Alpha • versionCode 809')
s = s.replace('0.8.8 Alpha', '0.8.9 Alpha')
s = s.replace('VARA 0.8.8 requires Android 8.0 / API 26 or newer.', 'VARA 0.8.9 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+808\b', 'versionCode 809', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.8\.8-alpha['\"]", "versionName '0.8.9-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'renderScanResults(int apps, int deviceFindings, int appFindings, int postureScore)',
    'Scan and remediation are separate',
    'Review device findings',
    'Review app findings',
    'renderScanResults(risk.visible, issues, risk.flaggedAppCount(), score)',
    '0.8.9 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.8.9 scan-result workflow patch applied")
