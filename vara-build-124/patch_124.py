from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_124.py <android-project-root>")

root = Path(sys.argv[1])
java = root / "app/src/main/java/com/varasecurity/alpha031/MainActivity.java"
gradle = root / "app/build.gradle"
s = java.read_text(encoding="utf-8")

for marker in [
    '0.11.13 ALPHA',
    'Protected form privacy',
    'setImportantForAutofill(View.IMPORTANT_FOR_AUTOFILL_NO_EXCLUDE_DESCENDANTS)',
    'onPermissionRequest(PermissionRequest request)',
    'request.deny()',
    'onShowFileChooser(WebView webView, ValueCallback<Uri[]>',
]:
    if marker not in s:
        raise SystemExit(f"missing validated 0.11.13 prerequisite: {marker}")

# 0.11.14: protected SafePay / Secure Browser WebViews reject native HTTP-auth
# and client-certificate prompts. These browser-level credential surfaces bypass
# normal HTML form controls and can expose credentials or client identity. Protected
# mode remains HTTPS-only and consumer-payment oriented, so fail closed here.
chooser = re.compile(
    r'@Override public boolean onShowFileChooser\(WebView webView, ValueCallback<Uri\[\]> filePathCallback, WebChromeClient\.FileChooserParams fileChooserParams\) \{\s*'
    r'filePathCallback\.onReceiveValue\(null\);\s*return true;\s*\}'
)
expected = len(list(chooser.finditer(s)))
if expected < 1:
    raise SystemExit('patch failed [auth prompt anchor]: no protected file-chooser guards found')

perm = re.compile(
    r'@Override public void onPermissionRequest\(PermissionRequest request\) \{\s*request\.deny\(\);\s*\}'
)
perm_matches = list(perm.finditer(s))
if len(perm_matches) != expected:
    raise SystemExit(
        f'patch failed [auth prompt coverage]: expected {expected} protected permission guards, found {len(perm_matches)}'
    )

if 'onReceivedHttpAuthRequest(WebView view, android.webkit.HttpAuthHandler handler' in s or \
   'onReceivedClientCertRequest(WebView view, android.webkit.ClientCertRequest request)' in s:
    raise SystemExit('patch failed [auth prompt mutation]: protected auth prompt guard already present')

replacement = '''@Override public void onPermissionRequest(PermissionRequest request) { request.deny(); }
            @Override public void onReceivedHttpAuthRequest(WebView view, android.webkit.HttpAuthHandler handler, String host, String realm) {
                handler.cancel();
            }
            @Override public void onReceivedClientCertRequest(WebView view, android.webkit.ClientCertRequest request) {
                request.cancel();
            }'''
s, changed = perm.subn(replacement, s)
if changed != expected:
    raise SystemExit(f'patch failed [auth prompt mutation]: expected {expected}, changed {changed}')

http_count = s.count('onReceivedHttpAuthRequest(WebView view, android.webkit.HttpAuthHandler handler, String host, String realm)')
cert_count = s.count('onReceivedClientCertRequest(WebView view, android.webkit.ClientCertRequest request)')
if http_count != expected or cert_count != expected:
    raise SystemExit(
        f'patch failed [auth prompt verify]: HTTP auth={http_count}, client cert={cert_count}, expected={expected}'
    )
if s.count('handler.cancel();') < expected or s.count('request.cancel();') < expected:
    raise SystemExit('patch failed [auth prompt verify]: cancel action missing')

compat_anchor = '        content.addView(autofillCard);'
if s.count(compat_anchor) != 1:
    raise SystemExit(f"patch failed [compatibility auth anchor]: found {s.count(compat_anchor)}")
card = '''        content.addView(autofillCard);\n\n        LinearLayout authPromptCard = card();\n        authPromptCard.addView(tv(t("Protected authentication prompts", "درخواست‌های احراز هویت محافظت‌شده"), 16, NAVY, true));\n        authPromptCard.addView(tv(t("HTTP auth and client-certificate prompts are blocked",\n                "درخواست احراز هویت HTTP و گواهی کاربر مسدود است"), 13, GOOD, true));\n        authPromptCard.addView(tv(t("SafePay and Secure Browser reject browser-native HTTP authentication and client-certificate requests. Standard HTTPS form sign-in and payment flows remain available; enterprise sites that require HTTP Basic/Digest authentication or mutual TLS are intentionally unsupported in Protected Session.",\n                "SafePay و مرورگر امن، درخواست‌های احراز هویت بومی مرورگر و گواهی کاربر را رد می‌کنند. ورود و پرداخت استاندارد مبتنی بر فرم HTTPS همچنان در دسترس است؛ سایت‌های سازمانی وابسته به HTTP Basic/Digest یا mutual TLS عمداً در Protected Session پشتیبانی نمی‌شوند."), 12, MUTED, false));\n        content.addView(authPromptCard);'''
s = s.replace(compat_anchor, card, 1)

s = s.replace('0.11.13 ALPHA', '0.11.14 ALPHA')
s = s.replace('0.11.13 Alpha • versionCode 1113', '0.11.14 Alpha • versionCode 1114')
s = s.replace('0.11.13 Alpha', '0.11.14 Alpha')
s = s.replace('VARA 0.11.13 requires Android 8.0 / API 26 or newer.', 'VARA 0.11.14 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding='utf-8')

g = gradle.read_text(encoding='utf-8')
g, n1 = re.subn(r'versionCode\s+1113\b', 'versionCode 1114', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.11\.13-alpha['\"]", "versionName '0.11.14-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f'version patch failed: versionCode={n1}, versionName={n2}')
gradle.write_text(g, encoding='utf-8')

for marker in [
    'Protected authentication prompts',
    'onReceivedHttpAuthRequest(WebView view, android.webkit.HttpAuthHandler handler',
    'onReceivedClientCertRequest(WebView view, android.webkit.ClientCertRequest request)',
    'handler.cancel();',
    'request.cancel();',
    '0.11.14 ALPHA',
]:
    if marker not in s:
        raise SystemExit(f'missing expected marker after patch: {marker}')

print(
    f'VARA Security 0.11.14 protected authentication-prompt hardening validated across {expected} protected WebViews'
)
