from pathlib import Path
import re, sys
if len(sys.argv)!=2: raise SystemExit('usage: patch_133.py <android-project-root>')
root=Path(sys.argv[1]); src=root/'app/src/main/java'

# Version bump
g=root/'app/build.gradle'
s=g.read_text(encoding='utf-8')
s=s.replace('versionCode 1200','versionCode 1201').replace("versionName '0.12.0-alpha'","versionName '0.12.1-alpha'")
g.write_text(s,encoding='utf-8')

p=src/'com/varasecurity/alpha031/MainActivity.java'
s=p.read_text(encoding='utf-8')

# Additional imports for actionable scan results
imports='''import com.varasecurity.core.heuristic.PackageSecurityAssessmentResult;\nimport com.varasecurity.core.model.DetectionReason;\n'''
if 'PackageSecurityAssessmentResult' not in s:
    s=s.replace('import com.varasecurity.core.scan.DeviceScanResult;\n', 'import com.varasecurity.core.scan.DeviceScanResult;\n'+imports)

# Replace completion behavior so the actual findings screen opens instead of collapsing back to Home.
s=s.replace('''                Toast.makeText(MainActivity.this, msg, Toast.LENGTH_LONG).show();\n                renderHome();''','''                Toast.makeText(MainActivity.this, msg, Toast.LENGTH_LONG).show();\n                renderScanResults(result);''')

# Add product-grade scan results screen before renderAudit.
anchor='    private void renderAudit() {'
if 'private void renderScanResults(DeviceScanResult result)' not in s:
    method=r'''    private void renderScanResults(DeviceScanResult result) {
        basePage();
        addTopBar(t("Scan Results", "نتیجه بررسی"), true);

        LinearLayout summary = card();
        summary.addView(tv(t("Device scan completed", "بررسی دستگاه تکمیل شد"), 20, NAVY, true));
        summary.addView(tv(t(
            result.getScannedCount() + " installed apps were analyzed by VARA's detection engine.",
            result.getScannedCount() + " برنامه نصب‌شده توسط موتور تشخیص VARA بررسی شد."
        ), 13, MUTED, false));

        LinearLayout metrics = new LinearLayout(this);
        metrics.setOrientation(LinearLayout.HORIZONTAL);
        metrics.setPadding(0, dp(16), 0, 0);
        metrics.addView(metric(String.valueOf(result.getMalwareCount()), t("Malware", "بدافزار")), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        metrics.addView(metric(String.valueOf(result.getSuspiciousCount()), t("Suspicious", "مشکوک")), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        metrics.addView(metric(String.valueOf(result.getConfigRiskCount()), t("Config risk", "ریسک تنظیم")), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        summary.addView(metrics);
        content.addView(summary);

        if (!result.getFailures().isEmpty()) {
            LinearLayout warning = card();
            warning.addView(tv(t(
                "Partial scan: " + result.getFailures().size() + " analysis stage(s) could not complete.",
                "بررسی ناقص: " + result.getFailures().size() + " مرحله تحلیل کامل نشد."
            ), 13, WARN, true));
            warning.addView(tv(t(
                "Other apps were still scanned normally. Retry the scan if this persists.",
                "سایر برنامه‌ها به‌صورت عادی بررسی شدند. اگر ادامه داشت بررسی را تکرار کنید."
            ), 12, MUTED, false));
            content.addView(warning);
        }

        sectionLabel(t("Findings", "یافته‌ها"));
        int findingCount = 0;
        for (PackageSecurityAssessmentResult item : result.getAssessments()) {
            String type = item.getAssessment().getDetectionType().name();
            if ("INFO".equals(type)) continue;
            findingCount++;
            LinearLayout finding = card();
            String pkg = item.getPackageName();
            String severity = item.getAssessment().getSeverity().name();
            int accent = "MALWARE".equals(type) ? DANGER : ("SUSPICIOUS".equals(type) ? WARN : NAVY_2);
            TextView label = tv(type.replace('_',' ') + "  •  " + severity, 12, accent, true);
            finding.addView(label);
            finding.addView(tv(pkg, 16, NAVY, true));

            if (!item.getAssessment().getReasons().isEmpty()) {
                LinearLayout reasons = new LinearLayout(this);
                reasons.setOrientation(LinearLayout.VERTICAL);
                LinearLayout.LayoutParams rp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
                rp.setMargins(0, dp(10), 0, dp(8));
                reasons.setLayoutParams(rp);
                for (DetectionReason reason : item.getAssessment().getReasons()) {
                    reasons.addView(tv("• " + reason.getMessage(), 12, MUTED, false));
                }
                finding.addView(reasons);
            }

            LinearLayout actions = new LinearLayout(this);
            actions.setOrientation(LinearLayout.VERTICAL);
            Button details = secondary(t("Review app settings", "بررسی تنظیمات برنامه"));
            details.setOnClickListener(v -> {
                try {
                    Intent intent = new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:" + pkg));
                    startActivity(intent);
                } catch (Exception e) {
                    Toast.makeText(MainActivity.this, t("App settings unavailable", "تنظیمات برنامه در دسترس نیست"), Toast.LENGTH_SHORT).show();
                }
            });
            actions.addView(details, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(48)));

            if ("MALWARE".equals(type) || "SUSPICIOUS".equals(type)) {
                Button uninstall = primary(t("Uninstall app", "حذف برنامه"));
                LinearLayout.LayoutParams up = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(48));
                up.setMargins(0, dp(8), 0, 0);
                actions.addView(uninstall, up);
                uninstall.setOnClickListener(v -> {
                    try { startActivity(new Intent(Intent.ACTION_DELETE, Uri.parse("package:" + pkg))); }
                    catch (Exception e) { Toast.makeText(MainActivity.this, t("Uninstall unavailable", "حذف برنامه در دسترس نیست"), Toast.LENGTH_SHORT).show(); }
                });
            }
            finding.addView(actions);
            content.addView(finding);
        }

        if (findingCount == 0) {
            LinearLayout clean = card();
            clean.addView(tv(t("No actionable malware findings", "یافته بدافزاری قابل اقدام پیدا نشد"), 18, GOOD, true));
            clean.addView(tv(t(
                "VARA found no malware or suspicious app verdicts in this scan. Configuration risks are reported separately.",
                "در این بررسی، VARA هیچ بدافزار یا برنامه مشکوکی تشخیص نداد. ریسک‌های تنظیمات به‌صورت جداگانه گزارش می‌شوند."
            ), 13, MUTED, false));
            content.addView(clean);
        }

        Button rescan = primary(t("Scan again", "بررسی مجدد"));
        LinearLayout.LayoutParams sp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(52));
        sp.setMargins(0, dp(16), 0, 0);
        content.addView(rescan, sp);
        rescan.setOnClickListener(v -> runQuickScan());
    }

'''
    if anchor not in s: raise SystemExit('renderAudit anchor missing')
    s=s.replace(anchor,method+anchor)

# Improve home copy so it does not imply protection features beyond what is actually active.
s=s.replace('Core protection is active. Review your device regularly.','Security tools are ready. Run a device scan to review installed apps and risks.')
s=s.replace('محافظت اصلی فعال است. وضعیت دستگاه را به‌صورت دوره‌ای بررسی کنید.','ابزارهای امنیتی آماده‌اند. برای بررسی برنامه‌ها و ریسک‌ها، دستگاه را اسکن کنید.')
s=s.replace('You are protected','VARA Security is ready').replace('دستگاه شما محافظت می‌شود','VARA Security آماده است')

p.write_text(s,encoding='utf-8')
print('VARA 0.12.1 product pass: actionable real scan results + version bump')
