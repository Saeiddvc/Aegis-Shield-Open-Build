from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: patch_130.py <android-project-root>')

root = Path(sys.argv[1])
src = root / 'app/src/main/java'
files = {
'com/varasecurity/core/scan/DeviceScanCoordinator.kt': r'''package com.varasecurity.core.scan

import com.varasecurity.core.detection.DetectionScanOutcome
import com.varasecurity.core.detection.InstalledPackageDetectionPipeline
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

class DeviceScanCoordinator(
    private val pipeline: InstalledPackageDetectionPipeline
) {
    private val _state = MutableStateFlow<DeviceScanState?>(null)
    val state: StateFlow<DeviceScanState?> = _state.asStateFlow()

    suspend fun runDeviceScan(): DeviceScanState {
        _state.value = DeviceScanState.Running(
            DeviceScanProgress(
                processedCount = 0,
                totalCount = 0,
                currentPackageName = null,
                currentStage = null
            )
        )
        return try {
            when (val outcome = pipeline.run()) {
                is DetectionScanOutcome.Success -> DeviceScanState.Completed(
                    DeviceScanResult.fromDetectionResult(outcome.result)
                )
                is DetectionScanOutcome.Failure -> DeviceScanState.Failed(
                    DeviceScanFailure.fromDetectionFailure(outcome.failure)
                )
            }.also { _state.value = it }
        } catch (e: CancellationException) {
            _state.value = null
            throw e
        }
    }
}
''',
'com/varasecurity/core/scan/SecurityEngineDeviceScanAdapter.kt': r'''package com.varasecurity.core.scan

sealed interface SecurityEngineScanState {
    data class Completed(val result: DeviceScanResult) : SecurityEngineScanState
    data class Failed(val failure: DeviceScanFailure) : SecurityEngineScanState
}

class SecurityEngineDeviceScanAdapter(
    private val coordinator: DeviceScanCoordinator
) {
    suspend fun runSecurityDeviceScan(): SecurityEngineScanState =
        when (val state = coordinator.runDeviceScan()) {
            is DeviceScanState.Completed -> SecurityEngineScanState.Completed(state.result)
            is DeviceScanState.Failed -> SecurityEngineScanState.Failed(state.failure)
            is DeviceScanState.Running -> throw IllegalStateException(
                "DeviceScanCoordinator.runDeviceScan() returned Running state unexpectedly."
            )
        }
}
''',
'com/varasecurity/core/scan/AndroidDeviceScanRuntime.kt': r'''package com.varasecurity.core.scan

import android.content.Context
import com.varasecurity.core.cert.AndroidSignerExtractor
import com.varasecurity.core.cert.CertificateAnalyzer
import com.varasecurity.core.cert.DefaultPackageCertificateScanner
import com.varasecurity.core.cert.InMemoryCertificateReputationRepository
import com.varasecurity.core.detection.InstalledPackageDetectionPipeline
import com.varasecurity.core.hash.DefaultInstalledPackageHashScanner
import com.varasecurity.core.hash.InMemoryHashReputationRepository
import com.varasecurity.core.heuristic.HeuristicEngine
import com.varasecurity.core.heuristic.PackageSecurityAssessmentOrchestrator
import com.varasecurity.core.installer.DefaultInstallerReputationAnalyzer
import com.varasecurity.core.inventory.AndroidPackageInventory
import com.varasecurity.core.staticanalysis.DefaultStaticPackageAnalyzer

object AndroidDeviceScanRuntime {
    fun create(context: Context): DeviceScanCoordinator {
        val pm = context.applicationContext.packageManager
        val certificateRepository = InMemoryCertificateReputationRepository()
        val certificateScanner = DefaultPackageCertificateScanner(
            AndroidSignerExtractor(),
            CertificateAnalyzer(certificateRepository)
        )
        val pipeline = InstalledPackageDetectionPipeline(
            inventory = AndroidPackageInventory(pm),
            hashScanner = DefaultInstalledPackageHashScanner(InMemoryHashReputationRepository()),
            staticAnalyzer = DefaultStaticPackageAnalyzer(),
            certificateScanner = certificateScanner,
            installerAnalyzer = DefaultInstallerReputationAnalyzer(pm),
            orchestrator = PackageSecurityAssessmentOrchestrator(HeuristicEngine())
        )
        return DeviceScanCoordinator(pipeline)
    }
}
'''
}
for rel, content in files.items():
    p = src / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding='utf-8')
print('VARA DeviceScan coordinator, adapter and Android runtime wiring integrated')
