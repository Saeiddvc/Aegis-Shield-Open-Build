from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_046.py <android-project-root>")

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

# Package metadata imports used for local application posture analysis.
rep(
    'import android.content.SharedPreferences;\nimport android.graphics.Color;',
    'import android.content.SharedPreferences;\nimport android.content.pm.ApplicationInfo;\nimport android.content.pm.PackageInfo;\nimport android.graphics.Color;',
    'package metadata imports',
)
rep(
    'import java.util.Date;\nimport java.util.Locale;',
    'import java.util.Date;\nimport java.util.List;\nimport java.util.Locale;',
    'list import',
)

# Add a compact local application risk model. This is posture analysis, not malware verdicting.
rep(
    '    private String currentPage = "home";\n    private String lastSecureUrl = "https://www.google.com";',
    '''    private String currentPage = "home";
    private String lastSecureUrl = "https://www.google.com";

    private static class AppRiskSummary {
        int visible;
        int userApps;
        int debuggable;
        int legacyTarget;
        int noInstallerAttribution;

        int highRiskCount() { return debuggable; }
        int reviewCount() { return legacyTarget + noInstallerAttribution; }
    }''',
    'app risk model',
)

# Replace the simple package count helper with a richer local-only posture scan.
rep(
    '''    private int installedApps() {
        try { return getPackageManager().getInstalledPackages(0).size(); }
        catch (Exception e) { return 0; }
    }
''',
    '''    private AppRiskSummary analyzeAppRisk() {
        AppRiskSummary out = new AppRiskSummary();
        try {
            List<PackageInfo> packages = getPackageManager().getInstalledPackages(0);
            out.visible = packages.size();
            for (PackageInfo pi : packages) {
                ApplicationInfo ai = pi.applicationInfo;
                if (ai == null) continue;
                boolean system = (ai.flags & ApplicationInfo.FLAG_SYSTEM) != 0;
                if (system) continue;
                out.userApps++;
                if ((ai.flags & ApplicationInfo.FLAG_DEBUGGABLE) != 0) out.debuggable++;
                if (ai.targetSdkVersion > 0 && ai.targetSdkVersion < 28) out.legacyTarget++;
                try {
                    String installer = getPackageManager().getInstallerPackageName(pi.packageName);
                    if (installer == null || installer.trim().isEmpty()) out.noInstallerAttribution++;
                } catch (Exception ignored) {
                    // Installer attribution is advisory only and may be unavailable on some OEM builds.
                }
            }
        } catch (Exception ignored) {
            // Keep the report usable even when package visibility is restricted by the platform.
        }
        return out;
    }

    private int installedApps() { return analyzeAppRisk().visible; }
''',
    'application posture analyzer',
)

# Home security report now exposes app posture instead of a generic safe-browsing constant.
rep(
    '''        int apps = installedApps();
        metrics.addView(metric(String.valueOf(apps), t("Apps", "برنامه")), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        metrics.addView(metric(auditIssueCount() == 0 ? "0" : String.valueOf(auditIssueCount()), t("Issues", "مورد")), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        metrics.addView(metric("ON", t("Safe browsing", "مرور امن")), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));''',
    '''        AppRiskSummary homeRisk = analyzeAppRisk();
        metrics.addView(metric(String.valueOf(homeRisk.visible), t("Apps", "برنامه")), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        metrics.addView(metric(String.valueOf(auditIssueCount()), t("Device issues", "موارد دستگاه")), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        metrics.addView(metric(String.valueOf(homeRisk.highRiskCount()), t("App alerts", "هشدار برنامه")), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));''',
    'home posture metrics',
)

# Add an app-review destination to Home after Security Audit.
rep(
    '''        LinearLayout audit = featureCard("✓", t("Security Audit", "ممیزی امنیت"), t("Review risky device settings and fix them", "تنظیمات پرریسک دستگاه را بررسی و اصلاح کنید"), WARN);
        audit.setOnClickListener(v -> renderAudit());
        content.addView(audit);

        LinearLayout pay = featureCard''',
    '''        LinearLayout audit = featureCard("✓", t("Security Audit", "ممیزی امنیت"), t("Review risky device settings and fix them", "تنظیمات پرریسک دستگاه را بررسی و اصلاح کنید"), WARN);
        audit.setOnClickListener(v -> renderAudit());
        content.addView(audit);

        LinearLayout appReview = featureCard("▦", t("App Risk Review", "بررسی ریسک برنامه‌ها"), t("Review debuggable, legacy and unattributed apps", "برنامه‌های دیباگ، قدیمی و بدون منبع نصب مشخص را بررسی کنید"), homeRisk.highRiskCount() > 0 ? DANGER : TEAL_DARK);
        appReview.setOnClickListener(v -> renderAppReview());
        content.addView(appReview);

        LinearLayout pay = featureCard''',
    'home app review card',
)

# Security Report now distinguishes device findings from app posture findings.
rep(
    '''        int apps = installedApps();
        int issues = auditIssueCount();''',
    '''        AppRiskSummary risk = analyzeAppRisk();
        int apps = risk.visible;
        int issues = auditIssueCount();''',
    'report app risk analysis',
)
rep(
    '''        metrics.addView(metric(String.valueOf(apps), t("Apps visible", "برنامه قابل مشاهده")), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        metrics.addView(metric(String.valueOf(issues), t("Audit issues", "مورد ممیزی")), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        metrics.addView(metric("HTTPS", t("Secure browser", "مرور امن")), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));''',
    '''        metrics.addView(metric(String.valueOf(apps), t("Apps visible", "برنامه قابل مشاهده")), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        metrics.addView(metric(String.valueOf(issues), t("Device issues", "موارد دستگاه")), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        metrics.addView(metric(String.valueOf(risk.highRiskCount()), t("App alerts", "هشدار برنامه")), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));''',
    'report posture metrics',
)

# Add an actionable local app posture page. Labels deliberately avoid claiming malware detection.
app_review = r'''
    private void renderAppReview() {
        currentPage = "appreview";
        basePage(); addTopBar(t("App Risk Review", "بررسی ریسک برنامه‌ها"), true);
        AppRiskSummary risk = analyzeAppRisk();

        LinearLayout hero = card();
        int severe = risk.highRiskCount();
        hero.setBackground(gradient(severe == 0 ? NAVY : DANGER, severe == 0 ? NAVY_2 : Color.rgb(154,53,53), 24));
        hero.addView(tv(severe == 0 ? t("No high-priority app alerts", "هشدار پرریسک برنامه‌ای مشاهده نشد") : t(severe + " high-priority app alert(s)", severe + " هشدار پرریسک برنامه"), 20, Color.WHITE, true));
        hero.addView(tv(t("This review uses local Android package metadata. It does not label an app as malware.", "این بررسی فقط از فراداده محلی بسته‌های Android استفاده می‌کند و به‌تنهایی برنامه‌ای را بدافزار اعلام نمی‌کند."), 13, Color.rgb(236,244,246), false));
        content.addView(hero);

        LinearLayout overview = card();
        overview.addView(tv(t("Application posture", "وضعیت برنامه‌ها"), 17, NAVY, true));
        LinearLayout metrics = new LinearLayout(this); metrics.setOrientation(LinearLayout.HORIZONTAL); metrics.setPadding(0, dp(14), 0, 0);
        metrics.addView(metric(String.valueOf(risk.userApps), t("User apps", "برنامه کاربر")), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        metrics.addView(metric(String.valueOf(risk.debuggable), t("Debuggable", "قابل دیباگ")), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        metrics.addView(metric(String.valueOf(risk.legacyTarget), t("Legacy target", "هدف قدیمی")), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        overview.addView(metrics); content.addView(overview);

        LinearLayout debug = card();
        debug.addView(tv(t("Debuggable applications", "برنامه‌های قابل دیباگ"), 16, NAVY, true));
        debug.addView(tv(risk.debuggable == 0 ? t("No user application is currently marked debuggable.", "هیچ برنامه کاربری در حال حاضر با وضعیت قابل دیباگ شناسایی نشد.") : t(risk.debuggable + " user application(s) expose the Android debuggable flag. Review development or test builds before sensitive use.", risk.debuggable + " برنامه کاربری دارای پرچم debuggable است. نسخه‌های توسعه یا آزمایشی را پیش از استفاده حساس بررسی کنید."), 13, risk.debuggable == 0 ? MUTED : DANGER, false));
        content.addView(debug);

        LinearLayout legacy = card();
        legacy.addView(tv(t("Legacy Android targets", "هدف‌های قدیمی Android"), 16, NAVY, true));
        legacy.addView(tv(risk.legacyTarget == 0 ? t("No user app with target SDK below 28 was found.", "برنامه کاربری با target SDK کمتر از 28 مشاهده نشد.") : t(risk.legacyTarget + " user application(s) target an older Android security baseline. Update them where possible.", risk.legacyTarget + " برنامه کاربری بر مبنای نسخه امنیتی قدیمی‌تر Android ساخته شده است. در صورت امکان آن‌ها را به‌روزرسانی کنید."), 13, risk.legacyTarget == 0 ? MUTED : WARN, false));
        content.addView(legacy);

        LinearLayout source = card();
        source.addView(tv(t("Installer attribution", "منبع نصب"), 16, NAVY, true));
        source.addView(tv(t(risk.noInstallerAttribution + " user app(s) have no installer attribution available. This can include sideloaded apps, restored apps, OEM behavior or unavailable metadata; it is a review signal, not a verdict.", risk.noInstallerAttribution + " برنامه کاربری منبع نصب قابل تشخیص ندارند. این وضعیت می‌تواند ناشی از نصب دستی، بازیابی، رفتار سازنده یا نبود فراداده باشد و صرفاً علامت بررسی است، نه تشخیص قطعی."), 13, MUTED, false));
        content.addView(source);

        Button settings = secondary(t("Open Android app settings", "باز کردن تنظیمات برنامه‌ها"));
        LinearLayout.LayoutParams sp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(52)); sp.setMargins(0, dp(8), 0, 0); content.addView(settings, sp);
        settings.setOnClickListener(v -> {
            try { startActivity(new Intent(Settings.ACTION_MANAGE_APPLICATIONS_SETTINGS)); }
            catch (Exception e) { Toast.makeText(this, t("App settings are not available on this device", "تنظیمات برنامه‌ها در این دستگاه در دسترس نیست"), Toast.LENGTH_LONG).show(); }
        });
    }

'''
rep(
    '    private LinearLayout metric(String value, String label) {',
    app_review + '    private LinearLayout metric(String value, String label) {',
    'app risk review page',
)

# Scan event includes app posture without overstating a malware result.
rep(
    '''    private void runQuickScan() {
        int apps = installedApps();
        int issues = auditIssueCount();
        String posture = issues == 0 ? t("Good", "مناسب") : t("Review", "نیازمند بررسی");
        String event = t("Device scan • " + apps + " apps visible • posture: " + posture, "بررسی دستگاه • " + apps + " برنامه قابل مشاهده • وضعیت: " + posture);
        recordActivity(event);
        Toast.makeText(this, issues == 0 ? t("Device posture is good", "وضعیت امنیتی دستگاه مناسب است") : t("Review " + issues + " device security issue(s)", "تعداد " + issues + " مورد امنیتی نیاز به بررسی دارد"), Toast.LENGTH_LONG).show();
        renderHome();
    }''',
    '''    private void runQuickScan() {
        AppRiskSummary risk = analyzeAppRisk();
        int issues = auditIssueCount();
        boolean review = issues > 0 || risk.highRiskCount() > 0;
        String posture = review ? t("Review", "نیازمند بررسی") : t("Good", "مناسب");
        String event = t("Device scan • " + risk.visible + " apps • " + risk.highRiskCount() + " app alert(s) • posture: " + posture, "بررسی دستگاه • " + risk.visible + " برنامه • " + risk.highRiskCount() + " هشدار برنامه • وضعیت: " + posture);
        recordActivity(event);
        Toast.makeText(this, review ? t("Review device settings and app alerts", "تنظیمات دستگاه و هشدارهای برنامه را بررسی کنید") : t("Current device posture is good", "وضعیت فعلی دستگاه مناسب است"), Toast.LENGTH_LONG).show();
        renderHome();
    }''',
    'scan app posture event',
)

# Drawer gets a direct route and active state for the app review page.
rep(
    '''        addDrawerItem(list, "◷", t("Activity Log", "گزارش فعالیت"), t("Recent security events", "رویدادهای امنیتی اخیر"), v -> { closeDrawer(); renderActivityLog(); });''',
    '''        addDrawerItem(list, "◷", t("Activity Log", "گزارش فعالیت"), t("Recent security events", "رویدادهای امنیتی اخیر"), v -> { closeDrawer(); renderActivityLog(); });
        addDrawerItem(list, "▦", t("App Risk Review", "بررسی ریسک برنامه‌ها"), t("Local application posture", "وضعیت محلی برنامه‌ها"), v -> { closeDrawer(); renderAppReview(); });''',
    'drawer app review route',
)
rep(
    '''        if ("activity".equals(currentPage) && title.equals(t("Activity Log", "گزارش فعالیت"))) return true;''',
    '''        if ("activity".equals(currentPage) && title.equals(t("Activity Log", "گزارش فعالیت"))) return true;
        if ("appreview".equals(currentPage) && title.equals(t("App Risk Review", "بررسی ریسک برنامه‌ها"))) return true;''',
    'drawer app review active state',
)

# Version labels.
rep('TextView buildTag = tv("0.4.5 ALPHA", 10, Color.WHITE, true);', 'TextView buildTag = tv("0.4.6 ALPHA", 10, Color.WHITE, true);', 'drawer build tag')
rep('addDrawerItem(list, "i", t("About VARA", "درباره VARA"), "0.4.5 Alpha",', 'addDrawerItem(list, "i", t("About VARA", "درباره VARA"), "0.4.6 Alpha",', 'drawer about version')
rep('about.addView(tv("0.4.5 Alpha • versionCode 405", 13, MUTED, false));', 'about.addView(tv("0.4.6 Alpha • versionCode 406", 13, MUTED, false));', 'settings version')
rep('hero.addView(tv("0.4.5 Alpha • versionCode 405", 13, Color.rgb(220,236,239), false));', 'hero.addView(tv("0.4.6 Alpha • versionCode 406", 13, Color.rgb(220,236,239), false));', 'about version')

java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
for old, new in [("versionCode 405", "versionCode 406"), ("versionName '0.4.5-alpha'", "versionName '0.4.6-alpha'")]:
    if g.count(old) != 1:
        raise SystemExit(f"gradle patch failed: {old}")
    g = g.replace(old, new, 1)
gradle.write_text(g, encoding="utf-8")

print("VARA 0.4.6 patch applied successfully")
