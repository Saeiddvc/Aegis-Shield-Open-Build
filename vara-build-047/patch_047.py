from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_047.py <android-project-root>")

root = Path(sys.argv[1])
java = root / "app/src/main/java/com/varasecurity/alpha031/MainActivity.java"
gradle = root / "app/build.gradle"
s = java.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str):
    global s
    count = s.count(old)
    if count != 1:
        raise SystemExit(f"patch failed [{label}]: expected 1 match, found {count}")
    s = s.replace(old, new, 1)


# Upgrade the local posture model from aggregate counters to per-application findings.
old_model = '''    private static class AppRiskSummary {
        int visible;
        int userApps;
        int debuggable;
        int legacyTarget;
        int noInstallerAttribution;

        int highRiskCount() { return debuggable; }
        int reviewCount() { return legacyTarget + noInstallerAttribution; }
    }'''
new_model = '''    private static class AppRiskItem {
        String packageName;
        String label;
        int targetSdk;
        String installer;
        boolean debuggable;
        boolean legacyTarget;
        boolean noInstallerAttribution;
        int reviewScore;

        String priority() {
            if (reviewScore >= 60) return "HIGH";
            if (reviewScore >= 25) return "MEDIUM";
            return "LOW";
        }
    }

    private static class AppRiskSummary {
        int visible;
        int userApps;
        int debuggable;
        int legacyTarget;
        int noInstallerAttribution;
        final java.util.List<AppRiskItem> findings = new java.util.ArrayList<>();

        int highRiskCount() {
            int count = 0;
            for (AppRiskItem item : findings) if (item.reviewScore >= 60) count++;
            return count;
        }

        int flaggedAppCount() { return findings.size(); }
    }'''
replace_once(old_model, new_model, "per-app posture model")

start = s.index('    private AppRiskSummary analyzeAppRisk() {')
end = s.index('    private int installedApps()', start)
new_analyzer = '''    private AppRiskSummary analyzeAppRisk() {
        AppRiskSummary out = new AppRiskSummary();
        try {
            java.util.List<PackageInfo> packages = getPackageManager().getInstalledPackages(0);
            out.visible = packages.size();
            for (PackageInfo pi : packages) {
                ApplicationInfo ai = pi.applicationInfo;
                if (ai == null) continue;
                boolean system = (ai.flags & ApplicationInfo.FLAG_SYSTEM) != 0;
                if (system) continue;
                out.userApps++;

                AppRiskItem item = new AppRiskItem();
                item.packageName = pi.packageName;
                try {
                    CharSequence appLabel = ai.loadLabel(getPackageManager());
                    item.label = appLabel == null ? pi.packageName : appLabel.toString();
                } catch (Exception ignored) {
                    item.label = pi.packageName;
                }
                item.targetSdk = ai.targetSdkVersion;
                item.debuggable = (ai.flags & ApplicationInfo.FLAG_DEBUGGABLE) != 0;
                item.legacyTarget = ai.targetSdkVersion > 0 && ai.targetSdkVersion < 28;
                try {
                    item.installer = getPackageManager().getInstallerPackageName(pi.packageName);
                } catch (Exception ignored) {
                    item.installer = null;
                }
                item.noInstallerAttribution = item.installer == null || item.installer.trim().isEmpty();

                // Explainable review score. This is a local review-priority heuristic, not a malware probability.
                item.reviewScore = 0;
                if (item.debuggable) item.reviewScore += 60;
                if (item.legacyTarget) item.reviewScore += 25;
                if (item.noInstallerAttribution) item.reviewScore += 15;
                if (item.reviewScore > 100) item.reviewScore = 100;

                if (item.debuggable) out.debuggable++;
                if (item.legacyTarget) out.legacyTarget++;
                if (item.noInstallerAttribution) out.noInstallerAttribution++;
                if (item.reviewScore > 0) out.findings.add(item);
            }
            java.util.Collections.sort(out.findings, (a, b) -> {
                int score = Integer.compare(b.reviewScore, a.reviewScore);
                if (score != 0) return score;
                String al = a.label == null ? a.packageName : a.label;
                String bl = b.label == null ? b.packageName : b.label;
                return al.compareToIgnoreCase(bl);
            });
        } catch (Exception ignored) {
            // Keep the report usable when package visibility is restricted by Android or an OEM build.
        }
        return out;
    }

'''
s = s[:start] + new_analyzer + s[end:]

# Home and Security Report now count affected applications instead of only debuggable apps.
s = s.replace('String.valueOf(homeRisk.highRiskCount()), t("App alerts", "هشدار برنامه")',
              'String.valueOf(homeRisk.flaggedAppCount()), t("App alerts", "هشدار برنامه")')
s = s.replace('homeRisk.highRiskCount() > 0 ? DANGER : TEAL_DARK',
              'homeRisk.flaggedAppCount() > 0 ? WARN : TEAL_DARK')
s = s.replace('String.valueOf(risk.highRiskCount()), t("App alerts", "هشدار برنامه")',
              'String.valueOf(risk.flaggedAppCount()), t("App alerts", "هشدار برنامه")')

# Replace App Risk Review with an actionable, per-app, explainable findings view.
start = s.index('    private void renderAppReview() {')
end = s.index('    private LinearLayout metric(String value, String label) {', start)
new_review = r'''    private void renderAppReview() {
        currentPage = "appreview";
        basePage(); addTopBar(t("App Risk Review", "بررسی ریسک برنامه‌ها"), true);
        AppRiskSummary risk = analyzeAppRisk();

        LinearLayout hero = card();
        int flagged = risk.flaggedAppCount();
        hero.setBackground(gradient(flagged == 0 ? NAVY : WARN, flagged == 0 ? NAVY_2 : Color.rgb(157,104,24), 24));
        hero.addView(tv(flagged == 0 ? t("No app review alerts", "هشدار برنامه‌ای برای بررسی وجود ندارد") : t(flagged + " app(s) need review", flagged + " برنامه نیازمند بررسی"), 20, Color.WHITE, true));
        hero.addView(tv(t("Scores below are local review priorities based on Android package metadata. They are not malware probabilities or verdicts.", "امتیازها فقط اولویت بررسی محلی بر اساس فراداده بسته‌های Android هستند و احتمال یا تشخیص بدافزار محسوب نمی‌شوند."), 13, Color.rgb(244,248,250), false));
        content.addView(hero);

        LinearLayout overview = card();
        overview.addView(tv(t("Application posture", "وضعیت برنامه‌ها"), 17, NAVY, true));
        LinearLayout metrics = new LinearLayout(this); metrics.setOrientation(LinearLayout.HORIZONTAL); metrics.setPadding(0, dp(14), 0, 0);
        metrics.addView(metric(String.valueOf(risk.userApps), t("User apps", "برنامه کاربر")), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        metrics.addView(metric(String.valueOf(flagged), t("Flagged", "نیازمند بررسی")), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        metrics.addView(metric(String.valueOf(risk.highRiskCount()), t("High priority", "اولویت بالا")), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        overview.addView(metrics); content.addView(overview);

        LinearLayout scoring = card();
        scoring.addView(tv(t("How review priority is calculated", "نحوه محاسبه اولویت بررسی"), 16, NAVY, true));
        scoring.addView(tv(t("Debuggable +60 • Target SDK below 28 +25 • Installer attribution unavailable +15. High: 60–100, Medium: 25–59, Low: 1–24.", "قابل دیباگ +۶۰ • Target SDK کمتر از ۲۸ +۲۵ • منبع نصب نامشخص +۱۵. اولویت بالا: ۶۰ تا ۱۰۰، متوسط: ۲۵ تا ۵۹، پایین: ۱ تا ۲۴."), 13, MUTED, false));
        content.addView(scoring);

        if (risk.findings.isEmpty()) {
            LinearLayout clean = card();
            clean.addView(tv(t("Nothing requires app-level review right now.", "در حال حاضر موردی برای بررسی در سطح برنامه وجود ندارد."), 15, TEAL_DARK, true));
            clean.addView(tv(t("VARA will continue to surface package-metadata signals during local scans.", "VARA در اسکن‌های محلی، سیگنال‌های فراداده برنامه‌ها را همچنان بررسی می‌کند."), 13, MUTED, false));
            content.addView(clean);
            return;
        }

        for (AppRiskItem item : risk.findings) {
            LinearLayout app = card();
            String title = (item.label == null || item.label.trim().isEmpty()) ? item.packageName : item.label;
            int priorityColor = item.reviewScore >= 60 ? DANGER : (item.reviewScore >= 25 ? WARN : TEAL_DARK);
            app.addView(tv(title, 16, NAVY, true));
            app.addView(tv(item.packageName, 12, MUTED, false));
            app.addView(tv(t("Review score " + item.reviewScore + "/100 • " + item.priority() + " priority", "امتیاز بررسی " + item.reviewScore + " از ۱۰۰ • اولویت " + (item.reviewScore >= 60 ? "بالا" : (item.reviewScore >= 25 ? "متوسط" : "پایین"))), 14, priorityColor, true));

            java.util.List<String> reasons = new java.util.ArrayList<>();
            if (item.debuggable) reasons.add(t("Debuggable build", "نسخه قابل دیباگ"));
            if (item.legacyTarget) reasons.add(t("Target SDK " + item.targetSdk + " is below 28", "Target SDK برابر " + item.targetSdk + " و کمتر از ۲۸ است"));
            if (item.noInstallerAttribution) reasons.add(t("Installer attribution unavailable", "منبع نصب قابل تشخیص نیست"));
            app.addView(tv(android.text.TextUtils.join(" • ", reasons), 13, MUTED, false));

            Button details = secondary(t("Review app settings", "بررسی تنظیمات برنامه"));
            LinearLayout.LayoutParams bp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(48));
            bp.setMargins(0, dp(12), 0, 0);
            app.addView(details, bp);
            details.setOnClickListener(v -> {
                try {
                    Intent intent = new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS);
                    intent.setData(android.net.Uri.parse("package:" + item.packageName));
                    startActivity(intent);
                } catch (Exception e) {
                    Toast.makeText(this, t("App settings are not available on this device", "تنظیمات این برنامه در دستگاه در دسترس نیست"), Toast.LENGTH_LONG).show();
                }
            });
            content.addView(app);
        }
    }

'''
s = s[:start] + new_review + s[end:]

# Scan event reflects all app-level findings, not only high-priority findings.
s = s.replace('risk.highRiskCount() > 0', 'risk.flaggedAppCount() > 0')
s = s.replace('risk.highRiskCount() + " app alert(s)', 'risk.flaggedAppCount() + " app alert(s)')
s = s.replace('risk.highRiskCount() + " هشدار برنامه', 'risk.flaggedAppCount() + " هشدار برنامه')

# Version metadata.
s = s.replace('0.4.6 ALPHA', '0.4.7 ALPHA')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+406\b', 'versionCode 407', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.4\.6-alpha['\"]", "versionName '0.4.7-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

# Fail fast if expected release markers were not produced.
checks = [
    'class AppRiskItem',
    'flaggedAppCount()',
    'Review score ',
    'ACTION_APPLICATION_DETAILS_SETTINGS',
    '0.4.7 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.4.7 patch applied")
