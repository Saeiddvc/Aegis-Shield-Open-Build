from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: patch_129.py <android-project-root>')
root = Path(sys.argv[1])
base = root / 'app/src/main/java/com/varasecurity/core'
files = {
'inventory/AndroidPackageInventory.kt': r'''package com.varasecurity.core.inventory

import android.content.pm.PackageInfo
import android.content.pm.PackageManager
import android.os.Build
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class AndroidPackageInventory(
    private val packageManager: PackageManager
) : PackageInventory {
    override suspend fun getInstalledPackages(): List<PackageInfo> = withContext(Dispatchers.IO) {
        val flags = PackageManager.GET_PERMISSIONS or
            PackageManager.GET_SERVICES or
            PackageManager.GET_RECEIVERS or
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) PackageManager.GET_SIGNING_CERTIFICATES else PackageManager.GET_SIGNATURES
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            packageManager.getInstalledPackages(PackageManager.PackageInfoFlags.of(flags.toLong()))
        } else {
            @Suppress("DEPRECATION")
            packageManager.getInstalledPackages(flags)
        }
    }
}
''',
'hash/HashReputationRepository.kt': r'''package com.varasecurity.core.hash

interface HashReputationRepository {
    fun lookup(sha256: String): HashReputation
}

class InMemoryHashReputationRepository(
    reputations: Collection<HashReputation> = emptyList()
) : HashReputationRepository {
    private val byHash = reputations.associateBy { it.sha256.lowercase() }
    override fun lookup(sha256: String): HashReputation =
        byHash[sha256.lowercase()] ?: HashReputation(sha256.lowercase(), HashReputationStatus.UNKNOWN)
}
''',
'hash/DefaultInstalledPackageHashScanner.kt': r'''package com.varasecurity.core.hash

import android.content.pm.PackageInfo
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.withContext
import java.io.File
import java.io.FileInputStream
import java.security.MessageDigest
import kotlin.coroutines.coroutineContext

class DefaultInstalledPackageHashScanner(
    private val repository: HashReputationRepository
) : InstalledPackageHashScanner {
    override suspend fun scan(packageInfo: PackageInfo): InstalledPackageHashScanResult = withContext(Dispatchers.IO) {
        val packageName = packageInfo.packageName.orEmpty()
        try {
            val sourceDir = packageInfo.applicationInfo?.sourceDir
                ?: throw IllegalStateException("SOURCE_APK_UNAVAILABLE")
            val digest = MessageDigest.getInstance("SHA-256")
            FileInputStream(File(sourceDir)).use { input ->
                val buffer = ByteArray(DEFAULT_BUFFER_SIZE)
                while (true) {
                    coroutineContext.ensureActive()
                    val read = input.read(buffer)
                    if (read < 0) break
                    if (read > 0) digest.update(buffer, 0, read)
                }
            }
            val sha256 = digest.digest().joinToString("") { "%02x".format(it) }
            InstalledPackageHashScanResult(packageName, repository.lookup(sha256), null)
        } catch (t: Throwable) {
            if (t is kotlinx.coroutines.CancellationException) throw t
            InstalledPackageHashScanResult(packageName, null, t)
        }
    }
}
''',
'staticanalysis/DefaultStaticPackageAnalyzer.kt': r'''package com.varasecurity.core.staticanalysis

import android.Manifest
import android.content.pm.PackageInfo
import com.varasecurity.core.model.RiskSignal

class DefaultStaticPackageAnalyzer : StaticPackageAnalyzer {
    override suspend fun analyze(packageInfo: PackageInfo): Set<RiskSignal> {
        val result = linkedSetOf<RiskSignal>()
        val requested = packageInfo.requestedPermissions?.toSet().orEmpty()
        if ("android.permission.SYSTEM_ALERT_WINDOW" in requested) result += RiskSignal.OVERLAY
        if (Manifest.permission.READ_SMS in requested) result += RiskSignal.READ_SMS
        if (Manifest.permission.RECEIVE_SMS in requested) result += RiskSignal.RECEIVE_SMS
        if ("android.permission.REQUEST_INSTALL_PACKAGES" in requested) result += RiskSignal.INSTALL_PACKAGES
        packageInfo.services.orEmpty().forEach { service ->
            when (service.permission) {
                "android.permission.BIND_ACCESSIBILITY_SERVICE" -> result += RiskSignal.ACCESSIBILITY_SERVICE
                "android.permission.BIND_NOTIFICATION_LISTENER_SERVICE" -> result += RiskSignal.NOTIFICATION_LISTENER
            }
        }
        packageInfo.receivers.orEmpty().forEach { receiver ->
            if (receiver.permission == "android.permission.BIND_DEVICE_ADMIN") result += RiskSignal.DEVICE_ADMIN
        }
        return result
    }
}
''',
'installer/DefaultInstallerReputationAnalyzer.kt': r'''package com.varasecurity.core.installer

import android.content.pm.PackageInfo
import android.content.pm.PackageManager
import android.os.Build

class DefaultInstallerReputationAnalyzer(
    private val packageManager: PackageManager
) : InstallerReputationAnalyzer {
    override suspend fun analyze(packageInfo: PackageInfo): InstallerReputation = try {
        val installer = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            packageManager.getInstallSourceInfo(packageInfo.packageName).installingPackageName
        } else {
            @Suppress("DEPRECATION")
            packageManager.getInstallerPackageName(packageInfo.packageName)
        }
        when (installer) {
            "com.android.vending" -> InstallerReputation.TRUSTED_STORE
            "com.google.android.packageinstaller",
            "com.android.packageinstaller",
            "com.google.android.permissioncontroller" -> InstallerReputation.KNOWN_INSTALLER
            else -> InstallerReputation.UNKNOWN
        }
    } catch (_: Exception) {
        InstallerReputation.UNKNOWN
    }
}
''',
'cert/CertificateReputationRepository.kt': r'''package com.varasecurity.core.cert

interface CertificateReputationRepository {
    fun lookup(fingerprintSha256: String): CertificateReputation
}

class InMemoryCertificateReputationRepository(
    entries: Map<String, CertificateReputation> = emptyMap()
) : CertificateReputationRepository {
    private val normalized = entries.mapKeys { it.key.lowercase() }
    override fun lookup(fingerprintSha256: String): CertificateReputation =
        normalized[fingerprintSha256.lowercase()] ?: CertificateReputation.UNKNOWN
}
''',
'cert/AndroidSignerExtractionResult.kt': r'''package com.varasecurity.core.cert

data class AndroidSignerExtractionResult(
    val currentSigners: List<ByteArray>,
    val historicalSigners: List<ByteArray>
)
''',
'cert/AndroidSignerExtractor.kt': r'''package com.varasecurity.core.cert

import android.content.pm.PackageInfo
import android.os.Build

class AndroidSignerExtractor {
    fun extract(packageInfo: PackageInfo): AndroidSignerExtractionResult {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            val info = packageInfo.signingInfo
            if (info == null) AndroidSignerExtractionResult(emptyList(), emptyList())
            else {
                val current = info.apkContentsSigners?.map { it.toByteArray() }.orEmpty()
                val history = info.signingCertificateHistory?.map { it.toByteArray() }.orEmpty()
                AndroidSignerExtractionResult(current, history)
            }
        } else {
            @Suppress("DEPRECATION")
            AndroidSignerExtractionResult(packageInfo.signatures?.map { it.toByteArray() }.orEmpty(), emptyList())
        }
    }
}
''',
'cert/CertificateAnalyzer.kt': r'''package com.varasecurity.core.cert

import java.security.MessageDigest

class CertificateAnalyzer(
    private val repository: CertificateReputationRepository
) {
    fun assess(extraction: AndroidSignerExtractionResult): CertificateAssessmentInput {
        if (extraction.currentSigners.isEmpty() && extraction.historicalSigners.isEmpty()) {
            return CertificateAssessmentInput(emptyList(), CertificateAssessmentStatus.SIGNER_UNAVAILABLE)
        }
        val evidence = mutableListOf<CertificateEvidence>()
        extraction.currentSigners.forEach { bytes -> evidence += evidence(bytes, SignerRole.CURRENT) }
        extraction.historicalSigners.forEach { bytes ->
            val fp = sha256(bytes)
            if (evidence.none { it.fingerprintSha256 == fp && it.signerRole == SignerRole.CURRENT }) {
                evidence += CertificateEvidence(fp, repository.lookup(fp), SignerRole.HISTORY)
            }
        }
        return CertificateAssessmentInput(evidence, CertificateAssessmentStatus.AVAILABLE)
    }

    private fun evidence(bytes: ByteArray, role: SignerRole): CertificateEvidence {
        val fp = sha256(bytes)
        return CertificateEvidence(fp, repository.lookup(fp), role)
    }

    private fun sha256(bytes: ByteArray): String = MessageDigest.getInstance("SHA-256")
        .digest(bytes).joinToString("") { "%02x".format(it) }
}
''',
'cert/DefaultPackageCertificateScanner.kt': r'''package com.varasecurity.core.cert

import android.content.pm.PackageInfo

class DefaultPackageCertificateScanner(
    private val extractor: AndroidSignerExtractor,
    private val analyzer: CertificateAnalyzer
) : PackageCertificateScanner {
    override suspend fun scan(packageInfo: PackageInfo): PackageCertificateScanResult {
        val packageName = packageInfo.packageName.orEmpty()
        val assessment = try {
            analyzer.assess(extractor.extract(packageInfo))
        } catch (_: Exception) {
            CertificateAssessmentInput(emptyList(), CertificateAssessmentStatus.PARSE_ERROR)
        }
        return PackageCertificateScanResult(packageName, assessment)
    }
}
'''
}
for rel, content in files.items():
    p = base / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding='utf-8')
print('VARA Android package detection stages implemented')
