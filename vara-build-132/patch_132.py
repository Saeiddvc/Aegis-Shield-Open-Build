from pathlib import Path
import re, sys
if len(sys.argv)!=2: raise SystemExit('usage: patch_132.py <android-project-root>')
root=Path(sys.argv[1]); src=root/'app/src/main/java'
bridge=src/'com/varasecurity/core/scan/DeviceScanJavaBridge.kt'
bridge.parent.mkdir(parents=True,exist_ok=True)
bridge.write_text(r'''package com.varasecurity.core.scan

import android.content.Context
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

object DeviceScanJavaBridge {
    interface Callback {
        fun onCompleted(result: DeviceScanResult)
        fun onFailed(failure: DeviceScanFailure)
    }

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)

    @JvmStatic
    fun run(context: Context, callback: Callback): Job = scope.launch {
        val coordinator = AndroidDeviceScanRuntime.create(context.applicationContext)
        when (val state = coordinator.runDeviceScan()) {
            is DeviceScanState.Completed -> withContext(Dispatchers.Main) { callback.onCompleted(state.result) }
            is DeviceScanState.Failed -> withContext(Dispatchers.Main) { callback.onFailed(state.failure) }
            is DeviceScanState.Running -> withContext(Dispatchers.Main) {
                callback.onFailed(DeviceScanFailure(com.varasecurity.core.detection.DetectionScanFailureReason.INVENTORY_FAILED, "UNEXPECTED_RUNNING_STATE"))
            }
        }
    }
}
''',encoding='utf-8')

p=src/'com/varasecurity/alpha031/MainActivity.java'
s=p.read_text(encoding='utf-8')
# imports
if 'com.varasecurity.core.scan.DeviceScanJavaBridge' not in s:
    s=s.replace('import java.text.DateFormat;', 'import com.varasecurity.core.scan.DeviceScanFailure;\nimport com.varasecurity.core.scan.DeviceScanJavaBridge;\nimport com.varasecurity.core.scan.DeviceScanResult;\n\nimport java.text.DateFormat;')
pattern=r'    private void runQuickScan\(\) \{.*?\n    \}\n\n    private void renderAudit\(\)'
replacement=r'''    private void runQuickScan() {
        Toast.makeText(this, t("Scanning installed apps...", "در حال بررسی برنامه‌های نصب‌شده..."), Toast.LENGTH_SHORT).show();
        DeviceScanJavaBridge.run(this, new DeviceScanJavaBridge.Callback() {
            @Override public void onCompleted(DeviceScanResult result) {
                String event = t(
                    "Scanned " + result.getScannedCount() + " apps • Malware " + result.getMalwareCount() + " • Suspicious " + result.getSuspiciousCount(),
                    result.getScannedCount() + " برنامه بررسی شد • بدافزار " + result.getMalwareCount() + " • مشکوک " + result.getSuspiciousCount()
                );
                prefs.edit()
                    .putString("last_activity", event)
                    .putString("last_activity_time", DateFormat.getDateTimeInstance(DateFormat.SHORT, DateFormat.SHORT).format(new Date()))
                    .putInt("last_malware_count", result.getMalwareCount())
                    .putInt("last_suspicious_count", result.getSuspiciousCount())
                    .putInt("last_config_risk_count", result.getConfigRiskCount())
                    .apply();
                String msg = result.getMalwareCount() > 0
                    ? t("Malware detected: " + result.getMalwareCount(), "بدافزار شناسایی شد: " + result.getMalwareCount())
                    : result.getSuspiciousCount() > 0
                        ? t("Suspicious apps: " + result.getSuspiciousCount(), "برنامه مشکوک: " + result.getSuspiciousCount())
                        : t("Malware scan completed", "بررسی بدافزار تکمیل شد");
                Toast.makeText(MainActivity.this, msg, Toast.LENGTH_LONG).show();
                renderHome();
            }
            @Override public void onFailed(DeviceScanFailure failure) {
                prefs.edit().putString("last_activity", t("Malware scan could not complete", "بررسی بدافزار کامل نشد"))
                    .putString("last_activity_time", DateFormat.getDateTimeInstance(DateFormat.SHORT, DateFormat.SHORT).format(new Date())).apply();
                Toast.makeText(MainActivity.this, t("Scan failed. Try again.", "بررسی ناموفق بود. دوباره تلاش کنید."), Toast.LENGTH_LONG).show();
                renderHome();
            }
        });
    }

    private void renderAudit()'''
s2,n=re.subn(pattern,replacement,s,flags=re.S)
if n!=1: raise SystemExit(f'runQuickScan replacement failed: {n}')
p.write_text(s2,encoding='utf-8')
print('VARA real device malware scan wired to existing UI')
