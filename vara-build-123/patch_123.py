from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_123.py <android-project-root>")

root = Path(sys.argv[1])
java = root / "app/src/main/java/com/varasecurity/alpha031/MainActivity.java"
gradle = root / "app/build.gradle"
s = java.read_text(encoding="utf-8")

for marker in [
    '0.11.12 ALPHA',
    'onShowFileChooser(WebView webView, ValueCallback<Uri[]>',
    'Protected web downloads',
    'setDownloadListener',
]:
    if marker not in s:
        raise SystemExit(f"missing validated 0.11.12 prerequisite: {marker}")

# 0.11.13: opt protected SafePay / Secure Browser WebViews out of Android Autofill
# and view-state persistence at WebView initialization time. Anchor each mutation to
# the nearest WebChromeClient receiver containing a validated fail-closed file chooser.
chooser = re.compile(
    r'@Override public boolean onShowFileChooser\(WebView webView, ValueCallback<Uri\[\]> filePathCallback, WebChromeClient\.FileChooserParams fileChooserParams\) \{\s*'
    r'filePathCallback\.onReceiveValue\(null\);\s*return true;\s*\}'
)
chooser_matches = list(chooser.finditer(s))
if not chooser_matches:
    raise SystemExit('patch failed [autofill anchor]: no protected file-chooser guards found')
expected = len(chooser_matches)

if 'IMPORTANT_FOR_AUTOFILL_NO_EXCLUDE_DESCENDANTS' in s:
    raise SystemExit('patch failed [autofill prerequisite]: protected autofill hardening already present')

client_start = re.compile(r'(?P<receiver>[A-Za-z_][A-Za-z0-9_]*)\.setWebChromeClient\(new WebChromeClient\(\)\s*\{')
insertions = []
for ordinal, cm in enumerate(chooser_matches, start=1):
    starts = list(client_start.finditer(s, 0, cm.start()))
    if not starts:
        raise SystemExit(f'patch failed [autofill client {ordinal}]: no preceding WebChromeClient found')
    st = starts[-1]
    if cm.start() - st.start() > 12000:
        raise SystemExit(f'patch failed [autofill client {ordinal}]: protected chooser too far from client anchor')
    receiver = st.group('receiver')
    line_start = s.rfind('\n', 0, st.start()) + 1
    indent = s[line_start:st.start()]
    guard = (
        f"{indent}{receiver}.setImportantForAutofill(View.IMPORTANT_FOR_AUTOFILL_NO_EXCLUDE_DESCENDANTS);\n"
        f"{indent}{receiver}.setSaveEnabled(false);\n"
    )
    insertions.append((line_start, guard, receiver))

positions = [item[0] for item in insertions]
if len(insertions) != expected or len(set(positions)) != expected:
    raise SystemExit(
        f'patch failed [autofill mutation]: expected {expected} unique protected WebView insertion points, '
        f'found {len(insertions)} / {len(set(positions))}'
    )

for pos, guard, _receiver in sorted(insertions, reverse=True):
    s = s[:pos] + guard + s[pos:]

if s.count('setImportantForAutofill(View.IMPORTANT_FOR_AUTOFILL_NO_EXCLUDE_DESCENDANTS)') != expected:
    raise SystemExit('patch failed [autofill coverage]: incomplete autofill exclusion coverage')
if s.count('setSaveEnabled(false)') < expected:
    raise SystemExit('patch failed [autofill coverage]: incomplete protected view-state suppression')

compat_anchor = '        content.addView(downloadCard);'
if s.count(compat_anchor) != 1:
    raise SystemExit(f"patch failed [compatibility autofill anchor]: found {s.count(compat_anchor)}")
card = '''        content.addView(downloadCard);\n\n        LinearLayout autofillCard = card();\n        autofillCard.addView(tv(t("Protected form privacy", "حریم خصوصی فرم‌های محافظت‌شده"), 16, NAVY, true));\n        autofillCard.addView(tv(t("Autofill and view-state persistence are disabled",\n                "تکمیل خودکار و ذخیره وضعیت فرم غیرفعال است"), 13, GOOD, true));\n        autofillCard.addView(tv(t("SafePay and Secure Browser opt protected WebViews out of Android Autofill and disable view-state saving. This reduces unintended persistence or disclosure of credentials and payment-form data to Autofill providers.",\n                "SafePay و مرورگر امن، WebViewهای محافظت‌شده را از Android Autofill خارج می‌کنند و ذخیره وضعیت فرم را غیرفعال نگه می‌دارند. این کنترل احتمال ماندگاری ناخواسته یا افشای اطلاعات ورود و فرم‌های پرداخت برای سرویس‌های Autofill را کاهش می‌دهد."), 12, MUTED, false));\n        content.addView(autofillCard);'''
s = s.replace(compat_anchor, card, 1)

s = s.replace('0.11.12 ALPHA', '0.11.13 ALPHA')
s = s.replace('0.11.12 Alpha • versionCode 1112', '0.11.13 Alpha • versionCode 1113')
s = s.replace('0.11.12 Alpha', '0.11.13 Alpha')
s = s.replace('VARA 0.11.12 requires Android 8.0 / API 26 or newer.', 'VARA 0.11.13 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding='utf-8')

g = gradle.read_text(encoding='utf-8')
g, n1 = re.subn(r'versionCode\s+1112\b', 'versionCode 1113', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.11\.12-alpha['\"]", "versionName '0.11.13-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f'version patch failed: versionCode={n1}, versionName={n2}')
gradle.write_text(g, encoding='utf-8')

for marker in [
    'IMPORTANT_FOR_AUTOFILL_NO_EXCLUDE_DESCENDANTS',
    'Protected form privacy',
    '0.11.13 ALPHA',
]:
    if marker not in s:
        raise SystemExit(f'missing expected marker after patch: {marker}')

receivers = [item[2] for item in insertions]
print(
    f'VARA Security 0.11.13 protected-form privacy hardening validated across {expected} protected WebViews: '
    f'{", ".join(receivers)}'
)
