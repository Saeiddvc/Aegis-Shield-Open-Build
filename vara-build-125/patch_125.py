from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: patch_125.py <android-project-root>')

root = Path(sys.argv[1])
project_gradle = root / 'build.gradle'
app_gradle = root / 'app/build.gradle'

pg = project_gradle.read_text(encoding='utf-8')
if "org.jetbrains.kotlin.android" not in pg:
    pg = pg.replace(
        "id 'com.android.application' version '8.7.3' apply false",
        "id 'com.android.application' version '8.7.3' apply false\n    id 'org.jetbrains.kotlin.android' version '1.9.24' apply false"
    )
project_gradle.write_text(pg, encoding='utf-8')

ag = app_gradle.read_text(encoding='utf-8')
ag = ag.replace("plugins { id 'com.android.application' }", "plugins { id 'com.android.application'; id 'org.jetbrains.kotlin.android' }")
ag, n1 = re.subn(r'versionCode\s+1114\b', 'versionCode 1200', ag, count=1)
ag, n2 = re.subn(r"versionName\s+['\"]0\.11\.14-alpha['\"]", "versionName '0.12.0-alpha'", ag, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit(f'version patch failed: versionCode={n1}, versionName={n2}')
if 'kotlinOptions' not in ag:
    ag = ag.replace(
        "    compileOptions {\n        sourceCompatibility JavaVersion.VERSION_17\n        targetCompatibility JavaVersion.VERSION_17\n    }",
        "    compileOptions {\n        sourceCompatibility JavaVersion.VERSION_17\n        targetCompatibility JavaVersion.VERSION_17\n    }\n\n    kotlinOptions {\n        jvmTarget = '17'\n    }"
    )
app_gradle.write_text(ag, encoding='utf-8')

src = root / 'app/src/main/java'
files = {
'com/varasecurity/core/model/RiskSignal.kt': '''package com.varasecurity.core.model\n\nenum class RiskSignal {\n    ACCESSIBILITY_SERVICE, OVERLAY, READ_SMS, RECEIVE_SMS, INSTALL_PACKAGES,\n    BOOT_RECEIVER, DEVICE_ADMIN, NOTIFICATION_LISTENER\n}\n''',
'com/varasecurity/core/model/DetectionReason.kt': '''package com.varasecurity.core.model\n\ndata class DetectionReason(val code: String, val message: String)\n''',
'com/varasecurity/core/heuristic/DetectionSeverity.kt': '''package com.varasecurity.core.heuristic\n\nenum class DetectionSeverity { CRITICAL, HIGH, MEDIUM, LOW, INFO }\n''',
'com/varasecurity/core/heuristic/DetectionType.kt': '''package com.varasecurity.core.heuristic\n\nenum class DetectionType { MALWARE, SUSPICIOUS, CONFIG_RISK, INFO }\n''',
'com/varasecurity/core/heuristic/CorrelationRule.kt': '''package com.varasecurity.core.heuristic\n\nenum class CorrelationRule {\n    ACCESSIBILITY_PLUS_OVERLAY, ACCESSIBILITY_PLUS_SMS, ACCESSIBILITY_OVERLAY_SMS,\n    INSTALL_PACKAGES_PLUS_SIDELOAD, BOOT_RECEIVER_WITH_HIGH_RISK_CAPABILITY\n}\n''',
'com/varasecurity/core/model/AppliedCorrelation.kt': '''package com.varasecurity.core.model\n\nimport com.varasecurity.core.heuristic.CorrelationRule\n\ndata class AppliedCorrelation(\n    val rule: CorrelationRule,\n    val scoreDelta: Int,\n    val reason: DetectionReason\n)\n''',
'com/varasecurity/core/cert/CertificateModels.kt': '''package com.varasecurity.core.cert\n\ndata class CertificateEvidence(\n    val fingerprintSha256: String,\n    val reputation: CertificateReputation,\n    val signerRole: SignerRole\n)\n\ndata class CertificateAssessmentInput(\n    val certificates: List<CertificateEvidence>,\n    val status: CertificateAssessmentStatus\n)\n\nenum class CertificateReputation { KNOWN_MALICIOUS, TRUSTED_PUBLISHER, KNOWN, UNKNOWN }\nenum class CertificateAssessmentStatus { AVAILABLE, SIGNER_UNAVAILABLE, PARSE_ERROR }\nenum class SignerRole { CURRENT, HISTORY }\n''',
'com/varasecurity/core/hash/HashModels.kt': '''package com.varasecurity.core.hash\n\ndata class HashReputation(val sha256: String, val status: HashReputationStatus)\nenum class HashReputationStatus { KNOWN_MALICIOUS, KNOWN_CLEAN, UNKNOWN }\n''',
'com/varasecurity/core/installer/InstallerReputation.kt': '''package com.varasecurity.core.installer\n\nenum class InstallerReputation { TRUSTED_STORE, KNOWN_INSTALLER, SIDELOADED, UNKNOWN }\n''',
'com/varasecurity/core/heuristic/inputs/StaticAnalysisInput.kt': '''package com.varasecurity.core.heuristic.inputs\n\nimport com.varasecurity.core.model.RiskSignal\n\ndata class StaticAnalysisInput(val signals: Set<RiskSignal>)\n''',
'com/varasecurity/core/heuristic/HeuristicInput.kt': '''package com.varasecurity.core.heuristic\n\nimport com.varasecurity.core.cert.CertificateAssessmentInput\nimport com.varasecurity.core.hash.HashReputation\nimport com.varasecurity.core.heuristic.inputs.StaticAnalysisInput\nimport com.varasecurity.core.installer.InstallerReputation\n\ndata class HeuristicInput(\n    val certificate: CertificateAssessmentInput? = null,\n    val static: StaticAnalysisInput? = null,\n    val hash: HashReputation? = null,\n    val installer: InstallerReputation? = null\n)\n''',
'com/varasecurity/core/heuristic/HeuristicAssessment.kt': '''package com.varasecurity.core.heuristic\n\nimport com.varasecurity.core.model.AppliedCorrelation\nimport com.varasecurity.core.model.DetectionReason\nimport com.varasecurity.core.model.RiskSignal\n\ndata class HeuristicAssessment(\n    val score: Int,\n    val confidence: Int,\n    val severity: DetectionSeverity,\n    val detectionType: DetectionType,\n    val suspicious: Boolean,\n    val staticScore: Int,\n    val certificateScore: Int,\n    val installerScore: Int,\n    val contributingRiskSignals: Set<RiskSignal>,\n    val reasons: List<DetectionReason>,\n    val appliedCorrelations: List<AppliedCorrelation>\n)\n''',
'com/varasecurity/core/heuristic/PackageSecurityAssessmentModels.kt': '''package com.varasecurity.core.heuristic\n\nimport com.varasecurity.core.cert.CertificateAssessmentInput\nimport com.varasecurity.core.hash.HashReputation\nimport com.varasecurity.core.heuristic.inputs.StaticAnalysisInput\nimport com.varasecurity.core.installer.InstallerReputation\n\ndata class PackageSecurityAssessmentInput(\n    val packageName: String,\n    val hash: HashReputation? = null,\n    val staticAnalysis: StaticAnalysisInput? = null,\n    val certificateAssessment: CertificateAssessmentInput? = null,\n    val installerReputation: InstallerReputation? = null\n)\n\ndata class PackageSecurityAssessmentResult(\n    val packageName: String,\n    val assessment: HeuristicAssessment\n)\n''',
'com/varasecurity/core/heuristic/PackageSecurityAssessmentOrchestrator.kt': '''package com.varasecurity.core.heuristic\n\nclass PackageSecurityAssessmentOrchestrator(\n    private val engine: HeuristicEngine\n) {\n    fun assess(input: PackageSecurityAssessmentInput): PackageSecurityAssessmentResult =\n        PackageSecurityAssessmentResult(\n            packageName = input.packageName,\n            assessment = engine.assess(\n                HeuristicInput(\n                    certificate = input.certificateAssessment,\n                    static = input.staticAnalysis,\n                    hash = input.hash,\n                    installer = input.installerReputation\n                )\n            )\n        )\n}\n'''
}

for rel, content in files.items():
    p = src / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding='utf-8')

print('VARA 0.12.0 detection-core model integration applied; Kotlin enabled; versionCode=1200')
