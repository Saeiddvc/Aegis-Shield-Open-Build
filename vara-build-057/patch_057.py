from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_057.py <android-project-root>")

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

# Navigation: use a route-aware back policy instead of sending every page directly to Home.
rep(
    '        nav.setOnClickListener(v -> { if (back) renderHome(); else showDrawer(); });',
    '        nav.setOnClickListener(v -> { if (back) navigateBack(); else showDrawer(); });',
    "route-aware top navigation",
)

navigate_method = r'''
    private void navigateBack() {
        if ("language".equals(currentPage) || "about".equals(currentPage) || "compatibility".equals(currentPage)) {
            renderSettings();
            return;
        }
        if ("browser".equals(currentPage)) {
            renderBrowserStart();
            return;
        }
        if ("audit".equals(currentPage) || "appreview".equals(currentPage)) {
            renderActionCenter();
            return;
        }
        renderHome();
    }

'''
rep(
    '    private void renderHome() {',
    navigate_method + '    private void renderHome() {',
    "navigation helper",
)

# Remove the remaining oversized chevrons from feature cards, settings and drawer rows.
rep(
    '        TextView chevron = tv(fa ? "‹" : "›", 28, MUTED, false); chevron.setGravity(Gravity.CENTER);',
    '        TextView chevron = tv(fa ? "←" : "→", 18, MUTED, true); chevron.setGravity(Gravity.CENTER);',
    "feature card arrow",
)
rep(
    '        TextView c = tv(fa ? "‹" : "›", 26, MUTED, false); c.setGravity(Gravity.CENTER);',
    '        TextView c = tv(fa ? "←" : "→", 18, MUTED, true); c.setGravity(Gravity.CENTER);',
    "settings row arrow",
)
rep(
    'TextView arrow = tv(fa ? "‹" : "›", 22, MUTED, false); arrow.setGravity(Gravity.CENTER);',
    'TextView arrow = tv(fa ? "←" : "→", 18, MUTED, true); arrow.setGravity(Gravity.CENTER);',
    "drawer row arrow",
)

# WebView runtime compatibility helpers. SafePay/Secure Browser require a working system WebView provider.
compat_helpers = r'''
    private android.content.pm.PackageInfo currentWebViewPackage() {
        try { return WebView.getCurrentWebViewPackage(); }
        catch (Exception ignored) { return null; }
    }

    private boolean webViewRuntimeReady() {
        android.content.pm.PackageInfo p = currentWebViewPackage();
        return p != null && p.packageName != null && !p.packageName.trim().isEmpty();
    }

    private String webViewRuntimeLabel() {
        android.content.pm.PackageInfo p = currentWebViewPackage();
        if (p == null) return t("Unavailable", "در دسترس نیست");
        String version = p.versionName == null ? "?" : p.versionName;
        return p.packageName + " • " + version;
    }

'''
rep(
    '    private boolean isSecurityPatchCurrent() {',
    compat_helpers + '    private boolean isSecurityPatchCurrent() {',
    "webview compatibility helpers",
)

# Treat a missing WebView provider as an actionable compatibility/security finding.
rep(
    '        if (!isSecurityPatchCurrent()) n++;\n        return n;',
    '        if (!isSecurityPatchCurrent()) n++;\n        if (!webViewRuntimeReady()) n++;\n        return n;',
    "webview audit issue",
)

rep(
    '''        content.addView(auditRow(
                t("Android security patch", "وصله امنیتی Android"),
                patchCurrent ? t("Patch level " + patchLevel + " is within the 180-day review window", "سطح وصله " + patchLevel + " در بازه بررسی ۱۸۰ روزه است")
                        : t("Patch level " + patchLevel + " should be reviewed for a system update", "سطح وصله " + patchLevel + " برای به‌روزرسانی سیستم نیاز به بررسی دارد"),
                patchCurrent,
                () -> openSettings("android.settings.SYSTEM_UPDATE_SETTINGS")));

        LinearLayout summary = card();''',
    '''        content.addView(auditRow(
                t("Android security patch", "وصله امنیتی Android"),
                patchCurrent ? t("Patch level " + patchLevel + " is within the 180-day review window", "سطح وصله " + patchLevel + " در بازه بررسی ۱۸۰ روزه است")
                        : t("Patch level " + patchLevel + " should be reviewed for a system update", "سطح وصله " + patchLevel + " برای به‌روزرسانی سیستم نیاز به بررسی دارد"),
                patchCurrent,
                () -> openSettings("android.settings.SYSTEM_UPDATE_SETTINGS")));
        boolean webViewReady = webViewRuntimeReady();
        content.addView(auditRow(
                t("Secure WebView runtime", "موتور WebView امن"),
                webViewReady ? t("Available • " + webViewRuntimeLabel(), "در دسترس • " + webViewRuntimeLabel())
                        : t("No usable system WebView provider detected — SafePay cannot start safely", "موتور WebView قابل استفاده شناسایی نشد — SafePay نمی‌تواند با ایمنی اجرا شود"),
                webViewReady,
                () -> openSettings(Settings.ACTION_SETTINGS)));

        LinearLayout summary = card();''',
    "actionable webview audit row",
)

# Compatibility screen: expose actual runtime/API/WebView/security-patch posture instead of a generic claim.
rep(
    '        content.addView(settingRow(t("Privacy & diagnostics", "حریم خصوصی و عیب‌یابی"), t("Local-first", "اولویت پردازش محلی"), null));',
    '        content.addView(settingRow(t("Privacy & diagnostics", "حریم خصوصی و عیب‌یابی"), t("Local-first", "اولویت پردازش محلی"), null));\n        content.addView(settingRow(t("Device compatibility", "سازگاری دستگاه"), "Android " + android.os.Build.VERSION.RELEASE + " • API " + android.os.Build.VERSION.SDK_INT, v -> renderCompatibility()));',
    "settings compatibility route",
)

compat_page = r'''
    private void renderCompatibility() {
        currentPage = "compatibility";
        basePage(); addTopBar(t("Device compatibility", "سازگاری دستگاه"), true);

        boolean webReady = webViewRuntimeReady();
        boolean patchCurrent = isSecurityPatchCurrent();
        LinearLayout hero = card();
        hero.setBackground(gradient(webReady ? NAVY : WARN, webReady ? NAVY_2 : Color.rgb(157,104,24), 24));
        hero.addView(tv(webReady ? t("Protected browser runtime ready", "موتور مرورگر محافظت‌شده آماده است") : t("Protected browser runtime needs attention", "موتور مرورگر محافظت‌شده نیاز به رسیدگی دارد"), 20, Color.WHITE, true));
        hero.addView(tv(t("Detected Android " + android.os.Build.VERSION.RELEASE + " • API " + android.os.Build.VERSION.SDK_INT + ". Build contract: min API 26, target API 35.", "Android " + android.os.Build.VERSION.RELEASE + " • API " + android.os.Build.VERSION.SDK_INT + " شناسایی شد. قرارداد ساخت: حداقل API 26 و هدف API 35."), 13, Color.rgb(230,240,243), false));
        content.addView(hero);

        LinearLayout runtime = card();
        runtime.addView(tv(t("Android runtime", "نسخه Android"), 16, NAVY, true));
        runtime.addView(tv("Android " + android.os.Build.VERSION.RELEASE + " • API " + android.os.Build.VERSION.SDK_INT, 13, TEXT, false));
        runtime.addView(tv(t("VARA 0.5.7 requires Android 8.0 / API 26 or newer.", "VARA 0.5.7 به Android 8.0 / API 26 یا جدیدتر نیاز دارد."), 12, MUTED, false));
        content.addView(runtime);

        LinearLayout web = card();
        web.addView(tv(t("System WebView provider", "موتور WebView سیستم"), 16, NAVY, true));
        web.addView(tv(webViewRuntimeLabel(), 13, webReady ? GOOD : WARN, webReady));
        web.addView(tv(webReady ? t("Available for SafePay and Secure Browser initialization.", "برای راه‌اندازی SafePay و Secure Browser در دسترس است.") : t("SafePay and Secure Browser will fail closed until a WebView provider is available.", "تا زمان در دسترس بودن WebView، SafePay و Secure Browser به‌صورت امن اجرا را متوقف می‌کنند."), 12, MUTED, false));
        content.addView(web);

        LinearLayout patch = card();
        patch.addView(tv(t("Security patch", "وصله امنیتی"), 16, NAVY, true));
        patch.addView(tv(securityPatchLabel(), 13, patchCurrent ? GOOD : WARN, true));
        patch.addView(tv(patchCurrent ? t("Within VARA's 180-day review window.", "در بازه بررسی ۱۸۰ روزه VARA است.") : t("Review Android system updates before sensitive transactions.", "پیش از تراکنش‌های حساس، به‌روزرسانی سیستم Android را بررسی کنید."), 12, MUTED, false));
        content.addView(patch);

        Button recheck = secondary(t("Recheck compatibility", "بررسی مجدد سازگاری"));
        LinearLayout.LayoutParams rp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(48)); rp.setMargins(0, dp(8), 0, 0); content.addView(recheck, rp);
        recheck.setOnClickListener(v -> renderCompatibility());
    }

'''
rep(
    '    private void renderAbout() {',
    compat_page + '    private void renderAbout() {',
    "compatibility page",
)

# Add compatibility to the drawer and selected-state logic.
rep(
    '        addDrawerItem(list, "⚙", t("Settings", "تنظیمات"), t("Language, privacy and updates", "زبان، حریم خصوصی و به‌روزرسانی"), v -> { closeDrawer(); renderSettings(); });',
    '        addDrawerItem(list, "◇", t("Device compatibility", "سازگاری دستگاه"), t("Android, WebView and patch posture", "وضعیت Android، WebView و وصله امنیتی"), v -> { closeDrawer(); renderCompatibility(); });\n        addDrawerItem(list, "⚙", t("Settings", "تنظیمات"), t("Language, privacy and updates", "زبان، حریم خصوصی و به‌روزرسانی"), v -> { closeDrawer(); renderSettings(); });',
    "drawer compatibility route",
)
rep(
    '        if ("settings".equals(currentPage) && title.equals(t("Settings", "تنظیمات"))) return true;',
    '        if ("compatibility".equals(currentPage) && title.equals(t("Device compatibility", "سازگاری دستگاه"))) return true;\n        if ("settings".equals(currentPage) && title.equals(t("Settings", "تنظیمات"))) return true;',
    "drawer compatibility active state",
)

# SafePay/Secure Browser: do not navigate until Android Safe Browsing initialization succeeds.
rep(
    '''        if (android.os.Build.VERSION.SDK_INT >= 26) WebView.startSafeBrowsing(this, value -> {
            if (!value) Toast.makeText(MainActivity.this, t("Safe Browsing service unavailable", "سرویس Safe Browsing در دسترس نیست"), Toast.LENGTH_SHORT).show();
        });
        page.addView(web, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1));
        root.addView(page, new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        String safe = normalizeHttps(initialUrl); web.loadUrl(safe == null ? "https://www.google.com" : safe);''',
    '''        page.addView(web, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1));
        root.addView(page, new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        String safe = normalizeHttps(initialUrl);
        final String launchUrl = safe == null ? "https://www.google.com" : safe;
        if (!webViewRuntimeReady()) {
            String event = t("Protected browser blocked: system WebView unavailable", "مرورگر محافظت‌شده مسدود شد: WebView سیستم در دسترس نیست");
            recordActivity(event);
            try { web.destroy(); } catch (Exception ignored) {}
            Toast.makeText(MainActivity.this, t("Secure WebView runtime unavailable", "موتور WebView امن در دسترس نیست"), Toast.LENGTH_LONG).show();
            renderBrowserStart();
            return;
        }
        WebView.startSafeBrowsing(this, value -> {
            if (!value) {
                String event = t("Protected browser blocked: Safe Browsing initialization failed", "مرورگر محافظت‌شده مسدود شد: راه‌اندازی Safe Browsing ناموفق بود");
                recordActivity(event);
                try { web.stopLoading(); web.destroy(); } catch (Exception ignored) {}
                Toast.makeText(MainActivity.this, t("Safe Browsing unavailable — session closed", "Safe Browsing در دسترس نیست — نشست بسته شد"), Toast.LENGTH_LONG).show();
                renderBrowserStart();
                return;
            }
            web.loadUrl(launchUrl);
        });''',
    "fail-closed safe browsing initialization",
)

# Android back button follows the same hierarchy as the top navigation.
rep(
    '''        if ("home".equals(currentPage)) { super.onBackPressed(); return; }
        if ("browser".equals(currentPage)) { renderBrowserStart(); return; }
        renderHome();''',
    '''        if ("home".equals(currentPage)) { super.onBackPressed(); return; }
        navigateBack();''',
    "android back navigation hierarchy",
)

# Version metadata.
s = s.replace('0.5.6 ALPHA', '0.5.7 ALPHA')
s = s.replace('0.5.6 Alpha • versionCode 506', '0.5.7 Alpha • versionCode 507')
s = s.replace('0.5.6 Alpha', '0.5.7 Alpha')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+506\b', 'versionCode 507', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.5\.6-alpha['\"]", "versionName '0.5.7-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'private void navigateBack()',
    'currentPage = "compatibility"',
    'webViewRuntimeReady()',
    'WebView.getCurrentWebViewPackage()',
    'Safe Browsing unavailable — session closed',
    'web.loadUrl(launchUrl)',
    'Build contract: min API 26, target API 35',
    '0.5.7 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.5.7 navigation, compatibility and fail-closed Safe Browsing patch applied")
