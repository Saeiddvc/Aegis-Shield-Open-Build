from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_043.py <android-project-root>")

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

rep(
    "import android.webkit.SslErrorHandler;\nimport android.webkit.WebResourceRequest;",
    "import android.webkit.CookieManager;\nimport android.webkit.SslErrorHandler;\nimport android.webkit.WebResourceRequest;",
    "cookie import",
)
rep(
    "import android.view.ViewGroup;\nimport android.webkit.CookieManager;",
    "import android.view.ViewGroup;\nimport android.view.WindowManager;\nimport android.webkit.CookieManager;",
    "window import",
)
rep(
    "    private boolean fa;\n    private String lastSecureUrl = \"https://www.google.com\";",
    "    private boolean fa;\n    private String currentPage = \"home\";\n    private String lastSecureUrl = \"https://www.google.com\";",
    "page state",
)
rep(
    "        v.setTypeface(Typeface.create(\"sans\", bold ? Typeface.BOLD : Typeface.NORMAL));",
    "        v.setTypeface(fa ? Typeface.create(\"sans\", bold ? Typeface.BOLD : Typeface.NORMAL) : Typeface.create(bold ? \"sans-serif-medium\" : \"sans-serif\", Typeface.NORMAL));",
    "typography",
)
rep(
    "    private LinearLayout basePage() {\n        root.removeAllViews();",
    "    private LinearLayout basePage() {\n        getWindow().clearFlags(WindowManager.LayoutParams.FLAG_SECURE);\n        root.removeAllViews();",
    "clear secure flag",
)
rep(
    "        nav.setBackground(rounded(Color.WHITE, 18));\n        nav.setElevation(dp(1));",
    "        nav.setBackgroundColor(Color.TRANSPARENT);\n        nav.setContentDescription(back ? t(\"Back\", \"بازگشت\") : t(\"Menu\", \"منو\"));",
    "minimal navigation icon",
)
rep(
    "    private void renderHome() {\n        basePage();",
    "    private void renderHome() {\n        currentPage = \"home\";\n        basePage();",
    "home state",
)
rep(
    "        report.setOnClickListener(v -> renderAudit());",
    "        report.setOnClickListener(v -> renderReport());",
    "report route",
)

report_method = r'''
    private void renderReport() {
        currentPage = "report";
        basePage(); addTopBar(t("Security Report", "گزارش امنیتی"), true);

        int apps = installedApps();
        int issues = auditIssueCount();
        LinearLayout status = card();
        status.setBackground(gradient(NAVY, NAVY_2, 24));
        status.addView(tv(issues == 0 ? t("Protection status: Good", "وضعیت محافظت: مناسب") : t("Protection needs attention", "محافظت نیاز به رسیدگی دارد"), 21, Color.WHITE, true));
        status.addView(tv(issues == 0 ? t("No risky device configuration was detected in the current audit.", "در ممیزی فعلی تنظیم پرریسکی در سطح دستگاه شناسایی نشد.") : t(issues + " device configuration issue(s) should be reviewed.", issues + " مورد در تنظیمات دستگاه نیاز به بررسی دارد."), 13, Color.rgb(220,236,239), false));
        content.addView(status);

        LinearLayout numbers = card();
        numbers.addView(tv(t("Device overview", "نمای کلی دستگاه"), 17, NAVY, true));
        LinearLayout metrics = new LinearLayout(this); metrics.setOrientation(LinearLayout.HORIZONTAL); metrics.setPadding(0, dp(14), 0, 0);
        metrics.addView(metric(String.valueOf(apps), t("Apps visible", "برنامه قابل مشاهده")), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        metrics.addView(metric(String.valueOf(issues), t("Audit issues", "مورد ممیزی")), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        metrics.addView(metric("HTTPS", t("Secure browser", "مرور امن")), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        numbers.addView(metrics); content.addView(numbers);

        LinearLayout last = card();
        last.addView(tv(t("Latest activity", "آخرین فعالیت"), 16, NAVY, true));
        last.addView(tv(prefs.getString("last_activity", t("No scan recorded yet", "هنوز اسکنی ثبت نشده است")), 13, TEXT, false));
        last.addView(tv(prefs.getString("last_activity_time", "—"), 12, MUTED, false));
        content.addView(last);

        Button audit = primary(t("Review Security Audit", "بررسی ممیزی امنیت"));
        LinearLayout.LayoutParams ap = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(52)); ap.setMargins(0, dp(8), 0, 0); content.addView(audit, ap);
        audit.setOnClickListener(v -> renderAudit());
    }

'''
rep(
    "    private LinearLayout metric(String value, String label) {",
    report_method + "    private LinearLayout metric(String value, String label) {",
    "security report page",
)
rep(
    "    private void renderAudit() {\n        basePage(); addTopBar",
    "    private void renderAudit() {\n        currentPage = \"audit\";\n        basePage(); addTopBar",
    "audit state",
)
rep(
    "    private void renderSafePay() {\n        basePage(); addTopBar",
    "    private void renderSafePay() {\n        currentPage = \"safepay\";\n        basePage(); addTopBar",
    "safepay state",
)
rep(
    "            if (u.getUserInfo() != null) return null;\n            if (host.matches(\"^[0-9a-fA-F:.]+$\")) return null;\n            return u.toString();",
    "            if (u.getUserInfo() != null) return null;\n            host = host.toLowerCase(Locale.ROOT);\n            if (\"localhost\".equals(host) || host.endsWith(\".local\")) return null;\n            if (host.matches(\"^[0-9a-fA-F:.]+$\")) return null;\n            if (u.getPort() != -1 && u.getPort() != 443) return null;\n            return u.toString();",
    "safepay destination hardening",
)
rep(
    "    private void renderBrowserStart() {\n        basePage(); addTopBar",
    "    private void renderBrowserStart() {\n        currentPage = \"browserStart\";\n        basePage(); addTopBar",
    "browser start state",
)
rep(
    "    private void openSecureBrowser(String initialUrl) {\n        root.removeAllViews();",
    "    private void openSecureBrowser(String initialUrl) {\n        currentPage = \"browser\";\n        getWindow().addFlags(WindowManager.LayoutParams.FLAG_SECURE);\n        root.removeAllViews();",
    "secure browser state",
)
rep(
    "        ws.setJavaScriptEnabled(true); ws.setDomStorageEnabled(true); ws.setAllowFileAccess(false); ws.setAllowContentAccess(false); ws.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW); ws.setSaveFormData(false); ws.setDatabaseEnabled(false);\n        web.clearCache(false);",
    "        ws.setJavaScriptEnabled(true); ws.setDomStorageEnabled(true); ws.setAllowFileAccess(false); ws.setAllowContentAccess(false); ws.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW); ws.setSaveFormData(false); ws.setDatabaseEnabled(false);\n        ws.setJavaScriptCanOpenWindowsAutomatically(false); ws.setSupportMultipleWindows(false); ws.setGeolocationEnabled(false); ws.setCacheMode(WebSettings.LOAD_NO_CACHE);\n        ws.setAllowFileAccessFromFileURLs(false); ws.setAllowUniversalAccessFromFileURLs(false);\n        if (android.os.Build.VERSION.SDK_INT >= 26) ws.setSafeBrowsingEnabled(true);\n        CookieManager.getInstance().setAcceptThirdPartyCookies(web, false);\n        web.clearHistory(); web.clearCache(false);",
    "webview hardening",
)
rep(
    "    private void renderSettings() {\n        basePage(); addTopBar",
    "    private void renderSettings() {\n        currentPage = \"settings\";\n        basePage(); addTopBar",
    "settings state",
)
rep(
    "about.addView(tv(\"0.4.2 Alpha • versionCode 402\", 13, MUTED, false));",
    "about.addView(tv(\"0.4.3 Alpha • versionCode 403\", 13, MUTED, false));",
    "settings version",
)

about_method = r'''
    private void renderAbout() {
        currentPage = "about";
        basePage(); addTopBar(t("About VARA", "درباره VARA"), true);
        LinearLayout hero = card(); hero.setBackground(gradient(NAVY, NAVY_2, 24));
        TextView mark = tv("V", 28, Color.WHITE, true); mark.setGravity(Gravity.CENTER); mark.setBackground(rounded(TEAL, 22));
        hero.addView(mark, new LinearLayout.LayoutParams(dp(56), dp(56)));
        hero.addView(tv("VARA Security for Android", 21, Color.WHITE, true));
        hero.addView(tv("0.4.3 Alpha • versionCode 403", 13, Color.rgb(220,236,239), false));
        content.addView(hero);
        LinearLayout model = card(); model.addView(tv(t("Security model", "مدل امنیتی"), 16, NAVY, true));
        model.addView(tv(t("Local-first device audit, HTTPS-only protected browsing, fail-closed TLS handling, and explicit user control for Android system changes.", "ممیزی محلی دستگاه، مرور محافظت‌شده فقط HTTPS، توقف اتصال در خطای TLS و کنترل صریح کاربر برای تغییرات سیستمی Android."), 13, MUTED, false));
        content.addView(model);
        LinearLayout build = card(); build.addView(tv(t("Build information", "اطلاعات ساخت"), 16, NAVY, true));
        build.addView(tv("Target SDK 35\nMinimum Android 8.0 (API 26)\nRelease channel: Alpha", 13, MUTED, false));
        content.addView(build);
    }

'''
rep(
    "    private LinearLayout settingRow(String title, String value, View.OnClickListener click) {",
    about_method + "    private LinearLayout settingRow(String title, String value, View.OnClickListener click) {",
    "about page",
)
rep(
    "        addDrawerItem(list, \"i\", t(\"About VARA\", \"درباره VARA\"), \"0.4.2 Alpha\", v -> { closeDrawer(); renderSettings(); });",
    "        addDrawerItem(list, \"i\", t(\"About VARA\", \"درباره VARA\"), \"0.4.3 Alpha\", v -> { closeDrawer(); renderAbout(); });",
    "drawer about",
)
rep(
    "    private void closeDrawer() { root.removeAllViews(); renderHome(); }",
    "    private void closeDrawer() { removeDrawer(); View shade = root.findViewWithTag(\"drawerShade\"); if (shade != null) root.removeView(shade); }",
    "drawer close behavior",
)
rep(
    "        final View shade = new View(this); shade.setBackgroundColor(0x66000000); shade.setOnClickListener(v -> { root.removeView(shade); removeDrawer(); });",
    "        final View shade = new View(this); shade.setTag(\"drawerShade\"); shade.setBackgroundColor(0x66000000); shade.setOnClickListener(v -> { root.removeView(shade); removeDrawer(); });",
    "drawer shade tag",
)
rep(
    "    @Override\n    public void onBackPressed() {\n        View d = root.findViewWithTag(\"drawer\");\n        if (d != null) { root.removeView(d); return; }\n        renderHome();\n    }",
    "    @Override\n    public void onBackPressed() {\n        View d = root.findViewWithTag(\"drawer\");\n        if (d != null) { View shade = root.findViewWithTag(\"drawerShade\"); if (shade != null) root.removeView(shade); root.removeView(d); return; }\n        if (\"home\".equals(currentPage)) { super.onBackPressed(); return; }\n        if (\"browser\".equals(currentPage)) { renderBrowserStart(); return; }\n        renderHome();\n    }",
    "android back behavior",
)

java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
for old, new in [("versionCode 402", "versionCode 403"), ("versionName '0.4.2-alpha'", "versionName '0.4.3-alpha'")]:
    if g.count(old) != 1:
        raise SystemExit(f"gradle patch failed: {old}")
    g = g.replace(old, new, 1)
gradle.write_text(g, encoding="utf-8")

print("VARA 0.4.3 patch applied successfully")
