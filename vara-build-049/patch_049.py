from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_049.py <android-project-root>")

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


# Home posture must reflect both device configuration findings and app-review findings.
rep(
    '        int homeIssues = auditIssueCount();\n        TextView status = tv(homeIssues == 0 ? t("You are protected", "دستگاه شما محافظت می‌شود") : t("Protection needs attention", "محافظت نیاز به رسیدگی دارد"), 24, Color.WHITE, true);',
    '        AppRiskSummary homePosture = analyzeAppRisk();\n        int homeIssues = auditIssueCount();\n        int homeActions = homeIssues + homePosture.flaggedAppCount();\n        TextView status = tv(homeActions == 0 ? t("You are protected", "دستگاه شما محافظت می‌شود") : t("Protection needs attention", "محافظت نیاز به رسیدگی دارد"), 24, Color.WHITE, true);',
    "unified home posture",
)
rep(
    '        TextView sub = tv(homeIssues == 0 ? t("Core protection is active. Your current device audit is clear.", "محافظت اصلی فعال است و ممیزی فعلی دستگاه موردی نشان نمی‌دهد.") : t(homeIssues + " device setting(s) should be reviewed.", homeIssues + " مورد از تنظیمات دستگاه نیاز به بررسی دارد."), 14, Color.rgb(220, 236, 239), false);',
    '        TextView sub = tv(homeActions == 0 ? t("Core protection is active. The current security posture is clear.", "محافظت اصلی فعال است و وضعیت امنیتی فعلی موردی نشان نمی‌دهد.") : t(homeActions + " security action(s) are waiting for review.", homeActions + " اقدام امنیتی نیازمند بررسی است."), 14, Color.rgb(220, 236, 239), false);',
    "unified home subtitle",
)
rep(
    '        TextView stateChip = tv(homeIssues == 0 ? t("SECURE", "ایمن") : t("REVIEW " + homeIssues, "بررسی " + homeIssues), 11, Color.WHITE, true);',
    '        TextView stateChip = tv(homeActions == 0 ? t("SECURE", "ایمن") : t("REVIEW " + homeActions, "بررسی " + homeActions), 11, Color.WHITE, true);',
    "unified home chip",
)
rep(
    '        stateChip.setBackground(rounded(homeIssues == 0 ? GOOD : WARN, 14));',
    '        stateChip.setBackground(rounded(homeActions == 0 ? GOOD : WARN, 14));',
    "unified home chip color",
)
rep(
    '        LinearLayout.LayoutParams scp = new LinearLayout.LayoutParams(dp(homeIssues == 0 ? 88 : 112), dp(30));',
    '        LinearLayout.LayoutParams scp = new LinearLayout.LayoutParams(dp(homeActions == 0 ? 88 : 112), dp(30));',
    "unified home chip size",
)
rep(
    '        AppRiskSummary homeRisk = analyzeAppRisk();',
    '        AppRiskSummary homeRisk = homePosture;',
    "reuse home posture",
)

# Give Home one operational destination that aggregates everything needing remediation.
rep(
    '        report.setOnClickListener(v -> renderReport());\n        content.addView(report);',
    '''        report.setOnClickListener(v -> renderReport());
        content.addView(report);

        LinearLayout actionCenter = featureCard("!", t("Action Center", "مرکز اقدامات"),
                homeActions == 0 ? t("No security actions are waiting", "اقدام امنیتی در انتظار نیست")
                        : t(homeActions + " action(s) ready for review", homeActions + " اقدام آماده بررسی است"),
                homeActions == 0 ? GOOD : WARN);
        actionCenter.setOnClickListener(v -> renderActionCenter());
        content.addView(actionCenter);''',
    "home action center",
)

# Add a remediation-first Action Center with drill-down to the existing audit and app-review flows.
action_center = r'''
    private void renderActionCenter() {
        currentPage = "actions";
        basePage(); addTopBar(t("Action Center", "مرکز اقدامات"), true);
        AppRiskSummary risk = analyzeAppRisk();
        int deviceIssues = auditIssueCount();
        int appFindings = risk.flaggedAppCount();
        int total = deviceIssues + appFindings;

        LinearLayout hero = card();
        hero.setBackground(gradient(total == 0 ? NAVY : WARN, total == 0 ? NAVY_2 : Color.rgb(157,104,24), 24));
        hero.addView(tv(total == 0 ? t("No actions required", "اقدامی لازم نیست") : t(total + " security action(s)", total + " اقدام امنیتی"), 21, Color.WHITE, true));
        hero.addView(tv(total == 0 ? t("Current device and app posture checks do not require remediation.", "بررسی فعلی وضعیت دستگاه و برنامه‌ها نیاز به اصلاحی نشان نمی‌دهد.") : t("Review the highest-impact findings first. VARA opens the relevant Android settings but does not change sensitive settings automatically.", "ابتدا موارد با اثر بیشتر را بررسی کنید. VARA تنظیمات مرتبط Android را باز می‌کند اما تنظیمات حساس را به‌صورت خودکار تغییر نمی‌دهد."), 13, Color.rgb(244,248,250), false));
        content.addView(hero);

        LinearLayout summary = card();
        summary.addView(tv(t("Remediation queue", "صف اقدامات اصلاحی"), 17, NAVY, true));
        LinearLayout metrics = new LinearLayout(this); metrics.setOrientation(LinearLayout.HORIZONTAL); metrics.setPadding(0, dp(14), 0, 0);
        metrics.addView(metric(String.valueOf(deviceIssues), t("Device", "دستگاه")), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        metrics.addView(metric(String.valueOf(risk.highRiskCount()), t("High apps", "برنامه پرریسک")), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        metrics.addView(metric(String.valueOf(appFindings), t("App review", "بررسی برنامه")), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        summary.addView(metrics);
        content.addView(summary);

        LinearLayout device = card();
        device.addView(tv(t("Device Security Audit", "ممیزی امنیت دستگاه"), 16, NAVY, true));
        device.addView(tv(deviceIssues == 0 ? t("No device configuration issue is currently detected.", "در حال حاضر موردی در پیکربندی امنیتی دستگاه شناسایی نشده است.") : t(deviceIssues + " device setting(s) need review.", deviceIssues + " مورد از تنظیمات دستگاه نیاز به بررسی دارد."), 13, deviceIssues == 0 ? MUTED : WARN, false));
        Button audit = secondary(deviceIssues == 0 ? t("View audit", "مشاهده ممیزی") : t("Fix device findings", "رسیدگی به موارد دستگاه"));
        LinearLayout.LayoutParams ap = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(48)); ap.setMargins(0, dp(12), 0, 0); device.addView(audit, ap);
        audit.setOnClickListener(v -> renderAudit());
        content.addView(device);

        LinearLayout apps = card();
        apps.addView(tv(t("App Risk Review", "بررسی ریسک برنامه‌ها"), 16, NAVY, true));
        apps.addView(tv(appFindings == 0 ? t("No application metadata finding currently needs review.", "در حال حاضر یافته‌ای در فراداده برنامه‌ها نیازمند بررسی نیست.") : t(appFindings + " app(s) have review signals; " + risk.highRiskCount() + " are high priority.", appFindings + " برنامه دارای سیگنال بررسی است؛ " + risk.highRiskCount() + " مورد اولویت بالا دارد."), 13, appFindings == 0 ? MUTED : WARN, false));
        Button appReview = secondary(appFindings == 0 ? t("View app posture", "مشاهده وضعیت برنامه‌ها") : t("Review flagged apps", "بررسی برنامه‌های علامت‌گذاری‌شده"));
        LinearLayout.LayoutParams rp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(48)); rp.setMargins(0, dp(12), 0, 0); apps.addView(appReview, rp);
        appReview.setOnClickListener(v -> renderAppReview());
        content.addView(apps);
    }

'''
rep(
    '    private LinearLayout metric(String value, String label) {',
    action_center + '    private LinearLayout metric(String value, String label) {',
    "action center page",
)

# Expose Action Center in the branded drawer and selected-state logic.
rep(
    '        addDrawerItem(list, "▤", t("Security Report", "گزارش امنیتی"), t("Device security summary", "خلاصه وضعیت امنیت دستگاه"), v -> { closeDrawer(); renderReport(); });\n        addDrawerItem(list, "◷", t("Activity Log", "گزارش فعالیت"), t("Recent security events", "رویدادهای امنیتی اخیر"), v -> { closeDrawer(); renderActivityLog(); });',
    '        addDrawerItem(list, "▤", t("Security Report", "گزارش امنیتی"), t("Device security summary", "خلاصه وضعیت امنیت دستگاه"), v -> { closeDrawer(); renderReport(); });\n        addDrawerItem(list, "!", t("Action Center", "مرکز اقدامات"), t("Prioritized remediation queue", "صف اولویت‌بندی‌شده اقدامات"), v -> { closeDrawer(); renderActionCenter(); });\n        addDrawerItem(list, "◷", t("Activity Log", "گزارش فعالیت"), t("Recent security events", "رویدادهای امنیتی اخیر"), v -> { closeDrawer(); renderActivityLog(); });',
    "drawer action center route",
)
rep(
    '        if ("report".equals(currentPage) && title.equals(t("Security Report", "گزارش امنیتی"))) return true;\n        if ("activity".equals(currentPage)',
    '        if ("report".equals(currentPage) && title.equals(t("Security Report", "گزارش امنیتی"))) return true;\n        if ("actions".equals(currentPage) && title.equals(t("Action Center", "مرکز اقدامات"))) return true;\n        if ("activity".equals(currentPage)',
    "drawer action center active state",
)

# Harden every top-level WebView navigation with the same destination policy used by SafePay.
rep(
    '''            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri u = request.getUrl();
                if (!"https".equalsIgnoreCase(u.getScheme())) { Toast.makeText(MainActivity.this, t("Blocked non-HTTPS navigation", "پیمایش غیر HTTPS مسدود شد"), Toast.LENGTH_SHORT).show(); return true; }
                return false;
            }''',
    '''            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                if (!request.isForMainFrame()) return false;
                Uri u = request.getUrl();
                String validated = normalizeHttps(u == null ? null : u.toString());
                if (validated == null) {
                    Toast.makeText(MainActivity.this, t("Blocked unsafe browser destination", "مقصد ناامن مرورگر مسدود شد"), Toast.LENGTH_SHORT).show();
                    return true;
                }
                return false;
            }''',
    "secure browser navigation policy",
)

# Version metadata across user-visible labels and Gradle.
s = s.replace('0.4.8 ALPHA', '0.4.9 ALPHA')
s = s.replace('0.4.8 Alpha • versionCode 408', '0.4.9 Alpha • versionCode 409')
s = s.replace('0.4.8 Alpha', '0.4.9 Alpha')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+408\b', 'versionCode 409', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.4\.8-alpha['\"]", "versionName '0.4.9-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'currentPage = "actions"',
    'Remediation queue',
    'homePosture.flaggedAppCount()',
    'request.isForMainFrame()',
    'Blocked unsafe browser destination',
    '0.4.9 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.4.9 action-center and navigation-policy patch applied")
