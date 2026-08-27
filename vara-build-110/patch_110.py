from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_110.py <android-project-root>")

root = Path(sys.argv[1])
java = root / "app/src/main/java/com/varasecurity/alpha031/MainActivity.java"
manifest = root / "app/src/main/AndroidManifest.xml"
gradle = root / "app/build.gradle"
s = java.read_text(encoding="utf-8")

required = [
    '0.10.9 ALPHA',
    'deviceEncryptionStatus()',
    'configuredSystemProxy()',
    'Storage encryption',
]
for marker in required:
    if marker not in s:
        raise SystemExit(f"missing validated 0.10.9 prerequisite: {marker}")

helpers = r'''
    private boolean activeVpnTransportDetected() {
        try {
            android.net.ConnectivityManager cm = (android.net.ConnectivityManager)
                    getSystemService(android.content.Context.CONNECTIVITY_SERVICE);
            if (cm == null) return false;
            android.net.Network active = cm.getActiveNetwork();
            if (active == null) return false;
            android.net.NetworkCapabilities caps = cm.getNetworkCapabilities(active);
            return caps != null && caps.hasTransport(android.net.NetworkCapabilities.TRANSPORT_VPN);
        } catch (Exception ignored) {
            return false;
        }
    }

    private String activeVpnDetail() {
        if (!activeVpnTransportDetected()) {
            return t("No active VPN transport is currently detected",
                    "در حال حاضر اتصال VPN فعالی شناسایی نشد");
        }
        return t("An active VPN transport is present. Confirm that you trust the VPN provider before sensitive activity. This is a review signal, not a malware verdict.",
                "یک اتصال VPN فعال است. پیش از عملیات حساس، از قابل‌اعتماد بودن ارائه‌دهنده VPN مطمئن شوید. این فقط یک سیگنال بازبینی است و تشخیص بدافزار محسوب نمی‌شود.");
    }

'''
anchor = '    private String configuredSystemProxy() {'
if s.count(anchor) != 1:
    raise SystemExit(f"patch failed [VPN helper anchor]: found {s.count(anchor)}")
s = s.replace(anchor, helpers + anchor, 1)

count_anchor = '''        if (!deviceEncryptionSecure()) n++;
        return n;'''
if s.count(count_anchor) != 1:
    raise SystemExit(f"patch failed [audit count anchor]: found {s.count(count_anchor)}")
s = s.replace(count_anchor, '''        if (!deviceEncryptionSecure()) n++;
        if (activeVpnTransportDetected()) n++;
        return n;''', 1)

row_anchor = '''        content.addView(auditRow(
                t("Storage encryption", "رمزگذاری فضای ذخیره‌سازی"),
                deviceEncryptionDetail(),
                deviceEncryptionSecure(),
                () -> openSettings(Settings.ACTION_SECURITY_SETTINGS)));

        LinearLayout summary = card();'''
if s.count(row_anchor) != 1:
    raise SystemExit(f"patch failed [VPN audit row anchor]: found {s.count(row_anchor)}")
s = s.replace(row_anchor, '''        content.addView(auditRow(
                t("Storage encryption", "رمزگذاری فضای ذخیره‌سازی"),
                deviceEncryptionDetail(),
                deviceEncryptionSecure(),
                () -> openSettings(Settings.ACTION_SECURITY_SETTINGS)));

        boolean vpnActive = activeVpnTransportDetected();
        content.addView(auditRow(
                t("Active VPN exposure", "اتصال VPN فعال"),
                activeVpnDetail(),
                !vpnActive,
                () -> openSettings(Settings.ACTION_WIRELESS_SETTINGS)));

        LinearLayout summary = card();''', 1)

compat_anchor = '        LinearLayout backgroundIsolation = card();'
if s.count(compat_anchor) != 1:
    raise SystemExit(f"patch failed [VPN compatibility anchor]: found {s.count(compat_anchor)}")
compat_card = '''        LinearLayout vpnCard = card();
        boolean compatibilityVpn = activeVpnTransportDetected();
        vpnCard.addView(tv(t("Network trust • VPN", "اعتماد شبکه • VPN"), 16, NAVY, true));
        vpnCard.addView(tv(activeVpnDetail(), 13,
                compatibilityVpn ? WARN : GOOD, compatibilityVpn));
        vpnCard.addView(tv(t("VARA reports an active VPN as a review-only trust signal. It does not independently block SafePay and does not classify the VPN app as malware.",
                "VARA اتصال VPN فعال را فقط به‌عنوان سیگنال بازبینی اعتماد گزارش می‌کند. این مورد به‌تنهایی SafePay را مسدود نمی‌کند و برنامه VPN را بدافزار تلقی نمی‌کند."), 12, MUTED, false));
        content.addView(vpnCard);

'''
s = s.replace(compat_anchor, compat_card + compat_anchor, 1)

s = s.replace('0.10.9 ALPHA', '0.11.0 ALPHA')
s = s.replace('0.10.9 Alpha • versionCode 1009', '0.11.0 Alpha • versionCode 1100')
s = s.replace('0.10.9 Alpha', '0.11.0 Alpha')
s = s.replace('VARA 0.10.9 requires Android 8.0 / API 26 or newer.', 'VARA 0.11.0 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

m = manifest.read_text(encoding="utf-8")
perm = '    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />\n'
if 'android.permission.ACCESS_NETWORK_STATE' not in m:
    internet = '    <uses-permission android:name="android.permission.INTERNET" />\n'
    if m.count(internet) != 1:
        raise SystemExit("manifest INTERNET permission anchor not found exactly once")
    m = m.replace(internet, internet + perm, 1)
manifest.write_text(m, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+1009\b', 'versionCode 1100', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.10\.9-alpha['\"]", "versionName '0.11.0-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'activeVpnTransportDetected()',
    'activeVpnDetail()',
    'Active VPN exposure',
    'Network trust • VPN',
    'TRANSPORT_VPN',
    'review-only trust signal',
    '0.11.0 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")
if 'android.permission.ACCESS_NETWORK_STATE' not in m:
    raise SystemExit('missing ACCESS_NETWORK_STATE after manifest patch')

print("VARA Security 0.11.0 active VPN trust audit patch applied")
