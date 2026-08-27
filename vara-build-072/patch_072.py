from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_072.py <android-project-root>")

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

# Keep the Home, drawer and Compatibility screens aligned with the same preflight contract
# used by protected browsing. This avoids UI drift where SafePay could say ready while the
# runtime gate would later reject the session.
readiness_helpers = r'''
    private boolean protectedSessionPreflightReady() {
        return webViewRuntimeReady() && isDeviceLockSecure() && !adbEnabled();
    }

    private String protectedSessionReadinessText() {
        if (protectedSessionPreflightReady()) {
            return t("Ready for SafePay", "آماده برای SafePay");
        }
        if (!webViewRuntimeReady()) return t("WebView runtime needs attention", "موتور WebView نیاز به رسیدگی دارد");
        if (!isDeviceLockSecure()) return t("Secure screen lock required", "قفل امن صفحه لازم است");
        if (adbEnabled()) return t("USB debugging must be disabled", "اشکال‌زدایی USB باید غیرفعال شود");
        return t("Protected session needs review", "نشست محافظت‌شده نیاز به بررسی دارد");
    }

'''
rep(
    '    private String postureRefreshStamp() {',
    readiness_helpers + '    private String postureRefreshStamp() {',
    "shared protected-session readiness helper",
)

# Home: surface transaction readiness as a first-class branded status card with one clear action.
rep(
    '''        actionCenter.setOnClickListener(v -> renderActionCenter());
        content.addView(actionCenter);

        Button recheckPosture = secondary(t("Recheck security posture", "بررسی مجدد وضعیت امنیتی"));''',
    '''        actionCenter.setOnClickListener(v -> renderActionCenter());
        content.addView(actionCenter);

        boolean protectedReady = protectedSessionPreflightReady();
        LinearLayout readyCard = card();
        readyCard.setBackground(gradient(protectedReady ? Color.rgb(230,247,242) : Color.rgb(255,246,226), protectedReady ? Color.rgb(242,251,248) : Color.rgb(255,250,239), 22));
        readyCard.addView(tv(t("Protected session readiness", "آمادگی نشست محافظت‌شده"), 15, NAVY, true));
        readyCard.addView(tv(protectedSessionReadinessText(), 18, protectedReady ? GOOD : WARN, true));
        readyCard.addView(tv(protectedReady
                ? t("Screen lock, WebView runtime and USB-debugging preflight are ready.", "قفل صفحه، WebView و وضعیت اشکال‌زدایی USB برای شروع نشست آماده‌اند.")
                : t("Review the blocking prerequisite before starting a sensitive payment or browser session.", "پیش از شروع پرداخت یا مرور حساس، پیش‌نیاز مسدودکننده را بررسی کنید."),
                12, MUTED, false));
        Button readinessAction = secondary(protectedReady ? t("Open SafePay", "باز کردن SafePay") : t("Review requirements", "بررسی پیش‌نیازها"));
        LinearLayout.LayoutParams rdy = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(46));
        rdy.setMargins(0, dp(10), 0, 0);
        readyCard.addView(readinessAction, rdy);
        readinessAction.setOnClickListener(v -> { if (protectedSessionPreflightReady()) renderBrowserStart(); else renderCompatibility(); });
        content.addView(readyCard);

        Button recheckPosture = secondary(t("Recheck security posture", "بررسی مجدد وضعیت امنیتی"));''',
    "home protected-session readiness card",
)

# Drawer: keep the current posture score but add a compact protected-session status line so the
# navigation layer itself carries useful security context.
rep(
    '        head.addView(tv(drawerActions == 0 ? t("Protected • no actions waiting", "محافظت فعال • اقدامی در انتظار نیست") : t("Attention • " + drawerActions + " action(s)", "نیاز به رسیدگی • " + drawerActions + " اقدام"), 11, Color.rgb(196,221,225), false));',
    '''        head.addView(tv(drawerActions == 0 ? t("Protected • no actions waiting", "محافظت فعال • اقدامی در انتظار نیست") : t("Attention • " + drawerActions + " action(s)", "نیاز به رسیدگی • " + drawerActions + " اقدام"), 11, Color.rgb(196,221,225), false));
        head.addView(tv(t("SafePay: ", "SafePay: ") + protectedSessionReadinessText(), 11, Color.rgb(196,221,225), false));''',
    "drawer protected-session status",
)

# Compatibility: consume the same helper used on Home/drawer and expose each blocking prerequisite
# explicitly so a user can understand why protected mode is unavailable.
rep(
    '        boolean protectedSessionReady = webViewRuntimeReady() && secureLockReady && !adbEnabled();',
    '        boolean protectedSessionReady = protectedSessionPreflightReady();',
    "shared compatibility readiness",
)
rep(
    '''        protectedReady.addView(tv(t("Safe Browsing initialization is also verified at session start and fails closed if unavailable.", "راه‌اندازی Safe Browsing نیز هنگام شروع نشست بررسی می‌شود و در صورت عدم دسترسی، نشست به‌صورت امن متوقف می‌شود."), 12, MUTED, false));
        content.addView(protectedReady);''',
    '''        protectedReady.addView(tv(t("Safe Browsing initialization is also verified at session start and fails closed if unavailable.", "راه‌اندازی Safe Browsing نیز هنگام شروع نشست بررسی می‌شود و در صورت عدم دسترسی، نشست به‌صورت امن متوقف می‌شود."), 12, MUTED, false));
        protectedReady.addView(tv((webViewRuntimeReady() ? "✓ " : "• ") + t("System WebView runtime", "موتور WebView سیستم"), 12, webViewRuntimeReady() ? GOOD : WARN, true));
        protectedReady.addView(tv((secureLockReady ? "✓ " : "• ") + t("Secure screen lock", "قفل امن صفحه"), 12, secureLockReady ? GOOD : WARN, true));
        protectedReady.addView(tv((!adbEnabled() ? "✓ " : "• ") + t("USB debugging disabled", "اشکال‌زدایی USB غیرفعال"), 12, !adbEnabled() ? GOOD : WARN, true));
        content.addView(protectedReady);''',
    "compatibility prerequisite breakdown",
)

# Version metadata.
s = s.replace('0.7.1 ALPHA', '0.7.2 ALPHA')
s = s.replace('0.7.1 Alpha • versionCode 701', '0.7.2 Alpha • versionCode 702')
s = s.replace('0.7.1 Alpha', '0.7.2 Alpha')
s = s.replace('VARA 0.7.1 requires Android 8.0 / API 26 or newer.', 'VARA 0.7.2 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+701\b', 'versionCode 702', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.7\.1-alpha['\"]", "versionName '0.7.2-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'protectedSessionPreflightReady()',
    'protectedSessionReadinessText()',
    'Protected session readiness',
    'Open SafePay',
    'Review requirements',
    'SafePay: ',
    'System WebView runtime',
    'USB debugging disabled',
    '0.7.2 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.7.2 protected-session readiness UX patch applied")
