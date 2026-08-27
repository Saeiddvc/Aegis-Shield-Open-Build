from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_060.py <android-project-root>")

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

# Typography: slightly more breathing room and remove legacy extra font padding for a cleaner
# Android-native baseline in both English and Persian.
rep(
    '        v.setLineSpacing(0, 1.08f);',
    '        v.setLineSpacing(0, 1.12f);\n        v.setIncludeFontPadding(false);',
    "typography rhythm",
)

# A local posture score gives Home and the drawer one consistent, explainable status signal.
# It is intentionally a review-priority heuristic, not a malware probability or compromise verdict.
posture_helpers = r'''
    private int securityPostureScore(AppRiskSummary risk) {
        int deviceIssues = auditIssueCount();
        int flagged = risk == null ? 0 : risk.flaggedAppCount();
        int high = risk == null ? 0 : risk.highRiskCount();
        int nonHigh = Math.max(0, flagged - high);
        int score = 100 - (deviceIssues * 12) - (high * 8) - (nonHigh * 3);
        return Math.max(0, Math.min(100, score));
    }

    private String securityPostureLabel(int score) {
        if (score >= 90) return t("Strong", "قوی");
        if (score >= 70) return t("Review", "نیازمند بررسی");
        return t("Priority review", "بررسی فوری");
    }

'''
rep(
    '    private void renderHome() {',
    posture_helpers + '    private void renderHome() {',
    "posture score helpers",
)

rep(
    '        int homeActions = homeIssues + homePosture.flaggedAppCount();',
    '        int homeActions = homeIssues + homePosture.flaggedAppCount();\n        int postureScore = securityPostureScore(homePosture);',
    "home posture score",
)

rep(
    '        TextView stateChip = tv(homeActions == 0 ? t("SECURE", "ایمن") : t("REVIEW " + homeActions, "بررسی " + homeActions), 11, Color.WHITE, true);',
    '        TextView stateChip = tv(postureScore + " / 100", 11, Color.WHITE, true);',
    "home score chip",
)

rep(
    '        postureText.addView(tv(homeActions == 0 ? t("No remediation is currently waiting", "در حال حاضر اقدام اصلاحی در انتظار نیست") : t(homeActions + " prioritized action(s) waiting", homeActions + " اقدام اولویت‌بندی‌شده در انتظار است"), 12, MUTED, false));',
    '        postureText.addView(tv(t("Posture " + postureScore + "/100 • " + securityPostureLabel(postureScore), "امتیاز وضعیت " + postureScore + "/100 • " + securityPostureLabel(postureScore)), 12, MUTED, false));\n        postureText.addView(tv(homeActions == 0 ? t("No remediation is currently waiting", "در حال حاضر اقدام اصلاحی در انتظار نیست") : t(homeActions + " prioritized action(s) waiting", homeActions + " اقدام اولویت‌بندی‌شده در انتظار است"), 12, MUTED, false));',
    "home posture explanation",
)

# Drawer header: surface the same posture score so navigation always carries useful security context.
rep(
    '        int drawerActions = drawerIssues + drawerRisk.flaggedAppCount();',
    '        int drawerActions = drawerIssues + drawerRisk.flaggedAppCount();\n        int drawerScore = securityPostureScore(drawerRisk);',
    "drawer posture score",
)
rep(
    '        head.addView(tv(drawerActions == 0 ? t("Protected • posture clear", "محافظت فعال • وضعیت مناسب") : t("Attention • " + drawerActions + " action(s)", "نیاز به رسیدگی • " + drawerActions + " اقدام"), 12, Color.rgb(214,235,237), false));',
    '        head.addView(tv(t("Posture " + drawerScore + "/100 • " + securityPostureLabel(drawerScore), "امتیاز وضعیت " + drawerScore + "/100 • " + securityPostureLabel(drawerScore)), 12, Color.rgb(214,235,237), false));\n        head.addView(tv(drawerActions == 0 ? t("Protected • no actions waiting", "محافظت فعال • اقدامی در انتظار نیست") : t("Attention • " + drawerActions + " action(s)", "نیاز به رسیدگی • " + drawerActions + " اقدام"), 11, Color.rgb(196,221,225), false));',
    "drawer score presentation",
)

# Action Center: make the remediation queue's score explicit while preserving drill-down actions.
rep(
    '        int total = deviceIssues + appFindings;',
    '        int total = deviceIssues + appFindings;\n        int postureScore = securityPostureScore(risk);',
    "action center score",
)
rep(
    '        hero.addView(tv(total == 0 ? t("No actions required", "اقدامی لازم نیست") : t(total + " security action(s)", total + " اقدام امنیتی"), 21, Color.WHITE, true));',
    '        hero.addView(tv(t("Posture " + postureScore + "/100 • " + securityPostureLabel(postureScore), "امتیاز وضعیت " + postureScore + "/100 • " + securityPostureLabel(postureScore)), 21, Color.WHITE, true));\n        hero.addView(tv(total == 0 ? t("No actions required", "اقدامی لازم نیست") : t(total + " security action(s)", total + " اقدام امنیتی"), 14, Color.rgb(244,248,250), true));',
    "action center score hero",
)

# SafePay / Secure Browser hardening: a protected session now requires a secure Android
# screen lock in addition to a usable WebView and Safe Browsing initialization. This prevents
# presenting a high-assurance payment/browser session on an unlocked device posture.
secure_lock_gate = r'''        if (!webViewRuntimeReady()) {
            String event = t("Protected browser blocked: system WebView unavailable", "مرورگر محافظت‌شده مسدود شد: WebView سیستم در دسترس نیست");
            recordActivity(event);
            try { web.destroy(); } catch (Exception ignored) {}
            Toast.makeText(MainActivity.this, t("Secure WebView runtime unavailable", "موتور WebView امن در دسترس نیست"), Toast.LENGTH_LONG).show();
            renderBrowserStart();
            return;
        }
        if (!isDeviceLockSecure()) {
            String event = t("Protected browser blocked: secure screen lock required", "مرورگر محافظت‌شده مسدود شد: قفل امن صفحه لازم است");
            recordActivity(event);
            try { web.stopLoading(); web.destroy(); } catch (Exception ignored) {}
            Toast.makeText(MainActivity.this, t("Enable a secure screen lock before SafePay or protected browsing", "پیش از SafePay یا مرور محافظت‌شده، قفل امن صفحه را فعال کنید"), Toast.LENGTH_LONG).show();
            openSettings(Settings.ACTION_SECURITY_SETTINGS);
            renderBrowserStart();
            return;
        }
        WebView.startSafeBrowsing(this, value -> {'''
rep(
    '''        if (!webViewRuntimeReady()) {
            String event = t("Protected browser blocked: system WebView unavailable", "مرورگر محافظت‌شده مسدود شد: WebView سیستم در دسترس نیست");
            recordActivity(event);
            try { web.destroy(); } catch (Exception ignored) {}
            Toast.makeText(MainActivity.this, t("Secure WebView runtime unavailable", "موتور WebView امن در دسترس نیست"), Toast.LENGTH_LONG).show();
            renderBrowserStart();
            return;
        }
        WebView.startSafeBrowsing(this, value -> {''',
    secure_lock_gate,
    "protected session secure-lock gate",
)

# Compatibility page: expose all protected-session prerequisites as one actionable contract.
rep(
    '        Button recheck = secondary(t("Recheck compatibility", "بررسی مجدد سازگاری"));',
    '''        LinearLayout protectedReady = card();
        boolean secureLockReady = isDeviceLockSecure();
        boolean protectedSessionReady = webViewRuntimeReady() && secureLockReady;
        protectedReady.addView(tv(t("Protected-session readiness", "آمادگی نشست محافظت‌شده"), 16, NAVY, true));
        protectedReady.addView(tv(protectedSessionReady
                ? t("Ready • WebView available and secure screen lock enabled", "آماده • WebView در دسترس و قفل امن صفحه فعال است")
                : t("Needs review • SafePay requires WebView and a secure screen lock", "نیازمند بررسی • SafePay به WebView و قفل امن صفحه نیاز دارد"),
                13, protectedSessionReady ? GOOD : WARN, true));
        protectedReady.addView(tv(t("Safe Browsing initialization is also verified at session start and fails closed if unavailable.", "راه‌اندازی Safe Browsing نیز هنگام شروع نشست بررسی می‌شود و در صورت عدم دسترسی، نشست به‌صورت امن متوقف می‌شود."), 12, MUTED, false));
        content.addView(protectedReady);

        Button recheck = secondary(t("Recheck compatibility", "بررسی مجدد سازگاری"));''',
    "protected session compatibility contract",
)

# Version metadata.
s = s.replace('0.5.9 ALPHA', '0.6.0 ALPHA')
s = s.replace('0.5.9 Alpha • versionCode 509', '0.6.0 Alpha • versionCode 600')
s = s.replace('0.5.9 Alpha', '0.6.0 Alpha')
s = s.replace('VARA 0.5.9 requires Android 8.0 / API 26 or newer.', 'VARA 0.6.0 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+509\b', 'versionCode 600', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.5\.9-alpha['\"]", "versionName '0.6.0-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'securityPostureScore(AppRiskSummary risk)',
    'Posture " + postureScore + "/100',
    'drawerScore = securityPostureScore(drawerRisk)',
    'setIncludeFontPadding(false)',
    'Protected browser blocked: secure screen lock required',
    'Protected-session readiness',
    '0.6.0 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.6.0 posture UX and protected-session preflight patch applied")
