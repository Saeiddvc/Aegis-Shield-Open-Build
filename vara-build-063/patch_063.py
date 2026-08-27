from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_063.py <android-project-root>")

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

# Protected WebView should not be able to open secondary windows/popups or expose
# a system file picker. Both surfaces can move sensitive flows outside the controlled
# SafePay/Secure Browser destination policy. Handle them explicitly and fail closed.
rep(
    '''        web.setWebChromeClient(new android.webkit.WebChromeClient() {
            @Override public void onPermissionRequest(android.webkit.PermissionRequest request) {''',
    '''        web.setWebChromeClient(new android.webkit.WebChromeClient() {
            @Override public boolean onCreateWindow(WebView view, boolean isDialog, boolean isUserGesture, android.os.Message resultMsg) {
                recordActivity(t("Protected browser blocked a popup or secondary window",
                        "مرورگر محافظت‌شده پنجره بازشو یا پنجره ثانویه را مسدود کرد"));
                Toast.makeText(MainActivity.this, t("Popup blocked in protected session", "پنجره بازشو در نشست محافظت‌شده مسدود شد"), Toast.LENGTH_SHORT).show();
                return false;
            }
            @Override public boolean onShowFileChooser(WebView webView,
                    android.webkit.ValueCallback<android.net.Uri[]> filePathCallback,
                    android.webkit.WebChromeClient.FileChooserParams fileChooserParams) {
                if (filePathCallback != null) filePathCallback.onReceiveValue(null);
                recordActivity(t("Protected browser blocked a web file-upload request",
                        "مرورگر محافظت‌شده درخواست بارگذاری فایل وب را مسدود کرد"));
                Toast.makeText(MainActivity.this, t("File upload blocked in protected session", "بارگذاری فایل در نشست محافظت‌شده مسدود شد"), Toast.LENGTH_SHORT).show();
                return true;
            }
            @Override public void onPermissionRequest(android.webkit.PermissionRequest request) {''',
    "popup and file chooser fail-closed policy",
)

rep(
    '• Web-auth and client-certificate prompts are blocked',
    '• Web-auth and client-certificate prompts are blocked\\n• Popups, secondary windows and web file uploads are blocked',
    "english protected-session disclosure",
)
rep(
    '• درخواست‌های احراز هویت وب و گواهی کاربر مسدود می‌شوند',
    '• درخواست‌های احراز هویت وب و گواهی کاربر مسدود می‌شوند\\n• پنجره‌های بازشو، پنجره‌های ثانویه و بارگذاری فایل وب مسدود می‌شوند',
    "persian protected-session disclosure",
)

# Version metadata.
s = s.replace('0.6.2 ALPHA', '0.6.3 ALPHA')
s = s.replace('0.6.2 Alpha • versionCode 602', '0.6.3 Alpha • versionCode 603')
s = s.replace('0.6.2 Alpha', '0.6.3 Alpha')
s = s.replace('VARA 0.6.2 requires Android 8.0 / API 26 or newer.', 'VARA 0.6.3 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+602\b', 'versionCode 603', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.6\.2-alpha['\"]", "versionName '0.6.3-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'onCreateWindow',
    'Popup blocked in protected session',
    'onShowFileChooser',
    'filePathCallback.onReceiveValue(null)',
    'File upload blocked in protected session',
    'Popups, secondary windows and web file uploads are blocked',
    '0.6.3 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.6.3 protected popup and file-upload hardening patch applied")
