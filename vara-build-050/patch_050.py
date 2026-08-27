from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_050.py <android-project-root>")

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

# Typography: use Android system sans families consistently and reduce the heavy visual weight.
rep(
    '        v.setTypeface(fa ? Typeface.create("sans", bold ? Typeface.BOLD : Typeface.NORMAL) : Typeface.create(bold ? "sans-serif-medium" : "sans-serif", Typeface.NORMAL));',
    '        v.setTypeface(Typeface.create(bold ? "sans-serif-medium" : "sans-serif", Typeface.NORMAL));',
    "system typography",
)

# Top navigation: replace oversized chevrons and floating white button treatment with a cleaner native-feeling back control.
rep(
    '        TextView nav = tv(back ? (fa ? "›" : "‹") : "☰", back ? 34 : 28, NAVY, false);\n        nav.setGravity(Gravity.CENTER);\n        nav.setBackgroundColor(Color.TRANSPARENT);\n        nav.setContentDescription(back ? t("Back", "بازگشت") : t("Menu", "منو"));',
    '        TextView nav = tv(back ? (fa ? "→" : "←") : "☰", back ? 22 : 26, NAVY, true);\n        nav.setGravity(Gravity.CENTER);\n        nav.setBackground(rounded(back ? Color.TRANSPARENT : Color.WHITE, 16));\n        if (!back) nav.setElevation(dp(1));\n        nav.setContentDescription(back ? t("Back", "بازگشت") : t("Menu", "منو"));',
    "clean top navigation",
)

# Make Home hierarchy more branded and actionable with a single posture summary row beneath the hero.
rep(
    '        content.addView(hero, hp);\n\n        sectionLabel(t("Security", "امنیت"));',
    '''        content.addView(hero, hp);

        LinearLayout postureStrip = card();
        postureStrip.setOrientation(LinearLayout.HORIZONTAL);
        postureStrip.setGravity(Gravity.CENTER_VERTICAL);
        postureStrip.setPadding(dp(16), dp(13), dp(16), dp(13));
        TextView postureIcon = tv(homeActions == 0 ? "✓" : "!", 18, Color.WHITE, true);
        postureIcon.setGravity(Gravity.CENTER);
        postureIcon.setBackground(rounded(homeActions == 0 ? GOOD : WARN, 14));
        postureStrip.addView(postureIcon, new LinearLayout.LayoutParams(dp(42), dp(42)));
        LinearLayout postureText = new LinearLayout(this); postureText.setOrientation(LinearLayout.VERTICAL);
        postureText.addView(tv(homeActions == 0 ? t("Security posture is clear", "وضعیت امنیتی مناسب است") : t("Security posture needs review", "وضعیت امنیتی نیاز به بررسی دارد"), 15, NAVY, true));
        postureText.addView(tv(homeActions == 0 ? t("No remediation is currently waiting", "در حال حاضر اقدام اصلاحی در انتظار نیست") : t(homeActions + " prioritized action(s) waiting", homeActions + " اقدام اولویت‌بندی‌شده در انتظار است"), 12, MUTED, false));
        LinearLayout.LayoutParams pst = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1); pst.setMargins(dp(12), 0, dp(8), 0); postureStrip.addView(postureText, pst);
        TextView postureGo = tv(fa ? "←" : "→", 20, TEAL_DARK, true); postureGo.setGravity(Gravity.CENTER); postureStrip.addView(postureGo, new LinearLayout.LayoutParams(dp(32), dp(42)));
        postureStrip.setOnClickListener(v -> renderActionCenter());
        content.addView(postureStrip);

        sectionLabel(t("Security", "امنیت"));''',
    "home posture strip",
)

# Settings: replace the one-tap language toggle with an explicit selector to avoid accidental language changes.
rep(
    '        content.addView(settingRow(t("Language", "زبان"), fa ? "فارسی" : "English", v -> toggleLanguage()));',
    '        content.addView(settingRow(t("Language", "زبان"), fa ? "فارسی" : "English", v -> renderLanguageSettings()));',
    "language settings route",
)

language_method = r'''
    private void renderLanguageSettings() {
        currentPage = "language";
        basePage(); addTopBar(t("Language", "زبان"), true);

        LinearLayout intro = card();
        intro.setBackground(gradient(NAVY, NAVY_2, 24));
        intro.addView(tv(t("App language", "زبان برنامه"), 20, Color.WHITE, true));
        intro.addView(tv(t("English is the default. You can switch to Persian at any time.", "زبان پیش‌فرض انگلیسی است و در هر زمان می‌توانید فارسی را انتخاب کنید."), 13, Color.rgb(220,236,239), false));
        content.addView(intro);

        LinearLayout english = card(); english.setOrientation(LinearLayout.HORIZONTAL); english.setGravity(Gravity.CENTER_VERTICAL);
        LinearLayout enText = new LinearLayout(this); enText.setOrientation(LinearLayout.VERTICAL); enText.addView(tv("English", 16, NAVY, true)); enText.addView(tv("Default interface language", 12, MUTED, false));
        english.addView(enText, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        TextView enMark = tv(!fa ? "✓" : "", 20, GOOD, true); enMark.setGravity(Gravity.CENTER); english.addView(enMark, new LinearLayout.LayoutParams(dp(40), dp(44)));
        english.setBackground(rounded(!fa ? Color.rgb(232,248,244) : Color.WHITE, 22));
        english.setOnClickListener(v -> setLanguage(false));
        content.addView(english);

        LinearLayout persian = card(); persian.setOrientation(LinearLayout.HORIZONTAL); persian.setGravity(Gravity.CENTER_VERTICAL);
        LinearLayout faText = new LinearLayout(this); faText.setOrientation(LinearLayout.VERTICAL); faText.addView(tv("فارسی", 16, NAVY, true)); faText.addView(tv("رابط کاربری راست‌به‌چپ", 12, MUTED, false));
        persian.addView(faText, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        TextView faMark = tv(fa ? "✓" : "", 20, GOOD, true); faMark.setGravity(Gravity.CENTER); persian.addView(faMark, new LinearLayout.LayoutParams(dp(40), dp(44)));
        persian.setBackground(rounded(fa ? Color.rgb(232,248,244) : Color.WHITE, 22));
        persian.setOnClickListener(v -> setLanguage(true));
        content.addView(persian);
    }

    private void setLanguage(boolean usePersian) {
        fa = usePersian;
        prefs.edit().putString("lang", fa ? "fa" : "en").apply();
        renderLanguageSettings();
    }

'''
rep(
    '    private void toggleLanguage() {',
    language_method + '    private void toggleLanguage() {',
    "explicit language selector",
)

# Keep old helper but make it delegate to the explicit setter for compatibility with any older route.
rep(
    '    private void toggleLanguage() {\n        fa = !fa; prefs.edit().putString("lang", fa ? "fa" : "en").apply(); renderSettings();\n    }',
    '    private void toggleLanguage() { setLanguage(!fa); }',
    "language helper delegation",
)

# Drawer header: show unified device + app posture rather than device settings only.
rep(
    '        int drawerIssues = auditIssueCount();\n        head.addView(tv(drawerIssues == 0 ? t("Protected • no device issues", "محافظت فعال • بدون مورد در دستگاه") : t("Attention • " + drawerIssues + " device issue(s)", "نیاز به رسیدگی • " + drawerIssues + " مورد در دستگاه"), 12, Color.rgb(214,235,237), false));',
    '        int drawerIssues = auditIssueCount();\n        AppRiskSummary drawerRisk = analyzeAppRisk();\n        int drawerActions = drawerIssues + drawerRisk.flaggedAppCount();\n        head.addView(tv(drawerActions == 0 ? t("Protected • posture clear", "محافظت فعال • وضعیت مناسب") : t("Attention • " + drawerActions + " action(s)", "نیاز به رسیدگی • " + drawerActions + " اقدام"), 12, Color.rgb(214,235,237), false));',
    "unified drawer posture",
)

# Version labels.
s = s.replace('0.4.9 ALPHA', '0.5.0 ALPHA')
s = s.replace('0.4.9 Alpha • versionCode 409', '0.5.0 Alpha • versionCode 500')
s = s.replace('0.4.9 Alpha', '0.5.0 Alpha')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+409\b', 'versionCode 500', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.4\.9-alpha['\"]", "versionName '0.5.0-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'currentPage = "language"',
    'English is the default',
    'Security posture needs review',
    'drawerRisk.flaggedAppCount()',
    'sans-serif-medium',
    '0.5.0 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.5.0 UI/localization posture patch applied")
