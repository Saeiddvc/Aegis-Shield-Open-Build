from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_070.py <android-project-root>")

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

# A visible freshness stamp makes clear that posture is a point-in-time assessment and gives
# users a concrete recheck action after changing Android settings or installed apps.
rep(
    '    private void renderHome() {',
    '''    private String postureRefreshStamp() {
        String time = android.text.format.DateFormat.format("HH:mm", new java.util.Date()).toString();
        return t("Status refreshed " + time, "وضعیت در " + time + " به‌روزرسانی شد");
    }

    private void renderHome() {''',
    "posture refresh helper",
)

rep(
    '        postureText.addView(tv(homeActions == 0 ? t("No remediation is currently waiting", "در حال حاضر اقدام اصلاحی در انتظار نیست") : t(homeActions + " prioritized action(s) waiting", homeActions + " اقدام اولویت‌بندی‌شده در انتظار است"), 12, MUTED, false));',
    '''        postureText.addView(tv(homeActions == 0 ? t("No remediation is currently waiting", "در حال حاضر اقدام اصلاحی در انتظار نیست") : t(homeActions + " prioritized action(s) waiting", homeActions + " اقدام اولویت‌بندی‌شده در انتظار است"), 12, MUTED, false));
        postureText.addView(tv(postureRefreshStamp(), 11, MUTED, false));''',
    "home posture freshness",
)

rep(
    '''        actionCenter.setOnClickListener(v -> renderActionCenter());
        content.addView(actionCenter);''',
    '''        actionCenter.setOnClickListener(v -> renderActionCenter());
        content.addView(actionCenter);

        Button recheckPosture = secondary(t("Recheck security posture", "بررسی مجدد وضعیت امنیتی"));
        LinearLayout.LayoutParams rcp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(48));
        rcp.setMargins(0, dp(4), 0, dp(8));
        content.addView(recheckPosture, rcp);
        recheckPosture.setOnClickListener(v -> renderHome());''',
    "home one-tap posture recheck",
)

# Action Center uses the same point-in-time posture evaluation and provides an explicit full
# recheck without making sensitive Android settings changes on the user's behalf.
rep(
    '        hero.addView(tv(total == 0 ? t("Current device and app posture checks do not require remediation.", "بررسی فعلی وضعیت دستگاه و برنامه‌ها نیاز به اصلاحی نشان نمی‌دهد.") : t("Review the highest-impact findings first. VARA opens the relevant Android settings but does not change sensitive settings automatically.", "ابتدا موارد با اثر بیشتر را بررسی کنید. VARA تنظیمات مرتبط Android را باز می‌کند اما تنظیمات حساس را به‌صورت خودکار تغییر نمی‌دهد."), 13, Color.rgb(244,248,250), false));',
    '''        hero.addView(tv(total == 0 ? t("Current device and app posture checks do not require remediation.", "بررسی فعلی وضعیت دستگاه و برنامه‌ها نیاز به اصلاحی نشان نمی‌دهد.") : t("Review the highest-impact findings first. VARA opens the relevant Android settings but does not change sensitive settings automatically.", "ابتدا موارد با اثر بیشتر را بررسی کنید. VARA تنظیمات مرتبط Android را باز می‌کند اما تنظیمات حساس را به‌صورت خودکار تغییر نمی‌دهد."), 13, Color.rgb(244,248,250), false));
        hero.addView(tv(postureRefreshStamp(), 11, Color.rgb(220,236,239), false));''',
    "action center freshness",
)

rep(
    '''        summary.addView(metrics);
        content.addView(summary);''',
    '''        summary.addView(metrics);
        Button recheckAll = secondary(t("Recheck all findings", "بررسی مجدد همه موارد"));
        LinearLayout.LayoutParams rap = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(46));
        rap.setMargins(0, dp(12), 0, 0);
        summary.addView(recheckAll, rap);
        recheckAll.setOnClickListener(v -> renderActionCenter());
        content.addView(summary);''',
    "action center full recheck",
)

# Version metadata.
s = s.replace('0.6.9 ALPHA', '0.7.0 ALPHA')
s = s.replace('0.6.9 Alpha • versionCode 609', '0.7.0 Alpha • versionCode 700')
s = s.replace('0.6.9 Alpha', '0.7.0 Alpha')
s = s.replace('VARA 0.6.9 requires Android 8.0 / API 26 or newer.', 'VARA 0.7.0 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+609\b', 'versionCode 700', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.6\.9-alpha['\"]", "versionName '0.7.0-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'postureRefreshStamp()',
    'Recheck security posture',
    'Recheck all findings',
    'Status refreshed ',
    '0.7.0 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.7.0 posture freshness and remediation recheck patch applied")
