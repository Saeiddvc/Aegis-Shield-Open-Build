from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: patch_126.py <android-project-root>')

root = Path(sys.argv[1])
p = root / 'app/src/main/java/com/varasecurity/core/heuristic/HeuristicEngine.kt'
p.parent.mkdir(parents=True, exist_ok=True)
p.write_text(r'''package com.varasecurity.core.heuristic

import com.varasecurity.core.cert.CertificateAssessmentStatus
import com.varasecurity.core.cert.CertificateReputation
import com.varasecurity.core.hash.HashReputationStatus
import com.varasecurity.core.installer.InstallerReputation
import com.varasecurity.core.model.AppliedCorrelation
import com.varasecurity.core.model.DetectionReason
import com.varasecurity.core.model.RiskSignal

class HeuristicEngine {
    fun assess(input: HeuristicInput): HeuristicAssessment {
        val signals = input.static?.signals.orEmpty()
        if (input.hash?.status == HashReputationStatus.KNOWN_MALICIOUS) {
            return HeuristicAssessment(
                score = 100,
                confidence = 100,
                severity = DetectionSeverity.CRITICAL,
                detectionType = DetectionType.MALWARE,
                suspicious = true,
                staticScore = 0,
                certificateScore = 0,
                installerScore = 0,
                contributingRiskSignals = signals,
                reasons = listOf(DetectionReason("KNOWN_MALICIOUS_HASH", "Known malicious file hash")),
                appliedCorrelations = emptyList()
            )
        }

        var staticScore = 0
        var certificateScore = 0
        var installerScore = 0
        val reasons = mutableListOf<DetectionReason>()
        val correlations = mutableListOf<AppliedCorrelation>()

        if (RiskSignal.ACCESSIBILITY_SERVICE in signals) staticScore += 4
        if (RiskSignal.OVERLAY in signals) staticScore += 3
        if (RiskSignal.READ_SMS in signals || RiskSignal.RECEIVE_SMS in signals) staticScore += 3
        if (RiskSignal.INSTALL_PACKAGES in signals) staticScore += 2
        if (RiskSignal.DEVICE_ADMIN in signals) staticScore += 3
        if (RiskSignal.NOTIFICATION_LISTENER in signals) staticScore += 2

        val hasAccessibility = RiskSignal.ACCESSIBILITY_SERVICE in signals
        val hasOverlay = RiskSignal.OVERLAY in signals
        val hasSms = RiskSignal.READ_SMS in signals || RiskSignal.RECEIVE_SMS in signals

        fun addCorrelation(rule: CorrelationRule, delta: Int, code: String, message: String, toInstaller: Boolean = false) {
            val reason = DetectionReason(code, message)
            if (toInstaller) installerScore += delta else staticScore += delta
            correlations += AppliedCorrelation(rule, delta, reason)
            reasons += reason
        }

        if (hasAccessibility && hasOverlay && hasSms) {
            addCorrelation(CorrelationRule.ACCESSIBILITY_OVERLAY_SMS, 18, "ACCESSIBILITY_OVERLAY_SMS", "Accessibility, overlay and SMS capabilities combined")
        } else {
            if (hasAccessibility && hasOverlay) {
                addCorrelation(CorrelationRule.ACCESSIBILITY_PLUS_OVERLAY, 18, "ACCESSIBILITY_PLUS_OVERLAY", "Accessibility and overlay capabilities combined")
            }
            if (hasAccessibility && hasSms) {
                addCorrelation(CorrelationRule.ACCESSIBILITY_PLUS_SMS, 12, "ACCESSIBILITY_PLUS_SMS", "Accessibility and SMS capabilities combined")
            }
        }

        if (RiskSignal.INSTALL_PACKAGES in signals && input.installer == InstallerReputation.SIDELOADED) {
            addCorrelation(CorrelationRule.INSTALL_PACKAGES_PLUS_SIDELOAD, 12, "INSTALL_PACKAGES_PLUS_SIDELOAD", "Package installation capability combined with sideload source", true)
        }

        val highRiskCapability = hasAccessibility || hasOverlay || hasSms || RiskSignal.INSTALL_PACKAGES in signals || RiskSignal.DEVICE_ADMIN in signals || RiskSignal.NOTIFICATION_LISTENER in signals
        if (RiskSignal.BOOT_RECEIVER in signals && highRiskCapability) {
            addCorrelation(CorrelationRule.BOOT_RECEIVER_WITH_HIGH_RISK_CAPABILITY, 8, "BOOT_RECEIVER_WITH_HIGH_RISK_CAPABILITY", "Boot persistence combined with a high-risk capability")
        }

        if (input.installer == InstallerReputation.SIDELOADED) installerScore += 2

        val cert = input.certificate
        if (cert?.status == CertificateAssessmentStatus.AVAILABLE && cert.certificates.any { it.reputation == CertificateReputation.KNOWN_MALICIOUS }) {
            certificateScore += 50
            reasons += DetectionReason("KNOWN_MALICIOUS_CERTIFICATE", "Known malicious signing certificate")
        }

        val score = (staticScore + certificateScore + installerScore).coerceIn(0, 100)
        val type = when {
            score >= 20 -> DetectionType.SUSPICIOUS
            score >= 10 -> DetectionType.CONFIG_RISK
            else -> DetectionType.INFO
        }
        val severity = when {
            score >= 80 -> DetectionSeverity.CRITICAL
            score >= 45 -> DetectionSeverity.HIGH
            score >= 20 -> DetectionSeverity.MEDIUM
            score >= 1 -> DetectionSeverity.LOW
            else -> DetectionSeverity.INFO
        }
        val confidence = when {
            certificateScore >= 50 -> 90
            correlations.any { it.rule == CorrelationRule.ACCESSIBILITY_OVERLAY_SMS } -> 80
            correlations.size >= 2 -> 70
            correlations.size == 1 -> 60
            score > 0 -> 40
            else -> 0
        }

        return HeuristicAssessment(
            score = score,
            confidence = confidence,
            severity = severity,
            detectionType = type,
            suspicious = type == DetectionType.SUSPICIOUS || type == DetectionType.MALWARE,
            staticScore = staticScore,
            certificateScore = certificateScore,
            installerScore = installerScore,
            contributingRiskSignals = signals,
            reasons = reasons.distinctBy { it.code },
            appliedCorrelations = correlations
        )
    }
}
''', encoding='utf-8')

print('VARA locked HeuristicEngine integrated')
