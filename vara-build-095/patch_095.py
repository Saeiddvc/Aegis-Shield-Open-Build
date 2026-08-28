from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_095.py <android-project-root>")

root = Path(sys.argv[1])
java = root / "app/src/main/java/com/varasecurity/alpha031/MainActivity.java"
gradle = root / "app/build.gradle"
s = java.read_text(encoding="utf-8")

required = [
    'PROTECTED_SESSION_MAX_MS',
    'PROTECTED_SESSION_WARNING_MS',
    'protectedSessionExpiryWarning',
    '15-minute maximum • 2-minute warning • fail-closed',
    '0.9.4 ALPHA',
]
for marker in required:
    if marker not in s:
        raise SystemExit(f"missing validated 0.9.4 prerequisite: {marker}")

# 0.9.5: make protected-session termination explicit and fail-closed from the
# in-session chrome. Leaving the browser with the back control must not leave a
# sensitive WebView alive behind a non-protected page.
clear_anchor = '''    private void clearProtectedSessionRuntime() {
        try { protectedSessionHandler.removeCallbacks(protectedSessionExpiry); } catch (Exception ignored) {}
        try { protectedSessionHandler.removeCallbacks(protectedSessionExpiryWarning); } catch (Exception ignored) {}'''
if s.count(clear_anchor) != 1:
    raise SystemExit(f"patch failed [manual protected-session end helper]: found {s.count(clear_anchor)}")
helper = '''    private void endProtectedSessionByUser() {
        if (protectedSessionActive || activeProtectedWebView != null) {
            recordActivity(t("Protected session ended by user",
                    "نشست محافظت‌شده توسط کاربر پایان یافت"));
        }
        clearProtectedSessionRuntime();
        renderHome();
        Toast.makeText(this,
                t("Protected session closed", "نشست محافظت‌شده بسته شد"),
                Toast.LENGTH_SHORT).show();
    }

'''
s = s.replace(clear_anchor, helper + clear_anchor, 1)

back_anchor = 'back.setOnClickListener(v -> renderBrowserStart()); bar.addView(back, new LinearLayout.LayoutParams(dp(48), dp(48)));'
if s.count(back_anchor) != 1:
    raise SystemExit(f"patch failed [protected browser back exit]: found {s.count(back_anchor)}")
back_new = '''back.setOnClickListener(v -> endProtectedSessionByUser()); bar.addView(back, new LinearLayout.LayoutParams(dp(48), dp(48)));
        TextView endSession = tv(t("END", "خروج"), 11, DANGER, true);
        endSession.setGravity(Gravity.CENTER);
        endSession.setBackground(rounded(Color.rgb(255, 241, 241), 14));
        endSession.setContentDescription(t("End protected session", "پایان نشست محافظت‌شده"));
        endSession.setOnClickListener(v -> endProtectedSessionByUser());
        bar.addView(endSession, new LinearLayout.LayoutParams(dp(58), dp(40)));'''
s = s.replace(back_anchor, back_new, 1)

compat_anchor = '''        sessionLifetime.addView(tv(t("SafePay and Secure Browser warn 2 minutes before the hard 15-minute expiry. The warning does not extend the session. Leaving VARA still closes the protected session immediately.",
                "SafePay و Secure Browser دو دقیقه پیش از پایان قطعی ۱۵ دقیقه‌ای هشدار می‌دهند. هشدار زمان نشست را تمدید نمی‌کند و خروج از VARA همچنان نشست محافظت‌شده را فوراً می‌بندد."), 12, MUTED, false));'''
if s.count(compat_anchor) != 1:
    raise SystemExit(f"patch failed [manual end compatibility disclosure]: found {s.count(compat_anchor)}")
compat_new = '''        sessionLifetime.addView(tv(t("SafePay and Secure Browser warn 2 minutes before the hard 15-minute expiry. The warning does not extend the session. Leaving VARA still closes the protected session immediately. The in-session END control also closes and clears the protected session immediately.",
                "SafePay و Secure Browser دو دقیقه پیش از پایان قطعی ۱۵ دقیقه‌ای هشدار می‌دهند. هشدار زمان نشست را تمدید نمی‌کند و خروج از VARA همچنان نشست محافظت‌شده را فوراً می‌بندد. کنترل خروج داخل نشست نیز نشست محافظت‌شده را فوراً می‌بندد و پاک‌سازی می‌کند."), 12, MUTED, false));'''
s = s.replace(compat_anchor, compat_new, 1)

s = s.replace('0.9.4 ALPHA', '0.9.5 ALPHA')
s = s.replace('0.9.4 Alpha • versionCode 904', '0.9.5 Alpha • versionCode 905')
s = s.replace('0.9.4 Alpha', '0.9.5 Alpha')
s = s.replace('VARA 0.9.4 requires Android 8.0 / API 26 or newer.', 'VARA 0.9.5 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+904\b', 'versionCode 905', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.9\.4-alpha['\"]", "versionName '0.9.5-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'endProtectedSessionByUser()',
    'Protected session ended by user',
    'End protected session',
    'endSession.setOnClickListener',
    'back.setOnClickListener(v -> endProtectedSessionByUser())',
    'in-session END control',
    '0.9.5 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.9.5 explicit protected-session exit patch applied")
