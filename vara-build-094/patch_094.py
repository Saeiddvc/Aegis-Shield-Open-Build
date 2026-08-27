from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_094.py <android-project-root>")

root = Path(sys.argv[1])
java = root / "app/src/main/java/com/varasecurity/alpha031/MainActivity.java"
gradle = root / "app/build.gradle"
s = java.read_text(encoding="utf-8")

required = [
    'PROTECTED_SESSION_MAX_MS',
    'protectedSessionExpiry',
    'Protected-session lifetime',
    '0.9.3 ALPHA',
]
for marker in required:
    if marker not in s:
        raise SystemExit(f"missing validated 0.9.3 prerequisite: {marker}")

# 0.9.4: keep the hard 15-minute fail-closed limit, but warn the user two
# minutes before expiry so a legitimate banking/payment flow is not interrupted
# without notice. The warning does not extend or weaken the security lifetime.
state_anchor = '''    private final Runnable protectedSessionExpiry = () -> {
        if (!protectedSessionActive) return;
        recordActivity(t("Protected session closed after 15-minute safety limit",
                "نشست محافظت‌شده پس از محدودیت ایمنی ۱۵ دقیقه‌ای بسته شد"));
        clearProtectedSessionRuntime();
        renderHome();
        Toast.makeText(this,
                t("Protected session expired for safety", "نشست محافظت‌شده برای حفظ ایمنی منقضی شد"),
                Toast.LENGTH_LONG).show();
    };'''
if s.count(state_anchor) != 1:
    raise SystemExit(f"patch failed [expiry warning state]: found {s.count(state_anchor)}")
state_new = state_anchor + '''
    private static final long PROTECTED_SESSION_WARNING_MS = PROTECTED_SESSION_MAX_MS - (2L * 60L * 1000L);
    private final Runnable protectedSessionExpiryWarning = () -> {
        if (!protectedSessionActive) return;
        recordActivity(t("Protected session expiry warning shown",
                "هشدار پایان نشست محافظت‌شده نمایش داده شد"));
        Toast.makeText(this,
                t("Protected session will close in 2 minutes", "نشست محافظت‌شده تا ۲ دقیقه دیگر بسته می‌شود"),
                Toast.LENGTH_LONG).show();
    };'''
s = s.replace(state_anchor, state_new, 1)

clear_anchor = '''        try { protectedSessionHandler.removeCallbacks(protectedSessionExpiry); } catch (Exception ignored) {}
        WebView web = activeProtectedWebView;'''
if s.count(clear_anchor) != 1:
    raise SystemExit(f"patch failed [warning cancellation]: found {s.count(clear_anchor)}")
clear_new = '''        try { protectedSessionHandler.removeCallbacks(protectedSessionExpiry); } catch (Exception ignored) {}
        try { protectedSessionHandler.removeCallbacks(protectedSessionExpiryWarning); } catch (Exception ignored) {}
        WebView web = activeProtectedWebView;'''
s = s.replace(clear_anchor, clear_new, 1)

launch_anchor = '''        protectedSessionHandler.removeCallbacks(protectedSessionExpiry);
        protectedSessionHandler.postDelayed(protectedSessionExpiry, PROTECTED_SESSION_MAX_MS);'''
if s.count(launch_anchor) != 1:
    raise SystemExit(f"patch failed [schedule expiry warning]: found {s.count(launch_anchor)}")
launch_new = '''        protectedSessionHandler.removeCallbacks(protectedSessionExpiry);
        protectedSessionHandler.removeCallbacks(protectedSessionExpiryWarning);
        protectedSessionHandler.postDelayed(protectedSessionExpiryWarning, PROTECTED_SESSION_WARNING_MS);
        protectedSessionHandler.postDelayed(protectedSessionExpiry, PROTECTED_SESSION_MAX_MS);'''
s = s.replace(launch_anchor, launch_new, 1)

compat_anchor = '''        sessionLifetime.addView(tv(t("15-minute maximum • fail-closed", "حداکثر ۱۵ دقیقه • بسته‌شدن امن"), 13, GOOD, true));
        sessionLifetime.addView(tv(t("SafePay and Secure Browser sessions close automatically after 15 minutes even if VARA remains in the foreground. Leaving VARA still closes them immediately.",
                "نشست‌های SafePay و Secure Browser حتی اگر VARA در پیش‌زمینه بماند، پس از ۱۵ دقیقه به‌صورت خودکار بسته می‌شوند. خروج از VARA همچنان نشست را فوراً می‌بندد."), 12, MUTED, false));'''
if s.count(compat_anchor) != 1:
    raise SystemExit(f"patch failed [compatibility lifetime warning copy]: found {s.count(compat_anchor)}")
compat_new = '''        sessionLifetime.addView(tv(t("15-minute maximum • 2-minute warning • fail-closed", "حداکثر ۱۵ دقیقه • هشدار ۲ دقیقه‌ای • بسته‌شدن امن"), 13, GOOD, true));
        sessionLifetime.addView(tv(t("SafePay and Secure Browser warn 2 minutes before the hard 15-minute expiry. The warning does not extend the session. Leaving VARA still closes the protected session immediately.",
                "SafePay و Secure Browser دو دقیقه پیش از پایان قطعی ۱۵ دقیقه‌ای هشدار می‌دهند. هشدار زمان نشست را تمدید نمی‌کند و خروج از VARA همچنان نشست محافظت‌شده را فوراً می‌بندد."), 12, MUTED, false));'''
s = s.replace(compat_anchor, compat_new, 1)

s = s.replace('0.9.3 ALPHA', '0.9.4 ALPHA')
s = s.replace('0.9.3 Alpha • versionCode 903', '0.9.4 Alpha • versionCode 904')
s = s.replace('0.9.3 Alpha', '0.9.4 Alpha')
s = s.replace('VARA 0.9.3 requires Android 8.0 / API 26 or newer.', 'VARA 0.9.4 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+903\b', 'versionCode 904', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.9\.3-alpha['\"]", "versionName '0.9.4-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'PROTECTED_SESSION_WARNING_MS',
    'protectedSessionExpiryWarning',
    'Protected session will close in 2 minutes',
    'protectedSessionHandler.postDelayed(protectedSessionExpiryWarning',
    '15-minute maximum • 2-minute warning • fail-closed',
    'warning does not extend the session',
    '0.9.4 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.9.4 protected-session expiry warning patch applied")
