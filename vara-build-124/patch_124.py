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
    'onSafeBrowsingHit',
]:
    if marker not in s:
        raise SystemExit(f"missing validated 0.11.13 prerequisite: {marker}")

chooser = re.compile(
    r'@Override public boolean onShowFileChooser\(WebView webView, ValueCallback<Uri\[\]> filePathCallback, WebChromeClient\.FileChooserParams fileChooserParams\) \{\s*'
    r'filePathCallback\.onReceiveValue\(null\);\s*return true;\s*\}'
)
chooser_matches = list(chooser.finditer(s))
if not chooser_matches:
    raise SystemExit('patch failed [auth prompt anchor]: no protected file-chooser guards found')
expected = len(chooser_matches)

chrome_start = re.compile(
    r'(?P<receiver>[A-Za-z_][A-Za-z0-9_]*)\.setWebChromeClient\(new WebChromeClient\(\)\s*\{'
)

def matching_brace(text, open_pos):
    depth = 0
    i = open_pos
    state = 'code'
    while i < len(text):
        c = text[i]
        n = text[i + 1] if i + 1 < len(text) else ''
        if state == 'code':
            if c == '"':
                state = 'string'
            elif c == "'":
                state = 'char'
            elif c == '/' and n == '/':
                state = 'line_comment'; i += 1
            elif c == '/' and n == '*':
                state = 'block_comment'; i += 1
            elif c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    return i
        elif state == 'string':
            if c == '\\':
                i += 1
            elif c == '"':
                state = 'code'
        elif state == 'char':
            if c == '\\':
                i += 1
            elif c == "'":
                state = 'code'
        elif state == 'line_comment':
            if c == '\n':
                state = 'code'
        elif state == 'block_comment':
            if c == '*' and n == '/':
                state = 'code'; i += 1
        i += 1
    raise SystemExit('patch failed [auth prompt parser]: unterminated anonymous client block')

# Resolve each protected chooser back to its owning WebChromeClient first.
protected = []
for ordinal, cm in enumerate(chooser_matches, start=1):
    chrome_candidates = list(chrome_start.finditer(s, 0, cm.start()))
    if not chrome_candidates:
        raise SystemExit(f'patch failed [auth prompt client {ordinal}]: protected WebChromeClient not found')
    chrome = chrome_candidates[-1]
    if cm.start() - chrome.start() > 12000:
        raise SystemExit(f'patch failed [auth prompt client {ordinal}]: chooser too far from WebChromeClient')
    protected.append((cm, chrome, chrome.group('receiver')))

insertions = []
covered_existing = 0
resolved = []
selected_view_clients = set()

for ordinal, (_cm, chrome, receiver) in enumerate(protected, start=1):
    view_client_start = re.compile(
        rf'\b{re.escape(receiver)}\.setWebViewClient\(new WebViewClient\(\)\s*\{{'
    )
    view_candidates = list(view_client_start.finditer(s))
    if not view_candidates:
        raise SystemExit(
            f'patch failed [auth prompt WebViewClient {ordinal}]: no WebViewClient for {receiver}'
        )

    # Match each protected WebChromeClient to the nearest still-unassigned WebViewClient
    # for the same receiver. Do not use an arbitrary byte-distance cutoff: the generated
    # MainActivity has long anonymous client bodies, and source ordering legitimately
    # differs between protected flows. Uniqueness prevents one local `web` client from
    # being accidentally reused for another protected flow.
    ranked = sorted(view_candidates, key=lambda m: abs(m.start() - chrome.start()))
    vc = next((c for c in ranked if c.start() not in selected_view_clients), None)
    if vc is None:
        raise SystemExit(
            f'patch failed [auth prompt WebViewClient {ordinal}]: no unique WebViewClient for {receiver}; '
            f'candidates={len(view_candidates)}, already-selected={len(selected_view_clients)}'
        )
    selected_view_clients.add(vc.start())

    open_pos = s.find('{', vc.start(), vc.end())
    close_pos = matching_brace(s, open_pos)
    block = s[vc.start():close_pos + 1]

    has_http = (
        'onReceivedHttpAuthRequest(WebView view, android.webkit.HttpAuthHandler handler, String host, String realm)'
        in block
    )
    has_cert = (
        'onReceivedClientCertRequest(WebView view, android.webkit.ClientCertRequest request)'
        in block
    )

    if has_http and has_cert:
        covered_existing += 1
        resolved.append(receiver)
        continue
    if has_http != has_cert:
        raise SystemExit(
            f'patch failed [auth prompt partial guard {ordinal}]: inconsistent existing guard for {receiver}'
        )

    line_start = s.rfind('\n', 0, close_pos) + 1
    close_indent = s[line_start:close_pos]
    method_indent = close_indent + '    '
    guard = (
        f"\n{method_indent}@Override public void onReceivedHttpAuthRequest(WebView view, android.webkit.HttpAuthHandler handler, String host, String realm) {{\n"
        f"{method_indent}    handler.cancel();\n"
        f"{method_indent}}}\n"
        f"{method_indent}@Override public void onReceivedClientCertRequest(WebView view, android.webkit.ClientCertRequest request) {{\n"
        f"{method_indent}    request.cancel();\n"
        f"{method_indent}}}\n{close_indent}"
    )
    insertions.append((close_pos, guard, receiver))
    resolved.append(receiver)

positions = [p for p, _g, _r in insertions]
if len(set(positions)) != len(positions):
    raise SystemExit(
        f'patch failed [auth prompt mutation]: duplicate WebViewClient insertion positions '
        f'({len(set(positions))}/{len(positions)})'
    )
if covered_existing + len(insertions) != expected:
    raise SystemExit(
        f'patch failed [auth prompt mutation]: expected {expected}, covered {covered_existing} + {len(insertions)}'
    )

for pos, guard, _receiver in sorted(insertions, reverse=True):
    s = s[:pos] + guard + s[pos:]

http_count = s.count(
    'onReceivedHttpAuthRequest(WebView view, android.webkit.HttpAuthHandler handler, String host, String realm)'
)
cert_count = s.count(
    'onReceivedClientCertRequest(WebView view, android.webkit.ClientCertRequest request)'
)
if http_count < expected or cert_count < expected:
    raise SystemExit(
        f'patch failed [auth prompt verify]: HTTP auth={http_count}, client cert={cert_count}, expected at least {expected}'
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
s = s.replace(
    'VARA 0.11.13 requires Android 8.0 / API 26 or newer.',
    'VARA 0.11.14 requires Android 8.0 / API 26 or newer.'
)
java.write_text(s, encoding='utf-8')

g = gradle.read_text(encoding='utf-8')
g, n1 = re.subn(r'versionCode\s+1113\b', 'versionCode 1114', g, count=1)
g, n2 = re.subn(
    r"versionName\s+['\"]0\.11\.13-alpha['\"]",
    "versionName '0.11.14-alpha'",
    g,
    count=1,
)
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
    f'VARA Security 0.11.14 protected authentication-prompt hardening validated across {expected} protected WebViews: '
    f'{", ".join(resolved)}; preserved {covered_existing} existing guards, added {len(insertions)} guards'
)
