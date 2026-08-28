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
# Install a no-op DownloadListener on each protected WebView itself. Local WebView
# variable names are intentionally allowed to repeat across different methods/scopes;
# coverage is therefore validated by structurally matched chooser instances and
# insertion positions rather than by receiver-name uniqueness.
if '.setDownloadListener(' in s:
    raise SystemExit('patch failed [download prerequisite]: unexpected pre-existing DownloadListener')

chooser = re.compile(
    r'@Override public boolean onShowFileChooser\(WebView webView, ValueCallback<Uri\[\]> filePathCallback, WebChromeClient\.FileChooserParams fileChooserParams\) \{\s*'
    r'filePathCallback\.onReceiveValue\(null\);\s*return true;\s*\}'
)
chooser_matches = list(chooser.finditer(s))
if not chooser_matches:
    raise SystemExit('patch failed [download anchor]: no protected file-chooser guards found')
expected = len(chooser_matches)

client_start = re.compile(r'(?P<receiver>[A-Za-z_][A-Za-z0-9_]*)\.setWebChromeClient\(new WebChromeClient\(\)\s*\{')
insertions = []

for ordinal, cm in enumerate(chooser_matches, start=1):
    starts = list(client_start.finditer(s, 0, cm.start()))
    if not starts:
        raise SystemExit(f'patch failed [download client {ordinal}]: no enclosing WebChromeClient start found')
    st = starts[-1]
    receiver = st.group('receiver')
    brace_open = s.find('{', st.start(), st.end())
    if brace_open < 0:
        raise SystemExit(f'patch failed [download client {ordinal}]: opening brace not found')

    depth = 0
    i = brace_open
    close_brace = -1
    while i < len(s):
        ch = s[i]
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                close_brace = i
                break
        i += 1
    if close_brace < 0 or not (st.start() < cm.start() < close_brace):
        raise SystemExit(f'patch failed [download client {ordinal}]: chooser not enclosed for {receiver}')

    j = close_brace + 1
    while j < len(s) and s[j].isspace():
        j += 1
    if s[j:j+2] != ');':
        raise SystemExit(f'patch failed [download client {ordinal}]: expected WebChromeClient call terminator for {receiver}')
    statement_end = j + 2

    line_start = s.rfind('\n', 0, st.start()) + 1
    indent = s[line_start:st.start()]
    guard = f"\n{indent}{receiver}.setDownloadListener((url, userAgent, contentDisposition, mimeType, contentLength) -> {{ }});"
    insertions.append((statement_end, guard, receiver, ordinal))

if len(insertions) != expected:
    raise SystemExit(f'patch failed [download mutation]: expected {expected}, located {len(insertions)}')

positions = [item[0] for item in insertions]
if len(set(positions)) != expected:
    raise SystemExit(f'patch failed [download mutation]: duplicate insertion positions detected ({len(set(positions))}/{expected})')

for pos, guard, _receiver, _ordinal in sorted(insertions, reverse=True):
    s = s[:pos] + guard + s[pos:]

listener_pattern = re.compile(
    r'\b[A-Za-z_][A-Za-z0-9_]*\.setDownloadListener\(\(url, userAgent, contentDisposition, mimeType, contentLength\) -> \{ \}\);'
)
listeners = list(listener_pattern.finditer(s))
if len(listeners) != expected:
    raise SystemExit(f'patch failed [download coverage]: expected {expected} listeners, found {len(listeners)}')

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

receivers = [item[2] for item in insertions]
print(f'VARA Security 0.11.12 protected-download hardening validated across {expected} protected WebViews: {", ".join(receivers)}')
