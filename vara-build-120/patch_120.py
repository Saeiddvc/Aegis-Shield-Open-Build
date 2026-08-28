from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_120.py <android-project-root>")

root = Path(sys.argv[1])
java = root / "app/src/main/java/com/varasecurity/alpha031/MainActivity.java"
gradle = root / "app/build.gradle"
s = java.read_text(encoding="utf-8")

for marker in [
    '0.11.9 ALPHA',
    'setAllowFileAccess(false)',
    'setAllowContentAccess(false)',
    'Protected local-resource boundary',
]:
    if marker not in s:
        raise SystemExit(f"missing validated 0.11.9 prerequisite: {marker}")

# 0.11.10: deny browser-originated runtime permission requests inside all
# protected WebViews. Banking/payment pages remain usable for normal HTTPS
# navigation while camera, microphone and other WebView permission surfaces
# fail closed instead of being delegated to the app/device.
if 'import android.webkit.PermissionRequest;' not in s:
    s = s.replace('import android.webkit.WebResourceRequest;\n', 'import android.webkit.PermissionRequest;\nimport android.webkit.WebChromeClient;\nimport android.webkit.WebResourceRequest;\n', 1)

anchor = re.compile(r'(?m)^(?P<indent>[ \t]*)ws\.setAllowContentAccess\(false\);[ \t]*$')
matches = list(anchor.finditer(s))
if not matches:
    raise SystemExit('patch failed [permission anchor]: no protected WebView settings blocks found')
expected = len(matches)

def add_permission_guard(match):
    indent = match.group('indent')
    tail = s[match.end():]
    lookahead = '\n'.join(tail.split('\n')[1:14]) if tail.startswith('\n') else ''
    if 'web.setWebChromeClient(new WebChromeClient()' in lookahead and 'request.deny();' in lookahead:
        return match.group(0)
    return (
        f"{match.group(0)}\n"
        f"{indent}web.setWebChromeClient(new WebChromeClient() {{\n"
        f"{indent}    @Override public void onPermissionRequest(PermissionRequest request) {{ request.deny(); }}\n"
        f"{indent}}});"
    )

s, _ = anchor.subn(add_permission_guard, s)
guards = s.count('onPermissionRequest(PermissionRequest request) { request.deny(); }')
if guards != expected:
    raise SystemExit(f'patch failed [permission coverage]: expected {expected} protected blocks, validated {guards}')

compat_anchor = '        content.addView(localResourceCard);'
if s.count(compat_anchor) != 1:
    raise SystemExit(f"patch failed [compatibility permission anchor]: found {s.count(compat_anchor)}")
card = '''        content.addView(localResourceCard);\n\n        LinearLayout webPermissionCard = card();\n        webPermissionCard.addView(tv(t("Protected web permissions", "مجوزهای وب محافظت‌شده"), 16, NAVY, true));\n        webPermissionCard.addView(tv(t("Browser permission requests are denied",\n                "درخواست مجوزهای مرورگر رد می‌شود"), 13, GOOD, true));\n        webPermissionCard.addView(tv(t("SafePay and Secure Browser fail closed on web-originated permission requests such as camera or microphone access. Standard HTTPS banking and payment navigation remains available.",\n                "SafePay و مرورگر امن درخواست‌های مجوز صادرشده از وب مانند دوربین یا میکروفن را به‌صورت پیش‌فرض رد می‌کنند. پیمایش عادی HTTPS بانکی و پرداخت بدون تغییر باقی می‌ماند."), 12, MUTED, false));\n        content.addView(webPermissionCard);'''
s = s.replace(compat_anchor, card, 1)

s = s.replace('0.11.9 ALPHA', '0.11.10 ALPHA')
s = s.replace('0.11.9 Alpha • versionCode 1109', '0.11.10 Alpha • versionCode 1110')
s = s.replace('0.11.9 Alpha', '0.11.10 Alpha')
s = s.replace('VARA 0.11.9 requires Android 8.0 / API 26 or newer.', 'VARA 0.11.10 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding='utf-8')

g = gradle.read_text(encoding='utf-8')
g, n1 = re.subn(r'versionCode\s+1109\b', 'versionCode 1110', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.11\.9-alpha['\"]", "versionName '0.11.10-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f'version patch failed: versionCode={n1}, versionName={n2}')
gradle.write_text(g, encoding='utf-8')

for marker in [
    'PermissionRequest',
    'request.deny()',
    'Protected web permissions',
    '0.11.10 ALPHA',
]:
    if marker not in s:
        raise SystemExit(f'missing expected marker after patch: {marker}')

print(f'VARA Security 0.11.10 web-permission hardening validated across {expected} protected WebViews')
