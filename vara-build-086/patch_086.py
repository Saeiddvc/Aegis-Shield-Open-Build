from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_086.py <android-project-root>")

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

# 0.8.6: tighten protected destination canonicalization further.
# Reject whitespace/control-character ambiguity and malformed dotted hostnames before load.
rep(
    '''            String userInfo = u.getUserInfo();
            if (userInfo != null && !userInfo.isEmpty()) return null;
            if (u.toString().contains("\\\\")) return null;
            int port = u.getPort();''',
    '''            String userInfo = u.getUserInfo();
            if (userInfo != null && !userInfo.isEmpty()) return null;
            String rawUrl = u.toString();
            for (int i = 0; i < rawUrl.length(); i++) {
                char c = rawUrl.charAt(i);
                if (Character.isISOControl(c) || Character.isWhitespace(c)) return null;
            }
            if (rawUrl.contains("\\\\")) return null;
            if (host.startsWith(".") || host.endsWith(".") || host.contains("..")) return null;
            int port = u.getPort();''',
    "reject whitespace/control and malformed dotted hostnames",
)

rep(
    'hero.addView(tv(t("VARA requires HTTPS on the standard secure port and blocks IP, internationalized/punycode hostnames, embedded URL credentials and ambiguous backslash URLs before protected browsing.", "VARA فقط HTTPS روی درگاه امن استاندارد را می‌پذیرد و پیش از مرور محافظت‌شده، مقصدهای IP، دامنه‌های بین‌المللی/punycode، اطلاعات کاربری داخل نشانی و URLهای مبهم دارای بک‌اسلش را مسدود می‌کند."), 13, Color.rgb(220,236,239), false));',
    'hero.addView(tv(t("VARA requires HTTPS on the standard secure port and blocks IP, internationalized/punycode hostnames, embedded URL credentials, ambiguous backslashes, whitespace/control characters and malformed dotted hostnames before protected browsing.", "VARA فقط HTTPS روی درگاه امن استاندارد را می‌پذیرد و پیش از مرور محافظت‌شده، مقصدهای IP، دامنه‌های بین‌المللی/punycode، اطلاعات کاربری داخل نشانی، بک‌اسلش مبهم، نویسه‌های فاصله/کنترلی و دامنه‌های نقطه‌گذاری‌شده نامعتبر را مسدود می‌کند."), 13, Color.rgb(220,236,239), false));',
    "SafePay destination policy copy",
)

rep(
    'Toast.makeText(this, t("Enter a standard HTTPS domain without IP, custom port, internationalized hostname, embedded credentials or backslashes", "یک دامنه استاندارد HTTPS وارد کنید؛ IP، درگاه سفارشی، دامنه بین‌المللی، اطلاعات کاربری داخل URL و بک‌اسلش مجاز نیست"), Toast.LENGTH_LONG).show();',
    'Toast.makeText(this, t("Enter a canonical HTTPS domain without IP, custom port, internationalized hostname, embedded credentials, backslashes, whitespace/control characters or malformed dot labels", "یک دامنه canonical و استاندارد HTTPS وارد کنید؛ IP، درگاه سفارشی، دامنه بین‌المللی، اطلاعات کاربری داخل URL، بک‌اسلش، نویسه‌های فاصله/کنترلی و برچسب‌های نقطه‌ای نامعتبر مجاز نیست"), Toast.LENGTH_LONG).show();',
    "SafePay validation message",
)

rep(
    'destination.addView(tv(t("HTTPS only • standard port 443 • no IP literals • no internationalized/punycode hostnames • no URL credentials • no backslash ambiguity", "فقط HTTPS • درگاه استاندارد 443 • بدون IP • بدون دامنه بین‌المللی/punycode • بدون اطلاعات کاربری در URL • بدون ابهام بک‌اسلش"), 12, MUTED, false));',
    'destination.addView(tv(t("HTTPS only • port 443 • no IP/punycode • no URL credentials • no backslash/whitespace/control ambiguity • canonical dotted hostname", "فقط HTTPS • درگاه 443 • بدون IP/punycode • بدون اطلاعات کاربری در URL • بدون ابهام بک‌اسلش/فاصله/نویسه کنترلی • دامنه نقطه‌ای canonical"), 12, MUTED, false));',
    "compatibility destination policy",
)

# Version metadata.
s = s.replace('0.8.5 ALPHA', '0.8.6 ALPHA')
s = s.replace('0.8.5 Alpha • versionCode 805', '0.8.6 Alpha • versionCode 806')
s = s.replace('0.8.5 Alpha', '0.8.6 Alpha')
s = s.replace('VARA 0.8.5 requires Android 8.0 / API 26 or newer.', 'VARA 0.8.6 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+805\b', 'versionCode 806', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.8\.5-alpha['\"]", "versionName '0.8.6-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'Character.isISOControl(c)',
    'Character.isWhitespace(c)',
    'host.startsWith(".")',
    'host.endsWith(".")',
    'host.contains("..")',
    'canonical HTTPS domain',
    '0.8.6 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.8.6 protected destination canonicalization hardening patch applied")
