from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_059.py <android-project-root>")

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

# Expand app-level review with declared high-impact Android capabilities. These are review
# signals only; declaration does not prove that the capability is granted, active or malicious.
rep(
    '''        boolean noInstallerAttribution;
        int reviewScore;''',
    '''        boolean noInstallerAttribution;
        boolean requestsInstallPackages;
        boolean requestsOverlay;
        boolean declaresAccessibilityService;
        int reviewScore;''',
    "app capability fields",
)

capability_helpers = r'''
    private boolean packageRequestsPermission(PackageInfo pi, String permission) {
        if (pi == null || pi.requestedPermissions == null || permission == null) return false;
        for (String p : pi.requestedPermissions) if (permission.equals(p)) return true;
        return false;
    }

    private boolean packageDeclaresAccessibilityService(PackageInfo pi) {
        if (pi == null || pi.services == null) return false;
        for (android.content.pm.ServiceInfo service : pi.services) {
            if (service != null && android.Manifest.permission.BIND_ACCESSIBILITY_SERVICE.equals(service.permission)) return true;
        }
        return false;
    }

'''
rep(
    '    private AppRiskSummary analyzeAppRisk() {',
    capability_helpers + '    private AppRiskSummary analyzeAppRisk() {',
    "capability helper methods",
)

rep(
    '            java.util.List<PackageInfo> packages = getPackageManager().getInstalledPackages(0);',
    '            java.util.List<PackageInfo> packages = getPackageManager().getInstalledPackages(android.content.pm.PackageManager.GET_PERMISSIONS | android.content.pm.PackageManager.GET_SERVICES);',
    "package metadata flags",
)

rep(
    '''                item.noInstallerAttribution = item.installer == null || item.installer.trim().isEmpty();

                // Explainable review score. This is a local review-priority heuristic, not a malware probability.''',
    '''                item.noInstallerAttribution = item.installer == null || item.installer.trim().isEmpty();
                item.requestsInstallPackages = packageRequestsPermission(pi, android.Manifest.permission.REQUEST_INSTALL_PACKAGES);
                item.requestsOverlay = packageRequestsPermission(pi, android.Manifest.permission.SYSTEM_ALERT_WINDOW);
                item.declaresAccessibilityService = packageDeclaresAccessibilityService(pi);

                // Explainable review score. This is a local review-priority heuristic, not a malware probability.''',
    "capability signal extraction",
)

rep(
    '''                if (item.debuggable) item.reviewScore += 60;
                if (item.legacyTarget) item.reviewScore += 25;
                if (item.noInstallerAttribution) item.reviewScore += 15;
                if (item.reviewScore > 100) item.reviewScore = 100;''',
    '''                if (item.debuggable) item.reviewScore += 60;
                if (item.legacyTarget) item.reviewScore += 25;
                if (item.noInstallerAttribution) item.reviewScore += 15;
                if (item.declaresAccessibilityService) item.reviewScore += 35;
                if (item.requestsInstallPackages) item.reviewScore += 25;
                if (item.requestsOverlay) item.reviewScore += 20;
                if (item.reviewScore > 100) item.reviewScore = 100;''',
    "capability review weights",
)

rep(
    '''        scoring.addView(tv(t("Debuggable +60 • Target SDK below 28 +25 • Installer attribution unavailable +15. High: 60–100, Medium: 25–59, Low: 1–24.", "قابل دیباگ +۶۰ • Target SDK کمتر از ۲۸ +۲۵ • منبع نصب نامشخص +۱۵. اولویت بالا: ۶۰ تا ۱۰۰، متوسط: ۲۵ تا ۵۹، پایین: ۱ تا ۲۴."), 13, MUTED, false));''',
    '''        scoring.addView(tv(t("Debuggable +60 • Accessibility service declaration +35 • Target SDK below 28 +25 • Install-packages capability +25 • Overlay capability +20 • Installer attribution unavailable +15. High: 60–100, Medium: 25–59, Low: 1–24.", "قابل دیباگ +۶۰ • اعلام سرویس دسترس‌پذیری +۳۵ • Target SDK کمتر از ۲۸ +۲۵ • قابلیت نصب بسته +۲۵ • قابلیت Overlay +۲۰ • منبع نصب نامشخص +۱۵. اولویت بالا: ۶۰ تا ۱۰۰، متوسط: ۲۵ تا ۵۹، پایین: ۱ تا ۲۴."), 13, MUTED, false));
        scoring.addView(tv(t("Capability signals mean the app declares access in its manifest; VARA does not treat declaration alone as evidence that access is currently granted, active or malicious.", "سیگنال قابلیت یعنی برنامه آن دسترسی را در Manifest اعلام کرده است؛ VARA صرف اعلام را نشانه فعال بودن، اعطا شدن یا مخرب بودن دسترسی نمی‌داند."), 12, MUTED, false));''',
    "explainable capability scoring",
)

rep(
    '''            if (item.debuggable) reasons.add(t("Debuggable build", "نسخه قابل دیباگ"));
            if (item.legacyTarget) reasons.add(t("Target SDK " + item.targetSdk + " is below 28", "Target SDK برابر " + item.targetSdk + " و کمتر از ۲۸ است"));
            if (item.noInstallerAttribution) reasons.add(t("Installer attribution unavailable", "منبع نصب قابل تشخیص نیست"));''',
    '''            if (item.debuggable) reasons.add(t("Debuggable build", "نسخه قابل دیباگ"));
            if (item.declaresAccessibilityService) reasons.add(t("Declares an Accessibility service", "سرویس دسترس‌پذیری اعلام می‌کند"));
            if (item.requestsInstallPackages) reasons.add(t("Declares install-packages capability", "قابلیت نصب بسته اعلام می‌کند"));
            if (item.requestsOverlay) reasons.add(t("Declares overlay capability", "قابلیت نمایش روی برنامه‌ها اعلام می‌کند"));
            if (item.legacyTarget) reasons.add(t("Target SDK " + item.targetSdk + " is below 28", "Target SDK برابر " + item.targetSdk + " و کمتر از ۲۸ است"));
            if (item.noInstallerAttribution) reasons.add(t("Installer attribution unavailable", "منبع نصب قابل تشخیص نیست"));''',
    "capability reasons",
)

rep(
    '''            if (item.debuggable) {
                nextAction = t("Recommended action: confirm this is an intentional debug/test build. If not, replace it with the official release build from a trusted source.", "اقدام پیشنهادی: بررسی کنید این نسخه عمداً برای تست یا دیباگ نصب شده است. در غیر این صورت آن را با نسخه رسمی از منبع مورد اعتماد جایگزین کنید.");''',
    '''            if (item.declaresAccessibilityService || item.requestsInstallPackages || item.requestsOverlay) {
                nextAction = t("Recommended action: open Android app info and verify whether this app genuinely needs its declared special capability. Review Accessibility, Install unknown apps and Display over other apps under Android Special access where applicable.", "اقدام پیشنهادی: اطلاعات برنامه در Android را باز کنید و بررسی کنید آیا برنامه واقعاً به قابلیت ویژه اعلام‌شده نیاز دارد. در صورت ارتباط، بخش‌های Accessibility، نصب برنامه‌های ناشناس و نمایش روی سایر برنامه‌ها را در Special access بررسی کنید.");
            } else if (item.debuggable) {
                nextAction = t("Recommended action: confirm this is an intentional debug/test build. If not, replace it with the official release build from a trusted source.", "اقدام پیشنهادی: بررسی کنید این نسخه عمداً برای تست یا دیباگ نصب شده است. در غیر این صورت آن را با نسخه رسمی از منبع مورد اعتماد جایگزین کنید.");''',
    "capability remediation action",
)

# Version metadata.
s = s.replace('0.5.8 ALPHA', '0.5.9 ALPHA')
s = s.replace('0.5.8 Alpha • versionCode 508', '0.5.9 Alpha • versionCode 509')
s = s.replace('0.5.8 Alpha', '0.5.9 Alpha')
s = s.replace('VARA 0.5.8 requires Android 8.0 / API 26 or newer.', 'VARA 0.5.9 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+508\b', 'versionCode 509', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.5\.8-alpha['\"]", "versionName '0.5.9-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'packageRequestsPermission(PackageInfo pi, String permission)',
    'packageDeclaresAccessibilityService(PackageInfo pi)',
    'REQUEST_INSTALL_PACKAGES',
    'SYSTEM_ALERT_WINDOW',
    'BIND_ACCESSIBILITY_SERVICE',
    'Declares an Accessibility service',
    'Capability signals mean the app declares access in its manifest',
    '0.5.9 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.5.9 app-capability review patch applied")
