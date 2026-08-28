from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_119.py <android-project-root>")

root = Path(sys.argv[1])
java = root / "app/src/main/java/com/varasecurity/alpha031/MainActivity.java"
gradle = root / "app/build.gradle"
s = java.read_text(encoding="utf-8")

for marker in [
    '0.11.8 ALPHA',
    'setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW)',
    'HTTPS mixed-content protection',
    'Protected WebView isolation',
]:
    if marker not in s:
        raise SystemExit(f"missing validated 0.11.8 prerequisite: {marker}")

# 0.11.9: deny protected WebViews direct access to local file:// and
# content:// resources. Remote HTTPS banking/payment flows do not require
# these Android-local resource surfaces, and blocking them narrows exposure
# to local-file/content-provider bridging attacks.
pattern = re.compile(
    r'(?m)^(?P<indent>[ \t]*)ws\.setMixedContentMode\(WebSettings\.MIXED_CONTENT_NEVER_ALLOW\);[ \t]*$'
)
matches = list(pattern.finditer(s))
if not matches:
    raise SystemExit("patch failed [local-resource anchor]: no protected WebView settings blocks found")
expected_blocks = len(matches)

def harden_local_resources(match):
    indent = match.group('indent')
    tail = s[match.end():]
    lookahead = '\n'.join(tail.split('\n')[1:4]) if tail.startswith('\n') else ''
    if (
        'ws.setAllowFileAccess(false);' in lookahead
        and 'ws.setAllowContentAccess(false);' in lookahead
    ):
        return match.group(0)
    return (
        f"{indent}ws.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);\n"
        f"{indent}ws.setAllowFileAccess(false);\n"
        f"{indent}ws.setAllowContentAccess(false);"
    )

s, _ = pattern.subn(harden_local_resources, s)
paired_pattern = re.compile(
    r'(?m)^[ \t]*ws\.setMixedContentMode\(WebSettings\.MIXED_CONTENT_NEVER_ALLOW\);[ \t]*\n'
    r'[ \t]*ws\.setAllowFileAccess\(false\);[ \t]*\n'
    r'[ \t]*ws\.setAllowContentAccess\(false\);[ \t]*$'
)
paired_blocks = len(list(paired_pattern.finditer(s)))
if paired_blocks != expected_blocks:
    raise SystemExit(
        f"patch failed [local-resource coverage]: expected {expected_blocks} protected blocks, validated {paired_blocks}"
    )

compat_anchor = '        content.addView(mixedContentCard);'
if s.count(compat_anchor) != 1:
    raise SystemExit(f"patch failed [compatibility local-resource anchor]: found {s.count(compat_anchor)}")
card = '''        content.addView(mixedContentCard);\n\n        LinearLayout localResourceCard = card();\n        localResourceCard.addView(tv(t("Protected local-resource boundary", "مرزبندی منابع محلی محافظت‌شده"), 16, NAVY, true));\n        localResourceCard.addView(tv(t("Local file and content-provider access blocked",\n                "دسترسی مستقیم به فایل محلی و Content Provider مسدود است"), 13, GOOD, true));\n        localResourceCard.addView(tv(t("SafePay and Secure Browser cannot directly read file:// or content:// resources. Normal HTTPS banking and payment flows remain available while Android-local resource bridging is disabled.",\n                "SafePay و مرورگر امن امکان خواندن مستقیم منابع file:// یا content:// را ندارند. جریان عادی بانکی و پرداخت HTTPS حفظ می‌شود و پل دسترسی به منابع محلی اندروید غیرفعال است."), 12, MUTED, false));\n        content.addView(localResourceCard);'''
s = s.replace(compat_anchor, card, 1)

s = s.replace('0.11.8 ALPHA', '0.11.9 ALPHA')
s = s.replace('0.11.8 Alpha • versionCode 1108', '0.11.9 Alpha • versionCode 1109')
s = s.replace('0.11.8 Alpha', '0.11.9 Alpha')
s = s.replace('VARA 0.11.8 requires Android 8.0 / API 26 or newer.', 'VARA 0.11.9 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+1108\b', 'versionCode 1109', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.11\.8-alpha['\"]", "versionName '0.11.9-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

for marker in [
    'setAllowFileAccess(false)',
    'setAllowContentAccess(false)',
    'Protected local-resource boundary',
    '0.11.9 ALPHA',
]:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print(
    f"VARA Security 0.11.9 local-resource hardening validated across {expected_blocks} protected settings blocks"
)
