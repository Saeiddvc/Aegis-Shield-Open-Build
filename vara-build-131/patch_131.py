from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: patch_131.py <android-project-root>')
root=Path(sys.argv[1])
base=root/'app/src/main/java/com/varasecurity/ui/scan'
files={
'UIScanSummary.kt':'''package com.varasecurity.ui.scan

data class UIScanSummary(
    val malwareCount:Int,
    val suspiciousCount:Int,
    val configRiskCount:Int,
    val infoCount:Int,
    val startedAtMillis:Long,
    val finishedAtMillis:Long
)
''',
'UIScanModels.kt':'''package com.varasecurity.ui.scan

import com.varasecurity.core.heuristic.DetectionSeverity
import com.varasecurity.core.heuristic.DetectionType
import com.varasecurity.core.model.DetectionReason

data class UIScanItem(
    val packageName:String,
    val detectionType:DetectionType,
    val severity:DetectionSeverity,
    val label:UIScanLabel,
    val reasons:List<DetectionReason>,
    val icon:UIScanIcon,
    val actions:List<UIRemediationAction>
)
enum class UIScanIcon { MALWARE, SUSPICIOUS, CONFIG_RISK, INFO }
enum class UIScanLabel { MALWARE_CRITICAL, MALWARE_HIGH, MALWARE, SUSPICIOUS_HIGH, SUSPICIOUS, SUSPICIOUS_LOW, CONFIG_RISK, INFO }
enum class UIRemediationAction { OPEN_APP_SETTINGS, UNINSTALL_APP, REVIEW_PERMISSIONS, REVIEW_ACCESSIBILITY, REVIEW_OVERLAY_PERMISSION, REVIEW_SMS_PERMISSION, REVIEW_DEVICE_ADMIN, FIX_CONFIGURATION, LEARN_MORE, REPORT_FALSE_POSITIVE }

data class UIScanResults(val summary:UIScanSummary,val items:List<UIScanItem>,val partialFailures:Int)
''',
'UIScanItemMapper.kt':'''package com.varasecurity.ui.scan

import com.varasecurity.core.heuristic.DetectionSeverity
import com.varasecurity.core.heuristic.DetectionType
import com.varasecurity.core.heuristic.PackageSecurityAssessmentResult

object UIScanItemMapper {
    private object ReasonCodes {
        const val ACCESSIBILITY_PLUS_OVERLAY="ACCESSIBILITY_PLUS_OVERLAY"
        const val ACCESSIBILITY_PLUS_SMS="ACCESSIBILITY_PLUS_SMS"
        const val ACCESSIBILITY_OVERLAY_SMS="ACCESSIBILITY_OVERLAY_SMS"
    }
    fun fromAssessment(result:PackageSecurityAssessmentResult):UIScanItem {
        val a=result.assessment
        return UIScanItem(result.packageName,a.detectionType,a.severity,mapLabel(a.detectionType,a.severity),a.reasons,mapIcon(a.detectionType),mapActions(result))
    }
    private fun mapIcon(type:DetectionType)=when(type){DetectionType.MALWARE->UIScanIcon.MALWARE;DetectionType.SUSPICIOUS->UIScanIcon.SUSPICIOUS;DetectionType.CONFIG_RISK->UIScanIcon.CONFIG_RISK;DetectionType.INFO->UIScanIcon.INFO}
    private fun mapLabel(type:DetectionType,severity:DetectionSeverity)=when(type){
        DetectionType.MALWARE->when(severity){DetectionSeverity.CRITICAL->UIScanLabel.MALWARE_CRITICAL;DetectionSeverity.HIGH->UIScanLabel.MALWARE_HIGH;else->UIScanLabel.MALWARE}
        DetectionType.SUSPICIOUS->when(severity){DetectionSeverity.HIGH,DetectionSeverity.CRITICAL->UIScanLabel.SUSPICIOUS_HIGH;DetectionSeverity.LOW,DetectionSeverity.INFO->UIScanLabel.SUSPICIOUS_LOW;else->UIScanLabel.SUSPICIOUS}
        DetectionType.CONFIG_RISK->UIScanLabel.CONFIG_RISK
        DetectionType.INFO->UIScanLabel.INFO
    }
    private fun mapActions(result:PackageSecurityAssessmentResult):List<UIRemediationAction>{
        val a=result.assessment
        if(a.detectionType==DetectionType.INFO) return listOf(UIRemediationAction.LEARN_MORE,UIRemediationAction.REPORT_FALSE_POSITIVE)
        val actions=linkedSetOf<UIRemediationAction>()
        actions+=UIRemediationAction.OPEN_APP_SETTINGS
        if(a.detectionType==DetectionType.MALWARE || a.detectionType==DetectionType.SUSPICIOUS) actions+=UIRemediationAction.UNINSTALL_APP
        val codes=a.reasons.map{it.code}.toSet()
        if(ReasonCodes.ACCESSIBILITY_PLUS_OVERLAY in codes || ReasonCodes.ACCESSIBILITY_PLUS_SMS in codes || ReasonCodes.ACCESSIBILITY_OVERLAY_SMS in codes) actions+=UIRemediationAction.REVIEW_ACCESSIBILITY
        if(ReasonCodes.ACCESSIBILITY_PLUS_OVERLAY in codes || ReasonCodes.ACCESSIBILITY_OVERLAY_SMS in codes) actions+=UIRemediationAction.REVIEW_OVERLAY_PERMISSION
        if(ReasonCodes.ACCESSIBILITY_PLUS_SMS in codes || ReasonCodes.ACCESSIBILITY_OVERLAY_SMS in codes) actions+=UIRemediationAction.REVIEW_SMS_PERMISSION
        if(a.detectionType==DetectionType.CONFIG_RISK) actions+=UIRemediationAction.FIX_CONFIGURATION
        actions+=UIRemediationAction.LEARN_MORE
        actions+=UIRemediationAction.REPORT_FALSE_POSITIVE
        return actions.toList()
    }
}
''',
'ScanResultsMapper.kt':'''package com.varasecurity.ui.scan

import com.varasecurity.core.scan.DeviceScanResult

object ScanResultsMapper {
    fun fromDeviceScanResult(result:DeviceScanResult):UIScanResults = UIScanResults(
        summary=UIScanSummary(result.malwareCount,result.suspiciousCount,result.configRiskCount,result.infoCount,result.startedAtMillis,result.finishedAtMillis),
        items=result.assessments.map{UIScanItemMapper.fromAssessment(it)},
        partialFailures=result.failures.size
    )
}
'''
}
for rel,content in files.items():
    p=base/rel; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(content,encoding='utf-8')
print('VARA scan results mapping layer integrated')
