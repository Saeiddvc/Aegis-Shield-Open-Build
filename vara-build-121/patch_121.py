from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_121.py <android-project-root>")

root = Path(sys.argv[1])
java = root / "app/src/main/java/com/varasecurity/alpha031/MainActivity.java"
gradle = root / "app/build.gradle"
s = java.read_text(encoding="utf-8")

for marker in [
    '0.11.10 ALPHA',
    'onPermissionRequest(PermissionRequest request)',
    'request.deny()',
    'Protected web permissions',
]:
    if marker not in s:
        raise SystemExit(f"missing validated 0.11.10 prerequisite: {marker}")

# 0.11.11: fail closed on HTML file-upload/file-picker requests inside all
# protected WebViews. This prevents a payment or browsing page from opening an
# Android document picker and receiving a user-selected local file. Normal
# HTTPS navigation remains unchanged.
if 'import android.net.Uri;' not in s:
    s = s.replace('import android.graphics.Color;\n', 'import android.graphics.Color;\nimport android.net.Uri;\n', 1)
if 'import android.webkit.ValueCallback;' not in s:
    s = s.replace('import android.webkit.PermissionRequest;\n', 'import android.webkit.PermissionRequest;\nimport android.webkit.ValueCallback;\n', 1)

anchor = re.compile(
    r'(?m)^(?P<indent>[ \t]*)@Override public void onPermissionRequest\(PermissionRequest request\) \{ request\.deny\(\); \}[ \t]*$'
)
matches = list(anchor.finditer(s))
if not matches:
    raise SystemExit('patch failed [file chooser anchor]: no protected WebChromeClient blocks found')
expected = len(matches)

def add_file_chooser_guard(match):
    indent = match.group('indent')
    return (
        f"{match.group(0)}\n"
        f"{indent}@Override public boolean onShowFileChooser(WebView webView, ValueCallback<Uri[]> filePathCallback, WebChromeClient.FileChooserParams fileChooserParams) {{\n"
        f"{indent}    filePathCallback.onReceiveValue(null);\n"
        f"{indent}    return true;\n"
        f"{indent}}}"
    )

s, changed = anchor.subn(add_file_chooser_guard, s)
if changed != expected:
    raise SystemExit(f'patch failed [file chooser mutation]: expected {expected}, changed {changed}')

guards = s.count('onShowFileChooser(WebView webView, ValueCallback<Uri[]> filePathCallback, WebChromeClient.FileChooserParams fileChooserParams)')
cancels = s.count('filePathCallback.onReceiveValue(null);')
if guards != expected or cancels != expected:
    raise SystemExit(f'patch failed [file chooser coverage]: expected {expected}, guards={guards}, cancels={cancels}')

compat_anchor = '        content.addView(webPermissionCard);'
if s.count(compat_anchor) != 1:
    raise SystemExit(f"patch failed [compatibility file chooser anchor]: found {s.count(compat_anchor)}")
card = '''        content.addView(webPermissionCard);\n\n        LinearLayout fileChooserCard = card();\n        fileChooserCard.addView(tv(t("Protected file sharing", "اشتراک‌گذاری فایل محافظت‌شده"), 16, NAVY, true));\n        fileChooserCard.addView(tv(t("Web file-picker requests are blocked",\n                "درخواست انتخاب فایل از وب مسدود است"), 13, GOOD, true));\n        fileChooserCard.addView(tv(t("SafePay and Secure Browser do not expose Android document-picker results to web pages. This reduces local-document exfiltration risk while standard HTTPS banking and payment navigation remains available.",\n                "SafePay و مرورگر امن نتیجه انتخاب فایل از حافظه دستگاه را در اختیار صفحات وب قرار نمی‌دهند. این کنترل ریسک خروج اسناد محلی را کاهش می‌دهد و پیمایش عادی HTTPS بانکی و پرداخت را حفظ می‌کند."), 12, MUTED, false));\n        content.addView(fileChooserCard);'''
s = s.replace(compat_anchor, card, 1)

s = s.replace('0.11.10 ALPHA', '0.11.11 ALPHA')
s = s.replace('0.11.10 Alpha • versionCode 1110', '0.11.11 Alpha • versionCode 1111')
s = s.replace('0.11.10 Alpha', '0.11.11 Alpha')
s = s.replace('VARA 0.11.10 requires Android 8.0 / API 26 or newer.', 'VARA 0.11.11 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding='utf-8')

g = gradle.read_text(encoding='utf-8')
g, n1 = re.subn(r'versionCode\s+1110\b', 'versionCode 1111', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.11\.10-alpha['\"]", "versionName '0.11.11-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f'version patch failed: versionCode={n1}, versionName={n2}')
gradle.write_text(g, encoding='utf-8')

for marker in [
    'ValueCallback<Uri[]>',
    'filePathCallback.onReceiveValue(null)',
    'Protected file sharing',
    '0.11.11 ALPHA',
]:
    if marker not in s:
        raise SystemExit(f'missing expected marker after patch: {marker}')

print(f'VARA Security 0.11.11 file-chooser hardening validated across {expected} protected WebViews')
