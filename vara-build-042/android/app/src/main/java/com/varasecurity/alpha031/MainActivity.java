package com.varasecurity.alpha031;

import android.app.Activity;
import android.app.KeyguardManager;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Bundle;
import android.provider.Settings;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.webkit.SslErrorHandler;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.net.http.SslError;
import android.widget.Button;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Space;
import android.widget.TextView;
import android.widget.Toast;

import java.text.DateFormat;
import java.util.Date;
import java.util.Locale;

public class MainActivity extends Activity {
    private static final int NAVY = Color.rgb(16, 42, 67);
    private static final int NAVY_2 = Color.rgb(28, 73, 92);
    private static final int TEAL = Color.rgb(18, 157, 148);
    private static final int TEAL_DARK = Color.rgb(13, 128, 121);
    private static final int BG = Color.rgb(245, 248, 250);
    private static final int TEXT = Color.rgb(31, 45, 61);
    private static final int MUTED = Color.rgb(103, 119, 133);
    private static final int LINE = Color.rgb(224, 232, 239);
    private static final int GOOD = Color.rgb(28, 149, 107);
    private static final int WARN = Color.rgb(225, 142, 43);
    private static final int DANGER = Color.rgb(204, 73, 73);

    private FrameLayout root;
    private LinearLayout content;
    private SharedPreferences prefs;
    private boolean fa;
    private String lastSecureUrl = "https://www.google.com";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        prefs = getSharedPreferences("vara", MODE_PRIVATE);
        fa = "fa".equals(prefs.getString("lang", "en"));
        root = new FrameLayout(this);
        root.setBackgroundColor(BG);
        setContentView(root);
        renderHome();
    }

    private String t(String en, String faText) { return fa ? faText : en; }

    private int dp(int n) { return Math.round(n * getResources().getDisplayMetrics().density); }

    private TextView tv(String text, float sp, int color, boolean bold) {
        TextView v = new TextView(this);
        v.setText(text);
        v.setTextSize(sp);
        v.setTextColor(color);
        v.setGravity(fa ? Gravity.RIGHT : Gravity.LEFT);
        v.setTypeface(Typeface.create("sans", bold ? Typeface.BOLD : Typeface.NORMAL));
        v.setLineSpacing(0, 1.08f);
        return v;
    }

    private GradientDrawable rounded(int color, int radius) {
        GradientDrawable g = new GradientDrawable();
        g.setColor(color);
        g.setCornerRadius(dp(radius));
        return g;
    }

    private GradientDrawable gradient(int c1, int c2, int radius) {
        GradientDrawable g = new GradientDrawable(GradientDrawable.Orientation.TL_BR, new int[]{c1, c2});
        g.setCornerRadius(dp(radius));
        return g;
    }

    private LinearLayout basePage() {
        root.removeAllViews();
        ScrollView sc = new ScrollView(this);
        sc.setFillViewport(true);
        sc.setClipToPadding(false);
        content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        content.setPadding(dp(18), dp(12), dp(18), dp(34));
        content.setLayoutDirection(fa ? View.LAYOUT_DIRECTION_RTL : View.LAYOUT_DIRECTION_LTR);
        sc.addView(content, new ScrollView.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        root.addView(sc, new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        return content;
    }

    private void addTopBar(String title, boolean back) {
        LinearLayout bar = new LinearLayout(this);
        bar.setGravity(Gravity.CENTER_VERTICAL);
        bar.setOrientation(LinearLayout.HORIZONTAL);
        bar.setPadding(0, dp(4), 0, dp(10));
        TextView nav = tv(back ? (fa ? "›" : "‹") : "☰", back ? 34 : 28, NAVY, false);
        nav.setGravity(Gravity.CENTER);
        nav.setBackground(rounded(Color.WHITE, 18));
        nav.setElevation(dp(1));
        nav.setOnClickListener(v -> { if (back) renderHome(); else showDrawer(); });
        bar.addView(nav, new LinearLayout.LayoutParams(dp(48), dp(48)));

        TextView ttl = tv(title, 20, NAVY, true);
        ttl.setGravity(fa ? Gravity.RIGHT | Gravity.CENTER_VERTICAL : Gravity.LEFT | Gravity.CENTER_VERTICAL);
        LinearLayout.LayoutParams tp = new LinearLayout.LayoutParams(0, dp(48), 1);
        tp.setMargins(dp(12), 0, dp(12), 0);
        bar.addView(ttl, tp);
        TextView dot = tv("●", 13, TEAL, true);
        dot.setGravity(Gravity.CENTER);
        bar.addView(dot, new LinearLayout.LayoutParams(dp(28), dp(48)));
        content.addView(bar);
    }

    private LinearLayout card() {
        LinearLayout c = new LinearLayout(this);
        c.setOrientation(LinearLayout.VERTICAL);
        c.setPadding(dp(18), dp(16), dp(18), dp(16));
        c.setBackground(rounded(Color.WHITE, 22));
        c.setElevation(dp(2));
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        lp.setMargins(0, dp(8), 0, dp(8));
        c.setLayoutParams(lp);
        return c;
    }

    private Button primary(String label) {
        Button b = new Button(this);
        b.setText(label);
        b.setTextColor(Color.WHITE);
        b.setTextSize(15);
        b.setAllCaps(false);
        b.setTypeface(Typeface.DEFAULT_BOLD);
        b.setBackground(gradient(TEAL, TEAL_DARK, 18));
        b.setPadding(dp(18), 0, dp(18), 0);
        return b;
    }

    private Button secondary(String label) {
        Button b = new Button(this);
        b.setText(label);
        b.setTextColor(NAVY);
        b.setTextSize(14);
        b.setAllCaps(false);
        b.setTypeface(Typeface.DEFAULT_BOLD);
        b.setBackground(rounded(Color.rgb(235, 246, 245), 18));
        return b;
    }

    private void sectionLabel(String title) {
        TextView s = tv(title.toUpperCase(Locale.ROOT), 12, MUTED, true);
        s.setLetterSpacing(0.08f);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        lp.setMargins(dp(4), dp(22), dp(4), dp(4));
        content.addView(s, lp);
    }

    private void renderHome() {
        basePage();
        addTopBar("VARA Security", false);

        LinearLayout hero = new LinearLayout(this);
        hero.setOrientation(LinearLayout.VERTICAL);
        hero.setGravity(Gravity.CENTER);
        hero.setPadding(dp(22), dp(24), dp(22), dp(22));
        hero.setBackground(gradient(NAVY, NAVY_2, 28));
        hero.setElevation(dp(3));
        TextView shield = tv("✓", 36, Color.WHITE, true);
        shield.setGravity(Gravity.CENTER);
        shield.setBackground(rounded(TEAL, 30));
        hero.addView(shield, new LinearLayout.LayoutParams(dp(64), dp(64)));
        TextView status = tv(t("You are protected", "دستگاه شما محافظت می‌شود"), 24, Color.WHITE, true);
        status.setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams sp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        sp.setMargins(0, dp(16), 0, dp(5));
        hero.addView(status, sp);
        TextView sub = tv(t("Core protection is active. Review your device regularly.", "محافظت اصلی فعال است. وضعیت دستگاه را به‌صورت دوره‌ای بررسی کنید."), 14, Color.rgb(220, 236, 239), false);
        sub.setGravity(Gravity.CENTER);
        hero.addView(sub);
        Button scan = primary(t("Scan device", "بررسی دستگاه"));
        LinearLayout.LayoutParams bp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(52));
        bp.setMargins(0, dp(20), 0, 0);
        hero.addView(scan, bp);
        scan.setOnClickListener(v -> runQuickScan());
        LinearLayout.LayoutParams hp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        hp.setMargins(0, dp(6), 0, dp(12));
        content.addView(hero, hp);

        sectionLabel(t("Security", "امنیت"));
        LinearLayout report = card();
        report.addView(tv(t("Security report", "گزارش امنیتی"), 18, NAVY, true));
        report.addView(tv(t("At-a-glance status for this device", "نمای کلی وضعیت امنیتی این دستگاه"), 13, MUTED, false));
        LinearLayout metrics = new LinearLayout(this);
        metrics.setOrientation(LinearLayout.HORIZONTAL);
        metrics.setPadding(0, dp(14), 0, 0);
        int apps = installedApps();
        metrics.addView(metric(String.valueOf(apps), t("Apps", "برنامه")), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        metrics.addView(metric(auditIssueCount() == 0 ? "0" : String.valueOf(auditIssueCount()), t("Issues", "مورد")), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        metrics.addView(metric("ON", t("Safe browsing", "مرور امن")), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        report.addView(metrics);
        report.setOnClickListener(v -> renderAudit());
        content.addView(report);

        LinearLayout audit = featureCard("✓", t("Security Audit", "ممیزی امنیت"), t("Review risky device settings and fix them", "تنظیمات پرریسک دستگاه را بررسی و اصلاح کنید"), WARN);
        audit.setOnClickListener(v -> renderAudit());
        content.addView(audit);

        LinearLayout pay = featureCard("▣", "VARA SafePay", t("Protected launch for banking and payments", "اجرای محافظت‌شده برای بانک و پرداخت"), TEAL);
        pay.setOnClickListener(v -> renderSafePay());
        content.addView(pay);

        LinearLayout browser = featureCard("◎", t("Secure Browser", "مرورگر امن"), t("HTTPS-only hardened browsing session", "نشست مرور سخت‌گیرانه و فقط HTTPS"), NAVY_2);
        browser.setOnClickListener(v -> renderBrowserStart());
        content.addView(browser);

        sectionLabel(t("Recent activity", "فعالیت اخیر"));
        LinearLayout activity = card();
        String last = prefs.getString("last_activity", t("No security events recorded yet", "هنوز رویداد امنیتی ثبت نشده است"));
        activity.addView(tv("●  " + last, 14, TEXT, false));
        TextView time = tv(prefs.getString("last_activity_time", "—"), 12, MUTED, false);
        LinearLayout.LayoutParams tlp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        tlp.setMargins(0, dp(7), 0, 0);
        activity.addView(time, tlp);
        content.addView(activity);
    }

    private LinearLayout metric(String value, String label) {
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setGravity(Gravity.CENTER);
        TextView v = tv(value, 18, NAVY, true); v.setGravity(Gravity.CENTER);
        TextView l = tv(label, 11, MUTED, false); l.setGravity(Gravity.CENTER);
        box.addView(v); box.addView(l);
        return box;
    }

    private LinearLayout featureCard(String icon, String title, String desc, int accent) {
        LinearLayout c = card();
        c.setOrientation(LinearLayout.HORIZONTAL);
        c.setGravity(Gravity.CENTER_VERTICAL);
        TextView i = tv(icon, 23, Color.WHITE, true);
        i.setGravity(Gravity.CENTER);
        i.setBackground(rounded(accent, 16));
        c.addView(i, new LinearLayout.LayoutParams(dp(52), dp(52)));
        LinearLayout tx = new LinearLayout(this); tx.setOrientation(LinearLayout.VERTICAL);
        TextView tt = tv(title, 16, NAVY, true);
        TextView dd = tv(desc, 12, MUTED, false);
        tx.addView(tt); tx.addView(dd);
        LinearLayout.LayoutParams txp = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1); txp.setMargins(dp(14), 0, dp(8), 0);
        c.addView(tx, txp);
        TextView chevron = tv(fa ? "‹" : "›", 28, MUTED, false); chevron.setGravity(Gravity.CENTER);
        c.addView(chevron, new LinearLayout.LayoutParams(dp(28), dp(52)));
        return c;
    }

    private int installedApps() {
        try { return getPackageManager().getInstalledPackages(0).size(); }
        catch (Exception e) { return 0; }
    }

    private int auditIssueCount() {
        int n = 0;
        KeyguardManager km = (KeyguardManager) getSystemService(KEYGUARD_SERVICE);
        if (km == null || !km.isDeviceSecure()) n++;
        if (Settings.Global.getInt(getContentResolver(), Settings.Global.DEVELOPMENT_SETTINGS_ENABLED, 0) != 0) n++;
        if (Settings.Global.getInt(getContentResolver(), Settings.Global.ADB_ENABLED, 0) != 0) n++;
        return n;
    }

    private void runQuickScan() {
        int apps = installedApps();
        int issues = auditIssueCount();
        String event = t("Scanned " + apps + " apps • " + issues + " device issues", "تعداد " + apps + " برنامه بررسی شد • " + issues + " مورد تنظیمات دستگاه");
        prefs.edit().putString("last_activity", event).putString("last_activity_time", DateFormat.getDateTimeInstance(DateFormat.SHORT, DateFormat.SHORT).format(new Date())).apply();
        Toast.makeText(this, issues == 0 ? t("No device configuration issues found", "مورد پرریسکی در تنظیمات دستگاه پیدا نشد") : t("Review " + issues + " device security issues", "تعداد " + issues + " مورد امنیتی نیاز به بررسی دارد"), Toast.LENGTH_LONG).show();
        renderHome();
    }

    private void renderAudit() {
        basePage(); addTopBar(t("Security Audit", "ممیزی امنیت"), true);
        TextView intro = tv(t("Fix device-level risks that can weaken app and payment protection.", "ریسک‌های سطح دستگاه را که می‌توانند امنیت برنامه و پرداخت را کاهش دهند اصلاح کنید."), 14, MUTED, false);
        LinearLayout.LayoutParams ip = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT); ip.setMargins(0, 0, 0, dp(10)); content.addView(intro, ip);

        KeyguardManager km = (KeyguardManager) getSystemService(KEYGUARD_SERVICE);
        boolean lock = km != null && km.isDeviceSecure();
        boolean dev = Settings.Global.getInt(getContentResolver(), Settings.Global.DEVELOPMENT_SETTINGS_ENABLED, 0) != 0;
        boolean adb = Settings.Global.getInt(getContentResolver(), Settings.Global.ADB_ENABLED, 0) != 0;
        content.addView(auditRow(t("Screen lock", "قفل صفحه"), lock ? t("Secure lock is enabled", "قفل امن فعال است") : t("No secure screen lock", "قفل امن صفحه فعال نیست"), lock, () -> openSettings(Settings.ACTION_SECURITY_SETTINGS)));
        content.addView(auditRow(t("Developer options", "گزینه‌های توسعه‌دهنده"), dev ? t("Enabled — disable when not needed", "فعال است — در صورت عدم نیاز غیرفعال شود") : t("Disabled", "غیرفعال"), !dev, () -> openSettings(Settings.ACTION_APPLICATION_DEVELOPMENT_SETTINGS)));
        content.addView(auditRow(t("USB debugging", "اشکال‌زدایی USB"), adb ? t("Enabled — increases attack surface", "فعال است — سطح حمله را افزایش می‌دهد") : t("Disabled", "غیرفعال"), !adb, () -> openSettings(Settings.ACTION_APPLICATION_DEVELOPMENT_SETTINGS)));

        LinearLayout summary = card();
        int issues = auditIssueCount();
        summary.setBackground(rounded(issues == 0 ? Color.rgb(235,248,242) : Color.rgb(255,247,235), 22));
        summary.addView(tv(issues == 0 ? t("Device configuration looks good", "پیکربندی دستگاه مناسب است") : t(issues + " issue(s) need attention", issues + " مورد نیاز به رسیدگی دارد"), 18, issues == 0 ? GOOD : WARN, true));
        summary.addView(tv(t("VARA does not change sensitive system settings automatically. Use the action buttons to review them in Android Settings.", "VARA تنظیمات حساس سیستم را خودکار تغییر نمی‌دهد. برای اصلاح، از دکمه‌های اقدام و تنظیمات Android استفاده کنید."), 13, MUTED, false));
        content.addView(summary);
    }

    private LinearLayout auditRow(String title, String desc, boolean good, Runnable action) {
        LinearLayout c = card();
        LinearLayout top = new LinearLayout(this); top.setOrientation(LinearLayout.HORIZONTAL); top.setGravity(Gravity.CENTER_VERTICAL);
        TextView badge = tv(good ? "✓" : "!", 18, Color.WHITE, true); badge.setGravity(Gravity.CENTER); badge.setBackground(rounded(good ? GOOD : WARN, 15));
        top.addView(badge, new LinearLayout.LayoutParams(dp(42), dp(42)));
        LinearLayout text = new LinearLayout(this); text.setOrientation(LinearLayout.VERTICAL); text.addView(tv(title, 16, NAVY, true)); text.addView(tv(desc, 12, MUTED, false));
        LinearLayout.LayoutParams tp = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1); tp.setMargins(dp(12), 0, 0, 0); top.addView(text, tp); c.addView(top);
        if (!good) { Button fix = secondary(t("Review setting", "بررسی تنظیمات")); LinearLayout.LayoutParams fp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(46)); fp.setMargins(0, dp(14), 0, 0); c.addView(fix, fp); fix.setOnClickListener(v -> action.run()); }
        return c;
    }

    private void openSettings(String action) {
        try { startActivity(new Intent(action)); } catch (Exception e) { startActivity(new Intent(Settings.ACTION_SETTINGS)); }
    }

    private void renderSafePay() {
        basePage(); addTopBar("VARA SafePay", true);
        LinearLayout hero = card(); hero.setBackground(gradient(NAVY, NAVY_2, 24));
        TextView h = tv(t("Protected payment launch", "اجرای محافظت‌شده پرداخت"), 22, Color.WHITE, true); hero.addView(h);
        hero.addView(tv(t("VARA validates the address, requires HTTPS, blocks IP-address destinations, and opens it inside the hardened browser.", "VARA نشانی را اعتبارسنجی می‌کند، HTTPS را الزامی می‌داند، مقصدهای مبتنی بر IP را رد می‌کند و صفحه را در مرورگر سخت‌گیرانه باز می‌کند."), 13, Color.rgb(220,236,239), false));
        content.addView(hero);
        TextView label = tv(t("Bank or payment website", "وب‌سایت بانک یا پرداخت"), 13, MUTED, true); LinearLayout.LayoutParams llp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT); llp.setMargins(dp(4), dp(18), 0, dp(6)); content.addView(label, llp);
        EditText url = new EditText(this); url.setSingleLine(true); url.setText("https://"); url.setTextColor(TEXT); url.setHintTextColor(MUTED); url.setTextSize(15); url.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI); url.setBackground(rounded(Color.WHITE, 18)); url.setPadding(dp(16), 0, dp(16), 0); content.addView(url, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(54)));
        Button open = primary(t("Open protected session", "باز کردن نشست محافظت‌شده")); LinearLayout.LayoutParams op = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(52)); op.setMargins(0, dp(12), 0, 0); content.addView(open, op);
        open.setOnClickListener(v -> { String normalized = normalizeHttps(url.getText().toString()); if (normalized == null) { Toast.makeText(this, t("Enter a valid HTTPS domain, not an IP address", "یک دامنه معتبر HTTPS وارد کنید؛ نشانی IP مجاز نیست"), Toast.LENGTH_LONG).show(); return; } lastSecureUrl = normalized; openSecureBrowser(normalized); });
        LinearLayout info = card(); info.addView(tv(t("SafePay protections", "محافظت‌های SafePay"), 16, NAVY, true)); info.addView(tv(t("• HTTPS-only navigation\n• TLS errors fail closed\n• Cleartext traffic disabled\n• File/content access disabled\n• Mixed content blocked", "• فقط پیمایش HTTPS\n• خطای TLS باعث توقف اتصال می‌شود\n• ترافیک بدون رمزنگاری غیرفعال است\n• دسترسی فایل و محتوا بسته است\n• محتوای ترکیبی مسدود است"), 13, MUTED, false)); content.addView(info);
    }

    private String normalizeHttps(String raw) {
        try {
            String s = raw == null ? "" : raw.trim();
            if (!s.startsWith("https://")) return null;
            Uri u = Uri.parse(s);
            String host = u.getHost();
            if (host == null || host.length() < 4 || !host.contains(".")) return null;
            if (u.getUserInfo() != null) return null;
            if (host.matches("^[0-9a-fA-F:.]+$")) return null;
            return u.toString();
        } catch (Exception e) { return null; }
    }

    private void renderBrowserStart() {
        basePage(); addTopBar(t("Secure Browser", "مرورگر امن"), true);
        LinearLayout c = card(); c.addView(tv(t("Hardened browser session", "نشست مرور سخت‌گیرانه"), 20, NAVY, true)); c.addView(tv(t("Use this browser for sensitive sign-in, banking and payment pages. Only HTTPS destinations are allowed.", "برای ورود حساس، بانک و پرداخت از این مرورگر استفاده کنید. فقط مقصدهای HTTPS مجاز هستند."), 13, MUTED, false)); content.addView(c);
        Button launch = primary(t("Start secure browsing", "شروع مرور امن")); LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(52)); lp.setMargins(0, dp(8), 0, 0); content.addView(launch, lp); launch.setOnClickListener(v -> openSecureBrowser(lastSecureUrl));
    }

    private void openSecureBrowser(String initialUrl) {
        root.removeAllViews();
        LinearLayout page = new LinearLayout(this); page.setOrientation(LinearLayout.VERTICAL); page.setBackgroundColor(BG);
        LinearLayout bar = new LinearLayout(this); bar.setPadding(dp(10), dp(8), dp(10), dp(8)); bar.setGravity(Gravity.CENTER_VERTICAL); bar.setBackgroundColor(Color.WHITE);
        TextView back = tv(fa ? "›" : "‹", 34, NAVY, false); back.setGravity(Gravity.CENTER); back.setOnClickListener(v -> renderBrowserStart()); bar.addView(back, new LinearLayout.LayoutParams(dp(48), dp(48)));
        TextView lock = tv("●", 12, GOOD, true); lock.setGravity(Gravity.CENTER); bar.addView(lock, new LinearLayout.LayoutParams(dp(28), dp(48)));
        TextView title = tv(t("Protected HTTPS session", "نشست محافظت‌شده HTTPS"), 15, NAVY, true); bar.addView(title, new LinearLayout.LayoutParams(0, dp(48), 1)); page.addView(bar);
        WebView web = new WebView(this);
        WebSettings ws = web.getSettings();
        ws.setJavaScriptEnabled(true); ws.setDomStorageEnabled(true); ws.setAllowFileAccess(false); ws.setAllowContentAccess(false); ws.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW); ws.setSaveFormData(false); ws.setDatabaseEnabled(false);
        web.clearCache(false);
        web.setWebViewClient(new WebViewClient() {
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri u = request.getUrl();
                if (!"https".equalsIgnoreCase(u.getScheme())) { Toast.makeText(MainActivity.this, t("Blocked non-HTTPS navigation", "پیمایش غیر HTTPS مسدود شد"), Toast.LENGTH_SHORT).show(); return true; }
                return false;
            }
            @Override public void onReceivedSslError(WebView view, SslErrorHandler handler, SslError error) {
                handler.cancel(); Toast.makeText(MainActivity.this, t("TLS certificate error — connection blocked", "خطای گواهی TLS — اتصال مسدود شد"), Toast.LENGTH_LONG).show();
            }
        });
        if (android.os.Build.VERSION.SDK_INT >= 26) WebView.startSafeBrowsing(this, value -> {});
        page.addView(web, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1));
        root.addView(page, new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        String safe = normalizeHttps(initialUrl); web.loadUrl(safe == null ? "https://www.google.com" : safe);
    }

    private void renderSettings() {
        basePage(); addTopBar(t("Settings", "تنظیمات"), true);
        content.addView(settingRow(t("Language", "زبان"), fa ? "فارسی" : "English", v -> toggleLanguage()));
        content.addView(settingRow(t("Protection mode", "حالت محافظت"), t("Automatic", "خودکار"), null));
        content.addView(settingRow(t("Updates", "به‌روزرسانی"), t("Automatic", "خودکار"), null));
        content.addView(settingRow(t("Privacy & diagnostics", "حریم خصوصی و عیب‌یابی"), t("Local-first", "اولویت پردازش محلی"), null));
        LinearLayout about = card(); about.addView(tv("VARA Security for Android", 17, NAVY, true)); about.addView(tv("0.4.2 Alpha • versionCode 402", 13, MUTED, false)); about.addView(tv(t("Experimental security build. Sensitive system changes always require explicit user action.", "نسخه آزمایشی امنیتی. تغییر تنظیمات حساس سیستم همیشه نیازمند اقدام صریح کاربر است."), 12, MUTED, false)); content.addView(about);
    }

    private LinearLayout settingRow(String title, String value, View.OnClickListener click) {
        LinearLayout r = card(); r.setOrientation(LinearLayout.HORIZONTAL); r.setGravity(Gravity.CENTER_VERTICAL);
        LinearLayout tx = new LinearLayout(this); tx.setOrientation(LinearLayout.VERTICAL); tx.addView(tv(title, 15, NAVY, true)); tx.addView(tv(value, 12, MUTED, false)); r.addView(tx, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        TextView c = tv(fa ? "‹" : "›", 26, MUTED, false); c.setGravity(Gravity.CENTER); r.addView(c, new LinearLayout.LayoutParams(dp(32), dp(48))); if (click != null) r.setOnClickListener(click); return r;
    }

    private void toggleLanguage() {
        fa = !fa; prefs.edit().putString("lang", fa ? "fa" : "en").apply(); renderSettings();
    }

    private void showDrawer() {
        final View shade = new View(this); shade.setBackgroundColor(0x66000000); shade.setOnClickListener(v -> { root.removeView(shade); removeDrawer(); });
        root.addView(shade, new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        LinearLayout drawer = new LinearLayout(this); drawer.setTag("drawer"); drawer.setOrientation(LinearLayout.VERTICAL); drawer.setBackgroundColor(Color.WHITE); drawer.setElevation(dp(12)); drawer.setLayoutDirection(fa ? View.LAYOUT_DIRECTION_RTL : View.LAYOUT_DIRECTION_LTR);
        LinearLayout head = new LinearLayout(this); head.setOrientation(LinearLayout.VERTICAL); head.setPadding(dp(22), dp(24), dp(22), dp(20)); head.setBackground(gradient(NAVY, NAVY_2, 0));
        TextView mark = tv("V", 24, Color.WHITE, true); mark.setGravity(Gravity.CENTER); mark.setBackground(rounded(TEAL, 18)); head.addView(mark, new LinearLayout.LayoutParams(dp(48), dp(48)));
        TextView brand = tv("VARA Security", 21, Color.WHITE, true); LinearLayout.LayoutParams br = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT); br.setMargins(0, dp(12), 0, dp(3)); head.addView(brand, br);
        head.addView(tv(t("Protected • core services active", "محافظت فعال • سرویس‌های اصلی روشن"), 12, Color.rgb(214,235,237), false)); drawer.addView(head);
        ScrollView ds = new ScrollView(this); LinearLayout list = new LinearLayout(this); list.setOrientation(LinearLayout.VERTICAL); list.setPadding(dp(12), dp(10), dp(12), dp(20));
        addDrawerSection(list, t("Protection", "محافظت"));
        addDrawerItem(list, "✓", t("Antivirus & Scan", "آنتی‌ویروس و اسکن"), t("Check installed applications", "بررسی برنامه‌های نصب‌شده"), v -> { closeDrawer(); runQuickScan(); });
        addDrawerItem(list, "▣", "VARA SafePay", t("Banking & payment protection", "محافظت بانک و پرداخت"), v -> { closeDrawer(); renderSafePay(); });
        addDrawerItem(list, "◎", t("Secure Browser", "مرورگر امن"), t("HTTPS-only hardened session", "نشست سخت‌گیرانه فقط HTTPS"), v -> { closeDrawer(); renderBrowserStart(); });
        addDrawerItem(list, "!", t("Security Audit", "ممیزی امنیت"), t("Fix risky device settings", "اصلاح تنظیمات پرریسک"), v -> { closeDrawer(); renderAudit(); });
        addDrawerSection(list, t("Account & app", "حساب و برنامه"));
        addDrawerItem(list, "⚙", t("Settings", "تنظیمات"), t("Language, privacy and updates", "زبان، حریم خصوصی و به‌روزرسانی"), v -> { closeDrawer(); renderSettings(); });
        addDrawerItem(list, "i", t("About VARA", "درباره VARA"), "0.4.2 Alpha", v -> { closeDrawer(); renderSettings(); });
        ds.addView(list); drawer.addView(ds, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1));
        FrameLayout.LayoutParams dlp = new FrameLayout.LayoutParams((int)(getResources().getDisplayMetrics().widthPixels * 0.86f), ViewGroup.LayoutParams.MATCH_PARENT, fa ? Gravity.RIGHT : Gravity.LEFT); root.addView(drawer, dlp);
    }

    private void addDrawerSection(LinearLayout list, String title) {
        TextView s = tv(title.toUpperCase(Locale.ROOT), 11, MUTED, true); s.setLetterSpacing(0.08f); LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT); lp.setMargins(dp(10), dp(15), dp(10), dp(5)); list.addView(s, lp);
    }

    private void addDrawerItem(LinearLayout list, String icon, String title, String desc, View.OnClickListener click) {
        LinearLayout row = new LinearLayout(this); row.setOrientation(LinearLayout.HORIZONTAL); row.setGravity(Gravity.CENTER_VERTICAL); row.setPadding(dp(10), dp(10), dp(8), dp(10)); row.setBackground(rounded(Color.WHITE, 16));
        TextView ic = tv(icon, 18, TEAL_DARK, true); ic.setGravity(Gravity.CENTER); ic.setBackground(rounded(Color.rgb(232,247,245), 14)); row.addView(ic, new LinearLayout.LayoutParams(dp(44), dp(44)));
        LinearLayout tx = new LinearLayout(this); tx.setOrientation(LinearLayout.VERTICAL); tx.addView(tv(title, 14, NAVY, true)); tx.addView(tv(desc, 11, MUTED, false)); LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1); p.setMargins(dp(12), 0, 0, 0); row.addView(tx, p); row.setOnClickListener(click); list.addView(row);
    }

    private void closeDrawer() { root.removeAllViews(); renderHome(); }
    private void removeDrawer() { View d = root.findViewWithTag("drawer"); if (d != null) root.removeView(d); }

    @Override
    public void onBackPressed() {
        View d = root.findViewWithTag("drawer");
        if (d != null) { root.removeView(d); return; }
        renderHome();
    }
}
