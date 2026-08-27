from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_112.py <android-project-root>")

root = Path(sys.argv[1])
java = root / "app/src/main/java/com/varasecurity/alpha031/MainActivity.java"
gradle = root / "app/build.gradle"
s = java.read_text(encoding="utf-8")

required = [
    '0.11.1 ALPHA',
    'protectedSessionPreflightReady()',
    'protectedSessionBlockingCount()',
    'fixProtectedSessionRequirement()',
    'activeNetworkCaptivePortalDetected()',
    'android.permission.ACCESS_NETWORK_STATE',
]
for marker in required:
    if marker not in s and marker != 'android.permission.ACCESS_NETWORK_STATE':
        raise SystemExit(f"missing validated 0.11.1 prerequisite: {marker}")

helpers = r'''
    private boolean activeNetworkValidated() {
        try {
            android.net.ConnectivityManager cm = (android.net.ConnectivityManager)
                    getSystemService(android.content.Context.CONNECTIVITY_SERVICE);
            if (cm == null) return false;
            android.net.Network active = cm.getActiveNetwork();
            if (active == null) return false;
            android.net.NetworkCapabilities caps = cm.getNetworkCapabilities(active);
            return caps != null && caps.hasCapability(android.net.NetworkCapabilities.NET_CAPABILITY_VALIDATED);
        } catch (Exception ignored) {
            return false;
        }
    }

    private String validatedNetworkDetail() {
        if (activeNetworkValidated()) {
            return t("Android reports the active network as validated for internet access",
                    "Android شبکه فعال را برای دسترسی اینترنتی معتبر گزارش می‌کند");
        }
        if (activeNetworkCaptivePortalDetected()) {
            return captivePortalNetworkDetail();
        }
        return t("Android cannot currently validate internet access on the active network. SafePay waits for a validated connection.",
                "Android در حال حاضر نمی‌تواند دسترسی اینترنتی شبکه فعال را معتبر تأیید کند. SafePay تا اتصال معتبر منتظر می‌ماند.");
    }

'''
anchor = '    private boolean activeNetworkCaptivePortalDetected() {'
if s.count(anchor) != 1:
    raise SystemExit(f"patch failed [validated network helper anchor]: found {s.count(anchor)}")
s = s.replace(anchor, helpers + anchor, 1)

old = '        return webViewRuntimeReady() && isDeviceLockSecure() && !adbEnabled() && !activeNetworkCaptivePortalDetected();'
if s.count(old) != 1:
    raise SystemExit(f"patch failed [preflight validated network gate]: found {s.count(old)}")
s = s.replace(old, '        return webViewRuntimeReady() && isDeviceLockSecure() && !adbEnabled() && !activeNetworkCaptivePortalDetected() && activeNetworkValidated();', 1)

old = '        if (activeNetworkCaptivePortalDetected()) return t("Captive portal network must be cleared", "درگاه ورود اجباری شبکه باید برطرف شود");'
if s.count(old) != 1:
    raise SystemExit(f"patch failed [readiness validated network text]: found {s.count(old)}")
s = s.replace(old, old + '\n        if (!activeNetworkValidated()) return t("Validated internet connection required", "اتصال اینترنتی معتبر لازم است");', 1)

old = '        if (activeNetworkCaptivePortalDetected()) count++;\n        return count;'
if s.count(old) != 1:
    raise SystemExit(f"patch failed [blocking count validated network]: found {s.count(old)}")
s = s.replace(old, '        if (activeNetworkCaptivePortalDetected()) count++;\n        else if (!activeNetworkValidated()) count++;\n        return count;', 1)

old = '''        if (activeNetworkCaptivePortalDetected()) {
            setProtectedRequirementFixPending(true);
            openSettings(Settings.ACTION_WIRELESS_SETTINGS);
            return;
        }
        renderBrowserStart();'''
if s.count(old) != 1:
    raise SystemExit(f"patch failed [direct validated network remediation]: found {s.count(old)}")
s = s.replace(old, '''        if (activeNetworkCaptivePortalDetected()) {
            setProtectedRequirementFixPending(true);
            openSettings(Settings.ACTION_WIRELESS_SETTINGS);
            return;
        }
        if (!activeNetworkValidated()) {
            setProtectedRequirementFixPending(true);
            openSettings(Settings.ACTION_WIRELESS_SETTINGS);
            return;
        }
        renderBrowserStart();''', 1)

old = '        if (activeNetworkCaptivePortalDetected()) return t("Open network settings", "باز کردن تنظیمات شبکه");'
if s.count(old) != 1:
    raise SystemExit(f"patch failed [validated network action label]: found {s.count(old)}")
s = s.replace(old, old + '\n        if (!activeNetworkValidated()) return t("Open network settings", "باز کردن تنظیمات شبکه");', 1)

launch_anchor = '        WebView.startSafeBrowsing(this, value -> {'
if s.count(launch_anchor) != 1:
    raise SystemExit(f"patch failed [runtime validated network gate]: found {s.count(launch_anchor)}")
launch_gate = '''        if (!activeNetworkValidated()) {
            String event = t("Protected browser blocked: active network is not validated", "مرورگر محافظت‌شده مسدود شد: شبکه فعال معتبر تأیید نشده است");
            recordActivity(event);
            try { web.stopLoading(); web.destroy(); } catch (Exception ignored) {}
            Toast.makeText(MainActivity.this, t("Use a validated internet connection before SafePay", "پیش از SafePay از اتصال اینترنتی معتبر استفاده کنید"), Toast.LENGTH_LONG).show();
            openSettings(Settings.ACTION_WIRELESS_SETTINGS);
            renderBrowserStart();
            return;
        }
'''
s = s.replace(launch_anchor, launch_gate + launch_anchor, 1)

portal_row = '        protectedReady.addView(tv((!activeNetworkCaptivePortalDetected() ? "✓ " : "• ") + t("No captive portal", "بدون درگاه ورود اجباری"), 12, !activeNetworkCaptivePortalDetected() ? GOOD : WARN, true));'
if s.count(portal_row) != 1:
    raise SystemExit(f"patch failed [compatibility validated network row]: found {s.count(portal_row)}")
s = s.replace(portal_row, portal_row + '\n        protectedReady.addView(tv((activeNetworkValidated() ? "✓ " : "• ") + t("Validated internet connection", "اتصال اینترنتی معتبر"), 12, activeNetworkValidated() ? GOOD : WARN, true));', 1)

compat_anchor = '        LinearLayout captivePortalCard = card();'
if s.count(compat_anchor) != 1:
    raise SystemExit(f"patch failed [validated network compatibility card]: found {s.count(compat_anchor)}")
compat_card = '''        LinearLayout validatedNetworkCard = card();
        boolean compatibilityValidatedNetwork = activeNetworkValidated();
        validatedNetworkCard.addView(tv(t("Network trust • validation", "اعتماد شبکه • اعتبارسنجی"), 16, NAVY, true));
        validatedNetworkCard.addView(tv(validatedNetworkDetail(), 13,
                compatibilityValidatedNetwork ? GOOD : WARN, !compatibilityValidatedNetwork));
        validatedNetworkCard.addView(tv(t("SafePay starts only when Android reports the active network as validated for internet access. Device Scan remains independent.",
                "SafePay فقط زمانی شروع می‌شود که Android شبکه فعال را برای دسترسی اینترنتی معتبر گزارش کند. اسکن دستگاه مستقل باقی می‌ماند."), 12, MUTED, false));
        content.addView(validatedNetworkCard);

'''
s = s.replace(compat_anchor, compat_card + compat_anchor, 1)

s = s.replace('0.11.1 ALPHA', '0.11.2 ALPHA')
s = s.replace('0.11.1 Alpha • versionCode 1101', '0.11.2 Alpha • versionCode 1102')
s = s.replace('0.11.1 Alpha', '0.11.2 Alpha')
s = s.replace('VARA 0.11.1 requires Android 8.0 / API 26 or newer.', 'VARA 0.11.2 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+1101\b', 'versionCode 1102', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.11\.1-alpha['\"]", "versionName '0.11.2-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'activeNetworkValidated()',
    'validatedNetworkDetail()',
    'NET_CAPABILITY_VALIDATED',
    'Validated internet connection required',
    'Protected browser blocked: active network is not validated',
    'Validated internet connection',
    'Network trust • validation',
    'Device Scan remains independent',
    '0.11.2 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.11.2 validated-network SafePay guard patch applied")
