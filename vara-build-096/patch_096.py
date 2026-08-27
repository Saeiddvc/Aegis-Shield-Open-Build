from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_096.py <android-project-root>")

root = Path(sys.argv[1])
java = root / "app/src/main/java/com/varasecurity/alpha031/MainActivity.java"
gradle = root / "app/build.gradle"
s = java.read_text(encoding="utf-8")

required = [
    'endProtectedSessionByUser()',
    'PROTECTED_SESSION_MAX_MS',
    'PROTECTED_SESSION_WARNING_MS',
    '0.9.5 ALPHA',
]
for marker in required:
    if marker not in s:
        raise SystemExit(f"missing validated 0.9.5 prerequisite: {marker}")

# 0.9.6: make the protected-session hard lifetime visible inside the session.
# The UI shows the absolute local expiry time so the user can see the security
# boundary before the 2-minute warning fires. This is informational only and
# does not extend or relax the 15-minute fail-closed limit.
state_anchor = '    private static final long PROTECTED_SESSION_MAX_MS = 15L * 60L * 1000L;'
if s.count(state_anchor) != 1:
    raise SystemExit(f"patch failed [session deadline state]: found {s.count(state_anchor)}")
state_new = '''    private static final long PROTECTED_SESSION_MAX_MS = 15L * 60L * 1000L;
    private long protectedSessionDeadlineMs = 0L;

    private String protectedSessionDeadlineLabel() {
        if (protectedSessionDeadlineMs <= 0L) return t("15 min max", "حداکثر ۱۵ دقیقه");
        try {
            java.text.DateFormat format = java.text.DateFormat.getTimeInstance(java.text.DateFormat.SHORT);
            return t("Ends " + format.format(new java.util.Date(protectedSessionDeadlineMs)),
                    "پایان " + format.format(new java.util.Date(protectedSessionDeadlineMs)));
        } catch (Exception ignored) {
            return t("15 min max", "حداکثر ۱۵ دقیقه");
        }
    }'''
s = s.replace(state_anchor, state_new, 1)

launch_anchor = '''        protectedSessionActive = true;
        protectedSessionLaunchAllowed = true;
        protectedSessionHandler.removeCallbacks(protectedSessionExpiry);'''
if s.count(launch_anchor) != 1:
    raise SystemExit(f"patch failed [session deadline scheduling]: found {s.count(launch_anchor)}")
launch_new = '''        protectedSessionActive = true;
        protectedSessionLaunchAllowed = true;
        protectedSessionDeadlineMs = System.currentTimeMillis() + PROTECTED_SESSION_MAX_MS;
        protectedSessionHandler.removeCallbacks(protectedSessionExpiry);'''
s = s.replace(launch_anchor, launch_new, 1)

clear_anchor = '''    private void clearProtectedSessionRuntime() {
        try { protectedSessionHandler.removeCallbacks(protectedSessionExpiry); } catch (Exception ignored) {}
        try { protectedSessionHandler.removeCallbacks(protectedSessionExpiryWarning); } catch (Exception ignored) {}'''
if s.count(clear_anchor) != 1:
    raise SystemExit(f"patch failed [session deadline reset]: found {s.count(clear_anchor)}")
clear_new = '''    private void clearProtectedSessionRuntime() {
        try { protectedSessionHandler.removeCallbacks(protectedSessionExpiry); } catch (Exception ignored) {}
        try { protectedSessionHandler.removeCallbacks(protectedSessionExpiryWarning); } catch (Exception ignored) {}
        protectedSessionDeadlineMs = 0L;'''
s = s.replace(clear_anchor, clear_new, 1)

end_anchor = '''        endSession.setOnClickListener(v -> endProtectedSessionByUser());
        bar.addView(endSession, new LinearLayout.LayoutParams(dp(58), dp(40)));'''
if s.count(end_anchor) != 1:
    raise SystemExit(f"patch failed [in-session deadline label]: found {s.count(end_anchor)}")
end_new = '''        endSession.setOnClickListener(v -> endProtectedSessionByUser());
        bar.addView(endSession, new LinearLayout.LayoutParams(dp(58), dp(40)));
        TextView sessionDeadline = tv(protectedSessionDeadlineLabel(), 11, MUTED, true);
        sessionDeadline.setGravity(Gravity.CENTER_VERTICAL | Gravity.END);
        LinearLayout.LayoutParams deadlineParams = new LinearLayout.LayoutParams(0, dp(40), 1);
        deadlineParams.setMargins(dp(8), 0, 0, 0);
        bar.addView(sessionDeadline, deadlineParams);'''
s = s.replace(end_anchor, end_new, 1)

compat_anchor = 'The in-session END control also closes and clears the protected session immediately.'
if s.count(compat_anchor) != 1:
    raise SystemExit(f"patch failed [compatibility deadline disclosure]: found {s.count(compat_anchor)}")
s = s.replace(compat_anchor,
              compat_anchor + ' The protected-session bar also shows the local expiry time.', 1)

s = s.replace('0.9.5 ALPHA', '0.9.6 ALPHA')
s = s.replace('0.9.5 Alpha • versionCode 905', '0.9.6 Alpha • versionCode 906')
s = s.replace('0.9.5 Alpha', '0.9.6 Alpha')
s = s.replace('VARA 0.9.5 requires Android 8.0 / API 26 or newer.', 'VARA 0.9.6 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+905\b', 'versionCode 906', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.9\.5-alpha['\"]", "versionName '0.9.6-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'protectedSessionDeadlineMs',
    'protectedSessionDeadlineLabel()',
    'System.currentTimeMillis() + PROTECTED_SESSION_MAX_MS',
    'TextView sessionDeadline',
    'shows the local expiry time',
    '0.9.6 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.9.6 protected-session expiry visibility patch applied")
