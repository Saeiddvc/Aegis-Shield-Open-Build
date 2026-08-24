from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_071.py <android-project-root>")

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

# Protected destinations are payment-sensitive. Require a conventional HTTPS origin,
# reject non-default ports and reject internationalized/punycode hostnames to reduce
# homograph ambiguity in the in-app browser. This intentionally trades some IDN
# compatibility for a narrower trust surface in SafePay/Secure Browser.
rep(
    '''    private String normalizeHttps(String raw) {
        try {
            String s = raw == null ? "" : raw.trim();
            if (!s.startsWith("https://")) return null;
            Uri u = Uri.parse(s);
            String host = u.getHost();
            if (host == null || host.length() < 4 || !host.contains(".")) return null;
            if (u.getUserInfo() != null) return null;
            if (host.matches("^[0-9a-fA-F:.]+$")) return null;
            return u.toString();
        } catch (Exception e) { return null; }
    }''',
    '''    private String normalizeHttps(String raw) {
        try {
            String s = raw == null ? "" : raw.trim();
            if (!s.startsWith("https://")) return null;
            Uri u = Uri.parse(s);
            String host = u.getHost();
            if (host == null || host.length() < 4 || !host.contains(".")) return null;
            if (u.getUserInfo() != null) return null;
            if (host.matches("^[0-9a-fA-F:.]+$")) return null;
            int port = u.getPort();
            if (port != -1 && port != 443) return null;
            String asciiHost = java.net.IDN.toASCII(host, java.net.IDN.USE_STD3_ASCII_RULES).toLowerCase(Locale.ROOT);
            if (!asciiHost.equals(host.toLowerCase(Locale.ROOT)) || asciiHost.contains("xn--")) return null;
            if (asciiHost.startsWith(".") || asciiHost.endsWith(".") || asciiHost.contains("..")) return null;
            return u.toString();
        } catch (Exception e) { return null; }
    }''',
    "protected destination policy",
)

# Make the stricter policy visible before a protected session begins.
rep(
    'hero.addView(tv(t("VARA validates the address, requires HTTPS, blocks IP-address destinations, and opens it inside the hardened browser.", "VARA نشانی را اعتبارسنجی می‌کند، HTTPS را الزامی می‌داند، مقصدهای مبتنی بر IP را رد می‌کند و صفحه را در مرورگر سخت‌گیرانه باز می‌کند."), 13, Color.rgb(220,236,239), false));',
    'hero.addView(tv(t("VARA requires HTTPS on the standard secure port, blocks IP and internationalized/punycode hostnames, and opens the destination inside the hardened browser.", "VARA فقط HTTPS روی درگاه امن استاندارد را می‌پذیرد، مقصدهای IP و دامنه‌های بین‌المللی/punycode را مسدود می‌کند و صفحه را در مرورگر سخت‌گیرانه باز می‌کند."), 13, Color.rgb(220,236,239), false));',
    "SafePay destination policy copy",
)

rep(
    'Toast.makeText(this, t("Enter a valid HTTPS domain, not an IP address", "یک دامنه معتبر HTTPS وارد کنید؛ نشانی IP مجاز نیست"), Toast.LENGTH_LONG).show();',
    'Toast.makeText(this, t("Enter a standard HTTPS domain without an IP address, custom port or internationalized hostname", "یک دامنه استاندارد HTTPS وارد کنید؛ IP، درگاه سفارشی و دامنه بین‌المللی مجاز نیست"), Toast.LENGTH_LONG).show();',
    "SafePay validation message",
)

# Surface the destination-trust contract in Device Compatibility so users can understand
# why some otherwise valid URLs are refused in protected mode.
rep(
    '        Button recheck = secondary(t("Recheck compatibility", "بررسی مجدد سازگاری"));',
    '''        LinearLayout destination = card();
        destination.addView(tv(t("Protected destination policy", "سیاست مقصد محافظت‌شده"), 16, NAVY, true));
        destination.addView(tv(t("HTTPS only • standard port 443 • no IP literals • no internationalized/punycode hostnames", "فقط HTTPS • درگاه استاندارد 443 • بدون IP • بدون دامنه بین‌المللی/punycode"), 12, MUTED, false));
        destination.addView(tv(t("This narrower policy reduces ambiguous or deceptive payment destinations.", "این سیاست محدودتر، ریسک مقصدهای مبهم یا فریبنده در پرداخت را کاهش می‌دهد."), 12, MUTED, false));
        content.addView(destination);

        Button recheck = secondary(t("Recheck compatibility", "بررسی مجدد سازگاری"));''',
    "compatibility destination policy",
)

# Version metadata.
s = s.replace('0.7.0 ALPHA', '0.7.1 ALPHA')
s = s.replace('0.7.0 Alpha • versionCode 700', '0.7.1 Alpha • versionCode 701')
s = s.replace('0.7.0 Alpha', '0.7.1 Alpha')
s = s.replace('VARA 0.7.0 requires Android 8.0 / API 26 or newer.', 'VARA 0.7.1 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+700\b', 'versionCode 701', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.7\.0-alpha['\"]", "versionName '0.7.1-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'java.net.IDN.toASCII',
    'port != -1 && port != 443',
    'asciiHost.contains("xn--")',
    'Protected destination policy',
    '0.7.1 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.7.1 protected-destination hardening patch applied")
