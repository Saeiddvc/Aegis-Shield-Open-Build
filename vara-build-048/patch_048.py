from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_048.py <android-project-root>")

root = Path(sys.argv[1])
java = root / "app/src/main/java/com/varasecurity/alpha031/MainActivity.java"
gradle = root / "app/build.gradle"
s = java.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str):
    global s
    count = s.count(old)
    if count != 1:
        raise SystemExit(f"patch failed [{label}]: expected 1 match, found {count}")
    s = s.replace(old, new, 1)


# Add explicit severity counters to support remediation planning.
old_summary = '''        int flaggedAppCount() { return findings.size(); }
    }'''
new_summary = '''        int flaggedAppCount() { return findings.size(); }

        int mediumRiskCount() {
            int count = 0;
            for (AppRiskItem item : findings) if (item.reviewScore >= 25 && item.reviewScore < 60) count++;
            return count;
        }

        int lowRiskCount() {
            int count = 0;
            for (AppRiskItem item : findings) if (item.reviewScore > 0 && item.reviewScore < 25) count++;
            return count;
        }
    }'''
replace_once(old_summary, new_summary, "severity counters")

# Expand posture metrics from aggregate flagged count to High / Medium / Low buckets.
old_metrics = '''        metrics.addView(metric(String.valueOf(risk.userApps), t("User apps", "برنامه کاربر")), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        metrics.addView(metric(String.valueOf(flagged), t("Flagged", "نیازمند بررسی")), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        metrics.addView(metric(String.valueOf(risk.highRiskCount()), t("High priority", "اولویت بالا")), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        overview.addView(metrics); content.addView(overview);'''
new_metrics = '''        metrics.addView(metric(String.valueOf(risk.highRiskCount()), t("High", "بالا")), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        metrics.addView(metric(String.valueOf(risk.mediumRiskCount()), t("Medium", "متوسط")), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        metrics.addView(metric(String.valueOf(risk.lowRiskCount()), t("Low", "پایین")), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        overview.addView(metrics);
        overview.addView(tv(t(risk.userApps + " user apps reviewed locally", risk.userApps + " برنامه کاربر به‌صورت محلی بررسی شد"), 12, MUTED, false));
        content.addView(overview);'''
replace_once(old_metrics, new_metrics, "severity metrics")

# Add a remediation queue before the per-app findings.
anchor = '''        content.addView(scoring);

        if (risk.findings.isEmpty()) {'''
insert = '''        content.addView(scoring);

        if (!risk.findings.isEmpty()) {
            LinearLayout plan = card();
            plan.addView(tv(t("Recommended review order", "ترتیب پیشنهادی بررسی"), 16, NAVY, true));
            String planText;
            if (risk.highRiskCount() > 0) {
                planText = t("Start with high-priority apps, then review medium and low-priority findings. Open each app's Android settings and verify whether the installation source and build type are expected.", "ابتدا برنامه‌های با اولویت بالا و سپس موارد متوسط و پایین را بررسی کنید. تنظیمات هر برنامه را در Android باز کنید و مطمئن شوید منبع نصب و نوع نسخه با انتظار شما مطابقت دارد.");
            } else if (risk.mediumRiskCount() > 0) {
                planText = t("No high-priority app findings were detected. Review medium-priority apps first, especially older Target SDK builds, then verify low-priority installer-attribution findings.", "موردی با اولویت بالا شناسایی نشد. ابتدا برنامه‌های با اولویت متوسط، به‌ویژه نسخه‌های دارای Target SDK قدیمی، و سپس موارد کم‌اولویت مربوط به منبع نصب را بررسی کنید.");
            } else {
                planText = t("Only low-priority metadata findings are present. Verify that the affected apps were intentionally installed and come from a trusted source.", "فقط یافته‌های کم‌اولویت فراداده‌ای وجود دارد. بررسی کنید برنامه‌های مربوطه با قصد شما نصب شده و از منبع مورد اعتماد دریافت شده باشند.");
            }
            plan.addView(tv(planText, 13, MUTED, false));
            Button recheck = secondary(t("Recheck app posture", "بررسی مجدد وضعیت برنامه‌ها"));
            LinearLayout.LayoutParams rp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(48));
            rp.setMargins(0, dp(12), 0, 0);
            plan.addView(recheck, rp);
            recheck.setOnClickListener(v -> renderAppReview());
            content.addView(plan);
        }

        if (risk.findings.isEmpty()) {'''
replace_once(anchor, insert, "remediation queue")

# Make each finding operational by explaining both impact and the next action.
old_reasons = '''            app.addView(tv(android.text.TextUtils.join(" • ", reasons), 13, MUTED, false));

            Button details = secondary(t("Review app settings", "بررسی تنظیمات برنامه"));'''
new_reasons = '''            app.addView(tv(android.text.TextUtils.join(" • ", reasons), 13, MUTED, false));

            String nextAction;
            if (item.debuggable) {
                nextAction = t("Recommended action: confirm this is an intentional debug/test build. If not, replace it with the official release build from a trusted source.", "اقدام پیشنهادی: بررسی کنید این نسخه عمداً برای تست یا دیباگ نصب شده است. در غیر این صورت آن را با نسخه رسمی از منبع مورد اعتماد جایگزین کنید.");
            } else if (item.legacyTarget) {
                nextAction = t("Recommended action: check whether a newer maintained version is available. Older Target SDK versions may not benefit from newer Android platform protections.", "اقدام پیشنهادی: بررسی کنید نسخه جدیدتر و پشتیبانی‌شده‌ای وجود دارد یا خیر. Target SDK قدیمی ممکن است از همه حفاظت‌های جدید Android بهره‌مند نباشد.");
            } else {
                nextAction = t("Recommended action: verify that you recognize this app and its installation source. Missing installer attribution alone is not a malware verdict.", "اقدام پیشنهادی: مطمئن شوید برنامه و منبع نصب آن برای شما شناخته‌شده است. نامشخص بودن منبع نصب به‌تنهایی به معنی بدافزار بودن برنامه نیست.");
            }
            app.addView(tv(nextAction, 13, priorityColor, false));

            Button details = secondary(t("Open Android app info", "باز کردن اطلاعات برنامه در Android"));'''
replace_once(old_reasons, new_reasons, "per-app remediation")

# Version metadata.
s = s.replace('0.4.7 ALPHA', '0.4.8 ALPHA')
java.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, n1 = re.subn(r'versionCode\s+407\b', 'versionCode 408', g, count=1)
g, n2 = re.subn(r"versionName\s+['\"]0\.4\.7-alpha['\"]", "versionName '0.4.8-alpha'", g, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f"version patch failed: versionCode={n1}, versionName={n2}")
gradle.write_text(g, encoding="utf-8")

checks = [
    'mediumRiskCount()',
    'lowRiskCount()',
    'Recommended review order',
    'Recheck app posture',
    'Recommended action:',
    '0.4.8 ALPHA',
]
for marker in checks:
    if marker not in s:
        raise SystemExit(f"missing expected marker after patch: {marker}")

print("VARA Security 0.4.8 remediation patch applied")
