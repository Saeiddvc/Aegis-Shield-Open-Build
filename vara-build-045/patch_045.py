from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_045.py <android-project-root>")

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

# Home: make recent activity actionable and expose the full event log.
rep(
    '        activity.addView(time, tlp);\n        content.addView(activity);',
    '        activity.addView(time, tlp);\n        activity.setOnClickListener(v -> renderActivityLog());\n        content.addView(activity);',
    "home activity route",
)

# Replace the one-slot scan history with a rolling local activity history.
rep(
    '    private void runQuickScan() {\n        int apps = installedApps();\n        int issues = auditIssueCount();\n        String event = t("Scanned " + apps + " apps • " + issues + " device issues", "تعداد " + apps + " برنامه بررسی شد • " + issues + " مورد تنظیمات دستگاه");\n        prefs.edit().putString("last_activity", event).putString("last_activity_time", DateFormat.getDateTimeInstance(DateFormat.SHORT, DateFormat.SHORT).format(new Date())).apply();\n        Toast.makeText(this, issues == 0 ? t("No device configuration issues found", "مورد پرریسکی در تنظیمات دستگاه پیدا نشد") : t("Review " + issues + " device security issues", "تعداد " + issues + " مورد امنیتی نیاز به بررسی دارد"), Toast.LENGTH_LONG).show();\n        renderHome();\n    }',
    '    private void recordActivity(String event) {\n        String now = DateFormat.getDateTimeInstance(DateFormat.SHORT, DateFormat.SHORT).format(new Date());\n        SharedPreferences.Editor e = prefs.edit();\n        for (int i = 4; i >= 1; i--) {\n            e.putString("activity_" + i, prefs.getString("activity_" + (i - 1), ""));\n            e.putString("activity_time_" + i, prefs.getString("activity_time_" + (i - 1), ""));\n        }\n        e.putString("activity_0", event).putString("activity_time_0", now);\n        e.putString("last_activity", event).putString("last_activity_time", now).apply();\n    }\n\n    private void runQuickScan() {\n        int apps = installedApps();\n        int issues = auditIssueCount();\n        String posture = issues == 0 ? t("Good", "مناسب") : t("Review", "نیازمند بررسی");\n        String event = t("Device scan • " + apps + " apps visible • posture: " + posture, "بررسی دستگاه • " + apps + " برنامه قابل مشاهده • وضعیت: " + posture);\n        recordActivity(event);\n        Toast.makeText(this, issues == 0 ? t("Device posture is good", "وضعیت امنیتی دستگاه مناسب است") : t("Review " + issues + " device security issue(s)", "تعداد " + issues + " مورد امنیتی نیاز به بررسی دارد"), Toast.LENGTH_LONG).show();\n        renderHome();\n    }',
    "rolling activity history",
)

activity_method = r'''
    private void renderActivityLog() {
        currentPage = "activity";
        basePage(); addTopBar(t("Activity Log", "گزارش فعالیت"), true);
        LinearLayout summary = card();
        summary.setBackground(gradient(NAVY, NAVY_2, 24));
        summary.addView(tv(t("Recent security activity", "فعالیت‌های امنیتی اخیر"), 20, Color.WHITE, true));
        summary.addView(tv(t("Stored locally on this device. Up to five recent events are shown.", "این اطلاعات به‌صورت محلی روی دستگاه نگهداری می‌شود و پنج رویداد آخر نمایش داده می‌شود."), 13, Color.rgb(220,236,239), false));
        content.addView(summary);

        boolean any = false;
        for (int i = 0; i < 5; i++) {
            String event = prefs.getString("activity_" + i, "");
            if (event == null || event.trim().isEmpty()) continue;
            any = true;
            LinearLayout item = card();
            TextView dot = tv("●  " + event, 14, TEXT, false);
            item.addView(dot);
            String when = prefs.getString("activity_time_" + i, "—");
            TextView tm = tv(when, 12, MUTED, false);
            LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
            p.setMargins(0, dp(7), 0, 0);
            item.addView(tm, p);
            content.addView(item);
        }
        if (!any) {
            LinearLayout empty = card();
            empty.addView(tv(t("No security activity has been recorded yet.", "هنوز فعالیت امنیتی ثبت نشده است."), 14, MUTED, false));
            content.addView(empty);
        }
    }

'''
rep(
    '    private LinearLayout metric(String value, String label) {',
    activity_method + '    private LinearLayout metric(String value, String label) {',
    "activity log page",
)

# Drawer: add Activity Log route and visually identify the selected destination.
rep(
    '        addDrawerItem(list, "▤", t("Security Report", "گزارش امنیتی"), t("Device security summary", "خلاصه وضعیت امنیت دستگاه"), v -> { closeDrawer(); renderReport(); });',
    '        addDrawerItem(list, "▤", t("Security Report", "گزارش امنیتی"), t("Device security summary", "خلاصه وضعیت امنیت دستگاه"), v -> { closeDrawer(); renderReport(); });\n        addDrawerItem(list, "◷", t("Activity Log", "گزارش فعالیت"), t("Recent security events", "رویدادهای امنیتی اخیر"), v -> { closeDrawer(); renderActivityLog(); });',
    "drawer activity route",
)
rep(
    '        LinearLayout row = new LinearLayout(this); row.setOrientation(LinearLayout.HORIZONTAL); row.setGravity(Gravity.CENTER_VERTICAL); row.setPadding(dp(10), dp(10), dp(8), dp(10)); row.setBackground(rounded(Color.rgb(249,251,252), 16)); LinearLayout.LayoutParams rlp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT); rlp.setMargins(0, dp(3), 0, dp(3)); row.setLayoutParams(rlp);',
    '        LinearLayout row = new LinearLayout(this); row.setOrientation(LinearLayout.HORIZONTAL); row.setGravity(Gravity.CENTER_VERTICAL); row.setPadding(dp(10), dp(10), dp(8), dp(10)); boolean active = drawerItemActive(title); row.setBackground(rounded(active ? Color.rgb(228,247,245) : Color.rgb(249,251,252), 16)); LinearLayout.LayoutParams rlp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT); rlp.setMargins(0, dp(3), 0, dp(3)); row.setLayoutParams(rlp);',
    "drawer active background",
)

active_helper = r'''
    private boolean drawerItemActive(String title) {
        if ("home".equals(currentPage) && title.equals(t("Home", "خانه"))) return true;
        if ("report".equals(currentPage) && title.equals(t("Security Report", "گزارش امنیتی"))) return true;
        if ("activity".equals(currentPage) && title.equals(t("Activity Log", "گزارش فعالیت"))) return true;
        if ("audit".equals(currentPage) && title.equals(t("Security Audit", "ممیزی امنیت"))) return true;
        if ("safepay".equals(currentPage) && title.equals("VARA SafePay")) return true;
        if (("browserStart".equals(currentPage) || "browser".equals(currentPage)) && title.equals(t("Secure Browser", "مرورگر امن"))) return true;
        if ("settings".equals(currentPage) && title.equals(t("Settings", "تنظیمات"))) return true;
        if ("about".equals(currentPage) && title.equals(t("About VARA", "درباره VARA"))) return true;
        return false;
    }

'''
rep(
    '    private void addDrawerItem(LinearLayout list, String icon, String title, String desc, View.OnClickListener click) {',
    active_helper + '    private void addDrawerItem(LinearLayout list, String icon, String title, String desc, View.OnClickListener click) {',
    "drawer active helper",
)

# Version labels.
rep('TextView buildTag = tv("0.4.4 ALPHA", 10, Color.WHITE, true);', 'TextView buildTag = tv("0.4.5 ALPHA", 10, Color.WHITE, true);', "drawer build tag")
rep('addDrawerItem(list, "i", t("About VARA", "درباره VARA"), "0.4.4 Alpha",', 'addDrawerItem(list, "i", t("About VARA", "درباره VARA"), "0.4.5 Alpha",', "drawer about version")
rep('about.addView(tv("0.4.4 Alpha • versionCode 404", 13, MUTED, false));', 'about.addView(tv("0.4.5 Alpha • versionCode 405", 13, MUTED, false));', "settings version")
rep('hero.addView(tv("0.4.4 Alpha • versionCode 404", 13, Color.rgb(220,236,239), false));', 'hero.addView(tv("0.4.5 Alpha • versionCode 405", 13, Color.rgb(220,236,239), false));', "about version")

java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
for old, new in [("versionCode 404", "versionCode 405"), ("versionName '0.4.4-alpha'", "versionName '0.4.5-alpha'")]:
    if g.count(old) != 1:
        raise SystemExit(f"gradle patch failed: {old}")
    g = g.replace(old, new, 1)
gradle.write_text(g, encoding="utf-8")

print("VARA 0.4.5 patch applied successfully")
