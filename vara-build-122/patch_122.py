from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_122.py <android-project-root>")

root = Path(sys.argv[1])
java = root / "app/src/main/java/com/varasecurity/alpha031/MainActivity.java"
gradle = root / "app/build.gradle"
s = java.read_text(encoding="utf-8")

for marker in [
    '0.11.11 ALPHA',
    'onShowFileChooser(WebView webView, ValueCallback<Uri[]>',
    'filePathCallback.onReceiveValue(null)',
    'Protected file sharing',
]:
    if marker not in s:
        raise SystemExit(f"missing validated 0.11.11 prerequisite: {marker}")

# 0.11.12: protected WebViews must not hand web-triggered downloads to Android.
# SafePay/Secure Browser are transaction/navigation surfaces, not file-transfer
# surfaces. A no-op DownloadListener keeps ordinary HTTPS navigation intact while
# preventing web pages from initiating device downloads from these sessions.
chooser = re.compile(
    r'(?P<indent>^[ \t]*)@Override public boolean onShowFileChooser\(WebView webView, ValueCallback<Uri\[\]> filePathCallback, WebChromeClient\.FileChooserParams fileChooserParams\) \{\s*'
    r'(?P=indent)[ \t]+filePathCallback\.onReceiveValue\(null\);\s*'
    r'(?P=indent)[ \t]+return true;\s*'
    r'(?P=indent)\}',
    re.MULTILINE,
)
matches = list(chooser.finditer(s))
if not matches:
    raise SystemExit('patch failed [download anchor]: no protected file-chooser guards found')
expected = len(matches)

def add_download_guard(match):
    indent = match.group('indent')
    block = match.group(0)
    return block + f"\n{indent}webView.setDownloadListener((url, userAgent, contentDisposition, mimeType, contentLength) -> {{ }});"

s, changed = chooser.subn(add_download_guard, s)
if changed != expected:
    raise SystemExit(f'patch failed [download mutation]: expected {expected}, changed {changed}')

guards = s.count('webView.setDownloadListener((url, userAgent, contentDisposition, mimeType, contentLength) -> { });')
if guards != expected:
    raise SystemExit(f'patch failed [download coverage]: expected {expected}, validated {guards}')

compat_anchor = '        content.addView(fileChooserCard);'
if s.count(compat_anchor) != 1:
    raise SystemExit(f"patch failed [compatibility download anchor]: found {s.count(compat_anchor)}")
card = '''        content.addView(fileChooserCard);\n\n        LinearLayout downloadCard = card();\n        downloadCard.addView(tv(t("Protected web downloads", "دانلود وب محافظت‌شده"), 16, NAVY, true));\n        downloadCard.addView(tv(t("Web-triggered downloads are blocked",\n                "دانلودهای آغازشده از وب مسدود هستند"), 13, GOOD, true));\n        downloadCard.addView(tv(t("SafePay and Secure Browser do not hand web-triggered downloads to Android. This reduces malicious or unintended file delivery from protected sessions while normal HTTPS navigation remains available.",\n                "SafePay و مرورگر امن دانلودهای آغازشده از صفحات وب را به اندروید تحویل نمی‌دهند. این کنترل ریسک دریافت فایل ناخواسته یا مخرب را در نشست‌های محافظت‌شده کاهش می‌دهد و پیمایش عادی HTTPS را حفظ می‌کند."), 12, MUTED, false));\n        content.addView(downloadCard);'''
s = s.replace(compat_anchor, card, 1)

s = s.replace('0.11.11 ALPHA', '0.11.12 ALPHA')
s = s.replace('0.11.11 Alpha • versionCode 1111', '0.11.12 Alpha • versionCode 1112')
s = s.replace('0.11.11 Alpha', '0.11.12 Alpha')
s = s.replace('VARA 0.11.11 requires Android 8.0 / API 26 or newer.', 'VARA 0.11.12 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding='utf-8')

g = gradle.read_text(encoding='utf-8')
g, n1 = re.subn(r'versionCode\s+1111\b', 'versionCode 1112', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.11\.11-alpha['\"]", "versionName '0.11.12-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f'version patch failed: versionCode={n1}, versionName={n2}')
gradle.write_text(g, encoding='utf-8')

for marker in [
    'setDownloadListener',
    'Protected web downloads',
    '0.11.12 ALPHA',
]:
    if marker not in s:
        raise SystemExit(f'missing expected marker after patch: {marker}')

print(f'VARA Security 0.11.12 protected-download hardening validated across {expected} protected WebViews')
