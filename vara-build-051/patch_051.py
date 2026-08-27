from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_051.py <android-project-root>")

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

# Re-evaluate remediation screens automatically after Android Settings returns to VARA.
rep(
    '    @Override\n    public void onBackPressed() {',
    '''    @Override
    protected void onResume() {
        super.onResume();
        if (root == null || currentPage == null) return;
        if ("audit".equals(currentPage)) renderAudit();
        else if ("actions".equals(currentPage)) renderActionCenter();
        else if ("appreview".equals(currentPage)) renderAppReview();
    }

    @Override
    public void onBackPressed() {''',
    "automatic remediation refresh",
)

# Give Security Audit an explicit recheck action so remediation has a clear completion loop.
rep(
    '        content.addView(summary);\n    }\n\n    private LinearLayout auditRow',
    '''        content.addView(summary);

        Button recheck = secondary(t("Recheck device posture", "بررسی مجدد وضعیت دستگاه"));
        LinearLayout.LayoutParams rcp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(48));
        rcp.setMargins(0, dp(8), 0, dp(4));
        content.addView(recheck, rcp);
        recheck.setOnClickListener(v -> {
            int remaining = auditIssueCount();
            String event = remaining == 0
                    ? t("Device audit rechecked • all device findings cleared", "ممیزی دستگاه دوباره بررسی شد • همه موارد دستگاه رفع شده است")
                    : t("Device audit rechecked • " + remaining + " finding(s) remain", "ممیزی دستگاه دوباره بررسی شد • " + remaining + " مورد باقی مانده است");
            prefs.edit().putString("last_activity", event)
                    .putString("last_activity_time", DateFormat.getDateTimeInstance(DateFormat.SHORT, DateFormat.SHORT).format(new Date())).apply();
            Toast.makeText(this, remaining == 0 ? t("Device posture is clear", "وضعیت دستگاه مناسب است") : t(remaining + " device finding(s) still need review", remaining + " مورد دستگاه هنوز نیاز به بررسی دارد"), Toast.LENGTH_LONG).show();
            renderAudit();
        });
    }

    private LinearLayout auditRow''',
    "audit recheck loop",
)

# Harden the secure WebView against obscured-touch/tapjacking and credential/autofill persistence.
rep(
    '        web.clearHistory(); web.clearCache(false);',
    '''        web.setFilterTouchesWhenObscured(true);
        if (android.os.Build.VERSION.SDK_INT >= 26) web.setImportantForAutofill(View.IMPORTANT_FOR_AUTOFILL_NO_EXCLUDE_DESCENDANTS);
        web.clearFormData(); web.clearHistory(); web.clearCache(false);''',
    "secure webview interaction hardening",
)

# Make the protected-session chrome communicate the active destination host instead of a generic status only.
rep(
    '        TextView title = tv(t("Protected HTTPS session", "نشست محافظت‌شده HTTPS"), 15, NAVY, true); bar.addView(title, new LinearLayout.LayoutParams(0, dp(48), 1)); page.addView(bar);',
    '''        String displayHost = "HTTPS";
        try { Uri displayUri = Uri.parse(initialUrl); if (displayUri.getHost() != null) displayHost = displayUri.getHost(); } catch (Exception ignored) {}
        TextView title = tv(t("Protected • " + displayHost, "محافظت‌شده • " + displayHost), 15, NAVY, true);
        title.setSingleLine(true); title.setEllipsize(android.text.TextUtils.TruncateAt.END);
        bar.addView(title, new LinearLayout.LayoutParams(0, dp(48), 1)); page.addView(bar);''',
    "secure browser host indicator",
)

# Version metadata.
s = s.replace('0.5.0 ALPHA', '0.5.1 ALPHA')
s = s.replace('0.5.0 Alpha • versionCode 500', '0.5.1 Alpha • versionCode 501')
s = s.replace('0.5.0 Alpha', '0.5.1 Alpha')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+500\b', 'versionCode 501', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.5\.0-alpha['\"]", "versionName '0.5.1-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'protected void onResume()',
    'Recheck device posture',
    'setFilterTouchesWhenObscured(true)',
    'IMPORTANT_FOR_AUTOFILL_NO_EXCLUDE_DESCENDANTS',
    'Protected • ',
    '0.5.1 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.5.1 remediation-refresh and secure-browser hardening patch applied")
