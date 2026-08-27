from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_111.py <android-project-root>")

root = Path(sys.argv[1])
java = root / "app/src/main/java/com/varasecurity/alpha031/MainActivity.java"
gradle = root / "app/build.gradle"
s = java.read_text(encoding="utf-8")

required = [
    '0.11.0 ALPHA',
    'protectedSessionPreflightReady()',
    'protectedSessionBlockingCount()',
    'fixProtectedSessionRequirement()',
    'activeVpnTransportDetected()',
    'android.permission.ACCESS_NETWORK_STATE',
]
for marker in required:
    if marker not in s and marker != 'android.permission.ACCESS_NETWORK_STATE':
        raise SystemExit(f"missing validated 0.11.0 prerequisite: {marker}")

helpers = r'''
    private boolean activeNetworkCaptivePortalDetected() {
        try {
            android.net.ConnectivityManager cm = (android.net.ConnectivityManager)
                    getSystemService(android.content.Context.CONNECTIVITY_SERVICE);
            if (cm == null) return false;
            android.net.Network active = cm.getActiveNetwork();
            if (active == null) return false;
            android.net.NetworkCapabilities caps = cm.getNetworkCapabilities(active);
            return caps != null && caps.hasCapability(android.net.NetworkCapabilities.NET_CAPABILITY_CAPTIVE_PORTAL);
        } catch (Exception ignored) {
            return false;
        }
    }

    private String captivePortalNetworkDetail() {
        if (!activeNetworkCaptivePortalDetected()) {
            return t("No captive-portal network is currently detected",
                    "در حال حاضر شبکه دارای درگاه ورود اجباری شناسایی نشد");
        }
        return t("A captive portal is active on the current network. Complete or leave the portal before SafePay or protected browsing.",
                "در شبکه فعلی یک درگاه ورود اجباری فعال است. پیش از SafePay یا مرور محافظت‌شده، ورود شبکه را تکمیل کنید یا شبکه را تغییر دهید.");
    }

'''
anchor = '    private boolean activeVpnTransportDetected() {'
if s.count(anchor) != 1:
    raise SystemExit(f"patch failed [captive portal helper anchor]: found {s.count(anchor)}")
s = s.replace(anchor, helpers + anchor, 1)

old = '        return webViewRuntimeReady() && isDeviceLockSecure() && !adbEnabled();'
if s.count(old) != 1:
    raise SystemExit(f"patch failed [preflight captive portal gate]: found {s.count(old)}")
s = s.replace(old, '        return webViewRuntimeReady() && isDeviceLockSecure() && !adbEnabled() && !activeNetworkCaptivePortalDetected();', 1)

old = '        if (adbEnabled()) return t("USB debugging must be disabled", "اشکال‌زدایی USB باید غیرفعال شود");'
if s.count(old) != 1:
    raise SystemExit(f"patch failed [readiness captive portal text]: found {s.count(old)}")
s = s.replace(old, old + '\n        if (activeNetworkCaptivePortalDetected()) return t("Captive portal network must be cleared", "درگاه ورود اجباری شبکه باید برطرف شود");', 1)

old = '        if (adbEnabled()) count++;\n        return count;'
if s.count(old) != 1:
    raise SystemExit(f"patch failed [blocking count captive portal]: found {s.count(old)}")
s = s.replace(old, '        if (adbEnabled()) count++;\n        if (activeNetworkCaptivePortalDetected()) count++;\n        return count;', 1)

old = '''        if (adbEnabled()) {
            setProtectedRequirementFixPending(true);
            try { openSettings(Settings.ACTION_APPLICATION_DEVELOPMENT_SETTINGS); }
            catch (Exception ignored) { openSettings(Settings.ACTION_SETTINGS); }
            return;
        }
        renderBrowserStart();'''
if s.count(old) != 1:
    raise SystemExit(f"patch failed [direct captive portal remediation]: found {s.count(old)}")
s = s.replace(old, '''        if (adbEnabled()) {
            setProtectedRequirementFixPending(true);
            try { openSettings(Settings.ACTION_APPLICATION_DEVELOPMENT_SETTINGS); }
            catch (Exception ignored) { openSettings(Settings.ACTION_SETTINGS); }
            return;
        }
        if (activeNetworkCaptivePortalDetected()) {
            setProtectedRequirementFixPending(true);
            openSettings(Settings.ACTION_WIRELESS_SETTINGS);
            return;
        }
        renderBrowserStart();''', 1)

old = '        if (adbEnabled()) return t("Turn off USB debugging", "خاموش کردن اشکال‌زدایی USB");'
if s.count(old) != 1:
    raise SystemExit(f"patch failed [captive portal action label]: found {s.count(old)}")
s = s.replace(old, old + '\n        if (activeNetworkCaptivePortalDetected()) return t("Open network settings", "باز کردن تنظیمات شبکه");', 1)

launch_anchor = '        WebView.startSafeBrowsing(this, value -> {'
if s.count(launch_anchor) != 1:
    raise SystemExit(f"patch failed [runtime captive portal gate]: found {s.count(launch_anchor)}")
launch_gate = '''        if (activeNetworkCaptivePortalDetected()) {
            String event = t("Protected browser blocked: captive portal network detected", "مرورگر محافظت‌شده مسدود شد: درگاه ورود اجباری شبکه شناسایی شد");
            recordActivity(event);
            try { web.stopLoading(); web.destroy(); } catch (Exception ignored) {}
            Toast.makeText(MainActivity.this, t("Complete or leave the captive portal before SafePay", "پیش از SafePay ورود شبکه را تکمیل کنید یا شبکه را تغییر دهید"), Toast.LENGTH_LONG).show();
            openSettings(Settings.ACTION_WIRELESS_SETTINGS);
            renderBrowserStart();
            return;
        }
'''
s = s.replace(launch_anchor, launch_gate + launch_anchor, 1)

usb_row = '        protectedReady.addView(tv((!adbEnabled() ? "✓ " : "• ") + t("USB debugging disabled", "اشکال‌زدایی USB غیرفعال"), 12, !adbEnabled() ? GOOD : WARN, true));'
if s.count(usb_row) != 1:
    raise SystemExit(f"patch failed [compatibility captive portal row]: found {s.count(usb_row)}")
s = s.replace(usb_row, usb_row + '\n        protectedReady.addView(tv((!activeNetworkCaptivePortalDetected() ? "✓ " : "• ") + t("No captive portal", "بدون درگاه ورود اجباری"), 12, !activeNetworkCaptivePortalDetected() ? GOOD : WARN, true));', 1)

compat_anchor = '        LinearLayout vpnCard = card();'
if s.count(compat_anchor) != 1:
    raise SystemExit(f"patch failed [captive portal compatibility card]: found {s.count(compat_anchor)}")
compat_card = '''        LinearLayout captivePortalCard = card();
        boolean compatibilityCaptivePortal = activeNetworkCaptivePortalDetected();
        captivePortalCard.addView(tv(t("Network trust • captive portal", "اعتماد شبکه • درگاه ورود اجباری"), 16, NAVY, true));
        captivePortalCard.addView(tv(captivePortalNetworkDetail(), 13,
                compatibilityCaptivePortal ? WARN : GOOD, compatibilityCaptivePortal));
        captivePortalCard.addView(tv(t("SafePay fails closed while Android reports a captive portal on the active network. Device Scan remains independent.",
                "تا زمانی که Android روی شبکه فعال درگاه ورود اجباری گزارش کند، SafePay به‌صورت امن اجرا نمی‌شود. اسکن دستگاه مستقل باقی می‌ماند."), 12, MUTED, false));
        content.addView(captivePortalCard);

'''
s = s.replace(compat_anchor, compat_card + compat_anchor, 1)

s = s.replace('0.11.0 ALPHA', '0.11.1 ALPHA')
s = s.replace('0.11.0 Alpha • versionCode 1100', '0.11.1 Alpha • versionCode 1101')
s = s.replace('0.11.0 Alpha', '0.11.1 Alpha')
s = s.replace('VARA 0.11.0 requires Android 8.0 / API 26 or newer.', 'VARA 0.11.1 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+1100\b', 'versionCode 1101', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.11\.0-alpha['\"]", "versionName '0.11.1-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'activeNetworkCaptivePortalDetected()',
    'captivePortalNetworkDetail()',
    'NET_CAPABILITY_CAPTIVE_PORTAL',
    'Captive portal network must be cleared',
    'Protected browser blocked: captive portal network detected',
    'No captive portal',
    'Network trust • captive portal',
    'Device Scan remains independent',
    '0.11.1 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.11.1 captive portal SafePay guard patch applied")
