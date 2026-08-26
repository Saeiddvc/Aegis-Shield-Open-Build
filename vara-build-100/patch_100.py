from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_100.py <android-project-root>")

root = Path(sys.argv[1])
java = root / "app/src/main/java/com/varasecurity/alpha031/MainActivity.java"
gradle = root / "app/build.gradle"
s = java.read_text(encoding="utf-8")

required = [
    'protectedSessionPreflightReady()',
    'protectedSessionReadinessText()',
    'protectedSessionRequirementActionText()',
    'fixProtectedSessionRequirement()',
    'Device Scan still works independently',
    '0.9.9 ALPHA',
]
for marker in required:
    if marker not in s:
        raise SystemExit(f"missing validated 0.9.9 prerequisite: {marker}")

# 0.10.0 milestone: make SafePay readiness immediately understandable on Home,
# in the drawer and on Compatibility. This changes presentation only; the actual
# protected-session preflight remains the same fail-closed contract.
anchor = '    private String protectedSessionReadinessText() {'
if s.count(anchor) != 1:
    raise SystemExit(f"patch failed [readiness helper anchor]: found {s.count(anchor)}")
helpers = r'''    private int protectedSessionBlockingCount() {
        int count = 0;
        if (!webViewRuntimeReady()) count++;
        if (!isDeviceLockSecure()) count++;
        if (adbEnabled()) count++;
        return count;
    }

    private String protectedSessionCompactStatus() {
        int blockers = protectedSessionBlockingCount();
        if (blockers == 0) return t("READY", "آماده");
        return t("BLOCKED • " + blockers + " prerequisite" + (blockers == 1 ? "" : "s"),
                "مسدود • " + blockers + " پیش‌نیاز");
    }

'''
s = s.replace(anchor, helpers + anchor, 1)

home_old = '        readyCard.addView(tv(protectedSessionReadinessText(), 18, protectedReady ? GOOD : WARN, true));'
if s.count(home_old) != 1:
    raise SystemExit(f"patch failed [home compact SafePay status]: found {s.count(home_old)}")
home_new = '''        readyCard.addView(tv(protectedSessionCompactStatus(), 19, protectedReady ? GOOD : WARN, true));
        readyCard.addView(tv(protectedSessionReadinessText(), 12, MUTED, false));'''
s = s.replace(home_old, home_new, 1)

# Rename the Home/Compatibility heading from an implementation-centric phrase to the
# user-facing product name. Replace both English and Persian labels consistently.
s = s.replace('t("Protected session readiness", "آمادگی نشست محافظت‌شده")',
              't("SafePay readiness", "آمادگی SafePay")')

# Drawer: a compact state comes first; the specific unmet requirement remains directly below it.
drawer_old = '        head.addView(tv(t("SafePay: ", "SafePay: ") + protectedSessionReadinessText(), 11, Color.rgb(196,221,225), false));'
if s.count(drawer_old) != 1:
    raise SystemExit(f"patch failed [drawer SafePay status]: found {s.count(drawer_old)}")
drawer_new = '''        head.addView(tv(t("SafePay: ", "SafePay: ") + protectedSessionCompactStatus(), 11, Color.rgb(214,235,237), true));
        if (!protectedSessionPreflightReady()) {
            head.addView(tv(protectedSessionReadinessText(), 10, Color.rgb(196,221,225), false));
        }'''
s = s.replace(drawer_old, drawer_new, 1)

# Compatibility: make the number of launch blockers explicit while keeping each row actionable.
compat_anchor = '        protectedReady.addView(tv(t("Safe Browsing initialization is also verified at session start and fails closed if unavailable.", "راه‌اندازی Safe Browsing نیز هنگام شروع نشست بررسی می‌شود و در صورت عدم دسترسی، نشست به‌صورت امن متوقف می‌شود."), 12, MUTED, false));'
if s.count(compat_anchor) != 1:
    raise SystemExit(f"patch failed [compatibility blocker summary]: found {s.count(compat_anchor)}")
compat_insert = '''        protectedReady.addView(tv(protectedSessionBlockingCount() == 0
                ? t("No blocking prerequisite", "پیش‌نیاز مسدودکننده‌ای وجود ندارد")
                : t(protectedSessionBlockingCount() + " blocking prerequisite(s)", protectedSessionBlockingCount() + " پیش‌نیاز مسدودکننده"),
                13, protectedSessionBlockingCount() == 0 ? GOOD : WARN, true));
'''
s = s.replace(compat_anchor, compat_insert + compat_anchor, 1)

# Version metadata.
s = s.replace('0.9.9 ALPHA', '0.10.0 ALPHA')
s = s.replace('0.9.9 Alpha • versionCode 909', '0.10.0 Alpha • versionCode 1000')
s = s.replace('0.9.9 Alpha', '0.10.0 Alpha')
s = s.replace('VARA 0.9.9 requires Android 8.0 / API 26 or newer.', 'VARA 0.10.0 requires Android 8.0 / API 26 or newer.')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+909\b', 'versionCode 1000', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.9\.9-alpha['\"]", "versionName '0.10.0-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'protectedSessionBlockingCount()',
    'protectedSessionCompactStatus()',
    'SafePay readiness',
    'BLOCKED • ',
    'No blocking prerequisite',
    'blocking prerequisite(s)',
    '0.10.0 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.10.0 SafePay readiness clarity milestone patch applied")
