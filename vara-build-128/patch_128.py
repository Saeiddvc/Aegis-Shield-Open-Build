from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: patch_128.py <android-project-root>')
root=Path(sys.argv[1])
base=root/'app/src/main/java/com/varasecurity/core'
files={
'inventory/PackageInventory.kt':'''package com.varasecurity.core.inventory
import android.content.pm.PackageInfo
interface PackageInventory { suspend fun getInstalledPackages(): List<PackageInfo> }
''',
'hash/InstalledPackageHashScanResult.kt':'''package com.varasecurity.core.hash
data class InstalledPackageHashScanResult(val packageName:String,val hashReputation:HashReputation?=null,val hashError:Throwable?=null)
''',
'hash/InstalledPackageHashScanner.kt':'''package com.varasecurity.core.hash
import android.content.pm.PackageInfo
interface InstalledPackageHashScanner { suspend fun scan(packageInfo: PackageInfo): InstalledPackageHashScanResult }
''',
'staticanalysis/StaticPackageAnalyzer.kt':'''package com.varasecurity.core.staticanalysis
import android.content.pm.PackageInfo
import com.varasecurity.core.model.RiskSignal
interface StaticPackageAnalyzer { suspend fun analyze(packageInfo: PackageInfo): Set<RiskSignal> }
''',
'cert/PackageCertificateScanResult.kt':'''package com.varasecurity.core.cert
data class PackageCertificateScanResult(val packageName:String,val assessment:CertificateAssessmentInput)
''',
'cert/PackageCertificateScanner.kt':'''package com.varasecurity.core.cert
import android.content.pm.PackageInfo
interface PackageCertificateScanner { suspend fun scan(packageInfo: PackageInfo): PackageCertificateScanResult }
''',
'installer/InstallerReputationAnalyzer.kt':'''package com.varasecurity.core.installer
import android.content.pm.PackageInfo
interface InstallerReputationAnalyzer { suspend fun analyze(packageInfo: PackageInfo): InstallerReputation }
''',
'detection/InstalledPackageDetectionPipeline.kt':'''package com.varasecurity.core.detection

import com.varasecurity.core.cert.PackageCertificateScanner
import com.varasecurity.core.hash.InstalledPackageHashScanner
import com.varasecurity.core.heuristic.PackageSecurityAssessmentInput
import com.varasecurity.core.heuristic.PackageSecurityAssessmentOrchestrator
import com.varasecurity.core.heuristic.inputs.StaticAnalysisInput
import com.varasecurity.core.installer.InstallerReputation
import com.varasecurity.core.installer.InstallerReputationAnalyzer
import com.varasecurity.core.inventory.PackageInventory
import com.varasecurity.core.staticanalysis.StaticPackageAnalyzer
import kotlinx.coroutines.CancellationException

class InstalledPackageDetectionPipeline(
    private val inventory: PackageInventory,
    private val hashScanner: InstalledPackageHashScanner,
    private val staticAnalyzer: StaticPackageAnalyzer,
    private val certificateScanner: PackageCertificateScanner,
    private val installerAnalyzer: InstallerReputationAnalyzer,
    private val orchestrator: PackageSecurityAssessmentOrchestrator,
    private val clock: () -> Long = System::currentTimeMillis
) {
    suspend fun run(): DetectionScanOutcome {
        val startedAt=clock()
        val packages=try { inventory.getInstalledPackages() } catch (e:CancellationException){ throw e } catch(e:Exception){
            return DetectionScanOutcome.Failure(DetectionScanFailure(DetectionScanFailureReason.INVENTORY_FAILED,"INVENTORY_STAGE_FAILED"))
        }
        val assessments=mutableListOf<com.varasecurity.core.heuristic.PackageSecurityAssessmentResult>()
        val failures=mutableListOf<PackageScanFailure>()
        for (pkg in packages) {
            val name=pkg.packageName.orEmpty()
            var hash:com.varasecurity.core.hash.HashReputation?=null
            try { val r=hashScanner.scan(pkg); if(r.hashError!=null) failures+=PackageScanFailure(name,PackageScanStage.HASH,"HASH_STAGE_FAILED") else hash=r.hashReputation } catch(e:CancellationException){throw e}catch(e:Exception){failures+=PackageScanFailure(name,PackageScanStage.HASH,"HASH_STAGE_FAILED")}
            var staticInput:StaticAnalysisInput?=null
            try { staticInput=StaticAnalysisInput(staticAnalyzer.analyze(pkg)) } catch(e:CancellationException){throw e}catch(e:Exception){failures+=PackageScanFailure(name,PackageScanStage.STATIC_ANALYSIS,"STATIC_ANALYSIS_STAGE_FAILED")}
            var cert:com.varasecurity.core.cert.CertificateAssessmentInput?=null
            try { cert=certificateScanner.scan(pkg).assessment } catch(e:CancellationException){throw e}catch(e:Exception){failures+=PackageScanFailure(name,PackageScanStage.CERTIFICATE,"CERTIFICATE_STAGE_FAILED")}
            var installer=InstallerReputation.UNKNOWN
            try { installer=installerAnalyzer.analyze(pkg) } catch(e:CancellationException){throw e}catch(e:Exception){failures+=PackageScanFailure(name,PackageScanStage.INSTALLER,"INSTALLER_STAGE_FAILED")}
            try {
                assessments+=orchestrator.assess(PackageSecurityAssessmentInput(name,hash,staticInput,cert,installer))
            } catch(e:CancellationException){throw e}catch(e:Exception){failures+=PackageScanFailure(name,PackageScanStage.ASSESSMENT,"ASSESSMENT_STAGE_FAILED")}
        }
        return DetectionScanOutcome.Success(DetectionScanResult(packages.size,assessments,failures,startedAt,clock()))
    }
}
'''
}
for rel,content in files.items():
    p=base/rel; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(content,encoding='utf-8')
# coroutines dependency for suspend/cancellation semantics
bg=root/'app/build.gradle'
s=bg.read_text(encoding='utf-8')
if 'kotlinx-coroutines-core' not in s:
    if 'dependencies {' in s: s=s.replace('dependencies {','dependencies {\n    implementation "org.jetbrains.kotlinx:kotlinx-coroutines-core:1.8.1"',1)
    else: s += '\n\ndependencies {\n    implementation "org.jetbrains.kotlinx:kotlinx-coroutines-core:1.8.1"\n}\n'
    bg.write_text(s,encoding='utf-8')
print('VARA installed package detection pipeline integrated')
