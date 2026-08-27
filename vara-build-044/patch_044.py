from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_044.py <android-project-root>")

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

# Home becomes state-driven instead of always looking identical.
rep(
    '        TextView status = tv(t("You are protected", "دستگاه شما محافظت می‌شود"), 24, Color.WHITE, true);\n        status.setGravity(Gravity.CENTER);',
    '        int homeIssues = auditIssueCount();\n        TextView status = tv(homeIssues == 0 ? t("You are protected", "دستگاه شما محافظت می‌شود") : t("Protection needs attention", "محافظت نیاز به رسیدگی دارد"), 24, Color.WHITE, true);\n        status.setGravity(Gravity.CENTER);',
    "dynamic home status",
)
rep(
    '        TextView sub = tv(t("Core protection is active. Review your device regularly.", "محافظت اصلی فعال است. وضعیت دستگاه را به‌صورت دوره‌ای بررسی کنید."), 14, Color.rgb(220, 236, 239), false);',
    '        TextView sub = tv(homeIssues == 0 ? t("Core protection is active. Your current device audit is clear.", "محافظت اصلی فعال است و ممیزی فعلی دستگاه موردی نشان نمی‌دهد.") : t(homeIssues + " device setting(s) should be reviewed.", homeIssues + " مورد از تنظیمات دستگاه نیاز به بررسی دارد."), 14, Color.rgb(220, 236, 239), false);',
    "dynamic home subtitle",
)
rep(
    '        hero.addView(sub);\n        Button scan = primary(t("Scan device", "بررسی دستگاه"));',
    '        hero.addView(sub);\n        TextView stateChip = tv(homeIssues == 0 ? t("SECURE", "ایمن") : t("REVIEW " + homeIssues, "بررسی " + homeIssues), 11, Color.WHITE, true);\n        stateChip.setGravity(Gravity.CENTER);\n        stateChip.setBackground(rounded(homeIssues == 0 ? GOOD : WARN, 14));\n        LinearLayout.LayoutParams scp = new LinearLayout.LayoutParams(dp(homeIssues == 0 ? 88 : 112), dp(30)); scp.setMargins(0, dp(14), 0, 0); hero.addView(stateChip, scp);\n        Button scan = primary(t("Scan device", "بررسی دستگاه"));',
    "home status chip",
)

# More branded, useful drawer header and navigation hierarchy.
rep(
    '        head.addView(tv(t("Protected • core services active", "محافظت فعال • سرویس‌های اصلی روشن"), 12, Color.rgb(214,235,237), false)); drawer.addView(head);',
    '        int drawerIssues = auditIssueCount();\n        head.addView(tv(drawerIssues == 0 ? t("Protected • no device issues", "محافظت فعال • بدون مورد در دستگاه") : t("Attention • " + drawerIssues + " device issue(s)", "نیاز به رسیدگی • " + drawerIssues + " مورد در دستگاه"), 12, Color.rgb(214,235,237), false));\n        TextView buildTag = tv("0.4.4 ALPHA", 10, Color.WHITE, true); buildTag.setGravity(Gravity.CENTER); buildTag.setBackground(rounded(0x3325C8B8, 12)); LinearLayout.LayoutParams btp = new LinearLayout.LayoutParams(dp(96), dp(27)); btp.setMargins(0, dp(12), 0, 0); head.addView(buildTag, btp); drawer.addView(head);',
    "drawer branded status",
)
rep(
    '        addDrawerSection(list, t("Protection", "محافظت"));\n        addDrawerItem(list, "✓", t("Antivirus & Scan", "آنتی‌ویروس و اسکن"),',
    '        addDrawerSection(list, t("Overview", "نمای کلی"));\n        addDrawerItem(list, "⌂", t("Home", "خانه"), t("Protection status and shortcuts", "وضعیت محافظت و میانبرها"), v -> { closeDrawer(); renderHome(); });\n        addDrawerItem(list, "▤", t("Security Report", "گزارش امنیتی"), t("Device security summary", "خلاصه وضعیت امنیت دستگاه"), v -> { closeDrawer(); renderReport(); });\n        addDrawerSection(list, t("Protection", "محافظت"));\n        addDrawerItem(list, "✓", t("Antivirus & Scan", "آنتی‌ویروس و اسکن"),',
    "drawer overview routes",
)
rep(
    '        addDrawerItem(list, "i", t("About VARA", "درباره VARA"), "0.4.3 Alpha", v -> { closeDrawer(); renderAbout(); });',
    '        addDrawerItem(list, "i", t("About VARA", "درباره VARA"), "0.4.4 Alpha", v -> { closeDrawer(); renderAbout(); });',
    "drawer version",
)
rep(
    '        LinearLayout row = new LinearLayout(this); row.setOrientation(LinearLayout.HORIZONTAL); row.setGravity(Gravity.CENTER_VERTICAL); row.setPadding(dp(10), dp(10), dp(8), dp(10)); row.setBackground(rounded(Color.WHITE, 16));',
    '        LinearLayout row = new LinearLayout(this); row.setOrientation(LinearLayout.HORIZONTAL); row.setGravity(Gravity.CENTER_VERTICAL); row.setPadding(dp(10), dp(10), dp(8), dp(10)); row.setBackground(rounded(Color.rgb(249,251,252), 16)); LinearLayout.LayoutParams rlp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT); rlp.setMargins(0, dp(3), 0, dp(3)); row.setLayoutParams(rlp);',
    "drawer row rhythm",
)
rep(
    '        LinearLayout tx = new LinearLayout(this); tx.setOrientation(LinearLayout.VERTICAL); tx.addView(tv(title, 14, NAVY, true)); tx.addView(tv(desc, 11, MUTED, false)); LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1); p.setMargins(dp(12), 0, 0, 0); row.addView(tx, p); row.setOnClickListener(click); list.addView(row);',
    '        LinearLayout tx = new LinearLayout(this); tx.setOrientation(LinearLayout.VERTICAL); tx.addView(tv(title, 14, NAVY, true)); tx.addView(tv(desc, 11, MUTED, false)); LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1); p.setMargins(dp(12), 0, dp(4), 0); row.addView(tx, p); TextView arrow = tv(fa ? "‹" : "›", 22, MUTED, false); arrow.setGravity(Gravity.CENTER); row.addView(arrow, new LinearLayout.LayoutParams(dp(28), dp(44))); row.setOnClickListener(click); list.addView(row);',
    "drawer chevrons",
)

# Version labels.
rep('about.addView(tv("0.4.3 Alpha • versionCode 403", 13, MUTED, false));', 'about.addView(tv("0.4.4 Alpha • versionCode 404", 13, MUTED, false));', "settings version")
rep('hero.addView(tv("0.4.3 Alpha • versionCode 403", 13, Color.rgb(220,236,239), false));', 'hero.addView(tv("0.4.4 Alpha • versionCode 404", 13, Color.rgb(220,236,239), false));', "about version")

java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
for old, new in [("versionCode 403", "versionCode 404"), ("versionName '0.4.3-alpha'", "versionName '0.4.4-alpha'")]:
    if g.count(old) != 1:
        raise SystemExit(f"gradle patch failed: {old}")
    g = g.replace(old, new, 1)
gradle.write_text(g, encoding="utf-8")

print("VARA 0.4.4 patch applied successfully")
