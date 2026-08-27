from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_084.py <android-project-root>")

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

# 0.8.4: expose an explicitly configured system HTTP/HTTPS proxy as an
# actionable device-trust signal. Proxies can be legitimate (enterprise,
# debugging or parental-control use), so VARA reports the condition for review
# and does not independently classify it as malware or block SafePay.
proxy_helpers = r'''
    private String configuredSystemProxy() {
        String host = null;
        int port = -1;
        try {
            host = android.net.Proxy.getDefaultHost();
            port = android.net.Proxy.getDefaultPort();
        } catch (Exception ignored) {}
        if (host == null || host.trim().isEmpty()) {
            String httpsHost = System.getProperty("https.proxyHost");
            String httpHost = System.getProperty("http.proxyHost");
            host = (httpsHost != null && !httpsHost.trim().isEmpty()) ? httpsHost : httpHost;
            String portValue = System.getProperty(
                    (httpsHost != null && !httpsHost.trim().isEmpty()) ? "https.proxyPort" : "http.proxyPort");
            if (portValue != null) {
                try { port = Integer.parseInt(portValue.trim()); } catch (Exception ignored) {}
            }
        }
        if (host == null || host.trim().isEmpty()) return null;
        host = host.trim();
        return port > 0 ? host + ":" + port : host;
    }

    private String proxyExposureDetail(String proxy) {
        if (proxy == null || proxy.isEmpty()) {
            return t("No explicit system HTTP/HTTPS proxy was detected",
                    "هیچ پراکسی صریح HTTP/HTTPS در سطح سیستم شناسایی نشد");
        }
        return t("A system proxy is configured (" + proxy + "). Verify that it is intentional and trusted before sensitive browsing or payment activity.",
                "یک پراکسی سیستمی تنظیم شده است (" + proxy + "). پیش از مرور حساس یا پرداخت، مطمئن شوید این تنظیم عمدی و قابل اعتماد است.");
    }

'''
rep(
    '    private String recommendedActionTitle(int deviceIssues, int appFindings) {',
    proxy_helpers + '    private String recommendedActionTitle(int deviceIssues, int appFindings) {',
    "system proxy exposure helpers",
)

rep(
    '''        if (!thirdPartySmsAccessApps().isEmpty()) n++;
        if (enabledThirdPartyAutofillService() != null) n++;
        return n;''',
    '''        if (!thirdPartySmsAccessApps().isEmpty()) n++;
        if (enabledThirdPartyAutofillService() != null) n++;
        if (configuredSystemProxy() != null) n++;
        return n;''',
    "system proxy exposure in device trust score",
)

rep(
    '''        String autofillProvider = enabledThirdPartyAutofillService();
        content.addView(auditRow(
                t("Autofill service exposure", "دسترسی سرویس تکمیل خودکار"),
                autofillExposureDetail(autofillProvider),
                autofillProvider == null,
                () -> openSettings(Settings.ACTION_SETTINGS)));

        LinearLayout summary = card();''',
    '''        String autofillProvider = enabledThirdPartyAutofillService();
        content.addView(auditRow(
                t("Autofill service exposure", "دسترسی سرویس تکمیل خودکار"),
                autofillExposureDetail(autofillProvider),
                autofillProvider == null,
                () -> openSettings(Settings.ACTION_SETTINGS)));

        String configuredProxy = configuredSystemProxy();
        content.addView(auditRow(
                t("System proxy exposure", "پراکسی سیستمی"),
                proxyExposureDetail(configuredProxy),
                configuredProxy == null,
                () -> openSettings(Settings.ACTION_WIFI_SETTINGS)));

        LinearLayout summary = card();''',
    "actionable system proxy audit row",
)

rep(
    '''        content.addView(autofillExposure);

        LinearLayout backgroundIsolation = card();''',
    '''        content.addView(autofillExposure);

        LinearLayout proxyExposure = card();
        String compatibilityProxy = configuredSystemProxy();
        proxyExposure.addView(tv(t("System proxy exposure", "پراکسی سیستمی"), 16, NAVY, true));
        proxyExposure.addView(tv(proxyExposureDetail(compatibilityProxy), 13,
                compatibilityProxy == null ? GOOD : WARN, compatibilityProxy != null));
        proxyExposure.addView(tv(t("This is an advisory trust signal. Enterprise or debugging proxies can be legitimate. VARA does not treat a configured proxy alone as malware evidence or an automatic SafePay blocker.",
                "این مورد یک سیگنال بازبینی اعتماد است. پراکسی‌های سازمانی یا عیب‌یابی می‌توانند کاملاً معتبر باشند. VARA صرف تنظیم بودن پراکسی را نشانه بدافزار یا دلیل مسدودشدن خودکار SafePay تلقی نمی‌کند."), 12, MUTED, false));
        content.addView(proxyExposure);

        LinearLayout backgroundIsolation = card();''',
    "compatibility system proxy exposure card",
)

# Version metadata.
s = s.replace('0.8.3 ALPHA', '0.8.4 ALPHA')
s = s.replace('0.8.3 Alpha • versionCode 803', '0.8.4 Alpha • versionCode 804')
s = s.replace('0.8.3 Alpha', '0.8.4 Alpha')
s = s.replace('VARA 0.8.3 requires Android 8.0 / API 26 or newer.', 'VARA 0.8.4 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+803\b', 'versionCode 804', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.8\.3-alpha['\"]", "versionName '0.8.4-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'configuredSystemProxy()',
    'proxyExposureDetail(',
    'System proxy exposure',
    'Settings.ACTION_WIFI_SETTINGS',
    'https.proxyHost',
    'automatic SafePay blocker',
    '0.8.4 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.8.4 system proxy exposure audit patch applied")
