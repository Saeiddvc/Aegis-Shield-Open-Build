from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_080.py <android-project-root>")

root = Path(sys.argv[1])
java = root / "app/src/main/java/com/varasecurity/alpha031/MainActivity.java"
gradle = root / "app/build.gradle"
s = java.read_text(encoding="utf-8")


def rep(old: str, new: str, label: str):
    global s
    count = s.count(old)
    if count != 1:
        raise SystemExit(f"patch failed [{label}]: expected 1 match, found {count}")
    s = s.replace(old, new, 1)

# 0.8.0 milestone: turn Home into a more explicit command surface. The user should
# see one recommended next action rather than having to infer priority from counters.
helpers = r'''
    private String recommendedActionTitle(int deviceIssues, int appFindings) {
        if (deviceIssues > 0) return t("Review device security first", "ابتدا امنیت دستگاه را بررسی کنید");
        if (appFindings > 0) return t("Review flagged apps", "برنامه‌های علامت‌گذاری‌شده را بررسی کنید");
        return t("No remediation required", "اقدام اصلاحی لازم نیست");
    }

    private String recommendedActionDetail(int deviceIssues, int appFindings) {
        if (deviceIssues > 0) {
            return t(deviceIssues + " device configuration finding(s) should be addressed before lower-priority app review.",
                    deviceIssues + " یافته پیکربندی دستگاه بهتر است پیش از بررسی برنامه‌ها رسیدگی شود.");
        }
        if (appFindings > 0) {
            return t(appFindings + " app review signal(s) are waiting. Review the highest-priority app first.",
                    appFindings + " سیگنال بررسی برنامه در انتظار است. ابتدا مورد با اولویت بالاتر را بررسی کنید.");
        }
        return t("Current device and app posture checks are clear. You can review the full security report or start SafePay when needed.",
                "بررسی فعلی وضعیت دستگاه و برنامه‌ها موردی نشان نمی‌دهد. در صورت نیاز گزارش کامل را ببینید یا SafePay را اجرا کنید.");
    }

'''
rep(
    '    private boolean protectedSessionPreflightReady() {',
    helpers + '    private boolean protectedSessionPreflightReady() {',
    "recommended remediation helpers",
)

rep(
    '''        readinessAction.setOnClickListener(v -> { if (protectedSessionPreflightReady()) renderBrowserStart(); else renderCompatibility(); });
        content.addView(readyCard);

        Button recheckPosture = secondary(t("Recheck security posture", "بررسی مجدد وضعیت امنیتی"));''',
    '''        readinessAction.setOnClickListener(v -> { if (protectedSessionPreflightReady()) renderBrowserStart(); else renderCompatibility(); });
        content.addView(readyCard);

        int priorityDeviceIssues = auditIssueCount();
        AppRiskSummary priorityRisk = analyzeAppRisk();
        int priorityAppFindings = priorityRisk.flaggedAppCount();
        boolean priorityClear = priorityDeviceIssues == 0 && priorityAppFindings == 0;
        LinearLayout priorityCard = card();
        priorityCard.setBackground(gradient(priorityClear ? Color.rgb(235,249,246) : Color.rgb(255,247,231),
                priorityClear ? Color.rgb(247,253,251) : Color.rgb(255,252,244), 22));
        priorityCard.addView(tv(t("Next recommended action", "اقدام پیشنهادی بعدی"), 13, MUTED, true));
        priorityCard.addView(tv(recommendedActionTitle(priorityDeviceIssues, priorityAppFindings), 18,
                priorityClear ? GOOD : WARN, true));
        priorityCard.addView(tv(recommendedActionDetail(priorityDeviceIssues, priorityAppFindings), 12, MUTED, false));
        Button priorityAction = secondary(priorityDeviceIssues > 0
                ? t("Open Device Security Audit", "باز کردن ممیزی امنیت دستگاه")
                : (priorityAppFindings > 0 ? t("Open App Risk Review", "باز کردن بررسی ریسک برنامه‌ها")
                        : t("Open Security Report", "باز کردن گزارش امنیتی")));
        LinearLayout.LayoutParams pap = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(46));
        pap.setMargins(0, dp(10), 0, 0);
        priorityCard.addView(priorityAction, pap);
        priorityAction.setOnClickListener(v -> {
            if (auditIssueCount() > 0) renderAudit();
            else if (analyzeAppRisk().flaggedAppCount() > 0) renderAppReview();
            else renderReport();
        });
        content.addView(priorityCard);

        Button recheckPosture = secondary(t("Recheck security posture", "بررسی مجدد وضعیت امنیتی"));''',
    "home recommended next action card",
)

# Drawer header carries the same recommendation so navigation and Home never disagree.
rep(
    '        head.addView(tv(t("SafePay: ", "SafePay: ") + protectedSessionReadinessText(), 11, Color.rgb(196,221,225), false));',
    '''        head.addView(tv(t("SafePay: ", "SafePay: ") + protectedSessionReadinessText(), 11, Color.rgb(196,221,225), false));
        head.addView(tv(t("Next: ", "بعدی: ") + recommendedActionTitle(auditIssueCount(), analyzeAppRisk().flaggedAppCount()),
                11, Color.rgb(196,221,225), false));''',
    "drawer remediation recommendation",
)

# Navigation hierarchy: Action Center is a first-level security destination, and its back action
# should return Home instead of bouncing through an unrelated page.
rep(
    '''        if ("audit".equals(currentPage) || "appreview".equals(currentPage)) {
            renderActionCenter();
            return;
        }
        renderHome();''',
    '''        if ("audit".equals(currentPage) || "appreview".equals(currentPage)) {
            renderActionCenter();
            return;
        }
        if ("actions".equals(currentPage) || "report".equals(currentPage) || "activity".equals(currentPage)) {
            renderHome();
            return;
        }
        renderHome();''',
    "clean first-level navigation",
)

# Version metadata.
s = s.replace('0.7.9 ALPHA', '0.8.0 ALPHA')
s = s.replace('0.7.9 Alpha • versionCode 709', '0.8.0 Alpha • versionCode 800')
s = s.replace('0.7.9 Alpha', '0.8.0 Alpha')
s = s.replace('VARA 0.7.9 requires Android 8.0 / API 26 or newer.', 'VARA 0.8.0 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+709\b', 'versionCode 800', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.7\.9-alpha['\"]", "versionName '0.8.0-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'recommendedActionTitle(',
    'recommendedActionDetail(',
    'Next recommended action',
    'Open Device Security Audit',
    'Open App Risk Review',
    'Open Security Report',
    'Next: ',
    '0.8.0 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.8.0 guided remediation and navigation UX patch applied")
