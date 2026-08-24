from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_069.py <android-project-root>")

root = Path(sys.argv[1])
java = root / "app/src/main/java/com/varasecurity/alpha031/MainActivity.java"
gradle = root / "app/build.gradle"
s = java.read_text(encoding="utf-8")


def rep(old: str, new: str, label: str):
    global s
    count = s.count(old)
    if count != 1:
        raise SystemExit(f"patch failed [{label}]: expected 1 match, found {count}")
    s = s.replace(old, new, 1)

# Protected-session interaction hardening. Long-press context menus are not required for payment
# or banking flows and can expose sensitive page text to clipboard/copy actions. Suppress them in
# the protected WebView while keeping normal tap, keyboard and form interactions intact.
rep(
    '        ws.setCacheMode(WebSettings.LOAD_NO_CACHE);',
    '''        ws.setCacheMode(WebSettings.LOAD_NO_CACHE);\n        web.setLongClickable(false);\n        web.setHapticFeedbackEnabled(false);\n        web.setOnLongClickListener(v -> true);''',
    "protected webview context-menu suppression",
)

# Surface the enforced interaction policy in Device Compatibility so users can understand what
# the protected session disables and why. This is informational and does not alter posture score.
rep(
    '''        content.addView(transportTrust);\n\n        Button recheck = secondary(t("Recheck compatibility", "بررسی مجدد سازگاری"));''',
    '''        content.addView(transportTrust);\n\n        LinearLayout interactionPolicy = card();\n        interactionPolicy.addView(tv(t("Protected session interaction policy", "سیاست تعامل در نشست محافظت‌شده"), 16, NAVY, true));\n        interactionPolicy.addView(tv(t("Long-press copy/context menu disabled", "کپی با لمس طولانی و منوی زمینه غیرفعال است"), 13, GOOD, true));\n        interactionPolicy.addView(tv(t("VARA suppresses long-press context actions inside SafePay and Secure Browser to reduce accidental clipboard exposure of sensitive page content. Normal taps, typing and form submission remain available.",\n                "VARA در SafePay و مرورگر امن، عملیات لمس طولانی و منوی زمینه را غیرفعال می‌کند تا احتمال انتقال ناخواسته محتوای حساس صفحه به کلیپ‌بورد کاهش یابد. لمس معمولی، تایپ و ارسال فرم همچنان فعال است."), 12, MUTED, false));\n        content.addView(interactionPolicy);\n\n        Button recheck = secondary(t("Recheck compatibility", "بررسی مجدد سازگاری"));''',
    "compatibility protected-session interaction card",
)

# Version metadata.
s = s.replace('0.6.8 ALPHA', '0.6.9 ALPHA')
s = s.replace('0.6.8 Alpha • versionCode 608', '0.6.9 Alpha • versionCode 609')
s = s.replace('0.6.8 Alpha', '0.6.9 Alpha')
s = s.replace('VARA 0.6.8 requires Android 8.0 / API 26 or newer.', 'VARA 0.6.9 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+608\b', 'versionCode 609', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.6\.8-alpha['\"]", "versionName '0.6.9-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'web.setLongClickable(false)',
    'web.setHapticFeedbackEnabled(false)',
    'web.setOnLongClickListener(v -> true)',
    'Protected session interaction policy',
    'Long-press copy/context menu disabled',
    '0.6.9 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.6.9 protected-session interaction hardening patch applied")
