from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: patch_127.py <android-project-root>')

root = Path(sys.argv[1])
src = root / 'app/src/main/java'
files = {
'com/varasecurity/core/detection/DetectionScanModels.kt': '''package com.varasecurity.core.detection\n\nimport com.varasecurity.core.heuristic.PackageSecurityAssessmentResult\n\nenum class PackageScanStage { HASH, STATIC_ANALYSIS, CERTIFICATE, INSTALLER, ASSESSMENT }\n\ndata class PackageScanFailure(\n    val packageName: String,\n    val stage: PackageScanStage,\n    val reason: String\n)\n\ndata class DetectionScanResult(\n    val scannedCount: Int,\n    val assessments: List<PackageSecurityAssessmentResult>,\n    val failures: List<PackageScanFailure>,\n    val startedAtMillis: Long,\n    val finishedAtMillis: Long\n)\n\nenum class DetectionScanFailureReason { INVENTORY_UNAVAILABLE, INVENTORY_FAILED }\n\ndata class DetectionScanFailure(\n    val reason: DetectionScanFailureReason,\n    val message: String\n)\n\nsealed interface DetectionScanOutcome {\n    data class Success(val result: DetectionScanResult) : DetectionScanOutcome\n    data class Failure(val failure: DetectionScanFailure) : DetectionScanOutcome\n}\n''',
'com/varasecurity/core/scan/DeviceScanProgress.kt': '''package com.varasecurity.core.scan\n\nimport com.varasecurity.core.detection.PackageScanStage\n\ndata class DeviceScanProgress(\n    val processedCount: Int,\n    val totalCount: Int,\n    val currentPackageName: String?,\n    val currentStage: PackageScanStage?\n)\n''',
'com/varasecurity/core/scan/DeviceScanFailure.kt': '''package com.varasecurity.core.scan\n\nimport com.varasecurity.core.detection.DetectionScanFailure\nimport com.varasecurity.core.detection.DetectionScanFailureReason\n\ndata class DeviceScanFailure(\n    val reason: DetectionScanFailureReason,\n    val message: String\n) {\n    companion object {\n        fun fromDetectionFailure(failure: DetectionScanFailure): DeviceScanFailure =\n            DeviceScanFailure(failure.reason, failure.message)\n    }\n}\n''',
'com/varasecurity/core/scan/DeviceScanResult.kt': '''package com.varasecurity.core.scan\n\nimport com.varasecurity.core.detection.DetectionScanResult\nimport com.varasecurity.core.detection.PackageScanFailure\nimport com.varasecurity.core.heuristic.DetectionType\nimport com.varasecurity.core.heuristic.PackageSecurityAssessmentResult\n\ndata class DeviceScanResult(\n    val scannedCount: Int,\n    val assessments: List<PackageSecurityAssessmentResult>,\n    val failures: List<PackageScanFailure>,\n    val startedAtMillis: Long,\n    val finishedAtMillis: Long,\n    val malwareCount: Int,\n    val suspiciousCount: Int,\n    val configRiskCount: Int,\n    val infoCount: Int\n) {\n    companion object {\n        fun fromDetectionResult(result: DetectionScanResult): DeviceScanResult {\n            var malware = 0; var suspicious = 0; var configRisk = 0; var info = 0\n            result.assessments.forEach { item ->\n                when (item.assessment.detectionType) {\n                    DetectionType.MALWARE -> malware++\n                    DetectionType.SUSPICIOUS -> suspicious++\n                    DetectionType.CONFIG_RISK -> configRisk++\n                    DetectionType.INFO -> info++\n                }\n            }\n            return DeviceScanResult(\n                result.scannedCount, result.assessments, result.failures,\n                result.startedAtMillis, result.finishedAtMillis,\n                malware, suspicious, configRisk, info\n            )\n        }\n    }\n}\n''',
'com/varasecurity/core/scan/DeviceScanState.kt': '''package com.varasecurity.core.scan\n\nsealed interface DeviceScanState {\n    data class Running(val progress: DeviceScanProgress) : DeviceScanState\n    data class Completed(val result: DeviceScanResult) : DeviceScanState\n    data class Failed(val failure: DeviceScanFailure) : DeviceScanState\n}\n'''
}

for rel, content in files.items():
    p = src / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding='utf-8')

print('VARA 0.12.0 detection scan + device scan locked core models integrated')
