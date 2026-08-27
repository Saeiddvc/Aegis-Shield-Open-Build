from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_108.py <android-project-root>")

root = Path(sys.argv[1])
java = root / "app/src/main/java/com/varasecurity/alpha031/MainActivity.java"
gradle = root / "app/build.gradle"
s = java.read_text(encoding="utf-8")

required = [
    'onCreateWindow(WebView view, boolean isDialog, boolean isUserGesture, android.os.Message resultMsg)',
    'onShowFileChooser(WebView webView,',
    'onPermissionRequest(android.webkit.PermissionRequest request)',
    '0.10.7 ALPHA',
]
for marker in required:
    if marker not in s:
        raise SystemExit(f"missing validated 0.10.7 prerequisite: {marker}")

anchor = '''        web.setWebChromeClient(new android.webkit.WebChromeClient() {\n            @Override public boolean onCreateWindow(WebView view, boolean isDialog, boolean isUserGesture, android.os.Message resultMsg) {'''
if s.count(anchor) != 1:
    raise SystemExit(f"patch failed [web chrome anchor]: found {s.count(anchor)}")

replacement = '''        web.setWebChromeClient(new android.webkit.WebChromeClient() {\n            @Override public boolean onJsAlert(WebView view, String url, String message, android.webkit.JsResult result) {\n                if (result != null) result.cancel();\n                recordActivity(t("Protected browser blocked a JavaScript alert dialog",\n                        "مرورگر محافظت‌شده پنجره هشدار JavaScript را مسدود کرد"));\n                Toast.makeText(MainActivity.this, t("Script dialog blocked in protected session", "پنجره اسکریپت در نشست محافظت‌شده مسدود شد"), Toast.LENGTH_SHORT).show();\n                return true;\n            }\n            @Override public boolean onJsConfirm(WebView view, String url, String message, android.webkit.JsResult result) {\n                if (result != null) result.cancel();\n                recordActivity(t("Protected browser blocked a JavaScript confirmation dialog",\n                        "مرورگر محافظت‌شده پنجره تأیید JavaScript را مسدود کرد"));\n                Toast.makeText(MainActivity.this, t("Script confirmation blocked in protected session", "تأیید اسکریپت در نشست محافظت‌شده مسدود شد"), Toast.LENGTH_SHORT).show();\n                return true;\n            }\n            @Override public boolean onJsPrompt(WebView view, String url, String message, String defaultValue, android.webkit.JsPromptResult result) {\n                if (result != null) result.cancel();\n                recordActivity(t("Protected browser blocked a JavaScript prompt dialog",\n                        "مرورگر محافظت‌شده پنجره ورودی JavaScript را مسدود کرد"));\n                Toast.makeText(MainActivity.this, t("Script prompt blocked in protected session", "ورودی اسکریپت در نشست محافظت‌شده مسدود شد"), Toast.LENGTH_SHORT).show();\n                return true;\n            }\n            @Override public boolean onCreateWindow(WebView view, boolean isDialog, boolean isUserGesture, android.os.Message resultMsg) {'''
s = s.replace(anchor, replacement, 1)

# Surface the policy in Compatibility without depending on disclosure wording from older builds.
compat_anchor = '        LinearLayout backgroundIsolation = card();'
if s.count(compat_anchor) != 1:
    raise SystemExit(f"patch failed [compatibility anchor]: found {s.count(compat_anchor)}")
compat_card = '''        LinearLayout scriptDialogPolicy = card();\n        scriptDialogPolicy.addView(tv(t("Protected script-dialog policy", "سیاست پنجره‌های اسکریپت محافظت‌شده"), 16, NAVY, true));\n        scriptDialogPolicy.addView(tv(t("JavaScript alert, confirm and prompt dialogs are blocked inside SafePay and Secure Browser to reduce spoofed credential or confirmation surfaces.",\n                "پنجره‌های alert، confirm و prompt جاوااسکریپت در SafePay و Secure Browser مسدود می‌شوند تا سطح سوءاستفاده برای جعل ورود اطلاعات یا تأیید کاهش یابد."), 12, MUTED, false));\n        content.addView(scriptDialogPolicy);\n\n'''
s = s.replace(compat_anchor, compat_card + compat_anchor, 1)

s = s.replace('0.10.7 ALPHA', '0.10.8 ALPHA')
s = s.replace('0.10.7 Alpha • versionCode 1007', '0.10.8 Alpha • versionCode 1008')
s = s.replace('0.10.7 Alpha', '0.10.8 Alpha')
s = s.replace('VARA 0.10.7 requires Android 8.0 / API 26 or newer.', 'VARA 0.10.8 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+1007\b', 'versionCode 1008', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.10\.7-alpha['\"]", "versionName '0.10.8-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'onJsAlert(WebView view, String url, String message, android.webkit.JsResult result)',
    'onJsConfirm(WebView view, String url, String message, android.webkit.JsResult result)',
    'onJsPrompt(WebView view, String url, String message, String defaultValue, android.webkit.JsPromptResult result)',
    'Script dialog blocked in protected session',
    'Protected script-dialog policy',
    '0.10.8 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.10.8 protected JavaScript dialog hardening patch applied")
