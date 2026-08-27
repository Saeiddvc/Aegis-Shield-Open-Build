from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_068.py <android-project-root>")

root = Path(sys.argv[1])
java = root / "app/src/main/java/com/varasecurity/alpha031/MainActivity.java"
gradle = root / "app/build.gradle"
manifest = root / "app/src/main/AndroidManifest.xml"
xml_dir = root / "app/src/main/res/xml"
s = java.read_text(encoding="utf-8")


def rep(old: str, new: str, label: str):
    global s
    count = s.count(old)
    if count != 1:
        raise SystemExit(f"patch failed [{label}]: expected 1 match, found {count}")
    s = s.replace(old, new, 1)

# Transport trust hardening: explicitly trust only Android system roots for app HTTPS.
# This keeps user-added CA certificates out of VARA's WebView trust store while preserving
# normal banking/payment certificates anchored in the platform system store.
m = manifest.read_text(encoding="utf-8")
old_manifest = '        android:label="VARA Security"\n        android:theme="@style/AppTheme"\n        android:usesCleartextTraffic="false">'
new_manifest = '        android:label="VARA Security"\n        android:networkSecurityConfig="@xml/network_security_config"\n        android:theme="@style/AppTheme"\n        android:usesCleartextTraffic="false">'
if m.count(old_manifest) != 1:
    raise SystemExit(f"manifest patch failed: expected 1 app policy match, found {m.count(old_manifest)}")
m = m.replace(old_manifest, new_manifest, 1)
manifest.write_text(m, encoding="utf-8")
xml_dir.mkdir(parents=True, exist_ok=True)
network_config = xml_dir / "network_security_config.xml"
network_config.write_text('''<?xml version="1.0" encoding="utf-8"?>\n<network-security-config>\n    <base-config cleartextTrafficPermitted="false">\n        <trust-anchors>\n            <certificates src="system" />\n        </trust-anchors>\n    </base-config>\n</network-security-config>\n''', encoding="utf-8")

# Surface the enforced transport policy in Device Compatibility. This is a build-enforced
# property, not a dynamic risk score, so it remains informational and does not inflate posture.
rep(
    '''        content.addView(notifications);\n\n        Button recheck = secondary(t("Recheck compatibility", "بررسی مجدد سازگاری"));''',
    '''        content.addView(notifications);\n\n        LinearLayout transportTrust = card();\n        transportTrust.addView(tv(t("Transport trust policy", "سیاست اعتماد ارتباط امن"), 16, NAVY, true));\n        transportTrust.addView(tv(t("System CA store only", "فقط گواهی‌های مورد اعتماد سیستم"), 13, GOOD, true));\n        transportTrust.addView(tv(t("VARA does not opt in to user-installed certificate authorities. Cleartext traffic remains disabled and WebView TLS errors fail closed.",\n                "VARA گواهی‌های نصب‌شده توسط کاربر را به‌عنوان مرجع اعتماد فعال نمی‌کند. ارتباط بدون TLS همچنان غیرفعال است و خطای TLS در WebView باعث توقف امن نشست می‌شود."), 12, MUTED, false));\n        content.addView(transportTrust);\n\n        Button recheck = secondary(t("Recheck compatibility", "بررسی مجدد سازگاری"));''',
    "compatibility transport trust card",
)

# Version metadata.
s = s.replace('0.6.7 ALPHA', '0.6.8 ALPHA')
s = s.replace('0.6.7 Alpha • versionCode 607', '0.6.8 Alpha • versionCode 608')
s = s.replace('0.6.7 Alpha', '0.6.8 Alpha')
s = s.replace('VARA 0.6.7 requires Android 8.0 / API 26 or newer.', 'VARA 0.6.8 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+607\b', 'versionCode 608', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.6\.7-alpha['\"]", "versionName '0.6.8-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'Transport trust policy',
    'System CA store only',
    'user-installed certificate authorities',
    '0.6.8 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")
if '@xml/network_security_config' not in m:
    raise SystemExit('network security config not attached to application')
if '<certificates src="system" />' not in network_config.read_text(encoding='utf-8'):
    raise SystemExit('system-only trust anchor marker missing')

print("VARA Security 0.6.8 transport trust hardening patch applied")
