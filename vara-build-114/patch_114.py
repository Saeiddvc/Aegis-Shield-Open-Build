from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_114.py <android-project-root>")

root = Path(sys.argv[1])
java = root / "app/src/main/java/com/varasecurity/alpha031/MainActivity.java"
gradle = root / "app/build.gradle"
s = java.read_text(encoding="utf-8")

for marker in ['0.11.3 ALPHA', 'clearProtectedSessionRuntime()', 'web.clearHistory()', 'web.clearFormData()', 'Protected WebView isolation']:
    if marker not in s:
        raise SystemExit(f"missing validated 0.11.3 prerequisite: {marker}")

old = '''            try { web.stopLoading(); } catch (Exception ignored) {}
            try { web.clearHistory(); } catch (Exception ignored) {}
            try { web.clearFormData(); } catch (Exception ignored) {}
            try { web.destroy(); } catch (Exception ignored) {}'''
new = '''            try { web.stopLoading(); } catch (Exception ignored) {}
            try { web.clearHistory(); } catch (Exception ignored) {}
            try { web.clearFormData(); } catch (Exception ignored) {}
            try { web.clearCache(true); } catch (Exception ignored) {}
            try { web.clearSslPreferences(); } catch (Exception ignored) {}
            try { web.destroy(); } catch (Exception ignored) {}'''
if s.count(old) != 1:
    raise SystemExit(f"patch failed [protected WebView cleanup]: found {s.count(old)}")
s = s.replace(old, new, 1)

anchor = '        content.addView(webViewIsolationCard);'
if s.count(anchor) != 1:
    raise SystemExit(f"patch failed [compatibility cleanup anchor]: found {s.count(anchor)}")
card = '''        content.addView(webViewIsolationCard);

        LinearLayout sessionCleanupCard = card();
        sessionCleanupCard.addView(tv(t("Protected session cleanup", "پاک‌سازی نشست محافظت‌شده"), 16, NAVY, true));
        sessionCleanupCard.addView(tv(t("History, form state, HTTP cache and SSL preferences cleared on exit",
                "تاریخچه، داده فرم، کش HTTP و تنظیمات SSL هنگام خروج پاک می‌شوند"), 13, GOOD, true));
        sessionCleanupCard.addView(tv(t("Protected browser runtime is cleared before a new SafePay or Secure Browser session starts.",
                "وضعیت اجرایی مرورگر محافظت‌شده پیش از شروع نشست جدید SafePay یا Secure Browser پاک می‌شود."), 12, MUTED, false));
        content.addView(sessionCleanupCard);'''
s = s.replace(anchor, card, 1)

s = s.replace('0.11.3 ALPHA', '0.11.4 ALPHA')
s = s.replace('0.11.3 Alpha • versionCode 1103', '0.11.4 Alpha • versionCode 1104')
s = s.replace('0.11.3 Alpha', '0.11.4 Alpha')
s = s.replace('VARA 0.11.3 requires Android 8.0 / API 26 or newer.', 'VARA 0.11.4 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+1103\b', 'versionCode 1104', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.11\.3-alpha['\"]", "versionName '0.11.4-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

for marker in ['web.clearCache(true)', 'web.clearSslPreferences()', 'Protected session cleanup', '0.11.4 ALPHA']:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.11.4 protected-session cleanup patch applied")
